from django.urls import path
from . import views

urlpatterns = [
    path('records/', views.RecordListView.as_view()),
    path('records/<uuid:record_id>/', views.RecordDetailView.as_view()),
    path('records/<uuid:record_id>/review/', views.ReviewRecordView.as_view()),
    path('factors/', views.EmissionFactorListView.as_view()),
]