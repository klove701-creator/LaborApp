# Gunicorn 설정 파일
import os

# 서버 소켓
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# 워커 프로세스 수 (Railway의 메모리 고려)
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))

# 워커 클래스 (기본: sync)
worker_class = "sync"

# 워커당 스레드 수
threads = int(os.environ.get('THREADS_PER_WORKER', '4'))

# 워커 연결 수 제한
worker_connections = 1000

# 타임아웃 설정
timeout = 120
keepalive = 2

# 로깅 설정
accesslog = "-"  # stdout으로 액세스 로그
errorlog = "-"   # stderr로 에러 로그
loglevel = "info"

# 프리로드 (메모리 효율성)
preload_app = True

# 워커 재시작 설정
max_requests = 1000
max_requests_jitter = 50

# 프로세스 이름
proc_name = "nomubi-management"