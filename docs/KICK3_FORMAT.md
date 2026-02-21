# Kick 3 Preset Format Specification

## File Format

- **Type**: XML 1.0
- **Encoding**: UTF-8
- **Line endings**: CRLF (`\r\n`)
- **Extension**: `.preset`

## Top-Level Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Kick3>
  <PARAMS>
    <!-- 1006 PARAM elements -->
    <PARAM id="paramName" value="floatValue"/>
  </PARAMS>
  <DATA ...48 attributes...>
    <!-- Envelope elements -->
    <Slot0_AmpEnvelope>
      <node x="..." y="..." c="..." isKeytracked="0" isPhaseLocked="0" lockedPhaseValue="0.0"/>
    </Slot0_AmpEnvelope>
    <Slot0_PitchEnvelope>...</Slot0_PitchEnvelope>
    <!-- Slots 1-4 similar -->
    <fxs>
      <FxSettings IRFile="..." FxId="master0"/>
      <!-- 6 total: master0, master1, insert0_0, insert0_1, insert1_0, insert1_1 -->
    </fxs>
    <macros>
      <MacroSettings .../>
      <!-- 4 total -->
    </macros>
    <FxSettings/>
  </DATA>
</Kick3>
```

## PARAMS Section — Complete Parameter List

### Master Parameters (15)

| ID | Type | Range | Default | Description |
|---|---|---|---|---|
| `masterLength` | float | 50-2000 | 300.0 | Kick duration in milliseconds |
| `singleLengthMode` | bool | 0/1 | 1.0 | All slots share master length |
| `outGain` | float | -inf to +12 | 0.0 | Output gain in dB |
| `outGainPosition` | float | 0-1 | 1.0 | Gain stage position |
| `masterPan` | float | -1 to 1 | 0.0 | Master stereo pan |
| `tuning` | float | -24 to 24 | 0.0 | Master tuning in semitones |
| `pitchWheelRange` | float | 0-24 | 7.0 | Pitch wheel range |
| `processingMode` | float | 0-2 | 1.0 | Processing quality mode |
| `gate` | float | 0-1 | 0.0 | Gate threshold |
| `retrig` | float | 0/1 | — | Retrigger mode |
| `retrigPriority` | float | — | — | Retrigger priority |
| `portaTime` | float | 0-5000 | — | Portamento time (ms) |
| `slideEnable` | float | 0/1 | — | Slide enable |
| `triggerListen` | float | 0/1 | — | Trigger listen mode |
| `velocitySensitivity` | float | 0-1 | — | Velocity sensitivity |
| `internal_param` | float | — | — | Internal state |
| `effectsEnabled` | float | 0/1 | — | Global FX enable |

### Limiter (4)

| ID | Type | Range | Default | Description |
|---|---|---|---|---|
| `Lim_Enable` | bool | 0/1 | 1.0 | Limiter on/off |
| `Lim_Threshold` | float | -30 to 0 | 0.0 | Threshold in dB |
| `Lim_Lookahead` | float | 0-1 | 1.0 | Lookahead amount |
| `Lim_Release` | float | 0-1 | 1.0 | Release time |

### Master EQ (17)

| ID Pattern | Description |
|---|---|
| `EQ_Enable` | Master EQ on/off |
| `EQ_bandN_Enable` | Band N enable (N=1-4) |
| `EQ_bandN_Freq` | Band N frequency (Hz) |
| `EQ_bandN_Gain` | Band N gain (dB) |
| `EQ_bandN_Q` | Band N Q factor |

Default frequencies: 50, 200, 1000, 5000 Hz. Default Q: 0.707.

### Oscillator Slots (5 slots × ~48 params = ~240)

Each slot (N=1-5) has:

| ID Pattern | Type | Description |
|---|---|---|
| `SlotN_Type` | float | 0.0=Off, 1.0=Sine, 2.0=Sample |
| `SlotN_Gain` | float | Gain in dB |
| `SlotN_Mute` | bool | Mute toggle |
| `SlotN_Solo` | bool | Solo toggle |
| `SlotN_Pan` | float | Stereo pan (-1 to 1) |
| `SlotN_Tone` | float | Tonal character |
| `SlotN_Keytrack` | float | Keytracking amount |
| `SlotN_SelectiveKeytrack` | float | Selective keytracking |
| `SlotN_Loop` | float | Loop mode |
| `SlotN_StartPoint` | float | Sample start position |
| `SlotN_EndPoint` | float | Sample end position |
| `SlotN_PhaseOffset` | float | Phase offset |
| `SlotN_PhaseInvert` | bool | Phase inversion |
| `SlotN_PhaseLockOffset` | float | Phase lock offset |
| `SlotN_HarmoGain` | float | Harmonics gain |
| `SlotN_PitchEnvMax` | float | Max frequency (Hz) for pitch env |
| `SlotN_PitchEnvRangeMax` | float | Pitch range max |
| `SlotN_PitchSemi` | float | Semitone offset |
| `SlotN_PitchNode1-8_x` | float | Coarse pitch node X (0-1) |
| `SlotN_PitchNode1-8_y` | float | Coarse pitch node Y (0-1) |
| `SlotN_AmpEnvMaxLen` | float | Amp envelope length (ms) |
| `SlotN_AmpNode1-8_x` | float | Coarse amp node X (0-1) |
| `SlotN_AmpNode1-8_y` | float | Coarse amp node Y (0-1) |
| `SlotN_SubDecay01-08` | float | Sub harmonic decay per harmonic |
| `SlotN_SubHarmo01-08` | float | Sub harmonic level per harmonic |

### Macros (4)

| ID | Description |
|---|---|
| `macro1` - `macro4` | Macro control values |

### Sidechain (9)

| ID | Description |
|---|---|
| `SideChainTrigActive` | Sidechain trigger enable |
| `SideChainTrigRetrigRetThresh` | Retrigger threshold |
| ... | (7 more sidechain params) |

### FX Inserts (326 params)

Two FX inserts, each with 2 slots, each slot having:
- Routing: `FXInsertN_OscM_Routed` (which oscillators feed into this insert)
- BitCrush: Depth, Drive, Mix, Rate
- Distortion: Drive, Mix, Type
- Filter: Cutoff, Resonance, Type
- EQ: 4-band parametric (Enable, Freq, Gain, Q per band)
- Waveshaper: Multiple parameters
- Compressor: Attack, Release, Ratio, Threshold
- And more FX types

Pattern: `FXInsertI_SlotJ_FXType_Param` where I=1-2, J=1-2.

### Master FX (158 params)

Same FX types as inserts but for the master chain.
Pattern: `MstrFXSlotJ_FXType_Param` where J=1-2.

## DATA Section

### Attributes (48)

File references for samples, sub harmonics, curve files per slot:

| Attribute Pattern | Description |
|---|---|
| `slotN_File` | Sample audio data (base64 for loaded samples, `////////` for empty) |
| `slotN_FileDirty` | Whether file needs reload (0/1) |
| `slotN_SubFile` | Sub harmonics file path |
| `slotN_SubFullFile` | Full sub data (can be very large base64) |
| `slotN_SubFullFileDirty` | Sub file state |
| `slotN_AmpCurveFile` | Amplitude curve file |
| `slotN_AmpCurveFileDirty` | Amp curve state |
| `slotN_PitchCurveFile` | Pitch curve file |
| `slotN_PitchCurveFileDirty` | Pitch curve state |
| `masterFile` | Master audio file |

Note: `N` in DATA attributes is **0-based** (slot0-slot4), while PARAMS use **1-based** (Slot1-Slot5).

### Envelope Elements

10 envelope elements (2 per slot × 5 slots):

```
Slot0_AmpEnvelope     (maps to Slot1 in PARAMS)
Slot0_PitchEnvelope
Slot1_AmpEnvelope     (maps to Slot2 in PARAMS)
Slot1_PitchEnvelope
...
Slot4_AmpEnvelope     (maps to Slot5 in PARAMS)
Slot4_PitchEnvelope
```

#### Node Format

```xml
<node x="0.15" y="0.42" c="-0.06" isKeytracked="0" isPhaseLocked="0" lockedPhaseValue="0.0"/>
```

| Attribute | Range | Description |
|---|---|---|
| `x` | 0.0 – 1.0 | Time position (normalized to total duration) |
| `y` | 0.0 – 1.0 | Value (pitch: fraction of PitchEnvMax; amp: linear amplitude) |
| `c` | -1.0 – 1.0 | Curve tension (0=linear, <0=concave/fast, >0=convex/slow) |
| `isKeytracked` | 0/1 | Node follows MIDI note |
| `isPhaseLocked` | 0/1 | Phase lock enabled |
| `lockedPhaseValue` | float | Locked phase value |

### FX Settings

```xml
<fxs>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="master0"/>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="master1"/>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="insert0_0"/>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="insert0_1"/>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="insert1_0"/>
  <FxSettings IRFile="Factory/IR/Techno 1.aif" FxId="insert1_1"/>
</fxs>
```

FxId mapping:
- `master0/1` — Master FX slots 1-2
- `insert0_0/1` — FX Insert 1, slots 1-2
- `insert1_0/1` — FX Insert 2, slots 1-2

### Macros

```xml
<macros>
  <MacroSettings ...attributes.../>  <!-- 4 total -->
</macros>
```

### Global FxSettings

```xml
<FxSettings/>  <!-- Empty element, global FX state -->
```

## Index Mapping Gotcha

**PARAMS use 1-based slot numbering**, **DATA uses 0-based**:

| PARAMS | DATA | Description |
|---|---|---|
| `Slot1Type` | `Slot0_AmpEnvelope` | First oscillator |
| `Slot2Type` | `Slot1_AmpEnvelope` | Second oscillator |
| `Slot5Type` | `Slot4_AmpEnvelope` | Fifth oscillator |
