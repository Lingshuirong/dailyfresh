# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20180324_1123'),
    ]

    operations = [
        migrations.DeleteModel(
            name='TestModel',
        ),
        migrations.DeleteModel(
            name='TestModelHtml',
        ),
    ]
