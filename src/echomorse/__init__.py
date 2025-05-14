"""Echo-Morse: A Python tool for converting text to audible Morse code using various voices."""

__version__ = "0.8.3"

from .translator import translator
from .synthesizer import generate_morse_audio
# Uncomment when implemented
# from .interpreter import interpreter 

__all__ = ['translator', 'generate_morse_audio'] 