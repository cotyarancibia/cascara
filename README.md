# Cáscara

## Descripción

**Cáscara** es una aplicación web para la venta de huevos de campo, desarrollada como proyecto de la materia **Programación I**.

Su objetivo es permitir la consulta de productos y, en futuras etapas, la gestión de usuarios, carritos y compras.

## Tecnologías utilizadas

- **Backend:** Python, Django y Django REST Framework.
- **Base de datos:** PostgreSQL.
- **Documentación API:** Swagger (drf-spectacular).
- **Frontend:** React (próximamente).
- **Herramientas:** Git, GitHub, VS Code y DBeaver.

## Funcionalidades implementadas

### Configuración inicial
- Creación del proyecto Django `config` y la aplicación `core`.
- Instalación de dependencias y configuración de CORS.
- Configuración inicial de la base de datos.
- Creación del superusuario y acceso a Django Admin.

### Modelado de datos y API REST
- Configuración de PostgreSQL mediante variables de entorno.
- Creación de ocho modelos: `User`, `Category`, `Product`, `Stock`, `Cart`, `CartItem`, `Order` y `OrderItem`.
- Definición de relaciones y aplicación de migraciones.
- Registro de modelos en Django Admin.
- Implementación de serializers y endpoints CRUD con Django REST Framework.
- Documentación y pruebas manuales mediante Swagger.

## Instalación y ejecución

**1. Clonar el repositorio**

```bash
git clone https://github.com/cotyarancibia/cascara.git
cd cascara
```

**2. Crear y activar el entorno virtual (Windows)**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**3. Instalar dependencias**

```bash
pip install -r requirements.txt
```

**4. Configurar PostgreSQL**

Crear la base de datos `cascara_db` y un usuario con permisos sobre ella.

Crear un archivo `.env` en la raíz del proyecto:

```env
DJANGO_SECRET_KEY=tu_clave_secreta
DB_NAME=cascara_db
DB_USER=cascara_user
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

**5. Aplicar migraciones e iniciar el servidor**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API REST

Los endpoints están disponibles bajo `/api/`:

- `/api/categorias/`
- `/api/productos/`
- `/api/stock/`
- `/api/carritos/`
- `/api/items-carrito/`
- `/api/pedidos/`
- `/api/items-pedido/`

Permiten realizar operaciones CRUD mediante los métodos HTTP `GET`, `POST`, `PUT`, `PATCH` y `DELETE`.

## Usuarios, roles y autenticación

Los roles son `CLIENTE`, `VENDEDOR` y `ADMIN`. El registro público crea
exclusivamente clientes; administradores y vendedores pueden gestionar productos,
categorías y stock. Cada cliente gestiona su propio carrito y sus propios pedidos.
Los ítems solo pueden cambiarse mientras el pedido esté `PENDIENTE`; el precio
unitario y el total se calculan en el servidor.

| Endpoint | Uso |
| --- | --- |
| `POST /api/auth/register/` | Registro: `username`, `email`, `password` y `password_confirm` (opcionalmente `telefono` y `direccion`). |
| `POST /api/auth/login/` | Recibe `username` y `password`; devuelve `access` y `refresh`. |
| `POST /api/auth/refresh/` | Recibe `refresh` y devuelve un nuevo access y un nuevo refresh; el refresh anterior queda revocado. |
| `GET /api/auth/profile/` | Devuelve el perfil del usuario autenticado. |
| `POST /api/auth/logout/` | Recibe el `refresh` propio y lo revoca. |

Para acceder a un endpoint protegido, enviar el access token en el encabezado
`Authorization: Bearer <access>`. Al renovar tokens, conservar el nuevo refresh.
El logout no invalida el access token ya emitido, que sigue válido hasta vencer.
El servidor asigna el usuario al carrito y al pedido; para añadir un ítem de
carrito se envían `producto` y `cantidad`, y para un ítem de pedido también
se indica `pedido`. Las relaciones de propiedad no se pueden cambiar después.

### Usuarios existentes al actualizar desde TP2

La migración agrega el rol `CLIENTE` a los usuarios existentes sin cambiar
`is_staff`, `is_superuser`, grupos ni permisos. Los superusuarios conservan
sus privilegios de superusuario; `is_staff` por sí solo no concede el rol
`ADMIN` de la API. Un administrador debe revisar individualmente los usuarios
existentes y asignar `ADMIN` o `VENDEDOR` en Django Admin solo cuando corresponda.
No se promueve automáticamente a todo el staff, ya que sus permisos pueden ser
limitados. Verificar la migración primero en una copia de PostgreSQL.

**Documentación Swagger:** http://127.0.0.1:8000/api/docs/

**Panel de administración:** http://127.0.0.1:8000/admin/

## Próximas etapas

Se incorporará el frontend con React para completar el proceso de compra.
