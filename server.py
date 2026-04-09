from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os

app = Flask(__name__)
CORS(app)  # разрешаем запросы с GitHub Pages

DB_FILE = 'players.json'

# ── Загрузить базу ──
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# ── Сохранить базу ──
def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# ── Сохранить игрока ──
@app.route('/save', methods=['POST'])
def save_player():
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({'ok': False, 'error': 'no id'}), 400

        db = load_db()
        db[str(data['id'])] = {
            'id':         str(data['id']),
            'name':       data.get('name', 'Игрок'),
            'photo':      data.get('photo', ''),
            'money':      int(data.get('money', 0)),
            'level':      int(data.get('level', 1)),
            'popularity': int(data.get('popularity', 0)),
            'businesses': int(data.get('businesses', 0)),
            'updatedAt':  data.get('updatedAt', 0)
        }
        save_db(db)
        return jsonify({'ok': True})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ── Получить топ всех игроков ──
@app.route('/top', methods=['GET'])
def get_top():
    try:
        db = load_db()
        players = list(db.values())
        players.sort(key=lambda x: x.get('money', 0), reverse=True)
        return jsonify(players[:100])  # топ 100
    except Exception as e:
        return jsonify([]), 500

# ── Получить друзей по списку id ──
@app.route('/friends', methods=['POST'])
def get_friends():
    try:
        data = request.json
        ids  = [str(i) for i in data.get('ids', [])]
        db   = load_db()
        friends = [db[i] for i in ids if i in db]
        friends.sort(key=lambda x: x.get('money', 0), reverse=True)
        return jsonify(friends)
    except Exception as e:
        return jsonify([]), 500

# ── Проверка что сервер живой ──
@app.route('/ping', methods=['GET'])
def ping():
    db = load_db()
    return jsonify({'ok': True, 'players': len(db)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)