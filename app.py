from flask import Flask, request, url_for, render_template, g, redirect
import redis
import pickle
import utils

app = Flask(__name__)


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
    filename = f'melodies/melody_{mel_id}.wav'
    with open(filename, 'wb') as file:
        file.write(request.data)

    note = utils.get_notes(filename=filename, duration=10)
    note['id'] = mel_id
    redis_db.set(f'melody_{mel_id}', value=pickle.dumps(note))
    redis_db.set('mel_id', (mel_id + 1))
    return redirect(url_for('index'))


@app.route("/", methods=['GET'])
def index():
    redis_db = get_db()
    notes = list()
    for x in redis_db.scan_iter(match='melody_*'):
        melody = pickle.loads(redis_db.get(x))
        notes.append(melody)

    notes = sorted(notes, key=lambda x: x['id'], reverse=True)

    return render_template("index.html", notes=notes)


if __name__ == "__main__":
    app.run()
