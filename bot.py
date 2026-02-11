import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"

bot = Bot(TOKEN)
dp = Dispatcher()

db = sqlite3.connect("finance.db")
cur = db.cursor()

# ================= DATABASE =================

cur.execute("""
CREATE TABLE IF NOT EXISTS admins(
    phone TEXT,
    admin_id TEXT UNIQUE,
    telegram_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS clients(
    phone TEXT,
    client_id TEXT UNIQUE,
    telegram_id INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments(
    client_id TEXT,
    amount INTEGER,
    date TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    client_id TEXT,
    product TEXT,
    amount INTEGER,
    date TEXT
)
""")

db.commit()

selected_client = {}

# ================= MENUS =================

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="1️⃣ Mijozlar ro‘yxati")],
            [KeyboardButton(text="2️⃣ Admin qo‘shish")],
            [KeyboardButton(text="3️⃣ Mijoz qo‘shish")],
            [KeyboardButton(text="4️⃣ Hisobotlar markazi")],
            [KeyboardButton(text="5️⃣ Grafiklar")]
        ],
        resize_keyboard=True
    )

def client_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Pul yozish")],
            [KeyboardButton(text="📦 Xarajat yozish")],
            [KeyboardButton(text="📄 Hisobot")],
            [KeyboardButton(text="📈 Grafik")]
        ],
        resize_keyboard=True
    )

# ================= START =================

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Xush kelibsiz ADMIN", reply_markup=admin_menu())

# ================= MIJOZLAR =================

@dp.message(F.text == "1️⃣ Mijozlar ro‘yxati")
async def clients_list(msg: types.Message):
    cur.execute("SELECT client_id FROM clients")
    rows = cur.fetchall()
    if not rows:
        await msg.answer("Mijoz yo‘q")
        return
    text = "Mijozlar:\n"
    for r in rows:
        text += f"{r[0]}\n"
    await msg.answer(text + "\nMijoz ID yozing:")

@dp.message()
async def handle_text(msg: types.Message):
    text = msg.text.strip()

    # Mijoz tanlash
    cur.execute("SELECT client_id FROM clients WHERE client_id=?", (text,))
    if cur.fetchone():
        selected_client[msg.from_user.id] = text
        await msg.answer(f"Tanlandi: {text}", reply_markup=client_menu())
        return

    # Pul yozish
    if text == "💰 Pul yozish":
        await msg.answer("Summani yozing (faqat raqam):")
        selected_client[msg.from_user.id+"_mode"] = "payment"
        return

    if selected_client.get(msg.from_user.id+"_mode") == "payment":
        cid = selected_client.get(msg.from_user.id)
        amount = int(text)
        date = datetime.now().strftime("%d.%m.%Y")
        cur.execute("INSERT INTO payments VALUES (?,?,?)", (cid, amount, date))
        db.commit()
        await msg.answer("✅ Pul yozildi")
        selected_client.pop(msg.from_user.id+"_mode")
        return

    # Xarajat
    if text == "📦 Xarajat yozish":
        await msg.answer("Masalan: 50 g‘isht 150000")
        selected_client[msg.from_user.id+"_mode"] = "expense"
        return

    if selected_client.get(msg.from_user.id+"_mode") == "expense":
        cid = selected_client.get(msg.from_user.id)
        parts = text.split()
        amount = int(parts[-1])
        product = " ".join(parts[:-1])
        date = datetime.now().strftime("%d.%m.%Y")
        cur.execute("INSERT INTO expenses VALUES (?,?,?,?)", (cid, product, amount, date))
        db.commit()
        await msg.answer("✅ Xarajat yozildi")
        selected_client.pop(msg.from_user.id+"_mode")
        return

    # Hisobot
    if text == "📄 Hisobot":
        cid = selected_client.get(msg.from_user.id)
        cur.execute("SELECT SUM(amount) FROM payments WHERE client_id=?", (cid,))
        inc = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(amount) FROM expenses WHERE client_id=?", (cid,))
        exp = cur.fetchone()[0] or 0
        bal = inc - exp
        await msg.answer(f"Kirim: {inc}\nXarajat: {exp}\nQoldiq: {bal}")
        return

    # Grafik
    if text == "📈 Grafik":
        cid = selected_client.get(msg.from_user.id)
        cur.execute("SELECT SUM(amount) FROM payments WHERE client_id=?", (cid,))
        inc = cur.fetchone()[0] or 0
        cur.execute("SELECT SUM(amount) FROM expenses WHERE client_id=?", (cid,))
        exp = cur.fetchone()[0] or 0
        plt.bar(["Kirim", "Xarajat"], [inc, exp])
        img = "grafik.png"
        plt.savefig(img)
        plt.close()
        await msg.answer_photo(FSInputFile(img))
        return

    # PDF
    if text == "5️⃣ Grafiklar":
        await msg.answer("Grafik mijoz ichidan olinadi")
        return

    if text == "4️⃣ Hisobotlar markazi":
        await msg.answer("Umumiy hisobot keyingi bosqichda kengaytiriladi")
        return

# ================= RUN =================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
