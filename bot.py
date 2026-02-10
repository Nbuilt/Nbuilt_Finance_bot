import asyncio
import sqlite3
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"
SUPER_ADMIN = 5378186366
DB = "finance.db"

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= DB =================
conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS admins (phone TEXT UNIQUE)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE,
    telegram_id INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    client_id INTEGER,
    amount INTEGER,
    date TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    client_id INTEGER,
    title TEXT,
    amount INTEGER,
    date TEXT
)
""")
conn.commit()

# SUPER ADMIN
cursor.execute("INSERT OR IGNORE INTO admins VALUES (?)", (str(SUPER_ADMIN),))
conn.commit()

# ================= STATES =================
class AddClient(State): pass
class AddAdmin(State): pass
class AddPayment(State): pass
class AddExpense(State): pass

selected_client = {}

# ================= MENUS =================
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Mijozlar ro'yhati")],
        [KeyboardButton(text="➕ Mijoz qo‘shish")],
        [KeyboardButton(text="➕ Admin qo‘shish")]
    ],
    resize_keyboard=True
)

client_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Pul yozish")],
        [KeyboardButton(text="📦 Xarajat yozish")],
        [KeyboardButton(text="📊 Hisobot")]
    ],
    resize_keyboard=True
)

# ================= HELPERS =================
def is_admin(uid):
    cursor.execute("SELECT 1 FROM admins WHERE phone=?", (str(uid),))
    return cursor.fetchone()

# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):
    if is_admin(msg.from_user.id):
        await msg.answer("Xush kelibsiz ADMIN", reply_markup=admin_menu)
    else:
        await msg.answer("Siz admin emassiz")

# ================= CLIENT LIST =================
@dp.message(F.text == "👥 Mijozlar ro'yhati")
async def list_clients(msg: Message):
    cursor.execute("SELECT id, phone FROM clients")
    rows = cursor.fetchall()
    if not rows:
        await msg.answer("Mijoz yo‘q")
        return
    text = "Mijozlar:\n"
    for cid, phone in rows:
        text += f"{cid}. {phone}\n"
    await msg.answer(text + "\nMijoz ID yozing:")
    
@dp.message(F.text.regexp(r"^\d+$"))
async def select_client(msg: Message):
    cid = int(msg.text)
    cursor.execute("SELECT phone FROM clients WHERE id=?", (cid,))
    if cursor.fetchone():
        selected_client[msg.from_user.id] = cid
        await msg.answer("Mijoz tanlandi", reply_markup=client_menu)

# ================= PAYMENT =================
@dp.message(F.text == "💰 Pul yozish")
async def ask_payment(msg: Message, state: FSMContext):
    await state.set_state(AddPayment())
    await msg.answer("Summa yozing (faqat raqam)")

@dp.message(AddPayment())
async def save_payment(msg: Message, state: FSMContext):
    cid = selected_client.get(msg.from_user.id)
    amount = int(msg.text)
    date = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("INSERT INTO payments VALUES (?,?,?)", (cid, amount, date))
    conn.commit()
    await msg.answer("Pul yozildi")
    await state.clear()

# ================= EXPENSE =================
@dp.message(F.text == "📦 Xarajat yozish")
async def ask_expense(msg: Message, state: FSMContext):
    await state.set_state(AddExpense())
    await msg.answer("Masalan: 50 g‘isht 150000")

@dp.message(AddExpense())
async def save_expense(msg: Message, state: FSMContext):
    cid = selected_client.get(msg.from_user.id)
    parts = msg.text.rsplit(" ", 1)
    title, amount = parts[0], int(parts[1])
    cursor.execute(
        "INSERT INTO expenses VALUES (?,?,?,?)",
        (cid, title, amount, datetime.now().strftime("%d.%m.%Y"))
    )
    conn.commit()
    await msg.answer("Xarajat yozildi")
    await state.clear()

# ================= REPORT =================
@dp.message(F.text == "📊 Hisobot")
async def report(msg: Message):
    cid = selected_client.get(msg.from_user.id)
    cursor.execute("SELECT SUM(amount) FROM payments WHERE client_id=?", (cid,))
    inc = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM expenses WHERE client_id=?", (cid,))
    exp = cursor.fetchone()[0] or 0
    await msg.answer(
        f"HISOBOT:\n"
        f"Kirim: {inc}\n"
        f"Chiqim: {exp}\n"
        f"Qoldiq: {inc-exp}"
    )

# ================= ADMIN ADD =================
@dp.message(F.text == "➕ Admin qo‘shish")
async def add_admin(msg: Message, state: FSMContext):
    await state.set_state(AddAdmin())
    await msg.answer("Admin TELEGRAM ID yozing")

@dp.message(AddAdmin())
async def save_admin(msg: Message, state: FSMContext):
    cursor.execute("INSERT OR IGNORE INTO admins VALUES (?)", (msg.text,))
    conn.commit()
    await msg.answer("Admin qo‘shildi")
    await state.clear()

# ================= CLIENT ADD =================
@dp.message(F.text == "➕ Mijoz qo‘shish")
async def add_client(msg: Message, state: FSMContext):
    await state.set_state(AddClient())
    await msg.answer("Mijoz telefon raqamini yozing")

@dp.message(AddClient())
async def save_client(msg: Message, state: FSMContext):
    cursor.execute("INSERT OR IGNORE INTO clients (phone) VALUES (?)", (msg.text,))
    conn.commit()
    await msg.answer("Mijoz qo‘shildi")
    await state.clear()

# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
