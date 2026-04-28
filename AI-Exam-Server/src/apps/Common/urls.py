# @File    : urls.py
# @Describe: 公共Apps相关路由

from django.urls import path

from .views import DownloadFileView
from .views import DownloadResultFileView

urlpatterns = [
    path('download/<str:filename>', DownloadFileView.as_view(), name='download_file'),
    path('downloadResult/<str:filename>', DownloadResultFileView.as_view(), name='download_result_file'),
]


if __name__ == '__main__':
    pass
