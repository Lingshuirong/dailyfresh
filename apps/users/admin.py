from django.contrib import admin

# Register your models here.
from apps.users.models import TestModel, TestModelHtml

admin.site.register(TestModel)
admin.site.register(TestModelHtml)
