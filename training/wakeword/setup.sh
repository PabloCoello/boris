#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Setup script for training a custom "boris" wake word model with openwakeword
# Run from: training/wakeword/
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Step 1/5: Clone piper-sample-generator ==="
if [ ! -d "piper-sample-generator" ]; then
    git clone https://github.com/dscripka/piper-sample-generator
    # Download the Spanish TTS model (es_ES) + English as fallback for variety
    mkdir -p piper-sample-generator/models
    echo "Downloading Piper TTS model..."
    wget -q --show-progress -O piper-sample-generator/models/en-us-libritts-high.pt \
        'https://github.com/rhasspy/piper-sample-generator/releases/download/v1.0.0/en-us-libritts-high.pt'
else
    echo "  Already cloned, skipping"
fi

echo ""
echo "=== Step 2/5: Install training dependencies ==="
# These are only needed for training, not for boris runtime
pip install piper-phonemize webrtcvad 2>/dev/null || \
    uv pip install piper-phonemize webrtcvad
pip install mutagen==1.47.0 torchinfo torchmetrics speechbrain audiomentations \
    torch-audiomentations acoustics pronouncing datasets deep-phonemizer 2>/dev/null || \
    uv pip install mutagen torchinfo torchmetrics speechbrain audiomentations \
        torch-audiomentations acoustics pronouncing datasets deep-phonemizer

echo ""
echo "=== Step 3/5: Download Room Impulse Responses ==="
if [ ! -d "mit_rirs" ]; then
    python -c "
from huggingface_hub import snapshot_download
import os, glob, shutil

# Download the dataset files directly (avoids torchcodec dependency)
path = snapshot_download('davidscripka/MIT_environmental_impulse_responses', repo_type='dataset')
os.makedirs('mit_rirs', exist_ok=True)

# Find all wav files in the downloaded snapshot and copy them
wavs = glob.glob(os.path.join(path, '**/*.wav'), recursive=True)
for i, wav in enumerate(wavs):
    shutil.copy2(wav, f'mit_rirs/rir_{i:04d}.wav')
print(f'Copied {len(wavs)} RIR files')
"
else
    echo "  Already downloaded, skipping"
fi

echo ""
echo "=== Step 4/5: Download background audio ==="
if [ ! -d "background_clips" ]; then
    mkdir -p background_clips

    python -c "
from huggingface_hub import snapshot_download
import os, glob, shutil

# AudioSet — download a small balanced subset
print('  Downloading AudioSet sample...')
path = snapshot_download(
    'agkphysics/AudioSet',
    repo_type='dataset',
    allow_patterns='data/bal_train00.tar',
)
# Extract the tar
import tarfile
tars = glob.glob(os.path.join(path, '**/*.tar'), recursive=True)
for t in tars:
    with tarfile.open(t) as tf:
        tf.extractall('background_clips')
print(f'  AudioSet extracted from {len(tars)} tar(s)')

# FMA — download a few music clips for background noise variety
print('  Downloading FMA sample...')
os.makedirs('background_clips/fma', exist_ok=True)
try:
    path = snapshot_download(
        'rudraml/fma',
        repo_type='dataset',
        allow_patterns='data/fma_small/000/*.mp3',
    )
    mp3s = glob.glob(os.path.join(path, '**/*.mp3'), recursive=True)[:200]
    for i, mp3 in enumerate(mp3s):
        shutil.copy2(mp3, f'background_clips/fma/fma_{i:04d}.mp3')
    print(f'  Copied {len(mp3s)} FMA clips')
except Exception as e:
    print(f'  FMA download failed ({e}), continuing with AudioSet only')
"
else
    echo "  Already downloaded, skipping"
fi

echo ""
echo "=== Step 5/5: Download pre-computed features ==="
if [ ! -f "openwakeword_features_ACAV100M_2000_hrs_16bit.npy" ]; then
    echo "  Downloading ACAV100M features (~2GB)..."
    wget -q --show-progress \
        'https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/openwakeword_features_ACAV100M_2000_hrs_16bit.npy'
else
    echo "  Already downloaded, skipping"
fi

if [ ! -f "validation_set_features.npy" ]; then
    echo "  Downloading validation features..."
    wget -q --show-progress \
        'https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/validation_set_features.npy'
else
    echo "  Already downloaded, skipping"
fi

echo ""
echo "============================================"
echo "Setup complete! Now run train.sh to train."
echo "============================================"
