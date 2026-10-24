# Cáscara

## Descripción del proyecto

Cáscara es una aplicación web orientada a la venta de huevos de campo. Su objetivo es permitir que los clientes consulten los productos disponibles y, en futuras etapas del desarrollo, puedan registrarse, realizar pedidos y gestionar sus compras.

El proyecto se desarrolla como parte de la materia **Programación I**, utilizando una arquitectura que separa el backend del frontend.

## Tecnologías utilizadas

**Backend:**
- Python
- Django
- Django REST Framework
- django-cors-headers
- drf-spectacular

**Base de datos:**
- SQLite (durante el TP1).
- PostgreSQL (previsto para los próximos trabajos prácticos).

**Frontend:**
- React (previsto para una etapa posterior).

**Herramientas de desarrollo:**
- Visual Studio Code
- Git y GitHub
- GitHub Desktop

## Estado actual del proyecto

En el Trabajo Práctico N.º 1 se realizó la configuración inicial del backend.

Se implementó:
- Creación del proyecto Django `config`.
- Creación de la aplicación base `core`.
- Instalación y registro de las dependencias iniciales.
- Configuración de CORS para el futuro frontend.
- Aplicación de las migraciones iniciales.
- Creación de un superusuario.
- Verificación del servidor local y del panel de administración.

Las funcionalidades de productos, pedidos y compras se desarrollarán en etapas posteriores.

## Requisitos previos

Para ejecutar el proyecto es necesario tener instalado:

- Python 3
- pip
- Git

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/cotyarancibia/cascara.git
cd cascara
```

### 2. Crear el entorno virtual

```bash
python -m venv venv
```

### 3. Activar el entorno virtual

En Windows con PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Instalar las dependencias

```bash
python -m pip install -r requirements.txt
```

### 5. Aplicar las migraciones

```bash
python manage.py migrate
```

### 6. Crear un superusuario

```bash
python manage.py createsuperuser
```

### 7. Iniciar el servidor

```bash
python manage.py runserver
```

El servidor estará disponible en:

http://127.0.0.1:8000/

El panel de administración se encuentra en:

http://127.0.0.1:8000/admin/

## Organización inicial

- `config/`: configuración principal de Django.
- `core/`: aplicación base del backend.
- `manage.py`: ejecución de comandos de Django.
- `requirements.txt`: dependencias del proyecto.
- `README.md`: documentación general.

## Próximas etapas

Se incorporarán el modelado de datos, PostgreSQL, los endpoints de la API REST, la autenticación, el frontend en React y las funcionalidades de venta de huevos de campo.

## Variables de entorno

Para ejecutar el proyecto, crear un archivo `.env` en la raíz
del repositorio con la siguiente variable:

DJANGO_SECRET_KEY=tu_clave_secreta

El archivo `.env` está incluido en `.gitignore` para evitar
publicar información sensible.