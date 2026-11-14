# TP10: preparación para publicar Cáscara

Este documento describe un despliegue **futuro**. La preparación del repositorio no crea cuentas, bases ni servicios y no prueba la infraestructura real. Confirmá el costo y los recursos activos en cada proveedor antes de empezar y al finalizar.

## Arquitectura y cuentas

Creá tus propias cuentas de Railway, Vercel y Cloudinary y conectá GitHub solo cuando decidas publicar. Vercel sirve el frontend React; Railway ejecuta Django y aloja una **nueva** base PostgreSQL; Cloudinary almacena fotografías. Son servicios independientes. La base local y `db_tp9_manual.sqlite3` no se usan ni se copian automáticamente.

Consultá la documentación vigente: [Railway y health checks](https://docs.railway.com/deployments/healthchecks), [Vite en Vercel](https://vercel.com/docs/frameworks/frontend/vite) y [SDK de Cloudinary](https://cloudinary.com/documentation/django_integration). El SDK 1.47.0 declara pruebas de compatibilidad hasta Django 6.0; el proyecto usa Django 6.1.3, por lo que debe verificarse la integración real en un entorno de prueba antes de entregar en producción.

## 1. Railway: base nueva y backend

1. Creá un proyecto y un servicio PostgreSQL **nuevo y vacío**. No reutilices `cascara_db` ni conectes recursos locales.
2. Creá el servicio de Django desde el repositorio GitHub, usando como directorio raíz el repositorio. Elegí la rama de despliegue aprobada por vos. Railpack instala las dependencias de `requirements.txt`; configurá en el servicio el comando de build `python manage.py collectstatic --noinput`. Configurá el comando de inicio `/bin/sh -c 'exec gunicorn config.wsgi:application --bind "0.0.0.0:$PORT"'` y el health check `/api/health/`. El `Procfile` contiene el mismo inicio para Railpack; comprobá que no haya un comando automático de migración en la configuración del servicio.
3. En las variables privadas del servicio Django configurá:

| Variable | Qué configurar |
| --- | --- |
| `CASCARA_ENV` | `production`, explícitamente en el entorno del servicio. |
| `DJANGO_SECRET_KEY` | Clave larga, aleatoria y privada; no compartir ni versionar. |
| `DJANGO_DEBUG` | `False`. |
| `DJANGO_ALLOWED_HOSTS` | Dominio público real del backend y `healthcheck.railway.app`, separados por comas, sin `https://`. |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Origen HTTPS exacto del frontend Vercel, sin barra final. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origen HTTPS exacto del backend para Django Admin; agregá el del frontend si enviará formularios con cookies. |
| `DATABASE_URL` | Referencia privada a la URL de la PostgreSQL **nueva** de este proyecto Railway. |
| `CLOUDINARY_URL` | Variable privada del entorno Cloudinary con sus credenciales. |
| `AUTH_REDIS_URL` | URL privada de una instancia Redis compartida entre todos los procesos Django, dedicada a la limitación de acceso. |
| `AUTH_TRUSTED_PROXIES` | Redes CIDR específicas de los proxies que conectan directamente con Django, separadas por comas. Confirmar los rangos reales de la infraestructura antes de configurarlos. |

Railway proporciona `PORT`. No copies credenciales a `VITE_*`, al repositorio, a capturas ni a mensajes. `CASCARA_DB_MODE` debe estar ausente o ser `postgresql`. Producción rechaza SQLite, hosts con comodines, orígenes inseguros, `DEBUG=True` y falta de Cloudinary. Los orígenes son listas separadas por comas. Al agregar un dominio de Vercel o backend, actualizá las listas y volvé a desplegar.

Para login se permiten 30 solicitudes por origen por hora y 8 por combinación origen/usuario por minuto; para registro, 5 por origen por hora. Los límites incluyen peticiones exitosas y fallidas. No se bloquea la cuenta globalmente. En producción Django exige Redis y redes de proxy explícitas; si falla Redis o la IP no es válida, las rutas protegidas responden 503. El proxy debe sobrescribir `X-Real-IP`, ser el único acceso al proceso y pertenecer a esas redes. No habilites rangos amplios que incluyan clientes u otros servicios no confiables. Confirmá con Railway estos supuestos y probalos antes de abrir el servicio: sin una ruta de red confiable, no hay identificación segura del cliente. Verificá costo, aislamiento, autenticación y transporte privado o TLS de Redis. No se ha creado ni probado ningún servicio externo.

La caché local se usa solo en desarrollo y pruebas: no comparte límites entre procesos. El throttling de DRF usa operaciones de caché no atómicas, puede admitir solicitudes adicionales en concurrencia y no protege por sí solo contra ataques distribuidos o denegación de servicio. Para un despliegue público complementalo con límites en un proxy/WAF confiable, monitoreo y pruebas de carga; usuarios detrás de una misma IP comparten el límite por origen.

El backend confía en `X-Forwarded-Proto` únicamente bajo el proxy HTTPS de Railway; no expongas Gunicorn directamente a Internet sin un proxy confiable. Se exige HTTPS para rutas públicas salvo el endpoint de salud interno, que no requiere credenciales. Django Admin usa cookies de sesión y CSRF seguras; la API React usa `Authorization: Bearer`, no cookies JWT. El estado de salud solo confirma que Django responde, no que la base o Cloudinary estén disponibles.

En producción el backend de correo queda configurado para SMTP y no para imprimir correos en consola. La aplicación no configura credenciales SMTP ni implementa una verificación de envío; si se incorporan funciones de correo, hay que configurar un proveedor y probarlo por separado. HSTS se activa para el host, sin incluir automáticamente subdominios ni solicitar precarga; evaluá esas opciones cuando controles todos los dominios afectados.

### Migraciones controladas y administrador

Después de verificar que `DATABASE_URL` referencia **la base nueva de Railway**, y antes de abrir el servicio al público, usá una consola del servicio Django dentro de Railway (por ejemplo, Railway SSH) para ejecutar:

```bash
python manage.py showmigrations core
python manage.py migrate --noinput
python manage.py createsuperuser
```

La primera migración aplica el conjunto desde 0001, incluidas 0005, 0006 y 0007. Revisá la salida y cualquier error; no ejecutes estos comandos con una URL de base local o de datos existentes sin un procedimiento de respaldo y aprobación. `createsuperuser` solicita los datos de forma interactiva: elegí credenciales propias y no las incluyas en capturas. El superusuario recibe capacidades administrativas de la API. En despliegues posteriores, revisá las migraciones y los respaldos antes de ejecutarlas; Railway ofrece un [paso pre-deploy](https://docs.railway.com/deployments/pre-deploy-command) que puede configurarse de forma consciente cuando el procedimiento esté aprobado.

Railway indica que su formato anterior `railway.json` de configuración como código está obsoleto para servicios nuevos; por eso esta preparación usa `Procfile` y configuración explícita en el panel. Revisá la [documentación vigente](https://docs.railway.com/builds/build-configuration) al realizar el despliegue.

El primer proceso puede responder al health check antes de que existan tablas; no confundas ese estado con migraciones aplicadas. Restringí el acceso hasta terminar la preparación. `collectstatic` prepara archivos estáticos en `staticfiles/`; WhiteNoise los sirve y no sirve las fotografías de usuarios.

## 2. Cloudinary: fotografías

En la consola de Cloudinary obtené la variable de entorno privada de API y configurala como `CLOUDINARY_URL` solo en Railway. No la pegues en Vercel ni en el frontend. Tras aplicar migraciones, iniciá sesión con una cuenta autorizada y cargá una fotografía desde el formulario de productos. Elegí manualmente el producto correcto. El backend valida JPEG, PNG o WebP, extensión y tipo, hasta 5 MiB y 20 megapíxeles. La API devuelve `imagen_url` HTTPS; comprobá en Cloudinary que la imagen efectivamente apareció y que la URL funciona.

Las fotografías guardadas previamente en el disco local no se copian solas. Para reutilizarlas, elegí los archivos aprobados de `frontend/public/images/` desde el formulario, sin asociarlos por ID o nombre automáticamente. Conservar copias y definir retención y borrado de imágenes reemplazadas es una tarea operativa. En producción se necesita almacenamiento persistente y respaldos tanto de la base como de los archivos.

## 3. Vercel: frontend

Importá el repositorio en Vercel y configurá **Root Directory** como `frontend`, framework Vite, build `npm run build` y salida `dist`. Establecé `VITE_API_URL` como la URL HTTPS pública del backend seguida una sola vez por `/api`, sin barra final. Es pública por diseño: nunca pongas contraseñas, claves de firma ni `CLOUDINARY_URL` en variables `VITE_*`. Reconstruí el frontend al cambiarla.

`frontend/vercel.json` reescribe las rutas de React hacia `index.html` para permitir recargar `/login`, `/productos` y las demás rutas. En local, `frontend/.env.example` conserva `http://localhost:8000/api` y Vite usa el puerto 3000.

## 4. Verificaciones después de publicar

- Consultá `GET https://<dominio-backend>/api/health/`: debe devolver `{"status":"ok","service":"api"}`. No pegues credenciales en la URL.
- Abrí `/api/schema/`, `/api/docs/` (Swagger) y `/api/redoc/` en el backend. Comprobá que la documentación cargue sin datos sensibles.
- Registrá o utilizá una cuenta autorizada de prueba y pedí tokens con `POST /api/auth/login/` enviando `username` y `password` de forma privada. Usá el `access` en `Authorization: Bearer <access>` para `GET /api/auth/profile/`; no compartas respuestas ni tokens en capturas.
- Cargá una imagen autorizada, comprobá Cloudinary y verificá su URL en catálogo y detalle. Abrí el frontend Vercel, probá login, navegación, carga de productos y recarga de una ruta interna. No confirmes compras reales durante la verificación.
- La consigna disponible no identifica qué capturas exige el profesor. Confirmá esa lista antes de entregar; como evidencia posible, prepará vistas sin secretos del health check, Swagger, aplicación y configuración de servicios.

## Problemas comunes

- **400 del health check:** agregá `healthcheck.railway.app` a `DJANGO_ALLOWED_HOSTS`; comprobá que Gunicorn escuche en `PORT`.
- **Error de CORS o CSRF:** compará origen, esquema HTTPS y puerto exactos; no habilites comodines.
- **404 al recargar una ruta React:** revisá que Vercel use `frontend` como raíz y aplique `vercel.json`.
- **Error de tablas inexistentes:** verificá primero que el servicio apunte a la base nueva y revisá las migraciones; no migres otra base por accidente.
- **Imágenes faltantes:** comprobá la configuración privada de Cloudinary y volvé a subir manualmente los archivos locales correspondientes; no publiques el secreto.
- **Frontend sin conexión:** `VITE_API_URL` debe terminar en `/api`, usar HTTPS en producción y configurarse antes del build.

La autenticación del TP8 guarda JWT en `localStorage` por la consigna educativa. Un ataque XSS podría acceder a ellos; antes de una publicación real se debe revisar el modelo de amenazas y considerar una solución de sesión adecuada para producción.
