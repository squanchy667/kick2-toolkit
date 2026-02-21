# Kick 2 Toolkit JSON Schema

## Full Preset JSON (output of parser, input to generator)

```json
{
  "meta": {
    "plugin_version": "1.5.3",
    "source_file": "LIKE_BRISBANE.preset"
  },
  "master": {
    "length_ms": 297.38,
    "single_length_mode": true,
    "output_gain_db": 0.0,
    "output_gain_position": 1.0,
    "pan": 0.0,
    "tuning_semitones": 0.0,
    "pitch_wheel_range": 7.0,
    "processing_mode": 1.0,
    "gate": 0.0
  },
  "limiter": {
    "enabled": true,
    "threshold_db": 0.0,
    "lookahead": 1.0,
    "release": 1.0
  },
  "slots": [
    {
      "slot_number": 1,
      "type": "sine",          // "off" | "sine" | "sample"
      "type_value": 1.0,
      "gain_db": 1.38,
      "muted": false,
      "active": true,
      "pitch_envelope": {
        "max_freq_hz": 20000,
        "semitone_offset": 0.0,
        "range_max": 100.0,
        "nodes": [             // detailed nodes from EnvelopeData
          {"x": 0.0, "y": 0.79, "c": 0.0},
          {"x": 0.037, "y": 0.52, "c": -0.1},
          // ...
        ],
        "coarse_nodes": [...], // 8 coarse nodes from Params
        "calculated_frequencies": [
          {"time_normalized": 0.0, "time_ms": 0.0, "freq_hz": 15800, "y_raw": 0.79}
          // ...
        ]
      },
      "amp_envelope": {
        "max_length_ms": 297.38,
        "nodes": [
          {"x": 0.0, "y": 0.23, "c": 0.0},
          // ...42 nodes for detailed shape
        ],
        "coarse_nodes": [...]
      }
    }
    // ... up to 5 slots
  ],
  "fx_routing": {
    "insert1": {
      "osc1": true,
      "osc2": false,
      "slot1_type": 0.0,
      "slot1_gain": 0.0
    },
    "insert2": {
      "osc1": false,
      "osc2": true
    },
    "master_fx": {
      "slot1_type": 0.0,
      "slot1_gain": 0.0
    }
  }
}
```

## Simple Config JSON (for quick kick generation)

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
  "limiter": true,
  "tuning": 0
}
```

### pitch_curve options
- `"exponential"` — Classic psy trance exponential pitch sweep
- `"linear"` — Straight line pitch drop
- `[nodes]` — Custom array of `{x, y, c}` nodes

### amp_shape options
- `"punchy"` — Psy trance punch with sustain bump and sharp tail
- `"sustain"` — Long sustained body with smooth decay
- `"short"` — Short punchy kick
- `[nodes]` — Custom array of `{x, y, c}` nodes

## Envelope Node Format

```json
{
  "x": 0.0,    // Time position (0.0 = start, 1.0 = end)
  "y": 0.79,   // Value (pitch: fraction of max_freq_hz, amp: 0-1 amplitude)  
  "c": -0.1    // Curve: 0=linear, <0=concave (fast start), >0=convex (slow start)
}
```
