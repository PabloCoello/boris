# Referencia de configuracion

Boris usa dos archivos de configuracion:

- **`config.yaml`** — comportamiento: modelos, umbrales, modos de interaccion
- **`.env`** — secretos: tokens, credenciales, URLs de servicios

---

## config.yaml

### assistant

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `name` | str | `"Boris"` | Nombre del asistente |
| `language` | str | `"es"` | Idioma principal |
| `wake_word` | str | `"boris"` | Palabra de activacion |
| `wake_word_model` | str | `""` | Ruta al modelo .onnx custom. Vacio = modelo pre-entrenado |
| `wake_word_threshold` | float | `0.5` | Umbral de deteccion (0.0-1.0). Mas bajo = mas sensible |
| `summon_phrase` | str | `"manifestate"` | Frase para entrar en modo convocado |
| `dismiss_phrase` | str | `"eso es todo"` | Frase para salir del modo convocado |
| `summon_timeout_s` | int | `120` | Segundos de inactividad para auto-desconvocar |
| `follow_up_timeout_s` | int | `10` | Segundos de espera para follow-up en modo comando |

### stt

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `model` | str | `"large-v3"` | Modelo de faster-whisper. Opciones: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `language` | str | `"es"` | Idioma de transcripcion |
| `device` | str | `"cuda"` | Dispositivo: `cuda` (GPU) o `cpu` |

**Nota:** `small` en CPU tarda ~300ms, `large-v3` en GPU ~200ms pero consume VRAM. Para empezar, `small` + `cpu` es suficiente.

### tts

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `model` | str | `"xtts_v2"` | Motor TTS. `vits_es` (rapido, ~300ms) o `xtts_v2` (clonado, ~2s) |
| `language` | str | `"es"` | Idioma de sintesis |
| `speaker_wav` | str | `"data/audio/reference.wav"` | Audio de referencia para clonado (solo xtts_v2) |
| `pitch_semitones` | float | `0.0` | Ajuste de tono. Negativo = voz mas grave. `-3` recomendado para Boris |

### llm

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `model` | str | `"gemma4-26b"` | Modelo Ollama. `gemma3:12b` (~7GB, rapido) o `gemma4-26b` (~18GB, mejor) |
| `temperature` | float | `0.7` | Creatividad (0.0-1.0). 0.7 es buen balance para conversacion |
| `max_tokens` | int | `512` | Tokens maximos por respuesta |

### audio

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `input_device_name` | str\|null | `null` | Nombre del microfono (busqueda parcial). Null = default del sistema |
| `feedback_sounds` | bool | `true` | Habilitar beeps y chimes de feedback |
| `feedback_volume` | float | `0.7` | Volumen de feedback sounds (0.0-1.0) |

**Para encontrar el nombre de tu microfono:**
```bash
uv run python -c "
import sounddevice as sd
for d in sd.query_devices():
    if d['max_input_channels'] > 0:
        print(f\"  {d['name']}\")
"
```

### memory

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `profile_max_tokens` | int | `800` | Tokens maximos para profile.md en el system prompt |
| `index_max_tokens` | int | `400` | Tokens maximos para index.md en el system prompt |
| `data_dir` | str | `"data/memory"` | Directorio de memoria persistente |

### skills

#### skills.home

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `enabled` | bool | `false` | Habilitar skill de Home Assistant |

#### skills.garmin

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `enabled` | bool | `true` | Habilitar skill de Garmin Connect |

#### skills.music

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `backend` | str | `"spotify"` | Backend de musica (actualmente solo Spotify) |

#### skills.search

| Campo | Tipo | Default | Descripcion |
|---|---|---|---|
| `url` | str | `"http://localhost:8080"` | URL de SearXNG. Vacio = skill deshabilitado |

---

## .env

Secretos que nunca deben estar en git. Copiar de `.env.example`:

```bash
cp .env.example .env
```

| Variable | Descripcion | Donde obtenerla |
|---|---|---|
| `OLLAMA_HOST` | URL del servidor Ollama | Default: `http://localhost:11434` |
| `HA_URL` | URL de Home Assistant | Tu instancia HA (ej: `http://homeassistant.local:8123`) |
| `HA_TOKEN` | Token de acceso de HA | HA > Perfil > Tokens de acceso de larga duracion |
| `GARMIN_EMAIL` | Email de Garmin Connect | Tu cuenta Garmin |
| `GARMIN_PASSWORD` | Password de Garmin Connect | Tu cuenta Garmin |
| `SPOTIFY_CLIENT_ID` | Client ID de Spotify | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| `SPOTIFY_CLIENT_SECRET` | Client Secret de Spotify | Misma app de Spotify Developer |
| `GOOGLE_CREDENTIALS_JSON` | Ruta al JSON de credenciales OAuth | Google Cloud Console > APIs > Credentials |

---

## Que pasa si falta cada variable

| Variable ausente | Efecto |
|---|---|
| `OLLAMA_HOST` | Usa default `localhost:11434`. Si Ollama no esta corriendo, Boris no arranca |
| `HA_URL` + `HA_TOKEN` | Skill `home` no se registra |
| `GARMIN_EMAIL` + `GARMIN_PASSWORD` | Skill `garmin` no se registra |
| `SPOTIFY_CLIENT_ID` + `SECRET` | Skills `music_play` y `music_control` no se registran |
| `GOOGLE_CREDENTIALS_JSON` | Skill `calendar` no se registra |

Boris funciona en modo conversacional basico solo con Ollama. Todas las skills externas son opcionales.

---

## Ejemplo minimo de config.yaml

```yaml
assistant:
  wake_word: boris
  wake_word_model: data/models/boris_wakeword.onnx
  wake_word_threshold: 0.3
  summon_phrase: "manifestate"
  dismiss_phrase: "eso es todo"
  summon_timeout_s: 120
  follow_up_timeout_s: 10

audio:
  input_device_name: Razer Seiren X
  feedback_sounds: true
  feedback_volume: 0.3

stt:
  model: small
  language: es
  device: cpu

tts:
  model: vits_es
  language: es
  pitch_semitones: -3

llm:
  model: gemma3:12b
  temperature: 0.7
  max_tokens: 256

memory:
  profile_max_tokens: 800
  index_max_tokens: 400
  data_dir: data/memory

skills:
  home:
    enabled: false
  garmin:
    enabled: true
  music:
    backend: spotify
  search:
    url: http://localhost:8080
```

## Ejemplo minimo de .env

```bash
OLLAMA_HOST=http://localhost:11434
HA_URL=
HA_TOKEN=
GARMIN_EMAIL=tu_email@garmin.com
GARMIN_PASSWORD=tu_password
SPOTIFY_CLIENT_ID=abc123
SPOTIFY_CLIENT_SECRET=xyz789
GOOGLE_CREDENTIALS_JSON=data/google-credentials.json
```
