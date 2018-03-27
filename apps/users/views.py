import re

from celery.app.base import Celery
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.signing import SignatureExpired
from django.core.urlresolvers import reverse
from  itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.db.backends.mysql.base import IntegrityError
from django.db.utils import IntegrityError
from django.shortcuts import render, redirect
from django.http.response import HttpResponse, HttpResponseRedirect

# Create your views here.
from django.views.generic.base import View

from apps.users.models import User, Address
from celery_task.tasks import send_active_mail
from dailyfresh import settings
from utils.common import LoginRequiredMixin


class RegisterView(View):
    def get(self, request):
        """显示注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """提交注册信息"""
        # 获取用户提交的注册信息
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 判断注册的信息是否合法
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '您输入的信息不能为空！'})

        # 判断密码是否用一致
        if password != password2:
            return render(request, 'register.html', {'errmsg': '两次输入的密码不一致！'})
        # 判断邮箱是否合法
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '您的邮箱不合法！'})

        # 判断是否勾选同意协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意用户协议!'})

        # 判断用户名是否重复,保存用户到数据库表中
        try:
            user = User.objects.create_user(username, email, password)
        except IntegrityError:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 处理用户激活状态
        user.is_active = False
        user.save()

        # 发送激活邮件到用户邮箱
        user_id = user.id
        print(user_id)
        # 用itstandgerous生成激活token
        s = Serializer(settings.SECRET_KEY, 3600)
        token = s.dumps({'confirm': user_id})
        token = token.decode()

        # 方式一 使用Django发送邮件
        # self.send_active_mail(username, email, token)

        # 方式二 使用celery异步多任务队列
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

        # 调用django的send_mail发送邮件

        send_mail(subject, message, from_email, recipient_list, html_message=html_message)


class ActiveView(View):
    """执行激活操作"""

    def get(self, request, token):
        print(token)

        try:
            s = Serializer(settings.SECRET_KEY, 3600)
            # 解密获取用户id
            my_dict = s.loads(token)

            user_id = my_dict.get('confirm')
            print(user_id)

        except SignatureExpired:
            return HttpResponse('Url已经过期')

        # 修改为激活状态
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
        print(username)
        password = request.POST.get('password')

        # 判断用户信息是否为空
        # if not all([username, password]):
        #     return render(request, 'login.html', {'errmsg': '用户名或者密码为空'})
        #
        # # 判断用户名是否存在,返回一个用户对象
        #
        # , password=password)
        # if user is None:
        #     return render(request, 'login.html', {'errmsg': '用户不能存在'})
        #
        # # 判断用户是否激活
        # if user.is_active == 0:
        #     return render(request, 'login.html', {'errmsg': '用户还未激活，是否前往邮箱激活'})
        #
        # login(request, user)


        # 校验参数合法性
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '请求参数不完整'})

        # 通过 django 提供的authenticate方法，
        # 验证用户名和密码是否正确
        user = authenticate(username=username, password=password)
        print(user)

        # 用户名或密码不正确
        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码不正确'})

        if not user.is_active:  # 注册账号未激活
            # 用户未激活
            return render(request, 'login.html', {'errmsg': '请先激活账号'})

        # 通过django的login方法，保存登录用户状态（使用session）
        login(request, user)

        """获取next参数"""
        next1 = request.GET.get('next')
        if next1 is None:
            return redirect(reverse('goods:index'))
        else:
            return redirect(next1)

        # 响应请求，返回html界面 (进入首页)

        return redirect(reverse('goods:index'))

class LogoutView(View):
    """退出登录"""
    def get(self, request):
        """退出登录处理逻辑"""
        #由Django的认证系统完成，会清理cookie和session，request中包括了user对象
        logout(request)

        return redirect(reverse('goods:index'))



# 用户地址
class UserAddressView(LoginRequiredMixin, View):
    """检测用户是否登陆"""

    def get(self, request):

        user = request.user
        try:
            address = user.address_set.latest('create_time')
            print(111)
            print(address.receiver_name)
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
        # 当前登录用户
        user = request.user

        # 判断合法性
        if not all([reciver, address]):
            return render(request, 'user_center_site.html', \
                          {'errmsg': '接收人或者地址不能为空'})

        # 新增地址
        Address.objects.create(
            receiver_name=reciver,
            detail_addr=address,
            zip_code=zip_code,
            receiver_mobile=mobile,
            user=user
        )

        return redirect(reverse('users:address'))


# 用户信息
class UserInforView(LoginRequiredMixin, View):
    """查看用户信息"""

    def get(self, request):
        user = request.user

        # 获取地址对象
        address = user.address_set.latest('create_time')
        data = {
            'which_page': 1,
            'address': address,
        }

        return render(request, 'user_center_info.html', data)


# 用户订单
class UserOrderView(LoginRequiredMixin, View):
    pass
