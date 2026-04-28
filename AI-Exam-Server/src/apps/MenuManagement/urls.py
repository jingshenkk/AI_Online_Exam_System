# @File    : urls.py
# @Describe: Menu应用URL

from django.urls import path

from .views import MenuBaseView

urlpatterns = [
    path('menu', MenuBaseView.as_view(), name='MenuOpts'),
]