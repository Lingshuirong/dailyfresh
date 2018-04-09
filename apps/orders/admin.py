from django.contrib import admin

# Register your models here.
from apps.orders.models import OrderGoods, OrderInfo

admin.site.register(OrderGoods)
admin.site.register(OrderInfo)