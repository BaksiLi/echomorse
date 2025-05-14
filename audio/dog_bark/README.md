# Dog Bark Voice

This is the default example voice for Echo-Morse that uses dog barks for Morse code.

## Included Sounds

- `dot.wav` - Short dog bark for dots (.)
- `dash.wav` - Longer dog bark for dashes (-)
- `triple_dot.wav` - Three quick barks used for the letter S (...)

## How to Use

```bash
# Generate Morse code with dog barks
pdm run text-to-morse-audio "HELLO WORLD" --voice dog_bark

# Use a different speed (WPM)
pdm run text-to-morse-audio "CQ CQ DE KI5ABC" --voice dog_bark --wpm 15
```

## Extending This Voice

You can add more pattern sounds to make the voice more expressive:

1. Record or find audio files for common patterns (e.g., "CQ", "SOS", etc.)
2. Add the audio files to this directory
3. Update `voice_config.json` to include:
   - New entries in the `elements` section mapping names to audio files
   - New entries in the `sequence_patterns` section mapping Morse patterns to element names

### Example Extension

To add a special sound for the CQ call:

1. Add `cq_call.wav` to this directory
2. Update `voice_config.json`:

```json
{
  "name": "dog_bark",
  "description": "Dog bark sounds for Morse code - a fun default voice",
  "elements": {
    "dot": "dot.wav",
    "dash": "dash.wav",
    "triple_dot": "triple_dot.wav",
    "cq": "cq_call.wav"
  },
  "sequence_patterns": {
    "triple_dot": "...",
    "cq": "-.-. --.-"
  }
}
```

## Timing

The duration of the dot sound determines the base timing unit for the voice. All other timing (spaces between elements, letters, and words) is calculated as multiples of this unit according to standard Morse code timing. 