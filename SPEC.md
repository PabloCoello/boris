# Spec: Boris — Asistente de hogar local por voz

## Objetivo

Construir un asistente de voz personal llamado **Boris** que corra 24/7 en una workstation con RTX 3090, usando modelos locales (sin cloud). Boris escucha por wake word, entiende español, controla el hogar vía Home Assistant, gestiona calendario/recordatorios/música, consulta datos de salud de Garmin, y acumula conocimiento sobre el usuario en una memoria persistente basada en Markdown.

### Usuarios
- Un único usuario (el propietario de la máquina).

### Principios
- **Local-first**: STT, LLM y TTS corren en la máquina. Servicios cloud solo donde aportan valor claro (Spotify, Google Calendar, Outlook).
- **Voz como interfaz principal**: no hay UI web ni app.
- **Memoria que crece**: el asistente recuerda y sintetiza, no solo almacena.
- **Incremental**: cada fase produce un sistema funcional antes de avanzar.

---

## Tech Stack

| Componente | Tecnología | Versión/Modelo |
|---|---|---|
| LLM | Gemma 4 26B MoE via Ollama | `gemma4-26b` (Q4_K_M, ~18 GB) |
| STT | faster-whisper | `large-v3` (mejor precisión en español) |
| TTS | Coqui XTTS v2 | `tts_models/multilingual/multi-dataset/xtts_v2` |
| VAD | silero-vad | última estable |
| Wake word | openwakeword | palabra: "Boris" |
| Runtime | Python 3.11+ via uv | — |
| GPU | NVIDIA RTX 3090 (24 GB VRAM) | CUDA 12.x |
| Domótica | Home Assistant | container Docker |
| Salud | garminconnect | — |
| Música | Spotify via spotipy | cuenta premium |
| Calendario | Google Calendar + Outlook | OAuth (Google) + Microsoft Graph API |
| Echo cancel | Mute micrófono durante TTS | — |

---

## Commands

```bash
# Entorno
uv sync                              # instalar dependencias
uv run python -m boris               # arrancar Boris

# Tests
uv run pytest                         # todos los tests
uv run pytest tests/unit              # solo unitarios
uv run pytest tests/integration       # solo integración
uv run pytest --cov=boris --cov-report=term-missing  # cobertura

# Lint
uv run ruff check boris/ tests/       # lint
uv run ruff format boris/ tests/      # formato

# Memoria
uv run python -m boris.memory.linter  # linting manual de memoria

# Diagnóstico
uv run python -m boris.diag           # check GPU, Ollama, micrófono, altavoz
```

---

## Project Structure

```
boris/
├── __main__.py              # entry point: arranca el loop principal
├── core/
│   ├── loop.py              # bucle asyncio: wake → STT → LLM → TTS
│   ├── orchestrator.py      # dispatcher de tools (parsea JSON del LLM)
│   └── context.py           # construye system prompt + memoria
├── stt/
│   └── whisper.py           # cliente faster-whisper
├── tts/
│   └── xtts.py              # cliente Coqui XTTS v2
├── vad/
│   └── silero.py            # detección de voz + wake word
├── llm/
│   └── ollama.py            # cliente ollama-python con streaming
├── memory/
│   ├── loader.py            # carga profile.md + index.md al contexto
│   ├── writer.py            # genera episodic/ al cerrar sesión
│   └── linter.py            # cron nocturno: sintetiza y actualiza
├── skills/
│   ├── base.py              # interfaz base para skills
│   ├── home.py              # Home Assistant API
│   ├── music.py             # MPD / Spotify
│   ├── search.py            # SearXNG
│   ├── calendar.py          # Google Calendar + Outlook (sync)
│   ├── reminders.py         # APScheduler
│   └── garmin.py            # garminconnect
├── diag.py                  # diagnóstico de hardware y servicios
└── config.py                # carga .env + config.yaml

data/
├── memory/                  # wiki Markdown (datos, NO código)
│   ├── profile.md           # resumen del usuario (≤ 800 tokens)
│   ├── index.md             # catálogo de la wiki (≤ 400 tokens)
│   ├── entities.md          # personas, lugares, dispositivos
│   └── episodic/            # una entrada por día
│       └── YYYY-MM-DD.md
└── audio/                   # samples de voz para clonado TTS (futuro)

tests/
├── unit/
│   ├── test_orchestrator.py
│   ├── test_context.py
│   ├── test_memory_loader.py
│   └── test_memory_writer.py
├── integration/
│   ├── test_stt_pipeline.py
│   ├── test_llm_tool_calling.py
│   └── test_skill_home.py
└── conftest.py

config.yaml                  # opciones de comportamiento
.env                         # secretos (tokens, credenciales)
pyproject.toml               # proyecto uv
SPEC.md                      # este documento
```

### Separación .env / config.yaml

**.env** — secretos que nunca entran en git:
```
OLLAMA_HOST=http://localhost:11434
HA_URL=http://homeassistant.local:8123
HA_TOKEN=eyJ...
GARMIN_EMAIL=...
GARMIN_PASSWORD=...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
GOOGLE_CREDENTIALS_JSON=...     # ruta a credentials.json de Google OAuth
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_TENANT_ID=...
```

**config.yaml** — opciones de comportamiento:
```yaml
assistant:
  name: Boris
  language: es
  wake_word: boris

stt:
  model: large-v3
  language: es

tts:
  model: xtts_v2
  speaker_wav: data/audio/reference.wav  # para clonado de voz (futuro)

llm:
  model: gemma4-26b
  temperature: 0.7
  max_tokens: 512

memory:
  profile_max_tokens: 800
  index_max_tokens: 400
  linter_cron: "0 3 * * *"

skills:
  home:
    enabled: false   # se activa cuando HA esté corriendo
  garmin:
    enabled: true
  music:
    backend: spotify  # spotify
  search:
    url: http://localhost:8080
```

---

## Code Style

- Python 3.11+, type hints en todas las firmas públicas.
- Formatter/linter: `ruff` (format + check).
- Async por defecto en el loop principal; skills pueden ser sync envueltas en `asyncio.to_thread`.
- Docstrings solo en módulos y clases, no en cada función.
- Nombres en inglés (código), mensajes al usuario en español.

Ejemplo de referencia:

```python
import asyncio
from boris.skills.base import Skill, SkillResult

class HomeSkill(Skill):
    """Control de dispositivos vía Home Assistant REST API."""

    name = "home"
    description = "Controla luces, termostato y otros dispositivos del hogar."

    async def execute(self, action: str, entity_id: str, **kwargs) -> SkillResult:
        url = f"{self.config.ha_url}/api/services/{action}"
        headers = {"Authorization": f"Bearer {self.config.ha_token}"}
        payload = {"entity_id": entity_id, **kwargs}

        async with self.session.post(url, json=payload, headers=headers, timeout=5) as resp:
            if resp.status == 200:
                return SkillResult(ok=True, message=f"{entity_id} → {action}")
            return SkillResult(ok=False, message=f"Error {resp.status}")
```

---

## Personalidad de Boris

Boris es un mayordomo milenario al servicio de su señor en una mansión encantada. Lleva 5000 años sirviendo sin ser ejecutado — un récord del que está secretamente orgulloso.

### Rasgos
- **Servicial hasta la obsesión**: cumple cualquier petición con eficiencia sobrenatural.
- **Ligeramente siniestro**: su tono es cortés pero con un matiz oscuro, como si supiera cosas que prefiere no contar.
- **Formal y anticuado**: usa un registro elevado, nunca tutea. "Como desee, mi señor", no "¡Claro, ahí va!".
- **Humor negro sutil**: desliza comentarios macabros con naturalidad, sin romper el servicio.
- **Leal sin cuestionamiento**: no juzga las peticiones, las ejecuta. Si algo sale mal, se disculpa con dignidad fúnebre.

### Ejemplos de tono

| Situación | Respuesta de Boris |
|---|---|
| Encender luces | "Las luces del salón han sido encendidas, mi señor. La oscuridad tendrá que esperar... por ahora." |
| Error de servicio | "Lamento profundamente informarle de que Home Assistant no responde. En mis cinco milenios de servicio, he visto caer imperios por menos." |
| Buenos días | "Buenos días, mi señor. Ha sobrevivido otra noche. Permítame informarle de su agenda." |
| Recordatorio creado | "Anotado. Le recordaré puntualmente. La puntualidad es lo único que separa a un buen sirviente de uno enterrado en el jardín." |
| Garmin / sueño | "Ha dormido 6 horas y 43 minutos. Insuficiente para un mortal, aunque admirable para alguien que habita esta mansión." |

### Directrices para el system prompt
- Boris **siempre** se refiere al usuario como "mi señor" o "señor".
- Las respuestas son **concisas** — Boris es eficiente, no verboso.
- El humor macabro es un condimento, no el plato principal. No forzar un chiste en cada respuesta.
- En situaciones de urgencia (recordatorios, errores críticos), Boris es directo y claro primero, siniestro después.

---

## Testing Strategy

### Frameworks
- **pytest** + **pytest-asyncio** para tests async.
- **pytest-cov** para cobertura.

### Niveles

| Nivel | Qué cubre | Dónde | Mock? |
|---|---|---|---|
| Unitario | orchestrator, context, memory loader/writer, config | `tests/unit/` | Sí — se mockea Ollama, filesystem, APIs |
| Integración | STT pipeline, LLM tool calling, skills contra servicios reales | `tests/integration/` | No — requiere Ollama corriendo, micrófono opcional |
| E2E manual | Conversación completa de voz | — | No — se hace hablando con Boris |

### Cobertura mínima
- **Unitarios**: ≥ 80% en `boris/core/` y `boris/memory/`.
- **Integración**: al menos un test por skill que valide happy path.

### Qué se testea y qué no
- **Sí**: parsing de tool calls, construcción de contexto, lectura/escritura de memoria, fallback ante JSON malformado del LLM.
- **No**: calidad de la voz del TTS, calidad de transcripción del STT (eso se evalúa manualmente).

---

## Tool Calling — Contrato

### Formato de request (en system prompt del LLM)
```
Cuando necesites ejecutar una acción, responde ÚNICAMENTE con un bloque JSON:
{"tool": "<nombre>", "args": {<argumentos>}}

Si no necesitas ejecutar ninguna acción, responde en texto normal.
No mezcles texto y JSON en la misma respuesta.
```

### Reglas del dispatcher
1. Se intenta parsear la respuesta como JSON.
2. Si el JSON es válido y `tool` está registrado → se ejecuta la skill.
3. Si el JSON es malformado → se trata como texto plano y se lee al usuario.
4. Si `tool` no existe → se responde "No conozco esa acción".
5. **Una tool por turno**. Si Boris necesita encadenar (buscar → resumir), hace dos turnos internos antes de responder al usuario.
6. Timeout por skill: **5 segundos**. Si se excede → "No pude completar la acción, inténtalo de nuevo."
7. El resultado de la skill se inyecta como mensaje de sistema y el LLM genera la respuesta final en lenguaje natural.

### Tools disponibles

| Tool | Args | Descripción |
|---|---|---|
| `home` | `action`, `entity_id`, `**kwargs` | Controla dispositivos Home Assistant |
| `reminder` | `text`, `datetime` | Crea un recordatorio |
| `reminders_list` | — | Lista recordatorios pendientes |
| `calendar` | `days` (default 7), `source` (google/outlook/all) | Eventos próximos (Google Calendar + Outlook) |
| `music_play` | `query`, `type` (artist/album/playlist) | Reproduce música |
| `music_control` | `action` (pause/next/prev/volume) | Controla reproducción |
| `search` | `query` | Búsqueda web (top 3 snippets) |
| `garmin` | `metric` (sleep/hrv/steps/battery/activity) | Datos de salud |

---

## Boundaries

### Always
- Ejecutar `uv run ruff check` y `uv run pytest tests/unit` antes de cada commit.
- Respetar límites de tokens en memoria (`profile.md` ≤ 800, `index.md` ≤ 400).
- Timeout de 5s en toda llamada a servicio externo (HA, Garmin, SearXNG).
- Guardar secretos exclusivamente en `.env`, nunca en código ni en `config.yaml`.
- Loguear latencia de cada etapa (STT, LLM, TTS) en cada turno.

### Ask first
- Añadir nuevas dependencias a `pyproject.toml`.
- Cambiar el formato de los archivos de memoria.
- Modificar el contrato de tool calling.
- Cambiar modelo de LLM/STT/TTS.

### Never
- Enviar audio, transcripciones o datos de memoria a servicios cloud (Spotify/Calendar son la excepción explícita).
- Commitear `.env` o archivos con credenciales.
- Borrar archivos de `data/memory/episodic/` automáticamente (solo el usuario decide).
- Ejecutar acciones de Home Assistant sin confirmación verbal en acciones destructivas (bloquear puertas, apagar calefacción).

---

## Success Criteria por Fase

### Fase 0 — Entorno base
- [ ] `ollama run gemma4-26b "Hola, ¿cómo estás?"` devuelve respuesta coherente en español.
- [ ] `uv run python -m boris.diag` reporta: GPU detectada, Ollama accesible, micrófono captura audio.
- [ ] Estructura de carpetas creada y `uv sync` instala sin errores.

### Fase 1 — Bucle de voz
- [ ] Decir "Boris" activa la escucha (wake word funcional).
- [ ] Decir "Boris, ¿qué hora es?" produce respuesta hablada en español.
- [ ] Latencia medida end-to-end (wake detect → fin de TTS) < 3 segundos en P50.
- [ ] Latencia por etapa logueada: STT < 500ms, LLM first token < 1s, TTS < 800ms.
- [ ] Echo cancellation: micrófono se silencia durante reproducción de TTS; Boris no se activa con su propia voz.
- [ ] El sistema no crashea tras 30 minutos de escucha idle.

### Fase 2 — Memoria
- [ ] Tras una conversación de 5 turnos, `data/memory/episodic/YYYY-MM-DD.md` se genera con resumen.
- [ ] `profile.md` se puede cargar y aparece en el contexto del LLM (verificable en logs).
- [ ] Linter ejecutado manualmente actualiza `profile.md` sin perder información previa.
- [ ] `entities.md` contiene al menos una entidad mencionada en conversación previa.
- [ ] Tests unitarios de loader y writer pasan con ≥ 80% cobertura.

### Fase 3 — Skills básicas
- [ ] "Boris, ponme un recordatorio para mañana a las 10" → recordatorio creado y confirmado por voz.
- [ ] "Boris, ¿qué tengo hoy en el calendario?" → lee eventos del día de Google Calendar y Outlook combinados.
- [ ] "Boris, busca cuántos habitantes tiene Asturias" → responde con dato de SearXNG.
- [ ] "Boris, pon música de Rosalía" → Spotify reproduce música de Rosalía.
- [ ] JSON malformado del LLM → Boris responde en texto normal sin crashear.
- [ ] Skill con timeout → Boris dice "No pude completar la acción".

### Fase 4 — Domótica + Garmin
- [ ] Home Assistant corriendo en Docker, accesible desde Boris.
- [ ] Al menos una luz inteligente registrada como entidad en HA.
- [ ] "Boris, enciende la luz del salón" → la luz se enciende.
- [ ] "Boris, ¿cómo dormí anoche?" → responde con datos reales de Garmin.
- [ ] Cron nocturno añade sección `### Salud` al episódico del día con datos de Garmin.
- [ ] Lista de entidades HA cacheada en `data/memory/entities.md`.

### Fase 5 — Voz personalizada + producción
- [ ] TTS usa voz clonada (o XTTS con speaker reference) — calidad evaluada subjetivamente como "aceptable".
- [ ] Servicio systemd arranca Boris al boot y se recupera de crasheos.
- [ ] Timer systemd ejecuta linter a las 03:00.
- [ ] Test de estabilidad: conversación de 20 turnos sin degradación de latencia (P95 < 5s).
- [ ] Logs rotan diariamente y no superan 100 MB/semana.

---

## Decisiones tomadas

1. **Dispositivos HA iniciales**: luces inteligentes. Se irán añadiendo dispositivos progresivamente.
2. **Calendario**: sincronización con Google Calendar + Outlook (Google OAuth + Microsoft Graph API).
3. **Música**: Spotify vía `spotipy`.
4. **Personalidad de Boris**: definida (ver sección Personalidad).
5. **Echo cancellation**: sí — micrófono se silencia durante reproducción de TTS.

## Open Questions

1. **¿Qué luces inteligentes concretas?** — marca/protocolo (Zigbee, Z-Wave, WiFi) determina si HA necesita un dongle USB o basta con integración WiFi. Pendiente de definir.
