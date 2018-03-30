# import os
# import django
#配置
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
#初始化
# django.setup()


from celery import Celery
from django.core.mail import send_mail
from django.shortcuts import render
from django.template import loader

from apps.goods.models import GoodsCategory, IndexSlideGoods, IndexPromotion, IndexCategoryGoods
from dailyfresh import settings

# 创建celery对象
app = Celery('dailyfresh', broker='redis://127.0.0.1:6379/1')


@app.task
def send_active_mail(username, email, token):
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


@app.task
def generate_static_html():
    """进入首页"""

    # 查询商品列别数据
    categories = GoodsCategory.objects.all()

    # 查询商品轮播数据
    slide_skus = IndexSlideGoods.objects.all().order_by('index')

    # 查询商品促销活动数据
    promotions = IndexPromotion.objects.all().order_by('index')

    # 查询类别商品数据
    for category in categories:
        # 查询某一类别下的文字类别商品
        text_skus = IndexCategoryGoods.objects.filter(
            category=category, display_type=0).order_by('index')

        # 查询某一类别下图片类别商品
        img_skus = IndexCategoryGoods.objects.filter(category=category, display_type=1) \
            .order_by('index')

        # 动态地给类别新增实例属性
        category.text_skus = text_skus
        category.img_skus = img_skus

    # 查询购物车中商品数量
    cart_count = 0

    context = {
        'catogories': categories,
        'slide_skus': slide_skus,
        'promotions': promotions,
        'cart_count': cart_count,
    }

    # 获取模板文件
    template = loader.get_template('index.html')

    # 渲染生成html页面
    html_str = template.render(context)

    # 生成一个叫index.html的文件，放在桌面的static目录下
    file_path = '/home/python/Desktop/static/index.html'
    with open(file_path, 'w') as file:
        file.write(html_str)

