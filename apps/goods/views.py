from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http.response import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.views.generic.base import View
from django_redis import get_redis_connection
from apps.goods.models import GoodsCategory, IndexSlideGoods, IndexPromotion, IndexCategoryGoods, GoodsSKU
from apps.orders.models import OrderGoods
from apps.users.models import Address
from utils.common import BaseCartView


# Create your views here.

class IndexView(BaseCartView):
    """首页"""

    def get(self, request):
        """进入首页"""
        context = cache.get('index_page_data')
        if context is None:
            categories = GoodsCategory.objects.all()
            slide_skus = IndexSlideGoods.objects.all().order_by('index')
            promotions = IndexPromotion.objects.all().order_by('index')
            for category in categories:
                text_skus = IndexCategoryGoods.objects.filter(
                    category=category, display_type=0).order_by('index')
                img_skus = IndexCategoryGoods.objects.filter(category=category, display_type=1) \
                    .order_by('index')
                category.text_skus = text_skus
                category.img_skus = img_skus
            context = {
                'catogories': categories,
                'slide_skus': slide_skus,
                'promotions': promotions,
            }
            cache.set('index_page_data', context, 3600)
        else:
            pass
        cart_count = super().get_cart_count(request)
        context.update({'cart_count': cart_count})
        return render(request, 'index.html', context)


class DetailView(BaseCartView):
    """进入商品详情页面"""

    def get(self, request, sku_id):
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        categories = GoodsCategory.objects.all()
        new_skus = GoodsSKU.objects.filter(
            category=sku.category).order_by('-create_time')[0:2]
        other_skus = sku.spu.goodssku_set.exclude(id=sku.id)
        if request.user.is_authenticated():
            user_id = request.user.id
            strict_redis = get_redis_connection('default')
            cart_count = super().get_cart_count(request)
            key = 'history_%s' % user_id
            strict_redis.lrem(key, 0, sku.id)
            strict_redis.lpush(key, sku.id)
            strict_redis.ltrim(key, 0, 2)
        else:
            cart_count = 0
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
        sort = request.GET.get('sort', 'default')
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))
        categories = GoodsCategory.objects.all()
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[0:2]
        if sort == 'price':
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            sort = 'default'
        page_num = int(page_num)
        paginator = Paginator(skus, 2)
        try:
            page = paginator.page(page_num)
        except EmptyPage:
            page = paginator.page(1)
        page_list = paginator.page_range
        if request.user.is_authenticated():
            cart_count = super().get_cart_count(request)
        else:
            cart_count = 0
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
