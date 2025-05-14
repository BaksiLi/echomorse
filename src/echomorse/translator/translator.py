import re
from typing import Dict, Tuple

# Define marker to identify prosigns in internal processing
PROSIGN_PREFIX = "_PROSIGN_"

# Main Morse code dictionary with all characters and prosigns
MORSE_CODE_DICT = {
    # Standard alphabet
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    
    # Numbers
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "0": "-----",
    
    # Punctuation
    ",": "--..--",
    ".": ".-.-.-",
    "?": "..--..",
    "/": "-..-.",
    "-": "-....-",
    "(": "-.--.",
    ")": "-.--.-",
    "!": "-.-.--",
    " ": "/",
    
    # CW Prosigns (using PROSIGN_PREFIX internally)
    f"{PROSIGN_PREFIX}AR": ".-.-.",  # End of message
    f"{PROSIGN_PREFIX}SK": "...-.-", # End of contact/Silent Key
    f"{PROSIGN_PREFIX}KN": "-.-.-",  # Go ahead, specific station only
    f"{PROSIGN_PREFIX}BT": "-...-",  # Break/pause (also used as "=")
    f"{PROSIGN_PREFIX}AS": ".-...",  # Wait/Stand by
    
    # Common CW procedural signals
    "CQ": "-.-. --.-",  # Calling any station
    "DE": "-.. .",      # From (used between callsigns)
    "K": "-.-",         # Invitation to transmit
}

# Create reverse lookup dictionary
REVERSE_MORSE_CODE_DICT = {morse: char for char, morse in MORSE_CODE_DICT.items()}
# Special handling for reverse lookup of word separator if it's not ambiguous
REVERSE_MORSE_CODE_DICT["/"] = " "

def text_to_morse(text: str) -> str:
    """Converts a text string to Morse code.

    Args:
        text: The input string.

    Returns:
        A string representing the Morse code. Characters are separated by a single space,
        and words are separated by a slash surrounded by spaces (" / ").
    """
    if not text:
        return ""
    
    # Convert to uppercase
    text = text.upper()
    
    # Special case for exact prosign matches
    for prosign in ["AR", "SK", "KN", "BT", "AS"]:
        if text == f"<{prosign}>":
            return MORSE_CODE_DICT.get(f"{PROSIGN_PREFIX}{prosign}", "")
    
    # Process text with prosigns embedded
    result = []
    words = text.split()
    
    for word in words:
        morse_chars_for_word = []
        i = 0
        while i < len(word):
            # Check if this position starts a prosign
            is_prosign = False
            if i <= len(word) - 4 and word[i] == '<' and word[i+3] == '>' and word[i+1:i+3] in ["AR", "SK", "KN", "BT", "AS"]:
                prosign = word[i+1:i+3]
                morse_chars_for_word.append(MORSE_CODE_DICT[f"{PROSIGN_PREFIX}{prosign}"])
                i += 4
                is_prosign = True
            
            # Standard character processing
            if not is_prosign and i < len(word):
                if word[i] in MORSE_CODE_DICT:
                    morse_chars_for_word.append(MORSE_CODE_DICT[word[i]])
                i += 1
                
        if morse_chars_for_word:
            result.append(" ".join(morse_chars_for_word))
    
    return " / ".join(result)

def morse_to_text(morse_code: str) -> str:
    """Converts a Morse code string back to text.

    Args:
        morse_code: The Morse code string. Assumes characters are separated by a single space
                    and words by ' / '.

    Returns:
        The decoded text string.
    """
    if not morse_code:
        return ""
        
    # Special case for exact prosign matches
    for prefix_key, morse_value in MORSE_CODE_DICT.items():
        if morse_code == morse_value and prefix_key.startswith(PROSIGN_PREFIX):
            prosign = prefix_key.replace(PROSIGN_PREFIX, "")
            return f"<{prosign}>"
    
    text_string_parts = []
    morse_words = morse_code.strip().split(" / ")

    for morse_word_segment in morse_words:
        if not morse_word_segment:
            continue
            
        decoded_chars_for_word = []
        morse_chars_in_word = morse_word_segment.split(" ")
        
        for single_morse_char in morse_chars_in_word:
            if not single_morse_char:
                continue
                
            if single_morse_char in REVERSE_MORSE_CODE_DICT:
                char = REVERSE_MORSE_CODE_DICT[single_morse_char]
                
                # Check if this is a prosign and format it appropriately
                if char.startswith(PROSIGN_PREFIX):
                    prosign = char.replace(PROSIGN_PREFIX, "")
                    char = f"<{prosign}>"
                
                decoded_chars_for_word.append(char)
        
        if decoded_chars_for_word:
            word = "".join(decoded_chars_for_word)
            text_string_parts.append(word)

    return " ".join(text_string_parts)

if __name__ == "__main__":
    # Test cases
    test_text = "Hello World 123 ! Test"
    print(f"Original: '{test_text}'")

    morse = text_to_morse(test_text)
    print(f"Morse: '{morse}'") # Expected: ".... . .-.. .-.. --- / .-- --- .-. .-.. -.. / .---- ..--- ...-- / -.-.-- / - . ... -"

    decoded_text = morse_to_text(morse)
    print(f"Decoded: '{decoded_text}'")

    test_text_2 = "SOS"
    print(f"Original: '{test_text_2}'")
    morse_2 = text_to_morse(test_text_2)
    print(f"Morse: '{morse_2}'") # Expected: "... --- ..."
    decoded_text_2 = morse_to_text(morse_2)
    print(f"Decoded: '{decoded_text_2}'")

    test_text_3 = "  Multiple   spaces  "
    print(f"Original: '{test_text_3}'")
    morse_3 = text_to_morse(test_text_3)
    # Expected: '-- ..- .-.. - .. .--. .-.. . / ... .--. .- -.-. . ...' (MULTIPLE / SPACES)
    print(f"Morse: '{morse_3}'") 
    decoded_text_3 = morse_to_text(morse_3)
    print(f"Decoded: '{decoded_text_3}'")

    print(f"Original: ''")
    morse_empty = text_to_morse("")
    print(f"Morse: '{morse_empty}'")
    decoded_empty = morse_to_text(morse_empty)
    print(f"Decoded: '{decoded_empty}'")

    # Test morse with leading/trailing/multiple separators
    morse_tricky = " / .... . .-.. .-.. --- / / .-- --- .-. .-.. -.. / "
    print(f"Original Morse: '{morse_tricky}'")
    decoded_tricky = morse_to_text(morse_tricky) # Expected: "HELLO WORLD"
    print(f"Decoded: '{decoded_tricky}'")
    
    # Test unspaced morse (Note: current morse_to_text is not designed for this without explicit char separators)
    unspaced_morse = "...---..." # SOS
    print(f"Original Unspaced Morse: '{unspaced_morse}'")
    decoded_unspaced = morse_to_text(unspaced_morse) # Will likely be empty or map to a single char if "...---..." is in dict
    print(f"Decoded Unspaced: '{decoded_unspaced}' (Expected to fail or be empty with current spaced logic)")

    # Test "A B"
    ab_text = "A B"
    print(f"Original: '{ab_text}'")
    ab_morse = text_to_morse(ab_text)
    print(f"Morse: '{ab_morse}'") # Expected: ".- / -..."
    ab_decoded = morse_to_text(ab_morse)
    print(f"Decoded: '{ab_decoded}'")

    # Test "Hello, World!"
    hwp_text = "Hello, World!"
    print(f"Original: '{hwp_text}'")
    hwp_morse = text_to_morse(hwp_text)
    print(f"Morse: '{hwp_morse}'") # Expected: ".... . .-.. .-.. --- --..-- / .-- --- .-. .-.. -.. -.-.--"
    hwp_decoded = morse_to_text(hwp_morse)
    print(f"Decoded: '{hwp_decoded}'")
