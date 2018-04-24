from django.core.urlresolvers import reverse
from django.http.response import JsonResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import View
from django_redis import get_redis_connection

from apps.goods.models import GoodsSKU
from apps.users.models import Address
from utils.common import LoginRequiredMixin


class CartAddVies(View):
    """购物车"""

    def post(self, request):
        """
        添加商品到购物车，URL：/cart/add
        :param request:
        :return:
        """

        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'errmsg': '请先登录'})
        user_id = request.user.id
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'code': 2, 'errmsg': '请求参数不能为空'})
        try:
            count = int(count)
        except:
            return JsonResponse({'code': 3, 'errmsg': '购买数量格式不正确'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 4, 'errmsg': '商品不存在'})
        strict_redis = get_redis_connection()
        key = 'cart_%s' % user_id
        val = strict_redis.hget(key, sku_id)
        if val:
            count += int(val)
        if count > sku.stock:
            return JsonResponse({'code': 5, 'errmsg': '库存不足'})
        strict_redis.hset(key, sku_id, count)
        cart_count = 0
        vals = strict_redis.hvals(key)
        for val in vals:
            cart_count += int(val)
        context = {
            'code': 0,
            'cart_count': cart_count
        }
        return JsonResponse(context)


class CartInfoView(LoginRequiredMixin, View):
    """购物车显示界面： 需要先登录才能访问"""

    def get(self, request):
        sr = get_redis_connection()
        key = 'cart_%s' % request.user.id
        my_dict = sr.hgetall(key)
        skus = []
        total_count = 0
        total_amount = 0
        for sku_id, count in my_dict.items():
            sku = GoodsSKU.objects.get(id=sku_id)
            sku.count = int(count)
            sku.amount = sku.price * int(count)
            total_count += sku.count
            total_amount += sku.amount
            skus.append(sku)
        data = {
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
        }
        return render(request, 'cart.html', data)


class CartUpdateView(View):
    """更新购物车"""

    def post(self, request):
        """ 修改购物车商品数量"""
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        if not all([sku_id, count]):
            return JsonResponse({'code': 2, 'errmsg': '参数不能为空'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 3, 'errmsg': '商品不存在'})
        try:
            count = int(count)
        except:
            return JsonResponse({'code': 4, 'errmsg': '购买数量需为整数'})
        if count > sku.stock:
            return JsonResponse({'code': 5, 'errmsg': '库存不足'})
        strict_redis = get_redis_connection()
        key = 'cart_%s' % request.user.id
        strict_redis.hset(key, sku_id, count)
        return JsonResponse({'code': 0, 'message': '商品数量修改成功'})


class CartDeleteView(View):
    """删除购物车数据"""

    def post(self, request):
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        if not sku_id:
            return JsonResponse({'code': 2, 'errmsg': '商品id不能为空'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 3, 'errmsg': '商品不存在'})
        sr = get_redis_connection()
        key = 'cart_%s' % request.user.id
        sr.hdel(key, sku_id)
        return JsonResponse({'code': 0, 'errmssg': '删除商品成功'})
