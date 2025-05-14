"""Voice manager for the Echo-Morse application.

This module handles the management of different voice types for morse code audio.
Voices are defined by a configuration file and associated audio samples.
"""
import os
import shutil
import logging
import json
import sys
import appdirs
from typing import Tuple, Optional, List, Dict, Union
from pydub import AudioSegment
from ..config import SAMPLE_RATE, DEFAULT_UNIT_DURATION_MS

logger = logging.getLogger(__name__)

# Define voice directories in priority order
VOICE_CONFIG_FILENAME = "voice_config.json"

# Primary directory: Package's audio directory (for included voices)
PACKAGE_AUDIO_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "audio")
)

# User directory: OS-specific user data directory
USER_DATA_DIR = appdirs.user_data_dir("echomorse", "echomorse")
USER_AUDIO_DIR = os.path.join(USER_DATA_DIR, "audio")

# Ensure user directory exists
os.makedirs(USER_AUDIO_DIR, exist_ok=True)

# Voice directories in priority order (user dir first for overrides)
VOICE_DIRS = [USER_AUDIO_DIR, PACKAGE_AUDIO_DIR]


def get_voice_dir_path(voice_name: str) -> Optional[str]:
    """
    Gets the absolute path to a voice's directory.
    Searches both user and package directories.
    """
    if not voice_name or "/" in voice_name or "\\" in voice_name:
        return None
    
    # Search in order of priority
    for base_dir in VOICE_DIRS:
        path = os.path.join(base_dir, voice_name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, VOICE_CONFIG_FILENAME)):
            return path
    
    return None


def load_voice_config(voice_name: str) -> Optional[Dict]:
    """Loads the voice_config.json for a given voice."""
    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        return None

    config_path = os.path.join(voice_dir, VOICE_CONFIG_FILENAME)
    if not os.path.isfile(config_path):
        logger.warning(f"Voice config not found for voice '{voice_name}'")
        return None

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading voice config: {e}")
        return None


def get_voice_element_samples(
    voice_name: str, element_keys: Dict[str, str] = {"dot": "dot", "dash": "dash"}
) -> Optional[Dict[str, AudioSegment]]:
    """Get audio samples for a voice."""
    if not voice_name:
        return None

    voice_config = load_voice_config(voice_name)
    if not voice_config:
        return None

    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        return None

    loaded_elements: Dict[str, AudioSegment] = {}
    elements_map = voice_config.get("elements")
    if not elements_map or not isinstance(elements_map, dict):
        logger.warning(f"No 'elements' map in voice config for '{voice_name}'")
        return None

    for logical_name, config_key in element_keys.items():
        sample_filename = elements_map.get(config_key)
        if not sample_filename:
            continue

        sample_path = os.path.join(voice_dir, sample_filename)
        if not os.path.isfile(sample_path):
            continue

        try:
            segment = AudioSegment.from_file(sample_path)
            loaded_elements[logical_name] = segment
        except Exception as e:
            logger.error(f"Error loading audio file: {e}")

    return loaded_elements if loaded_elements else None


def _is_valid_voice_dir(dir_path: str) -> bool:
    """Checks if a directory contains a valid voice configuration."""
    config_path = os.path.join(dir_path, VOICE_CONFIG_FILENAME)
    return os.path.isfile(config_path)


def list_available_voices() -> List[str]:
    """List all available voices."""
    voices = ["CW (built-in)"]  # Default sine wave voice
    
    # Check all voice directories
    for base_dir in VOICE_DIRS:
        if os.path.isdir(base_dir):
            for entry_name in os.listdir(base_dir):
                entry_path = os.path.join(base_dir, entry_name)
                if (os.path.isdir(entry_path) and 
                    not entry_name.startswith(".") and
                    _is_valid_voice_dir(entry_path) and 
                    entry_name not in voices):
                    voices.append(entry_name)
    
    return voices


def install_voice(voice_name: str) -> bool:
    """
    Install a voice from the package to the user directory.
    Used for built-in voices like dog_bark.
    """
    if voice_name not in list_available_voices():
        logger.error(f"Voice '{voice_name}' not found")
        return False
    
    # Skip if already in user directory
    user_voice_path = os.path.join(USER_AUDIO_DIR, voice_name)
    if os.path.isdir(user_voice_path):
        return True
    
    # Find the voice in package directory
    package_voice_path = os.path.join(PACKAGE_AUDIO_DIR, voice_name)
    if not os.path.isdir(package_voice_path):
        logger.error(f"Built-in voice '{voice_name}' not found in package")
        return False
    
    # Copy the voice files
    try:
        shutil.copytree(package_voice_path, user_voice_path)
        logger.info(f"Installed voice '{voice_name}' to {user_voice_path}")
        return True
    except Exception as e:
        logger.error(f"Error installing voice: {e}")
        return False


def get_voice_info(voice_name: str) -> Dict:
    """Get information about a voice."""
    info = {
        "name": voice_name,
        "description": "",
        "audio_count": 0,
        "has_patterns": False,
        "location": "",
    }

    # Special case for the default CW voice
    if voice_name == "CW (built-in)":
        info["description"] = "Sine wave tones for standard Morse code"
        info["location"] = "built-in"
        return info

    # For custom voices, check their config and directory
    voice_dir = get_voice_dir_path(voice_name)
    if not voice_dir:
        return info
    
    info["location"] = voice_dir

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


def print_voice_help():
    """Print help information about voices."""
    logger.info("Voice Directories:")
    for i, dir_path in enumerate(VOICE_DIRS, 1):
        exists = "✓" if os.path.isdir(dir_path) else "✗"
        logger.info(f"{i}. {dir_path} ({exists})")

    logger.info("\nAvailable Voices:")
    for voice in list_available_voices():
        info = get_voice_info(voice)
        logger.info(f"- {voice}: {info['description']}")
