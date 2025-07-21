FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv 설치
RUN pip install uv

# 프로젝트 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치
RUN uv sync --frozen

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 기본 명령어
CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]