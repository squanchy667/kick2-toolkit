# Kick Creation Workflow Guide

## Method 1: Clone & Modify (Recommended)

Start from an existing preset you like, parse it, modify parameters, regenerate.

### Step 1: Parse the reference preset

```bash
python3 scripts/kick2_parser.py reference.preset --summary --output reference.json
```

This gives you the full parameter breakdown and a JSON you can edit.

### Step 2: Copy and modify the JSON

```bash
cp reference.json my_kick.json
```

Edit `my_kick.json` — the key sections to modify:

**Change the pitch sweep:**
```json
"pitch_envelope": {
  "max_freq_hz": 20000,
  "nodes": [
    {"x": 0.0,   "y": 0.42,  "c": 0.0},     // Start frequency: y × 20000 Hz
    {"x": 0.015, "y": 0.32,  "c": -0.06},    // First drop (negative c = fast)
    ...
    {"x": 1.0,   "y": 0.030, "c": 0.0}       // End frequency
  ]
}
```

**Change the amplitude shape:**
```json
"amp_envelope": {
  "max_length_ms": 200.0,
  "nodes": [
    {"x": 0.0,   "y": 0.05,  "c": 0.0},    // Start (near silent)
    {"x": 0.008, "y": 0.88,  "c": 0.0},     // Attack peak
    ...
    {"x": 0.96,  "y": 0.0,   "c": 0.0}      // End (silence)
  ]
}
```

**Change duration:**
```json
"master": {
  "length_ms": 200.0
}
```

### Step 3: Generate Kick 3 preset

```bash
python3 scripts/kick3_generator.py my_kick.json \
  --template reference.preset \
  --output my_kick.preset
```

### Step 4: Preview (optional)

```bash
python3 scripts/kick2_renderer.py my_kick.json --output preview.wav
```

### Step 5: Load in Kick 3

Copy `my_kick.preset` to your Kick 3 presets folder and load it.

---

## Method 2: Quick Generate

Create a kick from basic parameters without editing JSON manually.

```bash
python3 kick2.py quick <start_hz> <end_hz> <length_ms> [options]
```

### Examples

```bash
# Full-on psy kick
python3 kick2.py quick 16000 1800 300 --curve exponential --shape punchy

# Progressive kick
python3 kick2.py quick 8000 600 200 --curve exponential --shape sustain

# Hi-tech kick
python3 kick2.py quick 17000 2000 150 --curve exponential --shape short

# Deep techno
python3 kick2.py quick 3000 60 400 --curve exponential --shape sustain --no-click
```

**Note**: Quick-generated presets use Kick 2 format. To get Kick 3 format, use the quick-generate to create a JSON config, then feed it through the Kick 3 generator with a template.

### Quick → Kick 3 Pipeline

```bash
# 1. Generate JSON config
python3 kick2.py quick 8000 600 200 -o temp.preset
# This also creates temp_preview.wav

# 2. Convert the temp preset's config to Kick 3
python3 scripts/kick3_generator.py my_config.json \
  --template presets/templates/LIKE_BRISBANE.preset \
  --output my_kick_k3.preset
```

---

## Method 3: From Scratch (JSON)

Write a minimal JSON config and generate. See `examples/simple_psy_kick.json`:

```json
{
  "length_ms": 300,
  "pitch_start_hz": 15000,
  "pitch_end_hz": 1800,
  "pitch_curve": "exponential",
  "amp_shape": "punchy",
  "click_layer": true,
  "click_decay_pct": 50,
  "gain_db": 0,
  "limiter": true
}
```

```bash
python3 scripts/kick2_generator.py simple_config.json --simple --output simple.preset
```

---

## Method 4: Full Roundtrip

Parse → render → regenerate in one command:

```bash
python3 kick2.py roundtrip reference.preset -o output_dir/
```

Creates:
- `reference_parsed.json` — Full parameter dump
- `reference_render.wav` — Audio preview
- `reference_regenerated.preset` — Regenerated preset file

---

## Parameter Cheat Sheet

### Quick pitch frequency reference

| Y value | Frequency (at PitchEnvMax=20000) |
|---|---|
| 0.90 | 18,000 Hz |
| 0.80 | 16,000 Hz |
| 0.50 | 10,000 Hz |
| 0.30 | 6,000 Hz |
| 0.15 | 3,000 Hz |
| 0.10 | 2,000 Hz |
| 0.05 | 1,000 Hz |
| 0.03 | 600 Hz |
| 0.005 | 100 Hz |
| 0.003 | 60 Hz |

### Curve tension reference

| c value | Effect | Use case |
|---|---|---|
| -0.15 | Very concave (snappy) | Aggressive attack on first pitch segment |
| -0.05 | Slightly concave | Smooth natural decay |
| 0.0 | Linear | Default, steady transition |
| +0.05 | Slightly convex | Lazy, building transition |
| +0.15 | Very convex | Unusual, "reverse swell" feel |

### Gain reference

| dB | Character |
|---|---|
| 0.0 | Unity gain |
| 0.5-1.0 | Subtle boost |
| 1.2-1.5 | Noticeable presence |
| 2.0+ | Hot, may need limiter |

---

## Troubleshooting

### Preset won't load in Kick 3
- Check root element is `<Kick3>` not `<Kick2PresetFile>`
- Ensure PARAMS tag is `<PARAMS>` (uppercase)
- Verify 1006 PARAM elements exist
- Use the template-based generator (`kick3_generator.py`)

### Kick sounds thin/weak
- Increase sustain phase in amp envelope (raise y values in 40-80% time range)
- Lower the pitch end frequency (try y=0.003 for deeper sub)
- Add a body rise in the amplitude envelope

### Kick is too clicky
- Lower click layer gain (Slot 2 gain)
- Shorten click layer amp decay
- Lower pitch envelope start frequency

### Kick tail is too abrupt
- Add more nodes in the final 15% of the amp envelope
- Use gradual decay (0.7 → 0.5 → 0.3 → 0.1 → 0.0) instead of sharp cutoff

### Click layer doesn't load (sample missing)
- Expected behavior when generating from template
- Load a click sample manually in Kick 3's UI
- Or use the sine oscillator's high initial pitch as the click instead
