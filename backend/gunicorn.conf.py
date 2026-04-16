import multiprocessing
import os

bind = "0.0.0.0:8000"

workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", 2))
worker_class = "gthread"

timeout = 30
graceful_timeout = 10
keepalive = 5

max_requests = 1000
max_requests_jitter = 50

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

forwarded_allow_ips = "*"
proxy_protocol = False

worker_tmp_dir = "/dev/shm"
