```
                    ___
                   /   \
                  | o o |
                  |  ^  |
                  | \_/ |
               ___\     /___
              /   |`---'|   \
             /    |     |    \
            |  B  |  O  |  R  |  I  |  S  |
             \    |     |    /
              \___|     |___/
                  |     |
                 /|     |\
                / |     | \
               /  |     |  \
              '   |_____|   '
         5000 anos a su servicio
```

# Boris

**Asistente de voz local con personalidad de mayordomo milenario.**

Boris es un asistente de voz personal que corre 100% en local sobre una GPU NVIDIA. Escucha por wake word, entiende espanol, controla el hogar, gestiona calendario y musica, consulta datos de salud, y acumula memoria sobre su senor. Todo con el tono cortes pero siniestro de un mayordomo que lleva 5000 anos sirviendo sin ser ejecutado.

---

## Demo

```
 Tu:    "Boris, pon jazz"
Boris:  beep  "Jazz activado, mi senor."

 Tu:    "Boris, como dormi anoche"
Boris:  "7 horas y 12 minutos. Body battery al 80%.
         Noche reparadora, diria yo."

 Tu:    "Boris, manifestate"
Boris:  chime  "A sus ordenes, mi senor."

 Tu:    "Que tengo manana en el calendario"
Boris:  "Dos reuniones. Standup a las 9 y revision de sprint a las 15."

 Tu:    "Pon algo de musica tranquila"
Boris:  beep  "Ambiente tranquilo activado."

 Tu:    "Eso es todo Boris"
Boris:  chime  "Me retiro, mi senor."
```

---

## Que es Boris

- **Local-first**: STT, LLM y TTS corren en la maquina. Solo usa cloud para APIs de terceros (Spotify, Google Calendar, Garmin).
- **Voz como interfaz**: sin UI web ni app. Hablas, Boris escucha y responde.
- **Dos modos de interaccion**: comando rapido ("Boris pon jazz") y conversacion libre ("Boris manifestate").
- **Memoria persistente**: Boris recuerda conversaciones previas, sintetiza perfiles y acumula conocimiento.
- **Wake word personalizada**: modelo entrenado con openwakeword, optimizado para "Boris".
- **Personalidad**: mayordomo formal, eficiente, ligeramente siniestro. Nunca tutea.

---

## Arquitectura

```
  Mic ──> Wake Word ──> VAD ──> STT ──> LLM ──> Orchestrator ──> TTS ──> Speaker
          (openwakeword)  (silero) (whisper) (ollama)    |          (piper/xtts)
                                                         |
                                                    Skills
                                              (home, music, calendar,
                                               garmin, search, reminders)
                                                         |
                                                    Memory
                                              (profile, episodic, entities)
```

El pipeline completo corre en un bucle asyncio. El wake word detector captura audio en un thread dedicado; al detectar "Boris", cede el microfono al AudioListener (VAD), que graba hasta silencio. La transcripcion pasa al LLM, que decide si ejecutar un skill (JSON) o responder en texto. El resultado se sintetiza a voz y se reproduce, silenciando el microfono durante la salida (echo cancellation).

Ver [docs/architecture.md](docs/architecture.md) para detalles del pipeline, maquina de estados y protocolo de microfono.

---

## Tech Stack

| Componente | Tecnologia | Modelo / Version |
|---|---|---|
| LLM | Ollama | `gemma3:12b` / `gemma4-26b` |
| STT | faster-whisper | `small` (CPU) / `large-v3` (GPU) |
| TTS | Coqui TTS | `vits_es` (rapido) / `xtts_v2` (clonado) |
| VAD | silero-vad | ultima estable |
| Wake word | openwakeword | modelo custom `.onnx` |
| Runtime | Python 3.11 via uv | — |
| GPU | NVIDIA RTX 3090 | CUDA 12.x |
| Domotica | Home Assistant | REST API |
| Salud | garminconnect | — |
| Musica | Spotify via spotipy | cuenta Premium |
| Calendario | Google Calendar | OAuth |
| Busqueda | SearXNG | container Docker |

---

## Quick Start

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/boris.git
cd boris

# 2. Instalar dependencias
uv sync --all-extras

# 3. Instalar Ollama y descargar modelo
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:12b

# 4. Configurar secretos
cp .env.example .env
# Editar .env con tus credenciales (Spotify, Garmin, Google Calendar)

# 5. Arrancar Boris
bash run.sh
```

`run.sh` verifica automaticamente que Ollama, el modelo LLM, PipeWire, el microfono y los servicios opcionales esten en orden antes de lanzar Boris.

Para la guia de instalacion completa (cada servicio paso a paso): [docs/setup.md](docs/setup.md)

---

## Modos de interaccion

### Modo Comando

```
"Boris <frase>" ──> beep ──> procesa ──> respuesta corta ──> idle
```

Una utterance, una respuesta. Si Boris necesita clarificar ("¿Que desea escuchar?"), espera **una** respuesta sin wake word (timeout 10s).

### Modo Convocado

```
"Boris manifestate" ──> chime ──> conversacion libre ──> "Eso es todo Boris" ──> idle
```

Boris escucha continuamente sin requerir wake word entre turnos. Se desconvoca con "Eso es todo Boris" o tras 2 minutos de silencio. Al salir, guarda un resumen episodico de la conversacion.

Ver [SPEC-interaction-modes.md](SPEC-interaction-modes.md) para diagramas de flujo completos.

---

## Skills

| Skill | Descripcion | Ejemplo de voz | Requiere |
|---|---|---|---|
| `music_play` | Reproduce musica | "Boris pon jazz" | Spotify |
| `music_control` | Controla reproduccion | "Boris pausa la musica" | Spotify |
| `calendar` | Eventos proximos | "Boris que tengo manana" | Google Calendar |
| `garmin` | Datos de salud | "Boris como dormi" | Garmin Connect |
| `search` | Busqueda web | "Boris busca X" | SearXNG |
| `reminder` | Crea recordatorios | "Boris recuerdame X a las Y" | — |
| `reminders_list` | Lista recordatorios | "Boris que recordatorios tengo" | — |
| `home` | Control domotico | "Boris enciende la luz" | Home Assistant |

Todas las skills son opcionales excepto `reminder`/`reminders_list`. Boris funciona en modo conversacional basico solo con Ollama.

Ver [docs/skills.md](docs/skills.md) para referencia detallada de argumentos y configuracion.

---

## Configuracion

Boris usa dos archivos:

**`config.yaml`** — comportamiento (modelos, umbrales, modos):

```yaml
assistant:
  wake_word: boris
  summon_phrase: "manifestate"
  dismiss_phrase: "eso es todo"
  summon_timeout_s: 120

stt:
  model: small
  device: cpu

tts:
  model: vits_es
  pitch_semitones: -3

llm:
  model: gemma3:12b
  temperature: 0.7
```

**`.env`** — secretos (nunca en git):

```bash
OLLAMA_HOST=http://localhost:11434
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
GARMIN_EMAIL=...
GARMIN_PASSWORD=...
GOOGLE_CREDENTIALS_JSON=data/google-credentials.json
```

Ver [docs/configuration.md](docs/configuration.md) para referencia completa de cada campo.

---

## Estructura del proyecto

```
boris/
├── __main__.py            # Entry point
├── config.py              # Carga .env + config.yaml
├── diag.py                # Diagnostico de hardware y servicios
├── core/
│   ├── loop.py            # Bucle principal: wake -> STT -> LLM -> TTS
│   ├── orchestrator.py    # Dispatcher de tool calls (JSON del LLM)
│   ├── context.py         # System prompt + memoria + modo
│   ├── feedback.py        # Sonidos de feedback (beeps, chimes)
│   └── state.py           # InteractionMode enum + SessionState
├── stt/
│   └── whisper.py         # faster-whisper
├── tts/
│   ├── xtts.py            # Coqui TTS (vits / xtts_v2) + pitch shift
│   └── normalize.py       # Normalizacion de texto para TTS
├── llm/
│   └── ollama.py          # Cliente Ollama con streaming
├── vad/
│   └── silero.py          # VAD + grabacion con silero-vad
├── wakeword/
│   └── detector.py        # openwakeword con pause/resume
├── memory/
│   ├── loader.py          # Carga profile.md + index.md al contexto
│   ├── writer.py          # Genera episodic/ al cerrar sesion
│   └── linter.py          # Sintetiza y actualiza memoria
└── skills/
    ├── base.py            # Interfaz Skill + SkillResult
    ├── registry.py        # Registro dinamico de skills
    ├── home.py            # Home Assistant
    ├── music.py           # Spotify
    ├── calendar.py        # Google Calendar
    ├── garmin.py          # Garmin Connect
    ├── search.py          # SearXNG
    └── reminders.py       # APScheduler

data/
├── memory/                # Memoria persistente (Markdown)
│   ├── profile.md         # Perfil del usuario
│   ├── index.md           # Catalogo de la wiki
│   └── episodic/          # Una entrada por sesion/dia
├── models/                # Modelo wake word (.onnx)
└── audio/                 # Samples de voz

tests/
├── unit/                  # Tests unitarios (mocks)
└── integration/           # Tests de integracion (servicios reales)

config.yaml                # Configuracion de comportamiento
.env                       # Secretos (no en git)
run.sh                     # Pre-flight checks + arranque
stop.sh                    # Parada limpia (SIGINT -> episodic save)
```

---

## Desarrollo

```bash
# Tests
uv run pytest                                         # todos
uv run pytest tests/unit                              # unitarios
uv run pytest --cov=boris --cov-report=term-missing   # cobertura

# Lint
uv run ruff check boris/ tests/
uv run ruff format boris/ tests/

# Diagnostico
uv run python -m boris.diag

# Arrancar / parar
bash run.sh
bash stop.sh

# Memoria: linting manual
uv run python -m boris.memory.linter
```

---

## Documentacion

| Documento | Contenido |
|---|---|
| [docs/setup.md](docs/setup.md) | Guia de instalacion completa |
| [docs/architecture.md](docs/architecture.md) | Pipeline, maquina de estados, mic protocol |
| [docs/skills.md](docs/skills.md) | Referencia de skills (args, ejemplos) |
| [docs/configuration.md](docs/configuration.md) | Referencia de config.yaml y .env |
| [docs/wake-word-training.md](docs/wake-word-training.md) | Entrenamiento del modelo de wake word |
| [docs/oauth-setup.md](docs/oauth-setup.md) | OAuth de Google Calendar |
| [SPEC.md](SPEC.md) | Spec tecnica del proyecto |
| [SPEC-interaction-modes.md](SPEC-interaction-modes.md) | Spec de modos de interaccion |

---

## Licencia

[MIT](LICENSE) - Pablo Coello, 2026
