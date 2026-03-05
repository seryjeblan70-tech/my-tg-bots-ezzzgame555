import asyncio
import json
import logging
import threading
import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from config import BOT_TOKEN, MINI_APP_URL, ADMIN_ID
from database import (
    init_db, create_user, get_user, update_energy,
    init_game_db, get_game_user, create_game_user, update_game_user
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
DB_PATH = "user_history.db"

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    ref_code = args[1] if len(args) > 1 else None
    referrer_id = int(ref_code.split('_')[1]) if ref_code and ref_code.startswith('ref_') else None

    # Создаём запись в таблице users (история, рефералы)
    await create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎮 Открыть питомца",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )]
        ]
    )
    await message.answer(
        "👋 Добро пожаловать в мир AI-питомца!\n"
        "Нажми кнопку ниже, чтобы начать игру.",
        reply_markup=keyboard
    )

# ==================== ОБРАБОТЧИК WEB_APP_DATA ====================
@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        user_id = message.from_user.id

        user = await get_game_user(user_id)
        if not user:
            user = await create_game_user(
                user_id,
                message.from_user.username,
                message.from_user.full_name
            )

        if action == 'get_user':
            await message.answer(json.dumps(user, ensure_ascii=False))

        elif action == 'click':
            power = data.get('power', 1)
            if user['stamina'] < 1:
                await message.answer("❌ Недостаточно энергии!")
                return
            new_gems = user['gems'] + power
            new_stamina = user['stamina'] - 1
            new_total_clicks = user['total_clicks'] + 1
            await update_game_user(
                user_id,
                gems=new_gems,
                stamina=new_stamina,
                total_clicks=new_total_clicks
            )
            await message.answer(
                f"💰 +{power} алмазов! Энергия: {new_stamina}/{user['max_stamina']}"
            )

        elif action == 'feed':
            if user['food'] < 1:
                await message.answer("❌ Нет еды!")
                return
            new_food = user['food'] - 1
            new_stamina = min(user['stamina'] + 10, user['max_stamina'])
            await update_game_user(user_id, food=new_food, stamina=new_stamina)
            await message.answer(
                f"🍖 Покормили! Энергия: {new_stamina}/{user['max_stamina']}, осталось еды: {new_food}"
            )

        elif action == 'play':
            if user['stamina'] < 20:
                await message.answer("❌ Недостаточно энергии!")
                return
            reward = 30
            new_stamina = user['stamina'] - 20
            new_gems = user['gems'] + reward
            await update_game_user(user_id, stamina=new_stamina, gems=new_gems)
            await message.answer(
                f"🎾 Поиграли! +{reward} алмазов. Энергия: {new_stamina}/{user['max_stamina']}"
            )

        # ... (остальные действия оставлены без изменений, они у тебя уже есть) ...
        # Сокращаю для экономии места, но в реальном коде вставь все остальные elif'ы из твоего файла.

        else:
            await message.answer("❓ Неизвестное действие")

    except json.JSONDecodeError:
        await message.answer("❌ Ошибка формата данных")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

# ==================== АДМИН-КОМАНДЫ ====================
@router.message(Command("add_gems"))
async def cmd_add_gems(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав админа.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /add_gems <user_id> <количество>")
        return

    try:
        user_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("❌ user_id и количество должны быть числами.")
        return

    user = await get_game_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден в игре.")
        return

    new_gems = user['gems'] + amount
    await update_game_user(user_id, gems=new_gems)
    await message.answer(f"✅ Пользователю {user_id} добавлено {amount} 💎. Теперь у него {new_gems} 💎.")

@router.message(Command("set_level"))
async def cmd_set_level(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У тебя нет прав админа.")
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /set_level <user_id> <уровень>")
        return

    try:
        user_id = int(args[1])
        target_level = int(args[2])
    except ValueError:
        await message.answer("❌ user_id и уровень должны быть числами.")
        return

    user = await get_game_user(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    if target_level <= 1:
        new_clicks = 0
    elif target_level <= 8:
        new_clicks = 200 * target_level - 100
    else:
        new_clicks = 300 * target_level - 900

    await update_game_user(user_id, total_clicks=new_clicks)
    await message.answer(f"✅ Уровень пользователя {user_id} установлен на {target_level}.")

# ==================== HTTP API ====================
http_app = FastAPI()

http_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@http_app.get("/user/{user_id}")
async def api_get_user(user_id: int):
    user = await get_game_user(user_id)
    if not user:
        user = await create_game_user(user_id, None, None)
    if isinstance(user.get('unlocked_pets'), str):
        user['unlocked_pets'] = json.loads(user['unlocked_pets'])
    return user

@http_app.post("/user/{user_id}")
async def api_update_user(user_id: int, data: dict):
    await update_game_user(user_id, **data)
    return {"status": "ok"}

@http_app.get("/health")
async def health():
    return {"status": "ok"}

@http_app.get("/test")
async def test():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        return {"status": "db ok"}
    except Exception as e:
        return {"error": str(e)}, 500

@http_app.get("/leaders")
async def api_get_leaders():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute('''
            SELECT user_id, first_name, gems 
            FROM game_users 
            ORDER BY gems DESC 
            LIMIT 10
        ''')
        rows = await cursor.fetchall()
        leaders = []
        for row in rows:
            data = dict(row)
            # Если нет имени, используем user_id
            if not data.get('first_name'):
                data['name'] = f"User {data['user_id']}"
            else:
                data['name'] = data['first_name']
            leaders.append(data)
        return leaders

def run_http():
    uvicorn.run(http_app, host="0.0.0.0", port=8000, log_level="info")

threading.Thread(target=run_http, daemon=True).start()
print("✅ HTTP-сервер запущен на порту 8000")

# ==================== ОСНОВНОЙ ЗАПУСК ====================
async def main():
    await init_db()
    await init_game_db()
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())


