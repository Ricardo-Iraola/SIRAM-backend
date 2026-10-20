# SIRAM Backend — Django REST Framework

Backend inicial para el frontend React/Vite/MUI de [dddarioDLC/siram-front](https://github.com/dddarioDLC/siram-front), basado en la especificación funcional del proyecto SIRAM.

## Requisitos
- Python 3.12+
- PostgreSQL 15+ (o SQLite para una prueba local sin configurar `DB_HOST`)
- Git

## Ejecutar localmente con PostgreSQL
```bash
# Windows PowerShell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Editar .env si el PostgreSQL local usa otras credenciales
python manage.py makemigrations core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
API base: `http://127.0.0.1:8000/api/`  
Administración Django: `http://127.0.0.1:8000/admin/`

Para SQLite de desarrollo, dejá `DB_HOST` vacío en `.env`. En el entorno del equipo se recomienda PostgreSQL.

## Ejecutar con Docker
```bash
Copy-Item .env.example .env
docker compose up --build
```
El servicio backend espera PostgreSQL y aplica migraciones al iniciar. En una primera instalación, creá el administrador con:
```bash
docker compose exec backend python manage.py createsuperuser
```

## Autenticación
`POST /api/auth/token/`
```json
{"username": "usuario", "password": "contraseña"}
```
Respuesta JWT: `access` y `refresh`. En endpoints protegidos enviar:
`Authorization: Bearer <access>`

`POST /api/auth/token/refresh/` acepta `{"refresh": "<refresh>"}`.  
`GET /api/auth/me/` devuelve el usuario autenticado.

## Endpoints principales
| Método | Endpoint | Uso |
|---|---|---|
| GET/POST | `/api/casos/` | Consultar/crear casos |
| GET/PATCH/DELETE | `/api/casos/{id}/` | Detalle/actualización/baja de caso |
| GET | `/api/casos/{id}/posibles_duplicados/` | Candidatos para revisión manual |
| POST | `/api/casos/{id}/consolidar_denuncia/` | Vincular una denuncia a un caso |
| GET | `/api/denuncias/` | Bandeja interna de denuncias |
| POST | `/api/denuncias/publica/` | Canal ciudadano sin autenticación |
| POST | `/api/denuncias/{id}/aprobar/` | Aprobar denuncia |
| POST | `/api/denuncias/{id}/rechazar/` | Rechazar denuncia |
| GET/POST | `/api/personas/` | Personas vinculadas a casos |
| GET/POST | `/api/animales/` | Animales vinculados a casos |
| GET/POST | `/api/documentos/` | Documentación asociada |
| GET/POST | `/api/seguimientos/` | Seguimiento de casos |
| GET | `/api/organismos/` | Organismos |
| GET | `/api/dashboard/` | Indicadores básicos |
| GET | `/api/auditoria/` | Auditoría (administrador) |
| GET/POST | `/api/usuarios/` | Administración de usuarios (administrador) |

La mayoría de listados soportan paginación, filtros y búsqueda. Ejemplos:
`/api/casos/?estado=ABIERTO&tipo_evento=MORDEDURA`
`/api/casos/?search=centro`
`/api/denuncias/?estado=PENDIENTE`

## Vincular con el frontend
El repositorio frontend actualmente documenta que trabaja con datos de ejemplo y todavía no consume una API. Configurá la URL de API en el frontend mediante una variable de Vite, por ejemplo:
```env
VITE_API_URL=http://127.0.0.1:8000/api
```
En las funciones de acceso a datos del frontend, usar esa variable y consumir los endpoints anteriores. Si el frontend aún no tiene una capa API, crear una en `src/services/api.js` (o en la ubicación que adopte el equipo) y reemplazar progresivamente los datos de ejemplo. No se modificó el repositorio frontend desde este paquete.

## Roles
- `ADMIN`: administración de usuarios y configuración.
- `AGENTE`: gestión operativa de casos y denuncias.
- `ANALISTA`: consulta y análisis.
- Ciudadanía: sólo puede enviar una denuncia al endpoint público; no obtiene acceso a los registros internos.

## Modelo de datos incluido
Organismo, Usuario, Caso, Denuncia, Persona, Animal, Documento, Seguimiento y Auditoria.

## Importante antes de producción
Este es un punto de partida funcional, no una implementación certificada para producción. Antes de utilizar datos reales:
- definir con los organismos la matriz definitiva de permisos y alcance por organismo;
- revisar las reglas de protección de datos personales, acceso a documentación y retención;
- endurecer HTTPS, secretos, backups, límites de carga y validación de archivos;
- incorporar pruebas de permisos y de integración;
- definir las reglas oficiales de detección y consolidación de duplicados;
- implementar exportación CSV/XLSX, PDF, importación CSV y geocodificación según se validen los requerimientos.
No cargar datos personales reales en ambientes de prueba.
