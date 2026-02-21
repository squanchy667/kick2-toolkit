# Reverse Engineering the Kick 3 Preset Format

## Context

This document records the process of reverse-engineering Sonic Academy Kick 3's `.preset` file format, starting from a single preset file: `LIKE_BRISBANE.preset`.

The goal was to understand the format well enough to:
1. Parse any preset and extract all synthesis parameters
2. Generate new presets that Kick 3 can load and play
3. Render audio previews without needing the plugin

## Phase 1: Initial File Analysis

### File identification
```
File: LIKE_BRISBANE.preset
Type: XML 1.0, UTF-8
Line endings: CRLF (\r\n)
```

### Root structure discovery
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Kick3>
  <PARAMS>
    <PARAM id="..." value="..."/>
    <!-- 1006 PARAM elements -->
  </PARAMS>
  <DATA ...attributes...>
    <Slot0_AmpEnvelope>
      <node x="..." y="..." c="..." isKeytracked="0" isPhaseLocked="0" lockedPhaseValue="0.0"/>
    </Slot0_AmpEnvelope>
    <!-- More envelopes, fxs, macros, FxSettings -->
  </DATA>
</Kick3>
```

**Key discovery**: The root element is `<Kick3>`, not `<Kick2PresetFile>`. This preset was from Kick 3, not Kick 2. The format has significant structural differences from Kick 2.

## Phase 2: Parameter Mapping

### Total parameter count: 1006

Parameters were grouped by prefix analysis:

| Group | Count | Purpose |
|---|---|---|
| `EQ_*` | 17 | Master EQ (4-band) |
| `FXInsert*` | 326 | Two FX insert chains (2 slots each, with EQ, distortion, bitcrush, etc.) |
| `MstrFX*` | 158 | Master FX chain (2 slots) |
| `Slot1-5*` | ~400 | 5 oscillator slots (type, gain, pitch/amp nodes, harmonics, phase, etc.) |
| `Lim_*` | 4 | Output limiter |
| `SideChain*` | 9 | Sidechain trigger settings |
| Master params | ~15 | Length, gain, tuning, gate, portamento, velocity, etc. |

### Oscillator Slot Parameters (per slot)

Each of the 5 slots has:
```
SlotN_Type              — 0.0=Off, 1.0=Sine, 2.0=Sample
SlotN_Gain              — Output gain in dB
SlotN_Mute              — Mute toggle
SlotN_Solo              — Solo toggle
SlotN_Pan               — Stereo pan
SlotN_Tone              — Tonal character
SlotN_Keytrack          — Pitch keytracking
SlotN_SelectiveKeytrack — Selective keytracking
SlotN_Loop              — Loop mode
SlotN_StartPoint        — Sample start
SlotN_EndPoint          — Sample end
SlotN_PhaseOffset       — Phase offset
SlotN_PhaseInvert       — Phase inversion
SlotN_PhaseLockOffset   — Phase lock
SlotN_HarmoGain         — Harmonics gain

SlotN_PitchEnvMax       — Maximum frequency for pitch envelope (Hz)
SlotN_PitchEnvRangeMax  — Pitch range max (semitones or %)
SlotN_PitchSemi         — Semitone offset
SlotN_PitchNode1-8_x    — Coarse pitch envelope X positions
SlotN_PitchNode1-8_y    — Coarse pitch envelope Y values

SlotN_AmpEnvMaxLen      — Amplitude envelope max length (ms)
SlotN_AmpNode1-8_x      — Coarse amplitude envelope X positions
SlotN_AmpNode1-8_y      — Coarse amplitude envelope Y values

SlotN_SubDecay01-08     — Sub harmonic decay values
SlotN_SubHarmo01-08     — Sub harmonic amplitude values
```

### Pitch Envelope Calculation

The pitch envelope Y values are **normalized fractions of PitchEnvMax**:

```
actual_frequency_hz = y_value * PitchEnvMax
```

Example from Brisbane:
- `PitchEnvMax = 20000 Hz`
- Node 0: `y = 0.7899` → `0.7899 × 20000 = 15,798 Hz`
- Node 5: `y = 0.0902` → `0.0902 × 20000 = 1,804 Hz`

### Amplitude Envelope

Y values are direct amplitude (0.0 = silence, 1.0 = full). The time axis is normalized (0.0 = start, 1.0 = end of `AmpEnvMaxLen` milliseconds).

## Phase 3: DATA Element Structure

The `<DATA>` element contains:

### Attributes (48 total)
```
masterFile              — Master sample file path (or "////////" for none)
masterFileDirty         — Whether master file needs regeneration
slotN_File              — Sample file data (can be huge base64 for sample slots)
slotN_FileDirty         — File state flag
slotN_SubFile           — Sub harmonic file path
slotN_SubFullFile       — Full sub file data (base64-encoded)
slotN_SubFullFileDirty  — Sub file state
slotN_AmpCurveFile      — Amp curve file path
slotN_AmpCurveFileDirty — Amp curve state
slotN_PitchCurveFile    — Pitch curve file path
slotN_PitchCurveFileDirty — Pitch curve state
```

**Critical finding**: `slot1_File` (the click layer sample) contained **72,341 characters** of base64-encoded audio data. This is the analyzed click sample embedded directly in the preset.

### Child Elements

```xml
<DATA>
  <Slot0_AmpEnvelope>    <!-- 42 nodes (detailed hand-drawn envelope) -->
  <Slot0_PitchEnvelope>  <!-- 6 nodes -->
  <Slot1_AmpEnvelope>    <!-- 2 nodes (simple decay) -->
  <Slot1_PitchEnvelope>  <!-- 2 nodes (flat) -->
  <Slot2-4_*Envelope>    <!-- 2 nodes each (default/inactive) -->
  <fxs>                  <!-- 6 FxSettings children (IR file references) -->
  <macros>               <!-- 4 MacroSettings children -->
  <FxSettings/>          <!-- Empty (global FX settings) -->
</DATA>
```

### Envelope Node Format (Kick 3)
```xml
<node x="0.004886" y="0.623779" c="0.0" 
      isKeytracked="0" isPhaseLocked="0" lockedPhaseValue="0.0"/>
```

- `x` — Time position (0.0 to 1.0, normalized)
- `y` — Value (pitch: fraction of PitchEnvMax; amp: 0.0-1.0 amplitude)
- `c` — Curve tension (-1.0 to 1.0; 0=linear, negative=concave, positive=convex)
- `isKeytracked` — Whether node follows MIDI key (0/1)
- `isPhaseLocked` — Phase lock state (0/1)
- `lockedPhaseValue` — Phase value when locked

### Coarse vs Detailed Envelopes

Kick 3 stores envelopes in **two places**:

1. **PARAMS section**: 8 coarse nodes (`SlotN_AmpNode1-8_x/y`) — these are the "control points" visible in the basic envelope editor
2. **DATA section**: Full detailed nodes (can be 42+ nodes) — these are the actual high-resolution envelope shapes

The detailed envelope in DATA takes priority. The coarse nodes in PARAMS appear to be a simplified representation for parameter automation and basic display.

## Phase 4: The Brisbane Kick Analysis

### Architecture
```
Slot 1 (Sine):     Main kick body — sine wave with pitch sweep
Slot 2 (Sample):   Click/transient layer — analyzed click sample
Slots 3-4:         Inactive (Off)
Slot 5:            Inactive (Muted sample)
```

### Pitch Envelope (Slot 1 — 6 nodes)
```
Time    Freq (Hz)   Character
0.0ms   15,799      Initial click/transient frequency
11.1ms  10,322      Fast initial drop (c=-0.10, concave curve)
46.4ms   7,209      Continued descent through upper harmonics
145.7ms  4,203      Mid-body tone
245.8ms  1,870      Approaching fundamental (c=-0.04, slight concave)
297.4ms  1,804      Final fundamental frequency
```

### Amplitude Envelope (Slot 1 — 42 nodes)
```
Phase           Time Range    Amplitude     Character
Attack          0-3.5ms       0.23→0.83     Fast transient rise
Initial peak    3.5ms         0.83          Maximum initial impact
Post-attack dip 3.5-53ms      0.83→0.37     Energy release after impact
Trough          53-93ms       0.37          Minimum body energy
Body rise       93-165ms      0.37→0.70     Second energy phase
Sustain         165-239ms     0.70-0.73     Plateau (the "weight" of the kick)
Tail decay      239-269ms     0.73→0.01     Rapid final decay
Silence         269-297ms     0.00          Clean cutoff
```

This 42-node shape was clearly hand-drawn or imported from waveform analysis — it creates the characteristic "double bump" shape common in psy trance kicks.

### Click Layer (Slot 2)
```
Sample: "10 BD Kämpfer - Brisbane F [2025-05-05 111445]_click.wav"
Amp:    Full amplitude at start → zero at 49% (~146ms)
Pitch:  Flat (no pitch envelope)
Gain:   1.38 dB
Route:  FX Insert 2
```

### FX Routing
```
Slot 1 (Sine)   → FX Insert 1
Slot 2 (Sample)  → FX Insert 2
```

## Phase 5: Generator Strategy

### Why Template-Based Generation?

With 1006 parameters, generating a valid Kick 3 preset from scratch would require knowing the correct default value for every single parameter — FX chain settings, EQ bands, sub harmonics, sidechain config, etc.

**Solution**: Use an existing Kick 3 preset as a template. Copy the entire XML tree, then surgically replace only the parameters we care about:
- Oscillator type, gain, mute
- Pitch and amplitude envelope nodes (both coarse in PARAMS and detailed in DATA)
- Master length, tuning, gain
- Limiter settings
- FX routing

This ensures structural validity while allowing creative control over the synthesis parameters.

### Sample Data Handling

When generating new presets, we clear all sample file references:
```xml
<!-- Set all file paths to empty -->
slot0_File="////////"
slot0_FileDirty="0"
slot0_SubFullFileDirty="1"  <!-- Mark dirty so Kick 3 regenerates -->
```

Kick 3 handles missing samples gracefully — it just plays the sine oscillator without the sample layer. The user can then load their own click sample in Kick 3's UI.

## Lessons Learned

1. **Don't assume format from plugin name** — "Kick 2 preset" was actually Kick 3 format
2. **Case sensitivity matters** — `<PARAMS>` vs `<Params>`, `<node>` vs `<Node>`
3. **Envelopes live in two places** — coarse nodes in PARAMS, detailed in DATA
4. **Sample data is embedded** — Kick 3 embeds analyzed samples as base64 in DATA attributes
5. **Template approach beats from-scratch** — 1006 params with unknown defaults makes generation from scratch impractical
6. **Dirty flags matter** — Setting `*FileDirty="1"` tells Kick 3 to regenerate cached data on load
