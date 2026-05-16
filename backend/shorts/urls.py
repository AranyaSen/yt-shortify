from django.urls import path

from shorts.views import (
    CleanupView,
    ContinueView,
    DownloadView,
    GenerateView,
    StatusView,
)

urlpatterns = [
    path('generate/', GenerateView.as_view(), name='generate'),
    path('continue/<str:job_id>/', ContinueView.as_view(), name='continue'),
    path('status/<str:job_id>/', StatusView.as_view(), name='status'),
    path(
        'download/<str:job_id>/<str:short_id>/',
        DownloadView.as_view(),
        name='download',
    ),
    path('cleanup/<str:job_id>/', CleanupView.as_view(), name='cleanup'),
]
