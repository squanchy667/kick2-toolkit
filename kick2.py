#!/usr/bin/env python3
"""
Kick 2 Toolkit - Unified CLI
Parse, generate, and render Kick 2 preset files.

Usage:
  kick2 parse  <input.preset> [-o output.json] [--summary]
  kick2 generate <input.json> [-o output.preset] [--simple]
  kick2 render <input.json> [-o output.wav] [-r 44100] [-b 24]
  kick2 roundtrip <input.preset> [-o output_dir]
  kick2 quick <pitch_start> <pitch_end> <length_ms> [-o output.preset]
"""

import sys
import os
import json
import argparse

# Add scripts directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'scripts'))

from kick2_parser import parse_preset, print_summary
from kick2_generator import generate_preset, create_from_simple, prettify_xml
from kick2_renderer import synthesize_kick, write_wav


def cmd_parse(args):
    """Parse a .preset file to JSON."""
    data = parse_preset(args.input)
    if args.summary:
        print_summary(data)
    
    json_str = json.dumps(data, indent=2)
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_str)
        print(f"Saved JSON: {args.output}")
    elif not args.summary:
        print(json_str)


def cmd_generate(args):
    """Generate a .preset from JSON config."""
    with open(args.input) as f:
        config = json.load(f)
    
    if args.simple:
        config = create_from_simple(config)
    
    root = generate_preset(config)
    xml_str = prettify_xml(root)
    
    output = args.output or 'output.preset'
    with open(output, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml_str)
    print(f"Generated: {output}")


def cmd_render(args):
    """Render parsed JSON to WAV."""
    with open(args.input) as f:
        config = json.load(f)
    
    samples = synthesize_kick(config, args.sample_rate)
    
    output = args.output or 'kick_render.wav'
    write_wav(output, samples, args.sample_rate, args.bit_depth)
    
    duration_ms = len(samples) / args.sample_rate * 1000
    print(f"Rendered: {output} ({duration_ms:.1f}ms, {args.sample_rate}Hz, {args.bit_depth}bit)")


def cmd_roundtrip(args):
    """Full roundtrip: parse → render → regenerate."""
    import os
    
    outdir = args.output or '.'
    os.makedirs(outdir, exist_ok=True)
    
    base = os.path.splitext(os.path.basename(args.input))[0]
    json_path = os.path.join(outdir, f'{base}_parsed.json')
    wav_path = os.path.join(outdir, f'{base}_render.wav')
    preset_path = os.path.join(outdir, f'{base}_regenerated.preset')
    
    # Parse
    print(f"1. Parsing: {args.input}")
    data = parse_preset(args.input)
    print_summary(data)
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"   → {json_path}")
    
    # Render
    print(f"\n2. Rendering to WAV...")
    samples = synthesize_kick(data, 44100)
    write_wav(wav_path, samples, 44100, 24)
    print(f"   → {wav_path}")
    
    # Regenerate
    print(f"\n3. Regenerating preset...")
    root = generate_preset(data)
    xml_str = prettify_xml(root)
    with open(preset_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml_str)
    print(f"   → {preset_path}")
    
    print(f"\nDone! All files in: {outdir}")


def cmd_quick(args):
    """Quick-generate a kick from basic parameters."""
    config = {
        'length_ms': args.length,
        'pitch_start_hz': args.pitch_start,
        'pitch_end_hz': args.pitch_end,
        'pitch_curve': args.curve,
        'amp_shape': args.shape,
        'click_layer': not args.no_click,
        'click_decay_pct': args.click_decay,
        'limiter': True
    }
    
    full_config = create_from_simple(config)
    root = generate_preset(full_config)
    xml_str = prettify_xml(root)
    
    output = args.output or 'quick_kick.preset'
    with open(output, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml_str)
    print(f"Generated: {output}")
    print(f"  Pitch: {args.pitch_start}Hz → {args.pitch_end}Hz")
    print(f"  Length: {args.length}ms | Shape: {args.shape} | Curve: {args.curve}")
    
    # Also render a preview
    wav_path = output.replace('.preset', '_preview.wav')
    samples = synthesize_kick(full_config, 44100)
    write_wav(wav_path, samples, 44100, 24)
    print(f"  Preview: {wav_path}")


def main():
    parser = argparse.ArgumentParser(description='Kick 2 Preset Toolkit')
    sub = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse
    p = sub.add_parser('parse', help='Parse .preset to JSON')
    p.add_argument('input', help='.preset file')
    p.add_argument('-o', '--output', help='Output JSON path')
    p.add_argument('-s', '--summary', action='store_true', help='Print summary')
    
    # Generate
    g = sub.add_parser('generate', help='Generate .preset from JSON')
    g.add_argument('input', help='JSON config file')
    g.add_argument('-o', '--output', help='Output .preset path')
    g.add_argument('-s', '--simple', action='store_true', help='Simple config mode')
    
    # Render
    r = sub.add_parser('render', help='Render JSON to WAV')
    r.add_argument('input', help='Parsed JSON file')
    r.add_argument('-o', '--output', help='Output WAV path')
    r.add_argument('-r', '--sample-rate', type=int, default=44100)
    r.add_argument('-b', '--bit-depth', type=int, default=24, choices=[16, 24, 32])
    
    # Roundtrip
    rt = sub.add_parser('roundtrip', help='Full parse → render → regenerate')
    rt.add_argument('input', help='.preset file')
    rt.add_argument('-o', '--output', help='Output directory')
    
    # Quick
    q = sub.add_parser('quick', help='Quick-generate from basic params')
    q.add_argument('pitch_start', type=float, help='Start pitch (Hz)')
    q.add_argument('pitch_end', type=float, help='End pitch (Hz)')
    q.add_argument('length', type=float, help='Length (ms)')
    q.add_argument('-o', '--output', help='Output .preset path')
    q.add_argument('--curve', default='exponential', choices=['exponential', 'linear'])
    q.add_argument('--shape', default='punchy', choices=['punchy', 'sustain', 'short'])
    q.add_argument('--no-click', action='store_true', help='Disable click layer')
    q.add_argument('--click-decay', type=int, default=50, help='Click decay %%')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        'parse': cmd_parse,
        'generate': cmd_generate,
        'render': cmd_render,
        'roundtrip': cmd_roundtrip,
        'quick': cmd_quick
    }
    
    commands[args.command](args)


if __name__ == '__main__':
    main()
