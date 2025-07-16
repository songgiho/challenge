from django.urls import path
from . import views

app_name = 'mlserver'

urlpatterns = [
    path('test-websocket/', views.test_websocket, name='test_websocket'),
] 