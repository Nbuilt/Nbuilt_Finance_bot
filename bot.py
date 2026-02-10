# -*- coding: utf-8 -*-
print("🔥 FINANCE BOT FINAL STABLE 🔥")

import asyncio, sqlite3, secrets, datetime, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)

import matplotlib.pyplot as plt

# ================== SOZLAMALAR ==================
TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"
SUPER_ADMINS = [5378186366]  # o‘zingning Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== DATABASE ==================
db = sqlite3.connect("finance.db")
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, role TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, name TEXT)")
cur.execute("""CREATE TABLE IF NOT EXISTS payments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    amount INTEGER,
    date TEXT,
    confirmed INTEGER
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS expenses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    amount INTEGER,
    reason TEXT,
    date TEXT
)""")
db.commit()

for a in SUPER_ADMINS:
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (a, "admin"))
db.commit()

# ================== XOTIRA ==================
selected_client = {}      # admin_id -> client_id
invite_tokens = {}        # token -> True
pending_payments = {}    # pid -> (client_id, amount, admin_id)

# ================== MENYULAR ==================
def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mijoz qo‘shish (havola)")],
            [KeyboardButton(text="👥 Mijozlar ro‘yxati")],
            [KeyboardButton(text="💰 Balans")],
            [KeyboardButton(text="📤 Xarajat")],
            [KeyboardButton(text="📊 Hisobot")],
            [KeyboardButton(text="📈 Grafik")],
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
async def start(m: types.Message):
    uid = m.from_user.id
    name = m.from_user.full_name
    parts = m.text.split()

    if len(parts) > 1 and parts[1] in invite_tokens:
        cur.execute("INSERT OR IGNORE INTO clients VALUES (?,?)", (uid, name))
        cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, "client"))
        db.commit()
        await m.answer("✅ Siz MIJOZ sifatida ulandingiz", reply_markup=client_menu())
        return

    cur.execute("SELECT role FROM users WHERE id=?", (uid,))
    r = cur.fetchone()

    if r and r[0] == "admin":
        await m.answer("👋 Salom ADMIN", reply_markup=admin_menu())
    elif r and r[0] == "client":
        await m.answer("👋 Salom", reply_markup=client_menu())
    else:
        await m.answer("⛔ Ruxsat yo‘q")

# ================== MIJOZ HAVOLA ==================
@dp.message(lambda m: m.text == "➕ Mijoz qo‘shish (havola)")
async def add_client(m: types.Message):
    token = secrets.token_hex(6)
    invite_tokens[token] = True
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={token}"
    await m.answer(f"🔗 MIJOZ UCHUN HAVOLA:\n{link}")

# ================== MIJOZLAR ==================
@dp.message(lambda m: m.text == "👥 Mijozlar ro‘yxati")
async def list_clients(m: types.Message):
    cur.execute("SELECT id,name FROM clients")
    rows = cur.fetchall()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=n, callback_data=f"sel:{i}")]
            for i,n in rows
        ]
    )
    await m.answer("Mijozni tanlang:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("sel:"))
async def select(c: types.CallbackQuery):
    selected_client[c.from_user.id] = int(c.data.split(":")[1])
    await c.message.answer("✅ Mijoz tanlandi")
    await c.answer()

# ================== BALANS / XARAJAT / HISOBOT ==================
def get_balance(cid):
    cur.execute("SELECT SUM(amount) FROM payments WHERE client_id=? AND confirmed=1", (cid,))
    inc = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(amount) FROM expenses WHERE client_id=?", (cid,))
    exp = cur.fetchone()[0] or 0
    return inc - exp

@dp.message(lambda m: m.text == "💰 Balans")
async def admin_balance(m: types.Message):
    cid = selected_client.get(m.from_user.id)
    if not cid:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer(f"💰 Balans: {get_balance(cid)} so‘m")

@dp.message(lambda m: m.text == "📤 Xarajat")
async def add_expense(m: types.Message):
    if m.from_user.id not in selected_client:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer("Format: summa,sabab")

@dp.message(lambda m: "," in m.text)
async def save_expense(m: types.Message):
    if m.from_user.id not in selected_client:
        return
    amount, reason = m.text.split(",",1)
    cid = selected_client[m.from_user.id]
    cur.execute(
        "INSERT INTO expenses(client_id,amount,reason,date) VALUES (?,?,?,?)",
        (cid,int(amount),reason,datetime.datetime.now().isoformat())
    )
    db.commit()
    await m.answer("📤 Xarajat saqlandi")

@dp.message(lambda m: m.text == "📊 Hisobot")
async def admin_report(m: types.Message):
    cid = selected_client.get(m.from_user.id)
    if not cid:
        await m.answer("❗ Avval mijoz tanlang")
        return
    await m.answer(f"📊 Balans: {get_balance(cid)} so‘m")

# ================== GRAFIK ==================
@dp.message(lambda m: m.text == "📈 Grafik")
async def graph(m: types.Message):
    cid = selected_client.get(m.from_user.id)
    if not cid:
        await m.answer("❗ Avval mijoz tanlang")
        return

    cur.execute("SELECT date,amount FROM payments WHERE client_id=? AND confirmed=1", (cid,))
    inc = cur.fetchall()
    cur.execute("SELECT date,amount FROM expenses WHERE client_id=?", (cid,))
    exp = cur.fetchall()

    plt.figure()
    if inc:
        plt.plot([i[0][:10] for i in inc],[i[1] for i in inc],label="Kirim")
    if exp:
        plt.plot([e[0][:10] for e in exp],[e[1] for e in exp],label="Xarajat")
    plt.legend()
    fname="graph.png"
    plt.savefig(fname)
    plt.close()
    await m.answer_photo(FSInputFile(fname))
    os.remove(fname)

# ================== ADMIN QO‘SHISH ==================
@dp.message(lambda m: m.text == "➕ Admin qo‘shish")
async def add_admin(m: types.Message):
    await m.answer("Yangi admin TELEGRAM ID sini yoz")

@dp.message(lambda m: m.text.isdigit())
async def save_admin(m: types.Message):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (int(m.text),"admin"))
    db.commit()
    await m.answer("✅ Admin qo‘shildi")

# ================== MIJOZ TOMONI ==================
@dp.message(lambda m: m.text == "💰 Balansim")
async def my_balance(m: types.Message):
    await m.answer(f"💰 Balans: {get_balance(m.from_user.id)} so‘m")

@dp.message(lambda m: m.text == "📊 Hisobotim")
async def my_report(m: types.Message):
    await m.answer(f"📊 Balans: {get_balance(m.from_user.id)} so‘m")

# ================== MAIN ==================
async def main():
    print("BOT ISHLAYAPTI")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
