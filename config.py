# config.py
import os
# import bcrypt # bcrypt больше не нужен здесь
from dotenv import load_dotenv # <-- Импорт для чтения .env

# Загружаем переменные из .env в переменные окружения ОС
# Это нужно сделать ДО доступа к os.environ
load_dotenv()

# Определяем корневую папку проекта (папка, где лежит этот config.py)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# APP_ROOT теперь равен BASE_DIR, так как config.py лежит в корне проекта
APP_ROOT = BASE_DIR

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or "my_fixed_secret_key_12345" # Лучше брать из переменных окружения
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Пути загрузок ---

    # --- ВАРИАНТ ДЛЯ ЛОКАЛЬНОЙ РАЗРАБОТКИ (Windows/Mac/Linux) ---
    # Файлы сохраняются внутри проекта в папке myapp/static/uploads
    # Убедись, что папка myapp/static/uploads существует или будет создана
    UPLOAD_FOLDER_BASE = os.path.join(APP_ROOT, 'myapp', 'static', 'uploads')

    UPLOADED_FILES_DEST = os.path.join(UPLOAD_FOLDER_BASE, 'files')
    UPLOADED_LOGOS_DEST = os.path.join(UPLOAD_FOLDER_BASE, 'shop_logos')
    UPLOADED_ICONS_DEST = os.path.join(UPLOAD_FOLDER_BASE, 'category_icons')
    UPLOADED_BACKGROUNDS_DEST = os.path.join(UPLOAD_FOLDER_BASE, 'backgrounds') # <-- Локальный путь для фонов
    UPLOADED_NEWSIMAGES_DEST = os.path.join(UPLOAD_FOLDER_BASE, 'news_content')
    ABOUT_IMAGES_FOLDER = os.path.join(UPLOADED_FILES_DEST, 'about_images') # <-- Подпапка для картинок "О нас" внутри папки files

    # --- ВАРИАНТ ДЛЯ ПРОДАКШЕН ХОСТИНГА (Linux, как было у тебя) ---
    # Закомментируй блок выше и раскомментируй этот блок перед выгрузкой на хостинг

    # UPLOADED_FILES_DEST = '/home/m/mwmnew/new_izmaylovskiy/myapp/static/uploads/files'
    # UPLOADED_LOGOS_DEST = '/home/m/mwmnew/new_izmaylovskiy/myapp/static/uploads/shop_logos'
    # UPLOADED_ICONS_DEST = '/home/m/mwmnew/new_izmaylovskiy/myapp/static/uploads/category_icons'
    # # Путь для фонов этажей указывает на public_html на хостинге
    # UPLOADED_BACKGROUNDS_DEST = '/home/m/mwmnew/new_izmaylovskiy/public_html/static/uploads'
    # UPLOADED_NEWSIMAGES_DEST = '/home/m/mwmnew/new_izmaylovskiy/myapp/static/uploads/news_content'
    # ABOUT_IMAGES_FOLDER = os.path.join(UPLOADED_FILES_DEST, 'about_images') # Зависит от UPLOADED_FILES_DEST

    # --- Разрешенные расширения ---
    UPLOADED_FILES_ALLOW = ('svg',)
    UPLOADED_LOGOS_ALLOW = ('png', 'jpg', 'jpeg', 'gif')
    UPLOADED_ICONS_ALLOW = ('png', 'jpg', 'jpeg', 'gif')
    UPLOADED_BACKGROUNDS_ALLOW = ('png', 'jpg', 'jpeg', 'gif')
    UPLOADED_NEWSIMAGES_ALLOW = ('png', 'jpg', 'jpeg', 'gif')

    # --- Настройки UploadSet (имена остаются те же) ---
    # Имена UploadSet'ов, которые используются в __init__.py и routes/*.py
    # Flask-Uploads будет использовать соответствующий UPLOADED_..._DEST как папку назначения
    UPLOADED_FILES_FOLDER = 'files'         # Имя UploadSet: files
    UPLOADED_LOGOS_FOLDER = 'logos'         # Имя UploadSet: logos
    UPLOADED_ICONS_FOLDER = 'icons'         # Имя UploadSet: icons
    UPLOADED_BACKGROUNDS_FOLDER = 'backgrounds' # Имя UploadSet: backgrounds
    UPLOADED_NEWSIMAGES_FOLDER = 'newsimages'   # Имя UploadSet: newsimages


    # --- База данных ---
    # Путь к БД относительно папки instance в корне проекта
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(APP_ROOT, 'instance', 'site.db') # Используем APP_ROOT

    # --- Админ (читаем из .env - НЕБЕЗОПАСНЫЙ ВАРИАНТ!) ---
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin_fallback') # Дефолтное имя на всякий случай
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') # Читаем пароль как есть из .env

    # --- Старые строки с bcrypt УДАЛЕНЫ ---
    # ADMIN_SALT = bcrypt.gensalt()
    # ADMIN_HASHED_PASSWORD = bcrypt.hashpw("123".encode('utf-8'), ADMIN_SALT).decode('utf-8')

    # --- Прочее ---
    # Можно добавить настройки для разных сред (Development, Production)

class DevelopmentConfig(Config):
    DEBUG = True
    # Можно переопределить пути для разработки, если нужно, но обычно наследуются из Config

class ProductionConfig(Config):
    DEBUG = False
    # Здесь можно переопределить SECRET_KEY, DATABASE_URL и т.д. для продакшена
    # Если пути для продакшена отличаются, их нужно переопределить ЗДЕСЬ,
    # либо использовать вариант с закомментированными абсолютными путями в Config.

# Словарь для выбора конфигурации по имени
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # По умолчанию используем DevelopmentConfig
}

# Функция для создания папок для загрузки (вызывается в __init__.py)
def ensure_upload_dirs_exist():
    # Используем Config напрямую, т.к. пути загрузки определены там
    dirs_to_create = [
        Config.UPLOADED_FILES_DEST,
        Config.UPLOADED_LOGOS_DEST,
        Config.UPLOADED_ICONS_DEST,
        Config.UPLOADED_BACKGROUNDS_DEST,
        Config.UPLOADED_NEWSIMAGES_DEST,
        Config.ABOUT_IMAGES_FOLDER,
    ]
    print("\nПроверка и создание папок для загрузок:")
    for dir_path in dirs_to_create:
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"  [СОЗДАНА]: {dir_path}")
            elif not os.path.isdir(dir_path):
                 print(f"  [ОШИБКА]: Путь существует, но не является папкой: {dir_path}")
            else:
                 print(f"  [OK]: {dir_path}")
        except OSError as e:
            print(f"  [ОШИБКА СОЗДАНИЯ]: {dir_path}. Причина: {e}")
        except Exception as e:
             print(f"  [НЕИЗВЕСТНАЯ ОШИБКА]: При проверке папки {dir_path}. Причина: {e}")
    print("-" * 30)


# --- Проверка наличия пароля админа при старте ---
# Обращаемся через Config, так как он базовый
if not Config.ADMIN_PASSWORD:
    # Можно использовать logging вместо print в продакшене
    print("\n" + "*"*50)
    print(" КРИТИЧЕСКАЯ ОШИБКА КОНФИГУРАЦИИ: ")
    print(" Переменная ADMIN_PASSWORD не найдена в файле .env!")
    print(" Пожалуйста, добавьте ADMIN_PASSWORD=... в файл .env")
    print(" ПРЕДУПРЕЖДЕНИЕ: Хранение пароля в открытом виде небезопасно!")
    print("*"*50 + "\n")
    # Выбрасываем исключение, чтобы приложение не запустилось без пароля
    raise ValueError("ADMIN_PASSWORD не установлен в .env")
# Можно добавить предупреждение, если используется пароль из твоего примера
elif Config.ADMIN_PASSWORD == 'UvyiUo2_Q3':
    print("\n" + "="*50)
    print(" ПРЕДУПРЕЖДЕНИЕ: Используется небезопасный пароль администратора!")
    print(" Настоятельно рекомендуется сменить пароль в файле .env")
    print(" и использовать хеширование паролей для безопасности.")
    print("="*50 + "\n")
# --- Конец проверки ---