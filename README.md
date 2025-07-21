# FoodCalorie 백엔드 실행 가이드

## 🚀 빠른 시작 (Windows)

### 원클릭 실행

```bash
# backend 폴더에서 실행
start-services.bat
```

### 서비스 종료

```bash
# backend 폴더에서 실행
stop-services.bat
```

---

## 📋 수동 실행 방법

### 1. 필수 조건

- Python 3.11+
- uv 패키지 매니저

### 2. 의존성 설치

```bash
cd backend
uv sync
```

### 3. 서비스 실행 순서

#### Windows

```bash
# 1. Redis 서버 (새 터미널)
redis-windows\redis-server.exe --port 6379

# 2. Celery 워커 (새 터미널)
uv run celery -A config worker -l info --pool=solo

# 3. Django 서버 (새 터미널)
uv run manage.py runserver
```

#### Linux/Mac

```bash
# 1. Redis 설치 및 실행
sudo apt install redis-server  # Ubuntu
brew install redis             # Mac
redis-server

# 2. Celery 워커 (새 터미널)
uv run celery -A config worker -l info

# 3. Django 서버 (새 터미널)
uv run manage.py runserver
```

---

## 🐳 Docker 실행 (추천)

### Docker Compose 사용

```bash
cd backend
docker-compose up -d
```

### 개별 서비스 확인

```bash
# Redis 상태 확인
docker-compose ps redis

# 로그 확인
docker-compose logs -f django
docker-compose logs -f celery
```

---

## 🔧 시스템 구성

### 포트 정보

- **Django**: http://localhost:8000
- **Redis**: localhost:6379
- **MLServer**: http://localhost:8001 (별도 실행 필요)

### 주요 API 엔드포인트

- **Gemini 이미지 분석**: `POST /api/logs/analyze-image/`
- **MLServer 연동**: `POST /mlserver/api/upload/`
- **WebSocket 테스트**: http://localhost:8000/mlserver/test-websocket/

---

## 🛠️ 문제 해결

### Windows Celery 권한 오류

```bash
# 해결 방법: --pool=solo 옵션 사용
uv run celery -A config worker -l info --pool=solo
```

### Redis 연결 오류

```bash
# Redis 서버 상태 확인
redis-windows\redis-cli.exe ping
# 응답: PONG (정상)
```

### 포트 충돌

```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000
netstat -ano | findstr :6379
```

---

## 📁 폴더 구조

```
backend/
├── redis-windows/          # Redis 서버 (Windows용)
├── start-services.bat      # 원클릭 시작 스크립트
├── stop-services.bat       # 서비스 종료 스크립트
├── docker-compose.yml      # Docker 설정
├── api_integrated/         # 메인 API (Gemini)
├── mlserver/              # MLServer 연동
└── config/                # Django 설정
```

---

## 🎯 팀원 공유 시

1. **저장소 클론**

   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **의존성 설치**

   ```bash
   uv sync
   ```

3. **서비스 실행**

   ```bash
   start-services.bat  # Windows
   ```

4. **브라우저 접속**
   - http://localhost:8000 (Django)
   - http://localhost:3000 (프론트엔드)

---

## 💡 추가 정보

- CSV 파일 오류는 무시해도 됩니다 (런타임에만 필요)
- MLServer는 별도로 실행해야 합니다 (8001포트)
- 모든 서비스가 실행되어야 전체 기능 사용 가능
