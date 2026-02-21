---
name: kick2-toolkit
description: Reverse-engineer, parse, generate, and synthesize Kick 2 preset files (.preset). Use this skill whenever the user mentions Kick 2 presets, kick drum synthesis, .preset files from Sonic Academy Kick 2, recreating kicks from presets, pitch envelope extraction, kick design analysis, or rendering kick drums to audio. Also trigger when the user wants to build or modify psy trance kicks, analyze kick synthesis parameters, or automate Kick 2 preset creation. Covers full pipeline from preset XML parsing to WAV audio rendering.
---

# Kick 2 Preset Toolkit

A complete toolkit for reverse-engineering, analyzing, generating, and rendering Sonic Academy Kick 2 preset files.

## Overview

Kick 2 presets are XML files containing oscillator configurations, pitch/amplitude envelopes, FX routing, and master settings. This toolkit provides three main capabilities:

1. **Parse** — Extract all parameters from a `.preset` file into structured JSON
2. **Generate** — Create new `.preset` XML files from parameter definitions
3. **Render** — Synthesize the kick to a WAV audio file using extracted envelopes

## Quick Start

### Parse a preset
```bash
python3 /path/to/scripts/kick2_parser.py input.preset [--output params.json]
```

### Generate a preset from JSON
```bash
python3 /path/to/scripts/kick2_generator.py params.json [--output new.preset]
```

### Render a kick to WAV
```bash
python3 /path/to/scripts/kick2_renderer.py params.json [--output kick.wav] [--sample-rate 44100]
```

## Architecture

### Preset File Structure

Kick 2 `.preset` files are XML 1.0 with this structure:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Kick2PresetFile pluginVersion="X.X.X">
  <Params>
    <PARAM id="paramName" value="floatValue"/>
    ...
  </Params>
  <EnvelopeData>
    <Envelope id="SlotN_TypeEnvelope">
      <Node x="0.0" y="0.5" c="0.0"/>
      ...
    </Envelope>
    ...
  </EnvelopeData>
</Kick2PresetFile>
```

### Key Parameter Groups

| Group | Params | Description |
|-------|--------|-------------|
| SlotN Type/Gain/Mute | `Slot1Type`, `Slot1Gain` | Oscillator config (0=Off, 1=Sine, 2=Sample) |
| Pitch Envelope | `Slot1PitchNode*`, `Slot1PitchEnvMax` | Pitch sweep nodes + max frequency |
| Amp Envelope | `Slot1AmpNode*`, `Slot1AmpEnvMaxLen` | Amplitude shape + duration in ms |
| FX Routing | `FXInsert*Osc*Routed` | Which oscillators route to which FX |
| Master | `masterLength`, `outGain`, `tuning` | Global settings |
| Limiter | `Lim_Enable`, `Lim_Threshold` | Output limiter |

### Envelope Node Format

Each envelope node has:
- **x** (0.0–1.0): Position in time (normalized to total length)
- **y** (0.0–1.0): Value (pitch = fraction of PitchEnvMax, amp = amplitude)
- **c** (-1.0–1.0): Curve tension (0 = linear, negative = concave, positive = convex)

### Pitch Calculation

Actual frequency at any node: `freq_hz = y * PitchEnvMax`

Example: y=0.7899, PitchEnvMax=20000 → 15,798 Hz

### Synthesis Algorithm

The renderer uses this approach:
1. Generate time array for total duration (from `masterLength` or `AmpEnvMaxLen`)
2. Interpolate pitch envelope to get instantaneous frequency at each sample
3. Calculate phase by integrating frequency (cumulative sum)
4. Generate sine wave from phase
5. Apply amplitude envelope
6. Apply limiter if enabled
7. Normalize and export as WAV

For the click/sample layer (Type=2), the renderer uses a noise burst shaped by its amplitude envelope, since we don't have access to the original sample file.

## Scripts Reference

- `scripts/kick2_parser.py` — Full preset parser, outputs JSON
- `scripts/kick2_generator.py` — Preset generator from JSON parameters
- `scripts/kick2_renderer.py` — WAV audio renderer with envelope interpolation

## Typical Workflow

1. Parse existing preset → understand its parameters
2. Modify parameters (pitch curve, duration, amp shape)
3. Generate new preset file → load in Kick 2
4. Optionally render to WAV for quick preview without DAW

For details on the JSON schema used between tools, see `references/schema.md`.
