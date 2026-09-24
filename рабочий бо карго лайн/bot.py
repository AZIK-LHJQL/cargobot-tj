import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(level=logging.INFO)

# --- ТОКЕНЫ БОТОВ ---
CLIENT_BOT_TOKEN = "8062523385:AAEiT_k4GgnruspjJ8NpR89fLLpYo3DWd6I"
ADMIN_BOT_TOKEN = "8863411087:AAEyzpsG9-S__O1ys9-7S9VSH8vF4gOtP60"

# Впиши сюда свой Telegram ID (узнать можно в @userinfobot), чтобы иметь доступ к админке
ADMIN_IDS = [123456789]  

# Инициализация ботов
client_bot = Bot(token=CLIENT_BOT_TOKEN)
admin_bot = Bot(token=ADMIN_BOT_TOKEN)

dp_client = Dispatcher(storage=MemoryStorage())
dp_admin = Dispatcher(storage=MemoryStorage())

# --- БАЗА ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            track_code TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'RU'
        )
    ''')
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 'RU'

def set_user_lang(user_id, lang):
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language = ?", (user_id, lang, lang))
    conn.commit()
    conn.close()

def add_or_update_tracks(tracks, status):
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    count = 0
    for track in tracks:
        track = track.strip().upper()
        if track:
            cursor.execute('''
                INSERT INTO tracks (track_code, status) VALUES (?, ?)
                ON CONFLICT(track_code) DO UPDATE SET status = ?
            ''', (track, status, status))
            count += 1
    conn.commit()
    conn.close()
    return count

def get_track_status(track_code):
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM tracks WHERE track_code = ?", (track_code.strip().upper(),))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def get_stats():
    conn = sqlite3.connect("cargo_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tracks")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tracks WHERE status = 'В Китае'")
    china = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tracks WHERE status = 'В пути'")
    transit = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tracks WHERE status = 'На складе в Худжанде'")
    khujand = cursor.fetchone()[0]
    conn.close()
    return total, china, transit, khujand

# --- КЛАВИАТУРЫ КЛИЕНТСКОГО БОТА ---
def get_main_keyboard(lang='RU'):
    if lang == 'TJ':
        kb = [
            [KeyboardButton(text="🔍 Пайгирии бор (Отследить)"), KeyboardButton(text="📍 Султони Чин (Адрес)")],
            [KeyboardButton(text="🧮 Калькулятор"), KeyboardButton(text="🚫 Молҳои манъшуда")],
            [KeyboardButton(text="📞 Контактҳо"), KeyboardButton(text="🌐 Тағири забон")],
            [KeyboardButton(text="🔄 Тағири карго / Тариф")]
        ]
    else:
        kb = [
            [KeyboardButton(text="🔍 Отследить трек-код"), KeyboardButton(text="📍 Адрес склада в Китае")],
            [KeyboardButton(text="🧮 Калькулятор"), KeyboardButton(text="🚫 Запрещенные товары")],
            [KeyboardButton(text="📞 Контакты"), KeyboardButton(text="🌐 Сменить язык")],
            [KeyboardButton(text="🔄 Переключение тарифа / Карго")]
        ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Состояния для ввода админом
class AdminStates(StatesGroup):
    waiting_for_china_tracks = State()
    waiting_for_transit_tracks = State()
    waiting_for_khujand_tracks = State()

# ==========================================
#          ЛОГИКА КЛИЕНТСКОГО БОТА
# ==========================================

@dp_client.message(CommandStart())
async def client_start(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    text = (
        "✨ <b>АС САЛАМУ АЛЕЙКУМ!</b> ✨\n"
        "Вас приветствует компания <b>Cargo Line TJ</b>! 🚚💨\n\n"
        "Мы обеспечиваем быструю и надежную доставку ваших грузов из Китая в Таджикистан.\n"
        "Выберите нужное действие в меню ниже 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(lang))

@dp_client.message(F.text.in_(["📍 Адрес склада в Китае", "📍 Султони Чин (Адрес)"]))
async def show_address(message: types.Message):
    address_text = (
        "<b>📍 Адрес склада в Китае (копируйте полностью):</b>\n\n"
        "<code>收货人：MA \n"
        "手机号码：13311198266\n"
        "所在地区： 浙江省金华市义乌市 北苑街道\n"
        "详细地址: 浙江省金华市义乌市 北苑街道凌云三区9栋2单元扎娜供应链Z178仓库 МА-(ваш номер)</code>\n\n"
        "⚠️ <b>Обязательно вместо <code>МА-(ваш номер)</code> укажите ваш личный код!</b>"
    )
    await message.answer(address_text, parse_mode="HTML")

@dp_client.message(F.text.in_(["🧮 Калькулятор"]))
async def show_calc(message: types.Message):
    text = (
        "💎 <b>Удобный калькулятор Cargo Line TJ</b> 💎\n\n"
        "💰 <b>Тарифы:</b>\n"
        "• <b>1 кг</b> = 25 сомони\n"
        "• <b>1 куб ($m^3$)</b> = $260\n\n"
        "Для расчета отправьте сообщение в формате:\n"
        "👉 <code>кг 5.5</code> — для расчета по весу\n"
        "👉 <code>куб 0.5</code> — для расчета по объему"
    )
    await message.answer(text, parse_mode="HTML")

@dp_client.message(F.text.in_(["🚫 Запрещенные товары", "🚫 Молҳои манъшуда"]))
async def show_prohibited(message: types.Message):
    text = (
        "🛑 <b>КАТЕГОРИЧЕСКИ ЗАПРЕЩЕННЫЕ К ПЕРЕВОЗКЕ ТОВАРЫ:</b>\n\n"
        "❌ <b>Электронные сигареты</b> (вейпы, жидкости, POD-системы)\n"
        "❌ <b>Химические товары</b> (опасные реагенты, кислоты, яды)\n"
        "❌ <b>Холодное оружие</b> (ножи, кастеты, спецсредства)\n"
        "❌ <b>Медицинские препараты</b> (лекарства без сертификации, шприцы)\n"
        "❌ <b>Живые растения</b> (семена, саженцы, цветы)\n"
        "❌ <b>Пищевые товары</b> (скоропортящиеся продукты)\n"
        "❌ <b>Взрывчатые вещества</b> (пиротехника, салюты, баллоны)"
    )
    await message.answer(text, parse_mode="HTML")

@dp_client.message(F.text.in_(["📞 Контакты", "📞 Контактҳо"]))
async def show_contacts(message: types.Message):
    text = (
        "📞 <b>НАШИ КОНТАКТЫ И АДРЕС:</b>\n\n"
        "📱 <b>Telegram:</b> +992926277667\n"
        "💬 <b>WhatsApp:</b> +992719277667\n"
        "📸 <b>Instagram:</b> <a href='https://www.instagram.com/cargoline.tj?igsh=dmM3aDViMHV3aHI4'>cargoline.tj</a>\n\n"
        "📍 <b>Адрес склада в Таджикистане:</b>\n"
        "трасса Худжанд — Гафуров (прямо рядом с рестораном <b>ДИДОР</b>)"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)

@dp_client.message(F.text.in_(["🌐 Сменить язык", "🌐 Тағири забон"]))
async def change_lang(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="set_lang_TJ")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_RU")]
    ])
    await message.answer("Интихоби забон / Выберите язык:", reply_markup=kb)

@dp_client.callback_query(F.data.startswith("set_lang_"))
async def set_lang_callback(call: types.CallbackQuery):
    lang = call.data.split("_")[2]
    set_user_lang(call.from_user.id, lang)
    msg = "Забон ба тоҷикӣ иваз карда шуд! 🇹🇯" if lang == 'TJ' else "Язык успешно изменен на русский! 🇷🇺"
    await call.message.answer(msg, reply_markup=get_main_keyboard(lang))
    await call.answer()

@dp_client.message(F.text.in_(["🔄 Переключение тарифа / Карго", "🔄 Тағири карго / Тариф"]))
async def change_cargo_info(message: types.Message):
    text = (
        "🏢 <b>Филиал и Тариф Cargo Line TJ:</b>\n\n"
        "📍 <b>Филиал:</b> г. Худжанд (трасса Худжанд-Гафуров, ориентир: ресторан ДИДОР)\n"
        "⚡️ <b>Текущий тариф:</b> Стандартный (Авто / Экспресс)"
    )
    await message.answer(text, parse_mode="HTML")

@dp_client.message(F.text.in_(["🔍 Отследить трек-код", "🔍 Пайгирии бор (Отследить)"]))
async def track_prompt(message: types.Message):
    await message.answer("🔍 Отправьте ваш трек-код в чат для проверки статуса:")

# Обработка ввода калькулятора и трек-кодов
@dp_client.message()
async def process_client_text(message: types.Message):
    text = message.text.strip()
    
    # Расчет калькулятора по весу
    if text.lower().startswith("кг"):
        try:
            val = float(text.split()[1].replace(',', '.'))
            total_som = val * 25
            await message.answer(f"⚖️ Вес: <b>{val} кг</b>\n💵 Итого к оплате: <b>{total_som:.2f} сомони</b>", parse_mode="HTML")
            return
        except:
            pass

    # Расчет калькулятора по объему
    if text.lower().startswith("куб"):
        try:
            val = float(text.split()[1].replace(',', '.'))
            total_usd = val * 260
            await message.answer(f"📦 Объем: <b>{val} м³</b>\n💵 Итого к оплате: <b>${total_usd:.2f} (USD)</b>", parse_mode="HTML")
            return
        except:
            pass

    # Поиск трек-кода
    status = get_track_status(text)
    if status:
        icon = "🇨🇳" if status == "В Китае" else ("🚛" if status == "В пути" else "🏢")
        await message.answer(f"📦 <b>Трек-код:</b> <code>{text.upper()}</code>\n{icon} <b>Статус:</b> <b>{status}</b>", parse_mode="HTML")
    else:
        await message.answer(f"❌ Трек-код <code>{text.upper()}</code> пока не зарегистрирован в системе.", parse_mode="HTML")

# ==========================================
#           ЛОГИКА АДМИН-БОТА
# ==========================================

def admin_keyboard():
    kb = [
        [KeyboardButton(text="🇨🇳 На складе в Китае")],
        [KeyboardButton(text="🚛 В пути")],
        [KeyboardButton(text="🏢 На складе в Худжанде")],
        [KeyboardButton(text="📊 Статистика и База")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp_admin.message(CommandStart())
async def admin_start(message: types.Message):
    await message.answer(
        "⚙️ <b>Панель управления Cargo Line TJ (Админка)</b>\n\n"
        "Выберите категорию для массовой загрузки трек-кодов:",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )

@dp_admin.message(F.text == "📊 Статистика и База")
async def show_stats(message: types.Message):
    total, china, transit, khujand = get_stats()
    text = (
        "📊 <b>ПОЛНАЯ СТАТИСТИКА БАЗЫ ДАННЫХ:</b>\n\n"
        f"📦 Всего трек-кодов в базе: <b>{total}</b>\n"
        f"🇨🇳 На складе в Китае: <b>{china}</b>\n"
        f"🚛 В пути: <b>{transit}</b>\n"
        f"🏢 На складе в Худжанде: <b>{khujand}</b>\n\n"
        "<i>Все данные сохраняются и учитываются за весь период!</i>"
    )
    await message.answer(text, parse_mode="HTML")

@dp_admin.message(F.text == "🇨🇳 На складе в Китае")
async def admin_china(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_china_tracks)
    await message.answer("📥 Отправьте список трек-кодов (каждый с новой строки или через пробел/запятую) для статуса <b>'В Китае'</b>:", parse_mode="HTML")

@dp_admin.message(F.text == "🚛 В пути")
async def admin_transit(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_transit_tracks)
    await message.answer("📥 Отправьте список трек-кодов для статуса <b>'В пути'</b>:", parse_mode="HTML")

@dp_admin.message(F.text == "🏢 На складе в Худжанде")
async def admin_khujand(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_khujand_tracks)
    await message.answer("📥 Отправьте список трек-кодов для статуса <b>'На складе в Худжанде'</b>:", parse_mode="HTML")

@dp_admin.message(AdminStates.waiting_for_china_tracks)
async def process_china_tracks(message: types.Message, state: FSMContext):
    tracks = message.text.replace('\n', ' ').replace(',', ' ').split()
    count = add_or_update_tracks(tracks, "В Китае")
    await message.answer(f"✅ Успешно добавлено/обновлено <b>{count}</b> трек-кодов со статусом <b>'В Китае'</b>!", parse_mode="HTML")
    await state.clear()

@dp_admin.message(AdminStates.waiting_for_transit_tracks)
async def process_transit_tracks(message: types.Message, state: FSMContext):
    tracks = message.text.replace('\n', ' ').replace(',', ' ').split()
    count = add_or_update_tracks(tracks, "В пути")
    await message.answer(f"✅ Успешно добавлено/обновлено <b>{count}</b> трек-кодов со статусом <b>'В пути'</b>!", parse_mode="HTML")
    await state.clear()

@dp_admin.message(AdminStates.waiting_for_khujand_tracks)
async def process_khujand_tracks(message: types.Message, state: FSMContext):
    tracks = message.text.replace('\n', ' ').replace(',', ' ').split()
    count = add_or_update_tracks(tracks, "На складе в Худжанде")
    await message.answer(f"✅ Успешно добавлено/обновлено <b>{count}</b> трек-кодов со статусом <b>'На складе в Худжанде'</b>!", parse_mode="HTML")
    await state.clear()

# --- ЗАПУСК ОБОИХ БОТОВ ОДНОВРЕМЕННО ---
async def main():
    init_db()
    print("🚀 Боты Cargo Line TJ успешно запущены!")
    await asyncio.gather(
        dp_client.start_polling(client_bot),
        dp_admin.start_polling(admin_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())