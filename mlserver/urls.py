from django.urls import path
from . import views

app_name = 'mlserver'

urlpatterns = [
    # 비동기 질량 추정 API
    path('estimate_async/', views.estimate_async, name='estimate_async'),
    
    # 동기 질량 추정 API
    path('estimate/', views.estimate, name='estimate'),
    
    # 작업 상태 조회 API
    path('task/<uuid:task_id>/', views.get_task_status, name='get_task_status'),
    
    # 작업 목록 조회 API
    path('tasks/', views.get_task_list, name='get_task_list'),
    # 테스트 업로드 폼
    path('test-upload/', views.test_upload, name='test_upload'),
] 