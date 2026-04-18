# Referencia de Skills

Boris ejecuta skills cuando el LLM responde con un JSON tool call. Cada skill se registra condicionalmente segun la configuracion y los secretos disponibles en `.env`.

## Como funcionan

1. El LLM recibe la lista de herramientas en el system prompt
2. Si decide ejecutar una, responde con: `{"tool": "<nombre>", "args": {<args>}}`
3. El orchestrator busca el skill en el registry y lo ejecuta con timeout de 5s
4. El resultado se inyecta en el historial y el LLM genera una respuesta natural

Si el skill falla o hace timeout, Boris responde con un mensaje de error.

---

## music_play

Reproduce musica via Spotify.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `query` | str | si | Busqueda (artista, album, cancion, genero) |
| `type` | str | no | `track`, `artist`, `album`, `playlist` (default: `track`) |

**Ejemplo de voz:** "Boris pon jazz" / "Boris pon musica de Rosalia"

**JSON generado:**
```json
{"tool": "music_play", "args": {"query": "jazz", "type": "playlist"}}
```

**Requiere:**
- `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET` en `.env`
- Un dispositivo Spotify activo (app desktop, movil, o spotifyd)
- Cuenta Spotify Premium

**Edge cases:**
- Si la busqueda devuelve items nulos (Spotify a veces devuelve `[None]`), se filtran y se responde "No encontre X"
- Sin dispositivo activo: Spotify API devuelve error 404 → Boris dice "No hay dispositivo activo"

---

## music_control

Controla la reproduccion activa de Spotify.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `action` | str | si | `pause`, `next`, `prev`, `volume` |
| `level` | int | no | Nivel de volumen 0-100 (solo con action=volume) |

**Ejemplo de voz:** "Boris pausa la musica" / "Boris siguiente cancion" / "Boris volumen al 50"

**JSON generado:**
```json
{"tool": "music_control", "args": {"action": "pause"}}
{"tool": "music_control", "args": {"action": "volume", "level": 50}}
```

**Requiere:** igual que `music_play`.

---

## calendar

Consulta eventos proximos de Google Calendar.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `days` | int | no | Ventana de dias a consultar (default: 7) |

**Ejemplo de voz:** "Boris que tengo manana" / "Boris que tengo esta semana en el calendario"

**JSON generado:**
```json
{"tool": "calendar", "args": {"days": 1}}
```

**Requiere:**
- `GOOGLE_CREDENTIALS_JSON` en `.env` apuntando a `data/google-credentials.json`
- Autenticacion OAuth completada: `uv run python -m boris.skills.calendar --auth`
- Token guardado en `data/google-token.json` (se renueva automaticamente)

**Setup detallado:** [docs/oauth-setup.md](oauth-setup.md)

---

## garmin

Consulta datos de salud desde Garmin Connect.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `metric` | str | si | `sleep`, `hrv`, `steps`, `battery`, `activity` |

**Ejemplo de voz:** "Boris como dormi anoche" / "Boris cuantos pasos llevo" / "Boris body battery"

**JSON generado:**
```json
{"tool": "garmin", "args": {"metric": "sleep"}}
```

**Metricas disponibles:**

| Metrica | Datos devueltos |
|---|---|
| `sleep` | Total, profundo, ligero, REM, despierto |
| `steps` | Pasos del dia + distancia en km |
| `hrv` | HRV ultima noche + media semanal |
| `battery` | Body Battery actual |
| `activity` | Ultimas 3 actividades (nombre, duracion, distancia) |

**Requiere:**
- `GARMIN_EMAIL` y `GARMIN_PASSWORD` en `.env`
- `skills.garmin.enabled: true` en `config.yaml`
- Tokens generados en `data/garmin-tokens/` (ver [docs/setup.md](setup.md#8-garmin-connect))
- Parche de login widget aplicado si Cloudflare bloquea (ver setup.md)

**Edge cases:**
- Si la sesion expira, el skill reintenta login una vez con tokens cacheados
- Si falla de nuevo, devuelve error y el usuario debe regenerar tokens

---

## search

Busqueda web via SearXNG (instancia local).

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `query` | str | si | Consulta de busqueda |

**Ejemplo de voz:** "Boris busca cuantos habitantes tiene Asturias"

**JSON generado:**
```json
{"tool": "search", "args": {"query": "habitantes Asturias"}}
```

**Respuesta:** devuelve los 3 primeros resultados con titulo y snippet.

**Requiere:**
- SearXNG corriendo en Docker: `docker run -d --name searxng -p 8080:8080 searxng/searxng:latest`
- Formato JSON habilitado en SearXNG settings
- `skills.search.url: http://localhost:8080` en `config.yaml`

---

## reminder

Crea un recordatorio.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `text` | str | si | Texto del recordatorio |
| `datetime` | str | si | Fecha/hora en formato ISO 8601 |

**Ejemplo de voz:** "Boris recuerdame comprar leche manana a las 10"

**JSON generado:**
```json
{"tool": "reminder", "args": {"text": "Comprar leche", "datetime": "2026-04-19T10:00:00"}}
```

**Requiere:** nada (siempre activo, almacenamiento en memoria).

**Nota:** los recordatorios se almacenan en memoria del proceso. Se pierden al reiniciar Boris.

---

## reminders_list

Lista recordatorios pendientes.

Sin argumentos.

**Ejemplo de voz:** "Boris que recordatorios tengo"

**JSON generado:**
```json
{"tool": "reminders_list", "args": {}}
```

**Requiere:** nada (siempre activo).

---

## home

Control de dispositivos via Home Assistant REST API.

| Arg | Tipo | Requerido | Descripcion |
|---|---|---|---|
| `action` | str | si | Accion a ejecutar (ej: `light/turn_on`, `light/turn_off`) |
| `entity_id` | str | si | ID de la entidad en Home Assistant |

**Ejemplo de voz:** "Boris enciende la luz del salon"

**JSON generado:**
```json
{"tool": "home", "args": {"action": "light/turn_on", "entity_id": "light.salon"}}
```

**Requiere:**
- `HA_URL` y `HA_TOKEN` en `.env`
- `skills.home.enabled: true` en `config.yaml`
- Home Assistant corriendo y accesible

**Estado:** pendiente de implementacion. La skill esta definida en el schema del LLM pero no tiene clase implementada aun.

---

## Registro de skills

Las skills se registran condicionalmente en `boris/skills/registry.py`:

| Skill | Condicion de registro |
|---|---|
| `reminder`, `reminders_list` | Siempre |
| `search` | `skills.search.url` no vacio en config.yaml |
| `music_play`, `music_control` | `SPOTIFY_CLIENT_ID` presente en .env |
| `calendar` | `GOOGLE_CREDENTIALS_JSON` presente en .env |
| `garmin` | `skills.garmin.enabled: true` en config.yaml + `GARMIN_EMAIL` en .env |
| `home` | No implementado aun |

Boris funciona sin ninguna skill externa — solo necesita Ollama para conversacion basica.

## Crear una skill nueva

1. Crear clase en `boris/skills/tu_skill.py` que herede de `Skill`
2. Definir `name` y `description` como atributos de clase
3. Implementar `async execute(**kwargs) -> SkillResult`
4. Registrar en `boris/skills/registry.py` (con condicion si requiere config)
5. Anadir al `TOOL_SCHEMA` en `boris/core/context.py`

```python
from boris.skills.base import Skill, SkillResult

class MiSkill(Skill):
    name = "mi_skill"
    description = "Hace algo util."

    async def execute(self, **kwargs) -> SkillResult:
        param = kwargs.get("param")
        if not param:
            return SkillResult(ok=False, message="Falta el parametro.")
        # ... logica ...
        return SkillResult(ok=True, message="Hecho.")
```

El metodo `run()` de la clase base envuelve `execute()` con timeout (5s) y manejo de errores automaticamente.
