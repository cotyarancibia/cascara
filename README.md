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

**Documentación Swagger:** http://127.0.0.1:8000/api/docs/

**Panel de administración:** http://127.0.0.1:8000/admin/

## Próximas etapas

Se incorporarán autenticación JWT, permisos, validaciones, pruebas automatizadas y el frontend con React para completar el proceso de compra.
