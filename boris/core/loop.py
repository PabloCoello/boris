"""Main async loop: wake word → listen → STT → LLM → orchestrator → TTS."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from loguru import logger

from boris.config import Config
from boris.core.context import build_system_prompt
from boris.core.orchestrator import execute_tool_call, parse_tool_call
from boris.llm.ollama import OllamaClient
from boris.memory.loader import load_memory_context
from boris.memory.writer import save_episodic
from boris.skills.registry import build_registry
from boris.stt.whisper import WhisperSTT
from boris.tts.xtts import TTSEngine
from boris.vad.silero import AudioListener
from boris.wakeword.detector import WakeWordDetector


async def main_loop(config: Config):
    """Run Boris: wake word → listen → transcribe → respond → speak, forever."""
    logger.info("Iniciando Boris...")

    # Initialize components
    listener = AudioListener(config.assistant, config.audio)
    stt = WhisperSTT(config.stt)
    llm = OllamaClient(config.llm, config.secrets)
    tts = TTSEngine(config.tts)

    # Wire echo cancellation
    tts.set_listener(listener)

    # Build skill registry
    registry = build_registry(config)

    # Load memory into context
    memory_ctx = load_memory_context(
        config.memory.data_dir,
        profile_max_tokens=config.memory.profile_max_tokens,
        index_max_tokens=config.memory.index_max_tokens,
    )
    if memory_ctx:
        logger.info(f"Memoria cargada: {len(memory_ctx)} chars")

    # Build system prompt
    system_prompt = build_system_prompt(config, memory_context=memory_ctx or None)
    history: list[dict[str, str]] = []

    # Episodic dir for saving conversation summaries
    episodic_dir = Path(config.memory.data_dir) / "episodic"

    # Wake word detector — own mic stream, never muted
    ww_model = config.assistant.wake_word_model
    ww_detector = WakeWordDetector(
        model_path=ww_model if ww_model else None,
        threshold=config.assistant.wake_word_threshold,
        device_name=config.audio.input_device_name,
    )

    loop = asyncio.get_event_loop()
    ww_detector.start(loop)

    logger.info("Boris listo. Esperando wake word...")

    while True:
        try:
            # ── Phase 1: Wait for wake word ──────────────────────────
            await ww_detector.wait()
            ww_detector.reset()
            logger.info("Wake word detectado")

            # If TTS was playing, stop it (barge-in)
            tts.stop()

            # ── Phase 2: Listen for speech (VAD-based) ───────────────
            audio = await listener.listen()

            # ── Phase 3: Transcribe ──────────────────────────────────
            t_turn_start = time.perf_counter()
            text = await stt.transcribe(audio)

            if not text.strip():
                logger.debug("Transcripción vacía, ignorando")
                continue

            logger.info(f"Señor dice: {text}")

            # ── Phase 4: LLM ────────────────────────────────────────
            history.append({"role": "user", "content": text})
            messages = [{"role": "system", "content": system_prompt}] + history

            response = await llm.chat_full(messages)
            logger.info(f"Boris dice: {response[:100]}...")
            history.append({"role": "assistant", "content": response})

            # ── Phase 5: Tool call dispatch ──────────────────────────
            tool_call, spoken_text = parse_tool_call(response)

            if tool_call:
                result = await execute_tool_call(tool_call, registry)
                logger.info(f"Skill result: ok={result.ok}, msg={result.message[:80]}")

                # Inject result and get natural language response
                history.append({
                    "role": "system",
                    "content": f"Resultado de {tool_call.get('tool')}: {result.message}",
                })
                messages = [{"role": "system", "content": system_prompt}] + history
                spoken_text = await llm.chat_full(messages)
                history.append({"role": "assistant", "content": spoken_text})

                # Guard against nested tool call
                nested_tool, cleaned = parse_tool_call(spoken_text)
                if nested_tool:
                    logger.warning(f"Nested tool call ignorado: {nested_tool.get('tool')}")
                    spoken_text = cleaned or f"Listo, mi señor. {result.message}"

            # ── Phase 6: Speak (can be interrupted by wake word) ─────
            if spoken_text:
                await tts.speak(spoken_text)

            t_turn_total = (time.perf_counter() - t_turn_start) * 1000
            logger.info(f"Turno completo: {t_turn_total:.0f}ms")

            # Keep history manageable
            if len(history) > 40:
                history = history[-40:]

        except KeyboardInterrupt:
            logger.info("Boris se retira. Guardando memoria...")
            ww_detector.stop()
            if history:
                try:
                    await save_episodic(
                        history,
                        episodic_dir,
                        summarize_fn=llm.prompt,
                    )
                except Exception as e:
                    logger.error(f"Error guardando episodic: {e}")
            logger.info("Buenas noches, mi señor.")
            break
        except Exception as e:
            logger.error(f"Error en el loop: {e}")
            await asyncio.sleep(1)
