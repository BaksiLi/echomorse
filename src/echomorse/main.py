import argparse
from .translator import translator
from .synthesizer import synthesizer

# Placeholder for future interpreter import
# from .interpreter import interpreter
from .utils.voice_manager import (
    list_available_voices,
    # create_voice_from_audio_files, # No longer used by main.py as add-voice is removed
    # VOICE_CATEGORIES, # Removed
    get_voice_info,  # Added for enhanced voice listing
    generate_dummy_voice_samples,  # Keep for potential future programmatic use
)
import os
import sys
# from typing import Dict, List # No longer needed here after list-voices simplification


def main():
    parser = argparse.ArgumentParser(
        description="Echo-Morse: Translate text to Morse code sounds using various voices."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # --- text-to-morse-audio command ---
    parser_ttm = subparsers.add_parser(
        "text-to-morse-audio", help="Convert text to morse code audio file."
    )
    parser_ttm.add_argument("text", type=str, help="The text string to convert.")
    parser_ttm.add_argument(
        "-o",
        "--output",
        type=str,
        default="output_morse.wav",
        help="Path to save the output WAV file (default: output_morse.wav)",
    )
    parser_ttm.add_argument(
        "--voice",
        type=str,
        help='Voice to use for the morse code elements (e.g., "dog1"). If not specified, uses sine wave tones.',
    )
    parser_ttm.add_argument(
        "--wpm",
        type=int,
        default=20,
        help="Words per minute for playback speed (default: 20).",
    )
    parser_ttm.add_argument(
        "--pattern-chance",
        type=float,
        default=1.0,
        help="Chance (0.0 to 1.0) to use a custom sequence pattern if matched. Default: 1.0 (always use).",
    )
    # parser_ttm.add_argument('--config', type=str, help='Path to a custom configuration file.') # Future enhancement

    # --- morse-audio-to-text command (Placeholder for now) ---
    parser_mtt = subparsers.add_parser(
        "morse-audio-to-text", help="Convert morse code audio file to text."
    )
    parser_mtt.add_argument(
        "audio_file", type=str, help="Path to the input WAV audio file."
    )
    # parser_mtt.add_argument('--config', type=str, help='Path to a custom configuration file.') # Future enhancement

    # --- text-to-morse command (Utility) ---
    parser_ttm_code = subparsers.add_parser(
        "text-to-morse", help="Convert text to Morse code string."
    )
    parser_ttm_code.add_argument("text", type=str, help="The text string to convert.")

    # --- morse-to-text command (Utility) ---
    parser_mtt_code = subparsers.add_parser(
        "morse-to-text", help="Convert Morse code string to text."
    )
    parser_mtt_code.add_argument(
        "morse_code", type=str, help="The Morse code string to convert."
    )

    # --- list-voices command ---
    parser_lv = subparsers.add_parser("list-voices", help="List available voices.")

    # --- add-voice command (Removed) ---
    # parser_av = subparsers.add_parser('add-voice', help='Add a new voice from audio files.')
    # ... (arguments for add-voice removed)

    args = parser.parse_args()

    if args.command == "text-to-morse-audio":
        # Validate pattern_chance range
        if not (0.0 <= args.pattern_chance <= 1.0):
            print("Error: --pattern-chance must be between 0.0 and 1.0.")
            return

        print(
            f"Converting text: '{args.text}' to morse audio at '{args.output}' with WPM: {args.wpm} and pattern chance: {args.pattern_chance}"
        )

        voice_name = getattr(args, "voice", None)
        if voice_name and ("/" in voice_name or "\\" in voice_name):
            print(
                f"Error: Voice name '{voice_name}' should not contain path separators. Please provide a simple voice name."
            )
            return

        morse_code = translator.text_to_morse(args.text)
        print(f"Intermediate Morse: {morse_code}")
        if morse_code:
            try:
                synthesizer.generate_morse_audio(
                    morse_code,
                    args.output,
                    voice_name_full=voice_name,
                    wpm=args.wpm,
                    pattern_chance=args.pattern_chance,
                )
            except FileNotFoundError as e:
                print(
                    f"Error during audio generation: {e}. Ensure voice '{voice_name}' is configured correctly or files exist."
                )
            except Exception as e:
                print(f"An unexpected error occurred during audio generation: {e}")
        else:
            print("Input text did not produce any Morse code. No audio generated.")

    elif args.command == "morse-audio-to-text":
        print(f"Converting morse audio from '{args.audio_file}' to text.")
        print("Morse audio decoding not yet implemented.")

    elif args.command == "text-to-morse":
        morse_code = translator.text_to_morse(args.text)
        print(f"Morse Code: {morse_code}")

    elif args.command == "morse-to-text":
        text_result = translator.morse_to_text(args.morse_code)
        print(f"Text: {text_result}")

    elif args.command == "list-voices":
        all_voices = list_available_voices()
        if all_voices:
            print("Available voices:")
            # Ensure 'CW (built-in)' is always first if it exists
            sorted_voices = sorted(
                all_voices,
                key=lambda v: (
                    v != "CW (built-in)",
                    v,
                ),  # Sorts CW (built-in) first, then alphabetically
            )

            for voice_name in sorted_voices:
                voice_info = get_voice_info(voice_name)
                description = voice_info["description"]
                audio_count = voice_info["audio_count"]
                has_patterns = voice_info["has_patterns"]

                # Format display string
                desc_str = f": {description}" if description else ""
                pattern_info = " (patterns)" if has_patterns else ""
                files_info = f"{audio_count} files" if audio_count > 0 else "built-in"

                print(f"  - {voice_name}{desc_str} ({files_info}{pattern_info})")

        else:
            # This case might be less likely if CW (built-in) is always present
            print("No voices found.")
            print(
                "To add a custom voice, create a subdirectory in 'audio/' (e.g., 'audio/my_voice/'),"
            )
            print("add your .wav files, and a 'voice_config.json' pointing to them.")

    # elif args.command == 'add-voice': # Logic removed
    #     pass

    else:
        # This case should ideally not be reached if subparsers are required=True
        # and a command is always provided.
        parser.print_help()


if __name__ == "__main__":
    main()
