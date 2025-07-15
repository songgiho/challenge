import requests
import json
from django.conf import settings
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


class MLServerService:
    """ML 서버와 통신하는 서비스 클래스"""
    
    def __init__(self):
        self.base_url = settings.ML_SERVER_URL
        self.session = requests.Session()
    
    def estimate_mass(self, image_file) -> Dict[str, Any]:
        """
        ML 서버에 이미지를 전송하여 질량을 추정 (동기)
        image_file: 파일 경로(str) 또는 파일 객체
        """
        try:
            if isinstance(image_file, (str, bytes, os.PathLike)):
                f = open(image_file, 'rb')
                files = {'file': (os.path.basename(image_file), f, 'application/octet-stream')}
            else:
                files = {'file': (getattr(image_file, 'name', 'upload.jpg'), image_file, getattr(image_file, 'content_type', 'application/octet-stream'))}
            response = self.session.post(
                f"{self.base_url}/api/v1/estimate",
                files=files,
                timeout=300
            )
            if isinstance(image_file, (str, bytes, os.PathLike)):
                f.close()
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ML 서버 통신 오류: {e}")
            raise Exception(f"ML 서버 통신 실패: {str(e)}")
        except Exception as e:
            logger.error(f"질량 추정 처리 오류: {e}")
            raise Exception(f"질량 추정 실패: {str(e)}")
    
    def estimate_mass_async(self, image_file) -> Dict[str, Any]:
        """
        ML 서버에 비동기로 이미지를 전송하여 질량을 추정
        image_file: 파일 경로(str) 또는 파일 객체
        """
        try:
            if isinstance(image_file, (str, bytes, os.PathLike)):
                f = open(image_file, 'rb')
                files = {'file': (os.path.basename(image_file), f, 'application/octet-stream')}
            else:
                files = {'file': (getattr(image_file, 'name', 'upload.jpg'), image_file, getattr(image_file, 'content_type', 'application/octet-stream'))}
            response = self.session.post(
                f"{self.base_url}/api/v1/estimate_async",
                files=files,
                timeout=30
            )
            if isinstance(image_file, (str, bytes, os.PathLike)):
                f.close()
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"ML 서버 비동기 통신 오류: {e}")
            raise Exception(f"ML 서버 비동기 통신 실패: {str(e)}")
        except Exception as e:
            logger.error(f"비동기 질량 추정 처리 오류: {e}")
            raise Exception(f"비동기 질량 추정 실패: {str(e)}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        ML 서버에서 작업 상태 조회
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/task/{task_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"작업 상태 조회 오류: {e}")
            raise Exception(f"작업 상태 조회 실패: {str(e)}")
    
    def format_ml_response(self, ml_response: Dict[str, Any]) -> Dict[str, Any]:
        try:
            mass_estimation = ml_response.get('mass_estimation', {})
            foods = mass_estimation.get('foods', [])
            formatted_result = {
                "filename": ml_response.get('filename', ''),
                "detected_objects": ml_response.get('detected_objects', {}),
                "mass_estimation": {
                    "foods": foods,
                    "total_mass_g": mass_estimation.get('total_mass_g', 0.0),
                    "food_count": len(foods)
                }
            }
            return formatted_result
        except Exception as e:
            logger.error(f"ML 응답 형식 변환 오류: {e}")
            raise Exception(f"응답 형식 변환 실패: {str(e)}") 