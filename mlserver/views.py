from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import MassEstimationTask
from .serializers import (
    MassEstimationTaskSerializer, 
    MassEstimationTaskCreateSerializer,
    MassEstimationTaskUpdateSerializer
)
from .tasks import process_mass_estimation, process_image_upload
import json


# Create your views here.

def test_websocket(request):
    """웹소켓 테스트 페이지"""
    return render(request, 'mlserver/test_websocket.html')

def test_task(request):
    """음식 질량 추정 작업 테스트 페이지"""
    return render(request, 'mlserver/test_task.html')

def test_upload(request):
    """파일 업로드 테스트 페이지"""
    return render(request, 'mlserver/test_upload.html')

def test_celery(request):
    """Celery 작업 테스트 페이지"""
    return render(request, 'mlserver/test_celery.html')

class MassEstimationTaskViewSet(APIView):
    """음식 질량 추정 작업 API 뷰셋"""
    permission_classes = [AllowAny]
    
    def get(self, request, task_id=None):
        """작업 조회"""
        if task_id:
            # 특정 작업 조회
            try:
                task = MassEstimationTask.objects.get(task_id=task_id)
                serializer = MassEstimationTaskSerializer(task)
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            except MassEstimationTask.DoesNotExist:
                return Response({
                    'success': False,
                    'error': '작업을 찾을 수 없습니다.'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # 모든 작업 조회
            tasks = MassEstimationTask.objects.all().order_by('-created_at')[:10]
            serializer = MassEstimationTaskSerializer(tasks, many=True)
            return Response({
                'success': True,
                'data': serializer.data
            })
    
    def post(self, request):
        """새로운 작업 생성"""
        serializer = MassEstimationTaskCreateSerializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save()
            
            # 작업 생성 후 상태를 'processing'으로 변경
            task.status = 'processing'
            task.message = '이미지 분석을 시작합니다...'
            task.save()
            
            # 웹소켓을 통해 상태 업데이트 전송
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'task_{task.task_id}',
                {
                    'type': 'task_update',
                    'task_id': task.task_id,
                    'data': {
                        'status': task.status,
                        'progress': task.progress,
                        'message': task.message
                    }
                }
            )
            
            return Response({
                'success': True,
                'data': {
                    'task_id': task.task_id,
                    'status': task.status,
                    'message': '작업이 생성되었습니다.'
                }
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class MassEstimationTaskUpdateView(APIView):
    """음식 질량 추정 작업 업데이트 API"""
    permission_classes = [AllowAny]
    
    def put(self, request, task_id):
        """작업 상태 업데이트"""
        try:
            task = MassEstimationTask.objects.get(task_id=task_id)
            serializer = MassEstimationTaskUpdateSerializer(task, data=request.data, partial=True)
            
            if serializer.is_valid():
                task = serializer.save()
                
                # 웹소켓을 통해 상태 업데이트 전송
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                
                if task.status == 'completed':
                    async_to_sync(channel_layer.group_send)(
                        f'task_{task.task_id}',
                        {
                            'type': 'task_completed',
                            'task_id': task.task_id,
                            'data': {
                                'status': 'completed',
                                'progress': 1.0,
                                'message': '작업이 완료되었습니다.',
                                'result': task.result_data,
                                'estimated_mass': task.estimated_mass,
                                'confidence_score': task.confidence_score
                            }
                        }
                    )
                elif task.status == 'failed':
                    async_to_sync(channel_layer.group_send)(
                        f'task_{task.task_id}',
                        {
                            'type': 'task_failed',
                            'task_id': task.task_id,
                            'data': {
                                'status': 'failed',
                                'error': task.error
                            }
                        }
                    )
                else:
                    async_to_sync(channel_layer.group_send)(
                        f'task_{task.task_id}',
                        {
                            'type': 'task_update',
                            'task_id': task.task_id,
                            'data': {
                                'status': task.status,
                                'progress': task.progress,
                                'message': task.message
                            }
                        }
                    )
                
                return Response({
                    'success': True,
                    'data': MassEstimationTaskSerializer(task).data
                })
            else:
                return Response({
                    'success': False,
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except MassEstimationTask.DoesNotExist:
            return Response({
                'success': False,
                'error': '작업을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def create_test_task(request):
    """테스트용 작업 생성 API"""
    import uuid
    
    # 테스트용 작업 생성 (이미지 없이)
    task = MassEstimationTask.objects.create(
        task_id=str(uuid.uuid4()),
        status='pending',
        message='테스트 작업이 생성되었습니다.',
        original_filename='test.jpg'
    )
    
    # Celery 작업 시작
    process_mass_estimation.delay(task.task_id)
    
    return Response({
        'success': True,
        'data': {
            'task_id': task.task_id,
            'status': task.status,
            'message': '테스트 작업이 생성되었습니다.',
            'celery_task_started': True
        }
    }, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
@permission_classes([AllowAny])
def update_test_task(request, task_id):
    """테스트용 작업 업데이트 API"""
    try:
        task = MassEstimationTask.objects.get(task_id=task_id)
        
        # 요청 데이터에서 상태 업데이트
        new_status = request.data.get('status', task.status)
        new_progress = request.data.get('progress', task.progress)
        new_message = request.data.get('message', task.message)
        
        task.status = new_status
        task.progress = new_progress
        task.message = new_message
        
        # 완료 상태인 경우 결과 데이터 추가
        if new_status == 'completed':
            task.result_data = {
                'estimated_mass': 250.5,
                'confidence_score': 0.85,
                'food_type': '사과',
                'calories': 130
            }
            task.estimated_mass = 250.5
            task.confidence_score = 0.85
        
        task.save()
        
        # 웹소켓을 통해 상태 업데이트 전송
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        if task.status == 'completed':
            async_to_sync(channel_layer.group_send)(
                f'task_{task.task_id}',
                {
                    'type': 'task_completed',
                    'task_id': task.task_id,
                    'data': {
                        'status': 'completed',
                        'progress': 1.0,
                        'message': '작업이 완료되었습니다.',
                        'result': task.result_data,
                        'estimated_mass': task.estimated_mass,
                        'confidence_score': task.confidence_score
                    }
                }
            )
        else:
            async_to_sync(channel_layer.group_send)(
                f'task_{task.task_id}',
                {
                    'type': 'task_update',
                    'task_id': task.task_id,
                    'data': {
                        'status': task.status,
                        'progress': task.progress,
                        'message': task.message
                    }
                }
            )
        
        return Response({
            'success': True,
            'data': MassEstimationTaskSerializer(task).data
        })
        
    except MassEstimationTask.DoesNotExist:
        return Response({
            'success': False,
            'error': '작업을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
def upload_image(request):
    """이미지 파일 업로드 API"""
    try:
        # 파일 검증
        if 'image' not in request.FILES:
            return Response({
                'success': False,
                'error': '이미지 파일이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        
        # 파일 타입 검증
        if not image_file.content_type.startswith('image/'):
            return Response({
                'success': False,
                'error': '이미지 파일만 업로드 가능합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 파일 크기 검증 (10MB 제한)
        if image_file.size > 10 * 1024 * 1024:
            return Response({
                'success': False,
                'error': '파일 크기는 10MB 이하여야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 작업 생성
        import uuid
        task = MassEstimationTask.objects.create(
            task_id=str(uuid.uuid4()),
            image_file=image_file,
            original_filename=image_file.name,
            status='pending',
            message='이미지 업로드 완료. 분석을 시작합니다...'
        )
        
        # Celery 작업 시작
        process_image_upload.delay(task.task_id)
        
        # 웹소켓을 통해 상태 업데이트 전송
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'task_{task.task_id}',
            {
                'type': 'task_update',
                'task_id': task.task_id,
                'data': {
                    'status': task.status,
                    'progress': task.progress,
                    'message': task.message
                }
            }
        )
        
        return Response({
            'success': True,
            'data': {
                'task_id': task.task_id,
                'status': task.status,
                'message': '이미지 업로드가 완료되었습니다.',
                'filename': image_file.name,
                'file_size': image_file.size,
                'celery_task_started': True
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'업로드 중 오류가 발생했습니다: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
