import multiprocessing
import os

# Bind to the container port configured for the API
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8088")

# Calculate a sensible default for workers while allowing overrides
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")

# Tuning knobs for production workloads
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "90"))

# Logging configuration (default to stdout/stderr so container logging captures it)
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Forward standard proxy headers if deployed behind a load balancer / reverse proxy
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")
proxy_protocol = bool(int(os.getenv("GUNICORN_PROXY_PROTOCOL", "0")))

# Enable application preloading for copy-on-write memory savings when using multiple workers
preload_app = bool(int(os.getenv("GUNICORN_PRELOAD_APP", "1")))

# Surfacing worker lifecycle hooks allows for future customization if needed
def on_starting(server):
    server.log.info("Starting Gunicorn with %s workers", workers)

