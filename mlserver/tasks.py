from celery import shared_task
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging
from .models import MassEstimationTask
from .services import MLServerService

logger = logging.getLogger(__name__)


@shared_task
def process_mass_estimation(task_id: str):
    """
    질량 추정 작업을 비동기로 처리
    
    Args:
        task_id: 작업 ID
    """
    try:
        # 작업 조회
        task = MassEstimationTask.objects.get(task_id=task_id)
        
        # 상태를 처리 중으로 변경
        task.status = 'processing'
        task.progress = 0.1
        task.message = "이미지를 ML 서버로 전송하는 중..."
        task.save()
        
        # WebSocket으로 진행 상황 전송
        send_task_update(task_id, {
            "status": "processing",
            "progress": 0.1,
            "message": "이미지를 ML 서버로 전송하는 중..."
        })
        
        # ML 서버 서비스 초기화
        ml_service = MLServerService()
        
        # 이미지 경로
        image_path = task.image.path
        
        # ML 서버에 이미지 전송 (동기 처리)
        logger.info(f"ML 서버에 이미지 전송 시작: {task_id}")
        
        # 진행 상황 업데이트
        task.progress = 0.3
        task.message = "AI 모델로 이미지를 분석하는 중..."
        task.save()
        
        send_task_update(task_id, {
            "status": "processing",
            "progress": 0.3,
            "message": "AI 모델로 이미지를 분석하는 중..."
        })
        
        # ML 서버 호출
        ml_response = ml_service.estimate_mass(image_path)
        
        # 진행 상황 업데이트
        task.progress = 0.8
        task.message = "결과를 처리하는 중..."
        task.save()
        
        send_task_update(task_id, {
            "status": "processing",
            "progress": 0.8,
            "message": "결과를 처리하는 중..."
        })
        
        # ML 응답을 표준 형식으로 변환
        formatted_result = ml_service.format_ml_response(ml_response)
        
        # 작업 완료 처리
        task.mark_completed(formatted_result)
        
        # WebSocket으로 완료 메시지 전송
        send_task_completed(task_id, formatted_result)
        
        logger.info(f"질량 추정 작업 완료: {task_id}")
        
    except MassEstimationTask.DoesNotExist:
        logger.error(f"작업을 찾을 수 없음: {task_id}")
        send_task_failed(task_id, "작업을 찾을 수 없습니다.")
        
    except Exception as e:
        logger.error(f"질량 추정 작업 실패: {task_id}, 오류: {e}")
        
        # 작업 실패 처리
        try:
            task = MassEstimationTask.objects.get(task_id=task_id)
            task.mark_failed(str(e))
        except:
            pass
        
        # WebSocket으로 실패 메시지 전송
        send_task_failed(task_id, str(e))


def send_task_update(task_id: str, data: dict):
    """WebSocket으로 작업 업데이트 전송"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task_id}",
            {
                "type": "task_update",
                "task_id": task_id,
                "data": data
            }
        )
    except Exception as e:
        logger.error(f"WebSocket 업데이트 전송 실패: {e}")


def send_task_completed(task_id: str, result: dict):
    """WebSocket으로 작업 완료 메시지 전송"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task_id}",
            {
                "type": "task_completed",
                "task_id": task_id,
                "data": {
                    "status": "completed",
                    "progress": 1.0,
                    "message": "작업이 완료되었습니다.",
                    "result": result
                }
            }
        )
    except Exception as e:
        logger.error(f"WebSocket 완료 메시지 전송 실패: {e}")


def send_task_failed(task_id: str, error: str):
    """WebSocket으로 작업 실패 메시지 전송"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task_id}",
            {
                "type": "task_failed",
                "task_id": task_id,
                "data": {
                    "status": "failed",
                    "error": error
                }
            }
        )
    except Exception as e:
        logger.error(f"WebSocket 실패 메시지 전송 실패: {e}") 