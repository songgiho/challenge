# FoodCalorie 백엔드 실행 가이드

## Redis 설치 방법

### Windows
- 공식 윈도우 포트: [https://github.com/tporadowski/redis/releases](https://github.com/tporadowski/redis/releases)
- 최신 zip 파일 다운로드 → 압축 해제 → `redis-server.exe` 실행

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install redis-server
```

### Mac (Homebrew)
```bash
brew install redis
brew services start redis
```

---

## 실행 순서

1. **Redis 서버 실행**
   - Windows: `redis-server.exe` 실행 (설치 경로에서 더블클릭 또는 명령 프롬프트에서 실행)
   - Linux/Mac: `redis-server` 명령어 실행

2. **Celery 워커 실행**
   - **Windows (권한 문제 해결):**
     ```bash
     celery -A config worker -l info --pool=solo
     ```
   - **Linux/Mac:**
     ```bash
     celery -A config worker -l info
     ```

3. **Django 서버 실행**
   - 아래 명령어를 프로젝트 루트(backend)에서 실행
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

4. **ML 서버 실행**
   - ML 서버가 포트 8001에서 실행 중이어야 합니다.
   - 예시: `python -m uvicorn ml_server.main:app --host 0.0.0.0 --port 8001`

---

## 전체 예시 (윈도우 기준)

1. `redis-server.exe` 실행 (별도 창)
2. 새 터미널에서:
   ```bash
   celery -A config worker -l info --pool=solo
   ```
3. 또 다른 터미널에서:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
4. ML 서버도 별도 터미널에서 실행

---

## Windows에서 발생하는 문제 해결

### Celery 권한 오류
Windows에서 `PermissionError: [WinError 5] 액세스가 거부되었습니다` 오류가 발생하면:

**해결 방법:**
```bash
celery -A config worker -l info --pool=solo
```

**원인:** Windows의 멀티프로세싱 제한으로 인한 권한 문제
**해결:** `--pool=solo` 옵션으로 단일 프로세스 모드 사용

---

## 참고
- 모든 서비스가 동시에 실행되어야 비동기 API가 정상 동작합니다.
- 각 서비스가 정상적으로 실행 중인지 확인하세요.
- 궁금한 점이 있으면 언제든 문의하세요!
