# txt2wav — kayman send me msg via telegram id: @mrwolf621

Store text on cassette tapes as audio tones using the [Kansas City Standard](https://en.wikipedia.org/wiki/Kansas_City_standard) (KCS).

Encodes text into a `.wav` file you can record onto a cassette tape via an aux cable, then play it back and decode it into text again.

## How It Works

- **300 baud** (bits per second)
- Logic `0` = 4 cycles of 1200 Hz
- Logic `1` = 8 cycles of 2400 Hz
- Each byte: 1 start bit + 8 data bits (LSB first) + 2 stop bits

No dependencies — pure Python stdlib (`wave`, `struct`, `math`).

## Usage

### Encode text to WAV

```bash
python3 main.py encode input.txt output.wav
```

### Decode WAV back to text

```bash
python3 main.py decode output.wav decoded.txt
```

Or print decoded text to the terminal:

```bash
python3 main.py decode output.wav
```

### Quick roundtrip test

```bash
python3 main.py demo
```

## Recording to Cassette

1. Encode your text: `python3 main.py encode myfile.txt myfile.wav`
2. Connect your computer's headphone jack to the cassette recorder's line-in with an aux cable
3. Hit record on the cassette, then play `myfile.wav`
4. To read it back: play the cassette into your computer's line-in and record it as a `.wav`
5. Decode: `python3 main.py decode recorded.wav output.txt`

## Example

```
$ echo "Hello, cassette world!" > sample.txt
$ python3 main.py encode sample.txt output.wav
Encoded 23 characters → output.wav
Audio duration: 1.94s  (0.0 min)
Effective rate: ~12 chars/sec  (300 baud)

$ python3 main.py decode output.wav
--- Decoded text (23 chars) ---
Hello, cassette world!
--- end ---
```
