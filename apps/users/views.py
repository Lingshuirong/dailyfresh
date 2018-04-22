import re

from celery.app.base import Celery
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage
from django.core.signing import SignatureExpired
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from  itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.db.backends.mysql.base import IntegrityError
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect
from django.http.response import HttpResponse, HttpResponseRedirect
from django.contrib.auth.views import PasswordResetForm
# Create your views here.
from django.views.generic.base import View

from apps.goods.models import GoodsSKU
from apps.orders.models import OrderInfo, OrderGoods
from apps.users.models import User, Address
from celery_task.tasks import send_active_mail, send_change_password
from dailyfresh import settings
from utils.common import LoginRequiredMixin


class RegisterView(View):
    def get(self, request):
        """显示注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """提交注册信息"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '您输入的信息不能为空！'})
        if password != password2:
            return render(request, 'register.html', {'errmsg': '两次输入的密码不一致！'})
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '您的邮箱不合法！'})
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意用户协议!'})
        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        user.is_active = False
        user.save()
        user_id = user.id
        # 用itstandgerous生成激活token
        s = Serializer(settings.SECRET_KEY, 3600)
        token = s.dumps({'confirm': user_id})
        token = token.decode()
        send_active_mail.delay(username, email, token)
        return redirect(reverse('users:login'))

    def send_active_mail(self, username, email, token):
        """
        发送激活邮件
        :param username: 注册的用户
        :param email:  注册用户的邮箱
        :param token: 对字典 {'confirm':用户id} 加密后的结果
        :return:
        """

        subject = '天天生鲜注册激活'
        message = ''
        from_email = settings.EMAIL_FROM
        recipient_list = [email]
        html_message = '<h3>尊敬的%(name)s:</h3> 欢迎注册天天生鲜' \
                       '请点击以下链接激活您的账号：</br>' \
                       '<a href="http://127.0.0.1:8000/users/active/%(token)s"> \
                       http://127.0.0.1:8000/users/active/%(token)s</a>' \
                       % {'name': username, 'token': token}

        send_mail(subject, message, from_email, recipient_list, html_message=html_message)


class ActiveView(View):
    """执行激活操作"""

    def get(self, request, token):
        try:
            s = Serializer(settings.SECRET_KEY, 3600)
            my_dict = s.loads(token)
            user_id = my_dict.get('confirm')
        except SignatureExpired:
            return HttpResponse('Url已经过期')
        user = User.objects.get(id=user_id)
        user.is_active = 1
        user.save()
        return redirect(reverse('users:login'))


class LoginView(View):
    """进入登陆页面"""

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """提交用户登陆信息"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '请求参数不完整'})
        if remember != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码不正确'})
        if not user.is_active:
            return render(request, 'login.html', {'errmsg': '请先激活账号'})
        login(request, user)
        next1 = request.GET.get('next')
        if next1 is None:
            return redirect(reverse('goods:index'))
        else:
            return redirect(next1)
        return redirect(reverse('goods:index'))


class LogoutView(View):
    """退出登录"""

    def get(self, request):
        """退出登录处理逻辑"""
        # 由Django的认证系统完成，会清理cookie和session，request中包括了user对象
        logout(request)

        return redirect(reverse('goods:index'))


# 用户地址
class UserAddressView(LoginRequiredMixin, View):
    """检测用户是否登陆"""

    def get(self, request):
        user = request.user
        try:
            address = user.address_set.latest('create_time')
        except Exception:
            address = None
        data = {
            'address': address,
            'which_page': 3,
        }
        return render(request, 'user_center_site.html', data)

    def post(self, request):
        """新增用户地址"""
        reciver = request.POST.get('reciver')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        mobile = request.POST.get('mobile')
        user = request.user
        if not all([reciver, address]):
            return render(request, 'user_center_site.html', \
                          {'errmsg': '接收人或者地址不能为空'})
        Address.objects.create(
            receiver_name=reciver,
            detail_addr=address,
            zip_code=zip_code,
            receiver_mobile=mobile,
            user=user
        )
        return redirect(reverse('users:address'))


class UserInforView(LoginRequiredMixin, View):
    """查看用户信息"""

    def get(self, request):
        user = request.user

        # 获取地址对象
        try:
            address = user.address_set.latest('create_time')
        except Exception:
            address = None

        # 从redis数据库中查询出用户浏览过的商品记录
        strict_redis = get_redis_connection('default')
        key = 'history_%s' % request.user.id

        # 查看最多五条记录
        goods_ids = strict_redis.lrange(key, 0, 4)
        print(goods_ids)

        # 保证数据库查询后，顺序不变
        skus = []
        for id in goods_ids:
            try:
                sku = GoodsSKU.objects.get(id=id)
                skus.append(sku)
            except GoodsSKU.DoesNotExist:
                pass

        data = {
            'which_page': 0,
            'address': address,
            'skus': skus,
        }

        return render(request, 'user_center_info.html', data)


class UserOrderView(LoginRequiredMixin, View):
    def get(self, request, page):
        user = request.user
        orders = OrderInfo.objects.filter(
            user=user).order_by('-create_time')

        for order in orders:
            order_skus = OrderGoods.objects.filter(order=order)
            order_desc = OrderInfo.ORDER_STATUS.get(order.status)
            total_amount = 0

            for sku in order_skus:
                sku_amount = sku.price * sku.count
                sku.sku_amount = sku_amount
                total_amount += sku_amount

            order.skus = order_skus
            order.order_desc = order_desc
            order.total_pay = total_amount + order.trans_cost

        # 创建分页
        paginator = Paginator(orders, 2)
        # Page对象
        try:
            page = paginator.page(page)
        except EmptyPage:
            page = paginator.page(1)
        page_list = paginator.page_range
        data = {
            'which_page': 1,
            'page': page,
            'page_list': page_list,
        }
        return render(request, 'user_center_order.html', data)


# 找回密码
class RePassword(View):
    def get(self, request):
        """重设用户密码"""
        return render(request, 're_password.html')


# 处理密码重设
class Rec(View):
    """重设密码"""

    def post(self, request):
        """接收邮箱"""
        email = request.POST.get('email')
        username = request.POST.get('username')
        user = User.objects.get(username=username)
        user_id = user.id
        # 用itstandgerous生成激活token
        s = Serializer(settings.SECRET_KEY, 3600)
        token = s.dumps({'confirm': user_id})
        token = token.decode()
        send_change_password.delay(username, email, token)
        return redirect(reverse('users:login'))


# 更改密码
class Change(View):
    def get(self, request, token):
        """重设密码"""
        data = {
            'token': token
        }
        return render(request, 'reset_password.html', data)

    def post(self, request, token):

        # 获取用户输入的密码和确认密码
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        try:
            s = Serializer(settings.SECRET_KEY, 3600)
            # 解密获取用户id
            my_dict = s.loads(token)
            user_id = my_dict.get('confirm')
        except SignatureExpired:
            return HttpResponse('Url已经过期')
        user = User.objects.get(id=user_id)
        if password == password2:
            user.password = make_password(password)
            user.save()
        return redirect(reverse('users:login'))

