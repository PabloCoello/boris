# Entrenamiento del modelo de wake word

Boris usa un modelo custom de [openwakeword](https://github.com/dscripka/openwakeword) entrenado para la palabra "Boris". Este documento describe el proceso de entrenamiento.

## Resumen del pipeline

```
1. setup.sh     → Descarga dependencias, TTS, RIRs, background audio, features
2. train.sh     → Genera clips sinteticos, los aumenta, entrena el modelo
3. Resultado    → output/boris/boris.onnx
4. Despliegue   → cp output/boris/boris.onnx data/models/boris_wakeword.onnx
```

Todo el entrenamiento corre en local. No se necesitan muestras de voz reales — se generan sinteticamente con Piper TTS y se aumentan con ruido ambiental y reverberacion.

---

## Estructura de training/wakeword/

```
training/wakeword/
├── setup.sh                      # Descarga todo lo necesario
├── train.sh                      # Ejecuta las 3 fases del entrenamiento
├── boris_model.yml               # Configuracion del modelo
├── piper-sample-generator/       # Generador de clips sinteticos (clonado de GitHub)
├── mit_rirs/                     # Room Impulse Responses para augmentacion
├── background_clips/             # Audio de fondo (AudioSet + FMA)
├── openwakeword_features_*.npy   # Features pre-computadas (ACAV100M, ~2GB)
├── validation_set_features.npy   # Features de validacion
└── output/boris/                 # Modelo entrenado (.onnx)
```

---

## Configuracion del modelo (boris_model.yml)

| Parametro | Valor | Descripcion |
|---|---|---|
| `target_phrase` | `"boris"` | Palabra a detectar |
| `n_samples` | 20,000 | Clips positivos sinteticos |
| `n_samples_val` | 2,000 | Clips de validacion |
| `model_type` | `dnn` | Red neuronal densa (rapida, baja latencia) |
| `layer_size` | 32 | Neuronas por capa |
| `steps` | 50,000 | Pasos de entrenamiento |
| `target_false_positives_per_hour` | 0.2 | Objetivo de falsos positivos |
| `max_negative_weight` | 1,500 | Peso de negativos en la loss |

### Negativos adversarios

Se definen frases similares a "Boris" para que el modelo aprenda a distinguirlas:

```yaml
custom_negative_phrases:
  - "florís"
  - "norris"
  - "forris"
  - "morris"
  - "doris"
  - "noris"
  - "borrás"
```

---

## Paso a paso

### 1. Setup

```bash
cd training/wakeword
bash setup.sh
```

Descarga (~3-4 GB total):
- **piper-sample-generator**: generador de clips con TTS
- **Modelo Piper TTS**: `en-us-libritts-high.pt` (se usa ingles para variedad fonetica)
- **MIT RIRs**: respuestas al impulso de habitaciones reales (reverberacion)
- **Background clips**: AudioSet (ruido ambiental) + FMA (musica de fondo)
- **Features ACAV100M**: 2000 horas de audio pre-procesado para negativos (~2GB)
- **Validation features**: set de validacion para medir false positives

### 2. Entrenamiento

```bash
bash train.sh
```

Ejecuta 3 fases usando `openwakeword.train`:

1. **Generar clips**: Piper TTS sintetiza 20,000 variaciones de "Boris" con diferentes voces
2. **Aumentar clips**: Se aplica ruido de fondo, reverberacion (RIRs) y variaciones de volumen
3. **Entrenar modelo**: DNN que clasifica frames de 80ms como wake word / no wake word

Tiempo aproximado: 30-60 minutos en RTX 3090.

### 3. Desplegar

```bash
cp output/boris/boris.onnx ../../data/models/boris_wakeword.onnx
```

Configurar en `config.yaml`:

```yaml
assistant:
  wake_word_model: data/models/boris_wakeword.onnx
  wake_word_threshold: 0.3
```

---

## Ajuste de threshold

El threshold controla la sensibilidad del detector:

| Threshold | Comportamiento |
|---|---|
| `0.1 - 0.2` | Muy sensible. Detecta "Boris" casi siempre, pero puede activarse con palabras similares |
| `0.3` | **Recomendado**. Buen balance entre deteccion y falsos positivos |
| `0.5` | Default de openwakeword. Mas conservador |
| `0.7 - 0.9` | Muy estricto. Puede requerir decir "Boris" mas fuerte o claro |

Si Boris no responde al wake word, bajar el threshold. Si se activa con otras palabras, subirlo.

---

## Re-entrenamiento

Si el modelo necesita ajustes (demasiados falsos positivos, o no detecta bien):

1. Ajustar `boris_model.yml`:
   - Anadir frases negativas que causan falsos positivos
   - Aumentar `n_samples` para mas diversidad
   - Ajustar `target_false_positives_per_hour`
2. Re-ejecutar `bash train.sh`
3. Copiar el nuevo .onnx

---

## Notas

- El modelo .onnx pesa ~100KB y corre con latencia imperceptible en CPU
- openwakeword procesa frames de 80ms (1280 samples a 16kHz)
- El detector corre en un thread dedicado, independiente del bucle asyncio principal
- No se necesitan muestras de voz reales del usuario — todo es sintetico
- Los archivos grandes (features .npy, background clips) estan en `.gitignore`
