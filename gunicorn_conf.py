import multiprocessing

# Escucha en todas las interfaces, puerto 8000
bind = "0.0.0.0:8000"

worker_class = "uvicorn.workers.UvicornWorker"

# IMPORTANTE: debe ser 1 worker para que el singleton RBGManager
# (generador aleatorio de reservas) sea único en todo el proceso.
# Con múltiples workers, cada uno tiene su propia copia del singleton
# y el start/stop desde el frontend solo afecta al worker que recibe
# la petición — los demás siguen generando. Con asyncio + uvicorn,
# 1 worker maneja miles de conexiones concurrentes sin problema.
workers = 1

timeout = 30
graceful_timeout = 30
keepalive = 5

accesslog = "-"   # stdout, para que journald/systemd lo capture
errorlog = "-"
loglevel = "info"
