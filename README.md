# flight-booking-backend

API REST del **Flight Booking Simulator**, construida con FastAPI +
SQLAlchemy (async) + Gunicorn/Uvicorn, sobre el esquema de
`flight-booking-database`.

Forma parte de la demo de continuidad de negocio junto con:
- `flight-booking-database` — esquema PostgreSQL
- `flight-booking-frontend` — simulador de reservas (con RBG integrado)
- `observability-console` — dashboard de KPIs y monitorización (consulta esta API + Zerto directamente)

## Endpoints principales

| Método | Ruta                        | Descripción                                            |
|--------|-----------------------------|---------------------------------------------------------|
| GET    | `/api/health`                | Estado del servicio + conectividad a BD (monitorización) |
| GET    | `/api/airports`               | Catálogo de aeropuertos                                  |
| GET    | `/api/seat-classes`           | Catálogo de clases de asiento                            |
| GET    | `/api/flights`                | Lista de vuelos (filtrable por origen/destino/fecha)     |
| GET    | `/api/flights/{id}`           | Detalle de un vuelo                                      |
| POST   | `/api/bookings`                | **Crea una reserva** (usado por el RBG del frontend)     |
| GET    | `/api/bookings`                | Lista de reservas (filtrable por estado/fecha)           |
| GET    | `/api/bookings/{id}`           | Detalle de una reserva                                   |
| PATCH  | `/api/bookings/{id}/status`    | Cambia el estado de una reserva (p.ej. cancelar)         |
| GET    | `/api/kpis/summary`            | KPIs globales (total reservas, ingresos, última reserva) |
| GET    | `/api/kpis/timeseries`         | Serie temporal reservas/ingresos por minuto              |

Documentación interactiva automática en `/docs` (Swagger) y `/redoc`.

## Requisitos

- Python 3.11+
- Acceso de red a la VM de base de datos (puerto 5432)

## Despliegue en la VM de backend

```bash
# 1. Copiar el proyecto a la VM, p.ej. en /opt/flight-booking-backend
sudo mkdir -p /opt/flight-booking-backend
# (copia aquí el contenido del repo)

# 2. Crear entorno virtual e instalar dependencias
cd /opt/flight-booking-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
nano .env   # ajustar DATABASE_URL con la IP real de la VM de base de datos

# 4. Probar en local antes de systemd
gunicorn app.main:app -c gunicorn_conf.py

# 5. Instalar como servicio systemd para que arranque solo y se reinicie ante fallos
sudo useradd -r -s /bin/false flightapp || true
sudo chown -R flightapp:flightapp /opt/flight-booking-backend
sudo cp deploy/flight-booking-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now flight-booking-backend
sudo systemctl status flight-booking-backend
```

El backend queda escuchando en el puerto `8000` de la VM. Si quieres
exponerlo por el puerto 80/443 con TLS, coloca un NGINX como proxy
inverso delante (igual que en el frontend), apuntando a
`http://127.0.0.1:8000`.

## Notas para la demo de continuidad de negocio

- `/api/health` es el endpoint que la Observability Console usará para
  pintar el estado de "BackEnd - API" en tiempo real. Si esta VM cae,
  la consola debe reflejarlo como fallo de conectividad.
- `/api/kpis/*` son los únicos endpoints que necesita consultar la
  Observability Console para las gráficas — no necesita acceso directo
  a la base de datos.
- El estado de protección de datos (Zerto) **no pasa por este backend**:
  según el diseño acordado, la Observability Console lo consulta
  directamente contra la API de Zerto.

## Próximos pasos

1. `flight-booking-frontend`: UI + generador aleatorio de reservas (RBG) que llama a `POST /api/bookings`
2. `observability-console`: dashboard que consume `/api/kpis/*`, `/api/health` y la API de Zerto
