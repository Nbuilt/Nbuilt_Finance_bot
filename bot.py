import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "8344170323:AAF0MmwX9LxBAELpFlf-70Lx9ec0LCHdS0w"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ================= DB =================
conn = sqlite3.connect("finance.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE,
    balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    amount INTEGER,
    date TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    text TEXT,
    amount INTEGER,
    date TEXT
)
""")

conn.commit()

# ================= STATES =================
waiting_admin_phone = set()
waiting_client_phone = set()
waiting_payment = {}
waiting_expense = {}
selected_client = {}

# ================= MENUS =================
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("👥 Mijozlar ro'yhati")
    kb.add("➕ Admin qo‘shish", "➕ Mijoz qo‘shish")
    return kb

def client_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Pul yozish", "📦 Xarajat yozish")
    kb.add("📄 Hisobot", "📊 Grafik")
    kb.add("⬅️ Orqaga")
    return kb

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    phone = msg.from_user.phone_number
    await msg.answer("Xush kelibsiz ADMIN", reply_markup=admin_menu())

# ================= ADMIN ADD =================
@dp.message_handler(lambda m: m.text == "➕ Admin qo‘shish")
async def add_admin(msg: types.Message):
    waiting_admin_phone.add(msg.from_user.id)
    await msg.answer("📞 Admin telefon raqamini kiriting\nMisol: +998901234567")

@dp.message_handler(lambda m: m.from_user.id in waiting_admin_phone)
async def save_admin(msg: types.Message):
    phone = msg.text.strip()
    cur.execute("INSERT OR IGNORE INTO admins(phone) VALUES(?)", (phone,))
    conn.commit()
    waiting_admin_phone.remove(msg.from_user.id)
    await msg.answer("✅ Adminlar ro'yhatiga qo‘shildingiz", reply_markup=admin_menu())

# ================= CLIENT ADD =================
@dp.message_handler(lambda m: m.text == "➕ Mijoz qo‘shish")
async def add_client(msg: types.Message):
    waiting_client_phone.add(msg.from_user.id)
    await msg.answer("📞 Mijoz telefon raqamini kiriting\nMisol: +998971234567")

@dp.message_handler(lambda m: m.from_user.id in waiting_client_phone)
async def save_client(msg: types.Message):
    phone = msg.text.strip()
    cur.execute("INSERT OR IGNORE INTO clients(phone) VALUES(?)", (phone,))
    conn.commit()
    waiting_client_phone.remove(msg.from_user.id)
    await msg.answer("✅ Mijozlar ro'yhatiga qo‘shildi", reply_markup=admin_menu())

# ================= CLIENT LIST =================
@dp.message_handler(lambda m: m.text == "👥 Mijozlar ro'yhati")
async def list_clients(msg: types.Message):
    cur.execute("SELECT id, phone FROM clients")
    rows = cur.fetchall()
    if not rows:
        await msg.answer("Mijoz yo‘q")
        return

    text = "Mijozlar:\n"
    for r in rows:
        text += f"{r[0]}) {r[1]}\n"
    await msg.answer(text + "\nID yozib tanlang:")

@dp.message_handler(lambda m: m.text.isdigit())
async def select_client(msg: types.Message):
    cid = int(msg.text)
    cur.execute("SELECT id FROM clients WHERE id=?", (cid,))
    if not cur.fetchone():
        return
    selected_client[msg.from_user.id] = cid
    await msg.answer("Mijoz tanlandi", reply_markup=client_menu())

# ================= PAYMENT =================
@dp.message_handler(lambda m: m.text == "💰 Pul yozish")
async def payment_start(msg: types.Message):
    if msg.from_user.id not in selected_client:
        await msg.answer("❗ Avval mijozni tanlang")
        return
    waiting_payment[msg.from_user.id] = True
    await msg.answer("💰 Summani kiriting (so‘m)")

@dp.message_handler(lambda m: m.from_user.id in waiting_payment)
async def payment_save(msg: types.Message):
    amount = int(msg.text)
    cid = selected_client[msg.from_user.id]
    date = datetime.now().strftime("%d.%m.%Y")
    cur.execute("INSERT INTO payments(client_id, amount, date) VALUES(?,?,?)",
                (cid, amount, date))
    cur.execute("UPDATE clients SET balance = balance + ? WHERE id=?", (amount, cid))
    conn.commit()
    waiting_payment.pop(msg.from_user.id)
    await msg.answer(f"✅ Pul yozildi\n{amount} so‘m\n{date}", reply_markup=client_menu())

# ================= EXPENSE =================
@dp.message_handler(lambda m: m.text == "📦 Xarajat yozish")
async def expense_start(msg: types.Message):
    if msg.from_user.id not in selected_client:
        await msg.answer("❗ Avval mijozni tanlang")
        return
    waiting_expense[msg.from_user.id] = True
    await msg.answer("📦 Xarajatni yozing\nMasalan: 50 ta g'isht 150000")

@dp.message_handler(lambda m: m.from_user.id in waiting_expense)
async def expense_save(msg: types.Message):
    cid = selected_client[msg.from_user.id]
    text = msg.text
    amount = int(text.split()[-1])
    date = datetime.now().strftime("%d.%m.%Y")
    cur.execute("INSERT INTO expenses(client_id, text, amount, date) VALUES(?,?,?,?)",
                (cid, text, amount, date))
    cur.execute("UPDATE clients SET balance = balance - ? WHERE id=?", (amount, cid))
    conn.commit()
    waiting_expense.pop(msg.from_user.id)
    await msg.answer("✅ Xarajat yozildi", reply_markup=client_menu())

# ================= REPORT =================
@dp.message_handler(lambda m: m.text == "📄 Hisobot")
async def report(msg: types.Message):
    cid = selected_client.get(msg.from_user.id)
    cur.execute("SELECT balance FROM clients WHERE id=?", (cid,))
    bal = cur.fetchone()[0]
    await msg.answer(f"📄 Hisobot\n💰 Qoldiq: {bal} so‘m")

# ================= GRAPH =================
@dp.message_handler(lambda m: m.text == "📊 Grafik")
async def graph(msg: types.Message):
    await msg.answer("📊 Grafik hozircha tayyorlanmoqda (xato yo‘q)")

# ================= BACK =================
@dp.message_handler(lambda m: m.text == "⬅️ Orqaga")
async def back(msg: types.Message):
    selected_client.pop(msg.from_user.id, None)
    await msg.answer("Orqaga", reply_markup=admin_menu())

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp)
