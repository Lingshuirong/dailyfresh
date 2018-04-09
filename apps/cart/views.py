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

        # 判断用户是否登录
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1,'errmsg': '请先登录'})

        # 获取用户提交的参数
        user_id = request.user.id
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # todo： 判断参数合法性
        if not all([sku_id, count]):
            return JsonResponse({'code': 2, 'errmsg': '请求参数不能为空'})
        # 检验购买参数数量的合法性
        try:
            count = int(count)
        except:
            return JsonResponse({'code': 3, 'errmsg': '购买数量格式不正确'})

        # 检验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 4, 'errmsg': '商品不存在'})

        # todo： 业务处理：添加商品到redis数据库中
        # 格式 cart_1 = {'1': '2', '2': '2'}
        strict_redis = get_redis_connection()
        key = 'cart_%s' % user_id
        # 获取不到返回None
        val = strict_redis.hget(key, sku_id)
        if val:
            count += int(val)

        # 检验库存是否充足
        if count > sku.stock:
            return JsonResponse({'code': 5, 'errmsg': '库存不足'})

        # 更新商品数量
        strict_redis.hset(key, sku_id, count)

        # todo: 计算购物车中上皮总数量
        cart_count = 0
        vals = strict_redis.hvals(key)
        for val in vals:
            cart_count += int(val)
        # 响应json数据
        context ={
            'code': 0,
            'cart_count': cart_count
             }
        return JsonResponse(context)


class CartInfoView(LoginRequiredMixin, View):
    """购物车显示界面： 需要先登录才能访问"""

    def get(self, request):
        # 查询当前登录用户添加到哦购物车中的嗖又商品
        sr = get_redis_connection()
        key = 'cart_%s' % request.user.id
        # 获取购物车中所有的商品
        my_dict = sr.hgetall(key)

        # 保存购物车中的所有的商品对象
        skus = []
        # 商品总数量
        total_count = 0
        # 商品总金额
        total_amount = 0

        for sku_id, count in my_dict.items():
            # 根据商品id，查询商品对象
            sku = GoodsSKU.objects.get(id=sku_id)
            # sku对象新增一个实例属性
            sku.count = int(count)
            sku.amount = sku.price * int(count)

            # 累加总数量和总金额
            total_count += sku.count
            total_amount += sku.amount

            # 列表中新增一个商品对象
            skus.append(sku)

        # 定义模板显示的数据
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

        # 判断登录状态
        if not request.user.is_authenticated():
            return JsonResponse({'code': 1, 'errmsg': '请先登录'})

        # 获取请求参数: sku_id count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 参数合法性判断
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

        # todo: 业务处理: 保存购物车商品数量
        # hset cart_1 sku_id count
        strict_redis = get_redis_connection()
        key = 'cart_%s' % request.user.id
        strict_redis.hset(key, sku_id, count)

        # 响应json
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
















