from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.views.generic.base import View

# Create your views here.
from django_redis import get_redis_connection

from apps.goods.models import GoodsCategory, IndexSlideGoods, IndexPromotion, IndexCategoryGoods, GoodsSKU
from apps.orders.models import OrderGoods
from utils.common import BaseCartView


class IndexView(BaseCartView):
    """首页"""

    def get(self, request):
        """进入首页"""

        # 读取缓存
        context = cache.get('index_page_data')

        # 判断缓存是否为空
        if context is None:
            print('缓存为空，数据将从mysql查找')
            # 查询商品列别数据
            categories = GoodsCategory.objects.all()

            # 查询商品轮播数据
            slide_skus = IndexSlideGoods.objects.all().order_by('index')

            # 查询商品促销活动数据
            promotions = IndexPromotion.objects.all().order_by('index')

            # 查询类别商品数据
            for category in categories:
                # 查询某一类别下的文字类别商品
                text_skus = IndexCategoryGoods.objects.filter(
                    category=category, display_type=0).order_by('index')

                # 查询某一类别下图片类别商品
                img_skus = IndexCategoryGoods.objects.filter(category=category, display_type=1) \
                    .order_by('index')

                # 动态地给类别新增实例属性
                category.text_skus = text_skus
                category.img_skus = img_skus

            context = {
                'catogories': categories,
                'slide_skus': slide_skus,
                'promotions': promotions,
            }

            # 缓存数据
            cache.set('index_page_data', context, 3600)

        else:
            pass

        # 查询购物车中商品数量（动态生成）
        cart_count = super().get_cart_count(request)

        # 更新数据
        context.update({'cart_count': cart_count})

        return render(request, 'index.html', context)


class DetailView(BaseCartView):
    """进入商品详情页面"""

    def get(self, request, sku_id):
        # 查询商品详情信息
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 查询不到商品则跳转
            return redirect(reverse('goods:index'))

        # 获取商品的评论信息
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取所有的类别数据
        categories = GoodsCategory.objects.all()

        # 获取最新推荐
        new_skus = GoodsSKU.objects.filter(
            category=sku.category).order_by('-create_time')[0:2]

        # 查询其他规格的商品
        other_skus = sku.spu.goodssku_set.exclude(id=sku.id)

        # 购物车中商品数量

        # 判断用户是否登陆
        if request.user.is_authenticated():
            # 获取用户id
            user_id = request.user.id

            # 从redis中获取购物车的信息
            strict_redis = get_redis_connection('default')
            # cart_dict = strict_redis.hgetall('cart_%s' % user_id)
            # for val in cart_dict.values():
            #     cart_count += int(val)
            cart_count = super().get_cart_count(request)

            # 移除现有的商品浏览记录
            key = 'history_%s' % user_id
            strict_redis.lrem(key, 0, sku.id)

            # 从左侧添加新的商品浏览记录
            strict_redis.lpush(key, sku.id)

            # 控制历史浏览记录最多保存3项(包含头尾)
            strict_redis.ltrim(key, 0, 2)

        context = {
            'categories': categories,
            'sku': sku,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'other_skus': other_skus,
            'order_skus': order_skus

        }

        return render(request, 'detail.html', context)


class ListView(BaseCartView):
    """商品列表"""

    def get(self, request, category_id, page_num):
        # 获取sort参数：如果用户不传，就是默认的排序规则
        sort = request.GET.get('sort', 'default')

        # 校验参数
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 查询所有商品类别
        categories = GoodsCategory.objects.all()

        # 查询该类商品的新品推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[0:2]

        # 查询该类别所有商品sku信息，按照排序规则来查询
        if sort == 'price':
            # 按照价格高低排序
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            sort = 'default'

        # 分页:需要知道从第几页展示
        page_num = int(page_num)

        # 创建分液器：每页两条记录
        paginator = Paginator(skus, 2)

        # 校验page_num：只有知道分页对象，才能知道page_num是否正确
        try:
            page = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户显示第一页数据
            page = paginator.page(1)

        # 获取页数列表
        page_list = paginator.page_range

        if request.user.is_authenticated():
            cart_count = super().get_cart_count(request)

            # 构造上下文
        context = {
            'category': category,
            'categories': categories,
            'page': page,
            'new_skus': new_skus,
            'page_list': page_list,
            'cart_count': cart_count,
            'sort': sort,
        }

        return render(request, 'list.html', context)
