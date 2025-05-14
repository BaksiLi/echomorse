# Echo-Morse: Development Roadmap

This document outlines planned enhancements and future features for the Echo-Morse project.

## Core Features

- [x] **Text Conversion**: Convert between text and Morse code notation
- [x] **Audio Generation**: Create Morse code audio files from text input
- [ ] **Audio Decoding**: Implement robust audio-to-text conversion with noise tolerance
- [ ] **CW Keyer Interface**: Add support for using Echo-Morse as a hardware keyer via serial/USB
- [ ] **Web Interface**: Create a browser-based UI and REST API for remote operation

## Voice Synthesis System

- [x] **Custom Sound Elements**: Support for user-defined audio files for voice elements
- [x] **Natural Treatment** (?):
  - [x] Consistent audio levels
  - [x] Crossfades between elements for natural sound
  - [ ] Wave peak centre alignment for custom elements
- [x] **Randomization**: Add variability to timing and sounds for more natural output
- [ ] **Background Audio**: Add configurable static/noise for realistic CW training

## Amateur Radio Features

- [x] **CW Prosigns**: Support for common amateur radio prosigns (AR, SK, BT, etc.)
- [ ] **Farnsworth Timing**: Add option to separate character speed from word spacing
- [ ] **Code Variants**: Support for different Morse code standards (American Landline, Japanese, etc.)
- [ ] **QSO Templates**: Add pre-configured message templates for common QSO exchanges

## Performance & UI

- [ ] **Streaming Support**: Enable real-time audio streaming for longer messages
- [ ] **Containerization**: Create Docker container for easy deployment and consistency
- [ ] **Machine Learning**: Investigate AI approaches for adaptive Morse code recognition
- [ ] **Multiplatform Support**: Ensure full compatibility across Windows, macOS, and Linux