import os
import time
import json
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import MassEstimationTask
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .services import run_ml_task_sync


@shared_task(bind=True)
def process_mass_estimation(self, task_id):
    """
    음식 질량 추정 작업을 처리하는 Celery 작업
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting mass estimation task: {task_id}")
        # 작업 조회
        task = MassEstimationTask.objects.get(task_id=task_id)
        
        # 웹소켓 채널 레이어 가져오기
        channel_layer = get_channel_layer()
        
        # 작업 시작 상태 업데이트
        task.status = 'processing'
        task.save()
        
        # 웹소켓으로 상태 전송
        logger.info(f"Sending processing start message for task: {task.task_id}")
        async_to_sync(channel_layer.group_send)(
            f"task_{task.task_id}",
            {
                "type": "task.update",
                "task_id": task.task_id,
                "data": {
                    "status": "processing",
                    "message": "작업이 시작되었습니다."
                }
            }
        )
        
        # 작업 진행 상황 시뮬레이션 (실제로는 ML 모델 호출)
        total_steps = 10
        for step in range(1, total_steps + 1):
            # 작업 진행률 계산
            progress = int((step / total_steps) * 100)
            
            # 진행 상황 업데이트
            task.progress = progress
            task.save()
            
            # 웹소켓으로 진행 상황 전송
            group_name = f"task_{task.task_id}"
            message_data = {
                "type": "task.update",
                "task_id": task.task_id,
                "data": {
                    "status": "processing",
                    "progress": progress / 100.0,  # 0-100을 0-1로 변환
                    "message": f"처리 중... ({progress}%)"
                }
            }
            logger.info(f"Sending progress update: {progress}% for task: {task.task_id}")
            logger.info(f"Group name: {group_name}")
            logger.info(f"Message data: {message_data}")
            async_to_sync(channel_layer.group_send)(group_name, message_data)
            
            # 작업 시뮬레이션 (실제로는 ML 모델 처리)
            time.sleep(1)
        
        # 작업 완료 처리
        task.status = 'completed'
        task.progress = 100
        task.result = {
            "estimated_mass": 250.5,
            "confidence": 0.85,
            "food_type": "밥",
            "unit": "g"
        }
        task.save()
        
        # 웹소켓으로 완료 상태 전송
        logger.info(f"Sending completion message for task: {task.task_id}")
        async_to_sync(channel_layer.group_send)(
            f"task_{task.task_id}",
            {
                "type": "task.completed",
                "task_id": task.task_id,
                "data": {
                    "status": "completed",
                    "progress": 1.0,  # 100%를 1.0으로 변환
                    "result": task.result,
                    "message": "작업이 완료되었습니다."
                }
            }
        )
        
        logger.info(f"Task {task_id} completed successfully")
        return f"Task {task_id} completed successfully"
        
    except MassEstimationTask.DoesNotExist:
        # 작업이 존재하지 않는 경우
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task_id}",
            {
                "type": "task.failed",
                "task_id": task_id,
                "data": {
                    "status": "failed",
                    "message": "작업을 찾을 수 없습니다."
                }
            }
        )
        raise Exception(f"Task {task_id} not found")
        
    except Exception as e:
        # 오류 발생 시
        task = MassEstimationTask.objects.get(task_id=task_id)
        task.status = 'failed'
        task.error = str(e)
        task.save()
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task.task_id}",
            {
                "type": "task.failed",
                "task_id": task.task_id,
                "data": {
                    "status": "failed",
                    "error": str(e),
                    "message": f"작업 처리 중 오류가 발생했습니다: {str(e)}"
                }
            }
        )
        raise


@shared_task(bind=True)
def process_image_upload(self, task_id):
    """
    이미지 업로드 후 ML 서버로 처리 작업
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        task = MassEstimationTask.objects.get(task_id=task_id)
        channel_layer = get_channel_layer()
        
        # 파일 존재 확인
        if not task.image_file:
            raise Exception("업로드된 이미지 파일이 없습니다.")
        
        # 파일 경로 확인
        image_path = None
        if task.image_file:
            try:
                image_path = default_storage.path(task.image_file.name)
            except Exception as e:
                logger.error(f"default_storage.path 변환 오류: {e}")
                image_path = None
        if not image_path or not os.path.exists(image_path):
            raise Exception("이미지 파일 경로가 올바르지 않거나 파일이 존재하지 않습니다.")
        # 작업 시작
        task.status = 'processing'
        task.save()
        
        # Django WebSocket으로 시작 메시지 전송
        async_to_sync(channel_layer.group_send)(
            f"task_{task.task_id}",
            {
                "type": "task.update",
                "task_id": task.task_id,
                "data": {
                    "status": "processing",
                    "progress": 0.0,
                    "message": "ML 서버에 이미지 전송 중..."
                }
            }
        )
        
        # ML 서버 API 호출 및 WebSocket 연동
        logger.info(f"ML 서버 작업 시작: {task.task_id}")
        logger.info(f"이미지 파일명: {task.image_file.name}")
        logger.info(f"이미지 파일 경로: {image_path}")
        
        # ML 서버 작업 실행
        result = run_ml_task_sync(task.task_id, image_path)
        
        if result["success"]:
            # ML 서버 작업이 성공적으로 완료됨
            # (결과는 WebSocket을 통해 이미 전송됨)
            logger.info(f"ML 서버 작업 완료: {task.task_id}")
            
            # 작업 상태 업데이트
            task.status = 'completed'
            task.progress = 100
            task.save()
            
            return f"ML 서버 작업 완료: {task_id}"
        else:
            # ML 서버 작업 실패
            error_msg = result.get("error", "알 수 없는 오류")
            logger.error(f"ML 서버 작업 실패: {error_msg}")
            
            task.status = 'failed'
            task.error = error_msg
            task.save()
            
            # 실패 메시지 전송
            async_to_sync(channel_layer.group_send)(
                f"task_{task.task_id}",
                {
                    "type": "task.failed",
                    "task_id": task.task_id,
                    "data": {
                        "status": "failed",
                        "error": error_msg,
                        "message": f"ML 서버 처리 실패: {error_msg}"
                    }
                }
            )
            
            raise Exception(f"ML 서버 작업 실패: {error_msg}")
        
    except Exception as e:
        logger.error(f"process_image_upload 오류: {str(e)}")
        
        # 작업 상태 업데이트
        task = MassEstimationTask.objects.get(task_id=task_id)
        task.status = 'failed'
        task.error = str(e)
        task.save()
        
        # 에러 메시지 전송
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"task_{task.task_id}",
            {
                "type": "task.failed",
                "task_id": task.task_id,
                "data": {
                    "status": "failed",
                    "error": str(e),
                    "message": f"이미지 처리 중 오류가 발생했습니다: {str(e)}"
                }
            }
        )
        raise 