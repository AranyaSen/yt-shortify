from django.urls import path

from shorts.views import (
    CleanupView,
    ContinueView,
    DownloadView,
    GenerateView,
    RenderCompleteView,
    SegmentView,
    SourceView,
    StatusView,
)

urlpatterns = [
    path('generate/', GenerateView.as_view(), name='generate'),
    path('continue/<str:job_id>/', ContinueView.as_view(), name='continue'),
    path('status/<str:job_id>/', StatusView.as_view(), name='status'),
    path('source/<str:job_id>/', SourceView.as_view(), name='source'),
    path(
        'segment/<str:job_id>/<str:short_id>/',
        SegmentView.as_view(),
        name='segment',
    ),
    path(
        'render-complete/<str:job_id>/',
        RenderCompleteView.as_view(),
        name='render-complete',
    ),
    path(
        'download/<str:job_id>/<str:short_id>/',
        DownloadView.as_view(),
        name='download',
    ),
    path('cleanup/<str:job_id>/', CleanupView.as_view(), name='cleanup'),
]
