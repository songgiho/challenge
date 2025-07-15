import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import MassEstimationTask


class TaskConsumer(AsyncWebsocketConsumer):
    """작업 상태를 실시간으로 전송하는 WebSocket 소비자"""
    
    async def connect(self):
        """WebSocket 연결 처리"""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_{self.task_id}'
        
        # 작업이 존재하는지 확인
        task_exists = await self.check_task_exists(self.task_id)
        if not task_exists:
            await self.close()
            return
        
        # 그룹에 참가
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
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
                
        except json.JSONDecodeError:
            pass
    
    async def task_update(self, event):
        """작업 업데이트 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'task_update',
            'task_id': event['task_id'],
            'data': event['data']
        }))
    
    async def task_completed(self, event):
        """작업 완료 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'task_completed',
            'task_id': event['task_id'],
            'data': event['data']
        }))
    
    async def task_failed(self, event):
        """작업 실패 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'task_failed',
            'task_id': event['task_id'],
            'data': event['data']
        }))
    
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
                'result_data': task.result_data
            }
        except MassEstimationTask.DoesNotExist:
            return None
    
    async def send_current_task_status(self):
        """현재 작업 상태 전송"""
        task_status = await self.get_task_status(self.task_id)
        
        if task_status:
            if task_status['status'] == 'completed':
                await self.send(text_data=json.dumps({
                    'type': 'task_completed',
                    'task_id': self.task_id,
                    'data': {
                        'status': 'completed',
                        'progress': 1.0,
                        'message': '작업이 완료되었습니다.',
                        'result': task_status['result_data']
                    }
                }))
            elif task_status['status'] == 'failed':
                await self.send(text_data=json.dumps({
                    'type': 'task_failed',
                    'task_id': self.task_id,
                    'data': {
                        'status': 'failed',
                        'error': task_status['error']
                    }
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'task_update',
                    'task_id': self.task_id,
                    'data': {
                        'status': task_status['status'],
                        'progress': task_status['progress'],
                        'message': task_status['message']
                    }
                })) 