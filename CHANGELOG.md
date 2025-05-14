# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - YYYY-MM-DD

### Added
- **Major CLI Redesign**:
    - Introduced `src/echomorse/cli.py` using `argparse` for a structured command-line interface.
    - Main command `echomorse` with subcommands: `text2code` (alias `t2c`), `code2text` (`c2t`), `text2audio` (`t2a`), `code2audio` (`c2a`), `audio2text` (`a2t` - placeholder), and `list-voices`.
    - Common arguments: `-v/--verbose` (for verbosity levels), `-q/--quiet`, and `--log-file`.
    - Input for text/Morse code can be taken from positional arguments or `stdin`.
    - Output for text/Morse code can go to `stdout` or a file.
    - All synthesizer audio parameters (voice, WPM, pattern chance, fade type/value, target dBFS) exposed as CLI arguments for audio generation commands.
    - `setup_logging` function for configurable console and optional file logging.
- **Package Executability**: Created `src/echomorse/__main__.py` to allow running the package with `python -m echomorse`.
- **Audio Streaming**: Modified `synthesizer.py` and `cli.py` to allow audio output to `sys.stdout.buffer` (using `-o -`), enabling direct piping to audio players.
- **Direct Playback Documentation**: Updated `README.md` with instructions for direct audio playback, recommending `ffplay`.
- **Configurable Fades & Normalization**:
    - Made fade type ("percentage" or "absolute") and fade value configurable parameters in `generate_morse_audio` and CLI.
    - Added audio normalization to a configurable target dBFS in `synthesizer.py` and exposed it via CLI.
- **Initial `CHANGELOG.md` file.**

### Changed
- **Configuration Management**: Centralized Morse code timing and audio constants from `synthesizer.py` into `config.py`.
- **Updated Synthesizer & Voice Manager**: Modified `synthesizer.py` and `utils/voice_manager.py` to use constants from `config.py`.
- **`pyproject.toml` Updates**:
    - Updated `[project.scripts]` to point `echomorse` to `echomorse.cli:main`.
    - Updated `[tool.pdm.scripts]` to use the new `echomorse <subcommand>` structure.
    - Corrected build system configuration for proper packaging.
- **Improved Logging**: Implemented more structured and informative logging in `generate_morse_audio`, including original input text.
- **Stdout Piping Fixes**: Implemented a more robust solution for writing binary WAV data to `stdout` using `io.BytesIO` and `os.write` to overcome shell redirection issues.

### Removed
- **Standalone Shell Scripts**: Deleted legacy top-level shell scripts (`echomorse-cli`, `t2c`, `t2a`) in favor of the `echomorse` command installed by PDM.
- **Legacy Pitch Values**: Removed `DOT_PITCH` and `DASH_PITCH` from `config.py` as they were unused.

### Fixed
- Numerous fixes related to direct audio playback via stdout piping.
- Corrected `README.md` examples and structure.

### Deprecated
- N/A for this version.

### Security
- N/A for this version.

## [0.1.0] - Initial Version (Placeholder)
- Placeholder for features before current refactoring and CLI implementation. 