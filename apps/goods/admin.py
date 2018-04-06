from django.contrib import admin

# Register your models here.
from django.core.cache import cache

from apps.goods.models import GoodsSPU, GoodsCategory, GoodsSKU, IndexSlideGoods, IndexPromotion
from celery_task.tasks import generate_static_html

# admin.site.register(GoodsSPU)


class BaseAdmin(admin.ModelAdmin):
    """商品活动信息管理类"""

    def save_model(self, request, obj, form, change):
        """后台保存数据时候使用"""
        # obj表示保存的对象，调用save（），将对象保存到数据库中
        # obj.save()
        super().save_model(request, obj, form, change)
        # 调用delery异步生成静态文件方法
        generate_static_html.delay()
        # 后台修改完数据删除缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        """后台保存数据是使用"""
        # obj.delete()
        super().delete_model(request, obj)
        generate_static_html.delay()
        cache.delete('index_page_data')


class GoodsCategoryAdmin(BaseAdmin):
    pass


class GoodsSKUAdmin(BaseAdmin):
    pass


class GoodsSPUAdmin(BaseAdmin):
    pass


class IndexSlideGoodsAdmin(BaseAdmin):
    pass


class IndexPromotionAdmin(BaseAdmin):
    """商品活动站点管理"""
    pass

admin.site.register(GoodsCategory, GoodsCategoryAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(GoodsSPU, GoodsSPUAdmin)
admin.site.register(IndexSlideGoods, IndexSlideGoodsAdmin)
admin.site.register(IndexPromotion, IndexPromotionAdmin)
