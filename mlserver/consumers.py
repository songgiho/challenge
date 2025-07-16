import json
import asyncio
import websockets
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MassEstimationTask
from django.conf import settings

logger = logging.getLogger(__name__)

class TaskConsumer(AsyncWebsocketConsumer):
    """음식 질량 추정 작업을 위한 WebSocket 소비자"""
    
    async def connect(self):
        """WebSocket 연결 처리"""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'
        
        logger.info(f"TaskConsumer.connect: Task ID: {self.task_id}")
        logger.info(f"TaskConsumer.connect: Room group name: {self.room_group_name}")
        
        # 작업이 존재하는지 확인
        task_exists = await self.check_task_exists(self.task_id)
        if not task_exists:
            logger.warning(f"TaskConsumer.connect: Task {self.task_id} not found")
            await self.close()
            return
        
        # 그룹에 참가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"TaskConsumer.connect: Added to group {self.room_group_name} with channel {self.channel_name}")
        
        await self.accept()
        
        # 현재 작업 상태 전송
        await self.send_current_task_status()
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제 처리"""
        # 그룹에서 나가기
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', '')
            
            if message_type == 'ping':
                # 핑 메시지에 대한 응답
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'task_id': self.task_id
                }))
            elif message_type == 'get_status':
                # 현재 상태 요청
                await self.send_current_task_status()
                
        except json.JSONDecodeError:
            pass
    
    async def task_update(self, event):
        """작업 업데이트 메시지 전송"""
        message = {
            'type': 'task.update',
            'task_id': event['task_id'],
            'data': event['data']
        }
        logger.info(f"TaskConsumer.task_update: Sending message to {self.channel_name}: {message}")
        logger.info(f"TaskConsumer.task_update: Channel name: {self.channel_name}")
        logger.info(f"TaskConsumer.task_update: Room group name: {self.room_group_name}")
        await self.send(text_data=json.dumps(message))
    
    async def task_completed(self, event):
        """작업 완료 메시지 전송"""
        message = {
            'type': 'task.completed',
            'task_id': event['task_id'],
            'data': event['data']
        }
        logger.info(f"TaskConsumer.task_completed: Sending message to {self.channel_name}: {message}")
        await self.send(text_data=json.dumps(message))
    
    async def task_failed(self, event):
        """작업 실패 메시지 전송"""
        message = {
            'type': 'task.failed',
            'task_id': event['task_id'],
            'data': event['data']
        }
        logger.info(f"TaskConsumer.task_failed: Sending message to {self.channel_name}: {message}")
        await self.send(text_data=json.dumps(message))
    
    @database_sync_to_async
    def check_task_exists(self, task_id):
        """작업이 존재하는지 확인"""
        try:
            return MassEstimationTask.objects.filter(task_id=task_id).exists()
        except:
            return False
    
    @database_sync_to_async
    def get_task_status(self, task_id):
        """작업 상태 조회"""
        try:
            task = MassEstimationTask.objects.get(task_id=task_id)
            return {
                'status': task.status,
                'progress': task.progress,
                'message': task.message,
                'error': task.error,
                'result_data': task.result_data,
                'estimated_mass': task.estimated_mass,
                'confidence_score': task.confidence_score
            }
        except MassEstimationTask.DoesNotExist:
            return None
    
    async def send_current_task_status(self):
        """현재 작업 상태 전송"""
        task_status = await self.get_task_status(self.task_id)
        
        if task_status:
            if task_status['status'] == 'completed':
                await self.send(text_data=json.dumps({
                    'type': 'task.completed',
                    'task_id': self.task_id,
                    'data': {
                        'status': 'completed',
                        'progress': 1.0,
                        'message': '작업이 완료되었습니다.',
                        'result': task_status['result_data'],
                        'estimated_mass': task_status['estimated_mass'],
                        'confidence_score': task_status['confidence_score']
                    }
                }))
            elif task_status['status'] == 'failed':
                await self.send(text_data=json.dumps({
                    'type': 'task.failed',
                    'task_id': self.task_id,
                    'data': {
                        'status': 'failed',
                        'error': task_status['error']
                    }
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'task.update',
                    'task_id': self.task_id,
                    'data': {
                        'status': task_status['status'],
                        'progress': task_status['progress'] / 100.0,  # 0-100을 0-1로 변환
                        'message': task_status['message']
                    }
                }))


class TestConsumer(AsyncWebsocketConsumer):
    """간단한 테스트용 WebSocket 소비자"""
    
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'message': '연결 성공!'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        await self.send(text_data=json.dumps({
            'message': f'받은 메시지: {text_data}'
        })) 