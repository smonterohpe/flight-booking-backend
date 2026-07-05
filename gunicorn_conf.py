import multiprocessing

# Escucha en todas las interfaces, puerto 8000 (equivalente al :80000 /
# :8000 del backend en el diagrama de referencia)
bind = "0.0.0.0:8000"

worker_class = "uvicorn.workers.UvicornWorker"
workers = multiprocessing.cpu_count() * 2 + 1

timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"   # stdout, para que journald/systemd lo capture
errorlog = "-"
loglevel = "info"
