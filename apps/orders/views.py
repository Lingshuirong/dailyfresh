from time import sleep

import alipay
from django.db import transaction
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.http.response import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic.base import View
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from apps.orders.models import OrderInfo, OrderGoods
from datetime import datetime
from apps.users.models import Address
from utils.common import LoginRequiredMixin


class PlaceOrderView(LoginRequiredMixin, View):
    """订单确认页面"""

    def post(self, request):
        """进入确认订单界面"""

        # 获取请求参数：sku_ids
        sku_ids = request.POST.getlist('sku_ids')

        # 校验参数不能为空
        if not sku_ids:
            # 如果sku_ids为空，则重定向到购物车,让用户重选商品
            return redirect(reverse('cart:info'))

        # 获取用户地址信息(此处使用最新添加的地址)
        try:
            address = Address.objects.filter(
                user=request.user).latest('create_time')
        except Address.DoesNotExist:
            address = None  # 没有收货地址，则用户需要点界面的按钮击新增地址

        skus = []  # 订单商品列表
        total_count = 0  # 商品总数量
        total_amount = 0  # 商品总金额

        # todo: 查询购物车中的所有的商品
        redis_conn = get_redis_connection()
        # cart_1 = {1: 1, 2: 2}
        key = 'cart_%s' % request.user.id
        # cart_dict字典的键值都为bytes类型
        cart_dict = redis_conn.hgetall(key)
        # 循环操作每一个订单商品
        for sku_id in sku_ids:
            # 查询一个商品对象
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                # 没有查询到商品, 回到购物车界面
                return redirect(reverse('cart:info'))

            # 获取商品数量和小计金额(需要进行数据类型转换)
            sku_count = cart_dict.get(sku_id.encode())
            sku_count = int(sku_count)
            sku_amount = sku.price * sku_count

            # 新增实例属性,以便在模板界面中显示
            sku.count = sku_count
            sku.amount = sku_amount

            # 添加商品对象到列表中
            skus.append(sku)

            # 累计商品总数量和总金额
            total_count += sku_count
            total_amount += sku_amount

        # 运费(运费模块)
        trans_cost = 10
        # 实付金额
        total_pay = total_amount + trans_cost

        # 商品id字符串:  [1,2]  -> 1,2
        sku_ids_str = ','.join(sku_ids)

        # 定义模板显示的字典数据
        context = {
            'skus': skus,
            'address': address,
            'total_count': total_count,
            'total_amount': total_amount,
            'trans_cost': trans_cost,
            'total_pay': total_pay,
            'sku_ids_str': sku_ids_str,
        }


        # 响应结果: 返回确认订单html界面
        return render(request, 'place_order.html', context)


class CommitOrderView(View):
    """提交订单"""

    @transaction.atomic
    def post(self, request):
        # 登录判断
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '请先登录'})

        # 获取请求参数：address_id, pay_method, sku_ids_str (例如: 1,2 )
        address_id = request.POST.get('address_id')
        pay_method = request.POST.get('pay_method')
        sku_ids_str = request.POST.get('sku_ids_str')

        # 校验参数不能为空
        if not all([address_id, pay_method, sku_ids_str]):
            return JsonResponse({'code': 2, 'message': '参数不能为空'})

        # 类型转换: str -> 列表
        # 1,2  -> [1,2]
        sku_ids = sku_ids_str.split(',')

        # 判断地址是否存在
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '地址不存在'})

        # 创建一个保存点
        point = transaction.savepoint()
        try:
            # todo: 修改订单信息表: 保存订单数据到订单信息表中
            total_count = 0
            total_amount = 0
            trans_cost = 10
            # 订单号
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

            # 从Redis查询出购物车数据
            # 注意: 返回的是字典, 键值都为bytes类型
            # cart_1 = {1: 2, 2: 2}
            strict_redis = get_redis_connection()
            # strict_redis = StrictRedis()
            key = 'cart_%s' % request.user.id
            cart_dict = strict_redis.hgetall(key)

            # todo: 核心业务: 遍历每一个商品, 并保存到订单商品表
            for sku_id in sku_ids:
                # 查询订单中的每一个商品
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except:

                    # 回滚到上面的保存点: 撤销订单信息表的修改
                    transaction.savepoint_rollback(point)

                    return JsonResponse({'code': 4, 'message': '商品不存在'})

                # 获取商品数量，并判断库存
                # {1: 2, 2: 2}
                sku_count = cart_dict.get(sku_id.encode())
                sku_count = int(sku_count)
                if sku_count > sku.stock:
                    # 回滚到上面的保存点: 撤销订单信息表的修改
                    transaction.savepoint_rollback(point)

                    return JsonResponse({'code': 5, 'message': '库存不足'})

                # todo: 修改订单商品表: 保存订单商品到订单商品表
                OrderGoods.objects.create(
                    count=sku_count,
                    price=sku.price,
                    sku=sku,
                    order=order,
                )

                # todo: 修改商品sku表: 减少商品库存, 增加商品销量
                sku.stock -= sku_count
                sku.sales += sku_count
                sku.save()

                # 累加商品数量和总金额
                total_count += sku_count
                total_amount += sku.price * sku_count

                # todo: 修改订单信息表: 修改商品总数量和总金额
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()
        except Exception:
            # 回滚到上面的保存点: 撤销订单信息表的修改
            transaction.savepoint_rollback(point)
            return JsonResponse({'code': 6, 'message': '创建订单失败'})

        # 提交事务
        transaction.savepoint_commit(point)

        # 从Redis中删除购物车中的商品
        # cart_1 = {1: 2, 2: 2}
        # redis命令: hdel cart_1 1 2
        # strict_redis.delete(key)
        # [1,2] -> 1 2
        strict_redis.hdel(key, *sku_ids)

        # 订单创建成功， 响应请求，返回json
        return JsonResponse({'code': 0, 'message': '创建订单成功'})


class OrderPayView(View):

    def post(self, request):
        """支付功能"""

        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '请先登录'})

        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'code': 2, 'message': '订单id不能为空'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          status=1,
                                          user=request.user)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3,'message': '订单无效'})


        # 通过第三方sdk，调用支付宝接口，实现支付功能
        # 1.初始化
        from alipay import AliPay
        app_private_key_string = open('apps/orders/app_private_key.pem').read()
        alipay_public_key_string = open('apps/orders/alipay_public_key.pem').read()

        alipay = AliPay(
            appid='2016091000481374',
            app_notify_url=None, #默认回调url
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用
            sign_type='RSA2',
            debug=True #Ture表示使用沙箱环境
        )


        # 2.调用支付接口
        total_pay = order.total_amount + order.trans_cost
        order_string = alipay.api_alipay_trade_app_pay(
            out_trade_no=order_id,  # 订单号
            total_amount=str(total_pay),
            subject="生鲜测试订单",
            return_url=None,
            notify_url=None
        )

        # 响应浏览器，返回json数据
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        print(pay_url)
        return JsonResponse({'code': 0, 'pay_url': pay_url})


class CheckPayView(View):

    def post(self, request):
        """订单支付结果查询"""

        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'message': '请先登录'})

        order_id = request.POST.get('order_id')
        if not order_id:
            return JsonResponse({'code': 2, 'message': '订单id不能为空'})

        # 查询订单是否存在
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          status=1,
                                          user=request.user)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '订单无效'})

        # 通过第三方sdk，调用支付宝接口，实现订单支付功能
        # 1.初始化
        from alipay import AliPay
        app_private_key_string = open('apps/orders/app_private_key.pem').read()
        alipay_public_key_string = open('apps/orders/alipay_public_key.pem').read()

        alipay = AliPay(
            appid='2016091000481374',
            app_notify_url=None,
            app_private_key_string=app_private_key_string,
            alipay_public_key_string=alipay_public_key_string,
            sign_type='RSA2',
            debug=True
        )

        # 判断订单是否支付成功
        while(True):
            response = alipay.api_alipay_trade_query(out_trade_no=order_id)
            code = response.get('code') # 响应状态码
            trade_no = response.get('trade_no') # 支付交易号
            trade_status = response.get('trade_status')  # 订单支付状态

            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 修改订单状态
                order.status = 4
                order.trade_no = trade_no
                order.save()
                return JsonResponse({'code': 0, 'message': '订单支付成功'})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                sleep()
                print(code)
                continue
            else:
                # 支付失败
                print('code=%s' % code)
                print('trade_status=%s' % trade_status)
                return JsonResponse({'code': 4, 'message': '订单支付失败'})









