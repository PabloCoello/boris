#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Train the "boris" wake word model
# Run from: training/wakeword/
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

OWW_TRAIN="$(python -c 'import openwakeword; import os; print(os.path.join(os.path.dirname(openwakeword.__file__), "train.py"))')"

echo "=== Phase 1/3: Generate synthetic clips ==="
python "$OWW_TRAIN" --training_config boris_model.yml --generate_clips

echo ""
echo "=== Phase 2/3: Augment clips ==="
python "$OWW_TRAIN" --training_config boris_model.yml --augment_clips

echo ""
echo "=== Phase 3/3: Train model ==="
python "$OWW_TRAIN" --training_config boris_model.yml --train_model

echo ""
echo "============================================"
echo "Training complete!"
echo "Model saved to: output/boris/"
echo ""
echo "To use it in Boris, copy the .onnx file:"
echo "  cp output/boris/boris.onnx ../../data/models/boris_wakeword.onnx"
echo ""
echo "Then set in config.yaml:"
echo "  assistant:"
echo "    wake_word_model: data/models/boris_wakeword.onnx"
echo "============================================"
