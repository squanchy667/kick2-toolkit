#!/usr/bin/env python3
"""
Kick 2 Preset Generator
Creates Sonic Academy Kick 2 .preset XML files from structured JSON parameters.
Can generate from parsed JSON or from simplified parameter definitions.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import sys
import os
import argparse


# Default template values for a basic sine kick
DEFAULTS = {
    'master': {
        'length_ms': 300.0,
        'single_length_mode': True,
        'output_gain_db': 0.0,
        'output_gain_position': 1.0,
        'pan': 0.0,
        'tuning_semitones': 0.0,
        'pitch_wheel_range': 7.0,
        'processing_mode': 1.0,
        'gate': 0.0
    },
    'limiter': {
        'enabled': True,
        'threshold_db': 0.0,
        'lookahead': 1.0,
        'release': 1.0
    }
}

# Default pitch envelope: classic psy kick sweep
DEFAULT_PITCH_NODES = [
    {'x': 0.0, 'y': 0.79, 'c': 0.0},
    {'x': 0.037, 'y': 0.52, 'c': -0.1},
    {'x': 0.156, 'y': 0.36, 'c': 0.0},
    {'x': 0.49, 'y': 0.21, 'c': 0.0},
    {'x': 0.827, 'y': 0.094, 'c': -0.04},
    {'x': 1.0, 'y': 0.09, 'c': 0.0}
]

# Default amp envelope: punchy kick shape
DEFAULT_AMP_NODES = [
    {'x': 0.0, 'y': 0.23, 'c': 0.0},
    {'x': 0.005, 'y': 0.62, 'c': 0.0},
    {'x': 0.012, 'y': 0.83, 'c': 0.0},
    {'x': 0.02, 'y': 0.70, 'c': 0.0},
    {'x': 0.18, 'y': 0.37, 'c': 0.0},
    {'x': 0.31, 'y': 0.70, 'c': 0.0},
    {'x': 0.45, 'y': 0.73, 'c': 0.0},
    {'x': 0.80, 'y': 0.71, 'c': 0.0},
    {'x': 0.88, 'y': 0.42, 'c': 0.0},
    {'x': 0.90, 'y': 0.01, 'c': 0.0},
    {'x': 0.91, 'y': 0.0, 'c': 0.0},
    {'x': 1.0, 'y': 0.0, 'c': 0.0}
]


def generate_preset(config, plugin_version="1.5.3"):
    """Generate a Kick 2 preset XML from config dict."""
    
    root = ET.Element('Kick2PresetFile')
    root.set('pluginVersion', plugin_version)
    
    params_elem = ET.SubElement(root, 'Params')
    env_elem = ET.SubElement(root, 'EnvelopeData')
    
    # Master settings
    master = {**DEFAULTS['master'], **config.get('master', {})}
    add_param(params_elem, 'masterLength', master['length_ms'])
    add_param(params_elem, 'singleLengthMode', 1.0 if master['single_length_mode'] else 0.0)
    add_param(params_elem, 'outGain', master['output_gain_db'])
    add_param(params_elem, 'outGainPosition', master['output_gain_position'])
    add_param(params_elem, 'masterPan', master['pan'])
    add_param(params_elem, 'tuning', master['tuning_semitones'])
    add_param(params_elem, 'pitchWheelRange', master['pitch_wheel_range'])
    add_param(params_elem, 'processingMode', master['processing_mode'])
    add_param(params_elem, 'gate', master['gate'])
    
    # Limiter
    limiter = {**DEFAULTS['limiter'], **config.get('limiter', {})}
    add_param(params_elem, 'Lim_Enable', 1.0 if limiter['enabled'] else 0.0)
    add_param(params_elem, 'Lim_Threshold', limiter['threshold_db'])
    add_param(params_elem, 'Lim_Lookahead', limiter['lookahead'])
    add_param(params_elem, 'Lim_Release', limiter['release'])
    
    # Process slots
    slots = config.get('slots', [])
    
    # Ensure we have 5 slots (pad with inactive)
    while len(slots) < 5:
        slots.append({'type': 'off'})
    
    for i, slot_config in enumerate(slots[:5]):
        slot_num = i + 1
        generate_slot(params_elem, env_elem, slot_num, slot_config, master)
    
    # FX routing
    fx = config.get('fx_routing', {})
    for insert_num in [1, 2]:
        insert_key = f'insert{insert_num}'
        insert_config = fx.get(insert_key, {})
        for osc in range(1, 6):
            routed = insert_config.get(f'osc{osc}', False)
            add_param(params_elem, f'FXInsert{insert_num}Osc{osc}Routed', 1.0 if routed else 0.0)
        
        # FX slot types and gains
        for slot_num in [1, 2]:
            add_param(params_elem, f'FXInsert{insert_num}Slot{slot_num}Type',
                      insert_config.get(f'slot{slot_num}_type', 0.0))
            add_param(params_elem, f'FXInsert{insert_num}Slot{slot_num}Gain',
                      insert_config.get(f'slot{slot_num}_gain', 0.0))
    
    # Master FX
    master_fx = fx.get('master_fx', {})
    for slot_num in [1, 2]:
        add_param(params_elem, f'MstrFXSlot{slot_num}Type',
                  master_fx.get(f'slot{slot_num}_type', 0.0))
        add_param(params_elem, f'MstrFXSlot{slot_num}Gain',
                  master_fx.get(f'slot{slot_num}_gain', 0.0))
    
    return root


def generate_slot(params_elem, env_elem, slot_num, slot_config, master):
    """Generate params and envelopes for a single oscillator slot."""
    
    type_map = {'off': 0.0, 'sine': 1.0, 'sample': 2.0}
    slot_type = slot_config.get('type', 'off')
    
    add_param(params_elem, f'Slot{slot_num}Type', type_map.get(slot_type, 0.0))
    add_param(params_elem, f'Slot{slot_num}Gain', slot_config.get('gain_db', 0.0))
    
    if slot_config.get('muted', False):
        add_param(params_elem, f'Slot{slot_num}Mute', 1.0)
    
    # Pitch envelope
    pe = slot_config.get('pitch_envelope', {})
    pitch_max = pe.get('max_freq_hz', 20000.0)
    pitch_semi = pe.get('semitone_offset', 0.0)
    pitch_nodes = pe.get('nodes', [])
    
    # Use defaults for active sine slots with no nodes
    if slot_type == 'sine' and not pitch_nodes:
        pitch_nodes = DEFAULT_PITCH_NODES
    
    add_param(params_elem, f'Slot{slot_num}PitchEnvMax', pitch_max)
    add_param(params_elem, f'Slot{slot_num}PitchEnvRangeMax', pe.get('range_max', 100.0))
    add_param(params_elem, f'Slot{slot_num}PitchSemi', pitch_semi)
    
    # Write coarse pitch nodes (8 max in params)
    write_coarse_nodes(params_elem, f'Slot{slot_num}PitchNode', pitch_nodes, 8,
                       default_y=1.0 if slot_type == 'sample' else 0.09)
    
    # Write detailed pitch envelope
    env_slot_idx = slot_num - 1
    write_envelope(env_elem, f'Slot{env_slot_idx}_PitchEnvelope', pitch_nodes)
    
    # Amp envelope
    ae = slot_config.get('amp_envelope', {})
    amp_max_len = ae.get('max_length_ms', master.get('length_ms', 300.0))
    amp_nodes = ae.get('nodes', [])
    
    # Use defaults for active sine slots with no nodes
    if slot_type == 'sine' and not amp_nodes:
        amp_nodes = DEFAULT_AMP_NODES
    elif slot_type == 'sample' and not amp_nodes:
        amp_nodes = [
            {'x': 0.0, 'y': 1.0, 'c': 0.0},
            {'x': 0.5, 'y': 0.0, 'c': 0.0},
            {'x': 1.0, 'y': 0.0, 'c': 0.0}
        ]
    
    add_param(params_elem, f'Slot{slot_num}AmpEnvMaxLen', amp_max_len)
    
    # Write coarse amp nodes
    write_coarse_nodes(params_elem, f'Slot{slot_num}AmpNode', amp_nodes, 8,
                       default_y=0.0)
    
    # Write detailed amp envelope
    write_envelope(env_elem, f'Slot{env_slot_idx}_AmpEnvelope', amp_nodes)


def write_coarse_nodes(params_elem, prefix, nodes, max_nodes, default_y=0.0):
    """Write coarse envelope nodes to PARAM elements (max 8)."""
    for i in range(max_nodes):
        if i < len(nodes):
            add_param(params_elem, f'{prefix}{i+1}_x', nodes[i]['x'])
            add_param(params_elem, f'{prefix}{i+1}_y', nodes[i]['y'])
        else:
            add_param(params_elem, f'{prefix}{i+1}_x', 1.0)
            add_param(params_elem, f'{prefix}{i+1}_y', default_y)


def write_envelope(env_elem, env_id, nodes):
    """Write detailed envelope to EnvelopeData section."""
    envelope = ET.SubElement(env_elem, 'Envelope')
    envelope.set('id', env_id)
    
    for node in nodes:
        node_elem = ET.SubElement(envelope, 'Node')
        node_elem.set('x', f"{node['x']:.16f}" if isinstance(node['x'], float) else str(node['x']))
        node_elem.set('y', f"{node['y']:.16f}" if isinstance(node['y'], float) else str(node['y']))
        node_elem.set('c', f"{node.get('c', 0.0):.16f}")


def add_param(params_elem, pid, value):
    """Add a PARAM element."""
    param = ET.SubElement(params_elem, 'PARAM')
    param.set('id', pid)
    if isinstance(value, float):
        param.set('value', f"{value}")
    else:
        param.set('value', str(value))


def prettify_xml(elem):
    """Return prettified XML string."""
    rough = ET.tostring(elem, encoding='unicode', xml_declaration=False)
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent='  ', encoding=None)
    # Remove extra declaration minidom adds
    lines = pretty.split('\n')
    if lines[0].startswith('<?xml'):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    return '\n'.join(lines)


def create_from_simple(simple_config):
    """
    Create a preset from simplified parameters.
    
    Simple config format:
    {
        "length_ms": 300,
        "pitch_start_hz": 15000,
        "pitch_end_hz": 1800,
        "pitch_curve": "exponential",  # or "linear" or custom nodes
        "amp_shape": "punchy",  # or "sustain", "short", or custom nodes
        "click_layer": true,
        "click_decay_pct": 50,
        "gain_db": 0,
        "limiter": true
    }
    """
    length = simple_config.get('length_ms', 300)
    pitch_start = simple_config.get('pitch_start_hz', 15000)
    pitch_end = simple_config.get('pitch_end_hz', 1800)
    pitch_max = max(pitch_start, 20000)
    
    # Generate pitch nodes
    y_start = pitch_start / pitch_max
    y_end = pitch_end / pitch_max
    
    pitch_curve = simple_config.get('pitch_curve', 'exponential')
    if pitch_curve == 'exponential':
        # Classic psy trance exponential decay
        pitch_nodes = generate_exp_pitch_nodes(y_start, y_end)
    elif pitch_curve == 'linear':
        pitch_nodes = [
            {'x': 0.0, 'y': y_start, 'c': 0.0},
            {'x': 1.0, 'y': y_end, 'c': 0.0}
        ]
    elif isinstance(pitch_curve, list):
        pitch_nodes = pitch_curve
    else:
        pitch_nodes = generate_exp_pitch_nodes(y_start, y_end)
    
    # Generate amp envelope
    amp_shape = simple_config.get('amp_shape', 'punchy')
    if amp_shape == 'punchy':
        amp_nodes = DEFAULT_AMP_NODES
    elif amp_shape == 'sustain':
        amp_nodes = [
            {'x': 0.0, 'y': 0.0, 'c': 0.0},
            {'x': 0.003, 'y': 1.0, 'c': 0.0},
            {'x': 0.85, 'y': 0.95, 'c': 0.0},
            {'x': 0.95, 'y': 0.0, 'c': 0.0},
            {'x': 1.0, 'y': 0.0, 'c': 0.0}
        ]
    elif amp_shape == 'short':
        amp_nodes = [
            {'x': 0.0, 'y': 0.0, 'c': 0.0},
            {'x': 0.003, 'y': 1.0, 'c': 0.0},
            {'x': 0.5, 'y': 0.3, 'c': 0.0},
            {'x': 0.7, 'y': 0.0, 'c': 0.0},
            {'x': 1.0, 'y': 0.0, 'c': 0.0}
        ]
    elif isinstance(amp_shape, list):
        amp_nodes = amp_shape
    else:
        amp_nodes = DEFAULT_AMP_NODES
    
    # Build full config
    config = {
        'master': {
            'length_ms': length,
            'single_length_mode': True,
            'output_gain_db': simple_config.get('gain_db', 0),
            'tuning_semitones': simple_config.get('tuning', 0)
        },
        'limiter': {
            'enabled': simple_config.get('limiter', True)
        },
        'slots': [
            {
                'type': 'sine',
                'gain_db': 1.38,
                'pitch_envelope': {
                    'max_freq_hz': pitch_max,
                    'nodes': pitch_nodes
                },
                'amp_envelope': {
                    'max_length_ms': length,
                    'nodes': amp_nodes
                }
            }
        ],
        'fx_routing': {
            'insert1': {'osc1': True},
            'insert2': {}
        }
    }
    
    # Add click layer
    if simple_config.get('click_layer', True):
        click_decay = simple_config.get('click_decay_pct', 50) / 100.0
        config['slots'].append({
            'type': 'sample',
            'gain_db': 1.38,
            'pitch_envelope': {
                'max_freq_hz': 20000,
                'nodes': [
                    {'x': 0.0, 'y': 1.0, 'c': 0.0},
                    {'x': 1.0, 'y': 1.0, 'c': 0.0}
                ]
            },
            'amp_envelope': {
                'max_length_ms': length,
                'nodes': [
                    {'x': 0.0, 'y': 1.0, 'c': 0.0},
                    {'x': click_decay, 'y': 0.0, 'c': 0.0},
                    {'x': 1.0, 'y': 0.0, 'c': 0.0}
                ]
            }
        })
        config['fx_routing']['insert2'] = {'osc2': True}
    
    return config


def generate_exp_pitch_nodes(y_start, y_end, num_points=6):
    """Generate exponential pitch decay nodes."""
    import math
    nodes = []
    for i in range(num_points):
        t = i / (num_points - 1)
        # Exponential decay curve
        exp_t = 1.0 - math.exp(-4.0 * t)
        y = y_start + (y_end - y_start) * exp_t
        c = -0.1 if i == 1 else (-0.04 if i == num_points - 2 else 0.0)
        nodes.append({'x': round(t, 4), 'y': round(y, 4), 'c': c})
    return nodes


def main():
    parser = argparse.ArgumentParser(description='Generate Kick 2 preset files')
    parser.add_argument('input', help='JSON config file (full or simple format)')
    parser.add_argument('--output', '-o', default='output.preset', help='Output .preset path')
    parser.add_argument('--simple', '-s', action='store_true', help='Input is simple config format')
    parser.add_argument('--version', '-v', default='1.5.3', help='Plugin version string')
    args = parser.parse_args()
    
    with open(args.input) as f:
        config = json.load(f)
    
    if args.simple:
        config = create_from_simple(config)
    
    root = generate_preset(config, args.version)
    xml_str = prettify_xml(root)
    
    with open(args.output, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml_str)
    
    print(f"Generated preset: {args.output}")


if __name__ == '__main__':
    main()
