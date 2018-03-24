# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建事件')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('delete', models.BooleanField(default=False, verbose_name='是否删除')),
                ('receiver_name', models.CharField(max_length=20, verbose_name='收件人')),
                ('receiver_mobile', models.CharField(max_length=11, verbose_name='联系电话')),
                ('detail_addr', models.CharField(max_length=256, verbose_name='详细地址')),
                ('zip_code', models.CharField(null=True, max_length=6, verbose_name='邮政编码')),
                ('is_default', models.BooleanField(default=False, verbose_name='默认地址')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, verbose_name='所属用户')),
            ],
            options={
                'db_table': 'df_address',
            },
        ),
    ]
