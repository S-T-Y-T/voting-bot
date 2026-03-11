import json
import csv
import io
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import config

bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)

DB_FILE = "votes.json"
user_choice = {}

# ---------------- JSON DATABASE ----------------
async def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)

async def save_vote(user_id, phone, vote):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.append({
        "id": user_id,
        "phone": phone,
        "vote": vote
    })

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def user_voted(user_id):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return any(item["id"] == user_id for item in data)

async def export_votes():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def get_votes():
    # Подсчет голосов по названиям участков
    votes_count = {name: 0 for name in config.OPTIONS}
    data = await export_votes()
    for item in data:
        if item["vote"] in votes_count:
            votes_count[item["vote"]] += 1
    return votes_count  # {'Участок A': 3, 'Участок B': 5, ...}

# ---------------- BOT LOGIC ----------------
async def check_sub(user_id):
    for channel in config.CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def vote_keyboard(votes_count):
    kb = InlineKeyboardMarkup()
    for name, count in votes_count.items():
        kb.add(
            InlineKeyboardButton(
                text=f"{name} ({count})",
                callback_data=f"vote_{name}"
            )
        )
    return kb

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    votes_count = await get_votes()
    await message.answer(
        "Выберите участок",
        reply_markup=vote_keyboard(votes_count)
    )

@dp.callback_query_handler(lambda c: c.data.startswith("vote"))
async def vote(call: types.CallbackQuery):

    option = call.data.split("_", 1)[1]  # название участка
    voted = await user_voted(call.from_user.id)

    if voted:
        await call.message.answer("Вы уже голосовали")
        return

    sub = await check_sub(call.from_user.id)
    if not sub:
        kb = InlineKeyboardMarkup()
        for ch in config.CHANNELS:
            kb.add(InlineKeyboardButton("Подписаться", url=f"https://t.me/{ch[1:]}"))
        kb.add(InlineKeyboardButton("Проверить подписку", callback_data="check_sub"))
        await call.message.answer(
            "Подпишитесь на каналы",
            reply_markup=kb
        )
        user_choice[call.from_user.id] = option
        return

    user_choice[call.from_user.id] = option
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Отправить номер", request_contact=True))
    await call.message.answer(
        "Отправьте номер телефона",
        reply_markup=kb
    )

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check(call: types.CallbackQuery):
    sub = await check_sub(call.from_user.id)
    if sub:
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add(KeyboardButton("Отправить номер", request_contact=True))
        await call.message.answer(
            "Теперь отправьте номер",
            reply_markup=kb
        )
    else:
        await call.answer("Вы не подписаны", show_alert=True)

@dp.message_handler(content_types=["contact"])
async def contact(message: types.Message):
    user = message.from_user.id
    if user not in user_choice:
        return
    phone = message.contact.phone_number
    option = user_choice[user]
    await save_vote(user, phone, option)
    await message.answer("Ваш голос принят")

# ---------------- ADMIN PANEL ----------------
@dp.message_handler(commands=["admin"])
async def admin(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Скачать список голосов", callback_data="export"))
    await message.answer("Админ панель", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "export")
async def export(call: types.CallbackQuery):
    if call.from_user.id not in config.ADMINS:
        return

    rows = await export_votes()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["telegram_id", "phone", "vote"])
    for row in rows:
        writer.writerow([row["id"], row["phone"], row["vote"]])
    output.seek(0)

    await bot.send_document(
        call.from_user.id,
        types.InputFile(
            io.BytesIO(output.read().encode('utf-8')),
            filename="votes.csv"
        )
    )

# ---------------- STARTUP ----------------
async def on_startup(dp):
    await init_db()

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)