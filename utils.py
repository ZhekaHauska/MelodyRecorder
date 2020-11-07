import librosa
import numpy as np
from midiutil import MIDIFile
from midi2audio import FluidSynth
from flask import url_for


def get_notes(filename, duration):
    y, sr = librosa.load(filename)
    fmin = 73
    fmax = 1108
    n_bins = 256
    onsets = librosa.onset.onset_detect(y)
    harmonic = librosa.effects.harmonic(y)
    # get silence states
    rms = librosa.feature.rms(y=y)[0]
    r_normalized = (rms - 0.01) / np.std(rms)
    p = np.exp(r_normalized) / (1 + np.exp(r_normalized))
    transition = librosa.sequence.transition_loop(2, [0.5, 0.6])
    full_p = np.vstack([1 - p, p])
    states = librosa.sequence.viterbi_discriminative(full_p, transition)
    # drop silent onsets
    onsets_filtered = onsets[states[onsets] > 0]
    # silence start borders
    silence = np.nonzero(states[:-1] - states[1:] > 0)[0]
    # note borders
    borders = np.hstack([silence.reshape(1, -1), onsets_filtered.reshape(1, -1)])[0]
    borders = np.sort(borders)
    # get frequencies and aggregate them
    mel = librosa.feature.melspectrogram(harmonic, fmin=fmin,
                                         fmax=fmax, n_mels=n_bins)
    mel_sync = librosa.util.sync(mel, borders, aggregate=np.max)
    states_sync = librosa.util.sync(states, borders)
    mel_filtered_sync = mel_sync * states_sync
    mel_notes = np.argmax(mel_filtered_sync, axis=0)
    # get notation and midi keys
    mel_freq = librosa.mel_frequencies(n_mels=n_bins, fmin=fmin,
                                       fmax=fmax)
    notes = librosa.hz_to_note((mel_freq[mel_notes] + mel_freq[mel_notes+1])*0.5)
    midi = list(librosa.hz_to_midi((mel_freq[mel_notes] + mel_freq[mel_notes+1])*0.5))
    # check pauses
    pauses = np.nonzero(mel_filtered_sync.mean(axis=0) == 0)[0]
    for x in list(pauses):
        notes[int(x)] = 'P'
        midi[int(x)] = 'P'
    # add borders to borders and define notes lengths
    borders = np.append(borders, mel.shape[-1])
    borders = np.concatenate([np.array([0]), borders])
    lengths = borders[1:] - borders[:-1]

    bpm = librosa.beat.tempo(y, sr=sr)

    melody = dict(notes=notes,
                  lengths=list(lengths),
                  midi=midi,
                  bpm=bpm,
                  duration=duration)
    # convert to midi
    k = melody['duration'] * melody['bpm'] / (np.array(melody['lengths']).sum() * 60)

    time = 0
    track = 0
    channel = 0
    volume = 100

    my_midi = MIDIFile(1)
    my_midi.addTempo(track, time, melody['bpm'])
    my_midi.addProgramChange(track, channel, time, 0)

    for i, pitch in enumerate(melody['midi']):
        if pitch != 'P':
            my_midi.addNote(track, channel, int(pitch), time, k * melody['lengths'][i], volume)
        time = time + k * melody['lengths'][i]

    with open(filename.split('.')[0] + '.mid', "wb") as output_file:
        my_midi.writeFile(output_file)
    # convert back to wav
    fs = FluidSynth('static/Drama Piano.sf2')
    processed_filename = filename.split('.')[0] + '_processed' + '.wav'
    fs.midi_to_audio(filename.split('.')[0] + '.mid', 'static/' + processed_filename)
    melody['filename'] = url_for('static', filename=processed_filename)
    return melody


if __name__ == '__main__':
    get_notes('melodies/melody_14.wav', 10)
