# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_auto_20180405_1419'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ordergoods',
            options={'verbose_name_plural': '订单信息', 'verbose_name': '订单信息'},
        ),
        migrations.AlterModelOptions(
            name='orderinfo',
            options={'verbose_name_plural': '订单信息', 'verbose_name': '订单信息'},
        ),
    ]
