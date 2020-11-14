from flask import Flask, request, url_for, render_template, g, redirect, send_from_directory
import redis
import pickle
import utils
import os

app = Flask(__name__)

try:
    os.mkdir('tmp')
except FileExistsError:
    pass


@app.route('/tmp/<filename>')
def tmp(filename):
    return send_from_directory('tmp', filename)


def get_db():
    if not hasattr(g, 'redis_db'):
        g.redis_db = redis.Redis()
        if not g.redis_db.exists('mel_id'):
            mel_id = 0
            g.redis_db.set('mel_id', mel_id)
    return g.redis_db


@app.route("/process", methods=['POST'])
def process():
    redis_db = get_db()
    mel_id = int(redis_db.get('mel_id'))
    filename = f'melody_{mel_id}.wav'
    with open('tmp/' + filename, 'wb') as file:
        file.write(request.data)

    melody = utils.get_notes(filename='tmp/' + filename, duration=10)
    if len(melody['notes']) != 0:
        melody = utils.fix_notes(melody)

        melody['id'] = mel_id
        melody['midi_filename'] = filename.split('.')[0] + '.mid'
        melody['proc_filename'] = filename.split('.')[0] + '_processed' + '.wav'

        redis_db.set(f'melody_{mel_id}', value=pickle.dumps(melody))
        redis_db.set('mel_id', (mel_id + 1))
    return redirect(url_for('index'))


@app.route("/", methods=['GET'])
def index():
    redis_db = get_db()
    notes = list()
    files = os.listdir('tmp/')
    for x in redis_db.scan_iter(match='melody_*'):
        melody = pickle.loads(redis_db.get(x))
        notes.append(melody)
        if (melody['raw_filename'].split('.')[0] + '_processed.wav') not in files:
            utils.to_midi_wav(melody)

    notes = sorted(notes, key=lambda x: x['id'], reverse=True)

    return render_template("index.html", notes=notes)


if __name__ == "__main__":
    app.run(debug=True)
