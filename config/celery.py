import os
from celery import Celery

# Django 설정 모듈을 Celery의 기본 설정으로 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Django 설정에서 Celery 설정을 로드
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱에서 작업을 자동으로 발견
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 