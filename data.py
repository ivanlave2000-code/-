import json
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

FILE_PATH = "data.json"

# --- ОТРИМАННЯ ВСІХ ФІЛЬМІВ ---
def get_films(file_path: str = FILE_PATH):
    try:
        with open(file_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
            # Повертаємо список із ключа "films", якщо його немає - порожній список
            return data.get("films", [])
    except (FileNotFoundError, json.JSONDecodeError):
        # Якщо файлу немає або він пошкоджений - створюємо структуру з нуля
        return []

# --- ПОИСК ПО КОДУ (ID) ---
def get_film_by_code(code: str, file_path: str = FILE_PATH):
    films = get_films(file_path)
    # Шукаємо, приводячи все до рядка для надійності
    return next((f for f in films if str(f.get('id')) == str(code)), None)

# --- ЗБЕРІГАННЯ ---
def save_film(new_film, file_path: str = FILE_PATH):
    try:
        films = get_films(file_path)
        films.append(new_film)
        
        with open(file_path, 'w', encoding='utf-8') as fp:
            json.dump({"films": films}, fp, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Помилка збереження: {e}")
        return False

# --- ВИДАЛЕННЯ ---
def delete_film_by_code(code: str, file_path: str = FILE_PATH):
    try:
        films = get_films(file_path)
        # Фільтруємо список, прибираючи елемент із потрібним ID
        new_films = [f for f in films if str(f.get('id')) != str(code)]
        
        if len(films) == len(new_films):
            return False
            
        with open(file_path, 'w', encoding='utf-8') as fp:
            json.dump({"films": new_films}, fp, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Помилка видалення: {e}")
        return False

# --- КЛАВІАТУРА (ДЛЯ /films) ---
def films_keyboard_markup(films_list):
    builder = InlineKeyboardBuilder()
    
    for film in films_list:
        name = film.get("name", "Без назви")
        # Важливо: callback_data має бути коротким (до 64 байт)
        code = str(film.get("id", "0"))
        
        builder.row(InlineKeyboardButton(
            text=f"🎬 {name}", 
            callback_data=f"film_{code}") # Цей префікс "film" ловить бот
        )
    
    return builder.as_markup()
