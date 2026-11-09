# TP4 — Matriz de pruebas manuales de Cáscara

Esta matriz contiene **20 casos planificados**, basados en el código de la rama `tp4`. No se ejecutaron pruebas en Postman. La columna «Resultado esperado» describe el comportamiento deducido del backend actual; cuando existe una regla de negocio sin implementar, se indica también la diferencia que debe evaluarse frente a la consigna.

## Preparación

- Usar una base de datos y un servidor **de prueba**, separados de producción. Los casos crean, modifican y eliminan registros.
- Preparar un usuario `ADMIN`, dos clientes `CLIENTE_A` y `CLIENTE_B`, una categoría y un producto disponible de precio `100.00` con stock `5`. Preparar un pedido pendiente perteneciente a B para el caso de acceso ajeno.
- Configurar `{{base}}` con la URL del servidor de prueba. Guardar como variables los identificadores `{{categoria}}`, `{{producto}}`, `{{stock}}`, `{{pedidoA}}` y `{{pedidoB}}` según corresponda. Todos los endpoints de las tablas son relativos a `{{base}}`.
- Usar JSON y `Content-Type: application/json` en las solicitudes con cuerpo. Tras el login, enviar `Authorization: Bearer {{access}}`; en el caso sin token, quitar ese encabezado.
- Los casos son independientes salvo que se indique una secuencia. Para el CRUD de ADMIN crear un producto separado, sin ítems de pedido asociados, guardar su ID como `{{productoCRUD}}` y eliminarlo después de probar los intentos del cliente. No usar ese producto para el flujo final.
- Para los casos de registro, utilizar un username nuevo por ejecución y un email previamente registrado. En el flujo final usar el producto de precio `100.00` y stock `5`, un carrito inicialmente vacío y un pedido nuevo.

## 1. Autenticación y acceso

| ID | Endpoint | Rol | Acción | Datos de entrada | Resultado esperado | Resultado obtenido | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AUTH-01 | `GET /api/auth/profile/` | CLIENTE_A | Acceder con JWT válido | Bearer `{{access}}` obtenido con FLUJO-01 | `200`; devuelve el perfil de A sin contraseña | PENDIENTE | NO EJECUTADO |
| AUTH-02 | `GET /api/auth/profile/` | Sin autenticar | Acceder sin token | Sin encabezado Authorization | `401` | PENDIENTE | NO EJECUTADO |

## 2. CRUD de productos y permisos por rol

Ejecutar PROD-01 a PROD-07 en orden. Para las operaciones ADMIN usar un token de un usuario con rol `ADMIN`; para PROD-04 a PROD-06 cambiar al token de `CLIENTE_A`.

| ID | Endpoint | Rol | Acción | Datos de entrada | Resultado esperado | Resultado obtenido | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PROD-01 | `POST /api/productos/` | ADMIN | Crear producto | `{"nombre":"Docena QA","precio":"100.00","categoria":{{categoria}}}` | `201`; guardar el ID como `{{productoCRUD}}` | PENDIENTE | NO EJECUTADO |
| PROD-02 | `GET /api/productos/{{productoCRUD}}/` | ADMIN | Consultar producto | Sin cuerpo | `200`; devuelve nombre, precio y categoría creados | PENDIENTE | NO EJECUTADO |
| PROD-03 | `PATCH /api/productos/{{productoCRUD}}/` | ADMIN | Editar producto | `{"precio":"120.00"}` | `200`; precio actualizado a `120.00` | PENDIENTE | NO EJECUTADO |
| PROD-04 | `POST /api/productos/` | CLIENTE_A | Intentar crear producto | `{"nombre":"No permitido","precio":"100.00","categoria":{{categoria}}}` | `403`; no se crea el producto | PENDIENTE | NO EJECUTADO |
| PROD-05 | `PATCH /api/productos/{{productoCRUD}}/` | CLIENTE_A | Intentar editar producto | `{"precio":"1.00"}` | `403`; el precio continúa en `120.00` | PENDIENTE | NO EJECUTADO |
| PROD-06 | `DELETE /api/productos/{{productoCRUD}}/` | CLIENTE_A | Intentar eliminar producto | Sin cuerpo | `403`; el producto sigue existiendo | PENDIENTE | NO EJECUTADO |
| PROD-07 | `DELETE /api/productos/{{productoCRUD}}/` | ADMIN | Eliminar producto | Sin cuerpo; producto sin referencias de pedido | `204`; el producto se elimina | PENDIENTE | NO EJECUTADO |

## 3. Reglas de negocio y seguridad

Los resultados de RN-01 a RN-03 representan **brechas detectadas en el código**, no una confirmación de cumplimiento de la consigna. Ejecutarlos con datos independientes del flujo final.

| ID | Endpoint | Rol | Acción | Datos de entrada | Resultado esperado | Resultado obtenido | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RN-01 | `POST /api/items-pedido/` | CLIENTE_A | Intentar registrar una cantidad superior al stock | Pedido propio pendiente, stock `5`; `{"pedido":{{pedidoA}},"producto":{{producto}},"cantidad":6}` | Según el código actual, `201`: no valida ni descuenta stock. Si la consigna exige rechazar stock insuficiente, esa validación falta. | PENDIENTE | NO EJECUTADO |
| RN-02 | `POST /api/pedidos/` | CLIENTE_A | Crear pedido con carrito vacío | Carrito vacío; `{"direccion_entrega":"Calle QA 123"}` | Según el código actual, `201`: se crea un pedido pendiente con total `0`; no comprueba el carrito. Si la consigna exige rechazarlo, falta esa validación. | PENDIENTE | NO EJECUTADO |
| RN-03 | `POST /api/auth/register/` | Sin autenticar | Registrar email duplicado | `{"username":"qa_otro","email":"ya-registrado@example.com","password":"ClaveSegura99!","password_confirm":"ClaveSegura99!"}`; username nuevo y email ya existente | Según el código actual, `201`: no se exige unicidad de email. Si la consigna exige rechazarlo, falta esa validación. | PENDIENTE | NO EJECUTADO |
| RN-04 | `GET /api/pedidos/{{pedidoB}}/` | CLIENTE_A | Consultar pedido ajeno | Sin cuerpo; ID existente que pertenece a B | `403`; no devuelve el pedido | PENDIENTE | NO EJECUTADO |

## 4. Flujo disponible y verificación de stock

Ejecutar los pasos en orden con `CLIENTE_A`. Este recorrido crea un pedido y su detalle **manualmente**: no equivale a una compra completada porque no existe checkout. Guardar el token y los IDs devueltos. Antes de FLUJO-05 comprobar que el pedido creado en FLUJO-04 no tenga ítems, para que su total esperado sea `200.00`.

| ID | Endpoint | Rol | Acción | Datos de entrada | Resultado esperado | Resultado obtenido | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FLUJO-01 | `POST /api/auth/login/` | Sin autenticar | Iniciar sesión con JWT | `{"username":"{{usuarioA}}","password":"{{claveA}}"}`; credenciales de prueba válidas | `200`; devuelve `access` y `refresh`; guardar `access` | PENDIENTE | NO EJECUTADO |
| FLUJO-02 | `GET /api/productos/` | CLIENTE_A | Consultar productos | Bearer de A; sin cuerpo | `200`; identificar y guardar `{{producto}}` de precio `100.00` | PENDIENTE | NO EJECUTADO |
| FLUJO-03 | `POST /api/items-carrito/` | CLIENTE_A | Agregar al carrito | Carrito sin ese producto; `{"producto":{{producto}},"cantidad":2}` | `201`; crea el ítem y asocia el carrito de A | PENDIENTE | NO EJECUTADO |
| FLUJO-04 | `POST /api/pedidos/` | CLIENTE_A | Crear pedido manual | `{"direccion_entrega":"Calle QA 123"}` | `201`; guardar `{{pedidoA}}`; estado `PENDIENTE` y total `0` | PENDIENTE | NO EJECUTADO |
| FLUJO-05 | `POST /api/items-pedido/` | CLIENTE_A | Crear detalle manual del pedido | `{"pedido":{{pedidoA}},"producto":{{producto}},"cantidad":2}` | `201`; precio unitario `100.00` | PENDIENTE | NO EJECUTADO |
| FLUJO-06 | `GET /api/pedidos/{{pedidoA}}/` | CLIENTE_A | Verificar pedido | Sin cuerpo | `200`; total `200.00` y estado `PENDIENTE` | PENDIENTE | NO EJECUTADO |
| FLUJO-07 | `GET /api/stock/{{stock}}/` | CLIENTE_A | Verificar stock final | Sin cuerpo; stock inicial preparado en `5` | `200`; según el código actual sigue en `5`: crear pedido y detalle no descuenta stock. | PENDIENTE | NO EJECUTADO |

## Funcionalidades ausentes que requieren atención

- **Checkout o compra:** no hay un endpoint que convierta el carrito en pedido, confirme una compra, vacíe el carrito o descuente stock. El flujo anterior solo ejercita los CRUD existentes; no es posible probar la compra completa hasta implementar esa operación.
- **Stock insuficiente y carrito vacío:** no hay validación que impida las operaciones de RN-01 y RN-02. Sus códigos esperados reflejan el backend actual y deben contrastarse con el requisito del TP4.
- **Email duplicado:** no hay validación de unicidad; RN-03 registra la aceptación que se infiere del código.
- **Búsqueda de productos:** existe el listado, pero no se implementó una búsqueda o filtro específico del lado del servidor. En FLUJO-02 el producto se identifica dentro del listado.
