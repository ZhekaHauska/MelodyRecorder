import librosa
import numpy as np
from midiutil import MIDIFile
from midi2audio import FluidSynth

c_scales = {'major': [0, 2, 4, 5, 7, 9, 11],
            'minor': [0, 2, 3, 5, 7, 8, 10]}
notes_to_numbers = {'C': 0, 'C♯': 1, 'D': 2, 'D♯': 3, 'E': 4, 'F': 5, 'F♯': 6, 'G': 7, 'G♯': 8, 'A': 9, 'A♯': 10,
                    'B': 11}
numbers_to_notes = {value: key for key, value in notes_to_numbers.items()}


def get_notes(filename, duration):
    y, sr = librosa.load(filename)
    fmin = 73
    fmax = 1108
    n_bins = 256
    harmonic = librosa.effects.harmonic(y)
    onsets = librosa.onset.onset_detect(harmonic)
    # get silence states
    rms = librosa.feature.rms(y=harmonic)[0]
    r_normalized = (rms - 0.01) / (np.std(rms) + 1e-9)
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
    pitches, magnitudes = librosa.piptrack(harmonic, sr=sr,
                                           fmin=fmin,
                                           fmax=fmax)
    freq = pitches.max(axis=-1)
    bins = np.argmax(magnitudes, axis=0)
    bins_sync = librosa.util.sync(bins, borders, aggregate=np.median)
    states_sync = librosa.util.sync(states, borders, aggregate=np.median)
    pitch_sync = freq[bins_sync]
    pitch_sync[pitch_sync == 0] = 1e-6
    # get notation and midi keys
    notes = librosa.hz_to_note(pitch_sync)
    midi = list(librosa.hz_to_midi(pitch_sync))
    # check pauses
    pauses = np.nonzero(states_sync == 0)[0]
    for x in list(pauses):
        notes[int(x)] = 'P'
        midi[int(x)] = 'P'
    # check wrong notes
    for i, note in enumerate(notes):
        if note[:-1] not in notes_to_numbers.keys():
            notes[i] = 'P'
    # add borders to borders and define notes lengths
    borders = np.append(borders, pitches.shape[-1])
    borders = np.concatenate([np.array([0]), borders])
    lengths = borders[1:] - borders[:-1]

    bpm = librosa.beat.tempo(y, sr=sr)

    melody = dict(notes=notes,
                  lengths=list(lengths),
                  midi=midi,
                  bpm=bpm,
                  duration=duration,
                  raw_filename=filename.split('/')[-1])

    return melody


def to_midi_wav(melody):
    # convert to midi
    filename = melody['raw_filename']
    k = melody['duration'] * melody['bpm'] / (np.array(melody['lengths']).sum() * 60)

    time = 0
    track = 0
    channel = 0
    volume = 100

    my_midi = MIDIFile(1)
    my_midi.addTempo(track, time, melody['bpm'])
    my_midi.addProgramChange(track, channel, time, 0)

    for i, pitch in enumerate(melody['midi']):
        length = k * melody['lengths'][i]
        if pitch != 'P' and 0 <= pitch <= 255 and length >= 1/16:
            my_midi.addNote(track, channel, round(pitch), time, length, volume)
        time = time + k * melody['lengths'][i]

    midi_filename = 'tmp/' + filename.split('.')[0] + '.mid'
    with open(midi_filename, "wb") as output_file:
        my_midi.writeFile(output_file)

    # convert back to wav
    filename_processed = 'tmp/'+ filename.split('.')[0] + '_processed' + '.wav'
    fs = FluidSynth('static/Drama Piano.sf2')
    fs.midi_to_audio(midi_filename, filename_processed)


def fix_notes(melody):
    # generate scales
    notes_numbers = [notes_to_numbers[x[:-1]] for x in melody['notes'] if x != 'P']
    current_notes = set(notes_numbers)
    # %%
    possible_scales = list()
    for note in current_notes:
        for scale in generate_scales(note):
            possible_scales.append((scale, len(current_notes.intersection(scale))))

    possible_scales = sorted(possible_scales, key=lambda x: x[1], reverse=True)
    max_intersection = possible_scales[0][1]

    possible_scales = list(filter(lambda x: x[1] == max_intersection, possible_scales))

    substitutions = list()
    for scale, _ in possible_scales:
        wrong_notes = current_notes.difference(scale)
        loss = 0
        substitution = dict()
        for wrong_note in wrong_notes:
            scale = np.array(list(scale))
            differences = np.abs(scale - wrong_note) % 12
            loss += np.min(differences) * np.count_nonzero(
                wrong_note == np.array(notes_numbers))
            substitution[wrong_note] = scale[np.argmin(differences)]
        substitutions.append((substitution, loss))

    substitutions = sorted(substitutions, key=lambda x: x[1])

    best_substitution = substitutions[0][0]

    fixed_notes = list()
    for note in melody['notes']:
        if note != 'P':
            if notes_to_numbers[note[:-1]] in best_substitution.keys():
                key = notes_to_numbers[note[:-1]]
                fixed_notes.append(numbers_to_notes[best_substitution[key]] + note[-1])
            else:
                fixed_notes.append(note)
        else:
            fixed_notes.append(note)

    midi = [librosa.note_to_midi(x) if x != 'P' else x for x in fixed_notes]

    melody['notes'] = fixed_notes
    melody['midi'] = midi
    return melody


def generate_scales(base_note):
    scales = list()
    for base_scale in c_scales.values():
        scale = (np.array(base_scale) + (base_note - base_scale[0]) % 12) % 12
        scales.append(set(scale))
    return scales


if __name__ == '__main__':
    melody = get_notes('tmp/melody_5.wav', 10)
    melody = fix_notes(melody)
    to_midi_wav(melody)
