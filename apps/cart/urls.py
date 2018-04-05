
from django.conf.urls import include, url
from django.contrib import admin

from apps.cart import views

urlpatterns = [
    url(r'^add$', views.CartAddVies.as_view(), name='add'),
    url(r'^$', views.CartInfoView.as_view(), name='info'),
    url(r'^update$', views.CartUpdateView.as_view(), name='update'),
    url(r'^delete$', views.CartDeleteView.as_view(), name='delete'),



]
