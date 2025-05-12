# myapp/routes/admin.py
from flask import Blueprint, render_template, request, redirect, url_for, session, \
                  flash, send_file, jsonify, current_app, g
import bcrypt
import os
import shutil
from time import time
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from .. import db, csrf # Импорт db и csrf из __init__.py
# Импорт UploadSets из __init__.py
from .. import files, logos, icons, backgrounds, news_images

from ..models import Floor, CurrentFloor, Content, Shop, Category, Subcategory, \
                     ContactMessage, NewsItem, ShopData, ShopDescription, ShopGallery
from ..utils import load_maps, save_maps, load_content, save_content, load_all_shops, \
                    get_first_floor_id, parse_svg_and_save_shops, get_shop_folder_path, \
                    get_floor_background_folder, generate_unique_filename, move_temp_file, \
                    get_news_item_folder_path # Импорт утилит

from flask_uploads import UploadNotAllowed # Импорт исключения

# Создаем Blueprint для админки
admin_bp = Blueprint('admin', __name__) # Имя блюпринта 'admin'

# --- Декоратор для проверки авторизации админа ---
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Для доступа к этой странице необходимо войти.", "warning")
            return redirect(url_for('admin.login', next=request.url)) # Перенаправляем на логин админки
        # Проверка имени пользователя (на всякий случай)
        if session.get("username") != current_app.config['ADMIN_USERNAME']:
             session.pop("username", None) # Выкидываем из сессии, если имя не то
             flash("Неверная сессия администратора.", "error")
             return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Маршруты ---

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if "username" in session and session.get("username") == current_app.config['ADMIN_USERNAME']:
        return redirect(url_for('admin.edit'))

    if request.method == "POST":
        username_form = request.form.get("username")
        password_form = request.form.get("password")
        admin_user_config = current_app.config['ADMIN_USERNAME']
        admin_password_config = current_app.config['ADMIN_PASSWORD'] # Получаем пароль из конфига

        if username_form == admin_user_config:
            # --- ИЗМЕНЕНА ПРОВЕРКА ПАРОЛЯ ---
            if password_form == admin_password_config: # Прямое сравнение строк (НЕБЕЗОПАСНО)
            # --- КОНЕЦ ИЗМЕНЕНИЯ ---
                session["username"] = username_form
                flash("Вход выполнен успешно!", "success")
                next_url = request.args.get('next')
                return redirect(next_url or url_for("admin.edit"))
            else:
                flash("Неверный пароль.", "error")
        else:
            flash("Неверное имя пользователя.", "error")

    return render_template("admin/login.html")

@admin_bp.route("/logout")
@login_required
def logout():
    session.pop("username", None)
    session.pop("current_edit_floor", None) # Очищаем и этаж редактирования
    flash("Вы успешно вышли из системы.", "info")
    return redirect(url_for("admin.login")) # На страницу входа админки

# --- Редактирование главной страницы и карты ---
@admin_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    maps_data = load_maps()
    content = load_content()
    first_floor_id = get_first_floor_id(maps_data)
    current_edit_floor = session.get("current_edit_floor", first_floor_id)

    if current_edit_floor not in maps_data.get("floors", {}):
        current_edit_floor = first_floor_id
        session["current_edit_floor"] = current_edit_floor

    if request.method == "POST":
        # --- ПРОВЕРЯЕМ НАЛИЧИЕ ФАЙЛОВ В ЗАПРОСЕ ---
        map_file_uploaded = 'map_file' in request.files and request.files['map_file'].filename != ''
        background_file_uploaded = 'background_file' in request.files and request.files['background_file'].filename != ''
        floor_name_submitted = 'floor_name' in request.form

        # --- 1. Обработка загрузки КАРТЫ SVG (приоритет) ---
        if map_file_uploaded and current_edit_floor:
            map_file = request.files['map_file']
            print(f"Обнаружен файл карты: {map_file.filename}") # Отладка
            try:
                filename = f"{current_edit_floor}.svg"
                upload_folder = current_app.config['UPLOADED_FILES_DEST']
                print(f"Попытка сохранения карты в: {upload_folder}") # Отладка
                if not os.path.exists(upload_folder):
                     os.makedirs(upload_folder, exist_ok=True)
                     print(f"Создана папка: {upload_folder}")

                # Удаляем старый файл
                old_filename = maps_data["floors"][current_edit_floor].get("filename")
                if old_filename:
                    try:
                        old_filepath = files.path(old_filename)
                        if os.path.exists(old_filepath):
                            os.remove(old_filepath)
                            print(f"Старый файл карты удален: {old_filepath}")
                    except Exception as e_del:
                        print(f"Предупреждение: Не удалось удалить старый файл {old_filename}: {e_del}")

                # Сохраняем новый файл
                # Важно: Убедись, что UploadSet 'files' настроен правильно в __init__.py
                saved_filename = files.save(map_file, name=filename)
                saved_filepath = files.path(saved_filename) # Получаем путь после сохранения
                print(f"Файл карты сохранен как: {saved_filename}")
                print(f"Полный путь сохраненного файла: {saved_filepath}") # Отладка

                # Обновляем БД
                maps_data["floors"][current_edit_floor]["filename"] = saved_filename
                save_maps(maps_data)
                print(f"Имя файла {saved_filename} сохранено для этажа {current_edit_floor} в БД.")

                # Парсим SVG
                parse_svg_and_save_shops(current_edit_floor, saved_filename)
                print(f"SVG файл {saved_filename} обработан для этажа {current_edit_floor}.")

                flash(f"Карта для этажа '{maps_data['floors'][current_edit_floor]['name']}' ({current_edit_floor}) успешно загружена и обработана.", "success")
                return redirect(url_for("admin.edit")) # Редирект ПОСЛЕ успеха

            except UploadNotAllowed:
                flash("Недопустимый тип файла. Загрузите SVG.", "error")
            except Exception as e:
                db.session.rollback() # Откатываем изменения БД, если парсинг/сохранение не удалось
                flash(f"Ошибка при загрузке или обработке карты: {e}", "error")
                print(f"Map upload/parse error: {e}")
                # Редирект не делаем, чтобы показать ошибку

        # --- 2. Обработка загрузки ФОНА (если НЕ загружали карту) ---
        elif background_file_uploaded and current_edit_floor:
            background_file = request.files['background_file']
            print(f"Обнаружен файл фона: {background_file.filename}") # Отладка
            try:
                _, extension = os.path.splitext(background_file.filename)
                # Генерируем уникальное имя, чтобы избежать кэширования и конфликтов
                background_filename = f"background_{current_edit_floor}_{int(time())}{extension.lower()}"
                bg_upload_folder = current_app.config['UPLOADED_BACKGROUNDS_DEST']
                print(f"Попытка сохранения фона в: {bg_upload_folder}") # Отладка
                if not os.path.exists(bg_upload_folder):
                    os.makedirs(bg_upload_folder, exist_ok=True)
                    print(f"Создана папка: {bg_upload_folder}")

                # Удаляем старый фон
                old_bg_filename = maps_data["floors"][current_edit_floor].get("background_filename")
                if old_bg_filename:
                    try:
                        old_bg_path = backgrounds.path(old_bg_filename) # Используем UploadSet 'backgrounds'
                        if os.path.exists(old_bg_path):
                            os.remove(old_bg_path)
                            print(f"Старый файл фона удален: {old_bg_path}")
                    except Exception as e_del:
                         print(f"Предупреждение: Не удалось удалить старый фон {old_bg_filename}: {e_del}")

                # Сохраняем новый фон
                # Важно: UploadSet 'backgrounds' должен быть настроен на UPLOADED_BACKGROUNDS_DEST
                saved_bg_filename = backgrounds.save(background_file, name=background_filename)
                saved_bg_filepath = backgrounds.path(saved_bg_filename)
                print(f"Файл фона сохранен как: {saved_bg_filename}")
                print(f"Полный путь фона: {saved_bg_filepath}")

                # Обновляем БД
                maps_data["floors"][current_edit_floor]["background_filename"] = saved_bg_filename
                save_maps(maps_data)
                print(f"Имя фона {saved_bg_filename} сохранено для этажа {current_edit_floor} в БД.")

                flash(f"Фон для этажа '{maps_data['floors'][current_edit_floor]['name']}' ({current_edit_floor}) успешно загружен.", "success")
                return redirect(url_for("admin.edit")) # Редирект ПОСЛЕ успеха

            except UploadNotAllowed:
                flash("Недопустимый тип файла для фона (разрешены: png, jpg, jpeg, gif).", "error")
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при загрузке фона: {str(e)}", "error")
                print(f"Background upload error: {e}")
                # Редирект не делаем

        # --- 3. Обработка изменения ИМЕНИ ЭТАЖА (если НЕ загружали файлы) ---
        elif floor_name_submitted and current_edit_floor:
            new_floor_name = request.form.get('floor_name', '').strip()
            if new_floor_name:
                # Проверяем, изменилось ли имя
                if maps_data['floors'][current_edit_floor]['name'] != new_floor_name:
                    maps_data['floors'][current_edit_floor]['name'] = new_floor_name
                    save_maps(maps_data)
                    flash(f"Имя этажа '{new_floor_name}' ({current_edit_floor}) успешно обновлено.", "success")
                    # Редирект здесь необязателен, но можно сделать для единообразия
                    return redirect(url_for("admin.edit"))
                else:
                    flash("Имя этажа не изменилось.", "info") # Сообщаем, что изменений не было
                    # Редирект тоже не нужен
            else:
                flash("Имя этажа не может быть пустым.", "error")
                # Редирект не делаем

        # --- 4. Обработка сохранения ТЕКСТОВОГО КОНТЕНТА (если больше ничего не делали) ---
        # Эта логика может быть лишней, если сохранение контента происходит на других страницах.
        # Если она нужна именно здесь, убедись, что она не конфликтует.
        # Проверяем, что форма отправлена, но не было файлов или смены имени
        elif not map_file_uploaded and not background_file_uploaded and not floor_name_submitted:
            # Сохраняем только если есть какие-то данные формы, кроме CSRF
             if len(request.form) > 1: # Проверяем, есть ли что-то кроме csrf_token
                 content_changed = False
                 exclude_keys = {'csrf_token'}
                 new_content_data = {}
                 for key in request.form:
                     if key not in exclude_keys:
                         new_content_data[key] = request.form[key]

                 if new_content_data: # Проверяем, что что-то пришло
                     print("Обработка сохранения контента...") # Отладка
                     for key, value in new_content_data.items():
                         if content.get(key) != value:
                              content[key] = value
                              content_changed = True

                     if content_changed:
                         save_content(content)
                         flash("Текстовый контент успешно сохранен.", "success")
                     else:
                         flash("Изменений в текстовом контенте не обнаружено.", "info")
                     return redirect(url_for("admin.edit")) # Редирект
                 else:
                      # Пустая форма (только csrf) - ничего не делаем
                      pass
             else:
                  # Форма только с csrf - ничего не делаем
                  pass
        else:
             # Ситуация, когда отправлена форма, но не попала ни в одно условие
             print("Не удалось определить действие формы POST в /admin/edit")
             flash("Не удалось определить действие.", "warning")


    # --- Конец обработки POST ---

        # GET запрос или после ошибки POST
    current_bg_url = None
    if current_edit_floor and maps_data.get("floors", {}).get(current_edit_floor, {}).get("background_filename"):
         bg_filename = maps_data["floors"][current_edit_floor]["background_filename"]
         try:
              current_bg_url = url_for('static', filename=f'uploads/backgrounds/{bg_filename}')
              print(f"Пытаемся показать фон (URL для шаблона): {current_bg_url}")
         except Exception as e:
              print(f"Could not generate URL for background {bg_filename}: {e}")

    # Загрузка данных магазинов для карты (должна быть на том же уровне, что и return)
    shops_for_map = load_all_shops() # <--- ПРОВЕРЬ ОТСТУП ЭТОЙ СТРОКИ

    # Рендеринг шаблона (на том же уровне, что и shops_for_map)
    return render_template(
        "admin/edit.html",
        maps=maps_data,
        current_floor_id=current_edit_floor,
        first_floor_id=first_floor_id,
        content=content,
        current_background_url=current_bg_url,
        shops=shops_for_map, # <--- Передаем данные
        timestamp=int(time())
    )



@admin_bp.route("/edit/floor/<floor_id>", methods=["POST"]) # Сделал POST для смены этажа
@login_required
def edit_floor(floor_id):
    maps_data = load_maps()
    if floor_id in maps_data.get("floors", {}):
        session["current_edit_floor"] = floor_id
        flash(f"Переключено на редактирование этажа '{maps_data['floors'][floor_id]['name']}' ({floor_id}).", "info")
    else:
        flash('Выбранный этаж не существует.', 'error')
        # Не меняем этаж в сессии, если он не найден
    return redirect(url_for("admin.edit"))

@admin_bp.route("/edit/add_floor", methods=["POST"])
@login_required
def add_floor():
    maps_data = load_maps()
    floor_ids = [int(f) for f in maps_data.get("floors", {}).keys() if f.isdigit()]
    # Находим следующий номер этажа
    new_floor_id_num = 1
    if floor_ids:
         new_floor_id_num = max(floor_ids) + 1
    new_floor_id = str(new_floor_id_num)

    # Добавляем этаж в данные
    if "floors" not in maps_data: maps_data["floors"] = {}
    maps_data["floors"][new_floor_id] = {"name": f"Этаж {new_floor_id}", "filename": "", "background_filename": ""}
    save_maps(maps_data) # Сохраняем изменения в БД (Floor)

    # Переключаем редактирование на новый этаж
    session["current_edit_floor"] = new_floor_id
    flash(f"Добавлен новый этаж: Этаж {new_floor_id} ({new_floor_id}).", "success")
    return redirect(url_for("admin.edit"))

@admin_bp.route('/edit/delete_floor/<floor_id>', methods=['POST'])
@login_required
def delete_floor(floor_id):
    maps_data = load_maps()
    first_floor_id = get_first_floor_id(maps_data)

    if floor_id == first_floor_id:
        flash("Нельзя удалить первый/основной этаж.", "error")
        return redirect(url_for('admin.edit'))

    if floor_id not in maps_data.get("floors", {}):
        flash("Удаляемый этаж не найден.", "error")
        return redirect(url_for('admin.edit'))

    floor_name = maps_data["floors"][floor_id].get("name", floor_id)

    # Удаление файла карты SVG
    filename = maps_data["floors"][floor_id].get("filename")
    if filename:
        try:
            filepath = files.path(filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Удален файл карты: {filepath}")
        except Exception as e:
            print(f"Ошибка удаления файла карты {filename}: {e}")
            flash(f"Не удалось удалить файл карты SVG для этажа {floor_name}.", "warning")

    # Удаление файла фона
    bg_filename = maps_data["floors"][floor_id].get("background_filename")
    if bg_filename:
        try:
             bg_filepath = backgrounds.path(bg_filename)
             if os.path.exists(bg_filepath):
                  os.remove(bg_filepath)
                  print(f"Удален файл фона: {bg_filepath}")
        except Exception as e:
             print(f"Ошибка удаления файла фона {bg_filename}: {e}")
             flash(f"Не удалось удалить файл фона для этажа {floor_name}.", "warning")
        # Удаление папки фона (если она создавалась отдельно) - get_floor_background_folder создает, но файлы туда кладет UploadSet
        # floor_bg_folder = get_floor_background_folder(floor_id) # Получаем путь
        # if os.path.exists(floor_bg_folder) and os.path.isdir(floor_bg_folder):
        #     try:
        #         shutil.rmtree(floor_bg_folder)
        #         print(f"Удалена папка фона: {floor_bg_folder}")
        #     except OSError as e:
        #         print(f"Ошибка удаления папки фона {floor_bg_folder}: {e}")

    # Удаление магазинов (Shop) этого этажа из БД
    Shop.query.filter_by(floor_id=floor_id).delete()
    # Важно: ShopData, ShopDescription и т.д. НЕ удаляются автоматически!
    # Их нужно удалять вручную, если это требуется. Обычно они остаются сиротами.

    # Удаление самого этажа (Floor) из БД
    floor_to_delete = db.session.get(Floor, floor_id)
    if floor_to_delete:
        db.session.delete(floor_to_delete)

    # Обновление текущего этажа по умолчанию, если удалили его
    current_default = CurrentFloor.query.first()
    if current_default and current_default.floor_id == floor_id:
        current_default.floor_id = first_floor_id # Ставим первый по умолчанию
        print(f"Установлен новый этаж по умолчанию: {first_floor_id}")

    # Обновление текущего этажа редактирования в сессии, если удалили его
    if session.get("current_edit_floor") == floor_id:
        session["current_edit_floor"] = first_floor_id
        print(f"Установлен новый этаж для редактирования: {first_floor_id}")

    # Удаляем этаж из словаря maps_data (для консистентности до коммита)
    if floor_id in maps_data.get("floors", {}):
         del maps_data["floors"][floor_id]
    # Пересохранять maps_data не нужно, т.к. запись Floor удалена

    try:
        db.session.commit()
        flash(f"Этаж '{floor_name}' ({floor_id}) и связанные данные (карта, фон, магазины на схеме) удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении этажа '{floor_name}' из базы данных: {e}", "error")
        print(f"DB error deleting floor {floor_id}: {e}")

    return redirect(url_for('admin.edit'))

@admin_bp.route("/edit/delete_map/<floor_id>", methods=["POST"])
@login_required
def delete_map(floor_id):
    maps_data = load_maps()
    if floor_id in maps_data.get("floors", {}):
        filename = maps_data["floors"][floor_id].get("filename")
        if filename:
            try:
                filepath = files.path(filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    maps_data["floors"][floor_id]["filename"] = "" # Очищаем имя файла
                    save_maps(maps_data) # Сохраняем изменения в БД (Floor)
                    # Опционально: Удалить связанные Shop записи? Или оставить?
                    # Shop.query.filter_by(floor_id=floor_id).delete()
                    # db.session.commit()
                    flash(f"Карта SVG для этажа '{maps_data['floors'][floor_id]['name']}' ({floor_id}) удалена.", "success")
                else:
                    flash(f"Файл карты '{filename}' не найден на диске, но запись в БД очищена.", "warning")
                    maps_data["floors"][floor_id]["filename"] = ""
                    save_maps(maps_data)
            except Exception as e:
                flash(f"Ошибка при удалении файла карты '{filename}': {e}", "error")
                print(f"Error deleting map file {filename}: {e}")
        else:
            flash("У этого этажа нет загруженной карты.", "info")
    else:
        flash("Этаж не найден.", "error")
    return redirect(url_for("admin.edit"))

@admin_bp.route("/edit/delete_background/<floor_id>", methods=["POST"])
@login_required
def delete_background(floor_id):
    # Аналогично delete_map, но для фона
    maps_data = load_maps()
    if floor_id in maps_data.get("floors", {}):
        bg_filename = maps_data["floors"][floor_id].get("background_filename")
        if bg_filename:
            try:
                 bg_filepath = backgrounds.path(bg_filename)
                 if os.path.exists(bg_filepath):
                     os.remove(bg_filepath)
                 maps_data["floors"][floor_id]["background_filename"] = ""
                 save_maps(maps_data)
                 flash(f"Фон для этажа '{maps_data['floors'][floor_id]['name']}' ({floor_id}) удален.", "success")
            except Exception as e:
                 flash(f"Ошибка при удалении файла фона '{bg_filename}': {e}", "error")
                 print(f"Error deleting background file {bg_filename}: {e}")
        else:
            flash("У этого этажа нет загруженного фона.", "info")
    else:
        flash("Этаж не найден.", "error")
    return redirect(url_for("admin.edit"))


@admin_bp.route("/edit/set_default_floor/<floor_id>", methods=["POST"])
@login_required
def set_default_floor(floor_id):
    maps_data = load_maps()
    if floor_id in maps_data.get("floors", {}):
        current_default = CurrentFloor.query.first()
        if current_default:
            if current_default.floor_id != floor_id:
                 current_default.floor_id = floor_id
                 db.session.commit()
                 flash(f"Этаж '{maps_data['floors'][floor_id]['name']}' ({floor_id}) установлен как этаж по умолчанию.", "success")
            else:
                 flash(f"Этаж '{maps_data['floors'][floor_id]['name']}' ({floor_id}) уже является этажом по умолчанию.", "info")
        else:
             # Если записи CurrentFloor нет, создаем ее
             new_default = CurrentFloor(floor_id=floor_id)
             db.session.add(new_default)
             db.session.commit()
             flash(f"Этаж '{maps_data['floors'][floor_id]['name']}' ({floor_id}) установлен как этаж по умолчанию.", "success")
    else:
        flash("Выбранный этаж не найден.", "error")
    return redirect(url_for("admin.edit"))


@admin_bp.route("/download/<floor_id>")
@login_required # Доступ к скачиванию только админу? Или всем? Если всем - убрать @login_required
def download_map(floor_id):
    maps_data = load_maps()
    if floor_id not in maps_data.get("floors", {}):
        flash("Этаж не найден.", "error")
        return redirect(request.referrer or url_for("admin.edit")) # Вернуть назад или на главную админки

    filename = maps_data["floors"][floor_id].get("filename")
    if not filename:
        flash("Карта SVG для этого этажа не загружена.", "error")
        return redirect(request.referrer or url_for("admin.edit"))

    try:
        # Получаем путь к файлу через UploadSet
        filepath = files.path(filename)
        # Отправляем файл
        return send_file(filepath, mimetype='image/svg+xml', as_attachment=True, download_name=filename)
    except FileNotFoundError:
         flash(f"Файл карты '{filename}' не найден на сервере.", "error")
         return redirect(request.referrer or url_for("admin.edit"))
    except Exception as e:
         flash(f"Ошибка при скачивании карты: {e}", "error")
         print(f"Error downloading map {filename}: {e}")
         return redirect(request.referrer or url_for("admin.edit"))

# --- Управление магазинами (Shop, ShopData, etc.) ---

@admin_bp.route("/shops", methods=["GET"])
@login_required
def admin_shops():
    content = load_content() # Для base.html
    category_id = request.args.get('category_id')
    subcategory_ids_str = request.args.get('subcategory_ids', '').split(',')
    subcategory_ids = [sid for sid in subcategory_ids_str if sid]

    # Загружаем ВСЕ магазины для админки
    shops_list = load_all_shops() # visibility=None по умолчанию

    # Фильтрация (логика как в user.shops)
    if category_id:
        try:
            cat_id_int = int(category_id)
            shops_list = [s for s in shops_list if s.get('category_id') == cat_id_int]
        except (ValueError, TypeError): pass
    if subcategory_ids:
        try:
            search_sub_ids_int = {int(sid) for sid in subcategory_ids}
            filtered_shops = []
            for shop in shops_list:
                 shop_sub_ids = {sub['id'] for sub in shop.get('subcategories', [])}
                 if shop_sub_ids.intersection(search_sub_ids_int):
                     filtered_shops.append(shop)
            shops_list = filtered_shops
        except (ValueError, TypeError): pass

    shop_count = len(shops_list)
    categories = Category.query.order_by(Category.name).all() # Для фильтров

    return render_template(
        "admin/shops.html",
        content=content,
        shops=shops_list,
        shop_count=shop_count,
        categories=categories,
        selected_category_id=category_id,
        selected_subcategory_ids=subcategory_ids
        )

@admin_bp.route("/shop/<shop_id>", methods=["GET", "POST"])
@login_required
def admin_shop_detail(shop_id):
    # Загружаем Shop и связанные ShopData
    shop = db.session.query(Shop).options(db.joinedload(Shop.shop_data)).get(shop_id)
    if not shop:
        flash(f"Магазин с ID '{shop_id}' не найден на схеме.", "error")
        return redirect(url_for("admin.admin_shops"))

    # Получаем или создаем ShopData
    shop_data = shop.shop_data
    if not shop_data:
        shop_data = ShopData(id=shop_id)
        db.session.add(shop_data)
        # Не коммитим здесь, коммит будет после обработки POST или в конце GET

    categories = Category.query.options(db.selectinload(Category.subcategories)).order_by(Category.name).all()

    if request.method == "POST":
        form_action = request.form.get("form_action")

        if form_action == "update_details":
            # --- Основные данные ---
            shop_data.shop_name = request.form.get("shop_name", shop_data.shop_name)
            shop_data.web_text = request.form.get("web_text", shop_data.web_text)
            shop_data.web_url = request.form.get("web_url", shop_data.web_url)
            shop_data.work_time = request.form.get("work_time", shop_data.work_time)

            # --- Категория и подкатегории ---
            category_id_str = request.form.get("category_id")
            shop_data.category_id = int(category_id_str) if category_id_str else None

            subcategory_ids_str = request.form.get("subcategory_ids", "")
            subcategory_ids = [int(sid) for sid in subcategory_ids_str.split(',') if sid.isdigit()]
            if subcategory_ids:
                 selected_subcategories = Subcategory.query.filter(Subcategory.id.in_(subcategory_ids)).all()
                 shop_data.subcategories = selected_subcategories
            else:
                 shop_data.subcategories = [] # Очищаем список, если ничего не выбрано

            # --- Видимость ---
            shop_data.visibility = request.form.get("visibility") == "on"
            shop_data.visible_in_tenants = request.form.get("visible_in_tenants") == "on"

            # --- Логотипы и баннер ---
            shop_folder = get_shop_folder_path(shop_id) # Убедимся, что папка есть

            # Shop Logo
            if 'shop_logo' in request.files:
                logo_file = request.files['shop_logo']
                if logo_file.filename:
                    try:
                        # Удаляем старое лого
                        if shop_data.shop_logo:
                             old_logo_path = logos.path(shop_data.shop_logo, folder=shop_id)
                             if os.path.exists(old_logo_path): os.remove(old_logo_path)
                        # Сохраняем новое
                        filename = f"logo_{secure_filename(logo_file.filename)}"
                        saved_logo_filename = logos.save(logo_file, folder=shop_id, name=filename)
                        shop_data.shop_logo = saved_logo_filename # Сохраняем только имя файла
                    except Exception as e: flash(f"Ошибка загрузки логотипа: {e}", "error")

            # Shop Banner
            if 'shop_banner' in request.files:
                banner_file = request.files['shop_banner']
                if banner_file.filename:
                    try:
                        if shop_data.shop_banner:
                             old_banner_path = logos.path(shop_data.shop_banner, folder=shop_id)
                             if os.path.exists(old_banner_path): os.remove(old_banner_path)
                        filename = f"banner_{secure_filename(banner_file.filename)}"
                        saved_banner_filename = logos.save(banner_file, folder=shop_id, name=filename)
                        shop_data.shop_banner = saved_banner_filename
                    except Exception as e: flash(f"Ошибка загрузки баннера: {e}", "error")

            # Scheme Logo
            if 'scheme_logo' in request.files:
                scheme_file = request.files['scheme_logo']
                if scheme_file.filename:
                    try:
                        if shop_data.scheme_logo:
                            old_scheme_path = logos.path(shop_data.scheme_logo, folder=shop_id)
                            if os.path.exists(old_scheme_path): os.remove(old_scheme_path)
                        filename = f"scheme_{secure_filename(scheme_file.filename)}"
                        saved_scheme_filename = logos.save(scheme_file, folder=shop_id, name=filename)
                        shop_data.scheme_logo = saved_scheme_filename
                    except Exception as e: flash(f"Ошибка загрузки логотипа для схемы: {e}", "error")

            # --- Размеры и позиция лого на схеме ---
            try:
                 shop_data.scheme_logo_width = int(request.form.get("scheme_logo_width", shop_data.scheme_logo_width))
                 shop_data.scheme_logo_height = int(request.form.get("scheme_logo_height", shop_data.scheme_logo_height))
                 shop_data.scheme_logo_x = int(request.form.get("scheme_logo_x", shop_data.scheme_logo_x))
                 shop_data.scheme_logo_y = int(request.form.get("scheme_logo_y", shop_data.scheme_logo_y))
            except (ValueError, TypeError):
                 flash("Неверный формат размеров/координат логотипа для схемы.", "error")


            # --- Описания ---
            # Удаляем старые описания
            ShopDescription.query.filter_by(shop_id=shop_id).delete()
            # Добавляем новые непустые описания
            descriptions = request.form.getlist("description")
            new_descriptions = []
            for desc_text in descriptions:
                 if desc_text.strip():
                     new_descriptions.append(ShopDescription(shop_id=shop_id, description=desc_text.strip()))
            if new_descriptions:
                 db.session.add_all(new_descriptions)


            # --- Галерея ---
            if 'gallery_images' in request.files:
                gallery_files = request.files.getlist('gallery_images')
                # Проверяем, есть ли хотя бы один новый файл
                if any(file.filename for file in gallery_files):
                    # Удаляем ВСЕ старые изображения галереи ИЗ БД
                    # Файлы удаляются отдельно через кнопку "Удалить" или при очистке папки
                    # ShopGallery.query.filter_by(shop_id=shop_id).delete() # Не удаляем, чтобы сохранять старые

                    # Добавляем новые файлы
                    new_gallery_items = []
                    for file in gallery_files:
                        if file and file.filename:
                             try:
                                 filename = f"gallery_{secure_filename(file.filename)}"
                                 # Генерируем уникальное имя, чтобы избежать конфликтов
                                 unique_filename = f"gallery_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
                                 saved_gallery_filename = logos.save(file, folder=shop_id, name=unique_filename)
                                 new_gallery_items.append(ShopGallery(shop_id=shop_id, image_path=saved_gallery_filename))
                             except Exception as e:
                                 flash(f"Ошибка загрузки файла галереи '{file.filename}': {e}", "error")
                    if new_gallery_items:
                        db.session.add_all(new_gallery_items)


            # --- Сохранение изменений ---
            try:
                db.session.commit()
                flash(f"Данные магазина '{shop_data.shop_name}' ({shop_id}) успешно обновлены.", "success")
                return redirect(url_for("admin.admin_shop_detail", shop_id=shop_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка сохранения данных магазина: {e}", "error")
                print(f"DB error saving shop {shop_id}: {e}")

        # Другие возможные form_action (например, удаление логотипа)
        elif form_action == "delete_shop_logo":
             if shop_data and shop_data.shop_logo:
                 try:
                     logo_path = logos.path(shop_data.shop_logo, folder=shop_id)
                     if os.path.exists(logo_path): os.remove(logo_path)
                     shop_data.shop_logo = None
                     db.session.commit()
                     flash("Логотип магазина удален.", "success")
                 except Exception as e:
                     db.session.rollback()
                     flash(f"Ошибка удаления логотипа: {e}", "error")
             else: flash("Логотип магазина отсутствует.", "info")
             return redirect(url_for("admin.admin_shop_detail", shop_id=shop_id))

        # Аналогично для delete_shop_banner, delete_scheme_logo...

    # GET запрос или после неудачного POST
    # Загружаем описания и галерею для отображения
    descriptions = ShopDescription.query.filter_by(shop_id=shop_id).all()
    gallery_images_db = ShopGallery.query.filter_by(shop_id=shop_id).all()
    gallery_images_with_urls = []
    for img in gallery_images_db:
         try:
             img_url = url_for('static', filename=logos.url(f"{shop_id}/{img.image_path}"), _t=int(time()))
             gallery_images_with_urls.append({"id": img.id, "url": img_url, "filename": img.image_path})
         except Exception as e:
              print(f"Error generating URL for gallery image {img.image_path}: {e}")


    # Получаем URL для логотипов и баннера
    shop_logo_url = None
    shop_banner_url = None
    scheme_logo_url = None
    if shop_data:
        if shop_data.shop_logo:
             try: shop_logo_url = url_for('static', filename=logos.url(f"{shop_id}/{shop_data.shop_logo}"), _t=int(time()))
             except: pass
        if shop_data.shop_banner:
             try: shop_banner_url = url_for('static', filename=logos.url(f"{shop_id}/{shop_data.shop_banner}"), _t=int(time()))
             except: pass
        if shop_data.scheme_logo:
             try: scheme_logo_url = url_for('static', filename=logos.url(f"{shop_id}/{shop_data.scheme_logo}"), _t=int(time()))
             except: pass


    return render_template(
        "admin/shop_detail.html",
        shop=shop,
        shop_data=shop_data,
        descriptions=descriptions,
        gallery_images=gallery_images_with_urls, # Передаем с URL и ID
        categories=categories,
        shop_logo_url=shop_logo_url,
        shop_banner_url=shop_banner_url,
        scheme_logo_url=scheme_logo_url,
        timestamp=int(time())
        )


@admin_bp.route("/shop/<shop_id>/delete_gallery_image/<int:image_id>", methods=["POST"])
@login_required
def delete_gallery_image(shop_id, image_id):
    image = db.session.get(ShopGallery, image_id) # Используем get для поиска по PK
    if not image:
        flash("Изображение галереи не найдено.", "error")
    elif image.shop_id != shop_id:
        flash("Изображение не принадлежит этому магазину.", "error")
    else:
        try:
            # Получаем путь к файлу через UploadSet 'logos'
            image_path_full = logos.path(image.image_path, folder=shop_id)
            if os.path.exists(image_path_full):
                os.remove(image_path_full)
                print(f"Удален файл галереи: {image_path_full}")

            db.session.delete(image)
            db.session.commit()
            flash("Изображение галереи успешно удалено.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при удалении изображения галереи: {e}", "error")
            print(f"Error deleting gallery image {image.image_path}: {e}")

    return redirect(url_for("admin.admin_shop_detail", shop_id=shop_id))

@admin_bp.route("/shop/<shop_id>/clear_folder", methods=["POST"])
@login_required
def clear_shop_folder(shop_id):
    shop = db.session.get(Shop, shop_id)
    if not shop:
        flash("Магазин не найден.", "error")
        return redirect(url_for("admin.admin_shops")) # На список магазинов

    shop_folder_path = get_shop_folder_path(shop_id) # Получаем путь к папке

    if os.path.exists(shop_folder_path) and os.path.isdir(shop_folder_path):
        try:
            # Удаляем все содержимое папки
            for filename in os.listdir(shop_folder_path):
                 file_path = os.path.join(shop_folder_path, filename)
                 if os.path.isfile(file_path) or os.path.islink(file_path):
                     os.unlink(file_path)
                 elif os.path.isdir(file_path):
                     shutil.rmtree(file_path)
            print(f"Папка магазина очищена: {shop_folder_path}")

            # Очищаем ссылки на файлы в БД (ShopData, ShopGallery)
            shop_data = db.session.get(ShopData, shop_id)
            if shop_data:
                shop_data.shop_logo = None
                shop_data.shop_banner = None
                shop_data.scheme_logo = None

            ShopGallery.query.filter_by(shop_id=shop_id).delete()

            db.session.commit()
            flash("Папка магазина и связанные записи в БД успешно очищены.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при очистке папки магазина: {e}", "error")
            print(f"Error clearing shop folder {shop_id}: {e}")
    else:
        flash("Папка магазина не найдена или не является директорией.", "warning")

    return redirect(url_for("admin.admin_shop_detail", shop_id=shop_id))


@admin_bp.route("/shops/delete/<shop_id>", methods=["POST"])
@login_required
def delete_shop(shop_id):
    # Внимание: Это удаляет ВСЕ данные магазина, включая Shop, ShopData, описания, галерею И папку с файлами!
    shop = db.session.get(Shop, shop_id)
    if shop:
        shop_name = shop.shop_data.shop_name if shop.shop_data else shop_id
        try:
            # 1. Удалить папку с файлами
            shop_folder = get_shop_folder_path(shop_id)
            if os.path.exists(shop_folder) and os.path.isdir(shop_folder):
                 shutil.rmtree(shop_folder)
                 print(f"Удалена папка магазина: {shop_folder}")

            # 2. Удалить связанные записи (галерея, описания)
            ShopGallery.query.filter_by(shop_id=shop_id).delete()
            ShopDescription.query.filter_by(shop_id=shop_id).delete()

            # 3. Удалить ShopData (если существует)
            # Необходимо удалить ShopData ПЕРЕД Shop из-за ForeignKey constraint
            shop_data = db.session.get(ShopData, shop_id)
            if shop_data:
                # Удаляем связи many-to-many с подкатегориями
                shop_data.subcategories = []
                db.session.delete(shop_data)

             # 4. Удалить связанные новости/акции (или отвязать их?)
             # Решаем: удалять или отвязывать (shop_id=None)
            NewsItem.query.filter_by(shop_id=shop_id).delete() # Удаляем связанные новости


            # 5. Удалить сам Shop
            db.session.delete(shop)

            # 6. Коммит
            db.session.commit()
            flash(f"Магазин '{shop_name}' ({shop_id}) и все связанные с ним данные и файлы были полностью удалены.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при полном удалении магазина '{shop_name}': {e}", "error")
            print(f"Error deleting shop {shop_id}: {e}")
    else:
        flash("Магазин для удаления не найден.", "error")

    return redirect(url_for("admin.admin_shops"))


@admin_bp.route("/shops/refresh", methods=["POST"])
@login_required
def refresh_shops():
    maps_data = load_maps()
    processed_floors = []
    errors_occurred = False
    for floor_id, floor_data in maps_data.get("floors", {}).items():
        if floor_data.get("filename"):
            try:
                print(f"Обновление магазинов для этажа {floor_id} из файла {floor_data['filename']}...")
                parse_svg_and_save_shops(floor_id, floor_data["filename"])
                processed_floors.append(floor_id)
            except Exception as e:
                 flash(f"Ошибка при обработке SVG для этажа {floor_id}: {e}", "error")
                 print(f"Error parsing SVG for floor {floor_id}: {e}")
                 errors_occurred = True
        else:
             print(f"Пропуск этажа {floor_id}: файл SVG не указан.")

    if processed_floors and not errors_occurred:
        flash("Список магазинов на всех этажах с картами успешно обновлён из SVG.", "success")
    elif processed_floors and errors_occurred:
         flash("Список магазинов частично обновлен, но возникли ошибки при обработке некоторых SVG.", "warning")
    elif not processed_floors and not errors_occurred:
         flash("Не найдено этажей с загруженными картами SVG для обновления.", "info")
    else: # Не было обработанных + были ошибки (маловероятно)
        flash("При обновлении списка магазинов возникли ошибки.", "error")

    return redirect(url_for("admin.admin_shops"))


# --- Управление видимостью для "Арендаторам" ---
@admin_bp.route("/for_tenants")
@login_required
def admin_for_tenants():
    content = load_content()
    floor_id = request.args.get('floor_id')
    maps_data = load_maps()

    # Загружаем все магазины для админки
    all_shops = load_all_shops()

    # Фильтруем по этажу, если выбран
    shops_list = all_shops
    if floor_id and floor_id in maps_data.get("floors", {}):
        shops_list = [shop for shop in all_shops if shop.get("floor_id") == floor_id]

    shop_count = len(shops_list)
    floors = maps_data.get("floors", {})

    # Считаем общее количество магазинов на каждом этаже (независимо от видимости)
    floor_counts = {}
    for shop in all_shops:
        f_id = shop.get("floor_id")
        if f_id:
            floor_counts[f_id] = floor_counts.get(f_id, 0) + 1

    return render_template(
        "admin/for_tenants.html",
        content=content,
        shops=shops_list,
        shop_count=shop_count,
        floors=floors,
        selected_floor=floor_id,
        floor_counts=floor_counts
    )

@admin_bp.route("/toggle_visibility/<shop_id>", methods=["POST"])
@login_required
def toggle_visibility(shop_id):
    shop_data = db.session.get(ShopData, shop_id)
    if shop_data:
        shop_data.visibility = not shop_data.visibility
        db.session.commit()
        status = "видимым" if shop_data.visibility else "скрытым"
        flash(f"Магазин '{shop_data.shop_name}' ({shop_id}) сделан {status}.", "success")
    else:
        flash(f"Данные магазина {shop_id} не найдены.", "error")
    # Перенаправляем обратно на ту же страницу (арендаторам или список магазинов)
    return redirect(request.referrer or url_for("admin.admin_for_tenants"))

@admin_bp.route("/toggle_tenants_visibility/<shop_id>", methods=["POST"])
@login_required
def toggle_tenants_visibility(shop_id):
    shop_data = db.session.get(ShopData, shop_id)
    if shop_data:
        shop_data.visible_in_tenants = not shop_data.visible_in_tenants
        db.session.commit()
        status = "видимым" if shop_data.visible_in_tenants else "скрытым"
        flash(f"Магазин '{shop_data.shop_name}' ({shop_id}) сделан {status} в разделе 'Арендаторам'.", "success")
    else:
        flash(f"Данные магазина {shop_id} не найдены.", "error")
    return redirect(request.referrer or url_for("admin.admin_for_tenants"))

# --- Управление категориями и подкатегориями ---

@admin_bp.route("/category", methods=["GET", "POST"])
@login_required
def admin_category():
    content = load_content() # Для base.html

    if request.method == "POST":
        action = request.form.get("action")

        # --- Создание новой КАТЕГОРИИ ---
        if action == "create_category":
            category_name = request.form.get("category_name", "").strip()
            category_color = request.form.get("category_color", "#FF5733").strip()
            # Иконка пока не добавляется здесь, только через редактирование категории
            if category_name:
                existing = Category.query.filter(db.func.lower(Category.name) == db.func.lower(category_name)).first()
                if existing:
                    flash(f"Категория с именем '{category_name}' уже существует.", "error")
                else:
                    try:
                        new_category = Category(name=category_name, color=category_color)
                        db.session.add(new_category)
                        db.session.commit()
                        flash(f"Категория '{category_name}' успешно добавлена.", "success")
                    except Exception as e:
                         db.session.rollback()
                         flash(f"Ошибка добавления категории: {e}", "error")
            else:
                flash("Название категории не может быть пустым.", "error")
            # Остаемся на той же странице
            return redirect(url_for("admin.admin_category"))

        # --- Создание новой ПОДКАТЕГОРИИ ---
        elif action == "create_subcategory":
            subcategory_name = request.form.get("subcategory_name", "").strip()
            category_id = request.form.get("category_id")
            if subcategory_name and category_id:
                 parent_category = db.session.get(Category, category_id)
                 if parent_category:
                     existing = Subcategory.query.filter(
                         db.func.lower(Subcategory.name) == db.func.lower(subcategory_name),
                         Subcategory.category_id == category_id
                     ).first()
                     if existing:
                          flash(f"Подкатегория '{subcategory_name}' уже существует в категории '{parent_category.name}'.", "error")
                     else:
                          try:
                              new_subcategory = Subcategory(name=subcategory_name, category_id=category_id)
                              db.session.add(new_subcategory)
                              db.session.commit()
                              flash(f"Подкатегория '{subcategory_name}' успешно добавлена в категорию '{parent_category.name}'.", "success")
                          except Exception as e:
                              db.session.rollback()
                              flash(f"Ошибка добавления подкатегории: {e}", "error")
                 else:
                     flash("Выбранная родительская категория не найдена.", "error")
            else:
                flash("Название подкатегории и выбор категории обязательны.", "error")
            # Остаемся на той же странице
            return redirect(url_for("admin.admin_category"))

    # GET запрос
    categories = Category.query.options(
        db.selectinload(Category.subcategories) # Загружаем подкатегории сразу
        ).order_by(Category.name).all()

    # Генерация URL для иконок категорий
    for cat in categories:
        cat.icon_url = None
        if cat.icon_path:
             try:
                 cat.icon_url = url_for('static', filename=icons.url(cat.icon_path), _t=int(time()))
             except Exception as e:
                 print(f"Error generating icon URL for {cat.icon_path}: {e}")

    return render_template("admin/category.html", content=content, categories=categories)


# myapp/routes/admin.py

@admin_bp.route("/category/delete/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"success": False, "error": "Категория не найдена"}), 404

    category_name = category.name

    try:
        # 1. Отвязать магазины от этой категории
        ShopData.query.filter_by(category_id=category_id).update({"category_id": None})
        print(f"Магазины отвязаны от категории {category_id}")

        # 2. Удалить все подкатегории этой категории
        # (Сначала отвязываем магазины от подкатегорий)
        subcategories_to_delete = Subcategory.query.filter_by(category_id=category_id).all()
        if subcategories_to_delete:
             print(f"Начинаем отвязку магазинов от подкатегорий категории {category_id}...")
             for sub in subcategories_to_delete:
                 shops_with_sub = ShopData.query.filter(ShopData.subcategories.any(id=sub.id)).all()
                 for shop_data in shops_with_sub:
                     shop_data.subcategories.remove(sub)
             print("...Магазины отвязаны.")
             # Теперь удаляем сами подкатегории
             Subcategory.query.filter_by(category_id=category_id).delete()
             print(f"Подкатегории для категории {category_id} удалены.")
        else:
            print(f"Подкатегорий для удаления у категории {category_id} не найдено.")


        # --- БЛОК УДАЛЕНИЯ ФАЙЛА ИКОНКИ ЗАКОММЕНТИРОВАН ---
        # if category.icon_path:
        #     try:
        #          icon_filepath = icons.path(category.icon_path)
        #          if os.path.exists(icon_filepath):
        #              os.remove(icon_filepath)
        #              print(f"Удален файл иконки: {icon_filepath}")
        #     except Exception as e:
        #          print(f"Ошибка удаления файла иконки {category.icon_path}: {e}")
        # --- КОНЕЦ ЗАКОММЕНТИРОВАННОГО БЛОКА ---

        # 4. Удалить саму категорию из БД
        db.session.delete(category)
        print(f"Запись категории {category_id} удалена из БД.")
        db.session.commit()

        return jsonify({"success": True, "message": f"Категория '{category_name}' и все ее подкатегории удалены (файл иконки не затронут)."}), 200 # Возвращаем 200 OK

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка удаления категории {category_id}: {e}")
        return jsonify({"success": False, "error": f"Ошибка базы данных при удалении: {e}"}), 500

@admin_bp.route("/subcategory/delete/<int:subcategory_id>", methods=["POST"])
@login_required
def delete_subcategory(subcategory_id):
    subcategory = db.session.get(Subcategory, subcategory_id)
    if not subcategory:
        return jsonify({"success": False, "error": "Подкатегория не найдена"}), 404

    subcategory_name = subcategory.name

    try:
        # 1. Отвязать магазины от этой подкатегории (удалить из связи many-to-many)
        # SQLAlchemy должен сделать это автоматически при удалении подкатегории,
        # если настроен cascade='all, delete-orphan' на relationship в ShopData,
        # но безопаснее сделать это явно или проверить настройку cascade.
        # Ручной способ (менее эффективный):
        # shops_with_sub = ShopData.query.filter(ShopData.subcategories.any(id=subcategory_id)).all()
        # for shop_data in shops_with_sub:
        #    shop_data.subcategories.remove(subcategory)

        # 2. Удалить саму подкатегорию
        db.session.delete(subcategory)
        db.session.commit()
        return jsonify({"success": True, "message": f"Подкатегория '{subcategory_name}' удалена."})

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка удаления подкатегории {subcategory_id}: {e}")
        return jsonify({"success": False, "error": f"Ошибка базы данных при удалении: {e}"}), 500


@admin_bp.route("/category/edit/<int:category_id>", methods=["GET", "POST"])
@login_required
def admin_category_edit(category_id): # Переименовал, чтобы не конфликтовать с admin_category
    category = db.session.get(Category, category_id)
    if not category:
        flash("Категория не найдена.", "error")
        return redirect(url_for("admin.admin_category"))

    content = load_content() # Для base.html

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_category":
            name = request.form.get("category_name", "").strip()
            color = request.form.get("category_color", "#FF5733").strip()
            selected_icon_filename = request.form.get("category_icon") # Имя файла иконки или 'default'/'delete'

            if name:
                # Проверка уникальности имени (кроме текущей категории)
                existing_category = Category.query.filter(
                    db.func.lower(Category.name) == db.func.lower(name),
                    Category.id != category_id
                ).first()

                if existing_category:
                    flash(f"Категория с именем '{name}' уже существует.", "error")
                else:
                    category.name = name
                    category.color = color if color else "#FF5733"

                    # Обработка иконки
                    old_icon = category.icon_path
                    new_icon = None
                    delete_old = False

                    if selected_icon_filename == "delete":
                         new_icon = None
                         delete_old = True
                    elif selected_icon_filename and selected_icon_filename != "default":
                         new_icon = selected_icon_filename # Используем выбранное имя файла
                         if old_icon and old_icon != new_icon:
                              delete_old = True # Удалим старую, если выбрали новую
                    else: # 'default' или не выбрано - оставляем как есть
                         new_icon = old_icon

                    category.icon_path = new_icon

                    try:
                        db.session.commit()
                        flash("Категория успешно обновлена.", "success")

                        # Удаляем старый файл иконки, если нужно
                        if delete_old and old_icon:
                            try:
                                old_icon_path = icons.path(old_icon)
                                if os.path.exists(old_icon_path):
                                     os.remove(old_icon_path)
                                     print(f"Удален старый файл иконки: {old_icon_path}")
                            except Exception as e:
                                 print(f"Ошибка удаления старого файла иконки {old_icon}: {e}")
                                 flash(f"Категория обновлена, но не удалось удалить старый файл иконки '{old_icon}'.", "warning")

                        # Перенаправляем на страницу списка категорий
                        return redirect(url_for("admin.admin_category"))

                    except Exception as e:
                        db.session.rollback()
                        flash(f"Ошибка обновления категории: {e}", "error")

            else: # Имя не указано
                flash("Название категории не может быть пустым.", "error")

        # Тут могут быть другие actions, например, добавление подкатегории прямо отсюда
        elif action == "add_subcategory":
             # Логика добавления подкатегории (похожа на ту, что в admin_category)
             subcategory_name = request.form.get("new_subcategory_name", "").strip()
             if subcategory_name:
                  existing = Subcategory.query.filter(
                      db.func.lower(Subcategory.name) == db.func.lower(subcategory_name),
                      Subcategory.category_id == category_id
                  ).first()
                  if existing:
                       flash(f"Подкатегория '{subcategory_name}' уже существует в этой категории.", "error")
                  else:
                       try:
                           new_sub = Subcategory(name=subcategory_name, category_id=category_id)
                           db.session.add(new_sub)
                           db.session.commit()
                           flash(f"Подкатегория '{subcategory_name}' добавлена.", "success")
                       except Exception as e:
                           db.session.rollback()
                           flash(f"Ошибка добавления подкатегории: {e}", "error")
             else:
                  flash("Имя новой подкатегории не может быть пустым.", "error")
             # Остаемся на странице редактирования категории
             return redirect(url_for("admin.admin_category_edit", category_id=category_id))


    # GET запрос или после ошибки POST
    subcategories = Subcategory.query.filter_by(category_id=category_id).order_by(Subcategory.name).all()

    # Загрузка списка доступных иконок
    available_icons = []
    try:
        icon_dir = current_app.config['UPLOADED_ICONS_DEST']
        if os.path.isdir(icon_dir):
             available_icons = sorted([
                 f for f in os.listdir(icon_dir)
                 if os.path.isfile(os.path.join(icon_dir, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))
             ])
    except Exception as e:
        print(f"Ошибка чтения директории иконок {icon_dir}: {e}")
        flash("Не удалось загрузить список доступных иконок.", "warning")

    # URL текущей иконки
    current_icon_url = None
    if category.icon_path:
         try:
             current_icon_url = url_for('static', filename=icons.url(category.icon_path), _t=int(time()))
         except Exception: pass

    return render_template(
        "admin/category_edit.html", # Новый шаблон для редактирования
        content=content,
        category=category,
        subcategories=subcategories,
        available_icons=available_icons,
        current_icon_url=current_icon_url
    )

@admin_bp.route("/upload_icon", methods=["POST"])
@login_required
def upload_category_icon():
    if 'icon_file' in request.files:
        file = request.files['icon_file']
        if file and file.filename:
             # Генерируем безопасное и уникальное имя файла
             filename = f"cat_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
             try:
                 saved_filename = icons.save(file, name=filename)
                 return jsonify({"success": True, "filename": saved_filename, "message": f"Иконка '{saved_filename}' загружена."})
             except UploadNotAllowed:
                 return jsonify({"success": False, "error": "Недопустимый тип файла."}), 400
             except Exception as e:
                 print(f"Ошибка загрузки иконки: {e}")
                 return jsonify({"success": False, "error": f"Ошибка сервера при загрузке: {e}"}), 500
    return jsonify({"success": False, "error": "Файл не найден или не выбран."}), 400

@admin_bp.route("/delete_icon/<filename>", methods=["POST"])
@login_required
def delete_category_icon(filename):
     # Проверяем, используется ли иконка какой-либо категорией
     category_using_icon = Category.query.filter_by(icon_path=filename).first()
     if category_using_icon:
         return jsonify({
             "success": False,
             "error": f"Иконка '{filename}' используется категорией '{category_using_icon.name}'. Сначала смените иконку у категории."
             }), 400

     try:
         icon_filepath = icons.path(filename)
         if os.path.exists(icon_filepath):
             os.remove(icon_filepath)
             return jsonify({"success": True, "message": f"Иконка '{filename}' удалена."})
         else:
             return jsonify({"success": False, "error": "Файл иконки не найден на сервере."}), 404
     except Exception as e:
         print(f"Ошибка удаления иконки {filename}: {e}")
         return jsonify({"success": False, "error": f"Ошибка сервера при удалении: {e}"}), 500


# --- Управление Контактами ---
@admin_bp.route("/contacts", methods=["GET", "POST"])
@login_required
def admin_contacts():
    content = load_content() # Загружаем текущий контент

    if request.method == "POST":
        # Сохраняем изменения контактной информации
        content_changed = False
        fields_to_save = [
            'work_schedule_days', 'work_schedule_time',
            'contact_phone_display', 'contact_phone_raw', 'contact_email',
            'contact_address_text', 'contact_address_url',
            # Добавь сюда ключи для соцсетей, если они тоже в Content
            'social_vk_url', 'social_telegram_url' # Пример
        ]
        for field in fields_to_save:
            new_value = request.form.get(field, '') # Получаем значение из формы
            if content.get(field) != new_value:
                 content[field] = new_value
                 content_changed = True

        if content_changed:
             save_content(content) # Сохраняем обновленный словарь content
             flash("Контактная информация успешно обновлена.", "success")
        else:
             flash("Изменений в контактной информации не найдено.", "info")

        return redirect(url_for('admin.admin_contacts')) # Перезагружаем страницу

    # GET запрос: Загружаем сообщения из формы обратной связи
    messages = ContactMessage.query.order_by(ContactMessage.timestamp.desc()).all()
    return render_template("admin/contacts.html", content=content, messages=messages)

@admin_bp.route("/contacts/delete/<int:message_id>", methods=["POST"])
@login_required
def delete_contact_message(message_id):
     message = db.session.get(ContactMessage, message_id)
     if message:
         try:
             db.session.delete(message)
             db.session.commit()
             flash("Сообщение удалено.", "success")
         except Exception as e:
             db.session.rollback()
             flash(f"Ошибка удаления сообщения: {e}", "error")
     else:
         flash("Сообщение не найдено.", "error")
     return redirect(url_for('admin.admin_contacts'))


# --- Управление страницей "О нас" ---
@admin_bp.route("/about", methods=["GET", "POST"])
@login_required
def admin_about():
    content = load_content()

    if request.method == "POST":
        edited_html = request.form.get('about_content')
        if edited_html is not None:
            # Проверяем, изменился ли контент
            if content.get('about_page_content') != edited_html:
                content['about_page_content'] = edited_html
                save_content(content)
                flash("Страница 'О нас' успешно обновлена.", "success")
            else:
                flash("Изменений в содержании страницы 'О нас' не найдено.", "info")
        else:
            flash("Ошибка: Не удалось получить данные из редактора.", "error")
        return redirect(url_for('admin.admin_about'))

    # GET запрос
    about_content_html = content.get('about_page_content', '')
    return render_template("admin/about.html",
                           content=content, # Для base.html
                           about_content_html=about_content_html)

@admin_bp.route('/upload_about_image', methods=['POST'])
@login_required
# @csrf.exempt # Используй, только если не можешь передать CSRF-токен из TinyMCE
def admin_upload_about_image():
    # Путь для сохранения изображений "О нас"
    # Он должен быть доступен статически
    about_img_folder_rel = 'uploads/about_images' # Относительно static
    about_img_folder_abs = os.path.join(current_app.static_folder, about_img_folder_rel)
    os.makedirs(about_img_folder_abs, exist_ok=True) # Убедимся, что папка есть

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file: # Добавить проверку расширений, если нужно
        try:
            # Генерируем безопасное и уникальное имя
            filename = secure_filename(file.filename)
            _, ext = os.path.splitext(filename)
            unique_filename = f"about_{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(about_img_folder_abs, unique_filename)

            file.save(save_path)

            # Возвращаем URL относительно static
            file_url = url_for('static', filename=f'{about_img_folder_rel}/{unique_filename}')
            # TinyMCE ожидает JSON с ключом 'location'
            return jsonify({'location': file_url})

        except Exception as e:
            print(f"Error uploading about image: {e}")
            return jsonify({'error': f'Failed to save file: {e}'}), 500

    return jsonify({'error': 'Invalid file'}), 400

# --- Управление Новостями/Акциями (NewsItem) ---

@admin_bp.route("/news")
@login_required
def admin_news():
    # Загружаем все новости/акции с предзагрузкой магазина
    news_items_query = NewsItem.query.options(
        db.joinedload(NewsItem.shop).joinedload(Shop.shop_data) # Загружаем Shop -> ShopData
        ).order_by(NewsItem.created_at.desc())

    # Фильтрация по типу (news/promo)
    news_type_filter = request.args.get('type')
    if news_type_filter in ['news', 'promo']:
         news_items_query = news_items_query.filter(NewsItem.type == news_type_filter)

    # Фильтрация по статусу публикации
    publish_status_filter = request.args.get('status')
    if publish_status_filter == 'published':
         news_items_query = news_items_query.filter(NewsItem.is_published == True)
    elif publish_status_filter == 'unpublished':
         news_items_query = news_items_query.filter(NewsItem.is_published == False)


    news_items = news_items_query.all()

    # Добавляем отображаемое имя магазина
    for item in news_items:
        item.shop_name_display = None
        if item.shop and item.shop.shop_data:
            item.shop_name_display = item.shop.shop_data.shop_name or f"ID {item.shop_id}"
        elif item.shop_id:
             item.shop_name_display = f"Магазин ID {item.shop_id} (нет данных)"
        # Генерируем URL баннера для превью
        item.banner_url_preview = None
        if item.banner_image:
            try:
                banner_path = f"uploads/news_content/{item.id}/{item.banner_image}"
                item.banner_url_preview = url_for('static', filename=banner_path, _t=int(time()))
            except Exception: pass


    # --- Подсчет корневых файлов ---
    root_file_count = 0
    news_content_path = current_app.config['UPLOADED_NEWSIMAGES_DEST']
    try:
        if os.path.exists(news_content_path) and os.path.isdir(news_content_path):
            for item_name in os.listdir(news_content_path):
                item_path = os.path.join(news_content_path, item_name)
                # Считаем только файлы, игнорируем папки (которые должны быть для каждой новости)
                if os.path.isfile(item_path):
                    root_file_count += 1
        else:
             print(f"Warning: News content directory not found or not a directory: {news_content_path}")

    except Exception as e:
        print(f"Ошибка при подсчете файлов в {news_content_path}: {e}")
        flash(f"Не удалось получить информацию о корневых файлах: {e}", "warning")

    return render_template(
        "admin/news.html",
        news_items=news_items,
        root_file_count=root_file_count,
        current_type_filter=news_type_filter, # Для подсветки фильтра
        current_status_filter=publish_status_filter
    )

@admin_bp.route("/news/clear_root_files", methods=["POST"])
@login_required
def admin_news_clear_root_files():
    news_content_path = current_app.config['UPLOADED_NEWSIMAGES_DEST']
    deleted_count = 0
    error_count = 0
    errors = []

    try:
        if os.path.exists(news_content_path) and os.path.isdir(news_content_path):
            for item_name in os.listdir(news_content_path):
                item_path = os.path.join(news_content_path, item_name)
                if os.path.isfile(item_path): # Удаляем только файлы
                    try:
                        os.remove(item_path)
                        deleted_count += 1
                        print(f"Удален корневой файл: {item_path}")
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Не удалось удалить {item_name}: {e}")
                        print(f"Ошибка удаления файла {item_path}: {e}")

            if deleted_count > 0 and error_count == 0:
                flash(f"Успешно удалено {deleted_count} корневых файлов из папки новостей.", "success")
            elif deleted_count > 0 and error_count > 0:
                flash(f"Удалено {deleted_count} корневых файлов, но возникло {error_count} ошибок.", "warning")
            elif deleted_count == 0 and error_count > 0:
                flash(f"Не удалось удалить файлы. Возникло {error_count} ошибок.", "error")
            else: # deleted_count == 0 and error_count == 0
                 flash("В корне папки новостей не найдено файлов для удаления.", "info")
        else:
            flash("Папка для контента новостей не найдена.", "warning")

    except Exception as e:
        flash(f"Произошла ошибка при попытке очистки: {e}", "error")
        print(f"Ошибка при доступе к {news_content_path}: {e}")

    return redirect(url_for('admin.admin_news'))


@admin_bp.route("/news/create", methods=["GET", "POST"])
@login_required
def admin_news_create():
    # Получаем ID магазина из GET (если перешли со страницы магазина)
    shop_id_get = request.args.get('shop_id')
    # Список всех магазинов для выбора (опционально)
    # shops_list = ShopData.query.order_by(ShopData.shop_name).all()

    if request.method == "POST":
        news_type = request.form.get('news_type') # 'news' или 'promo'
        title = request.form.get('title', '').strip()
        short_description = request.form.get('short_description', '').strip()
        # icon = request.form.get('icon') # Иконки пока не используются явно
        shop_id_form = request.form.get('shop_id') or shop_id_get # ID магазина из формы или GET
        content_blocks_json = request.form.get('content_blocks_data', '[]') # JSON от редактора
        banner_file = request.files.get('banner_image')
        publish_now = request.form.get('publish_now') == 'on' # Публиковать сразу?

        errors = []
        if not news_type: errors.append("Не выбран тип (новость/акция).")
        if not title: errors.append("Заголовок не может быть пустым.")

        # Валидация JSON
        content_blocks_data = []
        try:
            parsed_blocks = json.loads(content_blocks_json)
            if isinstance(parsed_blocks, list):
                 content_blocks_data = parsed_blocks
            else:
                 errors.append("Ошибка формата данных блоков контента (ожидался список).")
        except json.JSONDecodeError:
            errors.append("Ошибка в формате JSON данных блоков контента.")

        # Валидация shop_id (если указан)
        selected_shop = None
        if shop_id_form:
             selected_shop = db.session.get(Shop, shop_id_form)
             if not selected_shop:
                 errors.append(f"Выбранный магазин (ID: {shop_id_form}) не найден.")
                 shop_id_form = None # Сбрасываем ID, если магазин не найден

        # Временное сохранение баннера (если есть)
        temp_banner_filename = None
        if banner_file and banner_file.filename:
            try:
                # Сохраняем во временное имя в корневой папке UPLOADED_NEWSIMAGES_DEST
                temp_banner_filename = f"temp_banner_{generate_unique_filename(banner_file.filename)}"
                saved_temp_name = news_images.save(banner_file, name=temp_banner_filename)
                print(f"Баннер временно сохранен как: {saved_temp_name}")
                # temp_banner_filename = saved_temp_name # Используем имя, возвращенное save()
            except UploadNotAllowed:
                errors.append("Недопустимый тип файла для баннера.")
            except Exception as e:
                errors.append(f"Ошибка временной загрузки баннера: {e}")
                print(f"Banner temp upload error: {e}")

        # Временное сохранение изображений из блоков
        temp_block_images = {} # {temp_url: real_temp_filename}
        files_to_move = {} # {real_temp_filename: final_filename (будет сгенерирован позже)}
        for i, block in enumerate(content_blocks_data):
            if isinstance(block, dict) and block.get('type') == 'image' and block.get('url', '').startswith('blob:'):
                 # Если URL - это blob, значит файл был загружен через input[type=file]
                 # Ищем соответствующий файл в request.files по имени (например, 'content_image_0')
                 file_key = f'content_image_{i}' # Предполагаемое имя поля
                 if file_key in request.files:
                     block_file = request.files[file_key]
                     if block_file and block_file.filename:
                          try:
                              temp_block_filename = f"temp_block_{generate_unique_filename(block_file.filename)}"
                              saved_block_temp_name = news_images.save(block_file, name=temp_block_filename)
                              temp_block_images[block['url']] = saved_block_temp_name # Связываем blob URL с временным файлом
                              files_to_move[saved_block_temp_name] = None # Зарезервировали для перемещения
                              print(f"Изображение блока {i} временно сохранено как: {saved_block_temp_name}")
                          except Exception as e:
                              errors.append(f"Ошибка временной загрузки изображения блока {i}: {e}")
                              print(f"Block image {i} temp upload error: {e}")
                     else:
                          errors.append(f"Файл для изображения блока {i} (blob) не найден или пуст.")
                 else:
                      errors.append(f"Не найден файл '{file_key}' для изображения блока {i} (blob).")


        # Если есть ошибки валидации или загрузки - показываем форму снова
                # Если есть ошибки валидации или загрузки - показываем форму снова
        if errors:
            # Удаляем временные файлы, если они были созданы
            if temp_banner_filename:
                try:
                    os.remove(news_images.path(temp_banner_filename))
                except OSError:
                    print(f"Warning: Could not remove temporary banner file {temp_banner_filename} during error handling.")
                    pass # Игнорируем ошибку удаления
            for temp_img_name in temp_block_images.values():
                 try:
                     os.remove(news_images.path(temp_img_name))
                 except OSError:
                     print(f"Warning: Could not remove temporary block image file {temp_img_name} during error handling.")
                     pass # Игнорируем ошибку удаления

            for error in errors: flash(error, "error")
            return render_template(
                "admin/news_create.html",
                shop_id=shop_id_form or shop_id_get,
                form_data=request.form,
                content_blocks_json=content_blocks_json
            )

        # --- Ошибок нет, создаем запись в БД ---
        try:
            new_item = NewsItem(
                type=news_type,
                title=title,
                short_description=short_description,
                shop_id=shop_id_form if shop_id_form else None,
                content_blocks=[], # Пока пустой, заполним после перемещения файлов
                banner_image=None, # Аналогично
                is_published=publish_now,
                # published_at можно установить здесь или оставить default (utcnow)
                published_at=datetime.utcnow() if publish_now else None
            )
            db.session.add(new_item)
            db.session.flush() # Получаем ID новости до коммита
            news_id = new_item.id
            print(f"Создана запись NewsItem с ID: {news_id}")

            # --- Перемещаем файлы в папку новости ---
            final_banner_filename = None
            if temp_banner_filename:
                 final_banner_filename = move_temp_file(temp_banner_filename, news_id)
                 if final_banner_filename:
                     new_item.banner_image = final_banner_filename
                     print(f"Баннер перемещен в {news_id}, финальное имя: {final_banner_filename}")
                 else:
                     print(f"Не удалось переместить баннер {temp_banner_filename}.")
                     flash(f"Не удалось сохранить файл баннера.", "warning") # Не фатально

            final_content_blocks = []
            for i, block in enumerate(content_blocks_data):
                 block_copy = block.copy() # Работаем с копией
                 if block_copy.get('type') == 'image':
                     original_url = block_copy.get('url', '')
                     if original_url in temp_block_images:
                         # Это изображение, которое мы временно сохранили
                         temp_block_filename = temp_block_images[original_url]
                         final_block_filename = move_temp_file(temp_block_filename, news_id)
                         if final_block_filename:
                              block_copy['url'] = final_block_filename # Заменяем blob/temp URL на реальное имя
                              print(f"Файл блока {i} перемещен, новое имя: {final_block_filename}")
                         else:
                              print(f"Не удалось переместить файл блока {temp_block_filename}, блок пропущен.")
                              flash(f"Не удалось сохранить изображение блока {i}.", "warning")
                              continue # Пропускаем этот блок, если файл не сохранился
                 # Если URL не временный, оставляем как есть (например, внешняя ссылка)
                 final_content_blocks.append(block_copy)


            new_item.content_blocks = final_content_blocks # Сохраняем обработанные блоки

            db.session.commit() # Коммитим все изменения

            flash(f'{ "Новость" if news_type == "news" else "Акция" } "{title}" успешно создана!', 'success')
            return redirect(url_for('admin.admin_news'))

        except Exception as e:
            db.session.rollback()
            # Удаляем временные файлы, если коммит не удался
            if temp_banner_filename:
                try:
                    os.remove(news_images.path(temp_banner_filename))
                except OSError:
                    print(f"Warning: Could not remove temporary banner file {temp_banner_filename} after DB error.")
                    pass
            for temp_img_name in temp_block_images.values():
                 try:
                     os.remove(news_images.path(temp_img_name))
                 except OSError:
                     print(f"Warning: Could not remove temporary block image file {temp_img_name} after DB error.")
                     pass

            flash(f"Произошла ошибка при создании записи: {e}", "error")
            print(f"DB or file move error on news create: {e}")
            # Лучше вернуть на ту же страницу с данными, но пока оставим редирект
            return redirect(url_for('admin.admin_news_create', shop_id=shop_id_form or shop_id_get))


    # GET запрос
    return render_template(
        "admin/news_create.html",
        shop_id=shop_id_get, # Передаем ID магазина, если есть
        # shops_list=shops_list # Для селектора магазинов
        timestamp=int(time()) # Для cache-busting скриптов редактора
    )


@admin_bp.route("/news/upload_image", methods=["POST"])
@login_required
# @csrf.exempt # Используй, только если CSRF мешает AJAX-загрузке редактора
def upload_news_image():
    # Эта функция для AJAX загрузки изображений прямо в редакторе (если он это поддерживает)
    # Она должна сохранять файл временно и возвращать URL или временное имя.
    # Логика похожа на временное сохранение в /news/create

    # !! Важно: Эта реализация предполагает, что редактор отправляет файл под именем 'image' !!
    # !! Возможно, имя поля другое (например, 'file', 'upload') - проверь в JS редактора !!
    if 'image' not in request.files:
        # Попробуем 'file' как альтернативу
        if 'file' in request.files:
            file = request.files['file']
        else:
            return jsonify({"success": False, "error": "Файл не найден (ожидался 'image' или 'file')"}), 400
    else:
         file = request.files['image']


    if not file or file.filename == '':
        return jsonify({"success": False, "error": "Файл не выбран или имя файла пустое"}), 400

    # Генерируем временное имя (например, в корневой папке новостей)
    temp_filename = f"temp_editor_{generate_unique_filename(file.filename)}"

    try:
        saved_temp_filename = news_images.save(file, name=temp_filename)
        print(f"Файл из редактора временно сохранен как: {saved_temp_filename}")

        # Возвращаем JSON, который ожидает редактор.
        # Часто это { "location": "url_to_image" } или { "url": "url_to_image" }
        # В нашем случае, мы не можем дать финальный URL, т.к. ID новости неизвестен.
        # Поэтому возвращаем временное имя файла. JS должен будет заменить его при сохранении.
        # !! Или, можно вернуть URL к временному файлу, если настроена его отдача !!
        # temp_file_url = url_for('static', filename=news_images.url(saved_temp_filename)) # Ненадежно

        # Возвращаем временное имя, JS на клиенте должен будет подставить его в блок 'image'
        # и отправить вместе с остальными данными формы.
        return jsonify({"success": True, "temp_filename": saved_temp_filename}), 200

    except UploadNotAllowed:
         return jsonify({"success": False, "error": "Тип файла не разрешен"}), 400
    except Exception as e:
        print(f"Ошибка сохранения временного файла из редактора: {e}")
        return jsonify({"success": False, "error": "Ошибка сервера при сохранении файла"}), 500


@admin_bp.route("/news/detail/<int:news_id>", methods=["GET", "POST"])
@login_required
def admin_news_detail(news_id):
    # Загружаем новость/акцию с магазином
    news_item = NewsItem.query.options(
        db.joinedload(NewsItem.shop).joinedload(Shop.shop_data)
    ).get_or_404(news_id)

    # Список магазинов для селектора (опционально)
    # shops_list = ShopData.query.order_by(ShopData.shop_name).all()

    if request.method == "POST":
        # --- Получаем данные из формы ---
        news_type = request.form.get('news_type', news_item.type)
        title = request.form.get('title', '').strip()
        short_description = request.form.get('short_description', '').strip()
        shop_id_form = request.form.get('shop_id') # Может быть пустым ('')
        content_blocks_json = request.form.get('content_blocks_data', '[]')
        is_published_form = request.form.get('is_published') == 'on'
        banner_file = request.files.get('banner_image') # Новый баннер
        delete_banner = request.form.get('delete_banner') == 'on' # Флаг удаления баннера

        errors = []
        if not news_type: errors.append("Не выбран тип.")
        if not title: errors.append("Заголовок не может быть пустым.")

        content_blocks_data = []
        try:
            parsed_blocks = json.loads(content_blocks_json)
            if isinstance(parsed_blocks, list):
                 content_blocks_data = parsed_blocks
            else: errors.append("Ошибка формата данных блоков (ожидался список).")
        except json.JSONDecodeError: errors.append("Ошибка формата JSON блоков контента.")

        selected_shop = None
        if shop_id_form:
            selected_shop = db.session.get(Shop, shop_id_form)
            if not selected_shop:
                 errors.append(f"Выбранный магазин (ID: {shop_id_form}) не найден.")
                 shop_id_form = news_item.shop_id # Возвращаем старый ID
        else: # Если '' или None
             shop_id_form = None # Явно ставим None для записи в БД

        # --- Обработка баннера ---
        temp_banner_filename = None
        new_banner_uploaded = False
        if banner_file and banner_file.filename:
            # Загружен новый баннер
            try:
                temp_banner_filename = f"temp_banner_edit_{generate_unique_filename(banner_file.filename)}"
                news_images.save(banner_file, name=temp_banner_filename)
                new_banner_uploaded = True
                print(f"Новый баннер временно сохранен как: {temp_banner_filename}")
            except UploadNotAllowed: errors.append("Недопустимый тип файла для нового баннера.")
            except Exception as e: errors.append(f"Ошибка загрузки нового баннера: {e}")

        # --- Обработка изображений блоков (аналогично /create) ---
        temp_block_images = {} # {url_or_key: temp_filename}
        files_to_move = {}     # {temp_filename: None}
        for i, block in enumerate(content_blocks_data):
             if isinstance(block, dict) and block.get('type') == 'image':
                 image_url = block.get('url', '')
                 # Ищем загруженный файл, если URL - это blob
                 if image_url.startswith('blob:'):
                     file_key = f'content_image_{i}' # Ожидаемое имя поля
                     if file_key in request.files:
                          block_file = request.files[file_key]
                          if block_file and block_file.filename:
                               try:
                                   temp_block_filename = f"temp_block_edit_{generate_unique_filename(block_file.filename)}"
                                   saved_block_temp = news_images.save(block_file, name=temp_block_filename)
                                   temp_block_images[image_url] = saved_block_temp # Связь blob -> temp file
                                   files_to_move[saved_block_temp] = None # Добавляем в очередь на перемещение
                                   print(f"Новое изображение блока {i} временно сохранено: {saved_block_temp}")
                               except Exception as e: errors.append(f"Ошибка временной загрузки нового изображения блока {i}: {e}")
                     # Если файл для blob не найден, это ошибка в JS или форме
                     else: errors.append(f"Не найден файл для blob-изображения блока {i}.")
                 # Если URL уже является временным файлом (из AJAX загрузки)
                 elif image_url.startswith('temp_editor_'):
                      # Предполагаем, что файл уже в корневой папке
                      temp_block_images[image_url] = image_url # Связь temp_url -> temp_filename
                      files_to_move[image_url] = None # Добавляем в очередь на перемещение


        # Если есть ошибки валидации/загрузки
                # Если есть ошибки валидации/загрузки
        if errors:
             if temp_banner_filename: # Удаляем временный новый баннер
                 try:
                     os.remove(news_images.path(temp_banner_filename))
                 except OSError:
                     print(f"Warning: Could not remove temporary banner file {temp_banner_filename} during error handling.")
                     pass # Игнорируем ошибку, если файл не удалился
             for temp_img_name in files_to_move: # Удаляем временные файлы блоков
                  try:
                      os.remove(news_images.path(temp_img_name))
                  except OSError:
                      print(f"Warning: Could not remove temporary block image file {temp_img_name} during error handling.")
                      pass # Игнорируем ошибку

             for error in errors: flash(error, "error")
             # Возвращаем на страницу редактирования с ошибками
             # (Нужно убедиться, что шаблон может обработать form_data и content_blocks_json при ошибке)
             flash("Обнаружены ошибки, проверьте форму и попробуйте снова.", "error")
             # Здесь нужно вернуть render_template, а не redirect, чтобы сохранить данные формы
             # TODO: Доработать возврат данных в шаблон при ошибке POST в admin_news_detail
             # Пока оставим редирект, но это не идеально:
             return redirect(url_for('admin.admin_news_detail', news_id=news_id))

        # --- Ошибок нет, обновляем запись ---
        try:
            news_item.type = news_type
            news_item.title = title
            news_item.short_description = short_description
            news_item.shop_id = shop_id_form # Обновляем ID магазина
            news_item.is_published = is_published_form
            # Обновляем дату публикации, если статус меняется на "опубликовано"
            if is_published_form and not news_item.published_at:
                 news_item.published_at = datetime.utcnow()
            elif not is_published_form:
                 news_item.published_at = None # Сбрасываем дату при снятии с публикации

            current_files_in_use = set() # Собираем файлы, которые должны остаться

            # --- Обработка баннера ---
            old_banner_filename = news_item.banner_image
            final_banner_filename = old_banner_filename # По умолчанию оставляем старый

            if delete_banner:
                 final_banner_filename = None
                 print("Запрошено удаление баннера.")
            elif new_banner_uploaded:
                 # Перемещаем новый баннер
                 moved_banner_name = move_temp_file(temp_banner_filename, news_id)
                 if moved_banner_name:
                     final_banner_filename = moved_banner_name
                     print(f"Новый баннер перемещен: {final_banner_filename}")
                 else:
                     print(f"Ошибка перемещения нового баннера {temp_banner_filename}, оставляем старый (если был).")
                     flash("Не удалось сохранить новый файл баннера.", "warning")
                     final_banner_filename = old_banner_filename # Явно оставляем старый

            # Добавляем финальный баннер в список используемых (если он есть)
            if final_banner_filename:
                current_files_in_use.add(final_banner_filename)

            # Удаляем старый файл баннера, если он был заменен или удален
            if old_banner_filename and old_banner_filename != final_banner_filename:
                 try:
                     old_banner_path = get_news_item_folder_path(news_id)
                     old_banner_full_path = os.path.join(old_banner_path, old_banner_filename)
                     if os.path.exists(old_banner_full_path):
                          os.remove(old_banner_full_path)
                          print(f"Удален старый файл баннера: {old_banner_full_path}")
                 except OSError as e: print(f"Ошибка удаления старого файла баннера {old_banner_filename}: {e}")

            news_item.banner_image = final_banner_filename # Сохраняем финальное имя

            # --- Обработка блоков контента ---
            final_content_blocks = []
            for i, block in enumerate(content_blocks_data):
                 block_copy = block.copy()
                 if block_copy.get('type') == 'image':
                     original_url = block_copy.get('url', '')
                     # Если это новый файл (blob или temp)
                     if original_url in temp_block_images:
                          temp_block_filename = temp_block_images[original_url]
                          final_block_filename = move_temp_file(temp_block_filename, news_id)
                          if final_block_filename:
                               block_copy['url'] = final_block_filename # Обновляем URL
                               current_files_in_use.add(final_block_filename) # Добавляем в используемые
                               print(f"Файл блока {i} перемещен/обновлен: {final_block_filename}")
                          else:
                               print(f"Ошибка перемещения файла блока {i} {temp_block_filename}, блок пропускается.")
                               flash(f"Не удалось сохранить новое изображение блока {i}.", "warning")
                               continue # Пропускаем этот блок
                     # Если это старый файл (просто имя файла)
                     elif original_url and not original_url.startswith(('http:', 'https:', 'blob:', 'temp_')):
                          # Проверяем, существует ли он (на всякий случай)
                          block_file_path = os.path.join(get_news_item_folder_path(news_id), original_url)
                          if os.path.exists(block_file_path):
                               current_files_in_use.add(original_url) # Добавляем старый файл в используемые
                          else:
                               print(f"Предупреждение: Файл блока '{original_url}' не найден, блок будет сохранен без файла.")
                               flash(f"Файл для изображения '{original_url}' не найден на сервере.", "warning")
                               # Можно либо пропустить блок, либо сохранить с пустым url
                               # block_copy['url'] = '' # или None
                               continue # Пока пропускаем
                 # Добавляем обработанный блок (текст или изображение с финальным URL)
                 final_content_blocks.append(block_copy)

            news_item.content_blocks = final_content_blocks # Сохраняем финальный список блоков

            # --- Очистка неиспользуемых файлов ---
            item_folder_path = get_news_item_folder_path(news_id)
            if os.path.exists(item_folder_path):
                 try:
                     existing_files = set(f for f in os.listdir(item_folder_path) if os.path.isfile(os.path.join(item_folder_path, f)))
                     files_to_delete = existing_files - current_files_in_use
                     print(f"--- Очистка папки {news_id} ---")
                     print(f"Используемые файлы: {current_files_in_use}")
                     print(f"Файлы к удалению: {files_to_delete}")
                     for filename_to_delete in files_to_delete:
                          try:
                              file_path_to_delete = os.path.join(item_folder_path, filename_to_delete)
                              os.remove(file_path_to_delete)
                              print(f"Удален неиспользуемый файл: {file_path_to_delete}")
                          except OSError as e: print(f"Ошибка удаления файла {filename_to_delete}: {e}")
                 except Exception as e: print(f"Ошибка при очистке папки {item_folder_path}: {e}")


            # --- Коммит изменений ---
            db.session.commit()
            print(f"Новость {news_id} успешно обновлена в БД.")
            flash(f'Запись "{news_item.title}" успешно обновлена!', 'success')
            return redirect(url_for('admin.admin_news')) # Возвращаемся к списку

        except Exception as e:
            db.session.rollback()
            # Удаляем временные файлы, если коммит/перемещение не удалось
                    # Если есть ошибки валидации/загрузки
        if errors:
             if temp_banner_filename: # Удаляем временный новый баннер
                 try:
                     os.remove(news_images.path(temp_banner_filename))
                 except OSError:
                     print(f"Warning: Could not remove temporary banner file {temp_banner_filename} during error handling (detail).")
                     pass # Игнорируем ошибку
             for temp_img_name in files_to_move: # Удаляем временные файлы блоков
                  try:
                      os.remove(news_images.path(temp_img_name))
                  except OSError:
                      print(f"Warning: Could not remove temporary block image file {temp_img_name} during error handling (detail).")
                      pass # Игнорируем ошибку

             for error in errors: flash(error, "error")
             # Возвращаем на страницу редактирования с ошибками
             flash("Обнаружены ошибки, проверьте форму и попробуйте снова.", "error")
             # TODO: Доработать возврат данных в шаблон при ошибке POST в admin_news_detail
             return redirect(url_for('admin.admin_news_detail', news_id=news_id))

    # --- GET Запрос ---
    # Подготовка данных для редактора
    blocks_for_json = []
    if isinstance(news_item.content_blocks, list):
        for i, block in enumerate(news_item.content_blocks):
            if isinstance(block, dict):
                block_copy = block.copy()
                if block_copy.get('type') == 'image' and block_copy.get('url'):
                    try:
                        # Генерируем полный URL для отображения в редакторе
                        filename_path_display = f"uploads/news_content/{news_id}/{block_copy['url']}"
                        block_copy['url_display'] = url_for('static', filename=filename_path_display, _t=int(time()))
                    except Exception as e:
                         print(f"Ошибка генерации URL для блока {block_copy.get('url')}: {e}")
                         block_copy['url_display'] = None # Или URL к заглушке
                    # Сохраняем оригинальное имя файла для отправки обратно
                    block_copy['url_saved'] = block_copy['url']
                    # Добавляем ключ для input[type=file], если нужно будет заменить файл
                    block_copy['file_input_key'] = f'content_image_{i}'
                blocks_for_json.append(block_copy)
            else:
                print(f"Предупреждение: Пропущен некорректный блок при GET-запросе для новости {news_id}: {block}")

    content_blocks_json_for_js = json.dumps(blocks_for_json)

    # URL текущего баннера
    banner_url_for_template = None
    if news_item.banner_image:
         try:
             banner_path = f"uploads/news_content/{news_id}/{news_item.banner_image}"
             banner_url_for_template = url_for('static', filename=banner_path, _t=int(time()))
         except Exception as e: print(f"Ошибка генерации URL для баннера {news_item.banner_image}: {e}")

    # Информация о связанном магазине для отображения
    shop_info = None
    if news_item.shop and news_item.shop.shop_data:
         shop_info = {"id": news_item.shop_id, "name": news_item.shop.shop_data.shop_name}


    return render_template(
        "admin/news_detail.html",
        news_item=news_item,
        shop_info=shop_info, # Инфо о магазине
        # shops_list=shops_list, # Список магазинов для селектора
        content_blocks_json=content_blocks_json_for_js, # Данные для редактора
        banner_url=banner_url_for_template, # URL текущего баннера
        timestamp=int(time())
    )

@admin_bp.route("/news/delete/<int:news_id>", methods=["POST"])
@login_required
def admin_news_delete(news_id):
    item_to_delete = NewsItem.query.get_or_404(news_id)
    item_title = item_to_delete.title

    # Удаляем папку с контентом
    item_folder_path = get_news_item_folder_path(news_id)
    if os.path.exists(item_folder_path) and os.path.isdir(item_folder_path):
        try:
            shutil.rmtree(item_folder_path)
            print(f"Удалена папка контента: {item_folder_path}")
        except OSError as e:
            print(f"Ошибка удаления папки {item_folder_path}: {e}")
            flash(f"Ошибка при удалении файлов новости/акции '{item_title}'.", "error")
            # Продолжаем удаление записи из БД

    try:
        db.session.delete(item_to_delete)
        db.session.commit()
        flash(f'Запись "{item_title}" и ее файлы успешно удалены.', 'success')
    except Exception as e:
         db.session.rollback()
         flash(f'Ошибка удаления записи "{item_title}" из базы данных: {e}.', 'error')

    return redirect(url_for('admin.admin_news'))

@admin_bp.route("/news/toggle_publish/<int:news_id>", methods=["POST"])
@login_required
def admin_news_toggle_publish(news_id):
    item = NewsItem.query.get_or_404(news_id)
    try:
        item.is_published = not item.is_published
        # Устанавливаем/сбрасываем дату публикации
        if item.is_published:
            item.published_at = datetime.utcnow()
        else:
            item.published_at = None
        db.session.commit()
        status = "опубликована" if item.is_published else "скрыта"
        flash(f'Запись "{item.title}" успешно {status}.', 'success')
    except Exception as e:
         db.session.rollback()
         flash(f'Ошибка изменения статуса публикации для "{item.title}": {e}', 'error')

    return redirect(url_for('admin.admin_news'))


# --- Прочие админские AJAX роуты ---

# myapp/routes/admin.py -> функция get_categories_admin

@admin_bp.route("/get_categories")
@login_required
def get_categories_admin():
    # Используется в admin/shop_detail.html для выбора категории/подкатегории
    categories = Category.query.options(db.selectinload(Category.subcategories)).order_by(Category.name).all()
    categories_data = []
    for cat in categories:
        icon_url_val = None # Переменная для URL иконки
        if cat.icon_path:
            try:
                # --- ИСПРАВЛЕНО ЗДЕСЬ ---
                # Строим URL через static, указывая папку 'category_icons'
                icon_url_val = url_for('static', filename=f'uploads/category_icons/{cat.icon_path}', _t=int(time()))
                # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
            except Exception as e:
                print(f"Ошибка генерации URL для иконки {cat.icon_path}: {e}")

        categories_data.append({
             "id": cat.id, # Отдаем ID как число
             "name": cat.name,
             "icon_url": icon_url_val, # Используем переменную
             "color": cat.color,
             "subcategories": [
                 {"id": sub.id, "name": sub.name}
                  for sub in sorted(cat.subcategories, key=lambda s: s.name)
             ]
        }) # Закрываем словарь

    return jsonify({"categories": categories_data})


@admin_bp.route("/get_subcategories/<int:category_id>")
@login_required
def get_subcategories_admin(category_id):
    # Используется для динамической загрузки подкатегорий в admin/shop_detail.html
    subcategories = Subcategory.query.filter_by(category_id=category_id).order_by(Subcategory.name).all()
    return jsonify({"subcategories": [{"id": sub.id, "name": sub.name} for sub in subcategories]})

@admin_bp.route("/edit/clear_uploads", methods=["POST"])
@login_required # Используем декоратор для админки
def clear_uploads():
    # Убрали проверку сессии, т.к. @login_required уже это делает

    maps_data = load_maps() # Загружаем данные карт
    # Получаем путь к папке с SVG картами из конфига
    uploads_dir = current_app.config['UPLOADED_FILES_DEST']
    deleted_files_count = 0
    error_occurred = False

    try:
        if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
            # Перебираем все файлы в папке uploads/files
            for filename in os.listdir(uploads_dir):
                # Составляем полный путь к файлу
                file_path = os.path.join(uploads_dir, filename)
                # Проверяем, что это файл (а не папка, например)
                if os.path.isfile(file_path):
                    try:
                        # Удаляем файл
                        os.remove(file_path)
                        deleted_files_count += 1
                        print(f"Удален файл карты: {file_path}")
                    except Exception as e:
                        flash(f"Ошибка при удалении файла {filename}: {e}", "error")
                        print(f"Ошибка удаления файла {filename}: {e}")
                        error_occurred = True
            # Если не было ошибок и что-то удалили
            if deleted_files_count > 0 and not error_occurred:
                 flash(f"Удалено {deleted_files_count} файлов карт из папки uploads.", "success")
            elif deleted_files_count == 0 and not error_occurred:
                 flash("В папке uploads/files не найдено файлов карт для удаления.", "info")

            # Очищаем имена файлов в данных карты и сохраняем
            for floor_id in maps_data.get("floors", {}):
                maps_data["floors"][floor_id]["filename"] = ""
            save_maps(maps_data) # Сохраняем изменения (пустые имена файлов)

        else:
            flash(f"Папка для загрузки карт не найдена: {uploads_dir}", "warning")

    except Exception as e:
        flash(f"Произошла ошибка при очистке папки uploads: {e}", "error")
        print(f"Ошибка при доступе/очистке папки {uploads_dir}: {e}")

    # Возвращаемся на страницу редактирования
    return redirect(url_for("admin.edit")) 

@admin_bp.route("/get_uploaded_icons") # Используем admin_bp и относительный URL
@login_required # Защищаем доступ
def get_uploaded_icons():
    # login_required уже проверил сессию, эту проверку можно убрать
    # if "username" not in session:
    #    return redirect(url_for("admin.login")) # Используем правильный url_for

    icon_dir = current_app.config['UPLOADED_ICONS_DEST'] # Используем current_app
    icons_list = []
    try:
        # Проверяем, что путь существует и это директория
        if os.path.exists(icon_dir) and os.path.isdir(icon_dir):
             # Получаем список файлов, фильтруя только файлы (не папки)
             icons_list = [f for f in os.listdir(icon_dir) if os.path.isfile(os.path.join(icon_dir, f))]
             # Опционально: можно добавить фильтр по расширениям, если нужно
             # icons_list = [f for f in icons_list if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
             icons_list.sort() # Сортируем для предсказуемости
        else:
            print(f"Warning: Icon directory not found or not a directory: {icon_dir}")
    except Exception as e:
        print(f"Error reading icons directory {icon_dir}: {e}")
        # В случае ошибки возвращаем пустой список или ошибку JSON
        # return jsonify({"error": "Could not read icon directory"}), 500

    return jsonify({"icons": icons_list})

@admin_bp.route("/shops/clear_shops", methods=["POST"]) # Используем admin_bp
@login_required # Защищаем доступ
def clear_shops():
    # login_required уже проверил сессию

    try:
        # Удаляем в порядке зависимостей (сначала те, что ссылаются, потом те, на которые ссылаются)
        # Хотя CASCADE может处理 это, лучше явно
        print("Удаление данных магазинов...")

        # Удаляем записи из связанных таблиц
        ShopGallery.query.delete()
        print("- Галереи удалены")
        ShopDescription.query.delete()
        print("- Описания удалены")

        # Отвязываем подкатегории (связь M2M) - SQLAlchemy должен сделать это при удалении ShopData
        # Удаляем ShopData
        ShopData.query.delete()
        print("- Данные магазинов (ShopData) удалены")

        # Отвязываем новости (если они ссылаются на Shop)
        NewsItem.query.filter(NewsItem.shop_id.isnot(None)).update({"shop_id": None})
        print("- Новости отвязаны от магазинов")
        # Или удаляем связанные новости: NewsItem.query.filter(NewsItem.shop_id.in_(db.session.query(Shop.id))).delete(synchronize_session=False)


        # Удаляем основные записи Shop
        Shop.query.delete()
        print("- Записи магазинов (Shop) удалены")

        db.session.commit()
        flash("Все данные магазинов (включая описания, галереи) успешно удалены из базы данных.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при очистке базы данных магазинов: {e}", "error")
        print(f"DB Error clearing shops: {e}")

    # Возвращаемся на страницу списка магазинов админки
    return redirect(url_for("admin.admin_shops")) # Используем правильный url_for

    # myapp/routes/admin.py
    # ...

@admin_bp.route("/save_category", methods=["POST"])
@login_required
def save_category():
        # login_required уже проверил авторизацию
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Нет данных"}), 400

        name = data.get("name", "").strip()
        # --- НУЖНО ПОЛУЧИТЬ ИКОНКУ ИЗ ДАННЫХ ---
        icon = data.get("icon") # Получаем имя файла иконки из JSON

        if not name:
            return jsonify({"success": False, "error": "Название категории обязательно"}), 400

        # --- ПРОВЕРКА НА ПУСТУЮ ИКОНКУ (если JS может прислать пустую строку) ---
        if not icon:
             # Можно либо вернуть ошибку, либо установить иконку по умолчанию (None)
             # return jsonify({"success": False, "error": "Иконка не выбрана"}), 400
             icon = None # Устанавливаем None, если иконка не пришла

        # Проверка на существование (регистронезависимая)
        existing_category = Category.query.filter(db.func.lower(Category.name) == db.func.lower(name)).first()
        if existing_category:
            return jsonify({"success": False, "error": f"Категория с именем '{name}' уже существует"}), 400

        try:
            # --- ИЗМЕНЯЕМ СОЗДАНИЕ КАТЕГОРИИ ---
            category = Category(
                name=name,
                # Сохраняем путь к иконке, если он есть и не 'default'
                icon_path = icon if icon and icon != "default" else None
                # Цвет пока не добавляем, т.к. в этой форме он не выбирается
                # color = color if color else "#FF5733"
            )
            # --- КОНЕЦ ИЗМЕНЕНИЯ ---

            db.session.add(category)
            db.session.commit()
            # Возвращаем ID созданной категории, может пригодиться
            return jsonify({"success": True, "category_id": category.id})
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка сохранения категории AJAX: {e}")
            return jsonify({"success": False, "error": "Ошибка базы данных при сохранении категории"}), 500

    # ... (остальные роуты) ...


@admin_bp.route("/save_subcategory", methods=["POST"])
@login_required
def save_subcategory():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Нет данных"}), 400

    name = data.get("name", "").strip()
    category_id_str = data.get("category_id")

    if not name:
         return jsonify({"success": False, "error": "Название подкатегории обязательно"}), 400
    if not category_id_str:
        return jsonify({"success": False, "error": "Не выбрана родительская категория"}), 400

    try:
         category_id = int(category_id_str)
    except (ValueError, TypeError):
         return jsonify({"success": False, "error": "Неверный ID родительской категории"}), 400

    # Проверяем родительскую категорию
    parent_category = db.session.get(Category, category_id)
    if not parent_category:
         return jsonify({"success": False, "error": "Родительская категория не найдена"}), 404

    # Проверка на существование (в рамках ОДНОЙ категории)
    existing_subcategory = Subcategory.query.filter(
        db.func.lower(Subcategory.name) == db.func.lower(name),
        Subcategory.category_id == category_id
    ).first()
    if existing_subcategory:
        return jsonify({"success": False, "error": f"Подкатегория с именем '{name}' уже существует в этой категории"}), 400

    try:
        subcategory = Subcategory(name=name, category_id=category_id)
        db.session.add(subcategory)
        db.session.commit()
        # Возвращаем ID созданной подкатегории
        return jsonify({"success": True, "subcategory_id": subcategory.id})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения подкатегории AJAX: {e}")
        return jsonify({"success": False, "error": "Ошибка базы данных при сохранении подкатегории"}), 500
    
@admin_bp.route("/shop/<shop_id>/set_category", methods=["POST"])
@login_required
def set_shop_category(shop_id):
    shop_data = db.session.get(ShopData, shop_id)
    if not shop_data:
        return jsonify({"success": False, "error": "Магазин не найден"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Нет данных"}), 400

    category_id_str = data.get("category_id") # Получаем ID из JSON

    try:
        # Если пришел пустой ID или null, ставим None
        new_category_id = int(category_id_str) if category_id_str else None
        # Проверяем, изменилась ли категория
        if shop_data.category_id != new_category_id:
            shop_data.category_id = new_category_id
            db.session.commit()
            print(f"Категория для магазина {shop_id} обновлена на {new_category_id}")
            return jsonify({"success": True, "message": "Категория обновлена"})
        else:
            # Категория не изменилась
            return jsonify({"success": True, "message": "Категория не изменена"})
    except ValueError:
         return jsonify({"success": False, "error": "Неверный ID категории"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка обновления категории для магазина {shop_id}: {e}")
        return jsonify({"success": False, "error": "Ошибка базы данных"}), 500

# --- НОВЫЙ РОУТ: Сохранение ТОЛЬКО подкатегорий для магазина (AJAX) ---
@admin_bp.route("/shop/<shop_id>/set_subcategories", methods=["POST"])
@login_required
def set_shop_subcategories(shop_id):
    shop_data = db.session.get(ShopData, shop_id)
    if not shop_data:
        return jsonify({"success": False, "error": "Магазин не найден"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Нет данных"}), 400

    # Получаем строку с ID подкатегорий, разделенных запятыми
    subcategory_ids_str = data.get("subcategory_ids", "")
    # Преобразуем в список чисел, убирая пустые и нечисловые
    subcategory_ids = [int(sid) for sid in subcategory_ids_str.split(',') if sid.isdigit()]

    try:
        # Получаем объекты подкатегорий по ID
        selected_subcategories = []
        if subcategory_ids:
             selected_subcategories = Subcategory.query.filter(Subcategory.id.in_(subcategory_ids)).all()

        # Обновляем связь many-to-many
        shop_data.subcategories = selected_subcategories
        db.session.commit()
        print(f"Подкатегории для магазина {shop_id} обновлены: {subcategory_ids}")
        return jsonify({"success": True, "message": "Подкатегории обновлены"})

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка обновления подкатегорий для магазина {shop_id}: {e}")
        return jsonify({"success": False, "error": "Ошибка базы данных"}), 500
    
    
    
@admin_bp.route('/shops/bulk/toggle_visibility', methods=['POST'])
@login_required
def bulk_toggle_visibility():
    data = request.get_json()
    shop_ids = data.get('shop_ids', [])
    action = data.get('action') # 'show' или 'hide'

    if not shop_ids or action not in ['show', 'hide']:
        return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400

    try:
        target_visibility = (action == 'show') # True для 'show', False для 'hide'
        # Обновляем видимость для выбранных магазинов
        updated_count = ShopData.query.filter(ShopData.id.in_(shop_ids)).update(
            {'visibility': target_visibility},
            synchronize_session=False # Важно для bulk update
        )
        db.session.commit()
        print(f"Массовое обновление видимости ({action}) для {updated_count} магазинов: {shop_ids}")
        return jsonify({'success': True, 'message': f'Видимость обновлена для {updated_count} магазинов.'})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка массового обновления видимости: {e}")
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500

@admin_bp.route('/shops/bulk/toggle_tenants_visibility', methods=['POST'])
@login_required
def bulk_toggle_tenants_visibility():
    data = request.get_json()
    shop_ids = data.get('shop_ids', [])
    action = data.get('action') # 'show_tenants' или 'hide_tenants'

    if not shop_ids or action not in ['show_tenants', 'hide_tenants']:
        return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400

    try:
        target_visibility = (action == 'show_tenants')
        updated_count = ShopData.query.filter(ShopData.id.in_(shop_ids)).update(
            {'visible_in_tenants': target_visibility},
            synchronize_session=False
        )
        db.session.commit()
        print(f"Массовое обновление видимости в аренде ({action}) для {updated_count} магазинов: {shop_ids}")
        return jsonify({'success': True, 'message': f'Видимость в арендаторах обновлена для {updated_count} магазинов.'})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка массового обновления видимости в аренде: {e}")
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500

@admin_bp.route('/shops/bulk/delete', methods=['POST'])
@login_required
def bulk_delete_shops():
    data = request.get_json()
    shop_ids = data.get('shop_ids', [])
    action = data.get('action') # Должен быть 'delete'

    if not shop_ids or action != 'delete':
        return jsonify({'success': False, 'error': 'Неверные параметры запроса'}), 400

    deleted_count = 0
    errors = []

    for shop_id in shop_ids:
        shop = db.session.get(Shop, shop_id)
        if shop:
            try:
                # --- Логика полного удаления магазина (как в delete_shop) ---
                # 1. Удалить папку
                shop_folder = get_shop_folder_path(shop_id)
                if os.path.exists(shop_folder) and os.path.isdir(shop_folder):
                    shutil.rmtree(shop_folder)

                # 2. Удалить связанные записи
                ShopGallery.query.filter_by(shop_id=shop_id).delete()
                ShopDescription.query.filter_by(shop_id=shop_id).delete()

                # 3. Удалить ShopData
                shop_data = db.session.get(ShopData, shop_id)
                if shop_data:
                    shop_data.subcategories = []
                    db.session.delete(shop_data)

                # 4. Отвязать/удалить новости
                NewsItem.query.filter_by(shop_id=shop_id).delete()

                # 5. Удалить Shop
                db.session.delete(shop)
                # Коммит делаем один раз в конце
                deleted_count += 1
                print(f"Магазин {shop_id} подготовлен к удалению.")
            except Exception as e:
                db.session.rollback() # Откатываем удаление ЭТОГО магазина
                errors.append(f"Ошибка удаления магазина {shop_id}: {e}")
                print(f"Ошибка удаления магазина {shop_id}: {e}")
                # Прерываем цикл или продолжаем удалять остальные?
                # Пока продолжаем
        else:
            errors.append(f"Магазин {shop_id} не найден.")

    try:
         db.session.commit() # Коммитим все успешные удаления
         message = f'Успешно удалено {deleted_count} магазинов.'
         if errors:
             message += f'\nВозникли ошибки при удалении: {"; ".join(errors)}'
             flash(message, 'warning') # Показываем flash с ошибками
             return jsonify({'success': False, 'error': message}) # Возвращаем ошибку, если были проблемы
         else:
             flash(message, 'success')
             return jsonify({'success': True, 'message': message})
    except Exception as e:
         db.session.rollback() # Общий откат на всякий случай
         print(f"Ошибка коммита при массовом удалении: {e}")
         return jsonify({'success': False, 'error': f'Критическая ошибка при удалении: {e}'}), 500 
    
# Добавь сюда остальные админские роуты...