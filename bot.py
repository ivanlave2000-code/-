import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware

# Імпорти із твоїх файлів
from config import BOT_TOKEN, ADMIN_ID, ALLOWED_USERS
from data import get_films, films_keyboard_markup, save_film, delete_film_by_code, get_film_by_code

# --- НАЛАШТУВАННЯ ЛОГУВАННЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# --- СТАН (FSM) ---
class AddContent(StatesGroup):
    id = State()
    type = State()         
    name = State()
    genre = State()
    rating = State()
    seasons = State()      
    description = State()
    poster = State()

class DeleteFilm(StatesGroup):
    code = State()

def is_text_valid(message: Message):
    return message.text and not message.text.startswith('/')

# --- ОСНОВНІ КОМАНДИ ---

@dp.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Вітаю, <b>{message.from_user.full_name}</b>!\n\n"
        "🎬 Я кіно-бот.\n"
        "🔹 /films — список всіх фільмів\n"
        "🔹 /find <code>назва</code> — пошук\n"
    )
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Ви адмін. Команди:\n/add — додати\n/delfilm — видалити")


@dp.message(Command("add"))
async def add_content_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    await state.set_state(AddContent.id)
    await message.answer("🔢 Шаг 1: Введіть <b>код</b> контенту (наприклад, 101):")

@dp.message(AddContent.id)
async def process_id(message: Message, state: FSMContext):
    if not is_text_valid(message):
        await message.answer("⚠ Введіть коректний код:")
        return
    
    if get_film_by_code(str(message.text)):
        await message.answer(f"❌ Код <b>{message.text}</b> вже зайнятий!")
        return

    await state.update_data(id=message.text)
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎬 Фільм"), KeyboardButton(text="📺 Серіал")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await state.set_state(AddContent.type)
    await message.answer("🎬 Шаг 2: Оберіть тип контенту:", reply_markup=markup)

@dp.message(AddContent.type)
async def process_type(message: Message, state: FSMContext):
    if message.text not in ["🎬 Фільм", "📺 Серіал"]:
        await message.answer("⚠ Використовуйте кнопки!")
        return
    content_type = "Серіал" if "Серіал" in message.text else "Фільм"
    await state.update_data(type=content_type)
    await state.set_state(AddContent.name)
    await message.answer(f"📝 Шаг 3: Назва {content_type.lower()}у:", reply_markup=ReplyKeyboardRemove())

@dp.message(AddContent.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddContent.genre)
    await message.answer("🎭 Шаг 4: Введіть жанр:")

@dp.message(AddContent.genre)
async def process_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddContent.rating)
    await message.answer("⭐ Шаг 5: Рейтинг:")

@dp.message(AddContent.rating)
async def process_rating(message: Message, state: FSMContext):
    await state.update_data(rating=message.text)
    data = await state.get_data()
    if data['type'] == "Серіал":
        await state.set_state(AddContent.seasons)
        await message.answer("🔢 Шаг 6: Кількість сезонів:")
    else:
        await state.update_data(seasons="Фільм")
        await state.set_state(AddContent.description)
        await message.answer("📖 Шаг 6: Опис фільма:")

@dp.message(AddContent.seasons)
async def process_seasons(message: Message, state: FSMContext):
    await state.update_data(seasons=message.text)
    await state.set_state(AddContent.description)
    await message.answer("📖 Шаг 7: Опис:")

@dp.message(AddContent.description)
async def process_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddContent.poster)
    await message.answer("🖼 Шаг 8: Відправте фото або напишіть 'нет':")

@dp.message(AddContent.poster)
async def process_poster(message: Message, state: FSMContext):
    data = await state.get_data()
    
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() == 'нет':
        photo_id = None
    elif message.text:
        photo_id = message.text

    new_item = {
        "id": data.get('id'), "type": data.get('type'), "name": data.get('name'),
        "genre": data.get('genre'), "rating": data.get('rating'), "seasons": data.get('seasons'),
        "description": data.get('description'), "poster": photo_id
    }

    if save_film(new_item):
        await message.answer("✅ Додано успішно!")
    else:
        await message.answer("❌ Помилка при збереженні!")
    await state.clear()

# --- ВИДАЛЕННЯ ---

@dp.message(Command("delfilm"))
async def delfilm_command(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.set_state(DeleteFilm.code)
    await message.answer("🗑 Введіть код фільму для видалення:")

@dp.message(DeleteFilm.code)
async def process_delete_code(message: Message, state: FSMContext):
    if delete_film_by_code(message.text):
        await message.answer("✅ Видалено!")
    else:
        await message.answer("❌ Код не знайдено!")
    await state.clear()

# --- ОБРОБКА ВИБОРУ З СПИСКУ ---

@dp.callback_query(F.data.startswith("film_"))
async def process_film_callback(callback: CallbackQuery):
    code = callback.data.split("_")[1]
    found = get_film_by_code(code)
    
    if found:
        season_info = f"\n🔢 Сезонів: {found['seasons']}" if found.get('type') == "Серіал" else ""
        text = (f"🎬 <b>{found['name']}</b> ({found.get('type', 'Фільм')})\n\n"
                f"⭐ Рейтинг: {found.get('rating')}\n"
                f"🎭 Жанр: {found.get('genre')}{season_info}\n\n📖 {found.get('description')}")
        
        if found.get('poster'):
            try:
                await callback.message.answer_photo(photo=found['poster'], caption=text)
            except:
                await callback.message.answer(text)
        else:
            await callback.message.answer(text)
    else:
        await callback.answer("❌ Контент не знайдено", show_alert=True)
    await callback.answer()

# --- ПОШУК І СПИСОК ---

@dp.message(Command('films'))
async def films_command(message: Message):
    films_list = get_films()
    if not films_list:
        await message.answer("База порожня 😢")
        return
    await message.answer("🍿 Оберіть контент:", reply_markup=films_keyboard_markup(films_list))

@dp.message(Command('find'))
async def find_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔍 Введіть назву! Приклад: /find Гарфілд")
        return
    query = parts[1].strip().lower()
    films_list = get_films()
    
    found = next((f for f in films_list if query in f['name'].lower()), None)
    
    if found:
        season_info = f"\n🔢 Сезонів: {found['seasons']}" if found.get('type') == "Серіал" else ""
        text = (f"🎬 <b>{found['name']}</b>\n\n⭐ Рейтинг: {found.get('rating')}\n"
                f"🎭 Жанр: {found.get('genre')}{season_info}\n\n📖 {found.get('description')}")
        if found.get('poster'):
            await message.answer_photo(photo=found['poster'], caption=text)
        else:
            await message.answer(text)
    else:
        await message.answer("😢 Нічого не знайдено.")

# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
