from django.db import models
import uuid
from django.utils import timezone


class MassEstimationTask(models.Model):
    """질량 추정 작업 모델"""
    
    STATUS_CHOICES = [
        ('pending', '대기 중'),
        ('processing', '처리 중'),
        ('completed', '완료'),
        ('failed', '실패'),
    ]
    
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ImageField(upload_to='uploads/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.FloatField(default=0.0)
    message = models.TextField(blank=True)
    error = models.TextField(blank=True)
    
    # 결과 데이터 (JSON 형태로 저장)
    result_data = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'mass_estimation_tasks'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Task {self.task_id} - {self.status}"
    
    def mark_completed(self, result_data=None):
        """작업 완료 처리"""
        self.status = 'completed'
        self.progress = 1.0
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        self.save()
    
    def mark_failed(self, error_message):
        """작업 실패 처리"""
        self.status = 'failed'
        self.error = error_message
        self.save()
    
    def update_progress(self, progress, message=""):
        """진행 상황 업데이트"""
        self.progress = progress
        if message:
            self.message = message
        self.save()


class FoodItem(models.Model):
    """음식 아이템 모델"""
    
    task = models.ForeignKey(MassEstimationTask, on_delete=models.CASCADE, related_name='foods')
    food_name = models.CharField(max_length=100)
    estimated_mass_g = models.FloatField()
    confidence = models.FloatField()
    verification_method = models.CharField(max_length=50)
    reasoning = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'food_items'
    
    def __str__(self):
        return f"{self.food_name} - {self.estimated_mass_g}g"
