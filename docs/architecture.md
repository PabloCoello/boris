# Arquitectura de Boris

## Pipeline de voz

Boris procesa audio en un pipeline secuencial dentro de un bucle asyncio:

```
                         ┌──────────────────────────────────────────────��
                         │              THREAD: wakeword               │
                         │                                              │
   Microfono ──────────> │  sounddevice ──> openwakeword ──> detected?  │
                         │       16kHz, 80ms frames         score>0.3   │
                         └─────���────────────┬───────────────────────────┘
                                            │
                                   asyncio.Event.set()
                                            │
                         ┌──────────────────▼───────────────────────────┐
                         │              ASYNC: main loop                │
                         │                                              │
                         │  1. AudioListener.listen()                   ���
                         │     - Abre stream mic (16kHz, mono)          │
                         │     - VAD (silero) detecta inicio/fin        │
                         │     - Devuelve numpy array con el audio      │
                         │                                              │
                         │  2. WhisperSTT.transcribe(audio)             │
                         │     - faster-whisper (small/large-v3)        │
                         │     - Devuelve texto en espanol              │
                         │                                              │
                         │  3. OllamaClient.chat_full(messages)         │
                         │     - System prompt + historial + turno      │
                         │     - Responde texto o JSON tool call        │
                         │                                              │
                         │  4. Orchestrator                             │
                         │     - parse_tool_call(): extrae JSON         │
                         │     - execute_tool_call(): corre skill       │
                         │     - Si tool: inyecta resultado, re-ask LLM│
                         │                                              │
                         │  5. TTSEngine.speak(texto)                   │
                         │     - Sintetiza audio (piper/xtts)           │
                         │     - Pitch shift (librosa)                  │
                         │     - Reproduce con sounddevice              │
                         │     - Mic silenciado durante reproduccion    │
                         └──────��───────────────────────────────────────┘
```

## Maquina de estados

```
                    ┌─────────────────────────────────┐
                    │            IDLE                  │
                    │   (wake word detector activo)    │
                    └──────────┬──────────────────────┘
                               │
                     wake word "Boris" detectada
                     detector pausa y suelta mic
                               │
                               ▼
                    ┌─────────────────────────────────┐
                    │         LISTENING                │
                    │   (VAD graba, STT transcribe)    │
                    ��──────────┬──────────────────────┘
                               │
                          transcripcion
                               │
                    ┌──────────┴──────────┐
                    │                     │
              "manifestate"          otro texto
                    │                     │
                    ▼                     ▼
          ┌─────────────────┐   ┌─────────────────────┐
          │    SUMMONED     │   │      COMMAND         │
          │ (conversacion)  │   │  (una respuesta)     │
          └────────┬────────┘   └──────────┬──────────┘
                   │                       │
           loop sin wake word      LLM + skill + TTS
           hasta dismiss/timeout          │
                   │               ¿Respuesta es pregunta?
                   │                  │           │
                   │                 SI           NO
                   │                  │           │
                   │           follow-up (10s)    │
                   │                  │           │
                   ▼                  ▼           ▼
          guardar episodic         [IDLE]      [IDLE]
          chime despedida
                   │
                   ▼
                [IDLE]
```

Los estados se definen en `boris/core/state.py` como `InteractionMode` (IDLE, LISTENING, COMMAND, SUMMONED).

## Protocolo de microfono

Boris tiene un unico microfono USB (ALSA exclusivo). Dos componentes necesitan acceder a el:

1. **WakeWordDetector** — thread dedicado, stream permanente a 16kHz
2. **AudioListener** — asyncio, abre stream por llamada para grabar

No pueden abrir el mismo dispositivo ALSA simultaneamente. El protocolo de handoff:

```
Estado normal (IDLE):
  WakeWordDetector tiene el stream abierto
  AudioListener esta inactivo

Deteccion de wake word:
  1. WakeWordDetector detecta "Boris"
  2. WakeWordDetector cierra su stream
  3. WakeWordDetector setea _paused + _resumed (threading.Events)
  4. WakeWordDetector senala _detected (asyncio.Event → main loop)
  5. Main loop llama AudioListener.listen() → abre stream, graba, cierra
  6. Main loop procesa (STT → LLM → TTS)
  7. Main loop llama ww_detector.resume()
  8. WakeWordDetector reabre su stream

Modo comando (barge-in):
  - resume() se llama ANTES de TTS
  - El detector escucha durante la reproduccion de voz
  - Si detecta "Boris" durante TTS → tts.stop() → nuevo ciclo

Modo convocado:
  - El detector permanece pausado toda la sesion
  - AudioListener abre/cierra stream en cada turno
  - resume() se llama al salir del modo convocado
```

Implementado en `boris/wakeword/detector.py` (lineas 119-194).

## Echo cancellation

Boris evita disparar el VAD o el wake word detector con su propia voz:

```
TTSEngine.speak():
  1. listener.mute()          # silencia el canal de entrada
  2. sounddevice.play(audio)  # reproduce la sintesis
  3. sounddevice.wait()       # espera a que termine
  4. listener.unmute()        # reactiva el canal

FeedbackPlayer._play():
  1. listener.mute()
  2. sounddevice.play(beep)
  3. sounddevice.wait()
  4. listener.unmute()
```

Ambos componentes aceptan `set_listener()` para recibir referencia al AudioListener. El mute/unmute opera sobre un flag interno — el stream de captura sigue abierto pero los frames se descartan.

## System prompt

El prompt se construye en `boris/core/context.py` con capas:

```
┌─────────────────────────────────────────┐
│ PERSONALITY                             │
│ Boris mayordomo, 5000 anos, formal,     │
│ humor negro sutil, siempre "mi senor"   │
├─────────────────────────────────────────┤
│ MEMORY (opcional)                       │
│ profile.md del usuario,                 │
│ index.md del catalogo de memoria        │
├─────────────────────────────────────────┤
│ TOOL_SCHEMA                             │
│ JSON format, lista de herramientas      │
│ disponibles con args                    │
├─────────────────────────────────────────┤
│ MODE (segun estado)                     │
│ COMMAND: "responde en UNA frase"        │
│ SUMMONED: "sesion activa, conciso"      │
│ IDLE: (sin directiva de modo)           │
└─────────────────────────────────────────┘
```

El prompt se pre-construye al arrancar Boris (uno por modo) para evitar recalcularlo en cada turno.

## Flujo de un tool call

Cuando el LLM decide ejecutar una herramienta:

```
1. LLM responde: {"tool": "music_play", "args": {"query": "jazz"}}

2. parse_tool_call() extrae el JSON
   - Intenta parsear respuesta completa como JSON
   - Si falla, busca JSON embebido en texto
   - Devuelve (tool_call_dict, spoken_text)

3. execute_tool_call() busca skill en registry
   - registry.get("music_play") → MusicPlaySkill
   - skill.run(timeout=5.0, query="jazz")
   - Devuelve SkillResult(ok=True, message="Reproduciendo: Jazz Classics")

4. Resultado se inyecta como mensaje de sistema en el historial:
   {"role": "system", "content": "Resultado de music_play: Reproduciendo: Jazz Classics"}

5. LLM genera respuesta natural:
   "Jazz activado, mi senor."

6. Guard contra tool calls anidados:
   - Si la respuesta del paso 5 contiene otro JSON tool call, se ignora
   - Se usa el texto limpio o un fallback generico
```

Implementado en `boris/core/loop.py:_process_turn()` y `boris/core/orchestrator.py`.

## Memoria

Boris mantiene tres capas de memoria en `data/memory/`:

```
data/memory/
├── profile.md       # Perfil sintetizado del usuario (≤800 tokens)
│                    # Se carga en el system prompt
│
├── index.md         # Catalogo de temas conocidos (≤400 tokens)
│                    # Permite al LLM saber que recuerda
│
├── entities.md      # Personas, lugares, dispositivos
│
└── episodic/        # Una entrada por sesion
    └── YYYY-MM-DD.md  # Resumen generado por el LLM al cerrar sesion
```

- **Carga** (`memory/loader.py`): al arrancar, `profile.md` e `index.md` se leen y concatenan como contexto en el system prompt.
- **Escritura** (`memory/writer.py`): al cerrar una sesion convocada o al salir con Ctrl+C, el historial se resume via el LLM y se guarda en `episodic/`.
- **Linter** (`memory/linter.py`): proceso que sintetiza episodicos acumulados para actualizar `profile.md` e `index.md`.

## Componentes y archivos

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Entry point | `boris/__main__.py` | Configura logging, carga config, lanza loop |
| Config | `boris/config.py` | Dataclasses + carga de YAML y .env |
| Main loop | `boris/core/loop.py` | Bucle asyncio con maquina de estados |
| System prompt | `boris/core/context.py` | Personalidad + memoria + tools + modo |
| Orchestrator | `boris/core/orchestrator.py` | Parsea JSON del LLM, despacha skills |
| Feedback | `boris/core/feedback.py` | Genera y reproduce tonos sinteticos |
| State | `boris/core/state.py` | InteractionMode enum + SessionState |
| STT | `boris/stt/whisper.py` | faster-whisper |
| TTS | `boris/tts/xtts.py` | Coqui TTS + pitch shift |
| TTS normalize | `boris/tts/normalize.py` | Normalizacion de texto para sintesis |
| VAD | `boris/vad/silero.py` | Deteccion de voz + grabacion |
| Wake word | `boris/wakeword/detector.py` | openwakeword con pause/resume |
| LLM | `boris/llm/ollama.py` | Cliente Ollama con streaming |
| Memory loader | `boris/memory/loader.py` | Carga memoria al contexto |
| Memory writer | `boris/memory/writer.py` | Guarda episodicos |
| Memory linter | `boris/memory/linter.py` | Sintetiza y actualiza memoria |
| Skill base | `boris/skills/base.py` | ABC + SkillResult + SkillRegistry |
| Skill registry | `boris/skills/registry.py` | Registro condicional segun config |
| Skills | `boris/skills/*.py` | Implementaciones individuales |
