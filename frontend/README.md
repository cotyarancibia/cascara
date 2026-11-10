# React + Vite

## TP8: conexión con la API

Configurá `VITE_API_URL` como en `.env.example` y reiniciá Vite después de cambiarla. En desarrollo, iniciá Django en `http://localhost:8000` y el frontend en `http://localhost:3000` (CORS permite ese origen). El login utiliza nombre de usuario y contraseña. El registro crea clientes en el backend.

Por la consigna educativa, el access y el refresh JWT se guardan en `localStorage` para recuperar la sesión tras recargar y permitir la rotación y el logout. Este almacenamiento es accesible a JavaScript y un ataque XSS podría robar ambos tokens; no debe asumirse apropiado para producción. Al restaurar la sesión se consulta el perfil en el backend; si el access venció, se intenta renovar una vez y se guarda el nuevo par. El logout limpia el estado local incluso cuando el servidor no confirma la revocación y muestra una advertencia en ese caso. La revocación del refresh no invalida inmediatamente el access ya emitido.

Las pestañas coordinan la sesión mediante Web Locks y el evento `storage`. Esta función requiere un navegador compatible y un contexto seguro (HTTPS o localhost); si Web Locks no está disponible se muestra un error y no se inicia la sesión. Las solicitudes tienen un límite de 10 segundos y la espera por el bloqueo, de 35 segundos. Si el navegador impide modificar `localStorage`, no puede garantizarse el borrado del token guardado: se informa el problema y no se considera autenticada la interfaz.

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
