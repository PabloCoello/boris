# Configuración OAuth — Google Calendar

Boris usa Google Calendar como fuente única de eventos. Si tienes calendarios en Outlook u otros servicios, sincronízalos con Google Calendar primero (Outlook > Settings > Shared calendars > Publish > copiar enlace ICS > añadir en Google Calendar como "From URL").

## 1. Crear proyecto en Google Cloud Console

1. Ir a https://console.cloud.google.com/
2. Crear un proyecto nuevo (o usar uno existente)
3. Nombre sugerido: `boris-assistant`

## 2. Habilitar la API de Google Calendar

1. Ir a **APIs & Services > Library**
2. Buscar "Google Calendar API"
3. Click en **Enable**

## 3. Configurar pantalla de consentimiento OAuth

1. Ir a **APIs & Services > OAuth consent screen**
2. Seleccionar **External** (no importa, solo lo usarás tú)
3. Rellenar:
   - App name: `Boris`
   - User support email: tu email
   - Developer contact: tu email
4. En **Scopes**, añadir:
   - `https://www.googleapis.com/auth/calendar.readonly`
5. En **Test users**, añadir tu cuenta de Gmail
6. Guardar

## 4. Crear credenciales OAuth

1. Ir a **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Nombre: `boris-desktop`
5. Click **Create**
6. Descargar el JSON — guardarlo como `data/google-credentials.json`

## 5. Configurar en Boris

Añadir a `.env`:

```
GOOGLE_CREDENTIALS_JSON=data/google-credentials.json
```

## 6. Primera autenticación

Ejecutar una vez para autorizar el acceso:

```bash
uv run python -m boris.skills.calendar --auth
```

Se abrirá un navegador para autorizar. El token se guarda en `data/google-token.json` y se renueva automáticamente.

## Verificación

```bash
# Comprobar que las variables están en .env
grep GOOGLE_CREDENTIALS .env

# Verificar que el archivo de credenciales existe
ls -la data/google-credentials.json
```

## Troubleshooting

| Problema | Solución |
|---|---|
| "Access blocked: app not verified" | Normal para apps en modo test. Click **Continue** — solo tú usarás la app. |
| Token expirado | Se renueva automáticamente con el refresh token. Si falla, borrar `data/google-token.json` y repetir paso 6. |
| "This app isn't verified" | Ir a OAuth consent screen > añadir tu email como test user. |

## Seguridad

- **Nunca commitear** `data/google-credentials.json`, `data/google-token.json`, ni `.env`
- Estos archivos ya están en `.gitignore`
- Los tokens dan acceso de lectura a tu calendario — tratar como contraseñas
