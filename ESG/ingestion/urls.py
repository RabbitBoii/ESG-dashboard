from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.UploadView.as_view()),
    path('batches/', views.BatchListView.as_view()),
    path('batches/<uuid:batch_id>/', views.BatchDetailView.as_view()),
]