from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

ASSET_DEFAULTS = {
    'kiosk': 2, 'shaurma': 2, 'apple': 2,
    'lada': 1, 'toyota': 1, 'bmw': 1,
    'apartment': 1, 'house': 1, 'tower': 1
}

# ── Подключение к БД ──
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# ── Создать таблицы если не существуют ──
def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id TEXT PRIMARY KEY,
                    name TEXT DEFAULT 'Игрок',
                    photo TEXT DEFAULT '',
                    money BIGINT DEFAULT 0,
                    level INT DEFAULT 1,
                    popularity INT DEFAULT 0,
                    businesses INT DEFAULT 0,
                    updated_at BIGINT DEFAULT 0,
                    savedata TEXT DEFAULT ''
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    count INT DEFAULT 0
                )
            ''')
            cur.execute('SELECT COUNT(*) FROM assets')
            if cur.fetchone()[0] == 0:
                for asset_id, count in ASSET_DEFAULTS.items():
                    cur.execute(
                        'INSERT INTO assets (id, count) VALUES (%s, %s) ON CONFLICT DO NOTHING',
                        (asset_id, count)
                    )
        conn.commit()

init_db()

# ── Сохранить игрока ──
@app.route('/save', methods=['POST'])
def save_player():
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({'ok': False, 'error': 'no id'}), 400

        savedata = data.get('savedata', '')

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO players (id, name, photo, money, level, popularity, businesses, updated_at, savedata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        photo = EXCLUDED.photo,
                        money = EXCLUDED.money,
                        level = EXCLUDED.level,
                        popularity = EXCLUDED.popularity,
                        businesses = EXCLUDED.businesses,
                        updated_at = EXCLUDED.updated_at,
                        savedata = EXCLUDED.savedata
                ''', (
                    str(data['id']),
                    data.get('name', 'Игрок'),
                    data.get('photo', ''),
                    int(data.get('money', 0)),
                    int(data.get('level', 1)),
                    int(data.get('popularity', 0)),
                    int(data.get('businesses', 0)),
                    data.get('updatedAt', 0),
                    savedata
                ))
            conn.commit()
        return jsonify({'ok': True})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ── Загрузить игрока ──
@app.route('/load/<player_id>', methods=['GET'])
def load_player(player_id):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT savedata FROM players WHERE id = %s', (player_id,))
                row = cur.fetchone()
                if row and row[0]:
                    return jsonify({'ok': True, 'savedata': row[0]})
                return jsonify({'ok': False})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

# ── Получить топ всех игроков ──
@app.route('/top', methods=['GET'])
def get_top():
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('''
                    SELECT id, name, photo, money, level, popularity, businesses, updated_at as "updatedAt"
                    FROM players
                    ORDER BY money DESC
                    LIMIT 100
                ''')
                return jsonify(cur.fetchall())
    except Exception as e:
        return jsonify([]), 500

# ── Получить друзей по списку id ──
@app.route('/friends', methods=['POST'])
def get_friends():
    try:
        data = request.json
        ids = [str(i) for i in data.get('ids', [])]
        if not ids:
            return jsonify([])

        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('''
                    SELECT id, name, photo, money, level, popularity, businesses, updated_at as "updatedAt"
                    FROM players
                    WHERE id = ANY(%s)
                    ORDER BY money DESC
                ''', (ids,))
                return jsonify(cur.fetchall())
    except Exception as e:
        return jsonify([]), 500

# ── Получить все счётчики активов ──
@app.route('/assets', methods=['GET'])
def get_assets():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id, count FROM assets')
                rows = cur.fetchall()
                counts = {row[0]: row[1] for row in rows}
                return jsonify({'counts': counts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Обновить счётчик актива ──
@app.route('/asset', methods=['POST'])
def update_asset():
    try:
        data = request.json
        asset_id = data.get('assetId')
        change = data.get('change', 0)
        player_id = data.get('playerId')

        if not asset_id:
            return jsonify({'success': False, 'error': 'no assetId'}), 400

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count FROM assets WHERE id = %s', (asset_id,))
                row = cur.fetchone()
                current = row[0] if row else 0

                if change == -1 and current <= 0:
                    cur.execute('SELECT id, count FROM assets')
                    counts = {r[0]: r[1] for r in cur.fetchall()}
                    return jsonify({'success': False, 'error': 'limit exceeded', 'counts': counts}), 400

                cur.execute(
                    'UPDATE assets SET count = count + %s WHERE id = %s',
                    (change, asset_id)
                )
                cur.execute('SELECT id, count FROM assets')
                counts = {r[0]: r[1] for r in cur.fetchall()}
            conn.commit()

        print(f"Player {player_id} updated {asset_id}. Remaining: {counts.get(asset_id)}")
        return jsonify({'success': True, 'counts': counts})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ── Проверка что сервер живой ──
@app.route('/ping', methods=['GET'])
def ping():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) FROM players')
                player_count = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM assets')
                asset_count = cur.fetchone()[0]
        return jsonify({'ok': True, 'players': player_count, 'assets': asset_count})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)