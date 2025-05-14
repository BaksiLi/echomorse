# Default Parameters for default voice
# Base unit is milliseconds for timing consistency across the codebase
DEFAULT_UNIT_DURATION_MS = 100  # Default base duration for a dot
SYMBOL_SPACE_UNITS = 1  # Space between dots and dashes within a letter
LETTER_SPACE_UNITS = 3  # Space between letters
WORD_SPACE_UNITS = 7    # Space between words
DEFAULT_WPM = 20        # Reference Words Per Minute for scaling

# Audio constants
SAMPLE_RATE = 44100     # Hz
CHANNELS = 1            # Mono audio (1 channel)
DEFAULT_TONE_FREQ = 800 # Hz - standard CW frequency

# For backwards compatibility - consider migrating to ms-based values
DOT_DURATION_SEC = DEFAULT_UNIT_DURATION_MS / 1000  # seconds
DASH_DURATION_SEC = DOT_DURATION_SEC * 3
INTRA_CHARACTER_SILENCE_SEC = DOT_DURATION_SEC
INTER_CHARACTER_SILENCE_SEC = DOT_DURATION_SEC * 3
WORD_SILENCE_SEC = DOT_DURATION_SEC * 7

# Legacy pitch values - consider migrating to DEFAULT_TONE_FREQ
DOT_PITCH = 440  # Hz (A4)
DASH_PITCH = 220  # Hz (A3)