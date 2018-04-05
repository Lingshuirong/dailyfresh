
from django.conf.urls import include, url
from django.contrib import admin

from apps.orders import views

urlpatterns = [
    url(r'^place$', views.PlaceOrderView.as_view(), name='place'),
    url(r'^commit$', views.CommitOrderView.as_view(), name='commit'),
    url(r'^pay$', views.OrderPayView.as_view(), name='pay'),
    url(r'^check$', views.CheckPayView.as_view(), name='check'),
]
