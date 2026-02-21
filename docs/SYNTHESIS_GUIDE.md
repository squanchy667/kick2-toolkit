# Kick Drum Synthesis Guide

## How Kick 2/3 Synthesizes Kicks

Kick 2/3 uses **pitch-swept sine wave synthesis** — the same fundamental technique used across most electronic kick drum design. A sine wave starts at a high frequency and rapidly sweeps down to a low fundamental, creating the characteristic "boom" of a kick drum.

## The Two Core Envelopes

### 1. Pitch Envelope — The "Character"

The pitch envelope defines **what frequencies the sine wave passes through over time**. This is the single most important factor in kick character.

```
Frequency (Hz)
  16000 |●
        |  ╲
   8000 |    ╲
        |      ╲___
   2000 |           ╲_______
        |                    ●
     0  |________________________
        0ms    100ms    200ms  300ms
```

#### Key Regions

| Region | Frequency Range | Character |
|---|---|---|
| **Click/Transient** | 8000-16000+ Hz | The initial "tick" or "click" — attack definition |
| **Upper Body** | 2000-8000 Hz | Tonal character, "singing" quality |
| **Lower Body** | 200-2000 Hz | The "punch" and weight |
| **Fundamental** | 30-200 Hz | Sub bass, the "thump" you feel |

#### Sweep Speed = Genre

| Genre | Start Freq | End Freq | Sweep Time | Character |
|---|---|---|---|---|
| **Full-On Psy** | 12-16 kHz | 1500-2000 Hz | 250-350ms | Aggressive, clicky, driving |
| **Dark Psy** | 10-14 kHz | 800-1500 Hz | 200-300ms | Growling, distorted |
| **Hi-Tech** | 14-18 kHz | 2000-3000 Hz | 150-200ms | Short, snappy, percussive |
| **Progressive** | 6-10 kHz | 400-800 Hz | 200-350ms | Deep, round, melodic |
| **Techno** | 4-8 kHz | 40-60 Hz | 200-400ms | Deep sub, minimal click |
| **House** | 2-6 kHz | 50-100 Hz | 150-300ms | Rounded, warm |

#### Curve Shape Matters

The **curve tension** (`c` parameter) controls how the pitch transitions between nodes:

- `c = 0.0` — **Linear**: Constant rate of descent
- `c < 0` — **Concave**: Fast start, slow finish (common for attack phase)
- `c > 0` — **Convex**: Slow start, fast finish (uncommon, "lazy" attack)

Most psy trance kicks use **negative curvature on the first segment** (c ≈ -0.05 to -0.15) for a snappy attack that quickly enters the tonal body range.

### 2. Amplitude Envelope — The "Shape"

The amplitude envelope defines **how loud the kick is at each point in time**.

```
Amplitude
  1.0 |    ●
      |   / \
  0.7 |  /   \_____●●●●__
      | /                  \
  0.3 |/                    \
      |                      \●
  0.0 |●________________________
      0ms    100ms    200ms  300ms
```

#### Typical Amplitude Phases

1. **Attack** (0-5ms): Rapid rise from near-zero to peak. Should be fast (1-5ms) for punch.
2. **Initial Peak** (3-15ms): Maximum amplitude. The "hit" of the kick.
3. **Post-Attack Dip** (15-80ms): Energy dips after the transient — creates the perception of "snap".
4. **Body Rise** (80-200ms): Second energy phase — the sustained "weight". This is where psy trance kicks differ from techno kicks.
5. **Sustain** (varies): A plateau that defines how "thick" the kick sounds.
6. **Decay/Release** (final 10-20%): How the kick ends. Sharp cutoff vs. smooth fade changes the groove feel.

#### The "Double Bump" Shape

Many psy trance kicks have a characteristic **double bump** amplitude envelope:

```
  ●
 / \          ●●●●
/   \   ●●   /    \
     \ /  \ /      \
      ●    ●        \●
```

This creates an initial transient hit, a dip, and then a second body swell that gives the kick its "driving" quality. The Brisbane preset demonstrates this with its 42-node hand-drawn curve.

## The Click Layer

Most Kick 2/3 presets use a **second oscillator slot** for the transient/click:

- **Slot 1**: Sine wave with pitch sweep (the main body)
- **Slot 2**: Sample or noise burst (the click)

The click layer:
- Has **no pitch envelope** (flat, or very short sweep)
- Has a **short amplitude envelope** (decays to zero within 10-50% of total duration)
- Provides the high-frequency transient that makes the kick "cut through"
- Is routed to a **separate FX insert** for independent processing

### Click Design by Genre

| Genre | Click Start Gain | Click Decay | Character |
|---|---|---|---|
| Full-On Psy | 1.0-1.5 dB | 30-50% of duration | Aggressive, defined |
| Progressive | 0.5-1.0 dB | 15-25% of duration | Soft, blended |
| Dark Psy | 1.0-2.0 dB | 20-40% | Sharp, often distorted |
| Hi-Tech | 1.5-2.5 dB | 10-20% | Very short, percussive |

## Designing Kicks for Specific BPMs

The kick length must fit within the beat grid without overlapping:

| BPM | Beat Length | Recommended Kick | Space for Sidechain |
|---|---|---|---|
| 138 | 435ms | 180-220ms | 215-255ms |
| 145 | 414ms | 200-280ms | 134-214ms |
| 150 | 400ms | 200-300ms | 100-200ms |
| 160 | 375ms | 150-250ms | 125-225ms |
| 180 | 333ms | 120-200ms | 133-213ms |
| 200 | 300ms | 100-180ms | 120-200ms |

**Rule of thumb**: Kick length should be 50-75% of beat length for psy trance. Shorter kicks leave more room for bass groove.

## Pitch Envelope Design Recipes

### Recipe: Classic Full-On Psy (like Brisbane)

```json
{
  "nodes": [
    {"x": 0.0,   "y": 0.79, "c": 0.0},
    {"x": 0.037, "y": 0.52, "c": -0.10},
    {"x": 0.156, "y": 0.36, "c": 0.0},
    {"x": 0.490, "y": 0.21, "c": 0.0},
    {"x": 0.827, "y": 0.09, "c": -0.04},
    {"x": 1.0,   "y": 0.09, "c": 0.0}
  ],
  "max_freq_hz": 20000
}
```
Start high (15.8kHz), steep initial drop with negative curvature, long gradual tail to 1.8kHz.

### Recipe: Progressive Melodic

```json
{
  "nodes": [
    {"x": 0.0,   "y": 0.42,  "c": 0.0},
    {"x": 0.015, "y": 0.32,  "c": -0.06},
    {"x": 0.06,  "y": 0.22,  "c": -0.04},
    {"x": 0.15,  "y": 0.14,  "c": -0.03},
    {"x": 0.35,  "y": 0.075, "c": -0.02},
    {"x": 0.55,  "y": 0.048, "c": -0.015},
    {"x": 0.75,  "y": 0.035, "c": -0.01},
    {"x": 1.0,   "y": 0.030, "c": 0.0}
  ],
  "max_freq_hz": 20000
}
```
Lower start (8.4kHz), many nodes for smooth melodic sweep, lands at 600Hz.

### Recipe: Short Hi-Tech

```json
{
  "nodes": [
    {"x": 0.0,  "y": 0.85, "c": 0.0},
    {"x": 0.02, "y": 0.50, "c": -0.15},
    {"x": 0.10, "y": 0.20, "c": -0.08},
    {"x": 0.40, "y": 0.12, "c": 0.0},
    {"x": 1.0,  "y": 0.10, "c": 0.0}
  ],
  "max_freq_hz": 20000
}
```
Very high start (17kHz), aggressive concave drop, quick settle at 2kHz.

### Recipe: Deep Techno Sub

```json
{
  "nodes": [
    {"x": 0.0,  "y": 0.15, "c": 0.0},
    {"x": 0.01, "y": 0.08, "c": -0.05},
    {"x": 0.05, "y": 0.004, "c": 0.0},
    {"x": 1.0,  "y": 0.003, "c": 0.0}
  ],
  "max_freq_hz": 20000
}
```
Low start (3kHz), rapid drop to 60Hz sub fundamental.

## Tips for AI-Assisted Kick Design

1. **Start with a recipe close to your target genre**, then adjust
2. **The first 5% of the pitch envelope is 80% of the character** — focus tweaks there
3. **Amplitude envelope node count affects smoothness** — 12-25 nodes is the sweet spot for hand-tunable curves, 40+ for waveform-analyzed shapes
4. **Always use negative curvature on the first pitch segment** — linear pitch drops sound unnatural
5. **The fundamental frequency should match your track's key** — use `tuning` parameter to fine-tune
6. **Click layer gain scales inversely with BPM** — faster tempos need less click to avoid clutter
7. **Test in context** — a kick that sounds great solo may not sit well in a mix
