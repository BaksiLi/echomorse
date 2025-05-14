#!/usr/bin/env python3
"""
Command-line interface for Echo-Morse.
"""
import argparse
import sys
import os
import logging
from typing import Optional, List, Dict, Any
import io

from . import __version__
from .translator import translator
from .synthesizer import synthesizer
from .utils.voice_manager import list_available_voices, get_voice_info

# Configure logging
logger = logging.getLogger("echomorse")


def setup_logging(verbosity: int, log_file: Optional[str] = None) -> None:
    """Configure logging based on verbosity level."""
    # Set up root logger
    root_logger = logging.getLogger()

    # Clear existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set log levels based on verbosity
    if verbosity == 0:
        console_level = logging.WARNING
    elif verbosity == 1:
        console_level = logging.INFO
    else:  # verbosity >= 2
        console_level = logging.DEBUG

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Configure file handler if log_file specified
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(
                min(console_level, logging.DEBUG)
            )  # File logs are always at least as detailed as console
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to set up log file {log_file}: {e}")

    # Set root logger level to the most detailed level used by any handler
    root_logger.setLevel(min(console_level, logging.DEBUG))


def get_input_from_pipe() -> Optional[str]:
    """Check if input is being piped in and return it if available."""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return None


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times: -v, -vv)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all output except errors"
    )
    parser.add_argument("--log-file", type=str, help="Log output to specified file")


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    # Main parser
    parser = argparse.ArgumentParser(
        prog="echomorse",
        description="Echo-Morse: Convert text to/from Morse code with customizable audio output",
    )
    add_common_args(parser)
    
    # Add version argument
    parser.add_argument(
        "--version", action="version", version=f"Echo-Morse v{__version__}"
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command", title="commands", required=True, help="Available commands"
    )

    # === TEXT TO MORSE CODE NOTATION ===
    t2c_parser = subparsers.add_parser(
        "text2code", aliases=["t2c"], help="Convert text to Morse code notation"
    )
    t2c_parser.add_argument(
        "text", nargs="?", help="Text to convert to Morse code (can also be piped in)"
    )
    t2c_parser.add_argument("-o", "--output", help="Output file (defaults to stdout)")

    # === MORSE CODE TO TEXT ===
    c2t_parser = subparsers.add_parser(
        "code2text", aliases=["c2t"], help="Convert Morse code notation to text"
    )
    c2t_parser.add_argument(
        "morse_code",
        nargs="?",
        help="Morse code to convert to text (can also be piped in)",
    )
    c2t_parser.add_argument("-o", "--output", help="Output file (defaults to stdout)")

    # === TEXT TO AUDIO ===
    t2a_parser = subparsers.add_parser(
        "text2audio", aliases=["t2a"], help="Convert text directly to Morse code audio"
    )
    t2a_parser.add_argument(
        "text", nargs="?", help="Text to convert to audio (can also be piped in)"
    )
    t2a_parser.add_argument(
        "-o",
        "--output",
        default="morse_output.wav",
        help="Output WAV file (default: morse_output.wav)",
    )
    t2a_parser.add_argument(
        "--voice",
        help="Voice profile to use (use 'list-voices' to see available options)",
    )
    t2a_parser.add_argument(
        "--wpm", type=int, default=20, help="Speed in words per minute (default: 20)"
    )
    t2a_parser.add_argument(
        "--pattern-chance",
        type=float,
        default=1.0,
        help="Chance (0.0-1.0) to use sequence patterns from voice profile (default: 1.0)",
    )
    t2a_parser.add_argument(
        "--fade-type",
        choices=["percentage", "absolute"],
        default="percentage",
        help="Type of fade to apply (default: percentage)",
    )
    t2a_parser.add_argument(
        "--fade-value",
        type=float,
        default=5.0,
        help="Fade value (percentage or milliseconds, default: 5.0)",
    )
    t2a_parser.add_argument(
        "--target-dbfs",
        type=float,
        default=-20.0,
        help="Target dBFS for audio normalization (default: -20.0)",
    )

    # === MORSE CODE TO AUDIO ===
    c2a_parser = subparsers.add_parser(
        "code2audio", aliases=["c2a"], help="Convert Morse code notation to audio"
    )
    c2a_parser.add_argument(
        "morse_code",
        nargs="?",
        help="Morse code to convert to audio (can also be piped in)",
    )
    c2a_parser.add_argument(
        "-o",
        "--output",
        default="morse_output.wav",
        help="Output WAV file (default: morse_output.wav)",
    )
    c2a_parser.add_argument(
        "--voice",
        help="Voice profile to use (use 'list-voices' to see available options)",
    )
    c2a_parser.add_argument(
        "--wpm", type=int, default=20, help="Speed in words per minute (default: 20)"
    )
    c2a_parser.add_argument(
        "--pattern-chance",
        type=float,
        default=1.0,
        help="Chance (0.0-1.0) to use sequence patterns from voice profile (default: 1.0)",
    )
    c2a_parser.add_argument(
        "--fade-type",
        choices=["percentage", "absolute"],
        default="percentage",
        help="Type of fade to apply (default: percentage)",
    )
    c2a_parser.add_argument(
        "--fade-value",
        type=float,
        default=5.0,
        help="Fade value (percentage or milliseconds, default: 5.0)",
    )
    c2a_parser.add_argument(
        "--target-dbfs",
        type=float,
        default=-20.0,
        help="Target dBFS for audio normalization (default: -20.0)",
    )

    # === AUDIO TO TEXT (placeholder) ===
    a2t_parser = subparsers.add_parser(
        "audio2text",
        aliases=["a2t"],
        help="Convert Morse code audio to text (experimental)",
    )
    a2t_parser.add_argument("audio_file", help="Audio file containing Morse code")
    a2t_parser.add_argument("-o", "--output", help="Output file (defaults to stdout)")

    # === LIST VOICES ===
    voices_parser = subparsers.add_parser(
        "list-voices", help="List available voice profiles"
    )
    voices_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information about each voice",
    )

    return parser


def handle_text2code(args: argparse.Namespace) -> int:
    """Handle text to Morse code conversion."""
    # Get input from argument or stdin pipe
    text = args.text or get_input_from_pipe()
    if not text:
        logger.error("No input text provided. Use positional argument or pipe input.")
        return 1

    # Convert to Morse code
    morse_code = translator.text_to_morse(text)

    # Output result
    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(morse_code)
            logger.info(f"Morse code written to: {args.output}")
        except Exception as e:
            logger.error(f"Failed to write to output file: {e}")
            return 1
    else:
        # Print to stdout without logging prefix
        print(morse_code)

    return 0


def handle_code2text(args: argparse.Namespace) -> int:
    """Handle Morse code to text conversion."""
    # Get input from argument or stdin pipe
    morse_code = args.morse_code or get_input_from_pipe()
    if not morse_code:
        logger.error(
            "No input Morse code provided. Use positional argument or pipe input."
        )
        return 1

    # Convert to text
    text = translator.morse_to_text(morse_code)

    # Output result
    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(text)
            logger.info(f"Text written to: {args.output}")
        except Exception as e:
            logger.error(f"Failed to write to output file: {e}")
            return 1
    else:
        # Print to stdout without logging prefix
        print(text)

    return 0


def handle_text2audio(args: argparse.Namespace) -> int:
    """Handle text to audio conversion."""
    # Get input from argument or stdin pipe
    text = args.text or get_input_from_pipe()
    if not text:
        logger.error("No input text provided. Use positional argument or pipe input.")
        return 1

    # Convert text to Morse code
    morse_code = translator.text_to_morse(text)
    if not morse_code:
        logger.error("Input text did not produce valid Morse code.")
        return 1

    if args.output == "-":
        # Use a BytesIO buffer for stdout to avoid buffering issues
        buffer = io.BytesIO()
        log_input_text = None  # Avoid logging input text if streaming

        try:
            synthesizer.generate_morse_audio(
                morse_code=morse_code,
                output_file=buffer,
                voice_name_full=args.voice,
                wpm=args.wpm,
                pattern_chance=args.pattern_chance,
                fade_type=args.fade_type,
                fade_value=args.fade_value,
                target_dbfs=args.target_dbfs,
                input_text_for_log=log_input_text,
            )

            # Get the WAV data
            wav_data = buffer.getvalue()

            # Write directly to stdout file descriptor to bypass Python's stdout buffering
            os.write(1, wav_data)
            return 0

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return 1
    else:
        # Normal file output
        output_target = args.output
        log_input_text = text  # Include input text in log for file output

        try:
            synthesizer.generate_morse_audio(
                morse_code=morse_code,
                output_file=output_target,
                voice_name_full=args.voice,
                wpm=args.wpm,
                pattern_chance=args.pattern_chance,
                fade_type=args.fade_type,
                fade_value=args.fade_value,
                target_dbfs=args.target_dbfs,
                input_text_for_log=log_input_text,
            )
            return 0
        except Exception as e:
            # Error already logged by synthesizer
            return 1


def handle_code2audio(args: argparse.Namespace) -> int:
    """Handle Morse code to audio conversion."""
    # Get input from argument or stdin pipe
    morse_code = args.morse_code or get_input_from_pipe()
    if not morse_code:
        logger.error(
            "No input Morse code provided. Use positional argument or pipe input."
        )
        return 1

    if args.output == "-":
        # Use a BytesIO buffer for stdout to avoid buffering issues
        buffer = io.BytesIO()

        try:
            synthesizer.generate_morse_audio(
                morse_code=morse_code,
                output_file=buffer,
                voice_name_full=args.voice,
                wpm=args.wpm,
                pattern_chance=args.pattern_chance,
                fade_type=args.fade_type,
                fade_value=args.fade_value,
                target_dbfs=args.target_dbfs,
                # No input_text_for_log here as we start from morse code
            )

            # Get the WAV data
            wav_data = buffer.getvalue()

            # Write directly to stdout file descriptor to bypass Python's stdout buffering
            os.write(1, wav_data)
            return 0

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return 1
    else:
        # Normal file output
        output_target = args.output

        try:
            synthesizer.generate_morse_audio(
                morse_code=morse_code,
                output_file=output_target,
                voice_name_full=args.voice,
                wpm=args.wpm,
                pattern_chance=args.pattern_chance,
                fade_type=args.fade_type,
                fade_value=args.fade_value,
                target_dbfs=args.target_dbfs,
                # No input_text_for_log here as we start from morse code
            )
            return 0
        except Exception as e:
            # Error already logged by synthesizer
            return 1


def handle_audio2text(args: argparse.Namespace) -> int:
    """Handle audio to text conversion (placeholder)."""
    logger.warning("Audio to text conversion is not yet implemented.")
    return 1


def handle_list_voices(args: argparse.Namespace) -> int:
    """Handle listing available voices."""
    all_voices = list_available_voices()

    if not all_voices:
        logger.warning("No voices found.")
        logger.info(
            "To add a custom voice, create a subdirectory in 'audio/' (e.g., 'audio/my_voice/'),"
        )
        logger.info("add your .wav files, and a 'voice_config.json' pointing to them.")
        return 1

    # Sort voices (ensure CW is first)
    sorted_voices = sorted(all_voices, key=lambda v: (v != "CW (built-in)", v))

    # Output voice list
    print("Available voice profiles:")
    for voice_name in sorted_voices:
        voice_info = get_voice_info(voice_name)

        if args.detailed:
            # Detailed output format
            print(f"\n  {voice_name}")
            print(f"  {'=' * len(voice_name)}")
            print(f"  Description: {voice_info['description'] or 'No description'}")
            print(f"  Audio files: {voice_info['audio_count']}")
            print(f"  Has patterns: {'Yes' if voice_info['has_patterns'] else 'No'}")
        else:
            # Simple format
            description = voice_info["description"]
            desc_str = f": {description}" if description else ""
            pattern_info = " (patterns)" if voice_info["has_patterns"] else ""
            files_info = (
                f"{voice_info['audio_count']} files"
                if voice_info["audio_count"] > 0
                else "built-in"
            )

            print(f"  - {voice_name}{desc_str} ({files_info}{pattern_info})")

    return 0


def run_cli() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging based on verbosity level
    if args.quiet:
        setup_logging(-1, args.log_file)  # -1 means only errors
    else:
        setup_logging(args.verbose, args.log_file)

    # Dispatch to appropriate handler based on command
    command_handlers = {
        "text2code": handle_text2code,
        "t2c": handle_text2code,
        "code2text": handle_code2text,
        "c2t": handle_code2text,
        "text2audio": handle_text2audio,
        "t2a": handle_text2audio,
        "code2audio": handle_code2audio,
        "c2a": handle_code2audio,
        "audio2text": handle_audio2text,
        "a2t": handle_audio2text,
        "list-voices": handle_list_voices,
    }

    # Call the appropriate handler function
    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


def main() -> int:
    """Entry point for the CLI."""
    try:
        return run_cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
