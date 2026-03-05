import aiosqlite
from datetime import datetime
import json

DB_PATH = "your_database.db"  # замени на свой путь

async def init_game_db():
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
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM game_users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

async def create_game_user(user_id: int, username: str, first_name: str):
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
    async with aiosqlite.connect(DB_PATH) as db:
        set_clause = ', '.join(f"{key} = ?" for key in kwargs)
        values = list(kwargs.values())
        values.append(user_id)
        await db.execute(f"UPDATE game_users SET {set_clause} WHERE user_id = ?", values)
        await db.commit()