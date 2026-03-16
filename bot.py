import json
import csv
import io
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config

BOT_USERNAME = getattr(config, 'BOT_USERNAME', 'qoshtepaNeobot')  # Замените на имя вашего бота

bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

DB_FILE = "votes.json"
CHANNEL_MESSAGES_FILE = "channel_messages.json"
user_choice = {}

# ---------------- JSON DATABASE ----------------
async def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    if not os.path.exists(CHANNEL_MESSAGES_FILE):
        with open(CHANNEL_MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

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
    return votes_count

async def save_channel_message(channel, message_id):
    with open(CHANNEL_MESSAGES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    data[channel] = message_id
    with open(CHANNEL_MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def get_channel_messages():
    with open(CHANNEL_MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def update_channel_votes():
    votes_count = await get_votes()
    channel_messages = await get_channel_messages()
    caption = ("🏆 Qoʻshtepa tumanida eng namunali «Mahalla yettiligi»ni aniqlaymiz!\n\n"
               "Hurmatli fuqarolar!\n\n"
               "Qoʻshtepa tumanidagi barcha mahallalar oʻrtasida «Mahalla yettiligi» faoliyati samaradorligini aniqlash maqsadida ochiq onlayn soʻrovnoma oʻtkazilmoqda.\n\n"
               "❓ Sizningcha, qaysi mahallaning «Mahalla yettiligi» jamoasi eng faol, tashabbuskor va samarali ishlamoqda?\n\n"
               "🗳 Oʻzingiz munosib deb bilgan mahalla nomi uchun ovoz bering.\n\n"
               "📅 Ovoz berish muddati: 21-mart kuni soat 23:59 ga qadar.\n\n"
               "🏅 Soʻrovnoma natijalari 22-mart – «Mahalla tizimi xodimlari kuni» munosabati bilan rasman eʼlon qilinadi.\n\n"
               "Sizning ovozingiz – eng adolatli baho!\n"
               "Faol ishtirok eting va eng munosib jamoani qoʻllab-quvvatlang!\n\n"
               "#soʻrovnoma")
    
    for channel, message_id in channel_messages.items():
        try:
            await bot.edit_message_caption(
                chat_id=channel,
                message_id=message_id,
                caption=caption,
                reply_markup=channel_keyboard(votes_count)
            )
        except Exception as e:
            print(f"Failed to update {channel}: {e}") 

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

def vote_keyboard(votes_count, add_share_button=False):
    buttons = []
    for name, count in votes_count.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{name} ({count})",
                callback_data=f"vote_{name}"
            )
        ])
    
    if add_share_button:
        buttons.append([InlineKeyboardButton(
            text=" Ovoz berish",
            url=f"https://t.me/{BOT_USERNAME}"
        )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def channel_keyboard(votes_count):
    """Клавиатура для канала - все кнопки ведут в бот"""
    buttons = []
    for name, count in votes_count.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{name} ({count})",
                url=f"https://t.me/{BOT_USERNAME}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(
        text="🗳 Ovoz berish",
        url=f"https://t.me/{BOT_USERNAME}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start(message: types.Message):
    votes_count = await get_votes()
    await message.answer(
        "Mahalla yettiligini tanlang",
        reply_markup=vote_keyboard(votes_count)
    )

@dp.callback_query(F.data.startswith("vote"))
async def vote(call: types.CallbackQuery):

    option = call.data.split("_", 1)[1]  # название участка
    voted = await user_voted(call.from_user.id)

    if voted:
        await call.message.answer("Siz allaqachon ovoz bergansiz")
        return

    sub = await check_sub(call.from_user.id)
    if not sub:
        buttons = []
        for ch in config.CHANNELS:
            buttons.append([InlineKeyboardButton(text="Obuna bo'lish", url=f"https://t.me/{ch[1:]}")])
        buttons.append([InlineKeyboardButton(text="Obunani tekshirish", callback_data="check_sub")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await call.message.answer(
            "Kanallarga obuna bo'ling",
            reply_markup=kb
        )
        user_choice[call.from_user.id] = option
        return

    user_choice[call.from_user.id] = option
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Telefon raqamni jo'natish", request_contact=True)]],
        resize_keyboard=True
    )
    await call.message.answer(
        "Iltimos telefon raqamingizni jo'nating",
        reply_markup=kb
    )

@dp.callback_query(F.data == "check_sub")
async def check(call: types.CallbackQuery):
    sub = await check_sub(call.from_user.id)
    if sub:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Telefon raqamni jo'natish", request_contact=True)]],
            resize_keyboard=True
        )
        await call.message.answer(
            "Endi telefon raqamni jo'nating",
            reply_markup=kb
        )
    else:
        try:
            await call.answer("Barcha kanallarga obuna bo'lmadingiz", show_alert=True)
        except:
            pass

@dp.message(F.contact)
async def contact(message: types.Message):
    user = message.from_user.id
    if user not in user_choice:
        return
    
    # Проверяем, не голосовал ли уже
    voted = await user_voted(user)
    if voted:
        await message.answer("Siz allaqachon ovoz bergansiz!")
        return
    
    phone = message.contact.phone_number
    option = user_choice[user]
    await save_vote(user, phone, option)
    await update_channel_votes()
    await message.answer("Ovozingiz qabul qilindi")

# ---------------- ADMIN PANEL ----------------
@dp.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id not in config.ADMINS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ovozlar ro'yxatini tortib olish", callback_data="export")],
        [InlineKeyboardButton(text="Ulash imkoniyati", callback_data="forward")]
    ])
    await message.answer("Nazoratchi akani paneli", reply_markup=kb)

@dp.callback_query(F.data == "forward")
async def forward_options(call: types.CallbackQuery):
    if call.from_user.id not in config.ADMINS:
        return
    
    votes_count = await get_votes()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Ulash", callback_data="do_forward")]])
    await call.message.answer(
        "Mahalla yettiligini tanlang",
        reply_markup=vote_keyboard(votes_count)
    )
    await call.message.answer("Ushbu ovoz berishni kanallarga ulash:", reply_markup=kb)

@dp.callback_query(F.data == "do_forward")
async def do_forward(call: types.CallbackQuery):
    if call.from_user.id not in config.ADMINS:
        return
    
    votes_count = await get_votes()
    forward_message = await call.message.answer(
            "🏆 Qoʻshtepa tumanida eng namunali «Mahalla yettiligi»ni aniqlaymiz!\n\n"
            "Hurmatli fuqarolar!\n\n"
            "Qoʻshtepa tumanidagi barcha mahallalar oʻrtasida «Mahalla yettiligi» faoliyati samaradorligini aniqlash maqsadida ochiq onlayn soʻrovnoma oʻtkazilmoqda.\n\n"
            "❓ Sizningcha, qaysi mahallaning «Mahalla yettiligi» jamoasi eng faol, tashabbuskor va samarali ishlamoqda?\n\n"
            "🗳 Oʻzingiz munosib deb bilgan mahalla nomi uchun ovoz bering.\n\n"
            "📅 Ovoz berish muddati: 21-mart kuni soat 23:59 ga qadar.\n\n"
            "🏅 Soʻrovnoma natijalari 22-mart – «Mahalla tizimi xodimlari kuni» munosabati bilan rasman eʼlon qilinadi.\n\n"
            "Sizning ovozingiz – eng adolatli baho!\n"
            "Faol ishtirok eting va eng munosib jamoani qoʻllab-quvvatlang!\n\n"
            "#soʻrovnoma",
        reply_markup=vote_keyboard(votes_count, add_share_button=True)
    )
    
    # Создаем кнопки для пересылки в каналы
    buttons = []
    for channel in config.CHANNELS:
        buttons.append([InlineKeyboardButton(text=f"Ulash {channel}", callback_data=f"send_to_{channel}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer("Qaysi kanalga ulashmoqchisiz:", reply_markup=kb)
    try:
        await call.answer("Xabar tayyor! Endi uni kerakli kanallarga ulashingiz mumkin.", show_alert=True)
    except:
        pass  # Игнорируем ошибку, если callback устарел

@dp.callback_query(F.data.startswith("send_to_"))
async def send_to_channel(call: types.CallbackQuery):
    if call.from_user.id not in config.ADMINS:
        return
    
    channel = call.data.replace("send_to_", "")
    votes_count = await get_votes()
    
    try:
        with open("1.jpg", "rb") as photo:
            sent_message = await bot.send_photo(
                channel,
                photo=types.BufferedInputFile(photo.read(), filename="1.jpg"),
                caption="🏆 Qoʻshtepa tumanida eng namunali «Mahalla yettiligi»ni aniqlaymiz!\n\n"
                "Hurmatli fuqarolar!\n\n"
                "Qoʻshtepa tumanidagi barcha mahallalar oʻrtasida «Mahalla yettiligi» faoliyati samaradorligini aniqlash maqsadida ochiq onlayn soʻrovnoma oʻtkazilmoqda.\n\n"
                "❓ Sizningcha, qaysi mahallaning «Mahalla yettiligi» jamoasi eng faol, tashabbuskor va samarali ishlamoqda?\n\n"
                "🗳 Oʻzingiz munosib deb bilgan mahalla nomi uchun ovoz bering.\n\n"
                "📅 Ovoz berish muddati: 21-mart kuni soat 23:59 ga qadar.\n\n"
                "🏅 Soʻrovnoma natijalari 22-mart – «Mahalla tizimi xodimlari kuni» munosabati bilan rasman eʼlon qilinadi.\n\n"
                "Sizning ovozingiz – eng adolatli baho!\n"
                "Faol ishtirok eting va eng munosib jamoani qoʻllab-quvvatlang!\n\n"
                "#soʻrovnoma",
                reply_markup=channel_keyboard(votes_count)
            )
        await save_channel_message(channel, sent_message.message_id)
        try:
            await call.answer(f"Xabar {channel} kanaliga muvaffaqiyatli yuborildi!", show_alert=True)
        except:
            pass
    except Exception as e:
        try:
            await call.answer(f"Xatolik: {str(e)}", show_alert=True)
        except:
            pass

@dp.callback_query(F.data == "export")
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
        types.BufferedInputFile(
            output.read().encode('utf-8'),
            filename="votes.csv"
        )
    )

# ---------------- STARTUP ----------------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())