from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.generic.base import View

# Create your views here.
class IndexView(View):
    """首页"""

    def get(self, request):
        """进入首页"""

        return render(request, 'index.html')