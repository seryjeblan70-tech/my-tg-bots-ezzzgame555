import asyncio
import json
import logging
import aiosqlite
import uvicorn
import threading
import asyncio
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from config import BOT_TOKEN, MINI_APP_URL, ADMIN_ID
from database import init_game_db, get_game_user, create_game_user, update_game_user

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
http_app = FastAPI()


@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    ref_code = args[1] if len(args) > 1 else None
    referrer_id = int(ref_code.split('_')[1]) if ref_code and ref_code.startswith('ref_') else None
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

@router.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get('action')
        user_id = message.from_user.id

        # Получаем пользователя (или создаём, если нет)
        user = await get_game_user(user_id)
        if not user:
            user = await create_game_user(
                user_id,
                message.from_user.username,
                message.from_user.full_name
            )

        if action == 'get_user':
            # отправляем все данные пользователя
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

        elif action == 'buyFood':
            amount = data.get('amount')
            price = data.get('price')
            if user['gems'] < price:
                await message.answer("❌ Недостаточно алмазов!")
                return
            new_gems = user['gems'] - price
            new_food = min(user['food'] + amount, 100)  # maxFood
            await update_game_user(user_id, gems=new_gems, food=new_food)
            await message.answer(f"🍖 Куплено {amount} еды. Осталось алмазов: {new_gems}")

        elif action == 'buyClickUpgrade':
            level = user['click_upgrade_level']
            cost = 10 + level * 5
            if user['gems'] < cost:
                await message.answer("❌ Недостаточно алмазов!")
                return
            new_gems = user['gems'] - cost
            new_click_power = user['click_power'] + 0.2
            new_level = level + 1
            await update_game_user(
                user_id,
                gems=new_gems,
                click_power=new_click_power,
                click_upgrade_level=new_level
            )
            await message.answer(
                f"⚡ Сила клика увеличена до {new_click_power:.1f}"
            )

        elif action == 'buyRegenUpgrade':
            level = user['regen_upgrade_level']
            cost = 15 + level * 8
            if user['gems'] < cost:
                await message.answer("❌ Недостаточно алмазов!")
                return
            new_gems = user['gems'] - cost
            new_regen = user['stamina_regen_rate'] + 0.5
            new_level = level + 1
            await update_game_user(
                user_id,
                gems=new_gems,
                stamina_regen_rate=new_regen,
                regen_upgrade_level=new_level
            )
            await message.answer(
                f"⚡ Скорость регенерации увеличена до {new_regen:.1f} ед/сек"
            )

        elif action == 'buyMaxStaminaUpgrade':
            level = user['max_stamina_upgrade_level']
            cost = 30 + level * 10
            if user['gems'] < cost:
                await message.answer("❌ Недостаточно алмазов!")
                return
            new_gems = user['gems'] - cost
            new_max_stamina = user['max_stamina'] + 20
            new_stamina = user['stamina'] + 20
            new_level = level + 1
            await update_game_user(
                user_id,
                gems=new_gems,
                max_stamina=new_max_stamina,
                stamina=new_stamina,
                max_stamina_upgrade_level=new_level
            )
            await message.answer(
                f"📈 Макс. энергия увеличена до {new_max_stamina}"
            )

        elif action == 'selectPet':
            pet_id = data.get('pet_id')
            unlocked = json.loads(user['unlocked_pets'])
            if pet_id in unlocked:
                await update_game_user(user_id, selected_pet=pet_id)
                await message.answer(f"✅ Питомец выбран: {pet_id}")
            else:
                await message.answer("❌ Этот питомец ещё не открыт!")

        elif action == 'inviteFriend':
            new_friends = user['friends_count'] + 1
            await update_game_user(user_id, friends_count=new_friends)
            await message.answer(f"👥 У вас теперь {new_friends} друзей!")

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

    # Проверяем, есть ли пользователь в игровой таблице
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

    # Пересчитываем total_clicks, чтобы получить нужный уровень
    # Уровень 1 требует 0 кликов, уровень 2 – 100, уровень 3 – 300, уровень 4 – 500 и т.д.
    if target_level <= 1:
        new_clicks = 0
    elif target_level <= 8:
        new_clicks = 200 * target_level - 100
    else:
        new_clicks = 300 * target_level - 900

    await update_game_user(user_id, total_clicks=new_clicks)
    await message.answer(f"✅ Уровень пользователя {user_id} установлен на {target_level}.")

# =======================================================

@http_app.get("/user/{user_id}")
async def api_get_user(user_id: int):
    """Получить данные пользователя. Если нет — создать."""
    # Используем асинхронную функцию из database, но FastAPI ожидает синхронность?
    # На самом деле FastAPI отлично работает с async, поэтому просто вызываем.
    user = await get_game_user(user_id)
    if not user:
        # Создаём без username и first_name, они не критичны
        user = await create_game_user(user_id, None, None)
    # Преобразуем unlocked_pets обратно в список (если ещё не)
    if isinstance(user.get('unlocked_pets'), str):
        user['unlocked_pets'] = json.loads(user['unlocked_pets'])
    return user

@http_app.post("/user/{user_id}")
async def api_update_user(user_id: int, data: dict):
    """Обновить данные пользователя."""
    await update_game_user(user_id, **data)
    return {"status": "ok"}

@http_app.get("/health")
async def health():
    return {"status": "ok"}

def run_http():
    """Запускает HTTP-сервер в отдельном потоке."""
    uvicorn.run(http_app, host="0.0.0.0", port=8000, log_level="info")

# Запускаем HTTP-сервер в фоновом потоке (daemon=True, чтобы он завершился при выходе)
threading.Thread(target=run_http, daemon=True).start()
print("✅ HTTP-сервер запущен на порту 8000")






async def main():
    await init_game_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
