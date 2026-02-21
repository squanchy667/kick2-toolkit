#!/usr/bin/env python3
"""
Kick 3 Preset Generator
Uses an existing Kick 3 .preset as a template, then injects custom
pitch/amp envelopes and key parameters to create a new preset.
This ensures all 1006 params, FX defaults, DATA structure etc. are valid.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import sys
import os
import copy
import argparse


def load_template(template_path):
    """Load and parse a Kick 3 preset template."""
    tree = ET.parse(template_path)
    return tree


def set_param(params_elem, param_id, value):
    """Set a PARAM value, creating it if it doesn't exist."""
    for p in params_elem.findall('PARAM'):
        if p.get('id') == param_id:
            p.set('value', str(value))
            return
    # Create new param if not found
    new_p = ET.SubElement(params_elem, 'PARAM')
    new_p.set('id', param_id)
    new_p.set('value', str(value))


def replace_envelope(data_elem, env_name, nodes):
    """Replace an envelope's nodes in the DATA element."""
    env = data_elem.find(env_name)
    if env is None:
        env = ET.SubElement(data_elem, env_name)
    else:
        # Clear existing nodes
        for node in list(env):
            env.remove(node)
    
    # Add new nodes
    for n in nodes:
        node_elem = ET.SubElement(env, 'node')
        node_elem.set('x', str(n['x']))
        node_elem.set('y', str(n['y']))
        node_elem.set('c', str(n.get('c', 0.0)))
        node_elem.set('isKeytracked', '0')
        node_elem.set('isPhaseLocked', '0')
        node_elem.set('lockedPhaseValue', '0.0')


def clear_sample_data(data_elem):
    """Clear sample/sub file references so the preset doesn't look for missing files."""
    for key in list(data_elem.attrib.keys()):
        if 'File' in key and 'Dirty' not in key:
            data_elem.set(key, '////////')
        if 'FileDirty' in key:
            data_elem.set(key, '0')
    # Mark sub files as dirty so Kick 3 regenerates them
    for key in list(data_elem.attrib.keys()):
        if 'SubFullFileDirty' in key or 'SubFileDirty' in key:
            data_elem.set(key, '1')
        if 'AmpCurveFileDirty' in key or 'PitchCurveFileDirty' in key:
            data_elem.set(key, '1')


def apply_config(tree, config):
    """Apply a kick config (parsed JSON format) to a Kick 3 template tree."""
    root = tree.getroot()
    params = root.find('PARAMS')
    data = root.find('DATA')
    
    if params is None or data is None:
        raise ValueError("Template doesn't have expected Kick 3 structure (PARAMS + DATA)")
    
    # Clear sample references
    clear_sample_data(data)
    
    # === MASTER ===
    master = config.get('master', {})
    if 'length_ms' in master:
        set_param(params, 'masterLength', master['length_ms'])
    if 'output_gain_db' in master:
        set_param(params, 'outGain', master['output_gain_db'])
    if 'pan' in master:
        set_param(params, 'masterPan', master['pan'])
    if 'tuning_semitones' in master:
        set_param(params, 'tuning', master['tuning_semitones'])
    if 'single_length_mode' in master:
        set_param(params, 'singleLengthMode', 1.0 if master['single_length_mode'] else 0.0)
    if 'processing_mode' in master:
        set_param(params, 'processingMode', master['processing_mode'])
    if 'gate' in master:
        set_param(params, 'gate', master['gate'])
    
    # === LIMITER ===
    limiter = config.get('limiter', {})
    if 'enabled' in limiter:
        set_param(params, 'Lim_Enable', 1.0 if limiter['enabled'] else 0.0)
    if 'threshold_db' in limiter:
        set_param(params, 'Lim_Threshold', limiter['threshold_db'])
    if 'lookahead' in limiter:
        set_param(params, 'Lim_Lookahead', limiter['lookahead'])
    if 'release' in limiter:
        set_param(params, 'Lim_Release', limiter['release'])
    
    # === SLOTS ===
    type_map = {'off': 0.0, 'sine': 1.0, 'sample': 2.0}
    
    for slot_config in config.get('slots', []):
        slot_num = slot_config.get('slot_number', 1)
        env_idx = slot_num - 1  # Envelopes use 0-based index
        
        # Type, gain, mute
        if 'type' in slot_config:
            set_param(params, f'Slot{slot_num}Type', type_map.get(slot_config['type'], 0.0))
        if 'gain_db' in slot_config:
            set_param(params, f'Slot{slot_num}Gain', slot_config['gain_db'])
        if 'muted' in slot_config:
            set_param(params, f'Slot{slot_num}Mute', 1.0 if slot_config['muted'] else 0.0)
        
        # Pitch envelope
        pe = slot_config.get('pitch_envelope', {})
        if 'max_freq_hz' in pe:
            set_param(params, f'Slot{slot_num}PitchEnvMax', pe['max_freq_hz'])
        if 'semitone_offset' in pe:
            set_param(params, f'Slot{slot_num}PitchSemi', pe['semitone_offset'])
        if 'range_max' in pe:
            set_param(params, f'Slot{slot_num}PitchEnvRangeMax', pe['range_max'])
        
        pitch_nodes = pe.get('nodes', [])
        if pitch_nodes:
            # Update coarse nodes (8 max)
            for i in range(8):
                if i < len(pitch_nodes):
                    set_param(params, f'Slot{slot_num}PitchNode{i+1}_x', pitch_nodes[i]['x'])
                    set_param(params, f'Slot{slot_num}PitchNode{i+1}_y', pitch_nodes[i]['y'])
                else:
                    set_param(params, f'Slot{slot_num}PitchNode{i+1}_x', 1.0)
                    set_param(params, f'Slot{slot_num}PitchNode{i+1}_y', pitch_nodes[-1]['y'] if pitch_nodes else 0.09)
            
            # Update detailed envelope in DATA
            replace_envelope(data, f'Slot{env_idx}_PitchEnvelope', pitch_nodes)
        
        # Amp envelope
        ae = slot_config.get('amp_envelope', {})
        if 'max_length_ms' in ae:
            set_param(params, f'Slot{slot_num}AmpEnvMaxLen', ae['max_length_ms'])
        
        amp_nodes = ae.get('nodes', [])
        if amp_nodes:
            # Update coarse nodes
            for i in range(8):
                if i < len(amp_nodes):
                    set_param(params, f'Slot{slot_num}AmpNode{i+1}_x', amp_nodes[i]['x'])
                    set_param(params, f'Slot{slot_num}AmpNode{i+1}_y', amp_nodes[i]['y'])
                else:
                    set_param(params, f'Slot{slot_num}AmpNode{i+1}_x', 1.0)
                    set_param(params, f'Slot{slot_num}AmpNode{i+1}_y', 0.0)
            
            # Update detailed envelope in DATA
            replace_envelope(data, f'Slot{env_idx}_AmpEnvelope', amp_nodes)
    
    # === FX ROUTING ===
    fx = config.get('fx_routing', {})
    for insert_num in [1, 2]:
        insert_key = f'insert{insert_num}'
        if insert_key in fx:
            for osc in range(1, 6):
                if f'osc{osc}' in fx[insert_key]:
                    set_param(params, f'FXInsert{insert_num}Osc{osc}Routed',
                              1.0 if fx[insert_key][f'osc{osc}'] else 0.0)
    
    return tree


def write_preset(tree, output_path):
    """Write the modified tree as a Kick 3 .preset file."""
    root = tree.getroot()
    
    # Use ElementTree's built-in write with xml_declaration
    # But we need to ensure CRLF line endings
    rough = ET.tostring(root, encoding='unicode', xml_declaration=False)
    
    # Reformat with minidom for readability
    try:
        parsed = minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>\n{rough}')
        pretty = parsed.toprettyxml(indent='  ')
        # Remove the extra declaration minidom adds
        lines = pretty.split('\n')
        if lines[0].startswith('<?xml'):
            lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
        output = '\n'.join(lines)
    except Exception:
        output = f'<?xml version="1.0" encoding="UTF-8"?>\n{rough}'
    
    with open(output_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(output)


def main():
    parser = argparse.ArgumentParser(description='Generate Kick 3 compatible preset files')
    parser.add_argument('config', help='JSON config with kick parameters')
    parser.add_argument('--template', '-t', required=True, help='Template .preset file (Kick 3 format)')
    parser.add_argument('--output', '-o', default='new_kick.preset', help='Output .preset path')
    args = parser.parse_args()
    
    # Load template
    print(f"Template: {args.template}")
    tree = load_template(args.template)
    
    # Load config
    with open(args.config) as f:
        config = json.load(f)
    print(f"Config: {args.config}")
    
    # Apply
    tree = apply_config(tree, config)
    
    # Write
    write_preset(tree, args.output)
    print(f"Generated: {args.output}")
    
    # Verify
    verify_tree = ET.parse(args.output)
    verify_root = verify_tree.getroot()
    print(f"  Root tag: <{verify_root.tag}> ✓")
    verify_params = verify_root.find('PARAMS')
    print(f"  PARAMS: {len(list(verify_params))} params ✓")
    verify_data = verify_root.find('DATA')
    if verify_data is not None:
        print(f"  DATA: {len(list(verify_data))} children ✓")


if __name__ == '__main__':
    main()
