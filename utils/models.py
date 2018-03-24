from django.db import models


class BaseModel(models.Model):
    """模型类基类"""
    create_time = models.DateTimeField(auto_now_add=True,verbose_name='创建事件')
    update_time = models.DateTimeField(auto_now=True,verbose_name='更新时间')
    delete = models.BooleanField(default=False,verbose_name='是否删除')

    class Meta(object):
        abstract = True

