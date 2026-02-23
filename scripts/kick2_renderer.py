#!/usr/bin/env python3
"""
Kick 2 Audio Renderer
Synthesizes kick drum audio from parsed Kick 2 preset parameters.
Outputs WAV files using pure Python (no external audio deps required).
"""

import json
import math
import struct
import wave
import sys
import argparse
import os


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def interpolate_envelope(nodes, num_samples):
    """
    Interpolate envelope nodes to per-sample values.
    Nodes are [{x, y, c}, ...] where x is normalized time 0-1.
    c is curve tension: 0=linear, negative=concave, positive=convex.
    """
    if not nodes:
        return [0.0] * num_samples
    
    if len(nodes) == 1:
        return [nodes[0]['y']] * num_samples
    
    values = [0.0] * num_samples
    
    for i in range(num_samples):
        t = i / max(num_samples - 1, 1)
        
        # Find surrounding nodes
        left_idx = 0
        for j in range(len(nodes) - 1):
            if nodes[j]['x'] <= t:
                left_idx = j
            else:
                break
        
        right_idx = min(left_idx + 1, len(nodes) - 1)
        
        if left_idx == right_idx:
            values[i] = nodes[left_idx]['y']
            continue
        
        left = nodes[left_idx]
        right = nodes[right_idx]
        
        # Calculate local t between these two nodes
        segment_len = right['x'] - left['x']
        if segment_len <= 0:
            values[i] = left['y']
            continue
        
        local_t = (t - left['x']) / segment_len
        local_t = max(0.0, min(1.0, local_t))
        
        # Apply curve tension
        c = left.get('c', 0.0)
        if abs(c) > 0.001:
            # Attempt curved interpolation
            if c < 0:
                # Concave: faster start, slower end
                local_t = 1.0 - (1.0 - local_t) ** (1.0 + abs(c) * 5)
            else:
                # Convex: slower start, faster end
                local_t = local_t ** (1.0 + abs(c) * 5)
        
        values[i] = lerp(left['y'], right['y'], local_t)
    
    return values


def synthesize_kick(config, sample_rate=44100):
    """
    Synthesize kick drum audio from parsed preset config.
    Returns list of float samples normalized to [-1, 1].
    """
    # Determine duration
    master = config.get('master', {})
    duration_ms = master.get('length_ms', 300)
    duration_s = duration_ms / 1000.0
    num_samples = int(duration_s * sample_rate)
    
    # Mix buffer
    mix = [0.0] * num_samples
    
    slots = config.get('slots', [])
    
    for slot_idx, slot in enumerate(slots):
        if not slot.get('active', False) and slot.get('type', 'off') == 'off':
            continue
        if slot.get('muted', False):
            continue
        
        slot_type = slot.get('type', 'off')
        if slot_type == 'off':
            continue
        
        gain_db = slot.get('gain_db', 0.0)
        gain_linear = 10 ** (gain_db / 20.0) if gain_db != 0 else 1.0
        
        if slot_type == 'sine':
            audio = synthesize_sine_slot(slot, num_samples, sample_rate)
        elif slot_type == 'sample':
            audio = synthesize_noise_slot(slot, num_samples, sample_rate)
        else:
            continue
        
        # Apply gain and mix
        for i in range(num_samples):
            mix[i] += audio[i] * gain_linear
    
    # Apply limiter if enabled
    limiter = config.get('limiter', {})
    if limiter.get('enabled', False):
        threshold_db = limiter.get('threshold_db', 0.0)
        threshold = 10 ** (threshold_db / 20.0) if threshold_db < 0 else 1.0
        mix = apply_limiter(mix, threshold, sample_rate)
    
    # Normalize
    peak = max(abs(s) for s in mix) if mix else 1.0
    if peak > 0:
        mix = [s / peak * 0.89 for s in mix]
    
    return mix


def synthesize_sine_slot(slot, num_samples, sample_rate):
    """Synthesize sine wave with pitch and amplitude envelopes."""
    pe = slot.get('pitch_envelope', {})
    ae = slot.get('amp_envelope', {})
    
    pitch_max = pe.get('max_freq_hz', 20000)
    pitch_nodes = pe.get('nodes', [])
    amp_nodes = ae.get('nodes', [])
    
    # Interpolate envelopes
    pitch_env = interpolate_envelope(pitch_nodes, num_samples)
    amp_env = interpolate_envelope(amp_nodes, num_samples)
    
    # Convert pitch envelope to frequency
    freqs = [y * pitch_max for y in pitch_env]
    
    # Synthesize sine with phase accumulation
    audio = [0.0] * num_samples
    phase = 0.0
    
    for i in range(num_samples):
        audio[i] = math.sin(2.0 * math.pi * phase) * amp_env[i]
        phase += freqs[i] / sample_rate
        # Keep phase bounded to avoid precision loss
        if phase > 1000.0:
            phase -= 1000.0
    
    return audio


def synthesize_noise_slot(slot, num_samples, sample_rate):
    """
    Synthesize filtered noise for texture/click layers.
    Uses low-pass filtered noise for a smoother, less harsh character.
    """
    ae = slot.get('amp_envelope', {})
    amp_nodes = ae.get('nodes', [])

    amp_env = interpolate_envelope(amp_nodes, num_samples)

    import random
    rng = random.Random(42)

    # Generate raw noise then low-pass filter for smooth texture
    raw = [rng.uniform(-1, 1) for _ in range(num_samples)]

    # Simple one-pole low-pass at ~4kHz for warmth
    cutoff = 4000.0
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)

    audio = [0.0] * num_samples
    prev = 0.0
    for i in range(num_samples):
        prev = prev + alpha * (raw[i] - prev)
        audio[i] = prev * amp_env[i] * 0.3

    return audio


def apply_limiter(samples, threshold, sample_rate):
    """Soft-knee limiter with lookahead smoothing."""
    output = list(samples)
    knee = 0.1  # soft knee width in linear
    # Smoothing: ~1ms attack, ~10ms release
    attack_coeff = math.exp(-1.0 / (0.001 * sample_rate))
    release_coeff = math.exp(-1.0 / (0.010 * sample_rate))
    gain_reduction = 1.0

    for i in range(len(output)):
        level = abs(output[i])
        if level > threshold:
            # Soft-knee: gradual compression above threshold
            overshoot = level / threshold
            target_gain = 1.0 / overshoot
        elif level > threshold - knee:
            # Knee region: blend between unity and compression
            blend = (level - (threshold - knee)) / knee
            target_gain = 1.0 - blend * (1.0 - threshold / max(level, 0.0001))
        else:
            target_gain = 1.0

        # Smooth gain changes
        if target_gain < gain_reduction:
            gain_reduction = attack_coeff * gain_reduction + (1 - attack_coeff) * target_gain
        else:
            gain_reduction = release_coeff * gain_reduction + (1 - release_coeff) * target_gain

        output[i] *= gain_reduction
    return output


def write_wav(filepath, samples, sample_rate=44100, bit_depth=24):
    """Write samples to WAV file."""
    num_samples = len(samples)
    
    if bit_depth == 16:
        max_val = 32767
        fmt = '<h'
        sampwidth = 2
    elif bit_depth == 24:
        max_val = 8388607
        sampwidth = 3
    elif bit_depth == 32:
        max_val = 2147483647
        fmt = '<i'
        sampwidth = 4
    else:
        raise ValueError(f"Unsupported bit depth: {bit_depth}")
    
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        
        frames = bytearray()
        for s in samples:
            val = int(max(min(s, 1.0), -1.0) * max_val)
            if bit_depth == 24:
                # Pack as 3 bytes (little-endian)
                frames.extend(struct.pack('<i', val)[:3])
            else:
                frames.extend(struct.pack(fmt, val))
        
        wf.writeframes(bytes(frames))


def main():
    parser = argparse.ArgumentParser(description='Render Kick 2 preset to WAV audio')
    parser.add_argument('input', help='Parsed preset JSON file')
    parser.add_argument('--output', '-o', default='kick_render.wav', help='Output WAV path')
    parser.add_argument('--sample-rate', '-r', type=int, default=44100, help='Sample rate')
    parser.add_argument('--bit-depth', '-b', type=int, default=24, choices=[16, 24, 32], help='Bit depth')
    args = parser.parse_args()
    
    with open(args.input) as f:
        config = json.load(f)
    
    print(f"Rendering kick: {args.input}")
    print(f"  Sample rate: {args.sample_rate} Hz")
    print(f"  Bit depth: {args.bit_depth}")
    
    samples = synthesize_kick(config, args.sample_rate)
    
    duration_ms = len(samples) / args.sample_rate * 1000
    peak_db = 20 * math.log10(max(abs(s) for s in samples) + 1e-10)
    
    print(f"  Duration: {duration_ms:.1f} ms ({len(samples)} samples)")
    print(f"  Peak: {peak_db:.1f} dB")
    
    write_wav(args.output, samples, args.sample_rate, args.bit_depth)
    print(f"  Saved: {args.output}")


if __name__ == '__main__':
    main()
