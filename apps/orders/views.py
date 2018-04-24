from time import sleep

import alipay
from django.db import transaction
from django.template import loader
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic.base import View
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from apps.orders.models import OrderInfo, OrderGoods
from datetime import datetime
from apps.users.models import Address, User
from utils.common import LoginRequiredMixin


class PlaceOrderView(LoginRequiredMixin, View):
    """订单确认页面"""

    def get(self, request):
        buy_context = BuyView()
        return render(request, 'place_order2.html', buy_context.context)

    def post(self, request):
        """进入确认订单界面"""
        sku_ids = request.POST.getlist('sku_ids')
        if not sku_ids:
            return redirect(reverse('cart:info'))
        try:
            address = Address.objects.filter(
                user=request.user).latest('create_time')
        except Address.DoesNotExist:
            address = None
        skus = []
        total_count = 0
        total_amount = 0
        redis_conn = get_redis_connection()
        key = 'cart_%s' % request.user.id
        cart_dict = redis_conn.hgetall(key)
        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                return redirect(reverse('cart:info'))
            sku_count = cart_dict.get(sku_id.encode())
            sku_count = int(sku_count)
            sku_amount = sku.price * sku_count
            sku.count = sku_count
            sku.amount = sku_amount
            skus.append(sku)
            total_count += sku_count
            total_amount += sku_amount
        trans_cost = 10
        total_pay = total_amount + trans_cost
        sku_ids_str = ','.join(sku_ids)
        context = {
            'skus': skus,
            'address': address,
            'total_count': total_count,
            'total_amount': total_amount,
            'trans_cost': trans_cost,
            'total_pay': total_pay,
            'sku_ids_str': sku_ids_str,
        }
        return render(request, 'place_order.html', context)


class CommitOrderView(View):
    """提交订单"""

    @transaction.atomic
    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '请先登录'})
        address_id = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids_str = request.POST.get('sku_ids_str')
        if not all([address_id, pay_method, sku_ids_str]):
            return JsonResponse({'code': 2, 'message': '参数不能为空'})
        sku_ids = sku_ids_str.split(',')
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '地址不存在'})
        point = transaction.savepoint()
        try:
            total_count = 0
            total_amount = 0
            trans_cost = 10
            order_id = datetime.now().strftime('%Y%m%d%H%M%S') \
                       + str(request.user.id)
            order = OrderInfo.objects.create(
                order_id=order_id,
                total_count=total_count,
                total_amount=total_amount,
                trans_cost=trans_cost,
                pay_method=pay_method,
                user=request.user,
                address=address
            )
            strict_redis = get_redis_connection()
            key = 'cart_%s' % request.user.id
            cart_dict = strict_redis.hgetall(key)
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except:
                    transaction.savepoint_rollback(point)
                    return JsonResponse({'code': 4, 'message': '商品不存在'})
                sku_count = cart_dict.get(sku_id.encode())
                sku_count = int(sku_count)
                if sku_count > sku.stock:
                    transaction.savepoint_rollback(point)
                    return JsonResponse({'code': 5, 'message': '库存不足'})
                OrderGoods.objects.create(
                    count=sku_count,
                    price=sku.price,
                    sku=sku,
                    order=order,
                )
                sku.stock -= sku_count
                sku.sales += sku_count
                sku.save()
                total_count += sku_count
                total_amount += sku.price * sku_count
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()
        except Exception:
            transaction.savepoint_rollback(point)
            return JsonResponse({'code': 6, 'message': '创建订单失败'})
        transaction.savepoint_commit(point)
        strict_redis.hdel(key, *sku_ids)
        return JsonResponse({'code': 0, 'message': '创建订单成功'})


class OrderPayView(View):
    def post(self, request):
        """订单支付"""

        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '用户未登录'})
        order_id = request.POST.get('order_id')
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          status=1,  # 未支付
                                          user=request.user)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '无效订单'})
        # 调用 第三方sdk, 实现支付功能
        from alipay import AliPay
        app_private_key_string = open("apps/orders/app_private_key.pem").read()
        alipay_public_key_string = open("apps/orders/alipay_public_key.pem").read()
        alipay = AliPay(
            appid="2016091000481374",  # 沙箱应用
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2  # 不要使用rsa
            debug=True  # 默认False  True: 表示使用测试环境(沙箱环境)
        )
        total_pay = order.trans_cost + order.total_amount
        # 支付返回的支付结果参数
        order_str = alipay.api_alipay_trade_page_pay(
            subject="天天生鲜支付订单",
            out_trade_no=order_id,
            total_amount=str(total_pay)  # 需要使用str类型, 不能使用浮点型
        )
        # 定义支付引导界面,并返回给浏览器
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_str
        data = {'code': 0, 'pay_url': pay_url}
        return JsonResponse(data)


class CheckPayView(View):
    def post(self, request):

        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '用户未登录'})
        order_id = request.POST.get('order_id')
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=request.user)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 2, 'message': '无效订单'})
        if not order_id:
            return JsonResponse({'code': 3, 'message': '订单id不能为空'})
        # 调用 第三方sdk, 实现支付功能
        # (1) 初始化sdk
        from alipay import AliPay
        app_private_key_string = open("apps/orders/app_private_key.pem").read()
        alipay_public_key_string = open("apps/orders/alipay_public_key.pem").read()

        alipay = AliPay(
            appid="2016091000481374",  # 沙箱应用
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2  # 不要使用rsa
            debug=True  # 默认False  True: 表示使用测试环境(沙箱环境)
        )

        while True:
            result_dict = alipay.api_alipay_trade_query(out_trade_no=order_id)
            code = result_dict.get('code')
            trade_status = result_dict.get('trade_status')
            trade_no = result_dict.get('trade_no')
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                order.status = 4  # 待评价
                order.trade_no = trade_no
                order.save()  # 修改订单信息表
                return JsonResponse({'code': 0, 'message': '支付成功'})
            elif (code == '10000' and trade_status == 'WAIT_BUYER_PAY') or code == '40004':
                sleep(2)
                continue
            else:
                return JsonResponse({'code': 4, 'message': '支付失败'})


class CommentView(View):
    def get(self, request, order_id):
        """显示订单商品评价界面"""
        user = request.user

        if not order_id:
            return redirect(reverse('users:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("users:order"))
        # 根据订单的状态获取订单的状态标题, 并动态新增一个实例属性
        order.status_name = OrderInfo.ORDER_STATUS[order.status]
        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计金额
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        order.order_skus = order_skus
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """订单商品评论"""
        user = request.user

        if not order_id:
            return redirect(reverse('users:order'))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("users:order"))
        total_count = request.POST.get("total_count")
        total_count = int(total_count)
        for i in range(1, total_count + 1):
            sku_id = request.POST.get("sku_%d" % i)
            comment = request.POST.get('comment_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = comment
            order_goods.save()
        order.status = 5
        order.save()
        return redirect(reverse("users:order", args=[1]))


class BuyView(View):

    context = {}

    def post(self, request):
        """直接购买商品"""

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '请先登录'})
        if not all([sku_id, count]):
            return JsonResponse({'code': 2, 'message': '参数不能为空'})
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code': 3, 'message': '购买数量不合法'})
        sku = GoodsSKU.objects.get(id=sku_id)
        if not sku:
            return JsonResponse({'code': 4, 'message': '商品不存在'})
        if count > sku.stock:
            return JsonResponse({'code': 5, 'message': '商品库存不足'})
        strict_redis = get_redis_connection()
        key = 'cart_%s' % request.user.id
        strict_redis.hset(key, sku_id, count)
        user = request.user
        address = Address.objects.filter(
            user=request.user).latest('create_time')
        total_count = count
        trans_cost = 10
        total_amount = total_count * sku.price
        total_pay = total_amount + trans_cost
        sku_amount = count * sku.price
        BuyView.context = {
            'sku': sku,
            'total_count': total_count,
            'trans_cost': trans_cost,
            'total_amount': total_amount,
            'total_pay': total_pay,
            'sku_ids_str': sku_id,
            'user': user,
            'address': address,
            'count': count,
            'sku_amount': sku_amount,
        }
        return JsonResponse({'code': 0, 'message': '发送成功'})
