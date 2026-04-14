from flask import Flask, request, jsonify
import threading
import math
import random
from flask_cors import CORS
import os
import psycopg2
import psycopg2.extras

# Базовые цены инвестиций (должны совпадать с клиентом)
INVESTMENTS_BASE = {
    'pear': 50,
    'sasung': 100,
    'gold': 2000,
    'bct': 8000,
}

market_prices = {k: v for k, v in INVESTMENTS_BASE.items()}
market_trends = {k: 'up' for k in INVESTMENTS_BASE}

def tick_market():
    global market_prices, market_trends
    for asset_id, base_price in INVESTMENTS_BASE.items():
        # 20% шанс сменить тренд
        if random.random() < 0.2:
            market_trends[asset_id] = 'down' if market_trends[asset_id] == 'up' else 'up'
        # Изменение цены 2-8%
        pct = random.uniform(0.02, 0.08)
        if market_trends[asset_id] == 'up':
            market_prices[asset_id] = math.floor(market_prices[asset_id] * (1 + pct))
        else:
            market_prices[asset_id] = math.floor(market_prices[asset_id] * (1 - pct))
        # Границы мин 10% макс 500%
        market_prices[asset_id] = max(
            math.floor(base_price * 0.1),
            min(market_prices[asset_id], base_price * 5)
        )
    # Повторяем каждые 30 секунд
    threading.Timer(30.0, tick_market).start()

# Запускаем рынок
tick_market()

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')

ASSET_DEFAULTS = {
    'kiosk': 100, 'shaurma': 100, 'apple': 100, 'sneaker': 100, 'zavod': 1, 'cum': 1, 'neft': 1,
    'pear': 500, 'sasung': 500, 'gold': 500, 'bct': 500,
    'lada': 50, 'toyota': 50, 'bmw': 50, 'velo': 50, 'lada2107': 50, 'lada2115': 50, 'galant': 50, 'haval': 50, 'solaris': 50, 'kawasaki': 50, 'lada2108': 50, 'jaecoo': 50, 'cruiser': 50, 'maybach': 50, 'kamaz': 50,'sls': 20,'g63': 20,'urus': 20,
    'apartment': 50, 'house': 50, 'tower': 50, 'dom': 50, 'obshaga': 50, 'shalash': 50, 'kvartira': 50, 'studio': 50,'townhouse': 50, '3kvartira': 50,
    'country_house': 50,'duplex': 50,'luxury_apartment': 50,'villa': 50,'manor': 50,'castle': 50,'sky_palace': 50,'private_island': 50,'royal_palace': 50
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

@app.route('/market')
def get_market():
    return jsonify({
        'prices': market_prices,
        'trends': market_trends
    })

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
