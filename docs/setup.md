# Guía de instalación — Boris

Esta guía cubre la instalación completa de Boris y todos sus servicios, **excepto Home Assistant** (que se documenta aparte).

## Requisitos previos

| Componente | Mínimo | Recomendado |
|---|---|---|
| OS | Ubuntu 22.04 | Ubuntu 24.04 LTS |
| GPU | NVIDIA con ≥16 GB VRAM | RTX 3090 (24 GB) |
| CUDA | 12.x | 12.x |
| Python | 3.11 | 3.11 |
| RAM | 16 GB | 32 GB |
| Micrófono | Cualquiera USB | Razer Seiren X o similar condensador |
| Altavoz | Cualquiera | — |

Verificar requisitos:

```bash
nvidia-smi                          # GPU detectada y VRAM
nvcc --version                      # CUDA 12.x
python3 --version                   # 3.11+
```

---

## 1. Clonar el repositorio

```bash
cd ~/Documentos/GitHub
git clone <url-del-repo> boris
cd boris
```

---

## 2. Instalar uv (gestor de paquetes)

Si no lo tienes:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Instalar dependencias del proyecto:

```bash
uv sync --all-extras
```

Verificar:

```bash
uv run python -c "import boris; print('OK')"
```

---

## 3. Ollama + modelo LLM

### Instalar Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Verificar que el servicio está corriendo:

```bash
systemctl status ollama
# o
curl http://localhost:11434/api/version
```

### Descargar modelo

**Opción A** — Directamente desde Ollama (si la red lo permite):

```bash
ollama pull gemma3:12b      # ~7 GB, rápido, bueno para empezar
# o
ollama pull gemma4-26b      # ~18 GB, mejor calidad, necesita más VRAM
```

**Opción B** — Desde Hugging Face (si Ollama pull falla por red):

```bash
pip install huggingface-hub
hf download bartowski/google_gemma-4-26B-A4B-it-GGUF \
  --include "google_gemma-4-26B-A4B-it-Q4_K_M.gguf" \
  --local-dir ~/models/gemma4

echo "FROM ~/models/gemma4/google_gemma-4-26B-A4B-it-Q4_K_M.gguf" > ~/models/Modelfile
ollama create gemma4-26b -f ~/models/Modelfile
```

Verificar:

```bash
ollama list                                        # modelo aparece en la lista
ollama run gemma3:12b "Hola, ¿cómo estás?"        # respuesta coherente en español
```

### Elegir modelo en config.yaml

Editar `config.yaml`:

```yaml
llm:
  model: gemma3:12b       # o gemma4-26b si tienes VRAM suficiente
  temperature: 0.7
  max_tokens: 256
```

---

## 4. Audio — Micrófono y altavoz

### Detectar dispositivos

```bash
uv run python -c "
import sounddevice as sd
print('=== Entrada ===')
for d in sd.query_devices():
    if d['max_input_channels'] > 0:
        print(f\"  [{d['index']}] {d['name']}\")
print()
print('=== Salida ===')
for d in sd.query_devices():
    if d['max_output_channels'] > 0:
        print(f\"  [{d['index']}] {d['name']}\")
"
```

### Configurar micrófono en config.yaml

Si el micrófono no es el dispositivo por defecto, especificarlo:

```yaml
audio:
  input_device_name: "Razer Seiren X"    # nombre parcial, se busca por coincidencia
  feedback_sounds: true                   # beeps y chimes de feedback
  feedback_volume: 0.7                    # volumen de los feedback sounds (0.0-1.0)
```

> **Nota sobre PipeWire:** Si el micrófono aparece en `arecord -l` pero no en sounddevice con canales de entrada (`in=0`), puede ser un problema de PipeWire. Intentar: `systemctl --user restart wireplumber` o verificar el perfil del dispositivo con `wpctl status`.

### Test rápido de audio

```bash
# Grabar 3 segundos y reproducir
uv run python -c "
import sounddevice as sd
import numpy as np
print('Grabando 3 segundos...')
audio = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()
print('Reproduciendo...')
sd.play(audio, samplerate=16000)
sd.wait()
print('OK')
"
```

---

## 5. SearXNG (búsqueda web local)

Boris usa [SearXNG](https://github.com/searxng/searxng) como motor de búsqueda local. Es opcional — sin él, la skill `search` simplemente no se registra.

### Instalar con Docker

> **Docker Desktop vs daemon del sistema:** En Ubuntu pueden coexistir dos daemons Docker (el del sistema vía `apt` y Docker Desktop). Si usas Docker Desktop, asegúrate de que es el único instalado para evitar confusión. Para eliminar el daemon del sistema: `sudo apt purge docker-ce docker-ce-cli containerd.io && sudo rm -rf /var/lib/docker /var/lib/containerd`.

```bash
docker run -d \
  --name searxng \
  -p 8080:8080 \
  -e SEARXNG_SECRET=$(openssl rand -hex 32) \
  searxng/searxng:latest
```

### Habilitar formato JSON

SearXNG no devuelve JSON por defecto. Hay que habilitarlo:

```bash
# Entrar al contenedor
docker exec -it searxng sh

# Editar settings
vi /etc/searxng/settings.yml
```

Buscar la sección `search:` y asegurar que `formats` incluya `json`:

```yaml
search:
  formats:
    - html
    - json
```

Reiniciar:

```bash
docker restart searxng
```

### Verificar

```bash
curl "http://localhost:8080/search?q=test&format=json" | python3 -m json.tool | head -20
```

### Configurar en config.yaml

```yaml
skills:
  search:
    url: http://localhost:8080
```

Si no quieres SearXNG, deja `url:` vacío y la skill no se registrará.

---

## 6. Spotify

Boris controla Spotify vía la API oficial. Necesitas una cuenta **Premium** (la API no permite controlar reproducción en cuentas gratuitas).

### Crear app en Spotify Developer

1. Ir a https://developer.spotify.com/dashboard
2. Click **Create app**
3. Rellenar:
   - App name: `Boris`
   - App description: `Asistente de voz`
   - Redirect URI: `http://127.0.0.1:8888/callback`
4. Click **Create**
5. Ir a **Settings** y copiar:
   - **Client ID**
   - **Client Secret** (click "View client secret")

### Configurar en .env

```bash
SPOTIFY_CLIENT_ID=tu_client_id_aqui
SPOTIFY_CLIENT_SECRET=tu_client_secret_aqui
```

### Primera autenticación

La primera vez que Boris use Spotify, se abrirá un navegador para autorizar. El token se guarda en `.cache` (ya está en `.gitignore`).

Para forzar la autenticación manualmente:

```bash
uv run python -c "
import spotipy
from spotipy.oauth2 import SpotifyOAuth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id='TU_CLIENT_ID',
    client_secret='TU_CLIENT_SECRET',
    redirect_uri='http://127.0.0.1:8888/callback',
    scope='user-modify-playback-state user-read-playback-state',
))
print(sp.current_user()['display_name'])
"
```

### Dispositivo de reproducción

La API de Spotify necesita un **dispositivo activo** para reproducir. Opciones:

- **Opción A** — Abrir Spotify en cualquier dispositivo (app móvil, web player, app de escritorio). Solo necesita estar abierto.
- **Opción B** — Instalar `spotifyd` (daemon sin GUI, ideal para que el PC actúe como altavoz):

```bash
# Descargar binario
wget https://github.com/Spotifyd/spotifyd/releases/latest/download/spotifyd-linux-full.tar.gz
tar xzf spotifyd-linux-full.tar.gz
sudo mv spotifyd /usr/local/bin/
sudo chmod +x /usr/local/bin/spotifyd
rm spotifyd-linux-full.tar.gz

# Configurar
mkdir -p ~/.config/spotifyd
cat > ~/.config/spotifyd/spotifyd.conf << 'EOF'
[global]
username = "TU_USUARIO_SPOTIFY"
password = "TU_PASSWORD_SPOTIFY"
backend = "pulseaudio"
device_name = "Boris"
bitrate = 320
device_type = "computer"
EOF

# Crear servicio systemd
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/spotifyd.service << 'EOF'
[Unit]
Description=Spotifyd - Spotify daemon
After=network-online.target pulseaudio.service

[Service]
ExecStart=/usr/local/bin/spotifyd --no-daemon
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# Arrancar y habilitar al inicio
systemctl --user daemon-reload
systemctl --user enable spotifyd
systemctl --user start spotifyd
systemctl --user status spotifyd
```

> **Nota:** Si usas login con Google/Facebook en Spotify, necesitas crear una "device password" en tu cuenta (Settings > Set device password).

### Verificar

Asegurar que Spotify está reproduciendo en algún dispositivo (móvil, desktop, web, o spotifyd) y probar:

```bash
uv run python -c "
import spotipy
from spotipy.oauth2 import SpotifyOAuth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id='TU_CLIENT_ID',
    client_secret='TU_CLIENT_SECRET',
    redirect_uri='http://127.0.0.1:8888/callback',
    scope='user-modify-playback-state user-read-playback-state',
))
devices = sp.devices()
print('Dispositivos:', [d['name'] for d in devices['devices']])
"
```

---

## 7. Google Calendar

Ver [docs/oauth-setup.md](oauth-setup.md) para las instrucciones detalladas de OAuth.

Resumen rápido:

1. Crear proyecto en Google Cloud Console
2. Habilitar Google Calendar API
3. Crear credenciales OAuth (Desktop app)
4. Descargar JSON → `data/google-credentials.json`
5. Configurar en `.env`:
   ```
   GOOGLE_CREDENTIALS_JSON=data/google-credentials.json
   ```
6. Autenticar:
   ```bash
   uv run python -m boris.skills.calendar --auth
   ```

### Sincronizar otros calendarios

Si tienes calendarios en Outlook u otros servicios, sincronízalos con Google Calendar:

- **Outlook**: Settings > Shared calendars > Publish > copiar enlace ICS > añadir en Google Calendar como "From URL"
- **Apple Calendar**: similar — exportar ICS o publicar y añadir en Google Calendar

---

## 8. Garmin Connect

Boris lee datos de salud (sueño, pasos, HRV, body battery, actividades) desde Garmin Connect. Solo necesitas tu email y contraseña de Garmin.

### Configurar en .env

```bash
GARMIN_EMAIL=tu_email@ejemplo.com
GARMIN_PASSWORD=tu_contraseña_garmin
```

### Habilitar en config.yaml

```yaml
skills:
  garmin:
    enabled: true
```

### Aplicar parche de login widget (necesario si Cloudflare bloquea)

La librería `garminconnect` usa endpoints de login que Cloudflare puede bloquear con 429/403. Existe un [PR pendiente (#345)](https://github.com/cyberjunky/python-garminconnect/pull/345) que añade una estrategia alternativa usando el widget SSO embed (`/sso/embed`), que no requiere `clientId` y por tanto no está sujeta al rate limit por cliente.

**Mientras el PR no se mergee upstream**, hay que aplicar el parche manualmente sobre el `client.py` instalado en el `.venv`:

```bash
# 1. Localizar el fichero
GARMIN_CLIENT=$(uv run python -c "import garminconnect; print(garminconnect.__path__[0])")/client.py
echo "Fichero: $GARMIN_CLIENT"

# 2. Aplicar el parche (sustituye el fichero con la versión parcheada del repo)
cp patches/garminconnect_client.py "$GARMIN_CLIENT"

# 3. Verificar que el endpoint widget responde
uv run python -c "
from curl_cffi import requests as cffi_requests
import re
sess = cffi_requests.Session(impersonate='safari')
r = sess.get('https://sso.garmin.com/sso/embed', timeout=30)
print(f'Embed: {r.status_code}')
r2 = sess.get('https://sso.garmin.com/sso/signin', params={
    'id': 'gauth-widget', 'embedWidget': 'true',
    'gauthHost': 'https://sso.garmin.com'
}, timeout=30)
print(f'Signin: {r2.status_code}')
csrf = re.search(r'name=\"_csrf\"\s+value=\"([^\"]+)\"', r2.text)
print(f'CSRF token encontrado: {bool(csrf)}')
"
```

Los tres checks deben dar `200`, `200`, `True`. Si el parche ya está incluido en una versión futura de `garminconnect`, este paso se puede omitir.

> **Importante:** El parche se pierde al ejecutar `uv sync`. Tras actualizar dependencias, re-aplicar con `cp patches/garminconnect_client.py "$GARMIN_CLIENT"`.

### Primera autenticación (generar tokens)

Boris cachea la sesión de Garmin en `data/garmin-tokens/` para evitar hacer login en cada petición. **La primera vez** necesitas generar los tokens manualmente:

```bash
uv run python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

from garminconnect import Garmin
from pathlib import Path

tokenstore = 'data/garmin-tokens'
Path(tokenstore).mkdir(parents=True, exist_ok=True)

client = Garmin('TU_EMAIL', 'TU_PASSWORD')
client.login(tokenstore=tokenstore)
client.client.dump(tokenstore)
print('Login OK — tokens guardados en', tokenstore)

from datetime import date
steps = client.get_stats(date.today().isoformat())
print(f\"Pasos hoy: {steps.get('totalSteps', 0)}\")
"
```

En los logs de debug deberías ver `Trying login strategy: widget+cffi` como primer intento. Si todo va bien:

```
Login OK — tokens guardados en data/garmin-tokens
Pasos hoy: 8432
```

Con MFA:

```bash
uv run python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

from garminconnect import Garmin
from pathlib import Path

tokenstore = 'data/garmin-tokens'
Path(tokenstore).mkdir(parents=True, exist_ok=True)

client = Garmin('EMAIL', 'pass', prompt_mfa=lambda: input('Código MFA: '))
client.login(tokenstore=tokenstore)
client.client.dump(tokenstore)
print('Login OK — tokens guardados')

from datetime import date
steps = client.get_stats(date.today().isoformat())
print(f\"Pasos hoy: {steps.get('totalSteps', 0)}\")
"
```



Si falla con 429 en todas las estrategias, espera 5-10 minutos y reintenta (Cloudflare tiene un cooldown).



### Verificar que Boris puede usar los tokens

Una vez generados los tokens, este comando debe funcionar **sin hacer login de nuevo** (usa los tokens cacheados):

```bash
uv run python -c "
from garminconnect import Garmin
client = Garmin('TU_EMAIL', 'TU_PASSWORD')
client.login(tokenstore='data/garmin-tokens')
from datetime import date
sleep = client.get_sleep_data(date.today().isoformat())
mins = sleep.get('dailySleepDTO', {}).get('sleepTimeSeconds', 0) // 60
print(f'{mins} minutos de sueño')
"
```

### Renovar tokens si expiran

Los tokens duran aproximadamente un año. Si Boris empieza a fallar con errores de autenticación:

```bash
# Borrar tokens viejos y regenerar
rm -rf data/garmin-tokens/*
# Ejecutar de nuevo el script de "Primera autenticación"
```

### Notas

- Garmin no tiene OAuth público — usa usuario/contraseña directamente
- Los tokens se guardan en `data/garmin-tokens/` y se reutilizan automáticamente
- Si la sesión expira durante el uso, Boris reintenta login una vez con los tokens cacheados
- La estrategia `widget+cffi` (del parche) evita el bloqueo de Cloudflare al no usar `clientId`
- `curl_cffi` es necesario para el parche — viene como dependencia transitiva de `garminconnect`
- Si tienes MFA habilitado en Garmin, el parche lo soporta vía el flujo widget (TOTP)

---

## 9. Archivo .env completo

Copiar `.env.example` y rellenar:

```bash
cp .env.example .env
```

Contenido esperado:

```bash
OLLAMA_HOST=http://localhost:11434
HA_URL=                                          # dejar vacío hasta instalar HA
HA_TOKEN=                                        # dejar vacío hasta instalar HA
GARMIN_EMAIL=tu_email@garmin.com
GARMIN_PASSWORD=tu_contraseña
SPOTIFY_CLIENT_ID=abc123...
SPOTIFY_CLIENT_SECRET=xyz789...
GOOGLE_CREDENTIALS_JSON=data/google-credentials.json
```

---

## 10. Diagnóstico completo

Ejecutar el diagnóstico integrado de Boris:

```bash
uv run python -m boris.diag
```

Salida esperada:

```
=== Boris — Diagnóstico ===

[GPU]
  GPU: NVIDIA GeForce RTX 3090, 24576 MiB, 22000 MiB
[Ollama]
  Ollama: conectado, 1 modelo(s)
    - gemma3:12b
[Micrófono]
  Micrófono: 3 dispositivo(s) de entrada
    Default: Razer Seiren X
[Altavoz]
  Altavoz: 5 dispositivo(s) de salida
    Default: Built-in Audio

=== Resumen ===
  GPU: OK
  Ollama: OK
  Micrófono: OK
  Altavoz: OK

Todo en orden, mi señor.
```

---

## 11. Arrancar Boris

### Con run.sh (recomendado)

```bash
bash run.sh
```

`run.sh` ejecuta pre-flight checks antes de arrancar:
- Verifica que Ollama está corriendo y el modelo LLM está disponible
- Comprueba SearXNG (intenta arrancar el container si existe)
- Verifica PipeWire y el micrófono configurado
- Comprueba que `.env` existe
- Verifica que el modelo de wake word existe

Si todo está en orden, lanza Boris automáticamente.

### Manual

```bash
uv run python -m boris
```

### Parar Boris

```bash
bash stop.sh
```

`stop.sh` envía SIGINT (Ctrl+C), lo que permite a Boris guardar la memoria episódica antes de salir. Si no responde en 5 segundos, fuerza la parada con SIGKILL.

### Modos de interacción

Boris tiene dos modos:

**Modo Comando** — una frase, una respuesta:
- "Boris, pon jazz" → beep + "Jazz activado" + idle
- "Boris, qué hora es" → responde + idle

**Modo Convocado** — conversación libre sin wake word:
- "Boris, manifiéstate" → chime + saludo → Boris escucha sin necesidad de wake word
- Hablas directamente → Boris responde
- "Eso es todo Boris" → despedida + idle
- Se auto-desconvoca tras 2 minutos de silencio

Configuración relevante en `config.yaml`:
```yaml
assistant:
  summon_phrase: "manifiéstate"      # frase para entrar en modo convocado
  dismiss_phrase: "eso es todo"      # frase para salir
  summon_timeout_s: 120              # auto-desconvocar tras 2 min silencio
  follow_up_timeout_s: 10           # espera respuesta en modo comando (si Boris pregunta)
```

### Ejemplos

- "Boris, ¿qué hora es?"
- "Boris, ponme un recordatorio para mañana a las 10"
- "Boris, ¿qué tengo en el calendario esta semana?"
- "Boris, pon música de Rosalía"
- "Boris, ¿cómo dormí anoche?"
- "Boris, busca cuántos habitantes tiene Asturias"
- "Boris, manifiéstate" → conversación libre

---

## Troubleshooting

| Problema | Solución |
|---|---|
| `uv sync` falla con error de torch | Asegurar CUDA 12.x instalado y `nvidia-smi` funciona |
| Ollama no responde | `systemctl restart ollama` y verificar `curl localhost:11434` |
| Micrófono no detectado | `arecord -l` para listar dispositivos ALSA; instalar `pulseaudio` si falta |
| Boris no escucha el wake word | Verificar `audio.input_device_name` en config.yaml |
| Spotify "No active device" | Abrir Spotify en algún dispositivo antes de pedir música |
| Google Calendar "Access blocked" | Añadir tu email como test user en OAuth consent screen |
| Garmin login falla | Verificar credenciales; si tienes MFA, ver docs de garminconnect |
| VRAM insuficiente | Cambiar a `gemma3:12b` y/o `stt.model: small` en config.yaml |
| Boris se activa con su propia voz | Echo cancel debería prevenirlo; verificar que TTS funciona correctamente |
| "Manifiéstate" no activa modo convocado | Whisper puede transcribir sin tildes. Verificar logs — la comparación es accent-insensitive |
| No se escuchan los beeps de feedback | Verificar `audio.feedback_volume` en config.yaml (0.7 recomendado) y que la salida de audio es correcta |
| Micrófono aparece con `in=0` en sounddevice | PipeWire no expone el input. Probar `systemctl --user restart wireplumber` |
| Error "Device or resource busy" al arrancar | Hay otro proceso Boris corriendo. Ejecutar `bash stop.sh` primero |

---

## Servicios opcionales — resumen

| Servicio | Variable .env | Qué pasa si falta |
|---|---|---|
| Ollama | `OLLAMA_HOST` | Boris no arranca (es obligatorio) |
| SearXNG | `skills.search.url` en config.yaml | Skill `search` no se registra |
| Spotify | `SPOTIFY_CLIENT_ID` + `SECRET` | Skills `music_play` y `music_control` no se registran |
| Google Calendar | `GOOGLE_CREDENTIALS_JSON` | Skill `calendar` no se registra |
| Garmin | `GARMIN_EMAIL` + `PASSWORD` | Skill `garmin` no se registra |
| Home Assistant | `HA_URL` + `HA_TOKEN` | Skill `home` no se registra (Fase 4) |

Todas las skills son opcionales excepto reminders (siempre activo). Boris funciona en modo conversacional básico sin ningún servicio externo — solo necesita Ollama.
