from pydub import AudioSegment

# Create a short silent segment for dot
dot_sound = AudioSegment.silent(duration=100) # 100 ms
dot_sound.export("dummy_dot.wav", format="wav")

# Create a slightly longer silent segment for dash
dash_sound = AudioSegment.silent(duration=300) # 300 ms
dash_sound.export("dummy_dash.wav", format="wav")

print("dummy_dot.wav and dummy_dash.wav created") 