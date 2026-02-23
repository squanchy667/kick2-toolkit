#!/usr/bin/env python3
"""
Kick Questionnaire — Interactive kick drum designer for progressive psy.
Walks through musical questions and generates Kick 2/3 preset files.

Usage:
  python3 kick_questionnaire.py                        # Interactive mode
  python3 kick_questionnaire.py --recipe my.recipe.json  # Replay saved answers
  python3 kick_questionnaire.py --list                  # List saved recipes
"""

import json
import os
import sys
import argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'scripts'))

from kick2_generator import generate_preset, prettify_xml
from kick2_renderer import synthesize_kick, write_wav

try:
    from kick3_generator import load_template, apply_config, write_preset as write_k3
    HAS_KICK3 = True
except ImportError:
    HAS_KICK3 = False


# ============================================================
# CONSTANTS
# ============================================================

BANNER = r"""
 ╔══════════════════════════════════════════════════════╗
 ║       KICK DESIGNER — Progressive Psy               ║
 ║    Answer musical questions, get kick presets        ║
 ╚══════════════════════════════════════════════════════╝
"""

OUT_DIR = os.path.join(SCRIPT_DIR, 'presets', 'generated')
RECIPE_DIR = os.path.join(SCRIPT_DIR, 'recipes')
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, 'presets', 'templates', 'LIKE_BRISBANE.preset')

# Musical note frequencies (octave 1)
NOTE_FREQ = {
    'C': 32.70, 'C#': 34.65, 'Db': 34.65,
    'D': 36.71, 'D#': 38.89, 'Eb': 38.89,
    'E': 41.20, 'F': 43.65,
    'F#': 46.25, 'Gb': 46.25,
    'G': 49.00, 'G#': 51.91, 'Ab': 51.91,
    'A': 55.00, 'A#': 58.27, 'Bb': 58.27,
    'B': 61.74,
}

# ============================================================
# VIBE PRESETS — base templates for each character
# ============================================================
# Each vibe defines starting parameters that subsequent
# questions will modify.  Tweak these dicts to reshape the
# defaults the questionnaire offers.

VIBES = {
    1: {
        "name": "Deep & Hypnotic",
        "desc": "Low, meditative groove. Smooth sweep, deep body, subtle movement.",
        "pitch_start_hz": 8000,
        "pitch_end_hz": 45,
        "sweep_speed": 0.35,       # 0 = slow, 1 = fast
        "default_attack": 0.40,
        "default_body": 0.75,
        "default_body_shape": "sustained",
        "length_pct": 0.50,        # fraction of one beat
        "default_click": 0.30,
        "default_click_decay": 0.18,
    },
    2: {
        "name": "Groovy & Punchy",
        "desc": "Tight, rhythmic energy. Snappy attack, controlled body.",
        "pitch_start_hz": 10000,
        "pitch_end_hz": 50,
        "sweep_speed": 0.55,
        "default_attack": 0.70,
        "default_body": 0.55,
        "default_body_shape": "punchy",
        "length_pct": 0.48,
        "default_click": 0.60,
        "default_click_decay": 0.16,
    },
    3: {
        "name": "Melodic & Warm",
        "desc": "Round, musical quality. Gentle sweep, warm sustain.",
        "pitch_start_hz": 6000,
        "pitch_end_hz": 45,
        "sweep_speed": 0.40,
        "default_attack": 0.50,
        "default_body": 0.70,
        "default_body_shape": "sustained",
        "length_pct": 0.50,
        "default_click": 0.40,
        "default_click_decay": 0.15,
    },
    4: {
        "name": "Driving & Energetic",
        "desc": "Forward momentum. Fast sweep, punchy body, strong presence.",
        "pitch_start_hz": 12000,
        "pitch_end_hz": 55,
        "sweep_speed": 0.65,
        "default_attack": 0.80,
        "default_body": 0.60,
        "default_body_shape": "deep_drive",
        "length_pct": 0.46,
        "default_click": 0.70,
        "default_click_decay": 0.20,
    },
}


# ============================================================
# INPUT HELPERS
# ============================================================

def print_header(text):
    w = 54
    print(f"\n {'─' * w}")
    print(f"  {text}")
    print(f" {'─' * w}")


def ask_choice(question, options, default=None):
    """Numbered choice selector. options = {int: (label, description)}."""
    print(f"\n  {question}\n")
    for num, (label, desc) in options.items():
        arrow = " <-" if num == default else ""
        print(f"    [{num}] {label}{arrow}")
        if desc:
            print(f"        {desc}")

    while True:
        prompt = f"\n  [{default}] > " if default else "\n  > "
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            val = int(raw)
            if val in options:
                return val
        except ValueError:
            pass
        print(f"    Enter a number between {min(options)} and {max(options)}")


def ask_number(question, lo, hi, default=None):
    """Numeric input with range validation."""
    while True:
        hint = f"({lo}-{hi})"
        prompt = f"\n  {question} {hint} [{default}] > " if default is not None else f"\n  {question} {hint} > "
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            v = float(raw) if '.' in raw else int(raw)
            if lo <= v <= hi:
                return v
            print(f"    Must be between {lo} and {hi}")
        except ValueError:
            print("    Enter a valid number")


def ask_text(question, default=None):
    """Free text input."""
    prompt = f"\n  {question} [{default}] > " if default else f"\n  {question} > "
    raw = input(prompt).strip()
    return raw if raw else default


# ============================================================
# ENVELOPE GENERATORS
# ============================================================

def generate_pitch_envelope(start_hz, end_hz, sweep_speed, max_hz=20000):
    """
    Create pitch-envelope nodes from musical intent.

    Shape: fast drop → body tone → gradual settle to fundamental.
    The renderer uses freq = y * max_hz linearly, so end_hz must be the
    actual bass fundamental (~40-55 Hz) to sound like a kick.

    start_hz   : initial click/transient frequency  (6 000 – 12 000)
    end_hz     : fundamental bass frequency          (40 – 80)
    sweep_speed: 0.0 = slow gradual, 1.0 = fast snappy
    """
    y_s = start_hz / max_hz
    y_e = end_hz / max_hz

    # Body tone sits LOW — 60-120 Hz, not mid-range
    # This is what gives the kick weight without sounding like a laser
    body_hz = 60 + sweep_speed * 60                    # 60 … 120 Hz
    y_body = body_hz / max_hz

    # Drop through mid-range FAST — just a brief pass, not a plateau
    x_click_end = 0.01 + (1.0 - sweep_speed) * 0.01   # 0.01 … 0.02
    y_mid = (body_hz * 4) / max_hz                     # brief mid pass ~240-480 Hz

    # Arrive at body tone quickly
    x_body = 0.04 + (1.0 - sweep_speed) * 0.03        # 0.04 … 0.07

    # Settle to fundamental — tight, controlled
    x_settle = 0.20 + (1.0 - sweep_speed) * 0.10      # 0.20 … 0.30

    nodes = [
        {"x": 0.0,                  "y": round(y_s, 5),      "c": 0.0},
        {"x": round(x_click_end, 4),"y": round(y_mid, 5),    "c": -0.40},
        {"x": round(x_body, 4),     "y": round(y_body, 5),   "c": -0.20},
        {"x": round(x_settle, 4),   "y": round(y_e * 1.15, 5), "c": -0.05},
        {"x": 0.50,                 "y": round(y_e, 5),      "c": 0.0},
        {"x": 1.0,                  "y": round(y_e, 5),      "c": 0.0},
    ]
    return nodes


def generate_amp_envelope(attack, body_level, tail_speed, body_shape="sustained"):
    """
    Create amplitude-envelope nodes from musical intent.

    All body shapes use a dip-swell foundation — analysis of real progressive
    psy kicks shows the dip-swell envelope produces a perceived smooth sustained
    body in rendered audio. The double-bump creates the sustain feel.

    attack     : 0 = soft thud, 1 = hard snap
    body_level : 0 = thin, 1 = full sustain
    tail_speed : 0 = quick cut, 1 = long ring
    body_shape : "sustained" | "punchy" | "deep_drive" | "lean"
    """
    nodes = []

    # --- ATTACK (0 – ~3 %) ---
    att_t = 0.003 + (1.0 - attack) * 0.012       # 3 – 15 ms normalised
    peak  = 0.82 + attack * 0.18                  # 0.82 – 1.0
    nodes.append({"x": 0.0,                  "y": 0.05,                    "c": 0.0})
    nodes.append({"x": round(att_t * 0.4, 4), "y": round(peak * 0.6, 3),  "c": 0.0})
    nodes.append({"x": round(att_t, 4),       "y": round(peak, 3),         "c": 0.0})

    # --- POST-ATTACK DIP (with organic curvature) ---
    dip = peak * (0.12 + attack * 0.12)
    dip_x = att_t + 0.02 + (1.0 - attack) * 0.02
    c_dip = -0.55 - attack * 0.15                # -0.55 … -0.70
    nodes.append({"x": round(dip_x, 4), "y": round(peak - dip, 3), "c": round(c_dip, 2)})

    # --- BODY — dip-swell shapes (all based on dip-swell foundation) ---
    sus = 0.40 + body_level * 0.38                # 0.40 – 0.78

    # Dip/swell ratios per shape
    shape_params = {
        "sustained":  (0.55, 0.88),   # thick, present — dip to 55%, swell to 88%
        "punchy":     (0.40, 0.80),   # snappy, controlled
        "deep_drive": (0.35, 0.92),   # maximum movement
        "lean":       (0.65, 0.75),   # space for bass
    }
    dip_ratio, swell_ratio = shape_params.get(body_shape, (0.55, 0.88))

    c_swell = -0.35 - body_level * 0.15          # -0.35 … -0.50

    nodes += [
        {"x": 0.12, "y": round(peak * dip_ratio * 0.9, 3),  "c": round(c_swell, 2)},
        {"x": 0.20, "y": round(peak * dip_ratio, 3),        "c": round(c_swell, 2)},
        {"x": 0.32, "y": round(peak * swell_ratio * 0.85, 3), "c": round(c_swell * 0.7, 2)},
        {"x": 0.42, "y": round(peak * swell_ratio, 3),      "c": 0.0},
        {"x": 0.52, "y": round(peak * swell_ratio * 0.97, 3), "c": 0.02},
    ]

    # --- TAIL (with gentle convex fade) ---
    last_y = nodes[-1]["y"]
    ts = 0.55 + (1.0 - tail_speed) * 0.15        # start of fade
    fd = 0.20 + tail_speed * 0.25                 # fade duration
    mid  = ts + fd * 0.4
    end  = ts + fd
    zero = min(end + 0.03, 0.98)

    c_tail = 0.03 + tail_speed * 0.02             # 0.03 … 0.05

    nodes += [
        {"x": round(ts, 3),   "y": round(last_y * 0.80, 3), "c": round(c_tail, 2)},
        {"x": round(mid, 3),  "y": round(last_y * 0.35, 3), "c": round(c_tail, 2)},
        {"x": round(end, 3),  "y": round(last_y * 0.08, 3), "c": round(c_tail, 2)},
        {"x": round(zero, 3), "y": 0.0,                       "c": 0.0},
        {"x": 1.0,            "y": 0.0,                       "c": 0.0},
    ]
    return nodes


def generate_click_envelope(intensity, decay_pct):
    """Short amplitude envelope for the click/transient layer."""
    peak = 0.5 + intensity * 0.5
    return [
        {"x": 0.0,                       "y": round(peak, 3),       "c": 0.0},
        {"x": round(decay_pct * 0.4, 4), "y": round(peak * 0.5, 3), "c": 0.0},
        {"x": round(decay_pct, 4),        "y": 0.0,                  "c": 0.0},
        {"x": 1.0,                        "y": 0.0,                  "c": 0.0},
    ]


# ============================================================
# INTERACTIVE QUESTIONNAIRE
# ============================================================

def run_questionnaire():
    """Walk through all questions. Returns an answers dict."""
    answers = {}
    print(BANNER)

    # ── 1. VIBE ──────────────────────────────────────────────
    print_header("1. VIBE — What's the overall feeling?")
    opts = {n: (v["name"], v["desc"]) for n, v in VIBES.items()}
    answers["vibe"] = ask_choice("Pick the character closest to what you hear:", opts)
    vibe = VIBES[answers["vibe"]]

    # ── 2. BPM ───────────────────────────────────────────────
    print_header("2. TEMPO")
    answers["bpm"] = ask_number("BPM of your track?", 120, 200, default=138)

    beat_ms = 60000 / answers["bpm"]
    auto_len = round(beat_ms * vibe["length_pct"])

    # ── 3. LENGTH ────────────────────────────────────────────
    print_header("3. KICK LENGTH")
    print(f"\n    Auto: {auto_len}ms  ({vibe['length_pct']*100:.0f}% of {beat_ms:.0f}ms beat)")
    lc = ask_choice("Use auto length or set custom?", {
        1: (f"Auto ({auto_len}ms)", f"Good default for {answers['bpm']} BPM"),
        2: ("Custom", "Enter your own value"),
    }, default=1)
    answers["length_ms"] = auto_len if lc == 1 else ask_number("Length (ms)?", 80, 500, auto_len)

    # ── 4. PITCH DEPTH ───────────────────────────────────────
    print_header("4. PITCH DEPTH — How deep does the sweep go?")
    dc = ask_choice("Where should the pitch settle?", {
        1: ("Very deep",  "Low sub (~35 Hz) — heavy, underground"),
        2: ("Deep",       "Sub bass (~45 Hz) — round, full"),
        3: ("Medium",     "Bass (~55 Hz) — versatile, present"),
        4: ("Bright",     "Upper bass (~65 Hz) — bright, cutting"),
    }, default=2)
    depth_mul = {1: 0.80, 2: 1.00, 3: 1.25, 4: 1.50}
    answers["pitch_end_hz"]   = round(vibe["pitch_end_hz"] * depth_mul[dc])
    answers["pitch_start_hz"] = vibe["pitch_start_hz"]
    answers["sweep_speed"]    = vibe["sweep_speed"]

    # ── 5. ATTACK ────────────────────────────────────────────
    print_header("5. ATTACK — How does the kick hit?")
    ac = ask_choice("What kind of transient?", {
        1: ("Soft thud",       "Gentle, round, no sharp edge"),
        2: ("Defined click",   "Clear, present, well-defined"),
        3: ("Sharp snap",      "Cutting, percussive, immediate"),
        4: ("Aggressive slap", "Hard, intense, in-your-face"),
    }, default=2)
    answers["attack"] = {1: 0.25, 2: 0.55, 3: 0.78, 4: 0.95}[ac]

    # ── 6. BODY ──────────────────────────────────────────────
    print_header("6. BODY — How does the middle feel?")
    bc = ask_choice("What body shape?", {
        1: ("Sustained & full",  "Thick, present — dip-swell sustain"),
        2: ("Tight & punchy",    "Snappy, controlled — fast dip-swell"),
        3: ("Deep drive",        "Maximum movement — deep dip, high swell"),
        4: ("Lean & open",       "Space for bass — shallow dip-swell"),
    }, default=1)
    body_tbl = {1: (0.78, "sustained"), 2: (0.55, "punchy"),
                3: (0.65, "deep_drive"), 4: (0.38, "lean")}
    answers["body_level"], answers["body_shape"] = body_tbl[bc]

    # ── 7. TAIL ──────────────────────────────────────────────
    print_header("7. TAIL — How does the kick end?")
    tc = ask_choice("Decay style?", {
        1: ("Quick cut",  "Tight, clean — more room for bass"),
        2: ("Smooth fade", "Natural, balanced decay"),
        3: ("Long ring",  "Extended resonance — fills more space"),
    }, default=2)
    answers["tail"] = {1: 0.15, 2: 0.50, 3: 0.85}[tc]

    # ── 8. TEXTURE & TRANSIENT LAYERS ─────────────────────────
    print_header("8. TEXTURE & TRANSIENT LAYERS — Sample layers for character?")
    cc = ask_choice("Do you want sample layers for character?", {
        1: ("None",              "Pure sine only"),
        2: ("Subtle texture",    "2 low-gain samples (-12 dB, -23 dB) for warmth"),
        3: ("Defined transient", "1 sample at -6 dB for click definition"),
        4: ("Full stack",        "Transient + texture layers combined"),
    }, default=2)
    answers["texture_mode"] = {1: "none", 2: "subtle", 3: "transient", 4: "full"}[cc]

    # ── 9. TRACK KEY (optional) ──────────────────────────────
    print_header("9. TRACK KEY (optional)")
    print("\n    Tune the kick to your track.  The tuning parameter")
    print("    in Kick 2/3 shifts pitch by semitones — you can")
    print("    fine-tune by ear in the plugin.")
    print("    Enter a note (e.g. F, G#, Bb) or press Enter to skip.")
    key = ask_text("Track key?")
    if key:
        norm = key.strip().capitalize()
        if norm in NOTE_FREQ:
            answers["track_key"] = norm
        else:
            print(f"    '{key}' not recognised — skipping")
            answers["track_key"] = None
    else:
        answers["track_key"] = None

    return answers


# ============================================================
# CONFIG BUILDER
# ============================================================

def build_config(answers):
    """Turn questionnaire answers into a full preset JSON config."""
    length = answers["length_ms"]

    pitch_nodes = generate_pitch_envelope(
        answers["pitch_start_hz"],
        answers["pitch_end_hz"],
        answers["sweep_speed"],
    )
    amp_nodes = generate_amp_envelope(
        answers["attack"],
        answers["body_level"],
        answers["tail"],
        answers["body_shape"],
    )

    config = {
        "meta": {
            "source": "kick_questionnaire",
            "vibe": VIBES[answers["vibe"]]["name"],
            "bpm": answers["bpm"],
            "track_key": answers.get("track_key"),
            "generated": datetime.now().isoformat(),
        },
        "master": {
            "length_ms": length,
            "single_length_mode": True,
            "output_gain_db": 0.0,
            "output_gain_position": 1.0,
            "pan": 0.0,
            "tuning_semitones": 0.0,
            "pitch_wheel_range": 7.0,
            "processing_mode": 1.0,
            "gate": 0.0,
        },
        "limiter": {
            "enabled": True,
            "threshold_db": -0.1,
            "lookahead": 1.0,
            "release": 1.0,
        },
        "slots": [
            {
                "slot_number": 1,
                "type": "sine",
                "type_value": 1.0,
                "gain_db": 0.0,
                "muted": False,
                "active": True,
                "pitch_envelope": {
                    "max_freq_hz": 20000,
                    "semitone_offset": 0.0,
                    "range_max": 100.0,
                    "nodes": pitch_nodes,
                    "coarse_nodes": [],
                },
                "amp_envelope": {
                    "max_length_ms": length,
                    "nodes": amp_nodes,
                    "coarse_nodes": [],
                },
            },
        ],
        "fx_routing": {
            "insert1": {"osc1": True, "osc2": False, "osc3": False,
                        "osc4": False, "osc5": False,
                        "slot1_type": 0.0, "slot1_gain": 0.0,
                        "slot2_type": 0.0, "slot2_gain": 0.0},
            "insert2": {"osc1": False, "osc2": False, "osc3": False,
                        "osc4": False, "osc5": False,
                        "slot1_type": 0.0, "slot1_gain": 0.0,
                        "slot2_type": 0.0, "slot2_gain": 0.0},
            "master_fx": {"slot1_type": 0.0, "slot1_gain": 0.0,
                          "slot2_type": 0.0, "slot2_gain": 0.0},
        },
    }

    # Texture / transient layers
    texture_mode = answers.get("texture_mode", "none")

    def _sample_slot(slot_num, gain_db, decay_pct):
        """Create a sample texture slot with short amp envelope."""
        env_nodes = generate_click_envelope(0.7, decay_pct)
        return {
            "slot_number": slot_num,
            "type": "sample",
            "type_value": 2.0,
            "gain_db": gain_db,
            "muted": False,
            "active": True,
            "pitch_envelope": {
                "max_freq_hz": 20000,
                "semitone_offset": 0.0,
                "range_max": 100.0,
                "nodes": [{"x": 0.0, "y": 1.0, "c": 0.0},
                          {"x": 1.0, "y": 1.0, "c": 0.0}],
                "coarse_nodes": [],
            },
            "amp_envelope": {
                "max_length_ms": length,
                "nodes": env_nodes,
                "coarse_nodes": [],
            },
        }

    if texture_mode == "subtle":
        # 2 low-gain texture samples for warmth/character
        config["slots"].append(_sample_slot(2, -12.0, 0.20))
        config["slots"].append(_sample_slot(3, -23.0, 0.15))
        config["fx_routing"]["insert2"]["osc2"] = True
        config["fx_routing"]["insert2"]["osc3"] = True
    elif texture_mode == "transient":
        # 1 sample at -6 dB for click definition
        config["slots"].append(_sample_slot(2, -6.0, 0.18))
        config["fx_routing"]["insert2"]["osc2"] = True
    elif texture_mode == "full":
        # Transient + texture layers
        config["slots"].append(_sample_slot(2, -6.0, 0.18))
        config["slots"].append(_sample_slot(3, -12.0, 0.20))
        config["slots"].append(_sample_slot(4, -23.0, 0.15))
        config["fx_routing"]["insert2"]["osc2"] = True
        config["fx_routing"]["insert2"]["osc3"] = True
        config["fx_routing"]["insert2"]["osc4"] = True

    # Pad remaining slots to 5
    used = len(config["slots"])
    for i in range(used + 1, 6):
        config["slots"].append({
            "slot_number": i,
            "type": "off", "type_value": 0.0,
            "gain_db": 0.0, "muted": (i == 5), "active": False,
            "pitch_envelope": {"max_freq_hz": 20000, "nodes": [], "coarse_nodes": []},
            "amp_envelope": {"max_length_ms": length, "nodes": [], "coarse_nodes": []},
        })

    return config


# ============================================================
# SUMMARY + TWEAK
# ============================================================

def print_summary(answers, config):
    """Show a readable summary of the designed kick."""
    vibe = VIBES[answers["vibe"]]
    pn = config["slots"][0]["pitch_envelope"]["nodes"]
    start_hz = round(pn[0]["y"] * 20000)
    end_hz   = round(pn[-1]["y"] * 20000)

    shape_labels = {"sustained": "Sustained & full", "punchy": "Tight & punchy",
                     "deep_drive": "Deep drive", "lean": "Lean & open"}
    body_lbl = shape_labels.get(answers["body_shape"], answers["body_shape"])

    texture_labels = {"none": "None", "subtle": "Subtle texture (-12/-23 dB)",
                      "transient": "Defined transient (-6 dB)",
                      "full": "Full stack (transient + texture)"}
    texture_lbl = texture_labels.get(answers.get("texture_mode", "none"), "None")

    W = 40  # value column width

    def row(label, value):
        return f" |  {label:<10}: {str(value):<{W}} |"

    border = f" +{'─' * (W + 16)}+"
    title  = f" |{'KICK SUMMARY':^{W + 16}}|"

    lines = [
        "", border, title, border,
        row("Vibe",   vibe['name']),
        row("BPM",    answers['bpm']),
        row("Length", f"{answers['length_ms']} ms"),
        row("Pitch",  f"{start_hz} Hz -> {end_hz} Hz"),
        row("Attack", f"{round(answers['attack']*100)}%"),
        row("Body",   f"{body_lbl}, {round(answers['body_level']*100)}% full"),
        row("Tail",   f"{round(answers['tail']*100)}% fade"),
        row("Texture", texture_lbl),
        row("Key",    answers.get('track_key') or 'Not set'),
        border, "",
    ]
    print("\n".join(lines))


def tweak_loop(answers):
    """Optional loop to adjust individual parameters before generating."""
    while True:
        ch = ask_choice("What next?", {
            1: ("Generate!", "Create preset files with these settings"),
            2: ("Tweak",     "Adjust individual parameters"),
            3: ("Start over", "Restart the questionnaire"),
        }, default=1)

        if ch == 1:
            return answers
        if ch == 3:
            return None  # signal restart

        # Tweak sub-menu
        print_header("TWEAK — pick a parameter to adjust")
        tc = ask_choice("Which parameter?", {
            1: (f"Pitch start   : {answers['pitch_start_hz']} Hz", ""),
            2: (f"Pitch end     : {answers['pitch_end_hz']} Hz", ""),
            3: (f"Sweep speed   : {answers['sweep_speed']}", "0 = slow, 1 = fast"),
            4: (f"Attack        : {answers['attack']}", "0 = soft, 1 = sharp"),
            5: (f"Body level    : {answers['body_level']}", "0 = thin, 1 = full"),
            6: (f"Body shape    : {answers['body_shape']}", "sustained / punchy / deep_drive / lean"),
            7: (f"Tail          : {answers['tail']}", "0 = quick cut, 1 = long ring"),
            8: (f"Texture       : {answers.get('texture_mode', 'none')}", "none / subtle / transient / full"),
            9: (f"Length        : {answers['length_ms']} ms", ""),
        })

        tweak_map = {
            1: ("pitch_start_hz", 2000, 16000),
            2: ("pitch_end_hz",   100,  2500),
            3: ("sweep_speed",    0.0,  1.0),
            4: ("attack",         0.0,  1.0),
            5: ("body_level",     0.0,  1.0),
            7: ("tail",           0.0,  1.0),
            9: ("length_ms",      80,   500),
        }

        if tc == 6:
            sc = ask_choice("Body shape?", {
                1: ("sustained", "Thick, present"), 2: ("punchy", "Snappy, controlled"),
                3: ("deep_drive", "Maximum movement"), 4: ("lean", "Space for bass"),
            })
            answers["body_shape"] = {1: "sustained", 2: "punchy", 3: "deep_drive", 4: "lean"}[sc]
        elif tc == 8:
            sc = ask_choice("Texture mode?", {
                1: ("none", "Pure sine only"), 2: ("subtle", "2 texture layers"),
                3: ("transient", "1 click layer"), 4: ("full", "Transient + texture"),
            })
            answers["texture_mode"] = {1: "none", 2: "subtle", 3: "transient", 4: "full"}[sc]
        elif tc in tweak_map:
            key, lo, hi = tweak_map[tc]
            answers[key] = ask_number(f"New value for {key}?", lo, hi, answers[key])

        # Rebuild and show updated summary
        config = build_config(answers)
        print_summary(answers, config)


# ============================================================
# OUTPUT
# ============================================================

def generate_output(config, answers, name):
    """Generate all output files and return list of (label, path)."""
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RECIPE_DIR, exist_ok=True)

    results = []

    # JSON config
    p = os.path.join(OUT_DIR, f"{name}.json")
    with open(p, 'w') as f:
        json.dump(config, f, indent=2)
    results.append(("JSON config", p))

    # Kick 2 preset
    root = generate_preset(config)
    xml_str = prettify_xml(root)
    p = os.path.join(OUT_DIR, f"{name}.preset")
    with open(p, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml_str)
    results.append(("Kick 2 preset", p))

    # Kick 3 preset (if template available)
    if HAS_KICK3 and os.path.exists(TEMPLATE_PATH):
        tree = load_template(TEMPLATE_PATH)
        tree = apply_config(tree, config)
        p = os.path.join(OUT_DIR, f"{name}_k3.preset")
        write_k3(tree, p)
        results.append(("Kick 3 preset", p))

    # WAV preview
    samples = synthesize_kick(config, 44100)
    p = os.path.join(OUT_DIR, f"{name}.wav")
    write_wav(p, samples, 44100, 24)
    dur = len(samples) / 44100 * 1000
    results.append(("WAV preview", f"{p}  ({dur:.0f}ms, 44.1kHz, 24-bit)"))

    # Save recipe
    p = os.path.join(RECIPE_DIR, f"{name}.recipe.json")
    recipe = {**answers, "generated": datetime.now().isoformat()}
    with open(p, 'w') as f:
        json.dump(recipe, f, indent=2)
    results.append(("Recipe", p))

    return results


def list_recipes():
    """Print saved recipes."""
    if not os.path.isdir(RECIPE_DIR):
        print("  No recipes yet.")
        return
    files = sorted(f for f in os.listdir(RECIPE_DIR) if f.endswith('.recipe.json'))
    if not files:
        print("  No recipes yet.")
        return
    print(f"\n  Saved recipes ({RECIPE_DIR}):\n")
    for f in files:
        path = os.path.join(RECIPE_DIR, f)
        try:
            with open(path) as fh:
                r = json.load(fh)
            vibe = VIBES.get(r.get("vibe", 0), {}).get("name", "?")
            print(f"    {f:<40} {vibe}, {r.get('bpm','')} BPM, {r.get('length_ms','')}ms")
        except Exception:
            print(f"    {f}")
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Kick Questionnaire — interactive kick designer')
    parser.add_argument('--recipe', '-r',
                        help='Load a saved recipe and regenerate (skip questions)')
    parser.add_argument('--output', '-o',
                        help='Output name (no extension)')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List saved recipes')
    args = parser.parse_args()

    if args.list:
        list_recipes()
        return

    # ── get answers ──────────────────────────────────────────
    if args.recipe:
        with open(args.recipe) as f:
            answers = json.load(f)
        print(f"\n  Loaded recipe: {args.recipe}")
    else:
        while True:
            answers = run_questionnaire()
            config = build_config(answers)
            print_summary(answers, config)
            result = tweak_loop(answers)
            if result is not None:
                answers = result
                break
            # result is None → restart

    # ── build config ─────────────────────────────────────────
    config = build_config(answers)
    if args.recipe:
        print_summary(answers, config)

    # ── output name ──────────────────────────────────────────
    if args.output:
        name = args.output
    else:
        vibe = VIBES[answers["vibe"]]
        slug = vibe["name"].lower().replace(" & ", "_").replace(" ", "_")
        default_name = f"{slug}_{answers['bpm']}bpm"
        name = ask_text("Output name?", default=default_name) or default_name

    # ── generate ─────────────────────────────────────────────
    print("\n  Generating...\n")
    results = generate_output(config, answers, name)

    for label, path in results:
        print(f"    + {label}: {path}")

    print("\n  Done! Load the .preset file in Kick 2/3 and fine-tune to taste.")
    print("  Your answers are saved as a recipe — rerun with --recipe to regenerate.\n")


if __name__ == '__main__':
    main()
