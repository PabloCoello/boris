"""Main async loop: wake word → listen → STT → LLM → orchestrator → TTS.

Supports two interaction modes:
- COMMAND: "Boris <command>" → beep, execute, short response, idle.
- SUMMONED: "Boris manifiéstate" → conversation loop until dismiss or timeout.
"""

from __future__ import annotations

import asyncio
import re
import time
import unicodedata
from pathlib import Path

from loguru import logger

from boris.config import Config
from boris.core.context import build_system_prompt
from boris.core.feedback import FeedbackPlayer
from boris.core.orchestrator import execute_tool_call, parse_tool_call
from boris.core.state import InteractionMode
from boris.llm.ollama import OllamaClient
from boris.memory.loader import load_memory_context
from boris.memory.writer import save_episodic
from boris.skills.base import SkillRegistry
from boris.skills.registry import build_registry
from boris.stt.whisper import WhisperSTT
from boris.tts.xtts import TTSEngine
from boris.vad.silero import AudioListener
from boris.wakeword.detector import WakeWordDetector


# ── Helpers ─���────────────────────────────��───────────────────────────


def _strip_wake_word(text: str, wake_word: str) -> str:
    """Remove the wake word prefix from a transcription."""
    pattern = rf"^{re.escape(wake_word)}[,.]?\s*"
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()


async def _process_turn(
    text: str,
    history: list[dict[str, str]],
    system_prompt: str,
    llm: OllamaClient,
    registry: SkillRegistry,
) -> tuple[str, bool]:
    """Run LLM + orchestrator for one turn.

    Returns (spoken_text, tool_executed_ok).
    """
    history.append({"role": "user", "content": text})
    messages = [{"role": "system", "content": system_prompt}] + history

    response = await llm.chat_full(messages)
    logger.info(f"Boris dice: {response[:100]}...")
    history.append({"role": "assistant", "content": response})

    tool_call, spoken_text = parse_tool_call(response)
    tool_ok = False

    if tool_call:
        result = await execute_tool_call(tool_call, registry)
        logger.info(f"Skill result: ok={result.ok}, msg={result.message[:80]}")
        tool_ok = result.ok

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

    return spoken_text, tool_ok


def _trim_history(history: list[dict[str, str]], max_len: int = 40):
    """Keep history within bounds (in-place)."""
    if len(history) > max_len:
        del history[: len(history) - max_len]


def _is_question(text: str) -> bool:
    """Heuristic: does the text end with a question mark?"""
    return text.rstrip().endswith("?")


def _normalize(text: str) -> str:
    """Strip accents and lowercase for fuzzy phrase matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# ── Main loop ────────────────���───────────────────────────────────────


async def main_loop(config: Config):
    """Run Boris: wake word → listen → transcribe → respond → speak, forever."""
    logger.info("Iniciando Boris...")

    # Initialize components
    listener = AudioListener(config.assistant, config.audio)
    stt = WhisperSTT(config.stt)
    llm = OllamaClient(config.llm, config.secrets)
    tts = TTSEngine(config.tts)
    feedback = FeedbackPlayer(
        enabled=config.audio.feedback_sounds,
        volume=config.audio.feedback_volume,
    )

    # Wire echo cancellation
    tts.set_listener(listener)
    feedback.set_listener(listener)

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

    # Pre-build system prompts for each mode
    prompt_base = build_system_prompt(config, memory_context=memory_ctx or None)
    prompt_command = build_system_prompt(
        config, memory_context=memory_ctx or None, mode=InteractionMode.COMMAND,
    )
    prompt_summoned = build_system_prompt(
        config, memory_context=memory_ctx or None, mode=InteractionMode.SUMMONED,
    )

    history: list[dict[str, str]] = []
    episodic_dir = Path(config.memory.data_dir) / "episodic"

    # Config shortcuts
    summon_phrase = _normalize(config.assistant.summon_phrase)
    dismiss_phrase = _normalize(config.assistant.dismiss_phrase)
    summon_timeout = config.assistant.summon_timeout_s
    follow_up_timeout = config.assistant.follow_up_timeout_s

    # Wake word detector
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
            # ── IDLE: Wait for wake word ───────��─────────────────────
            await ww_detector.wait()
            ww_detector.reset()
            logger.info("Wake word detectado")
            tts.stop()  # barge-in if TTS was playing

            # ── LISTENING: Capture speech ────────────────────────────
            audio = await listener.listen()

            # ── TRANSCRIBE ──────────��────────────────────────────────
            t_turn_start = time.perf_counter()
            text = await stt.transcribe(audio)

            if not text.strip():
                logger.debug("Transcripción vacía, ignorando")
                ww_detector.resume()
                continue

            logger.info(f"Señor dice: {text}")
            command = _strip_wake_word(text, config.assistant.wake_word)

            # ── ROUTE: Summon or Command? ────────────────────────────
            if summon_phrase in _normalize(text):
                await _summoned_session(
                    config, listener, stt, llm, tts, feedback, registry,
                    history, prompt_summoned, episodic_dir,
                    ww_detector, dismiss_phrase, summon_timeout,
                )
            else:
                # Resume wake word detector BEFORE TTS so barge-in works
                ww_detector.resume()

                await _command_turn(
                    command, history, prompt_command, llm, registry,
                    tts, feedback, listener, stt, follow_up_timeout,
                )

            t_turn_total = (time.perf_counter() - t_turn_start) * 1000
            logger.info(f"Turno completo: {t_turn_total:.0f}ms")
            _trim_history(history)

        except KeyboardInterrupt:
            logger.info("Boris se retira. Guardando memoria...")
            ww_detector.stop()
            if history:
                try:
                    await save_episodic(history, episodic_dir, summarize_fn=llm.prompt)
                except Exception as e:
                    logger.error(f"Error guardando episodic: {e}")
            logger.info("Buenas noches, mi señor.")
            break
        except Exception as e:
            logger.error(f"Error en el loop: {e}")
            ww_detector.resume()
            await asyncio.sleep(1)


# ── Command mode ──────���──────────────────────────────────────────────


async def _command_turn(
    command: str,
    history: list[dict[str, str]],
    prompt: str,
    llm: OllamaClient,
    registry: SkillRegistry,
    tts: TTSEngine,
    feedback: FeedbackPlayer,
    listener: AudioListener,
    stt: WhisperSTT,
    follow_up_timeout: int,
):
    """Handle a single command: beep → process → respond → idle."""
    await asyncio.to_thread(feedback.play_detect)

    spoken, tool_ok = await _process_turn(command, history, prompt, llm, registry)

    if tool_ok:
        await asyncio.to_thread(feedback.play_confirm)

    if spoken:
        await tts.speak(spoken)

    # Follow-up: if Boris asked a question, wait for ONE response
    if spoken and _is_question(spoken):
        logger.info(f"Follow-up: esperando respuesta ({follow_up_timeout}s)...")
        try:
            audio = await asyncio.wait_for(
                listener.listen(), timeout=follow_up_timeout,
            )
            text = await stt.transcribe(audio)
            if text.strip():
                logger.info(f"Señor responde: {text}")
                spoken, tool_ok = await _process_turn(
                    text, history, prompt, llm, registry,
                )
                if tool_ok:
                    await asyncio.to_thread(feedback.play_confirm)
                if spoken:
                    await tts.speak(spoken)
        except asyncio.TimeoutError:
            logger.debug("Follow-up timeout, volviendo a idle")


# ── Summoned mode ─────────────���──────────────────────────────────────


async def _summoned_session(
    config: Config,
    listener: AudioListener,
    stt: WhisperSTT,
    llm: OllamaClient,
    tts: TTSEngine,
    feedback: FeedbackPlayer,
    registry: SkillRegistry,
    history: list[dict[str, str]],
    prompt: str,
    episodic_dir: Path,
    ww_detector: WakeWordDetector,
    dismiss_phrase: str,
    summon_timeout: int,
):
    """Run a summoned conversation session.

    The wake word detector stays paused for the entire session.
    AudioListener opens/closes its own mic stream per listen() call.
    """
    logger.info("Entrando en modo convocado")
    session_start_idx = len(history)

    await asyncio.to_thread(feedback.play_summon)
    await tts.speak("A sus órdenes, mi señor.")

    last_activity = time.monotonic()

    while True:
        try:
            # Time remaining before auto-dismiss
            elapsed = time.monotonic() - last_activity
            remaining = max(1.0, summon_timeout - elapsed)

            audio = await asyncio.wait_for(listener.listen(), timeout=remaining)

            text = await stt.transcribe(audio)
            if not text.strip():
                continue  # silence — don't reset activity timer

            last_activity = time.monotonic()
            logger.info(f"Señor dice: {text}")

            # Check for dismiss phrase
            if dismiss_phrase in _normalize(text):
                logger.info("Frase de desconvocación detectada")
                break

            # Process turn (command or conversation)
            spoken, tool_ok = await _process_turn(text, history, prompt, llm, registry)

            if tool_ok:
                await asyncio.to_thread(feedback.play_confirm)

            if spoken:
                await tts.speak(spoken)

            _trim_history(history)

        except asyncio.TimeoutError:
            logger.info(f"Timeout de inactividad ({summon_timeout}s), desconvocando")
            break
        except Exception as e:
            logger.error(f"Error en sesión convocada: {e}")
            await asyncio.to_thread(feedback.play_error)
            # Continue session — don't exit on single error

    # ── Dismiss ──────────────────────────────────────────────────
    await asyncio.to_thread(feedback.play_dismiss)
    await tts.speak("Me retiro, mi señor.")

    # Save episodic memory for this session
    session_history = history[session_start_idx:]
    if session_history:
        try:
            await save_episodic(session_history, episodic_dir, summarize_fn=llm.prompt)
            logger.info("Episodic memory guardada")
        except Exception as e:
            logger.error(f"Error guardando episodic: {e}")

    # Resume wake word detector
    ww_detector.resume()
    logger.info("Modo convocado finalizado, volviendo a idle")
