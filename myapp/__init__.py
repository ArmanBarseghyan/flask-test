# myapp/__init__.py
import os
from flask import Flask, g, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_uploads import UploadSet, configure_uploads
from config import config, ensure_upload_dirs_exist # Импортируем конфиг

# Инициализация расширений (без привязки к app)
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

# UploadSets (имена должны совпадать с именами в config.py и старом коде)
files = UploadSet('files') # Имя 'files'
logos = UploadSet('logos') # Имя 'logos'
icons = UploadSet('icons') # Имя 'icons'
backgrounds = UploadSet('backgrounds') # Имя 'backgrounds'
news_images = UploadSet('newsimages') # Имя 'newsimages'

# Функция-фабрика для создания экземпляра приложения
def create_app(config_name='default'):
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True для instance/ папки

    # Загрузка конфигурации
    app.config.from_object(config[config_name])
    # Можно также загрузить из instance/config.py, если он есть
    # app.config.from_pyfile('config.py', silent=True)

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # --- Конфигурация Flask-Uploads ---
    # Настраиваем каждый UploadSet
    configure_uploads(app, files)
    configure_uploads(app, logos)
    configure_uploads(app, icons)
    configure_uploads(app, backgrounds)
    configure_uploads(app, news_images)
    # -----------------------------------

    # Создаем папки для загрузок при старте (если нужно)
    with app.app_context():
         ensure_upload_dirs_exist()
         # Создание папки ABOUT_IMAGES_FOLDER, если она настроена относительно другого DEST
         about_folder = app.config.get('ABOUT_IMAGES_FOLDER')
         if about_folder:
             try:
                 os.makedirs(about_folder, exist_ok=True)
             except OSError as e:
                 print(f"Warning: Could not create about images directory {about_folder}. Error: {e}")

    # Регистрация Blueprints (маршрутов)
    from .routes.user import user_bp
    from .routes.admin import admin_bp
    # from .routes.api import api_bp # Если есть
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin') # Префикс для всех админских роутов
    # app.register_blueprint(api_bp, url_prefix='/api')

    # Регистрация обработчиков ошибок и контекста
    register_error_handlers(app)
    register_request_handlers(app)

    return app

# Функции для регистрации обработчиков
def register_error_handlers(app):
    @app.errorhandler(404)
    def page_not_found(e):
        # Импортируем утилиту загрузки контента здесь, чтобы избежать циклических импортов
        from .utils import load_content
        content = load_content()
        return render_template("user/nonfoundpage.html", content=content), 404

    # Можно добавить другие обработчики (500, 403 и т.д.)

def register_request_handlers(app):
    @app.before_request
    def reset_db_flag():
        g.db_used = False

    @app.teardown_request
    def close_db_connection(exception=None):
        if getattr(g, 'db_used', False):
            # db берем из глобальной области видимости __init__.py
            db.session.remove()