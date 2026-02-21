#!/usr/bin/env python3
"""
Kick 2 Preset Parser
Parses Sonic Academy Kick 2 .preset XML files into structured JSON.
Extracts oscillator settings, envelopes, FX routing, master settings.
"""

import xml.etree.ElementTree as ET
import json
import sys
import os
import argparse
from collections import defaultdict


def parse_preset(filepath):
    """Parse a Kick 2 .preset file and return structured data."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    # Get plugin version - handle both Kick2PresetFile and Kick3 root elements
    root_tag = root.tag
    plugin_version = root.get('pluginVersion', root.get('version', 'unknown'))
    
    # Parse all PARAM elements - handle both <Params> and <PARAMS>
    params = {}
    params_elem = root.find('Params') or root.find('PARAMS')
    if params_elem is not None:
        for param in params_elem.findall('PARAM'):
            pid = param.get('id')
            val = param.get('value')
            try:
                params[pid] = float(val)
            except (ValueError, TypeError):
                params[pid] = val
    
    # Parse envelope data - try multiple locations
    envelopes = {}
    
    # Method 1: Dedicated EnvelopeData section (Kick 2 format)
    env_elem = root.find('EnvelopeData') or root.find('ENVELOPEDATA')
    if env_elem is not None:
        for envelope in env_elem.findall('Envelope') + env_elem.findall('ENVELOPE'):
            env_id = envelope.get('id')
            nodes = []
            for node in envelope.findall('Node') + envelope.findall('NODE'):
                nodes.append({
                    'x': float(node.get('x', 0)),
                    'y': float(node.get('y', 0)),
                    'c': float(node.get('c', 0))
                })
            envelopes[env_id] = nodes
    
    # Method 2: Envelopes inside <DATA> element (Kick 3 format)
    data_elem = root.find('DATA')
    if data_elem is not None:
        for child in data_elem:
            tag = child.tag
            if '_AmpEnvelope' in tag or '_PitchEnvelope' in tag:
                nodes = []
                for node in child.findall('node') + child.findall('Node'):
                    nodes.append({
                        'x': float(node.get('x', 0)),
                        'y': float(node.get('y', 0)),
                        'c': float(node.get('c', 0))
                    })
                envelopes[tag] = nodes
        
        # Also extract DATA element attributes (may contain sample paths etc.)
        for k, v in data_elem.attrib.items():
            if k not in params:
                params[f'_data_{k}'] = v
    
    # Method 3: Envelopes as direct children of root (another possible format)
    for child in root:
        tag = child.tag
        if '_AmpEnvelope' in tag or '_PitchEnvelope' in tag:
            if tag not in envelopes:
                nodes = []
                for node in child.findall('node') + child.findall('Node'):
                    nodes.append({
                        'x': float(node.get('x', 0)),
                        'y': float(node.get('y', 0)),
                        'c': float(node.get('c', 0))
                    })
                envelopes[tag] = nodes
    
    # Build structured output
    result = {
        'meta': {
            'plugin_version': plugin_version,
            'source_file': os.path.basename(filepath)
        },
        'master': extract_master(params),
        'limiter': extract_limiter(params),
        'slots': [],
        'fx_routing': extract_fx_routing(params),
        'envelopes_raw': envelopes
    }
    
    # Extract each oscillator slot (5 slots, indexed 1-5 in params)
    slot_type_map = {0.0: 'off', 1.0: 'sine', 2.0: 'sample'}
    
    for i in range(1, 6):
        slot = extract_slot(params, envelopes, i, slot_type_map)
        result['slots'].append(slot)
    
    # Add calculated pitch frequencies for sine slots
    for slot in result['slots']:
        if slot['type'] == 'sine' and slot['pitch_envelope']['nodes']:
            pitch_max = slot['pitch_envelope']['max_freq_hz']
            slot['pitch_envelope']['calculated_frequencies'] = [
                {
                    'time_normalized': n['x'],
                    'time_ms': n['x'] * slot['amp_envelope']['max_length_ms'],
                    'freq_hz': round(n['y'] * pitch_max, 1),
                    'y_raw': n['y']
                }
                for n in slot['pitch_envelope']['nodes']
            ]
    
    return result


def extract_master(params):
    """Extract master/global settings."""
    return {
        'length_ms': params.get('masterLength', 300),
        'single_length_mode': bool(params.get('singleLengthMode', 0)),
        'output_gain_db': params.get('outGain', 0),
        'output_gain_position': params.get('outGainPosition', 1),
        'pan': params.get('masterPan', 0),
        'tuning_semitones': params.get('tuning', 0),
        'pitch_wheel_range': params.get('pitchWheelRange', 7),
        'processing_mode': params.get('processingMode', 1),
        'gate': params.get('gate', 0)
    }


def extract_limiter(params):
    """Extract limiter settings."""
    return {
        'enabled': bool(params.get('Lim_Enable', 0)),
        'threshold_db': params.get('Lim_Threshold', 0),
        'lookahead': params.get('Lim_Lookahead', 1),
        'release': params.get('Lim_Release', 1)
    }


def extract_fx_routing(params):
    """Extract FX insert routing matrix."""
    routing = {
        'insert1': {},
        'insert2': {}
    }
    for osc in range(1, 6):
        routing['insert1'][f'osc{osc}'] = bool(params.get(f'FXInsert1Osc{osc}Routed', 0))
        routing['insert2'][f'osc{osc}'] = bool(params.get(f'FXInsert2Osc{osc}Routed', 0))
    
    # Extract FX slot parameters
    for insert_num in [1, 2]:
        for slot_num in [1, 2]:
            key = f'insert{insert_num}'
            fx_type = params.get(f'FXInsert{insert_num}Slot{slot_num}Type', 0)
            fx_gain = params.get(f'FXInsert{insert_num}Slot{slot_num}Gain', 0)
            routing[key][f'slot{slot_num}_type'] = fx_type
            routing[key][f'slot{slot_num}_gain'] = fx_gain
    
    # Master FX
    routing['master_fx'] = {}
    for slot_num in [1, 2]:
        routing['master_fx'][f'slot{slot_num}_type'] = params.get(f'MstrFXSlot{slot_num}Type', 0)
        routing['master_fx'][f'slot{slot_num}_gain'] = params.get(f'MstrFXSlot{slot_num}Gain', 0)
    
    return routing


def extract_slot(params, envelopes, slot_num, type_map):
    """Extract settings for a single oscillator slot."""
    slot_type_val = params.get(f'Slot{slot_num}Type', 0)
    slot_type = type_map.get(slot_type_val, 'unknown')
    
    is_muted = bool(params.get(f'Slot{slot_num}Mute', 0))
    gain = params.get(f'Slot{slot_num}Gain', 0)
    
    # Pitch envelope from PARAM nodes (coarse 8 nodes)
    pitch_coarse = []
    for n in range(1, 9):
        x = params.get(f'Slot{slot_num}PitchNode{n}_x', None)
        y = params.get(f'Slot{slot_num}PitchNode{n}_y', None)
        if x is not None and y is not None:
            pitch_coarse.append({'x': x, 'y': y})
    
    # Amp envelope from PARAM nodes (coarse 8 nodes)
    amp_coarse = []
    for n in range(1, 9):
        x = params.get(f'Slot{slot_num}AmpNode{n}_x', None)
        y = params.get(f'Slot{slot_num}AmpNode{n}_y', None)
        if x is not None and y is not None:
            amp_coarse.append({'x': x, 'y': y})
    
    # Detailed envelope from EnvelopeData (slot indices are 0-based there)
    env_slot_idx = slot_num - 1
    pitch_env_key = f'Slot{env_slot_idx}_PitchEnvelope'
    amp_env_key = f'Slot{env_slot_idx}_AmpEnvelope'
    
    pitch_nodes = envelopes.get(pitch_env_key, [])
    amp_nodes = envelopes.get(amp_env_key, [])
    
    pitch_env_max = params.get(f'Slot{slot_num}PitchEnvMax', 20000)
    pitch_semi = params.get(f'Slot{slot_num}PitchSemi', 0)
    amp_max_len = params.get(f'Slot{slot_num}AmpEnvMaxLen', 300)
    
    slot = {
        'slot_number': slot_num,
        'type': slot_type,
        'type_value': slot_type_val,
        'gain_db': gain,
        'muted': is_muted,
        'active': slot_type != 'off' and not is_muted,
        'pitch_envelope': {
            'max_freq_hz': pitch_env_max,
            'semitone_offset': pitch_semi,
            'range_max': params.get(f'Slot{slot_num}PitchEnvRangeMax', 100),
            'coarse_nodes': pitch_coarse,
            'nodes': pitch_nodes  # detailed from EnvelopeData
        },
        'amp_envelope': {
            'max_length_ms': amp_max_len,
            'coarse_nodes': amp_coarse,
            'nodes': amp_nodes  # detailed from EnvelopeData
        }
    }
    
    # Add sample info if applicable
    if slot_type == 'sample':
        # Look for sample path params
        sample_path = params.get(f'Slot{slot_num}SamplePath', '')
        slot['sample'] = {
            'path': sample_path
        }
    
    return slot


def print_summary(data):
    """Print a human-readable summary of the parsed preset."""
    print(f"\n{'='*60}")
    print(f"KICK 2 PRESET: {data['meta']['source_file']}")
    print(f"Plugin Version: {data['meta']['plugin_version']}")
    print(f"{'='*60}")
    
    m = data['master']
    print(f"\nMASTER: Length={m['length_ms']:.1f}ms | Gain={m['output_gain_db']}dB | Tuning={m['tuning_semitones']}st")
    
    lim = data['limiter']
    print(f"LIMITER: {'ON' if lim['enabled'] else 'OFF'} | Threshold={lim['threshold_db']}dB")
    
    print(f"\nOSCILLATOR SLOTS:")
    for slot in data['slots']:
        status = '✓' if slot['active'] else '✗'
        mute = ' [MUTED]' if slot['muted'] else ''
        print(f"  [{status}] Slot {slot['slot_number']}: {slot['type'].upper()}{mute} | Gain={slot['gain_db']:.2f}dB")
        
        if slot['active'] and slot['type'] == 'sine':
            pe = slot['pitch_envelope']
            if 'calculated_frequencies' in pe:
                freqs = pe['calculated_frequencies']
                print(f"      Pitch: {freqs[0]['freq_hz']:.0f}Hz → {freqs[-1]['freq_hz']:.0f}Hz ({len(freqs)} nodes)")
            
            ae = slot['amp_envelope']
            print(f"      Amp: {len(ae['nodes'])} nodes, {ae['max_length_ms']:.1f}ms")
        
        elif slot['active'] and slot['type'] == 'sample':
            ae = slot['amp_envelope']
            print(f"      Amp: {len(ae['nodes'])} nodes, {ae['max_length_ms']:.1f}ms")
    
    # FX routing
    fr = data['fx_routing']
    routed1 = [k for k, v in fr['insert1'].items() if v is True]
    routed2 = [k for k, v in fr['insert2'].items() if v is True]
    print(f"\nFX ROUTING:")
    print(f"  Insert 1 ← {', '.join(routed1) if routed1 else 'none'}")
    print(f"  Insert 2 ← {', '.join(routed2) if routed2 else 'none'}")


def main():
    parser = argparse.ArgumentParser(description='Parse Kick 2 preset files')
    parser.add_argument('input', help='Path to .preset file')
    parser.add_argument('--output', '-o', help='Output JSON path (default: stdout)')
    parser.add_argument('--summary', '-s', action='store_true', help='Print human-readable summary')
    parser.add_argument('--pretty', '-p', action='store_true', default=True, help='Pretty-print JSON')
    args = parser.parse_args()
    
    data = parse_preset(args.input)
    
    if args.summary:
        print_summary(data)
    
    json_str = json.dumps(data, indent=2 if args.pretty else None)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_str)
        print(f"\nSaved to: {args.output}")
    elif not args.summary:
        print(json_str)


if __name__ == '__main__':
    main()
