import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ContentType

# Инициализация бота и диспетчера
bot = Bot(token="9213429455:AAGrwSbJKc8utcFvIrXGwLXSZfYZIkf2Iuo")
dp = Dispatcher()


# --- РАБОТА С БАЗОЙ ДАННЫХ И ПЕРИОДАМИ ---
def get_current_periods():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # Опорная дата — суббота (00:00:00). Каждую субботу в 00:00 начинается новая неделя.
    week_anchor = datetime(2024, 1, 6, 0, 0, 0)
    week_index = int((now - week_anchor).total_seconds() // (7 * 24 * 3600))
    week_str = f"sat-week-{week_index}"

    return today_str, week_str


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            messages_count INTEGER DEFAULT 0,
            day_count INTEGER DEFAULT 0,
            week_count INTEGER DEFAULT 0,
            last_day TEXT,
            last_week TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    conn.commit()
    conn.close()


def add_message(user_id: int, chat_id: int, username: str):
    today_str, week_str = get_current_periods()
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT messages_count, day_count, week_count, last_day, last_week
        FROM stats WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("""
            INSERT INTO stats (user_id, chat_id, username, messages_count, day_count, week_count, last_day, last_week)
            VALUES (?, ?, ?, 1, 1, 1, ?, ?)
        """, (user_id, chat_id, username, today_str, week_str))
    else:
        total, day_c, week_c, last_day, last_week = row
        day_c = (day_c + 1) if last_day == today_str else 1
        week_c = (week_c + 1) if last_week == week_str else 1
        total += 1
        cursor.execute("""
            UPDATE stats
            SET username = ?, messages_count = ?, day_count = ?, week_count = ?, last_day = ?, last_week = ?
            WHERE user_id = ? AND chat_id = ?
        """, (username, total, day_c, week_c, today_str, week_str, user_id, chat_id))

    conn.commit()
    conn.close()


def get_user_stats(user_id: int, chat_id: int):
    today_str, week_str = get_current_periods()
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT day_count, week_count, messages_count, last_day, last_week
        FROM stats WHERE user_id = ? AND chat_id = ?
    """, (user_id, chat_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return 0, 0, 0

    day_c, week_c, total, last_day, last_week = row
    if last_day != today_str:
        day_c = 0
    if last_week != week_str:
        week_c = 0
    return day_c, week_c, total


# --- ХЕНДЛЕРЫ ---
@dp.message(Command("mystats"))
async def get_my_stats(message: Message):
    day_c, week_c, total = get_user_stats(message.from_user.id, message.chat.id)
    await message.reply(
        f"📊 Вы написали в этом чате сообщений: <b>{day_c} | {week_c} | {total}</b>\n"
        f"<i>(за день | за неделю | за всё время)</i>",
        parse_mode="HTML"
    )


@dp.message(F.content_type == ContentType.NEW_CHAT_MEMBERS)
async def welcome_new_members(message: Message):
    for member in message.new_chat_members:
        if member.id == message.bot.id:
            continue

        day_c, week_c, total = get_user_stats(member.id, message.chat.id)
        user_link = f"<a href='tg://user?id={member.id}'>{member.first_name}</a>"

        text = (
            f"📝 Приветствие:\n"
            f"Привет, {user_link}! Добро пожаловать в банду юный падаван ☺️\n\n"
            f"🗓 Коротко про {user_link}:\n"
            f"🗣 Сообщений в этом чате: {day_c} | {week_c} | {total}\n"
            f"🎭 Статус: Свежая кровь (пока без грехов)\n"
            f"📌 <a href='ССЫЛКА_НА_ПРАВИЛА'>Правила</a>"
        )
        await message.answer(text, parse_mode="HTML")


@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def count_messages(message: Message):
    if message.from_user.is_bot:
        return
    user_id = message.from_user.id
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    add_message(user_id, chat_id, username)


# --- ЗАПУСК ---
async def main():
    init_db()
    print("Бот запущен и считает сообщения!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())