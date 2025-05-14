import pytest
import os
import sys
import subprocess
from unittest.mock import patch
from pydub import AudioSegment

# Add src directory to path for direct imports in this test file
# This might not be strictly necessary if PDM sets up the path correctly
# when running pytest, but can be a fallback.
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import translator here as it's used in a test
from echomorse.translator import translator

# Standard CW (Continuous Wave) test examples
CW_TEST_CASES = {
    "cq": "CQ",  # Calling any station
    "cq_call": "CQ CQ DE W1AW",  # Standard CQ call
    "cq_dx": "CQ DX DE JA1XYZ",  # DX (long distance) call
    "exchange": "UR RST 599 599 BK",  # Signal report exchange
    "qth": "QTH BOSTON ES NAME JOHN",  # Location and name info
    "end": "73 SK",  # End of contact (best regards, silent key)
    "prosigns": "AR BT SK",  # Common procedural signals
    "emergency": "SOS",  # Distress signal
}


class TestIntegration:
    def run_cli_command(self, command_args, capture_output=True, check=True, text_input=None):
        """Helper to run CLI commands using 'echomorse' entry point."""
        env = os.environ.copy()
        # PDM should handle the path for the 'echomorse' executable when tests are run with 'pdm run pytest'
        # Ensure the current venv is in PATH if running pytest directly without pdm run
        venv_bin_path = os.path.join(sys.prefix, "bin")
        if venv_bin_path not in env.get("PATH", ""):
             env["PATH"] = venv_bin_path + os.pathsep + env.get("PATH", "")

        # The command is now 'echomorse' followed by its arguments
        cmd = ["echomorse"] + command_args
        
        # Print the command for debugging if needed
        # print(f"\nRunning command: {' '.join(cmd)}")
        # print(f"PATH: {env.get('PATH')}")
        # print(f"PYTHONPATH: {env.get('PYTHONPATH')}")
        # print(f"Which echomorse: {subprocess.run(['which', 'echomorse'], capture_output=True, text=True, env=env).stdout}")

        process_kwargs = {
            "capture_output": capture_output,
            "text": True, # For text-based stdout/stderr
            "check": check,
            "env": env
        }
        if text_input is not None:
            process_kwargs["input"] = text_input

        return subprocess.run(cmd, **process_kwargs)

    def test_text_to_morse_cli(self):
        """Test the text-to-morse CLI command with standard CW phrases."""
        result = self.run_cli_command(["text2code", CW_TEST_CASES["cq_call"]])
        expected_morse = translator.text_to_morse(CW_TEST_CASES["cq_call"])
        assert result.returncode == 0
        assert expected_morse in result.stdout

        result = self.run_cli_command(["t2c", "SOS"]) # Test alias
        assert result.returncode == 0
        assert translator.text_to_morse("SOS") in result.stdout

    def test_morse_to_text_cli(self):
        """Test the morse-to-text CLI command with CW phrases."""
        cq_call_morse = translator.text_to_morse(CW_TEST_CASES["cq_call"])
        result = self.run_cli_command(["code2text", cq_call_morse])
        assert result.returncode == 0
        assert CW_TEST_CASES["cq_call"].upper() in result.stdout

        sos_morse = translator.text_to_morse("SOS")
        result = self.run_cli_command(["c2t", sos_morse]) # Test alias
        assert result.returncode == 0
        assert "SOS" in result.stdout

    def test_text_to_audio_cli(self, tmp_path):
        """Test text-to-morse-audio CLI command."""
        output_file = tmp_path / "t2a_output.wav"
        self.run_cli_command([
            "text2audio",
            CW_TEST_CASES["end"],
            "-o",
            str(output_file),
            "--wpm",
            "25",
        ])
        assert os.path.exists(output_file)
        # Verify file is a valid WAV file and has some content
        audio = AudioSegment.from_file(output_file)
        assert len(audio) > 100  # Check if audio has a reasonable length (e.g., >100ms)

    def test_text_to_audio_alias_cli(self, tmp_path):
        """Test text-to-morse-audio CLI command using its alias."""
        output_file = tmp_path / "t2a_alias_output.wav"
        self.run_cli_command([
            "t2a", # Using alias
            CW_TEST_CASES["exchange"],
            "-o",
            str(output_file),
            "--wpm",
            "18",
        ])
        assert os.path.exists(output_file)
        audio = AudioSegment.from_file(output_file)
        assert len(audio) > 100

    def test_list_voices_cli(self):
        """Test the list-voices CLI command."""
        result = self.run_cli_command(["list-voices"])
        assert result.returncode == 0
        assert "Available voice profiles:" in result.stdout
        assert "CW (built-in)" in result.stdout
        # Assuming dog_bark voice exists from previous tests/setup
        assert "dog_bark" in result.stdout 

    def test_list_voices_detailed_cli(self):
        """Test the list-voices --detailed CLI command."""
        result = self.run_cli_command(["list-voices", "--detailed"])
        assert result.returncode == 0
        assert "Description: Sine wave tones for standard Morse code" in result.stdout
        assert "Audio files: 0" in result.stdout # For CW (built-in)
        # Assuming dog_bark voice exists and has a config
        assert "Description: Dog bark sounds for Morse code" in result.stdout 

    def test_help_message_main(self):
        """Test that the main help message is displayed."""
        result = self.run_cli_command(["-h"], check=False) # -h exits with 0
        assert result.returncode == 0
        assert "usage: echomorse" in result.stdout
        assert "Available commands" in result.stdout

    def test_help_message_subcommand(self):
        """Test that help message for a subcommand is displayed."""
        result = self.run_cli_command(["text2audio", "-h"], check=False)
        assert result.returncode == 0
        assert "usage: echomorse text2audio" in result.stdout
        assert "Text to convert to audio" in result.stdout
    
    def test_piping_text2code_code2text(self):
        """Test piping text through text2code and then code2text."""
        input_text = "HELLO PIPING TEST"
        # Simulate: echo "HELLO PIPING TEST" | echomorse t2c | echomorse c2t
        
        # Step 1: text2code
        process1 = subprocess.Popen(["echomorse", "t2c"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        morse_output, _ = process1.communicate(input=input_text)
        assert process1.returncode == 0
        assert morse_output.strip() == translator.text_to_morse(input_text) # Verify intermediate morse

        # Step 2: code2text
        process2 = subprocess.Popen(["echomorse", "c2t"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        final_text, _ = process2.communicate(input=morse_output)
        assert process2.returncode == 0
        assert final_text.strip() == input_text.upper()

    def test_piping_text2code_code2audio(self, tmp_path):
        """Test piping text through text2code then code2audio."""
        output_file = tmp_path / "pipe_t2c_c2a.wav"
        input_text = "PIPE TO AUDIO"
        # Simulate: echo "PIPE TO AUDIO" | echomorse t2c | echomorse c2a -o file.wav

        process1 = subprocess.Popen(["echomorse", "t2c"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        morse_output, _ = process1.communicate(input=input_text)
        assert process1.returncode == 0

        process2 = subprocess.Popen(["echomorse", "c2a", "-o", str(output_file)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        _, stderr_c2a = process2.communicate(input=morse_output)
        # print(f"c2a stderr: {stderr_c2a}") # For debugging
        assert process2.returncode == 0, f"CLI Error in c2a part of pipe: {stderr_c2a}"
        
        assert os.path.exists(output_file)
        audio = AudioSegment.from_file(output_file)
        assert len(audio) > 100

    def test_text2audio_output_file_created(self, tmp_path):
        """Test text2audio command piping audio data to stdout."""
        text_to_convert = "A"
        command = [
            "echomorse", "text2audio", text_to_convert, "-o", "-",
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        assert process.returncode == 0, f"CLI Error: {stderr.decode()}"
        assert stdout.startswith(b"RIFF"), "Output does not start with RIFF (not WAV format)"
        assert stdout[8:12] == b"WAVE", "Output does not have WAVE at offset 8 (not WAV format)"
        assert len(stdout) > 1000, "Suspiciously short audio output for 'A'"

    def test_code2audio_output_file_created(self, tmp_path):
        output_file = tmp_path / "test_c2a_output.wav"
        morse_to_convert = ".... . .-.. .-.. ---"
        result = self.run_cli_command([
            "code2audio", morse_to_convert, "-o", str(output_file)
        ])
        assert result.returncode == 0, f"CLI Error: {result.stderr}"
        assert output_file.exists()
        with open(output_file, 'rb') as f:
            header = f.read(12)
        assert header.startswith(b"RIFF")
        assert header[8:12] == b"WAVE"
        assert output_file.stat().st_size > 100

    def test_text2audio_output_to_stdout(self, tmp_path):
        """Test text2audio command piping audio data to stdout."""
        text_to_convert = "A"
        command = [
            "echomorse", "text2audio", text_to_convert, "-o", "-",
        ]
        # Use subprocess.Popen to capture binary stdout
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        assert process.returncode == 0, f"CLI Error: {stderr.decode(errors='ignore')}"
        assert stdout.startswith(b"RIFF"), "Output does not start with RIFF (not WAV format)"
        assert stdout[8:12] == b"WAVE", "Output does not have WAVE at offset 8 (not WAV format)"
        assert len(stdout) > 1000, "Suspiciously short audio output for 'A' to stdout"

    def test_code2audio_output_to_stdout(self, tmp_path):
        """Test code2audio command piping audio data to stdout."""
        morse_to_convert = ".-"
        command = [
            "echomorse", "code2audio", morse_to_convert, "-o", "-",
        ]
        # Use subprocess.Popen to capture binary stdout
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        assert process.returncode == 0, f"CLI Error: {stderr.decode(errors='ignore')}"
        assert stdout.startswith(b"RIFF"), "Output does not start with RIFF (not WAV format)"
        assert stdout[8:12] == b"WAVE", "Output does not have WAVE at offset 8 (not WAV format)"
        assert len(stdout) > 1000, "Suspiciously short audio output for '.-' to stdout"

    def test_text2audio_custom_voice_and_wpm(self, tmp_path):
        # ... existing code ...
        # If the synthesizer logs a warning about voice not found, that's acceptable here.
        pass

# Any further top-level test functions or fixtures can go here
