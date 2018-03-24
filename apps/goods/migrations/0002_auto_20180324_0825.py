# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='goodsspu',
            name='desc',
            field=tinymce.models.HTMLField(verbose_name='商品描述', blank=True, default=''),
        ),
    ]
