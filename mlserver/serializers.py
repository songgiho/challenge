from rest_framework import serializers
from .models import MassEstimationTask

class MassEstimationTaskSerializer(serializers.ModelSerializer):
    """음식 질량 추정 작업 시리얼라이저"""
    
    class Meta:
        model = MassEstimationTask
        fields = [
            'task_id', 'status', 'progress', 'message', 'error',
            'created_at', 'updated_at', 'estimated_mass', 'confidence_score',
            'result_data', 'original_filename'
        ]
        read_only_fields = [
            'task_id', 'status', 'progress', 'message', 'error',
            'created_at', 'updated_at', 'estimated_mass', 'confidence_score',
            'result_data'
        ]

class MassEstimationTaskCreateSerializer(serializers.ModelSerializer):
    """음식 질량 추정 작업 생성 시리얼라이저"""
    
    class Meta:
        model = MassEstimationTask
        fields = ['image_file', 'original_filename']
    
    def create(self, validated_data):
        # 작업 생성 시 자동으로 task_id 생성
        task = MassEstimationTask.objects.create(**validated_data)
        return task

class MassEstimationTaskUpdateSerializer(serializers.ModelSerializer):
    """음식 질량 추정 작업 업데이트 시리얼라이저"""
    
    class Meta:
        model = MassEstimationTask
        fields = ['status', 'progress', 'message', 'error', 'result_data', 'estimated_mass', 'confidence_score', 'ml_task_id'] 