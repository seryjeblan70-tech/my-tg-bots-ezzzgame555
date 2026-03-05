import aiosqlite
import json
from datetime import datetime

DB_PATH = "user_history.db"  # Путь к базе данных

# ==================== СТАРЫЕ ФУНКЦИИ (для таблицы users) ====================

async def init_db():
    """Создаёт таблицу users, если её нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referrer_id INTEGER,
                created_at TEXT
            )
        ''')
        await db.commit()

async def get_user(user_id: int):
    """Возвращает запись пользователя из таблицы users."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def create_user(user_id: int, username: str = None, referrer_id: int = None):
    """Создаёт нового пользователя в таблице users."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, username, referrer_id, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, referrer_id, now))
        await db.commit()

async def update_energy(user_id: int, new_energy: int):
    """Обновляет энергию пользователя (заглушка)."""
    pass

# ==================== НОВЫЕ ФУНКЦИИ (для таблицы game_users) ====================

async def init_game_db():
    """Создаёт таблицу game_users, если её нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS game_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                food INTEGER DEFAULT 50,
                gems INTEGER DEFAULT 100,
                click_power REAL DEFAULT 1.0,
                click_upgrade_level INTEGER DEFAULT 0,
                stamina INTEGER DEFAULT 100,
                max_stamina INTEGER DEFAULT 100,
                stamina_regen_rate REAL DEFAULT 1.0,
                regen_upgrade_level INTEGER DEFAULT 0,
                max_stamina_upgrade_level INTEGER DEFAULT 0,
                total_clicks INTEGER DEFAULT 0,
                unlocked_pets TEXT DEFAULT '["dog","cat","rabbit"]',
                selected_pet TEXT DEFAULT 'dog',
                friends_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        await db.commit()

async def get_game_user(user_id: int):
    """Возвращает данные игрока из таблицы game_users."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM game_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('unlocked_pets'):
                data['unlocked_pets'] = json.loads(data['unlocked_pets'])
            return data
        return None

async def create_game_user(user_id: int, username: str = None, first_name: str = None):
    """Создаёт нового игрока в таблице game_users."""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        await db.execute('''
            INSERT INTO game_users (
                user_id, username, first_name, food, gems, click_power,
                click_upgrade_level, stamina, max_stamina, stamina_regen_rate,
                regen_upgrade_level, max_stamina_upgrade_level, total_clicks,
                unlocked_pets, selected_pet, friends_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, username, first_name,
            50, 100, 1.0,
            0, 100, 100, 1.0,
            0, 0, 0,
            json.dumps(['dog', 'cat', 'rabbit']), 'dog', 0, now
        ))
        await db.commit()
        return await get_game_user(user_id)

async def update_game_user(user_id: int, **kwargs):
    """Обновляет указанные поля игрока в таблице game_users."""
    if not kwargs:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        set_clause = ', '.join(f"{key} = ?" for key in kwargs)
        values = list(kwargs.values())
        values.append(user_id)
        await db.execute(f"UPDATE game_users SET {set_clause} WHERE user_id = ?", values)
        await db.commit()