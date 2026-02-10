import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"
ADMINS = [5378186366]  # O'zingning telegram ID

# ===== DB =====
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE,
    created_at TEXT
)
""")
conn.commit()

# ===== BOT =====
bot = Bot(TOKEN)
dp = Dispatcher()

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Mijoz qo‘shish")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id

    if user_id in ADMINS:
        await message.answer("Salom ADMIN ✅", reply_markup=admin_menu)
        return

    if not message.contact:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)
        return

    phone = message.contact.phone_number

    cursor.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
    client = cursor.fetchone()

    if client:
        await message.answer("Xush kelibsiz! ✅ Sizga ruxsat berilgan.")
    else:
        await message.answer("❌ Sizga ruxsat yo‘q. Admin bilan bog‘laning.")

@dp.message(F.text == "➕ Mijoz qo‘shish")
async def add_client_prompt(message: Message):
    await message.answer("Mijoz telefon raqamini yozing:\nMasalan: +998901234567")

@dp.message(F.from_user.id.in_(ADMINS))
async def add_client_save(message: Message):
    phone = message.text.strip()

    if not phone.startswith("+"):
        await message.answer("❌ Telefon raqami + bilan boshlanishi kerak")
        return

    try:
        cursor.execute(
            "INSERT INTO clients (phone, created_at) VALUES (?, ?)",
            (phone, datetime.now().isoformat())
        )
        conn.commit()
        await message.answer(f"✅ Mijoz qo‘shildi: {phone}")
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Bu raqam allaqachon mavjud")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
