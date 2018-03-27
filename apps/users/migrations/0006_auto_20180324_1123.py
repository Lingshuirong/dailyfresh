# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20180324_1119'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestModelHtml',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('comment', tinymce.models.HTMLField(verbose_name='商品描述', blank=True, default='')),
            ],
        ),
        migrations.AlterModelOptions(
            name='testmodel',
            options={'verbose_name': '测试模型', 'verbose_name_plural': '测试模型'},
        ),
    ]
