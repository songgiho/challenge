from django.urls import path
from . import views

app_name = 'mlserver'

urlpatterns = [
    path('test-websocket/', views.test_websocket, name='test_websocket'),
    path('test-task/', views.test_task, name='test_task'),
    path('test-upload/', views.test_upload, name='test_upload'),
    path('test-celery/', views.test_celery, name='test_celery'),
    path('api/upload/', views.upload_image, name='upload_image'),
    path('api/tasks/', views.MassEstimationTaskViewSet.as_view(), name='task-list'),
    path('api/tasks/<str:task_id>/', views.MassEstimationTaskViewSet.as_view(), name='task-detail'),
    path('api/tasks/<str:task_id>/update/', views.MassEstimationTaskUpdateView.as_view(), name='task-update'),
    path('api/test/create-task/', views.create_test_task, name='create-test-task'),
    path('api/test/update-task/<str:task_id>/', views.update_test_task, name='update-test-task'),
] 