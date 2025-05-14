import pytest
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from echomorse.translator import translator


class TestTranslator:
    def test_text_to_morse(self):
        """Test converting text to morse code."""
        # Test basic alphabets
        assert translator.text_to_morse("HELLO") == ".... . .-.. .-.. ---"
        assert translator.text_to_morse("SOS") == "... --- ..."

        # Test case insensitivity
        assert translator.text_to_morse("hello") == ".... . .-.. .-.. ---"

        # Test numbers
        assert translator.text_to_morse("123") == ".---- ..--- ...--"

        # Test punctuation
        assert translator.text_to_morse("Hi!") == ".... .. -.-.--"

        # Test mixed content
        assert (
            translator.text_to_morse("Hello, World!")
            == ".... . .-.. .-.. --- --..-- / .-- --- .-. .-.. -.. -.-.--"
        )

        # Test empty string
        assert translator.text_to_morse("") == ""

        # Test spaces
        assert translator.text_to_morse("A B") == ".- / -..."

        # Test multiple spaces
        assert translator.text_to_morse("A  B") == ".- / -..."
        assert translator.text_to_morse("A   B") == ".- / -..."

    def test_morse_to_text(self):
        """Test converting morse code to text."""
        # Test basic alphabets
        assert translator.morse_to_text(".... . .-.. .-.. ---") == "HELLO"
        assert translator.morse_to_text("... --- ...") == "SOS"

        # Test numbers
        assert translator.morse_to_text(".---- ..--- ...--") == "123"

        # Test punctuation
        assert translator.morse_to_text(".... .. -.-.--") == "HI!"

        # Test mixed content
        assert (
            translator.morse_to_text(
                ".... . .-.. .-.. --- --..-- / .-- --- .-. .-.. -.. -.-.--"
            )
            == "HELLO, WORLD!"
        )

        # Test empty string
        assert translator.morse_to_text("") == ""

        # Test invalid morse code handling (an example of what it WON'T translate if not in dict)
        assert (
            translator.morse_to_text("...... . .-.. .-.. ---") != "HELLO"
        )  # Invalid morse for 'H'

        # Test extra spaces in morse code input (should be forgiving)
        assert translator.morse_to_text("....  .  .-..  .-..  ---") == "HELLO"

        # Test leading/trailing spaces
        assert translator.morse_to_text("   .... . .-.. .-.. ---   ") == "HELLO"

    def test_roundtrip(self):
        """Test text->morse->text roundtrip.

        Ensures that translating text to morse and back results in the original text.
        This verifies the consistency of both translation functions.
        """
        original_texts = [
            "HELLO WORLD",
            "SOS",
            "123",
            "TESTING 1, 2, 3!",
            "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
            "HELLO, WORLD!",
            "A B C",
            # Test with prosigns
            "<AR> TEST",
            "TEST <SK>",
            "BEFORE <BT> AFTER",
            # Test with callsigns
            "CQ DE BY1QH",
            "BY1QH DE W1AW <KN>",
        ]

        for text in original_texts:
            morse = translator.text_to_morse(text)
            decoded = translator.morse_to_text(morse)
            assert decoded == text.upper(), f"Roundtrip failed for '{text}'"

    def test_cw_prosigns(self):
        """Test CW prosigns and common ham radio phrases.

        Validates both text-to-morse and morse-to-text for various CW operating
        procedures, prosigns, and conventional amateur radio exchanges.
        """
        # Test prosigns
        assert translator.text_to_morse("<AR>") == ".-.-."
        assert translator.text_to_morse("<SK>") == "...-.-"
        assert translator.text_to_morse("<BT>") == "-...-"
        assert translator.text_to_morse("<KN>") == "-.-.-"
        assert translator.text_to_morse("<AS>") == ".-..."

        # Test reverse lookup of prosigns
        assert translator.morse_to_text(".-.-.") == "<AR>"
        assert translator.morse_to_text("...-.-") == "<SK>"
        assert translator.morse_to_text("-...-") == "<BT>"
        assert translator.morse_to_text("-.-.-") == "<KN>"
        assert translator.morse_to_text(".-...") == "<AS>"

        # Test common CW abbreviations
        assert translator.text_to_morse("CQ") == "-.-. --.-"
        assert translator.text_to_morse("DE") == "-.. ."
        assert translator.text_to_morse("K") == "-.-"

        # Test full ham radio phrases
        assert (
            translator.text_to_morse("CQ CQ CQ DE W1AW W1AW K")
            == "-.-. --.- / -.-. --.- / -.-. --.- / -.. . / .-- .---- .- .-- / .-- .---- .- .-- / -.-"
        )
        assert (
            translator.text_to_morse("W1AW DE BY1QH BY1QH <KN>")
            == ".-- .---- .- .-- / -.. . / -... -.-- .---- --.- .... / -... -.-- .---- --.- .... / -.-.-"
        )
        assert translator.text_to_morse("73 <SK>") == "--... ...-- / ...-.-"

        # Test prosigns embedded within words or phrases
        msg_with_prosign = "BREAK<BT>HERE"
        morse_with_prosign = translator.text_to_morse(msg_with_prosign)
        assert morse_with_prosign == "-... .-. . .- -.- -...- .... . .-. ."

        # Test with spaces properly formatted
        proper_msg = "BREAK <BT> HERE"
        proper_morse = translator.text_to_morse(proper_msg)
        assert proper_morse == "-... .-. . .- -.- / -...- / .... . .-. ."
        assert translator.morse_to_text(proper_morse) == proper_msg

        # Test multiple prosigns in a message
        complex_msg = "TESTING <AS> WAIT <BT> CONTINUE <AR>"
        morse_complex = translator.text_to_morse(complex_msg)
        decoded = translator.morse_to_text(morse_complex)
        assert decoded == complex_msg

    def test_error_handling(self):
        """Test error handling for various edge cases."""
        # Test with non-morse characters
        assert translator.text_to_morse("αβγ") == ""  # Greek letters not in morse dict

        # Test with mix of valid and invalid chars (output depends on spacing behavior)
        special_chars_result = translator.text_to_morse("A%B@C")
        assert ".-" in special_chars_result  # A should be present
        assert "-..." in special_chars_result  # B should be present
        assert "-.-." in special_chars_result  # C should be present

        # Test with extreme input
        assert (
            translator.text_to_morse("A" * 1000).count(".") > 0
        )  # Should handle long inputs

        # Test with invalid prosigns
        assert "<XZ>" not in translator.morse_to_text(
            translator.text_to_morse("<XZ>")
        )  # Not a valid prosign
