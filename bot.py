# -*- coding: utf-8 -*-
print("🔥 FINANCE BOT FINAL | PHONE + AUTO START 🔥")

import asyncio
import sqlite3
import secrets
import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ================== SOZLAMALAR ==================
TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"
SUPER_ADMINS = [5378186366]  # admin telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== DATABASE ==================
db = sqlite3.connect("finance.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    telegram_id INTEGER PRIMARY KEY,
    role TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS clients(
    telegram_id INTEGER UNIQUE,
    phone TEXT UNIQUE,
    name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_phone TEXT,
    amount INTEGER,
    date TEXT,
    confirmed INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_phone TEXT,
    amount INTEGER,
    reason TEXT,
    date TEXT
)
""")

db.commit()

for aid in SUPER_ADMINS:
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (aid, "admin")
    )
db.commit()

# ================== XOTIRA ==================
waiting_phone = set()          # admin telefon kiritayapti
invite_tokens = {}             # token -> phone
selected_client = {}           # admin_id -> phone

# ================== MENYULAR ==================
def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mijoz qo‘shish")],
            [KeyboardButton(text="👥 Mijozlar ro‘yxati")],
            [KeyboardButton(text="💰 Balans")],
            [KeyboardButton(text="📤 Xarajat")],
            [KeyboardButton(text="📊 Hisobot")],
            [KeyboardButton(text="➕ Admin qo‘shish")]
        ],
        resize_keyboard=True
    )

def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Balansim")],
            [KeyboardButton(text="📤 Xarajatlarim")],
            [KeyboardButton(text="📊 Hisobotim")]
        ],
        resize_keyboard=True
    )

# ================== START ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    uid = message.from_user.id
    name = message.from_user.full_name
    text = message.text.strip()

    # 1️⃣ HAVOLA ORQALI KIRGAN MIJOZ
    if text.startswith("/start "):
        token = text.split(" ", 1)[1]

        if token in invite_tokens:
            phone = invite_tokens[token]

            cur.execute(
                "UPDATE clients SET telegram_id=?, name=? WHERE phone=?",
                (uid, name, phone)
            )
            cur.execute(
                "INSERT OR IGNORE INTO users VALUES (?,?)",
                (uid, "client")
            )
            db.commit()

            invite_tokens.pop(token, None)

            await message.answer(
                "✅ Siz mijoz sifatida ulandingiz",
                reply_markup=client_menu()
            )
            return

    # 2️⃣ AGAR TELEGRAM ID HALI YO‘Q, LEKIN BITTA KUTILAYOTGAN TELEFON BO‘LSA
    cur.execute(
        "SELECT phone FROM clients WHERE telegram_id IS NULL"
    )
    rows = cur.fetchall()

    if len(rows) == 1:
        phone = rows[0][0]

        cur.execute(
            "UPDATE clients SET telegram_id=?, name=? WHERE phone=?",
            (uid, name, phone)
        )
        cur.execute(
            "INSERT OR IGNORE INTO users VALUES (?,?)",
            (uid, "client")
        )
        db.commit()

        await message.answer(
            "✅ Siz mijoz sifatida avtomatik ulandingiz",
            reply_markup=client_menu()
        )
        return

    # 3️⃣ OLDINDAN BOR MIJOZ
    cur.execute(
        "SELECT phone FROM clients WHERE telegram_id=?",
        (uid,)
    )
    if cur.fetchone():
        await message.answer(
            "👋 Salom, siz mijoz sifatida tizimdasiz",
            reply_markup=client_menu()
        )
        return

    # 4️⃣ ADMIN
    cur.execute("SELECT role FROM users WHERE telegram_id=?", (uid,))
    row = cur.fetchone()

    if row and row[0] == "admin":
        await message.answer("👋 Salom ADMIN", reply_markup=admin_menu())
        return

    await message.answer(
        "⛔ Sizda ruxsat yo‘q.\n"
        "Admin bergan havola yoki telefon orqali kiring."
    )

# ================== MIJOZ QO‘SHISH ==================
@dp.message(lambda m: m.text == "➕ Mijoz qo‘shish")
async def add_client_start(m: types.Message):
    if m.from_user.id not in SUPER_ADMINS:
        return
    waiting_phone.add(m.from_user.id)
    await m.answer(
        "📞 Mijoz telefon raqamini kiriting\n"
        "Masalan: +998901234567"
    )

@dp.message(lambda m: m.from_user.id in waiting_phone and m.text.startswith("+"))
async def save_phone(m: types.Message):
    phone = m.text.strip()
    waiting_phone.remove(m.from_user.id)

    cur.execute(
        "INSERT OR IGNORE INTO clients (phone) VALUES (?)",
        (phone,)
    )
    db.commit()

    token = secrets.token_hex(6)
    invite_tokens[token] = phone

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={token}"

    await m.answer(
        "✅ Mijoz qo‘shildi.\n\n"
        f"📞 Telefon: {phone}\n\n"
        "Agar Telegram bo‘lmasa — shu havolani yuboring:\n"
        f"{link}"
    )

# ================== MIJOZLAR RO‘YXATI ==================
@dp.message(lambda m: m.text == "👥 Mijozlar ro‘yxati")
async def list_clients(m: types.Message):
    cur.execute("SELECT phone FROM clients")
    rows = cur.fetchall()

    if not rows:
        await m.answer("Hozircha mijoz yo‘q")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=phone, callback_data=f"sel:{phone}")]
            for (phone,) in rows
        ]
    )
    await m.answer("Mijozni tanlang:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("sel:"))
async def select_client_cb(c: types.CallbackQuery):
    phone = c.data.split(":", 1)[1]
    selected_client[c.from_user.id] = phone
    await c.message.answer(f"✅ Mijoz tanlandi: {phone}")
    await c.answer()

# ================== BALANS / XARAJAT / HISOBOT ==================
def get_balance(phone):
    cur.execute(
        "SELECT SUM(amount) FROM payments WHERE client_phone=? AND confirmed=1",
        (phone,)
    )
    inc = cur.fetchone()[0] or 0
    cur.execute(
        "SELECT SUM(amount) FROM expenses WHERE client_phone=?",
        (phone,)
    )
    exp = cur.fetchone()[0] or 0
    return inc - exp

@dp.message(lambda m: m.text == "💰 Balans")
async def admin_balance(m: types.Message):
    phone = selected_client.get(m.from_user.id)
    if not phone:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer(f"💰 Balans ({phone}): {get_balance(phone)} so‘m")

@dp.message(lambda m: m.text == "📤 Xarajat")
async def add_expense(m: types.Message):
    phone = selected_client.get(m.from_user.id)
    if not phone:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer("Format: summa,sabab\nMasalan: 50000,transport")

@dp.message(lambda m: "," in m.text)
async def save_expense(m: types.Message):
    phone = selected_client.get(m.from_user.id)
    if not phone:
        return
    amount, reason = m.text.split(",", 1)

    cur.execute(
        "INSERT INTO expenses VALUES (NULL,?,?,?,?)",
        (phone, int(amount), reason.strip(), datetime.datetime.now().isoformat())
    )
    db.commit()

    await m.answer("📤 Xarajat saqlandi")

@dp.message(lambda m: m.text == "📊 Hisobot")
async def admin_report(m: types.Message):
    phone = selected_client.get(m.from_user.id)
    if not phone:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer(f"📊 Balans ({phone}): {get_balance(phone)} so‘m")

# ================== MIJOZ TOMONI ==================
@dp.message(lambda m: m.text == "💰 Balansim")
async def my_balance(m: types.Message):
    cur.execute(
        "SELECT phone FROM clients WHERE telegram_id=?",
        (m.from_user.id,)
    )
    row = cur.fetchone()
    if row:
        await m.answer(f"💰 Balansingiz: {get_balance(row[0])} so‘m")

@dp.message(lambda m: m.text == "📊 Hisobotim")
async def my_report(m: types.Message):
    cur.execute(
        "SELECT phone FROM clients WHERE telegram_id=?",
        (m.from_user.id,)
    )
    row = cur.fetchone()
    if row:
        await m.answer(f"📊 Balansingiz: {get_balance(row[0])} so‘m")

# ================== ADMIN QO‘SHISH ==================
@dp.message(lambda m: m.text == "➕ Admin qo‘shish")
async def add_admin(m: types.Message):
    await m.answer("Yangi admin TELEGRAM ID sini yozing")

@dp.message(lambda m: m.text.isdigit())
async def save_admin(m: types.Message):
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES (?,?)",
        (int(m.text), "admin")
    )
    db.commit()
    await m.answer("✅ Admin qo‘shildi")

# ================== MAIN ==================
async def main():
    print("BOT ISHLAYAPTI")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
