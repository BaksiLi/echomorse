import pytest
import os
import sys
import tempfile
import shutil
import random  # Ensure random is imported for mocking its methods
import json  # For creating dummy voice_config.json if needed by voice_manager mocks
from unittest.mock import patch, MagicMock, call

# Add src directory to path
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, SRC_DIR)

from echomorse.synthesizer import synthesizer  # This is the module under test
from echomorse.utils import voice_manager  # To mock its functions
from pydub import AudioSegment

# Morse timing constants from synthesizer to verify calculated durations
DEFAULT_UNIT_DURATION_MS = synthesizer.DEFAULT_UNIT_DURATION_MS
SYMBOL_SPACE_UNITS = synthesizer.SYMBOL_SPACE_UNITS
LETTER_SPACE_UNITS = synthesizer.LETTER_SPACE_UNITS
WORD_SPACE_UNITS = synthesizer.WORD_SPACE_UNITS
DEFAULT_WPM = synthesizer.DEFAULT_WPM


@pytest.fixture
def test_output_file():
    """Fixture for test output file."""
    # Use tempfile for the output to avoid clutter and ensure cleanup
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)  # Close the file descriptor immediately
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_voice_pack_dir():
    """Creates a temporary directory for a voice pack and cleans up afterward."""
    path = tempfile.mkdtemp(prefix="echomorse_test_voice_")
    yield path
    shutil.rmtree(path)


@pytest.fixture
def dummy_audio_file_creator(temp_voice_pack_dir):
    """Fixture to create a dummy WAV file in the temp_voice_pack_dir."""

    def _creator(filename: str, duration_ms: int = 100) -> str:
        filepath = os.path.join(temp_voice_pack_dir, filename)
        AudioSegment.silent(duration=duration_ms).export(filepath, format="wav")
        return filepath

    return _creator


@pytest.fixture
def voice_config_with_sequences():
    """Create a voice config with sequence patterns."""
    return {
        "name": "test_voice_with_sequences",
        "elements": {
            "dot": "dot.wav",
            "dash": "dash.wav",
            "sos": "sos.wav",
            "hello": "hello.wav",
        },
        "sequence_patterns": {"sos": "... --- ...", "hello": ".... . .-.. .-.. ---"},
    }


class TestSynthesizer:
    def test_generate_default_tone(self):
        """Test the generate_default_tone function."""
        tone = synthesizer.generate_default_tone(duration_ms=150, frequency=440)
        assert isinstance(tone, AudioSegment)
        assert len(tone) == 150
        assert tone.channels == 1
        assert tone.frame_rate == synthesizer.SAMPLE_RATE
        # Could also check fade in/out if pydub allows inspection, but length/type is good start

    def test_load_audio_element_single_file(
        self, temp_voice_pack_dir, dummy_audio_file_creator
    ):
        """Test _load_audio_element with a single valid filename."""
        # Create a real test file to avoid path not found issues
        test_file = "test.wav"
        test_path = dummy_audio_file_creator(test_file)

        result = synthesizer._load_audio_element(
            test_file, temp_voice_pack_dir, "test_el",
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )
        assert isinstance(result, AudioSegment)
        assert len(result) == 100  # The default duration from dummy_audio_file_creator

    def test_load_audio_element_list_of_files(
        self, temp_voice_pack_dir, dummy_audio_file_creator
    ):
        """Test _load_audio_element with a list of filenames."""
        # Create real test files to avoid path not found issues
        file1 = "file1.wav"
        file2 = "file2.wav"
        file3 = "file3.wav"

        dummy_audio_file_creator(file1, 100)
        dummy_audio_file_creator(file2, 110)
        dummy_audio_file_creator(file3, 120)

        file_list = [file1, file2, file3]

        # Mock random.choice to return a predictable file
        with patch("random.choice", return_value=file2) as mock_random_choice:
            result = synthesizer._load_audio_element(
                file_list, temp_voice_pack_dir, "test_el_list",
                fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
            )

            mock_random_choice.assert_called_once_with(file_list)
            assert isinstance(result, AudioSegment)
            assert len(result) == 110  # Length of file2

    def test_load_audio_element_file_not_found(self, temp_voice_pack_dir):
        """Test _load_audio_element when the audio file does not exist."""
        result = synthesizer._load_audio_element(
            "nonexistent.wav", temp_voice_pack_dir, "test_el_missing",
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )
        assert result is None

    def test_load_audio_element_invalid_type(self, temp_voice_pack_dir):
        """Test _load_audio_element with an invalid element_value type."""
        result = synthesizer._load_audio_element(
            123, temp_voice_pack_dir, "test_el_invalid_type",
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )  # type: ignore
        assert result is None
        result = synthesizer._load_audio_element(
            [], temp_voice_pack_dir, "test_el_empty_list",
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )
        assert result is None

    def test_load_audio_element_load_exception(
        self, temp_voice_pack_dir, dummy_audio_file_creator
    ):
        """Test error handling when AudioSegment.from_file raises an exception."""
        # Create a corrupt WAV file for testing
        corrupt_file = "corrupt.wav"
        path = os.path.join(temp_voice_pack_dir, corrupt_file)
        with open(path, "w") as f:
            f.write("This is not a valid WAV file")

        # Test the error handling
        with patch("logging.Logger.error") as mock_logger:
            result = synthesizer._load_audio_element(
                corrupt_file, temp_voice_pack_dir, "corrupt_el",
                fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
            )
            assert result is None
            mock_logger.assert_called_once()
            # Check that the error message contains the expected parts
            error_msg = mock_logger.call_args[0][0]
            assert "Error loading audio file" in error_msg
            assert corrupt_file in error_msg

    def test_get_basic_morse_elements_with_voice(
        self, temp_voice_pack_dir, dummy_audio_file_creator
    ):
        """Test get_basic_morse_elements with a voice config."""
        dot_path = dummy_audio_file_creator("dot.wav", 100)
        dash_path = dummy_audio_file_creator("dash.wav", 300)

        voice_config = {
            "name": "test_voice",
            "elements": {"dot": "dot.wav", "dash": "dash.wav"},
        }

        actual_unit_time_ms = 120  # WPM adjusted time

        dot_audio, dash_audio = synthesizer.get_basic_morse_elements(
            voice_config, temp_voice_pack_dir, actual_unit_time_ms,
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )

        # Check that we got AudioSegments back
        assert isinstance(dot_audio, AudioSegment)
        assert isinstance(dash_audio, AudioSegment)

        # Check the durations
        assert len(dot_audio) == 100  # Original dot.wav length
        assert len(dash_audio) == 300  # Original dash.wav length

    def test_get_basic_morse_elements_default_fallback(self):
        """Test get_basic_morse_elements with no voice config."""
        actual_unit_time_ms = 120  # WPM adjusted time

        dot_audio, dash_audio = synthesizer.get_basic_morse_elements(
            None, None, actual_unit_time_ms,
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )

        # Check that we got AudioSegments back
        assert isinstance(dot_audio, AudioSegment)
        assert isinstance(dash_audio, AudioSegment)

        # Check the durations
        assert len(dot_audio) == actual_unit_time_ms
        assert len(dash_audio) == actual_unit_time_ms * 3  # Default dash is 3x dot

    def test_get_basic_morse_elements_partial_fallback(
        self, temp_voice_pack_dir, dummy_audio_file_creator
    ):
        """Test get_basic_morse_elements with a voice config missing some elements."""
        # Create only a dot.wav, no dash.wav
        dot_path = dummy_audio_file_creator("dot.wav", 100)

        voice_config = {
            "name": "test_voice_partial",
            "elements": {
                "dot": "dot.wav"
                # No dash element
            },
        }

        actual_unit_time_ms = 120  # WPM adjusted time

        dot_audio, dash_audio = synthesizer.get_basic_morse_elements(
            voice_config, temp_voice_pack_dir, actual_unit_time_ms,
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )

        # Check that we got AudioSegments back
        assert isinstance(dot_audio, AudioSegment)
        assert isinstance(dash_audio, AudioSegment)

        # Check the durations
        assert len(dot_audio) == 100  # Original dot.wav length
        assert len(dash_audio) == actual_unit_time_ms * 3  # Default dash duration

    # --- Tests for generate_morse_audio ---

    @patch.object(synthesizer.voice_manager, "get_voice_dir_path")
    @patch.object(synthesizer.voice_manager, "load_voice_config")
    @patch(
        "echomorse.synthesizer.synthesizer._load_audio_element"
    )  # Patch the helper directly
    def test_gma_voice_basic_dot_dash(
        self,
        mock_load_element,
        mock_load_cfg,
        mock_get_dir,
        test_output_file,
        temp_voice_pack_dir,
        dummy_audio_file_creator,
    ):
        """Test with a voice providing basic dot and dash files."""
        voice_name = "testvoice_basic"
        dot_path = dummy_audio_file_creator("v_dot.wav", 100)
        dash_path = dummy_audio_file_creator("v_dash.wav", 300)

        mock_load_cfg.return_value = {
            "name": voice_name,
            "elements": {"dot": "v_dot.wav", "dash": "v_dash.wav"},
        }
        mock_get_dir.return_value = temp_voice_pack_dir

        mock_dot_segment = AudioSegment.silent(duration=100)
        mock_dash_segment = AudioSegment.silent(duration=300)

        # _load_audio_element will be called for 'dot', then 'dash' by get_segment (pre-caching)
        # then potentially again during morse processing if not using cache correctly (which it should)
        def side_effect_load_element(element_value, voice_dir, el_key, fade_type="percentage", fade_value=5.0, target_dbfs=-20.0):
            if el_key == "dot":
                return mock_dot_segment
            if el_key == "dash":
                return mock_dash_segment
            return None

        mock_load_element.side_effect = side_effect_load_element

        synthesizer.generate_morse_audio(
            ".-", test_output_file, voice_name_full=voice_name, wpm=20,
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )

        # Check a dot and dash were loaded
        mock_load_element.assert_any_call(
            "v_dot.wav", temp_voice_pack_dir, "dot", "percentage", 5.0, -20.0
        )
        mock_load_element.assert_any_call(
            "v_dash.wav", temp_voice_pack_dir, "dash", "percentage", 5.0, -20.0
        )

        # Check the audio was generated
        assert os.path.exists(test_output_file)

    @patch.object(synthesizer.voice_manager, "get_voice_dir_path")
    @patch.object(synthesizer.voice_manager, "load_voice_config")
    def test_gma_voice_dot_list_random_choice(
        self,
        mock_load_cfg,
        mock_get_dir,
        test_output_file,
        temp_voice_pack_dir,
        dummy_audio_file_creator,
    ):
        """Test voice with 'dot' as a list of files, ensuring random.choice is used."""
        voice_name = "testvoice_list"
        dot1_path = dummy_audio_file_creator("v_dot1.wav", 100)
        dot2_path = dummy_audio_file_creator(
            "v_dot2.wav", 110
        )  # Should be chosen by our patched random.choice
        dash_path = dummy_audio_file_creator("v_dash.wav", 300)
        dot_files_list = ["v_dot1.wav", "v_dot2.wav"]

        mock_load_cfg.return_value = {
            "name": voice_name,
            "elements": {"dot": dot_files_list, "dash": "v_dash.wav"},
        }
        mock_get_dir.return_value = temp_voice_pack_dir

        # Use real files but mock random.choice to select v_dot2.wav
        with patch("random.choice", return_value="v_dot2.wav") as mock_random_choice:
            synthesizer.generate_morse_audio(
                ".", test_output_file, voice_name_full=voice_name, wpm=20
            )
            assert os.path.exists(test_output_file)

            # Check random.choice was called with the dot files list
            mock_random_choice.assert_any_call(dot_files_list)

    @patch.object(
        synthesizer.voice_manager, "load_voice_config", return_value=None
    )  # No voice
    @patch.object(synthesizer.voice_manager, "get_voice_dir_path", return_value=None)
    @patch("echomorse.synthesizer.synthesizer.generate_default_tone")
    def test_gma_default_tones_no_voice(
        self, mock_generate_default_tone, mock_get_dir, mock_load_cfg, test_output_file
    ):
        """Test generate_morse_audio uses default tones when no voice is specified."""
        # Expected durations at WPM=20
        expected_dot_duration = int(DEFAULT_UNIT_DURATION_MS * (DEFAULT_WPM / 20.0))
        expected_dash_duration = int(expected_dot_duration * 3)

        # Mock segments returned by generate_default_tone
        mock_dot = AudioSegment.silent(duration=expected_dot_duration)
        mock_dash = AudioSegment.silent(duration=expected_dash_duration)

        # Define side_effect for mock_generate_default_tone
        # It will be called for pre-caching dot, then dash, then for each symbol in "... --- ..."
        tone_map = {expected_dot_duration: mock_dot, expected_dash_duration: mock_dash}

        def generate_tone_side_effect(duration_ms, frequency=synthesizer.DEFAULT_TONE_FREQ, fade_type="percentage", fade_value=5.0):
            return tone_map.get(duration_ms, AudioSegment.silent(duration=duration_ms))

        mock_generate_default_tone.side_effect = generate_tone_side_effect

        synthesizer.generate_morse_audio(
            "... --- ...", test_output_file, voice_name_full=None, wpm=20,
            fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
        )

        # Check the tone-generating function was called
        mock_generate_default_tone.assert_any_call(duration_ms=expected_dot_duration, frequency=synthesizer.DEFAULT_TONE_FREQ, fade_type="percentage", fade_value=5.0)
        mock_generate_default_tone.assert_any_call(duration_ms=expected_dash_duration, frequency=synthesizer.DEFAULT_TONE_FREQ, fade_type="percentage", fade_value=5.0)

        # Check the audio was generated
        assert os.path.exists(test_output_file)

    @patch("echomorse.synthesizer.synthesizer.AudioSegment.export")
    def test_gma_empty_or_whitespace_morse_code(self, mock_export, test_output_file):
        """Test generate_morse_audio with empty or whitespace Morse code."""
        # Prevent actual file creation by mocking export
        with pytest.raises(
            ValueError, match="Morse code cannot be empty or just whitespace."
        ):
            synthesizer.generate_morse_audio("", test_output_file)

        # Verify export wasn't called
        mock_export.assert_not_called()

        # Test with whitespace
        with pytest.raises(
            ValueError, match="Morse code cannot be empty or just whitespace."
        ):
            synthesizer.generate_morse_audio("   ", test_output_file)

        # Verify export still wasn't called
        mock_export.assert_not_called()

    def test_gma_sequence_patterns(
        self,
        temp_voice_pack_dir,
        dummy_audio_file_creator,
        voice_config_with_sequences,
        test_output_file,
    ):
        """Test sequence pattern matching in generate_morse_audio."""
        # Create the necessary audio files
        dummy_audio_file_creator("dot.wav", 100)
        dummy_audio_file_creator("dash.wav", 300)
        dummy_audio_file_creator("sos.wav", 800)  # Special SOS sound
        dummy_audio_file_creator("hello.wav", 1200)  # Special HELLO sound

        # Set up the voice manager mocks
        with patch.object(
            synthesizer.voice_manager,
            "load_voice_config",
            return_value=voice_config_with_sequences,
        ) as mock_load_cfg:
            with patch.object(
                synthesizer.voice_manager,
                "get_voice_dir_path",
                return_value=temp_voice_pack_dir,
            ) as mock_get_dir:
                # Test with pattern_chance=1.0 (always match patterns)
                synthesizer.generate_morse_audio(
                    "... --- ...",
                    test_output_file,
                    voice_name_full="test_voice_with_sequences",
                    wpm=20,
                    pattern_chance=1.0,
                )
                assert os.path.exists(test_output_file)

                # The SOS pattern should have been recognized and used
                audio = AudioSegment.from_file(test_output_file)
                # The length should be close to the sos.wav length (with slight adjustments for export/import)
                assert abs(len(audio) - 800) < 50

                # Now test with pattern_chance=0.0 (never match patterns)
                # We need a new output file to avoid overwriting the previous one
                new_output_file = test_output_file + ".no_pattern.wav"
                try:
                    synthesizer.generate_morse_audio(
                        "... --- ...",
                        new_output_file,
                        voice_name_full="test_voice_with_sequences",
                        wpm=20,
                        pattern_chance=0.0,
                    )
                    assert os.path.exists(new_output_file)

                    # The SOS pattern should NOT have been used, instead using individual dots and dashes
                    audio = AudioSegment.from_file(new_output_file)
                    # The length should be 9 symbols (3 dots, 3 dashes, 3 dots) plus spaces
                    # This would be significantly different from the single sos.wav file length
                    assert abs(len(audio) - 800) > 100
                finally:
                    # Clean up the second output file
                    if os.path.exists(new_output_file):
                        os.remove(new_output_file)

    def test_gma_with_word_and_letter_spaces(self, test_output_file):
        """Test generate_morse_audio with word spaces and letter spaces."""
        # Use default tones for simplicity
        morse_with_spaces = ". - . / ... --- ..."  # "E T E / SOS"

        synthesizer.generate_morse_audio(morse_with_spaces, test_output_file, wpm=20)
        assert os.path.exists(test_output_file)

        # Check that the audio file exists and has length > 0
        audio = AudioSegment.from_file(test_output_file)
        assert len(audio) > 0

    def test_gma_invalid_morse_char(self, test_output_file):
        """Test generate_morse_audio with invalid Morse characters."""
        # Include an invalid character '#' in the Morse code
        morse_with_invalid = "... # ..."

        with patch("logging.Logger.warning") as mock_logger:
            synthesizer.generate_morse_audio(
                morse_with_invalid, test_output_file, wpm=20
            )
            assert os.path.exists(test_output_file)

            # Check that a warning was logged for the invalid character
            mock_logger.assert_any_call(
                f"Unrecognized Morse char '#' at pos 4. Skipping."
            )

    def test_empty_final_audio_handling(self, test_output_file):
        """Test handling of an empty final audio segment (edge case)."""
        # This is a special case test where we manipulate the final_audio to be empty
        # We'll patch AudioSegment.export to check if a warning is logged
        morse_code = "."

        # Instead of trying to patch the local get_segment function directly,
        # we'll create a situation where the final audio is empty by patching
        # AudioSegment.export and verifying that the warning is logged
        with patch(
            "echomorse.synthesizer.synthesizer.AudioSegment.silent"
        ) as mock_silent:
            # First create a real silent segment for the check at the beginning
            real_silent = AudioSegment.silent(duration=0)
            # Then return a different silent segment for the 10ms fallback
            fallback_silent = AudioSegment.silent(duration=10)
            mock_silent.side_effect = [real_silent, fallback_silent]

            with patch("logging.Logger.warning") as mock_logger:
                synthesizer.generate_morse_audio(
                    morse_code, test_output_file, wpm=20,
                    fade_type="percentage", fade_value=5.0, target_dbfs=-20.0
                )
                assert os.path.exists(test_output_file)

                # Check that a warning was logged about the empty audio
                mock_logger.assert_any_call(
                    "Generated audio is empty. Creating 10ms silent file to prevent export errors."
                )

    def test_gma_cw_prosigns(
        self, temp_voice_pack_dir, dummy_audio_file_creator, test_output_file
    ):
        """Test special handling of CW prosigns with sequence patterns."""
        # Create sample audio files for testing
        dummy_audio_file_creator("dot.wav", 100)
        dummy_audio_file_creator("dash.wav", 300)
        dummy_audio_file_creator("cq.wav", 500)  # For CQ prosign
        dummy_audio_file_creator("ar.wav", 600)  # For AR (end of message) prosign
        dummy_audio_file_creator("sk.wav", 700)  # For SK (end of contact) prosign

        # Create a voice config with common CW prosigns
        cw_voice_config = {
            "name": "cw_prosigns_voice",
            "elements": {
                "dot": "dot.wav",
                "dash": "dash.wav",
                "cq": "cq.wav",
                "ar": "ar.wav",
                "sk": "sk.wav",
            },
            "sequence_patterns": {
                "cq": "-.-. --.-",  # CQ (calling any station)
                "ar": ".-.-.",  # AR (end of message)
                "sk": "...-.-",  # SK (end of contact)
            },
        }

        # Set up the voice manager mocks
        with patch.object(
            synthesizer.voice_manager, "load_voice_config", return_value=cw_voice_config
        ) as mock_load_cfg:
            with patch.object(
                synthesizer.voice_manager,
                "get_voice_dir_path",
                return_value=temp_voice_pack_dir,
            ) as mock_get_dir:
                # Test CQ pattern recognition
                synthesizer.generate_morse_audio(
                    "-.-. --.-",
                    test_output_file,  # CQ in Morse
                    voice_name_full="cw_prosigns_voice",
                    wpm=20,
                    pattern_chance=1.0,
                )
                assert os.path.exists(test_output_file)

                # The CQ pattern should have been recognized and used
                audio = AudioSegment.from_file(test_output_file)
                assert abs(len(audio) - 500) < 50  # Should be close to cq.wav length

                # Test AR pattern recognition
                ar_output_file = f"{test_output_file}.ar.wav"
                try:
                    synthesizer.generate_morse_audio(
                        ".-.-.",
                        ar_output_file,  # AR in Morse
                        voice_name_full="cw_prosigns_voice",
                        wpm=20,
                        pattern_chance=1.0,
                    )
                    assert os.path.exists(ar_output_file)

                    # The AR pattern should have been recognized and used
                    audio = AudioSegment.from_file(ar_output_file)
                    assert (
                        abs(len(audio) - 600) < 50
                    )  # Should be close to ar.wav length
                finally:
                    if os.path.exists(ar_output_file):
                        os.remove(ar_output_file)
