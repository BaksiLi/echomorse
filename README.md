# Echo-Morse


[![CI](https://github.com/BaksiLi/echomorse/actions/workflows/ci.yml/badge.svg)](https://github.com/BaksiLi/echomorse/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/echomorse.svg)](https://badge.fury.io/py/echomorse)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> a.k.a. 摩斯電狗 (Morse the E-Dog)

A versatile tool for converting text to Morse code (CW) with customizable audio synthesis, designed for HAM radio operators and enthusiasts.

## Features

- Convert text to/from Morse code notation
- Generate CW audio with customizable voices and parameters
- Support for ham radio abbreviations and prosigns (e.g. CQ, SK, AR, etc.)
- Adjustable speed, timing, and sound characteristics

For planned enhancements and upcoming features, see our [TODO](./TODO.md) list.

## Installation

### From PyPI (Recommended)

The easiest way to install Echo-Morse is via pip:

```bash
pip install echomorse
```

This will install the package and make the `echomorse` command available in your environment.

Make sure you have `ffmpeg` installed.

### From Source

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/baksili/echo-morse.git
    cd echo-morse
    ```
2.  **Install with PDM:**
    PDM is used for managing dependencies and the project environment.
    ```bash
    pdm install
    ```
    This installs the package and its dependencies. The `echomorse` command will then be available within the PDM environment (e.g., via `pdm run echomorse ...`) or globally if you activate the PDM virtual environment or install it globally.

## Basic Usage

All commands are run using the `echomorse` entry point. If you've installed via pip, you can simply run `echomorse <command>`. If you've installed from source using PDM, you can run via `pdm run echomorse <command>`.

**Convert text to Morse code notation:**
```bash
echomorse text2code "CQ DX"
# Shorter alias:
echomorse t2c "CQ DX"
```

**Convert Morse code notation to text:**
```bash
echomorse code2text ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."
# Shorter alias:
echomorse c2t ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."
```

**Convert text directly to Morse code audio:**
```bash
echomorse text2audio "CQ CQ DE BY1QH" --output cq_call.wav
# Shorter alias:
echomorse t2a "CQ CQ DE BY1QH" -o cq_call.wav
```

**Direct Playback:**

You can pipe the audio output directly to an audio player. `ffplay` (from the FFmpeg project) is recommended for its robust support for stdin streaming.

```bash
echomorse t2a "SOS" -o - | ffplay -i - -nodisp -autoexit
```

N.B. Unlike many other commands, `afplay` on macOS doesn't reliably support reading from stdin. If you're using macOS, install `ffplay` via Homebrew (`brew install ffmpeg`) for this functionality.

**Convert Morse code notation directly to audio:**
```bash
echomorse code2audio "... --- ..." --output sos.wav
# Shorter alias:
echomorse c2a "... --- ..." -o sos.wav
```

**Direct Playback:**

Using `ffplay`:
```bash
echomorse c2a "TEST" -o - | ffplay -i - -nodisp -autoexit
```

**List available voices:**
```bash
echomorse list-voices
# Show detailed information about each voice:
echomorse list-voices --detailed
```

### Piping Examples

Echo-Morse commands are designed to work with Unix-style pipes. Input arguments for text or Morse code can be piped from `stdin`.

```bash
# Convert text to Morse code via pipe, then to audio
echo "HELLO WORLD" | echomorse t2c | echomorse c2a -o pipe_hw.wav

# Process text from a file using cat and pipe to text2audio
cat message.txt | echomorse t2a -o message_from_file.wav --wpm 25

# Save Morse code to a file, then pipe its content to code2audio
echo "TEST" | echomorse t2c > morse_output.txt
cat morse_output.txt | echomorse c2a -o audio_from_morse_file.wav
```

### Command Options and Help

All commands and subcommands support `-h` or `--help` for detailed usage information:
```bash
echomorse -h
echomorse text2audio -h
```

**Common audio generation options:**
```bash
# Specify a voice and speed (WPM)
echomorse t2a "SOS" --voice dog_bark --wpm 15 -o sos_dog.wav

# Control fade type and value (e.g., 10% fade)
echomorse t2a "HELLO" --fade-type percentage --fade-value 10 -o hello_fade_p.wav

# Control fade type and value (e.g., 15ms absolute fade)
echomorse t2a "WORLD" --fade-type absolute --fade-value 15 -o world_fade_abs.wav

# Set the normalization level (in dBFS)
echomorse t2a "CQ" --target-dbfs -18 -o cq_louder.wav

# Adjust pattern matching probability for voices with sequence patterns
echomorse t2a "CQ DE BY1QH" --voice dog_bark --pattern-chance 0.5 -o cq_dog_less_pattern.wav
```

## Voice System Explained

The voice system allows for customizable audio outputs beyond simple tones. Each voice is a collection of audio files and configuration settings.

### Built-in Voices

Echo-Morse comes with two built-in voices:
- **CW (built-in)**: Default sine wave tones for standard Morse code
- **dog_bark**: Dog bark sounds for Morse code (automatically installed on first run)

To see all available voices:
```bash
echomorse list-voices
```

To install or manage voice packs:
```bash
# Install all built-in voices (if they weren't auto-installed)
echomorse voice-utils install-builtin

# View voice directory locations
echomorse voice-utils dirs
```

### Custom Voice Packs

Voices are stored in one of these locations:
1. The OS-specific user data directory (e.g., `~/.local/share/echomorse/audio` on Linux)
2. `~/.echomorse/audio/` directory
3. The package's built-in audio directory (for pre-installed voices)

Each voice directory must contain:
1. A `voice_config.json` configuration file
2. Audio files (e.g., `.wav`) referenced in the configuration

## License

MIT License