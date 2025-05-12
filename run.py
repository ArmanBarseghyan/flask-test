# run.py
import os
from myapp import create_app, db # Импортируем фабрику и db
from myapp.models import Floor, CurrentFloor, Content # Импортируем модели для инициализации

# Получаем имя конфигурации из переменной окружения или используем 'default'
config_name = os.environ.get('FLASK_CONFIG') or 'default'

# Создаем экземпляр приложения
app = create_app(config_name)

# --- Инициализация БД при первом запуске (или для разработки) ---
# Оборачиваем в app.app_context()
@app.cli.command('init-db')
def init_db_command():
    """Создает таблицы базы данных и начальные данные."""
    with app.app_context():
        print("Создание таблиц базы данных...")
        db.create_all()
        print("Таблицы созданы.")

        print("Проверка начальных данных...")
        # Создание первого этажа, если его нет
        if Floor.query.count() == 0:
            first_floor = Floor(id="1", name="Первый этаж", filename="", background_filename="")
            db.session.add(first_floor)
            print("Добавлен 'Первый этаж'.")

        # Создание записи о текущем этаже, если ее нет
        if CurrentFloor.query.count() == 0:
            # Убедимся, что этаж '1' существует перед созданием CurrentFloor
            floor1 = db.session.get(Floor, "1")
            if floor1:
                 current = CurrentFloor(floor_id="1")
                 db.session.add(current)
                 print("Установлен текущий этаж по умолчанию '1'.")
            else:
                 print("Предупреждение: Этаж '1' не найден, не могу установить текущий этаж.")


        # Создание начального контента для "О нас", если его нет
        existing_about = Content.query.filter_by(key='about_page_content').first()
        if not existing_about:
            initial_about = Content(key='about_page_content', value='<p>Начальная информация о торговом центре. Отредактируйте это в админ-панели.</p>')
            db.session.add(initial_about)
            print("Создан ключ 'about_page_content' для страницы 'О нас'.")

        # Другие начальные данные (например, категории по умолчанию) можно добавить здесь

        try:
            db.session.commit()
            print("Начальные данные успешно сохранены.")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка сохранения начальных данных: {e}")

    print("Инициализация БД завершена.")


# Запуск приложения Flask
if __name__ == "__main__":
    # Ты можешь запустить init-db командой: flask init-db
    # Запуск веб-сервера: python run.py
    # Для разработки используй debug=True (он берется из конфига)
    # Для продакшена используй Gunicorn или uWSGI:
    # gunicorn --bind 0.0.0.0:5000 run:app
    app.run(debug=app.config.get('DEBUG', False))