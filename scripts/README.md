# Scripts de demo (VM de backend)

Adaptados de los scripts equivalentes del proyecto de referencia.

## Simulación de error humano

| Script | Qué hace |
|---|---|
| `simulate-human-error.sh` | Añade una línea de sintaxis inválida a `app/main.py` y reinicia el servicio — Gunicorn no podrá levantar los workers |
| `rollback-human-error.sh` | Quita esa línea y reinicia el servicio — recupera el backend |

Por defecto operan sobre `/opt/flight-booking-backend/app/main.py` y el
servicio `flight-booking-backend`. Puedes sobreescribirlo con variables
de entorno si tu despliegue usa otra ruta/nombre:
```bash
APP_FILE=/otra/ruta/main.py SERVICE_NAME=otro-nombre ./simulate-human-error.sh
```

**Requieren ejecutarse con permisos para `systemctl restart`** (root o un
usuario con sudo/policykit configurado para ese servicio concreto).

## Checkpoint de Zerto

`zerto_insert-checkpoint.sh "<VPG_NAME>" "<CHECKPOINT_TEXT>"` — inserta un
checkpoint manual en el VPG indicado, útil para marcar un punto de
recuperación justo antes de provocar el fallo (por ejemplo, justo antes
de ejecutar `simulate-human-error.sh`).

Detecta solo él en cuál de los dos ZVMA (origen/destino) vive el VPG, y
prueba 3 métodos de autenticación en cascada (`client_credentials` →
`password grant` → sesión clásica para Zerto < 9).

### ⚠️ Configuración de credenciales

Este script **no lleva ninguna credencial hardcodeada** — las lee de
variables de entorno obligatorias. Copia `.env.example` a `.env`,
rellena los valores reales, y cárgalo antes de ejecutar:

```bash
cp .env.example .env
nano .env          # credenciales reales de tus dos ZVMA
source .env
./zerto_insert-checkpoint.sh "ResilienceApp Remote" "Pre-deploy v2.3.1"
```

**Añade `.env` a tu `.gitignore`** — solo `.env.example` (sin valores
reales) debe llegar al repositorio.

> Si el fichero original de este script que ya tenías en uso incluía
> contraseñas o client secrets reales como valores por defecto en el
> propio código, y ese fichero ha estado en algún repositorio Git,
> considera esas credenciales comprometidas y rótalas — quedan en el
> historial de commits aunque se borren después.
