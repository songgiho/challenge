import requests
import asyncio
import websockets
import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import os

logger = logging.getLogger(__name__)

class MLServerClient:
    """ML 서버와 통신하는 클라이언트"""
    
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.ws_base_url = base_url.replace('http', 'ws')
    
    def start_estimation_task(self, image_path):
        """ML 서버에 비동기 작업 시작 요청"""
        url = f"{self.base_url}/api/v1/estimate_async"
        
        # 파일 경로 검증
        if not image_path:
            raise Exception("이미지 파일 경로가 None입니다.")
        
        if not os.path.exists(image_path):
            raise Exception(f"이미지 파일이 존재하지 않습니다: {image_path}")
        
        if not os.path.isfile(image_path):
            raise Exception(f"경로가 파일이 아닙니다: {image_path}")
        
        try:
            # 파일 크기 확인
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                raise Exception("이미지 파일이 비어있습니다.")
            
            logger.info(f"ML 서버에 파일 전송 시작: {image_path} (크기: {file_size} bytes)")
            
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, files=files, timeout=30)
            
            logger.info(f"ML 서버 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"ML 서버 작업 시작 성공: {result['task_id']}")
                return result['task_id']
            else:
                error_msg = response.json().get('detail', '알 수 없는 오류')
                logger.error(f"ML 서버 작업 시작 실패: {error_msg}")
                raise Exception(f"ML 서버 오류: {error_msg}")
                
        except requests.exceptions.Timeout:
            raise Exception("ML 서버 응답 시간 초과")
        except requests.exceptions.ConnectionError:
            raise Exception("ML 서버에 연결할 수 없습니다")
        except Exception as e:
            logger.error(f"ML 서버 API 호출 중 오류: {str(e)}")
            raise
    
    async def listen_task_progress(self, task_id, django_task_id):
        """ML 서버 WebSocket으로 진행상황 수신하고 Django WebSocket으로 전송"""
        uri = f"{self.ws_base_url}/api/v1/ws/task/{task_id}"
        channel_layer = get_channel_layer()
        
        try:
            async with websockets.connect(uri) as websocket:
                logger.info(f"ML 서버 WebSocket 연결됨: {task_id}")
                
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    logger.info(f"ML 서버 메시지 수신: {data['type']}")
                    
                    if data['type'] == 'task_status':
                        # 진행상황을 Django WebSocket으로 전송
                        progress = data['data']['progress']
                        message_text = data['data']['message']
                        
                        await channel_layer.group_send(
                            f"task_{django_task_id}",
                            {
                                "type": "task.update",
                                "task_id": django_task_id,
                                "data": {
                                    "status": "processing",
                                    "progress": progress,
                                    "message": message_text
                                }
                            }
                        )
                    
                    elif data['type'] == 'task_completed':
                        # 완료 결과를 Django WebSocket으로 전송
                        result = data['data']['result']
                        
                        await channel_layer.group_send(
                            f"task_{django_task_id}",
                            {
                                "type": "task.completed",
                                "task_id": django_task_id,
                                "data": {
                                    "status": "completed",
                                    "progress": 1.0,
                                    "result": result,
                                    "message": "음식 분석이 완료되었습니다."
                                }
                            }
                        )
                        break
                    
                    elif data['type'] == 'task_failed':
                        # 실패 메시지를 Django WebSocket으로 전송
                        error = data['data']['error']
                        
                        await channel_layer.group_send(
                            f"task_{django_task_id}",
                            {
                                "type": "task.failed",
                                "task_id": django_task_id,
                                "data": {
                                    "status": "failed",
                                    "error": error,
                                    "message": f"ML 서버 오류: {error}"
                                }
                            }
                        )
                        break
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"ML 서버 WebSocket 연결이 끊어짐: {task_id}")
            raise Exception("ML 서버 연결이 끊어졌습니다")
        except Exception as e:
            logger.error(f"ML 서버 WebSocket 오류: {str(e)}")
            raise

def run_ml_task_sync(task_id, image_path):
    """동기적으로 ML 서버 작업을 실행하고 결과 반환"""
    client = MLServerClient()
    
    try:
        # 1. ML 서버에 작업 시작 요청
        ml_task_id = client.start_estimation_task(image_path)
        
        # 2. WebSocket으로 진행상황 수신
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                client.listen_task_progress(ml_task_id, task_id)
            )
        finally:
            loop.close()
            
        return {"success": True, "ml_task_id": ml_task_id}
        
    except Exception as e:
        logger.error(f"ML 서버 작업 실행 실패: {str(e)}")
        return {"success": False, "error": str(e)} 