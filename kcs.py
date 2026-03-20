"""
Kansas City Standard (KCS) encoder and decoder.

Encodes text as audio tones in a .wav file at 300 baud:
  - Logic 0: 4 cycles of 1200 Hz
  - Logic 1: 8 cycles of 2400 Hz
  - Each byte: 1 start bit (0) + 8 data bits (LSB first) + 2 stop bits (1)

Only uses Python stdlib (wave, struct, math).
"""

import math
import struct
import wave

# ── KCS Parameters ──────────────────────────────────────────────────────────

BAUD_RATE = 300              # bits per second
FREQ_ZERO = 1200             # Hz – 4 cycles per bit period
FREQ_ONE = 2400              # Hz – 8 cycles per bit period
SAMPLE_RATE = 48000          # samples per second
AMPLITUDE = 0.8              # sine amplitude (0.0 – 1.0)
BIT_DURATION = 1.0 / BAUD_RATE  # seconds per bit

# Leader tone: a burst of '1' bits before data so the decoder can sync
LEADER_SECONDS = 1.0         # seconds of leader tone


# ── Encoder ─────────────────────────────────────────────────────────────────

class _ToneGenerator:
    """Phase-continuous tone generator with warm harmonics."""

    def __init__(self, sample_rate=SAMPLE_RATE, amplitude=AMPLITUDE):
        self.sample_rate = sample_rate
        self.amplitude = amplitude
        self.phase = 0.0  # continuous phase (radians)

    def generate(self, freq, duration):
        """Generate samples for a tone, maintaining phase continuity."""
        n_samples = int(self.sample_rate * duration)
        samples = []
        phase_inc = 2.0 * math.pi * freq / self.sample_rate

        # Soft envelope: fade the first & last few samples to avoid clicks
        fade_len = min(40, n_samples // 6)

        for i in range(n_samples):
            # Fundamental
            s = math.sin(self.phase)
            # Warm harmonics: gentle 2nd and 3rd overtones
            s += 0.15 * math.sin(2.0 * self.phase)
            s += 0.07 * math.sin(3.0 * self.phase)
            # Normalize so peak doesn't exceed amplitude
            s *= self.amplitude * 0.82

            # Envelope shaping (smooth fade in/out)
            if i < fade_len:
                env = i / fade_len
                s *= env * env           # quadratic fade-in
            elif i > n_samples - fade_len:
                env = (n_samples - i) / fade_len
                s *= env * env           # quadratic fade-out

            samples.append(s)
            self.phase += phase_inc

        # Keep phase in [0, 2*pi) to avoid float drift
        self.phase %= (2.0 * math.pi)
        return samples


def _build_bit_sequence(text):
    """Convert text to a flat list of KCS bits (with leader/trailer)."""
    bits = []
    # Leader tone (continuous 1-bits)
    leader_bits = int(LEADER_SECONDS * BAUD_RATE)
    bits.extend([1] * leader_bits)
    # Encode each character
    for ch in text:
        byte_val = ord(ch) & 0xFF
        bits.append(0)  # start bit
        for i in range(8):
            bits.append((byte_val >> i) & 1)
        bits.extend([1, 1])  # 2 stop bits
    # Trailer
    bits.extend([1] * 30)
    return bits


def encode_text(text):
    """Encode a string into KCS audio samples (list of floats -1.0..1.0)."""
    bits = _build_bit_sequence(text)
    gen = _ToneGenerator()
    samples = []
    for bit in bits:
        freq = FREQ_ONE if bit else FREQ_ZERO
        samples.extend(gen.generate(freq, BIT_DURATION))
    return samples


def write_wav(filepath, samples, sample_rate=SAMPLE_RATE):
    """Write a list of float samples (-1.0..1.0) to a 16-bit mono WAV."""
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for s in samples:
            # Clamp and convert to signed 16-bit
            clamped = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack("<h", int(clamped * 32767)))


def encode_file(input_txt_path, output_wav_path):
    """Read a text file and write KCS-encoded audio to a WAV file."""
    with open(input_txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    samples = encode_text(text)
    write_wav(output_wav_path, samples)
    duration = len(samples) / SAMPLE_RATE
    return len(text), duration


# ── Decoder ─────────────────────────────────────────────────────────────────

def read_wav(filepath):
    """Read a mono WAV file and return (samples_as_floats, sample_rate)."""
    with wave.open(filepath, "r") as wf:
        n_channels = wf.getnchannels()
        samp_width = wf.getsampwidth()
        rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if samp_width == 2:
        fmt = "<{}h".format(n_frames * n_channels)
        int_samples = struct.unpack(fmt, raw)
        samples = [s / 32767.0 for s in int_samples]
    elif samp_width == 1:
        int_samples = struct.unpack("{}B".format(n_frames * n_channels), raw)
        samples = [(s - 128) / 128.0 for s in int_samples]
    else:
        raise ValueError(f"Unsupported sample width: {samp_width}")

    # If stereo, take only the first channel
    if n_channels > 1:
        samples = samples[0::n_channels]

    return samples, rate


def _count_zero_crossings(samples, start, end):
    """Count zero crossings in a slice of samples."""
    crossings = 0
    for i in range(start + 1, end):
        if (samples[i - 1] >= 0 and samples[i] < 0) or \
           (samples[i - 1] < 0 and samples[i] >= 0):
            crossings += 1
    return crossings


def _decode_bit(samples, offset, samples_per_bit):
    """Decode one bit starting at `offset`. Returns (bit_value, next_offset)."""
    end = offset + samples_per_bit
    if end > len(samples):
        return None, end
    crossings = _count_zero_crossings(samples, offset, end)
    # 1200 Hz → ~8 crossings per bit period, 2400 Hz → ~16 crossings
    # Threshold at ~12
    threshold = (FREQ_ZERO + FREQ_ONE) / BAUD_RATE  # (1200+2400)/300 = 12
    bit_val = 1 if crossings >= threshold else 0
    return bit_val, end


def _find_start_bit(samples, offset, samples_per_bit):
    """Scan forward until we find a 0-bit (start bit). Returns its offset."""
    while offset + samples_per_bit <= len(samples):
        bit, _ = _decode_bit(samples, offset, samples_per_bit)
        if bit is None:
            return None
        if bit == 0:
            return offset
        offset += samples_per_bit
    return None


def decode_samples(samples, sample_rate=SAMPLE_RATE):
    """Decode KCS audio samples back to text."""
    samples_per_bit = int(sample_rate * BIT_DURATION)
    text = []
    offset = 0

    while True:
        # Find the next start bit
        start_offset = _find_start_bit(samples, offset, samples_per_bit)
        if start_offset is None:
            break

        # Skip the start bit
        offset = start_offset + samples_per_bit

        # Read 8 data bits (LSB first)
        byte_val = 0
        ok = True
        for i in range(8):
            bit, offset = _decode_bit(samples, offset, samples_per_bit)
            if bit is None:
                ok = False
                break
            byte_val |= (bit << i)
        if not ok:
            break

        # Read 2 stop bits (expect 1s, but don't fail hard)
        for _ in range(2):
            bit, offset = _decode_bit(samples, offset, samples_per_bit)
            if bit is None:
                break

        # Convert to character
        if 0 < byte_val < 128:
            text.append(chr(byte_val))
        elif byte_val >= 128:
            # Extended ASCII – just keep it
            text.append(chr(byte_val))

    return "".join(text)


def decode_file(input_wav_path, output_txt_path=None):
    """Decode a KCS WAV file back to text. Optionally write to a file."""
    samples, rate = read_wav(input_wav_path)
    text = decode_samples(samples, rate)
    if output_txt_path:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(text)
    return text
