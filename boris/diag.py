"""Diagnostics: check GPU, Ollama, audio devices.

Run with: python -m boris.diag
"""

from __future__ import annotations

import subprocess
import sys


def check_gpu() -> bool:
    """Check if NVIDIA GPU is available."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                print(f"  GPU: {line.strip()}")
            return True
        print("  GPU: nvidia-smi falló")
        return False
    except FileNotFoundError:
        print("  GPU: nvidia-smi no encontrado")
        return False


def check_ollama() -> bool:
    """Check if Ollama is running and gemma4-26b is available."""
    try:
        import ollama

        models = ollama.list()
        model_names = [m.model for m in models.models]
        print(f"  Ollama: conectado, {len(model_names)} modelo(s)")
        for name in model_names:
            print(f"    - {name}")

        has_gemma = any("gemma4" in name for name in model_names)
        if not has_gemma:
            print("  ⚠ gemma4-26b no encontrado en modelos disponibles")
        return has_gemma
    except Exception as e:
        print(f"  Ollama: no accesible ({e})")
        return False


def check_microphone() -> bool:
    """Check if a microphone is available."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if input_devices:
            default = sd.query_devices(kind="input")
            print(f"  Micrófono: {len(input_devices)} dispositivo(s) de entrada")
            print(f"    Default: {default['name']}")
            return True
        print("  Micrófono: no se encontraron dispositivos de entrada")
        return False
    except Exception as e:
        print(f"  Micrófono: error ({e})")
        return False


def check_speaker() -> bool:
    """Check if an audio output device is available."""
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        output_devices = [d for d in devices if d["max_output_channels"] > 0]
        if output_devices:
            default = sd.query_devices(kind="output")
            print(f"  Altavoz: {len(output_devices)} dispositivo(s) de salida")
            print(f"    Default: {default['name']}")
            return True
        print("  Altavoz: no se encontraron dispositivos de salida")
        return False
    except Exception as e:
        print(f"  Altavoz: error ({e})")
        return False


def main():
    print("=== Boris — Diagnóstico ===\n")

    checks = [
        ("GPU", check_gpu),
        ("Ollama", check_ollama),
        ("Micrófono", check_microphone),
        ("Altavoz", check_speaker),
    ]

    results = {}
    for name, check_fn in checks:
        print(f"[{name}]")
        results[name] = check_fn()
        print()

    print("=== Resumen ===")
    all_ok = True
    for name, ok in results.items():
        status = "OK" if ok else "FALLO"
        print(f"  {name}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\nTodo en orden, mi señor.")
    else:
        print("\nHay problemas que resolver antes de proceder.")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
