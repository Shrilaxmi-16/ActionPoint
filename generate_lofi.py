import numpy as np
import scipy.io.wavfile as wavfile

sr = 44100
duration = 60.0  # 60 seconds
t = np.linspace(0, duration, int(sr * duration), endpoint=False)

# BPM: 84 bpm (lo-fi groove)
bpm = 84
beat_dur = 60.0 / bpm
bar_dur = beat_dur * 4  # 4/4 time

# Upbeat Jazz / Lo-Fi Chord Progression:
# 1. Cmaj7 (C4, E4, G4, B4)
# 2. Am7 (A3, C4, E4, G4)
# 3. Dm7 (D4, F4, A4, C5)
# 4. G7 (G3, B3, D4, F4)
chords = [
    [261.63, 329.63, 392.00, 493.88],  # Cmaj7
    [220.00, 261.63, 329.63, 392.00],  # Am7
    [293.66, 349.23, 440.00, 523.25],  # Dm7
    [196.00, 246.94, 293.66, 349.23],  # G7
]

# Bass line corresponding to roots
bass_notes = [130.81, 110.00, 146.83, 98.00]

audio = np.zeros(len(t))

# 1. EPiano / Rhodes synthesized chords with warm decay and tremolo
for i in range(int(duration / bar_dur) + 1):
    bar_start = i * bar_dur
    chord = chords[i % len(chords)]
    bass = bass_notes[i % len(bass_notes)]
    
    # Bass note
    b_idx = (t >= bar_start) & (t < bar_start + bar_dur)
    t_b = t[b_idx] - bar_start
    env_b = np.exp(-t_b * 1.5)
    bass_wave = (np.sin(2 * np.pi * bass * t_b) + 0.3 * np.sin(2 * np.pi * bass * 2 * t_b)) * env_b
    audio[b_idx] += 0.35 * bass_wave
    
    # Rhodes Chord hits on beats 1 and 2.5 (swing feel)
    for hit_offset, decay in [(0, 1.2), (beat_dur * 1.5, 1.8), (beat_dur * 3.0, 1.5)]:
        hit_start = bar_start + hit_offset
        if hit_start >= duration:
            break
        c_idx = (t >= hit_start) & (t < hit_start + bar_dur)
        t_c = t[c_idx] - hit_start
        env_c = np.exp(-t_c * decay)
        # Subtle tremolo
        tremolo = 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t_c)
        chord_wave = np.zeros(len(t_c))
        for freq in chord:
            chord_wave += np.sin(2 * np.pi * freq * t_c) + 0.25 * np.sin(2 * np.pi * freq * 2 * t_c)
        audio[c_idx] += 0.18 * chord_wave * env_c * tremolo

# 2. Drum Groove (Kick on 1 & 2.5, Snare/Clap on 2 & 4, subtle swing Hi-hat on 8ths)
for beat_idx in range(int(duration / (beat_dur / 2))):
    beat_time = beat_idx * (beat_dur / 2)
    sub_beat = beat_idx % 8  # 8 eighth notes per bar
    
    # Kick on 0 and 3
    if sub_beat in [0, 3]:
        idx = (t >= beat_time) & (t < beat_time + 0.25)
        t_k = t[idx] - beat_time
        # Pitch drop kick 120Hz -> 45Hz
        k_freq = 45 + 75 * np.exp(-t_k * 30)
        kick = np.sin(2 * np.pi * k_freq * t_k) * np.exp(-t_k * 14)
        audio[idx] += 0.45 * kick
        
    # Lo-fi warm snare / rim click on 2 and 6 (beats 2 and 4)
    if sub_beat in [2, 6]:
        idx = (t >= beat_time) & (t < beat_time + 0.2)
        t_s = t[idx] - beat_time
        noise = (np.random.rand(len(t_s)) * 2 - 1) * np.exp(-t_s * 22)
        body = np.sin(2 * np.pi * 180 * t_s) * np.exp(-t_s * 18)
        audio[idx] += 0.28 * (0.6 * noise + 0.4 * body)
        
    # Shaker / closed hat on eighth notes
    idx = (t >= beat_time) & (t < beat_time + 0.08)
    t_h = t[idx] - beat_time
    hat = (np.random.rand(len(t_h)) * 2 - 1) * np.exp(-t_h * 55)
    audio[idx] += 0.08 * hat

# 3. Lo-Fi Vinyl Crackle & Ambient warmth
crackle = (np.random.rand(len(t)) * 2 - 1) * 0.015
# Random pop pulses
pops = np.zeros(len(t))
pop_locs = np.random.randint(0, len(t), int(duration * 6))
pops[pop_locs] = np.random.uniform(-0.1, 0.1, len(pop_locs))
audio += crackle + pops

# Normalize to avoid clipping
max_amp = np.max(np.abs(audio))
if max_amp > 0:
    audio = (audio / max_amp) * 0.82

audio_int16 = (audio * 32767).astype(np.int16)
wavfile.write("/tmp/upbeat_lofi.wav", sr, audio_int16)
print("Successfully generated /tmp/upbeat_lofi.wav")
