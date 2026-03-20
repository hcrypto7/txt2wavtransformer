#!/usr/bin/env python3
"""
txt2wav — Kansas City Standard encoder/decoder CLI.

Usage:
  python main.py encode  input.txt  output.wav   # text  → cassette audio
  python main.py decode  input.wav  [output.txt]  # cassette audio → text
  python main.py demo                              # quick roundtrip test
"""

import sys
import os
from kcs import encode_file, encode_text, write_wav, decode_file


def cmd_encode(args):
    if len(args) < 2:
        print("Usage: python main.py encode <input.txt> <output.wav>")
        sys.exit(1)
    txt_path = args[0]
    wav_path = args[1]
    if not os.path.isfile(txt_path):
        print(f"Error: file not found: {txt_path}")
        sys.exit(1)
    n_chars, duration = encode_file(txt_path, wav_path)
    print(f"Encoded {n_chars} characters → {wav_path}")
    print(f"Audio duration: {duration:.2f}s  ({duration/60:.1f} min)")
    rate_cps = n_chars / duration if duration else 0
    print(f"Effective rate: ~{rate_cps:.0f} chars/sec  ({300} baud)")


def cmd_decode(args):
    if len(args) < 1:
        print("Usage: python main.py decode <input.wav> [output.txt]")
        sys.exit(1)
    wav_path = args[0]
    txt_path = args[1] if len(args) > 1 else None
    if not os.path.isfile(wav_path):
        print(f"Error: file not found: {wav_path}")
        sys.exit(1)
    text = decode_file(wav_path, txt_path)
    if txt_path:
        print(f"Decoded {len(text)} characters → {txt_path}")
    else:
        print(f"--- Decoded text ({len(text)} chars) ---")
        print(text)
        print("--- end ---")


def cmd_demo(_args):
    """Quick roundtrip demo: encode a string, write wav, decode it back."""
    test_text = "Hello, kayman! Kansas City Standard rules. 1234567890"
    print(f"Original : {test_text}")

    wav_path = "demo_output.wav"
    samples = encode_text(test_text)
    write_wav(wav_path, samples)
    duration = len(samples) / 48000
    print(f"Encoded  : {len(test_text)} chars → {wav_path} ({duration:.2f}s)")

    decoded = decode_file(wav_path)
    print(f"Decoded  : {decoded}")

    if decoded == test_text:
        print("\n✓ PERFECT roundtrip — decoded text matches original!")
    else:
        print(f"\n✗ Mismatch! Got {len(decoded)} chars back.")
        # Show first difference
        for i, (a, b) in enumerate(zip(test_text, decoded)):
            if a != b:
                print(f"  First diff at position {i}: expected {repr(a)}, got {repr(b)}")
                break

    # Cleanup
    if os.path.exists(wav_path):
        os.remove(wav_path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()
    rest = sys.argv[2:]

    commands = {
        "encode": cmd_encode,
        "decode": cmd_decode,
        "demo":   cmd_demo,
    }
    if command in commands:
        commands[command](rest)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
