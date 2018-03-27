# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_testmodelhtml'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TestModelHtml',
        ),
        migrations.AlterModelOptions(
            name='testmodel',
            options={},
        ),
        migrations.AlterField(
            model_name='testmodel',
            name='status',
            field=models.SmallIntegerField(choices=[(1, '已支付'), (2, '未支付'), (3, '已收货'), (4, '未评价'), (5, '已完成')], verbose_name='订单状态', default=1),
        ),
        migrations.AlterModelTable(
            name='testmodel',
            table=None,
        ),
    ]
