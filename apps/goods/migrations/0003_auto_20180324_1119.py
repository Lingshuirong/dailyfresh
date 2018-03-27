# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0002_auto_20180324_0825'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodsspu',
            name='desc',
            field=models.TextField(blank=True, verbose_name='商品描述', default=''),
        ),
    ]
