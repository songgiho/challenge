from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from .models import MassEstimationTask
from .services import MLServerService
from .tasks import process_mass_estimation
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def estimate_async(request):
    """
    비동기 질량 추정 API
    이미지를 업로드하고 비동기로 질량을 추정합니다.
    """
    try:
        # 이미지 파일 검증
        if 'file' not in request.FILES:
            return Response({
                'error': '이미지 파일이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['file']
        
        # 파일 형식 검증
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response({
                'error': '지원하지 않는 이미지 형식입니다. JPEG, PNG, WebP만 지원합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 파일 크기 검증 (10MB 제한)
        if image_file.size > 10 * 1024 * 1024:
            return Response({
                'error': '이미지 파일 크기가 너무 큽니다. 10MB 이하로 업로드해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 작업 생성
        task = MassEstimationTask.objects.create(
            image=image_file,
            status='pending',
            message='이미지 업로드 완료. 질량 추정을 시작합니다.'
        )
        
        # Celery 작업 시작
        process_mass_estimation.delay(str(task.task_id))
        
        return Response({
            'task_id': str(task.task_id),
            'status': 'pending',
            'message': f'질량 추정 작업이 시작되었습니다. /api/v1/task/{task.task_id}로 상태를 확인하세요.'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"비동기 질량 추정 API 오류: {e}")
        return Response({
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def estimate(request):
    """
    동기 질량 추정 API
    이미지를 업로드하고 즉시 질량을 추정합니다.
    """
    try:
        # 이미지 파일 검증
        if 'file' not in request.FILES:
            return Response({
                'error': '이미지 파일이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['file']
        
        # 파일 형식 검증
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response({
                'error': '지원하지 않는 이미지 형식입니다. JPEG, PNG, WebP만 지원합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 파일 크기 검증 (10MB 제한)
        if image_file.size > 10 * 1024 * 1024:
            return Response({
                'error': '이미지 파일 크기가 너무 큽니다. 10MB 이하로 업로드해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 작업 생성
        task = MassEstimationTask.objects.create(
            image=image_file,
            status='processing',
            message='이미지를 분석하는 중...'
        )
        
        try:
            # ML 서버 서비스 초기화
            ml_service = MLServerService()
            
            # ML 서버에 이미지 전송
            ml_response = ml_service.estimate_mass(task.image.path)
            
            # ML 응답을 표준 형식으로 변환
            formatted_result = ml_service.format_ml_response(ml_response)
            
            # 작업 완료 처리
            task.mark_completed(formatted_result)
            
            return Response({
                'task_id': str(task.task_id),
                'status': 'completed',
                'result': formatted_result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # 작업 실패 처리
            task.mark_failed(str(e))
            return Response({
                'error': f'질량 추정 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"동기 질량 추정 API 오류: {e}")
        return Response({
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_task_status(request, task_id):
    """
    작업 상태 조회 API
    """
    try:
        task = get_object_or_404(MassEstimationTask, task_id=task_id)
        
        response_data = {
            'task_id': str(task.task_id),
            'status': task.status,
            'progress': task.progress,
            'message': task.message,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
        }
        
        if task.completed_at:
            response_data['completed_at'] = task.completed_at.isoformat()
        
        if task.status == 'completed' and task.result_data:
            response_data['result'] = task.result_data
        
        if task.status == 'failed' and task.error:
            response_data['error'] = task.error
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except MassEstimationTask.DoesNotExist:
        return Response({
            'error': '작업을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"작업 상태 조회 API 오류: {e}")
        return Response({
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_task_list(request):
    """
    작업 목록 조회 API
    """
    try:
        tasks = MassEstimationTask.objects.all().order_by('-created_at')[:50]
        
        task_list = []
        for task in tasks:
            task_data = {
                'task_id': str(task.task_id),
                'status': task.status,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
            }
            
            if task.status == 'completed' and task.result_data:
                task_data['total_mass_g'] = task.result_data.get('mass_estimation', {}).get('total_mass_g', 0)
            
            task_list.append(task_data)
        
        return Response({
            'tasks': task_list,
            'count': len(task_list)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"작업 목록 조회 API 오류: {e}")
        return Response({
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 테스트용 업로드 폼 및 결과 디버그 뷰
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def test_upload(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('file'):
        image_file = request.FILES['file']
        context['debug'] = {
            'name': image_file.name,
            'content_type': image_file.content_type,
            'size': image_file.size,
            'type': str(type(image_file)),
        }
        try:
            ml_service = MLServerService()
            ml_response = ml_service.estimate_mass_async(image_file)
            context['result'] = ml_response
        except Exception as e:
            context['error'] = str(e)
    return render(request, 'mlserver/test_upload.html', context)
