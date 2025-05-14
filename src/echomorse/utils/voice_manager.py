"""Voice manager for the Echo-Morse application.

This module handles the management of different voice types for morse code audio,
including standard CW sounds, dog barks, bird chirps, train sounds, etc.
Voices are defined by a configuration file and associated audio samples.
"""
import os
import shutil
import logging
import json
from typing import Tuple, Optional, List, Dict
from pydub import AudioSegment
from ..config import SAMPLE_RATE, DEFAULT_UNIT_DURATION_MS

logger = logging.getLogger(__name__)

# Constants
# BASE_VOICES_DIR is now the 'audio' directory in the project root.
# Voice folders will be direct children, e.g., audio/my_voice/
BASE_VOICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio")
)
VOICE_CONFIG_FILENAME = "voice_config.json"
# VOICE_CATEGORIES is removed

# Ensure base directory exists (it should, but good practice)
os.makedirs(BASE_VOICES_DIR, exist_ok=True)


def get_voice_dir_path(voice_name: str) -> Optional[str]:
    """
    Gets the absolute path to a voice's directory.
    Voices are now top-level under BASE_VOICES_DIR.
    Returns None if the voice directory doesn't exist.
    """
    if not voice_name or "/" in voice_name or "\\" in voice_name:  # Basic validation
        logger.warning(
            f"Invalid voice name format: '{voice_name}'. Should not contain path separators."
        )
        return None
    path_try = os.path.join(BASE_VOICES_DIR, voice_name)
    if os.path.isdir(path_try):
        return path_try
    return None


def load_voice_config(voice_name: str) -> Optional[Dict]:
    """Loads the voice_config.json for a given voice."""
    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        # get_voice_dir_path or its callee logs the warning if name is invalid or dir not found
        return None

    config_path = os.path.join(voice_dir, VOICE_CONFIG_FILENAME)
    if not os.path.isfile(config_path):
        logger.warning(
            f"Voice config '{VOICE_CONFIG_FILENAME}' not found for voice '{voice_name}' in '{voice_dir}'."
        )
        return None

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        # Remove category from loaded config if it exists from old format (optional)
        # config.pop('category', None)
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from '{config_path}'. The file may be malformed. Details: {e}")
        # Explicitly state that the config is invalid and won't be used.
        # The calling function (e.g., in synthesizer) will then decide to use default tones.
        return None # Indicate that the config is invalid
    except Exception as e:
        logger.error(f"Error loading voice config '{config_path}': {e}")
        return None


def get_voice_element_samples(
    voice_name: str, element_keys: Dict[str, str] = {"dot": "dot", "dash": "dash"}
) -> Optional[Dict[str, AudioSegment]]:
    """
    Get specific audio samples (AudioSegment objects) for a voice based on element keys.

    Args:
        voice_name: Name of the voice (e.g., "dog1").
        element_keys: A dictionary mapping a logical name (e.g., "dot") to the key in voice_config.json's "elements" section.
                      Defaults to {"dot": "dot", "dash": "dash"}.

    Returns:
        A dictionary of logical names to AudioSegment objects (e.g., {"dot": <AudioSegment>, "dash": <AudioSegment>})
        or None if essential samples cannot be loaded.
    """
    if not voice_name:
        return None

    voice_config = load_voice_config(voice_name)
    if not voice_config:
        return None

    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        logger.error(
            f"Voice directory for '{voice_name}' became unavailable after config load."
        )  # Should not happen
        return None

    loaded_elements: Dict[str, AudioSegment] = {}
    elements_map = voice_config.get("elements")
    if not elements_map or not isinstance(elements_map, dict):
        logger.warning(
            f"No 'elements' map found or is invalid in config for voice '{voice_name}'."
        )
        return None

    for logical_name, config_key in element_keys.items():
        sample_filename = elements_map.get(config_key)
        if not sample_filename:
            logger.warning(
                f"Element key '{config_key}' (for logical '{logical_name}') not found in voice config for '{voice_name}'."
            )
            continue

        sample_path = os.path.join(voice_dir, sample_filename)
        if not os.path.isfile(sample_path):
            logger.warning(
                f"Audio file '{sample_filename}' for element '{config_key}' not found for voice '{voice_name}' at '{sample_path}'."
            )
            continue

        try:
            segment = AudioSegment.from_file(sample_path)
            loaded_elements[logical_name] = segment
        except Exception as e:
            logger.error(
                f"Error loading audio file '{sample_path}' for voice '{voice_name}': {e}"
            )

    if not loaded_elements:
        logger.warning(
            f"No audio elements could be loaded for voice '{voice_name}' with requested keys."
        )
        return None

    return loaded_elements


def _is_valid_voice_dir(dir_path: str) -> bool:
    """Checks if a directory represents a valid voice (contains voice_config.json)."""
    config_path = os.path.join(dir_path, VOICE_CONFIG_FILENAME)
    return os.path.isfile(config_path)


def list_available_voices() -> List[str]:
    """List all available voices including the built-in 'telegraph' default."""
    voices = ["CW (built-in)"]  # Default sine wave voice always listed first

    if os.path.exists(BASE_VOICES_DIR) and os.path.isdir(BASE_VOICES_DIR):
        for entry_name in os.listdir(BASE_VOICES_DIR):
            potential_voice_path = os.path.join(BASE_VOICES_DIR, entry_name)
            if os.path.isdir(potential_voice_path) and not entry_name.startswith("."):
                if _is_valid_voice_dir(potential_voice_path):
                    voices.append(entry_name)
    return voices


def create_voice_from_audio_files(
    voice_name: str,
    dot_file_src: str,
    dash_file_src: str,
    # category parameter removed
    description: Optional[str] = None,
    overwrite: bool = False,
) -> bool:
    """
    Creates a new voice structure from existing dot and dash audio files.
    It will create the voice directory (e.g., audio/<voice_name>/) and a voice_config.json.
    This function is no longer exposed via CLI but can be used internally or for testing.
    """
    if not voice_name or "/" in voice_name or "\\" in voice_name:  # Basic validation
        logger.error(
            f"Invalid voice name: '{voice_name}'. Cannot contain path separators."
        )
        return False

    voice_target_dir = os.path.join(BASE_VOICES_DIR, voice_name)

    if os.path.exists(voice_target_dir) and not overwrite:
        logger.error(
            f"Voice directory '{voice_target_dir}' already exists. Use overwrite=True or choose a different name."
        )
        return False

    try:
        os.makedirs(voice_target_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create directory '{voice_target_dir}': {e}")
        return False

    dot_sample_filename = "dot_default.wav"  # Standardized name within the voice folder
    dash_sample_filename = "dash_default.wav"

    dot_target_path = os.path.join(voice_target_dir, dot_sample_filename)
    dash_target_path = os.path.join(voice_target_dir, dash_sample_filename)

    try:
        if not os.path.isfile(dot_file_src):
            logger.error(f"Source dot file not found: {dot_file_src}")
            if overwrite and os.path.isdir(voice_target_dir):
                shutil.rmtree(voice_target_dir)  # Clean up on error if overwriting
            elif os.path.isdir(voice_target_dir) and not os.listdir(voice_target_dir):
                shutil.rmtree(voice_target_dir)
            return False
        dot_audio = AudioSegment.from_file(dot_file_src)
        dot_audio.export(dot_target_path, format="wav")

        if not os.path.isfile(dash_file_src):
            logger.error(f"Source dash file not found: {dash_file_src}")
            if overwrite and os.path.isdir(voice_target_dir):
                shutil.rmtree(voice_target_dir)
            elif os.path.isdir(voice_target_dir) and not os.listdir(voice_target_dir):
                shutil.rmtree(voice_target_dir)
            return False
        dash_audio = AudioSegment.from_file(dash_file_src)
        dash_audio.export(dash_target_path, format="wav")

    except Exception as e:
        logger.error(
            f"Error processing source audio files for voice '{voice_name}': {e}"
        )
        if overwrite and os.path.isdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        elif os.path.isdir(voice_target_dir) and not os.listdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        return False

    config_data = {
        "name": voice_name,
        "description": description
        if description
        else f"Voice '{voice_name}' created from external audio files.",
        # "category": category, # Removed category
        "elements": {
            "dot": dot_sample_filename,
            "dash": dash_sample_filename,
            # User can manually add more elements like "000": "pattern_000.wav" here
        },
        "metadata": {},
    }
    config_file_path = os.path.join(voice_target_dir, VOICE_CONFIG_FILENAME)
    try:
        with open(config_file_path, "w") as f:
            json.dump(config_data, f, indent=2)
        logger.info(
            f"Voice '{voice_name}' created successfully at '{voice_target_dir}'."
        )
        return True
    except Exception as e:
        logger.error(f"Error writing voice config file '{config_file_path}': {e}")
        # Attempt to clean up the directory if config writing fails
        if overwrite and os.path.isdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        elif os.path.isdir(voice_target_dir) and not os.listdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        return False


def generate_dummy_voice_samples(
    voice_name: str,
    # category parameter removed
    overwrite: bool = False,
    # api_key parameter was already not used effectively, removing for clarity
) -> bool:
    """
    Generates placeholder DUMMY (silent) voice samples and voice_config.json directly in audio/<voice_name>/.
    This is primarily for testing or bootstrapping a voice structure.
    """
    if not voice_name or "/" in voice_name or "\\" in voice_name:
        logger.error(f"Invalid voice name for dummy: '{voice_name}'.")
        return False

    voice_target_dir = os.path.join(BASE_VOICES_DIR, voice_name)
    if os.path.exists(voice_target_dir) and not overwrite:
        logger.error(
            f"Dummy voice directory '{voice_target_dir}' already exists. Use overwrite=True."
        )
        return False

    os.makedirs(voice_target_dir, exist_ok=True)

    dot_sample_filename = "dummy_dot.wav"
    dash_sample_filename = "dummy_dash.wav"
    dot_path = os.path.join(voice_target_dir, dot_sample_filename)
    dash_path = os.path.join(voice_target_dir, dash_sample_filename)

    try:
        dot_dummy = AudioSegment.silent(duration=DEFAULT_UNIT_DURATION_MS)
        dot_dummy.export(dot_path, format="wav")
        dash_dummy = AudioSegment.silent(duration=DEFAULT_UNIT_DURATION_MS * 3)
        dash_dummy.export(dash_path, format="wav")
    except Exception as e:
        logger.error(f"Error generating dummy audio files for '{voice_name}': {e}")
        if os.path.isdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        return False

    config_data = {
        "name": f"{voice_name} (Dummy)",
        "description": "Dummy voice with silent samples, generated for testing.",
        # "category": category, # Removed
        "elements": {"dot": dot_sample_filename, "dash": dash_sample_filename},
        "metadata": {"generator": "dummy_generator"},
    }
    config_file_path = os.path.join(voice_target_dir, VOICE_CONFIG_FILENAME)
    try:
        with open(config_file_path, "w") as f:
            json.dump(config_data, f, indent=2)
        logger.info(
            f"Dummy voice '{voice_name}' created successfully in '{voice_target_dir}'."
        )
        return True
    except Exception as e:
        logger.error(f"Error writing voice config for dummy voice '{voice_name}': {e}")
        if os.path.isdir(voice_target_dir):
            shutil.rmtree(voice_target_dir)
        return False


def get_voice_info(voice_name: str) -> Dict:
    """
    Get detailed information about a voice, including description and audio file count.
    Returns a dictionary with: name, description, audio_count, and has_patterns.
    """
    info = {
        "name": voice_name,
        "description": "",
        "audio_count": 0,
        "has_patterns": False,
    }

    # Special case for the default CW voice
    if voice_name == "CW (built-in)":
        info["description"] = "Sine wave tones for standard Morse code"
        info["audio_count"] = 0  # No audio files needed
        return info

    # For custom voices, check their config and directory
    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        return info

    # Count audio files
    audio_files = 0
    for file in os.listdir(voice_dir):
        if file.lower().endswith((".wav", ".mp3", ".ogg")):
            audio_files += 1
    info["audio_count"] = audio_files

    # Get description and pattern info from config
    config = load_voice_config(voice_name)
    if config:
        if "description" in config and config["description"]:
            info["description"] = config["description"]

        # Check if the voice has custom patterns
        patterns = config.get("sequence_patterns", {})
        info["has_patterns"] = len(patterns) > 0

    return info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing voice manager (simplified design - no categories)...")

    DUMMY_VOICE_NAME = "_test_dummy_voice"
    # Ensure the dummy voice directory is clean before test
    temp_dummy_voice_path = os.path.join(BASE_VOICES_DIR, DUMMY_VOICE_NAME)
    if os.path.isdir(temp_dummy_voice_path):
        shutil.rmtree(temp_dummy_voice_path)

    success = generate_dummy_voice_samples(DUMMY_VOICE_NAME, overwrite=True)
    assert success, f"Failed to create dummy voice {DUMMY_VOICE_NAME}"

    available = list_available_voices()
    logger.info(f"Available voices: {available}")
    assert (
        DUMMY_VOICE_NAME in available
    ), f"Dummy voice {DUMMY_VOICE_NAME} not in {available}"

    logger.info(f"Loading default dot/dash for '{DUMMY_VOICE_NAME}'")
    samples = get_voice_element_samples(DUMMY_VOICE_NAME)
    assert samples, f"Could not load samples for dummy voice {DUMMY_VOICE_NAME}"
    assert "dot" in samples and isinstance(samples["dot"], AudioSegment)
    assert "dash" in samples and isinstance(samples["dash"], AudioSegment)
    logger.info(f"Successfully loaded {len(samples)} samples for '{DUMMY_VOICE_NAME}'.")

    # Test creating a voice from the dummy files just created (as an example source)
    # This create_voice_from_audio_files is no longer CLI but can be used programmatically.
    dummy_dot_src = os.path.join(temp_dummy_voice_path, "dummy_dot.wav")
    dummy_dash_src = os.path.join(temp_dummy_voice_path, "dummy_dash.wav")

    EXT_VOICE_NAME = "_test_from_files_voice"
    ext_voice_target_dir = os.path.join(BASE_VOICES_DIR, EXT_VOICE_NAME)
    if os.path.isdir(ext_voice_target_dir):
        shutil.rmtree(ext_voice_target_dir)  # Clean before test

    if os.path.isfile(dummy_dot_src) and os.path.isfile(dummy_dash_src):
        created_ext = create_voice_from_audio_files(
            EXT_VOICE_NAME,
            dot_file_src=dummy_dot_src,
            dash_file_src=dummy_dash_src,
            description="Test voice created from other dummy files.",
            overwrite=True,
        )
        assert (
            created_ext
        ), f"Failed to create voice {EXT_VOICE_NAME} from existing files."
        available_after_create = list_available_voices()
        logger.info(f"Available voices after create: {available_after_create}")
        assert EXT_VOICE_NAME in available_after_create

        ext_samples = get_voice_element_samples(EXT_VOICE_NAME)
        assert ext_samples and "dot" in ext_samples and "dash" in ext_samples
        logger.info(
            f"Successfully loaded samples for externally created voice '{EXT_VOICE_NAME}'."
        )

        # Clean up the externally created voice
        if os.path.isdir(ext_voice_target_dir):
            shutil.rmtree(ext_voice_target_dir)
            logger.info(f"Cleaned up externally created voice: {ext_voice_target_dir}")
        else:
            logger.warning(
                "Source dummy files for create_voice_from_audio_files test not found. Skipping part of test."
            )

    # Clean up the main dummy voice directory
    if os.path.isdir(temp_dummy_voice_path):
        shutil.rmtree(temp_dummy_voice_path)
        logger.info(f"Cleaned up main dummy voice: {temp_dummy_voice_path}")

    logger.info("Voice manager test complete.")
