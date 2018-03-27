from celery import Celery
from django.core.mail import send_mail

from dailyfresh import settings
#创建celery对象
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
