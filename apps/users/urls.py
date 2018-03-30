from django.conf.urls import include, url
from django.contrib import admin

from apps.users import views

urlpatterns = [
    url(r'^register$', views.RegisterView.as_view(), name='register'),
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),
    url(r'^login$', views.LoginView.as_view(), name='login'),  # 登陆
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),  # 登出
    url(r'^address$', views.UserAddressView.as_view(), name='address'),
    url(r'^order$', views.UserOrderView.as_view(), name='order'),
    url(r'^', views.UserInforView.as_view(), name='info'),
]
