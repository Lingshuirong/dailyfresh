from django.contrib.auth.decorators import login_required
from django.views.generic.base import View


class LoginRequiredMixin(object):
    """检测用户是否已经登陆"""

    @classmethod
    def as_view(cls, **initkwargs):
        view_fun = super().as_view(**initkwargs)
        view_fun = login_required(view_fun)
        return view_fun


