# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_testmodel'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestModelHtml',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('desc', tinymce.models.HTMLField(null=True, verbose_name='商品描述')),
            ],
        ),
    ]
