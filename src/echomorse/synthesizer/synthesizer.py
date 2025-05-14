from pydub import AudioSegment
from pydub.generators import Sine
from ..utils.voice_manager import get_voice_element_samples
from ..utils import voice_manager
from ..config import (
    DEFAULT_UNIT_DURATION_MS,
    SYMBOL_SPACE_UNITS,
    LETTER_SPACE_UNITS,
    WORD_SPACE_UNITS,
    DEFAULT_WPM,
    SAMPLE_RATE,
    DEFAULT_TONE_FREQ,
)
import os
import logging
import shutil
import random
import json
from typing import Optional, Tuple, Dict, List, Union, Any

logger = logging.getLogger(__name__)


def generate_default_tone(
    duration_ms: int,
    frequency: float = DEFAULT_TONE_FREQ,
    fade_type: str = "percentage",
    fade_value: float = 5.0,
) -> AudioSegment:
    """Generate a simple sine wave tone with fade in/out."""
    generator = Sine(frequency, sample_rate=SAMPLE_RATE)
    tone = generator.to_audio_segment(duration=duration_ms)
    
    if fade_value > 0:
        if fade_type == "percentage":
            # Ensure duration_ms is not zero to avoid division by zero if FADE_PERCENT could be 0
            fade_ms_calc = int(duration_ms * fade_value / 100) if duration_ms > 0 else 0
        else:  # absolute
            fade_ms_calc = int(fade_value)
        
        # Ensure fade_ms is not longer than half the tone duration
        fade_ms_actual = min(fade_ms_calc, duration_ms // 2) if duration_ms > 0 else 0
        
        if fade_ms_actual > 0:
            return tone.fade_in(fade_ms_actual).fade_out(fade_ms_actual)
    return tone


def normalize_audio(segment: AudioSegment, target_dbfs: float = -20.0) -> AudioSegment:
    """Normalize audio segment to target dBFS. Handles silence gracefully."""
    if segment.dBFS == float('-inf'): # Check if segment is silence
        logger.debug("Segment is silent, skipping normalization.")
        return segment
    difference = target_dbfs - segment.dBFS
    return segment.apply_gain(difference)


def _load_audio_element(
    element_value: Union[str, List[str]],
    voice_dir_path: str,
    element_key_for_log: str,
    fade_type: str,
    fade_value: float,
    target_dbfs: float = -20.0, # Added target_dbfs for normalization
) -> Optional[AudioSegment]:
    """
    Loads an audio segment for a given element value (filename or list of filenames).
    If element_value is a list, a random file is chosen.
    Applies normalization and fades.
    Returns None if loading fails or file not found.
    """
    if not element_value:
        logger.debug(f"Element '{element_key_for_log}' has no value in voice config.")
        return None

    filename_to_load: Optional[str] = None
    if isinstance(element_value, list):
        if not element_value:  # Empty list
            logger.warning(
                f"Element '{element_key_for_log}' is an empty list in voice config."
            )
            return None
        filename_to_load = random.choice(element_value)
        logger.debug(
            f"Randomly selected '{filename_to_load}' for element '{element_key_for_log}'."
        )
    elif isinstance(element_value, str):
        filename_to_load = element_value
    else:
        logger.warning(
            f"Invalid type for element '{element_key_for_log}' in voice config: {type(element_value)}. Expected str or list."
        )
        return None

    if (
        not filename_to_load
    ):  # Should not happen if checks above are fine, but as safeguard
        logger.warning(f"No filename determined for element '{element_key_for_log}'.")
        return None

    sample_path = os.path.join(voice_dir_path, filename_to_load)
    if not os.path.isfile(sample_path):
        logger.warning(
            f"Audio file '{filename_to_load}' (for element '{element_key_for_log}') not found at '{sample_path}'."
        )
        return None

    try:
        segment = AudioSegment.from_file(sample_path)
        # Apply normalization
        segment = normalize_audio(segment, target_dbfs=target_dbfs) # Pass target_dbfs

        # Apply fades based on fade_type
        if fade_value > 0:
            if fade_type == "percentage":
                fade_ms_calc = int(len(segment) * fade_value / 100) if len(segment) > 0 else 0
            else:  # absolute
                fade_ms_calc = int(fade_value)
            
            # Ensure fade_ms is not longer than half the segment duration
            fade_ms_actual = min(fade_ms_calc, len(segment) // 2) if len(segment) > 0 else 0

            if fade_ms_actual > 0:
                segment = segment.fade_in(fade_ms_actual).fade_out(fade_ms_actual)
        return segment
    except Exception as e:
        logger.error(
            f"Error loading audio file '{sample_path}' for element '{element_key_for_log}': {e}"
        )
        return None


def get_basic_morse_elements( # Unused for now, consider removal or refactor
    voice_config: Optional[Dict[str, Any]],
    voice_dir_path: Optional[str],
    actual_unit_time_ms: float,
    fade_type: str, # Added fade params
    fade_value: float, # Added fade params
    target_dbfs: float, # Added target_dbfs
) -> Tuple[AudioSegment, AudioSegment]:
    """
    Gets basic dot and dash AudioSegments. Uses voice config if provided, else defaults.
    Actual_unit_time_ms is the WPM-adjusted duration for a default dot tone.
    """
    dot_audio: Optional[AudioSegment] = None
    dash_audio: Optional[AudioSegment] = None

    if voice_config and voice_dir_path:
        elements = voice_config.get("elements", {})
        dot_val = elements.get("dot")
        dash_val = elements.get("dash")

        if dot_val:
            dot_audio = _load_audio_element(
                dot_val, voice_dir_path, "dot", fade_type, fade_value, target_dbfs
            )
        if dash_val:
            # Custom dash sound plays at its own length. No scaling applied here.
            dash_audio = _load_audio_element(
                dash_val, voice_dir_path, "dash", fade_type, fade_value, target_dbfs
            )

    if not dot_audio:
        logger.info(
            f"Using default tone for dot (duration: {actual_unit_time_ms:.2f}ms)."
        )
        dot_audio = generate_default_tone(duration_ms=int(actual_unit_time_ms), fade_type=fade_type, fade_value=fade_value)

    if not dash_audio:
        # Default dash is 3x the actual unit time for this synthesis
        default_dash_duration = actual_unit_time_ms * 3
        logger.info(
            f"Using default tone for dash (duration: {default_dash_duration:.2f}ms)."
        )
        dash_audio = generate_default_tone(duration_ms=int(default_dash_duration), fade_type=fade_type, fade_value=fade_value)

    return dot_audio, dash_audio


def generate_morse_audio(
    morse_code: str,
    output_file: Union[str, Any], # Allow str or file-like object
    voice_name_full: Optional[str] = None,
    wpm: int = DEFAULT_WPM, # Use default from config
    pattern_chance: float = 1.0,
    fade_type: str = "percentage",
    fade_value: float = 5.0,
    target_dbfs: float = -20.0, # Default normalization target
    input_text_for_log: Optional[str] = None, # For richer logging
):
    """Generate an audio file from Morse code, with dynamic timing and sequence patterns."""
    if not morse_code or morse_code.isspace():
        logger.error("Morse code cannot be empty or just whitespace.")
        raise ValueError("Morse code cannot be empty or just whitespace.")

    # --- Timing Calculation ---
    voice_config: Optional[Dict[str, Any]] = None
    voice_dir_path: Optional[str] = None
    base_unit_duration_for_voice_ms = float(DEFAULT_UNIT_DURATION_MS)

    if voice_name_full:
        voice_config = voice_manager.load_voice_config(voice_name_full)
        if voice_config:
            voice_dir_path = voice_manager.get_voice_dir_path(voice_name_full)
            if not voice_dir_path:
                logger.warning( # Changed to warning as it's a fallback case
                    f"Voice dir for '{voice_name_full}' disappeared or invalid. Using default timing & tones."
                )
                voice_config = None  # Force fallback
            else:
                elements_map = voice_config.get("elements", {})
                dot_element_value = elements_map.get("dot")
                if dot_element_value:
                    temp_dot_filename = ""
                    if isinstance(dot_element_value, list) and dot_element_value:
                        temp_dot_filename = dot_element_value[0]
                    elif isinstance(dot_element_value, str):
                        temp_dot_filename = dot_element_value
                    
                    if temp_dot_filename:
                        temp_dot_path = os.path.join(voice_dir_path, temp_dot_filename)
                        try:
                            # Load without normalization/fade for timing derivation
                            temp_dot_segment = AudioSegment.from_file(temp_dot_path)
                            base_unit_duration_for_voice_ms = float(
                                len(temp_dot_segment)
                            )
                            logger.info(
                                f"Using duration of voice's 'dot' element ('{temp_dot_filename}': {base_unit_duration_for_voice_ms:.2f}ms) as base unit time."
                            )
                        except Exception as e:
                            logger.warning(
                                f"Could not load '{temp_dot_filename}' to derive unit time for voice '{voice_name_full}': {e}. Using default unit time."
                            )
                else: # If "dot" is not in elements for custom voice
                    logger.info(f"Voice '{voice_name_full}' has no 'dot' element for timing. Using default unit time {DEFAULT_UNIT_DURATION_MS}ms.")
        else:
            logger.warning(
                f"Voice config for '{voice_name_full}' not found or invalid. Using default timing & tones."
            )

    actual_unit_time_ms = base_unit_duration_for_voice_ms * (DEFAULT_WPM / wpm)
    
    current_symbol_space_duration = SYMBOL_SPACE_UNITS * actual_unit_time_ms
    current_letter_space_duration = LETTER_SPACE_UNITS * actual_unit_time_ms
    current_word_space_duration = WORD_SPACE_UNITS * actual_unit_time_ms

    loaded_audio_segments: Dict[str, AudioSegment] = {}
    sequence_patterns_map: Dict[str, str] = {}
    sorted_morse_sequences: List[str] = []

    if voice_config and voice_dir_path:
        raw_patterns = voice_config.get("sequence_patterns", {})
        if isinstance(raw_patterns, dict):
            sorted_pattern_items = sorted(
                raw_patterns.items(), key=lambda item: len(item[1]), reverse=True
            )
            for el_key, morse_seq_str in sorted_pattern_items:
                if el_key and morse_seq_str:
                    sequence_patterns_map[morse_seq_str] = el_key
                    sorted_morse_sequences.append(morse_seq_str)
            if sorted_morse_sequences:
                logger.info(
                    f"Loaded {len(sorted_morse_sequences)} sequence patterns for voice '{voice_name_full}'."
                )

    def get_segment(
        element_key: str, default_duration_ms: Optional[float] = None
    ) -> Optional[AudioSegment]:
        nonlocal voice_config, voice_dir_path # Allow modification if needed
        if element_key in loaded_audio_segments:
            return loaded_audio_segments[element_key]

        segment: Optional[AudioSegment] = None
        if voice_config and voice_dir_path:
            elements_map = voice_config.get("elements", {})
            element_value = elements_map.get(element_key)
            if element_value:
                segment = _load_audio_element(
                    element_value, voice_dir_path, element_key, fade_type, fade_value, target_dbfs
                )

        if not segment and default_duration_ms is not None:
            # Default tones also need fade parameters
            segment = generate_default_tone(
                duration_ms=int(default_duration_ms), 
                frequency=DEFAULT_TONE_FREQ, # Assuming default frequency
                fade_type=fade_type, 
                fade_value=fade_value
            )
            logger.debug(
                f"Element '{element_key}' not found or load failed. Using default tone (duration: {default_duration_ms:.2f}ms)."
            )
        
        if segment:
            loaded_audio_segments[element_key] = segment
        return segment

    final_audio = AudioSegment.silent(duration=0)
    cursor = 0
    last_symbol_was_sound = False

    log_voice_name = voice_name_full if voice_name_full else "CW (default)"
    display_morse = morse_code
    display_input = f"'{input_text_for_log}' → " if input_text_for_log else ""

    logger.info(
        f"MORSE AUDIO: {display_input}'{display_morse}' → '{output_file}'\n"
        f"  ├─ Voice:   {log_voice_name}\n"
        f"  ├─ Speed:   {wpm} WPM (unit: {actual_unit_time_ms:.1f}ms)\n"
        f"  ├─ Pattern: {pattern_chance*100:.0f}% chance\n"
        f"  └─ Fade:    {fade_value}{'%' if fade_type == 'percentage' else 'ms'}"
    )
    
    _ = get_segment("dot", default_duration_ms=actual_unit_time_ms)
    _ = get_segment("dash", default_duration_ms=actual_unit_time_ms * 3)

    while cursor < len(morse_code):
        char_processed_in_iteration = False
        if voice_config and sorted_morse_sequences and random.random() < pattern_chance:
            for morse_seq_str in sorted_morse_sequences:
                if morse_code.startswith(morse_seq_str, cursor):
                    sequence_element_key = sequence_patterns_map[morse_seq_str]
                    logger.debug(
                        f"Pattern matched: '{morse_seq_str}' -> '{sequence_element_key}' at pos {cursor}"
                    )
                    pattern_audio = get_segment(sequence_element_key)
                    if pattern_audio:
                        final_audio += pattern_audio
                        logger.debug(
                            f"Appended pattern '{sequence_element_key}' ({len(pattern_audio)}ms). New audio len: {len(final_audio)}ms"
                        )
                        cursor += len(morse_seq_str)
                        char_processed_in_iteration = True
                        last_symbol_was_sound = True
                        break
            if char_processed_in_iteration:
                continue

        current_char = morse_code[cursor]
        
        appended_segment = None
        if current_char == '.':
            if last_symbol_was_sound: final_audio += AudioSegment.silent(duration=int(current_symbol_space_duration))
            appended_segment = get_segment("dot", default_duration_ms=actual_unit_time_ms)
            if appended_segment: final_audio += appended_segment
            last_symbol_was_sound = True
            cursor += 1
        elif current_char == '-':
            if last_symbol_was_sound: final_audio += AudioSegment.silent(duration=int(current_symbol_space_duration))
            appended_segment = get_segment("dash", default_duration_ms=actual_unit_time_ms * 3)
            if appended_segment: final_audio += appended_segment
            last_symbol_was_sound = True
            cursor += 1
        elif morse_code.startswith(" / ", cursor):
            final_audio += AudioSegment.silent(duration=int(current_word_space_duration))
            last_symbol_was_sound = False
            cursor += 3
        elif current_char == ' ':
            final_audio += AudioSegment.silent(duration=int(current_letter_space_duration))
            last_symbol_was_sound = False
            cursor += 1
        else:
            logger.warning(
                f"Unrecognized Morse char '{current_char}' at pos {cursor}. Skipping."
            )
            last_symbol_was_sound = False
            cursor += 1
        char_processed_in_iteration = True

        if not char_processed_in_iteration:
            logger.error("Morse processing loop error: No char processed. Breaking.") # Should not happen
            break

    # Create the output directory if needed (only for string file paths)
    if isinstance(output_file, str):
        output_dir = os.path.dirname(os.path.abspath(output_file))
        if not os.path.exists(output_dir) and output_dir: # Ensure output_dir is not empty string
            try:
                os.makedirs(output_dir)
                logger.debug(f"Created output directory: {output_dir}")
            except OSError as e:
                logger.error(f"Could not create output directory '{output_dir}': {e}")
                raise # Re-raise to stop execution if dir cannot be made
    
    try:
        if len(final_audio) == 0:
             logger.warning("Generated audio is empty. Creating 10ms silent file to prevent export errors.")
             final_audio = AudioSegment.silent(duration=10) 
        
        # If output_file is a string (path), log it. Otherwise, assume it's a file-like object (e.g. stdout.buffer)
        if isinstance(output_file, str):
            final_audio.export(output_file, format="wav")
            logger.info(f"Morse code audio saved to: {output_file}")
        else: # Assuming output_file is a file-like object for streaming
            # For file-like objects, ensure proper export handling
            try:
                final_audio.export(output_file, format="wav")
                # Try to flush the file-like object, if it supports flushing
                if hasattr(output_file, 'flush'):
                    output_file.flush()
                logger.info("Morse code audio streamed to output.")
            except (ValueError, IOError, AttributeError) as stream_err:
                # Catch specific errors that might occur with file-like objects
                logger.error(f"Error during audio streaming: {stream_err}")
                raise
            
    except Exception as e:
        # If it's a file path, include it in the error.
        err_msg = f"Error exporting audio to {output_file}: {e}" if isinstance(output_file, str) else f"Error streaming audio: {e}"
        logger.error(err_msg)
        raise

    return output_file # Returning the path or the file-like object


if __name__ == '__main__':
    # --- Basic logging setup for script execution ---
    # This will be overridden by a more sophisticated setup if this module
    # is imported and used by a CLI application.
    if not logging.getLogger().hasHandlers(): # Avoid adding multiple handlers if already configured
        logging.basicConfig(
            level=logging.DEBUG, # Show debug for direct script run
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    # --- End basic logging setup ---

    test_morse_sos = "... --- ..." 
    test_text_hello = "Hello"
    test_morse_hello_world = ".... . .-.. .-.. --- / .-- --- .-. .-.. -.." 

    logger.info("--- Synthesizer Self-Test Script START ---")
    
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("Testing synthesizer with default tones (percentage fade)...")
    generate_morse_audio(
        test_morse_sos, 
        os.path.join(output_dir, "default_sos_percentage_fade.wav"), 
        wpm=20, 
        fade_type="percentage", 
        fade_value=10, # 10%
        input_text_for_log="SOS"
    )
    
    logger.info("Testing synthesizer with default tones (absolute ms fade)...")
    generate_morse_audio(
        test_morse_hello_world, 
        os.path.join(output_dir, "default_hello_absolute_fade.wav"), 
        wpm=15, 
        fade_type="absolute", 
        fade_value=10, # 10ms
        input_text_for_log="HELLO WORLD"
    )

    # Setup a dummy voice for testing
    DUMMY_VOICE_NAME = "_synth_test_dummy"
    try:
        if voice_manager.generate_dummy_voice_samples(DUMMY_VOICE_NAME, overwrite=True):
            logger.info(f"Testing synthesizer with dummy voice: '{DUMMY_VOICE_NAME}'")
    
            dummy_voice_dir = voice_manager.get_voice_dir_path(DUMMY_VOICE_NAME)
            if dummy_voice_dir:
                dummy_config_path = os.path.join(
                    dummy_voice_dir, voice_manager.VOICE_CONFIG_FILENAME
                )
                with open(dummy_config_path, 'r+') as f:
                    config_data = json.load(f)
                    # Create a second dummy dot file (slightly different length for testing)
                    dot_var2_path = os.path.join(dummy_voice_dir, "dummy_dot_var2.wav")
                    # Make it non-silent for normalization test
                    AudioSegment.silent(duration=80).overlay(Sine(440).to_audio_segment(duration=80).apply_gain(-20)).export(dot_var2_path, format="wav")
                    
                    config_data["elements"]["dot"] = [
                        config_data["elements"]["dot"], # Keep original dummy_dot.wav
                        "dummy_dot_var2.wav",
                    ]
                    
                    # Add a sequence pattern for testing
                    # Use a real sound for custom_sos to test normalization and fade on patterns
                    custom_sos_sound_path = os.path.join(dummy_voice_dir, "custom_sos_sound.wav")
                    Sine(600).to_audio_segment(duration=500).apply_gain(-10).export(custom_sos_sound_path, format="wav")
                    config_data["elements"]["custom_sos_element"] = "custom_sos_sound.wav"
                    config_data["sequence_patterns"] = {"custom_sos_element": "... --- ..."}

                    f.seek(0)
                    json.dump(config_data, f, indent=2)
                    f.truncate()
                logger.info(f"Modified dummy voice config for '{DUMMY_VOICE_NAME}' with dot variants and SOS pattern.")

            generate_morse_audio(
                test_morse_sos, 
                os.path.join(output_dir, f"{DUMMY_VOICE_NAME}_sos_pattern_norm_fade.wav"), 
                voice_name_full=DUMMY_VOICE_NAME, 
                wpm=20, 
                pattern_chance=1.0,
                fade_type="percentage",
                fade_value=5,
                target_dbfs=-15,
                input_text_for_log="SOS (pattern)"
            )
            generate_morse_audio(
                test_morse_sos, 
                os.path.join(output_dir, f"{DUMMY_VOICE_NAME}_sos_nopattern_norm_fade.wav"), 
                voice_name_full=DUMMY_VOICE_NAME, 
                wpm=20, 
                pattern_chance=0.0,
                fade_type="absolute",
                fade_value=8,
                target_dbfs=-25,
                input_text_for_log="SOS (no pattern)"
            )
            generate_morse_audio(
                ". . .", # Morse for EEE
                os.path.join(output_dir,f"{DUMMY_VOICE_NAME}_dot_variants_norm_fade.wav"), 
                voice_name_full=DUMMY_VOICE_NAME, 
                wpm=20,
                input_text_for_log="EEE"
            )

            if dummy_voice_dir and os.path.isdir(dummy_voice_dir):
                shutil.rmtree(dummy_voice_dir)
                logger.info(f"Cleaned up dummy voice: {dummy_voice_dir}")
        else:
            logger.error(
                f"Could not create dummy voice '{DUMMY_VOICE_NAME}' for synthesizer test."
            )

    except ImportError:
        logger.warning(
            "Could not import voice_manager for full synthesizer test. Run from project root or ensure PYTHONPATH is set."
        )
    except Exception as e:
        logger.error(
            f"Error during synthesizer self-test with dummy voice: {e}", exc_info=True
        )

    logger.info("--- Synthesizer Self-Test Script FINISHED ---")
    logger.info(f"Test outputs are in '{os.path.abspath(output_dir)}'")
