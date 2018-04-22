from django.contrib.auth.decorators import login_required
from django.views.generic.base import View
from django_redis import get_redis_connection


class LoginRequiredMixin(object):
    """检测用户是否已经登陆"""

    @classmethod
    def as_view(cls, **initkwargs):
        view_fun = super().as_view(**initkwargs)
        view_fun = login_required(view_fun)
        return view_fun


class BaseCartView(View):

    def get_cart_count(self, request):
        """获取购物车数量的方法"""
        cart_count = 0
        if request.user.is_authenticated():
            strict_redis = get_redis_connection()
            key = 'cart_%s' % request.user.id
            vals = strict_redis.hvals(key)
            # 累加商品数量
            for count in vals:
                cart_count += int(count)
        return cart_count



