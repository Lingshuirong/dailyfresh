from haystack import indexes

from apps.goods.models import GoodsSKU


class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    """模型索引类：针对那张表的那些数据创建索引"""
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        """商品sku模型类，对应商品sku表"""
        return GoodsSKU

    def index_queryset(self, using=None):
        """要对表中那些数据创建所以"""
        return self.get_model().objects.all()
