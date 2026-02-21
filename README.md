# Kick 2/3 Preset Toolkit

A complete Python toolkit for reverse-engineering, analyzing, generating, and rendering Sonic Academy **Kick 2** and **Kick 3** preset files (`.preset`).

Built as a skill/agent system for AI-assisted kick drum design — parse any preset into structured JSON, modify parameters, generate Kick 3–compatible presets, and render audio previews.

## Features

| Capability | Description |
|---|---|
| **Parse** | Extract all parameters from `.preset` → structured JSON |
| **Generate (Kick 3)** | Create Kick 3–compatible presets using a template + custom envelopes |
| **Generate (Kick 2)** | Create Kick 2–format presets from scratch or simple configs |
| **Render** | Synthesize kick to 24-bit WAV with pitch/amp envelope interpolation |
| **Roundtrip** | Full pipeline: parse → analyze → render → regenerate |
| **Quick Create** | One-liner kick generation from pitch/length/shape parameters |

## Quick Start

```bash
# Parse an existing preset
python3 scripts/kick2_parser.py my_kick.preset --summary --output parsed.json

# Generate a new Kick 3 preset (using a template)
python3 scripts/kick3_generator.py my_config.json --template presets/templates/LIKE_BRISBANE.preset --output new_kick.preset

# Render a preview WAV
python3 scripts/kick2_renderer.py parsed.json --output preview.wav

# Quick-create a psy trance kick
python3 kick2.py quick 16000 1800 300 --curve exponential --shape punchy -o quick_kick.preset
```

## Project Structure

```
kick2-toolkit/
├── README.md                          # This file
├── kick2.py                           # Unified CLI (parse/generate/render/roundtrip/quick)
├── scripts/
│   ├── kick2_parser.py                # Preset parser → JSON (Kick 2 & 3 compatible)
│   ├── kick2_generator.py             # JSON → Kick 2 format preset
│   ├── kick2_renderer.py              # JSON → WAV audio synthesis
│   └── kick3_generator.py             # JSON + template → Kick 3 format preset
├── presets/
│   ├── templates/                     # Reference presets (use as templates for Kick 3 generation)
│   │   └── LIKE_BRISBANE.preset       # Full-on psy kick template (1006 params)
│   └── generated/                     # Output presets
│       └── PROGRESSIVE_MELODIC_200.preset
├── examples/
│   ├── simple_psy_kick.json           # Simple config format example
│   └── progressive_melodic.json       # Full config for progressive kick
├── references/
│   └── schema.md                      # JSON schema documentation
├── docs/
│   ├── REVERSE_ENGINEERING.md         # How we reverse-engineered the preset format
│   ├── KICK3_FORMAT.md                # Kick 3 .preset XML format specification
│   ├── SYNTHESIS_GUIDE.md             # Kick drum synthesis theory & envelope design
│   └── WORKFLOW.md                    # Step-by-step workflow for creating new kicks
└── skill/
    └── SKILL.md                       # Claude skill definition for AI-assisted usage
```

## Requirements

- Python 3.8+
- No external dependencies (uses only stdlib: `xml`, `json`, `wave`, `struct`, `math`)

## Documentation

- **[Reverse Engineering Notes](docs/REVERSE_ENGINEERING.md)** — How the Kick 3 preset format was decoded
- **[Kick 3 Format Spec](docs/KICK3_FORMAT.md)** — Complete XML schema with all 1006 parameters
- **[Synthesis Guide](docs/SYNTHESIS_GUIDE.md)** — Pitch envelope design, amplitude shaping, layering theory
- **[Workflow Guide](docs/WORKFLOW.md)** — Step-by-step for creating kicks with this toolkit
- **[JSON Schema](references/schema.md)** — Data format between parser/generator/renderer

## Key Insight: Kick 2 vs Kick 3 Format

The original Kick 2 and newer Kick 3 use **different XML structures**:

| | Kick 2 | Kick 3 |
|---|---|---|
| Root element | `<Kick2PresetFile>` | `<Kick3>` |
| Params container | `<Params>` | `<PARAMS>` |
| Envelope location | `<EnvelopeData>` children | `<DATA>` children |
| Envelope node tag | `<Node>` | `<node>` |
| Node attributes | `x, y, c` | `x, y, c, isKeytracked, isPhaseLocked, lockedPhaseValue` |
| Param count | ~200 | **1006** (includes EQ, FX chains, sub harmonics, macros) |
| Sample data | Separate files | Base64-encoded in DATA attributes |

**The Kick 3 generator uses a template-based approach** — it takes an existing Kick 3 preset as a structural template and injects custom parameters, ensuring all 1006 params and DATA structures remain valid.

## License

MIT
