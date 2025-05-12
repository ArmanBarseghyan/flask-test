# myapp/utils.py
import os
import sys
# Если site-packages все еще нужен именно так:
# sys.path.append('/home/m/mwmnew/new_izmaylovskiy/venv/lib/python3.10/site-packages/')
import shutil
import xml.etree.ElementTree as ET
import json
import random
import string
import io
import base64
import uuid
from time import time
from flask import current_app, g, url_for # Используем current_app для доступа к config
from werkzeug.utils import secure_filename
from captcha.image import ImageCaptcha
from . import db # Импорт db из текущего пакета
from .models import Floor, CurrentFloor, Content, Shop, Category, Subcategory, \
                    ContactMessage, NewsItem, ShopData, ShopDescription, ShopGallery

# --- Функции работы с папками ---
def get_shop_folder_path(shop_id):
    # Берем путь из конфигурации текущего приложения
    base_path = current_app.config['UPLOADED_LOGOS_DEST']
    shop_folder = os.path.join(base_path, shop_id)
    os.makedirs(shop_folder, exist_ok=True)
    return shop_folder

def get_floor_background_folder(floor_id):
    base_path = current_app.config['UPLOADED_BACKGROUNDS_DEST']
    folder_path = os.path.join(base_path, f"floor_{floor_id}")
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_news_item_folder_path(news_id, create=False):
    base_path = current_app.config['UPLOADED_NEWSIMAGES_DEST']
    item_folder = os.path.join(base_path, str(news_id))
    if create:
        os.makedirs(item_folder, exist_ok=True)
    return item_folder

# --- Функции работы с файлами ---
def generate_unique_filename(original_filename):
    ext = os.path.splitext(original_filename)[1].lower()
    base_name = secure_filename(os.path.splitext(original_filename)[0])
    unique_id = uuid.uuid4().hex[:8]
    max_base_len = 50
    base_name = base_name[:max_base_len]
    filename = f"{int(time())}_{unique_id}_{base_name}{ext}"
    return filename

def move_temp_file(temp_filename, news_id):
    # Нужен доступ к UploadSet 'news_images'
    # Его можно импортировать из myapp/__init__.py
    from . import news_images # Импортируем UploadSet

    if not temp_filename or not temp_filename.startswith('temp_'):
        return temp_filename

    try:
        temp_path = news_images.path(temp_filename) # Используем метод path() UploadSet
    except Exception as e:
         print(f"Ошибка получения пути для временного файла {temp_filename}: {e}")
         return None # Возвращаем None, если путь не найден

    if not os.path.exists(temp_path):
        print(f"Ошибка: Временный файл не найден {temp_path}")
        return None

    original_name_part = temp_filename[len('temp_'):]
    new_filename = generate_unique_filename(original_name_part)
    target_folder = get_news_item_folder_path(news_id, create=True)
    new_path = os.path.join(target_folder, new_filename)

    try:
        shutil.move(temp_path, new_path)
        print(f"Файл перемещен: {temp_path} -> {new_path}")
        return new_filename
    except Exception as e:
        print(f"Ошибка перемещения файла {temp_filename}: {e}")
        try:
            os.remove(temp_path) # Попытка удалить временный файл при ошибке
        except OSError:
            pass
        return None


# --- Функции работы с картами и магазинами ---
def load_maps():
    g.db_used = True
    floors_query = Floor.query.all()
    floors = {floor.id: {"name": floor.name, "filename": floor.filename, "background_filename": floor.background_filename} for floor in floors_query}
    current = CurrentFloor.query.first()

    # Инициализация, если БД пустая
    if not floors_query:
        first_floor = Floor(id="1", name="Первый этаж", filename="", background_filename="")
        db.session.add(first_floor)
        db.session.commit()
        floors["1"] = {"name": "Первый этаж", "filename": "", "background_filename": ""}
        floor_id_for_current = "1"
    else:
        # Убедимся, что есть хотя бы один этаж для current
        floor_id_for_current = next(iter(floors.keys()), None)

    if not current:
        if floor_id_for_current:
             current = CurrentFloor(floor_id=floor_id_for_current)
             db.session.add(current)
             db.session.commit()
        else:
             # Совсем нет этажей, current не может быть создан
             return {"current_floor": None, "floors": floors}

    # Убедимся, что current.floor_id существует в floors
    if current.floor_id not in floors:
         if floor_id_for_current:
             current.floor_id = floor_id_for_current
             db.session.commit()
         else:
              # Странная ситуация: current есть, но этажа нет. Возвращаем как есть.
             return {"current_floor": {"id": current.floor_id}, "floors": floors}


    return {"current_floor": {"id": current.floor_id}, "floors": floors}

def save_maps(maps_data):
    g.db_used = True
    existing_floors = {floor.id: floor for floor in Floor.query.all()}

    # Обновляем или добавляем этажи
    for floor_id, floor_data in maps_data["floors"].items():
        floor = existing_floors.get(floor_id)
        if floor:
            floor.name = floor_data.get("name", floor.name)
            floor.filename = floor_data.get("filename", floor.filename)
            floor.background_filename = floor_data.get("background_filename", floor.background_filename)
        else:
            floor = Floor(
                id=floor_id,
                name=floor_data.get("name", f"Этаж {floor_id}"),
                filename=floor_data.get("filename", ""),
                background_filename=floor_data.get("background_filename", "")
            )
            db.session.add(floor)

    # Обновляем или добавляем текущий этаж
    current_floor_id_data = maps_data.get("current_floor", {}).get("id")
    if current_floor_id_data:
        current = CurrentFloor.query.first()
        if current:
            current.floor_id = current_floor_id_data
        else:
            current = CurrentFloor(floor_id=current_floor_id_data)
            db.session.add(current)
    else:
        # Если в maps_data нет current_floor, не меняем запись в БД
        pass

    db.session.commit()


def parse_svg_and_save_shops(floor_id, filename=None):
    g.db_used = True
    maps_data = load_maps()

    if filename is None:
        filename = maps_data.get("floors", {}).get(floor_id, {}).get("filename")

    if not filename:
        print(f"Предупреждение: Нет имени файла SVG для этажа {floor_id}, парсинг пропущен.")
        return

    filepath = os.path.join(current_app.config['UPLOADED_FILES_DEST'], filename)
    if not os.path.exists(filepath):
        print(f"Ошибка: Файл SVG не найден: {filepath}")
        return

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Ошибка парсинга SVG файла {filepath}: {e}")
        return
    except Exception as e:
        print(f"Неожиданная ошибка при открытии/парсинге SVG {filepath}: {e}")
        return

    namespace_map = {
        'svg': 'http://www.w3.org/2000/svg'
        # Добавь другие пространства имен, если они используются в твоем SVG
    }
    # Функция для добавления префикса пространства имен
    def ns_tag(tag_name):
        return f"{{{namespace_map['svg']}}}{tag_name}"

    # Очистка старых магазинов для этого этажа
    # Важно: удаляем только Shop, но не ShopData, ShopDescription и т.д.!
    Shop.query.filter_by(floor_id=floor_id).delete()
    # db.session.commit() # Коммит лучше делать один раз в конце

    new_shops_to_add = []
    shops_data_to_add = []
    shops_desc_to_add = []
    pavilion_count = 0

    # --- Обработка <rect> ---
    # Используем findall с пространством имен
    for rect in root.findall(f".//{ns_tag('rect')}"):
        pavilion_count += 1
        shop_id = f"pavilion_{pavilion_count}_{floor_id}"

        new_shop = Shop(
            id=shop_id,
            floor_id=floor_id,
            type="rect",
            x=rect.get("x"),
            y=rect.get("y"),
            width=rect.get("width"),
            height=rect.get("height")
        )
        new_shops_to_add.append(new_shop)

        # Создаем ShopData и ShopDescription, только если их еще нет
        if not db.session.get(ShopData, shop_id): # Используем db.session.get для проверки по PK
            shops_data_to_add.append(ShopData(id=shop_id))
        # Проверяем наличие описания (хотя можно и просто добавлять)
        if not ShopDescription.query.filter_by(shop_id=shop_id).first():
             shops_desc_to_add.append(ShopDescription(shop_id=shop_id))

        # Создание <g> и перемещение <rect> (исходная логика)
        g_elem = ET.Element("g", {"id": shop_id})
        g_elem.append(rect)
        # Поиск родителя <rect>
        parent = None
        for p in root.iter():
            if rect in list(p):
                parent = p
                break

        if parent is not None:
            try:
                index = list(parent).index(rect)
                parent.insert(index, g_elem)
                parent.remove(rect)
            except ValueError:
                 print(f"Warning: Could not find rect in parent list during SVG manipulation for {shop_id}.")
                 # Можно попытаться добавить в конец родителя или корня
                 parent.append(g_elem)
                 parent.remove(rect) # Повторная попытка удаления
        else:
            # Если родитель не найден (например, rect был прямо в корне)
            try:
                index = list(root).index(rect)
                root.insert(index, g_elem)
                root.remove(rect)
            except ValueError:
                print(f"Warning: Could not find rect in root list during SVG manipulation for {shop_id}.")
                root.append(g_elem) # Добавляем в конец корня
                root.remove(rect) # Повторная попытка

    # --- Обработка <path> ---
    for path in root.findall(f".//{ns_tag('path')}"):
        # Пропускаем path, если он уже внутри <g> (был обработан ранее или так в файле)
        parent_g = None
        for p in root.iter(ns_tag('g')):
             if path in list(p):
                 parent_g = p
                 break
        if parent_g is not None:
            continue # Этот path уже в группе, пропускаем

        pavilion_count += 1
        shop_id = f"pavilion_{pavilion_count}_{floor_id}"

        new_shop = Shop(
            id=shop_id,
            floor_id=floor_id,
            type="path",
            d=path.get("d")
        )
        new_shops_to_add.append(new_shop)

        if not db.session.get(ShopData, shop_id):
            shops_data_to_add.append(ShopData(id=shop_id))
        if not ShopDescription.query.filter_by(shop_id=shop_id).first():
             shops_desc_to_add.append(ShopDescription(shop_id=shop_id))


        # Создание <g> и перемещение <path>
        g_elem = ET.Element("g", {"id": shop_id})
        g_elem.append(path)
        # Поиск родителя <path>
        parent = None
        for p in root.iter():
            if path in list(p):
                parent = p
                break

        if parent is not None:
             try:
                 index = list(parent).index(path)
                 parent.insert(index, g_elem)
                 parent.remove(path)
             except ValueError:
                 print(f"Warning: Could not find path in parent list during SVG manipulation for {shop_id}.")
                 parent.append(g_elem)
                 parent.remove(path)
        else:
             try:
                 index = list(root).index(path)
                 root.insert(index, g_elem)
                 root.remove(path)
             except ValueError:
                 print(f"Warning: Could not find path in root list during SVG manipulation for {shop_id}.")
                 root.append(g_elem)
                 root.remove(path)


    # Очистка пространств имен из тегов и атрибутов (опционально, но полезно)
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]  # Удаляем namespace из тега
        for attr in list(elem.attrib):
            if '}' in attr:
                new_attr = attr.split('}', 1)[1]
                elem.attrib[new_attr] = elem.attrib.pop(attr) # Удаляем namespace из атрибута
            # Удаляем бесполезные xmlns: префиксы, кроме основного xmlns
            if attr.startswith('xmlns:') and attr != 'xmlns':
                del elem.attrib[attr]
    # Устанавливаем основной namespace
    root.set('xmlns', namespace_map['svg'])


    # Сохранение измененного SVG
    try:
        # Убираем xml_declaration для совместимости с браузерами, если нужно
        # tree.write(filepath, encoding="unicode") # unicode для utf-8 без декларации
        tree.write(filepath, encoding="utf-8", xml_declaration=True)
        print(f"SVG файл успешно обновлен: {filepath}")
    except Exception as e:
        print(f"Ошибка записи в SVG файл {filepath}: {e}")
        # Важно: если запись не удалась, не стоит сохранять изменения в БД
        return # Выходим, чтобы не сохранять магазины

    # Сохранение новых записей в БД (одним коммитом)
    try:
        if new_shops_to_add:
            db.session.add_all(new_shops_to_add)
        if shops_data_to_add:
             db.session.add_all(shops_data_to_add)
        if shops_desc_to_add:
             db.session.add_all(shops_desc_to_add)
        db.session.commit()
        print(f"Добавлено/обновлено {len(new_shops_to_add)} магазинов в БД для этажа {floor_id}.")
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка сохранения магазинов в БД для этажа {floor_id}: {e}")


def load_all_shops(visibility=None):
    g.db_used = True
    maps_data = load_maps() # Получаем актуальные данные по этажам

    # # Опционально: Проверить и распарсить SVG, если магазинов для этажа нет в БД
    # for floor_id, floor_data in maps_data.get("floors", {}).items():
    #     if floor_data.get("filename"):
    #         shop_count = Shop.query.filter_by(floor_id=floor_id).count()
    #         if shop_count == 0:
    #             print(f"Магазины для этажа {floor_id} отсутствуют в БД, запускаю парсинг SVG...")
    #             parse_svg_and_save_shops(floor_id, floor_data["filename"])
    #             # Перезагружаем maps_data, если parse_svg_and_save_shops мог изменить его (маловероятно)
    #             # maps_data = load_maps()

    shops_result = []
    # Строим базовый запрос к Shop
    query = db.session.query(Shop).options(
        db.joinedload(Shop.shop_data).joinedload(ShopData.category), # Предзагрузка ShopData и Category
        db.joinedload(Shop.shop_data).joinedload(ShopData.subcategories), # Предзагрузка подкатегорий
        # db.selectinload(Shop.shop_descriptions), # Можно использовать selectinload для коллекций
        # db.selectinload(Shop.shop_gallery_images)
    )


    # Фильтр по видимости, если указан
    if visibility is not None:
        # Присоединяем ShopData для фильтрации и фильтруем
        query = query.join(Shop.shop_data).filter(ShopData.visibility == visibility)

    # Выполняем запрос
    all_shops_from_db = query.all()

    # Обрабатываем результаты
    for shop in all_shops_from_db:
        shop_data = shop.shop_data # Доступ к предзагруженным данным
        shop_details = {
            "id": shop.id,
            "floor_id": shop.floor_id,
            "floor_name": maps_data.get("floors", {}).get(shop.floor_id, {"name": "Неизв."})["name"],
            "type": shop.type,
            "x": shop.x,
            "y": shop.y,
            "width": shop.width,
            "height": shop.height,
            "d": shop.d,
            "shop_name": "Свободный павильон",
            "shop_logo": url_for('static', filename='images/vector/static-logo.svg'), # Дефолтное лого
            "shop_banner": None,
            "scheme_logo": None,
            "scheme_logo_width": 30,
            "scheme_logo_height": 30,
            "scheme_logo_x": 0,
            "scheme_logo_y": 0,
            "web_text": "Сайт",
            "web_url": None,
            "work_time": "10:00-22:00",
            "descriptions": ["Свободный павильон — отличная возможность для вашего бизнеса или проекта."],
            "gallery_images": [],
            "category": None,
            "category_id": None,
            "category_icon": None,
            "category_color": None,
            "subcategories": [],
            "visibility": False,
            "visible_in_tenants": False,
            "data_version": int(time()) # Версия данных для кеширования JS
        }

        if shop_data:
            shop_details.update({
                "shop_name": shop_data.shop_name or "Свободный павильон",
                "web_text": shop_data.web_text or "Сайт",
                "web_url": shop_data.web_url,
                "work_time": shop_data.work_time or "10:00-22:00",
                "scheme_logo_width": shop_data.scheme_logo_width or 30,
                "scheme_logo_height": shop_data.scheme_logo_height or 30,
                "scheme_logo_x": shop_data.scheme_logo_x or 0,
                "scheme_logo_y": shop_data.scheme_logo_y or 0,
                "visibility": shop_data.visibility,
                "visible_in_tenants": shop_data.visible_in_tenants,
                "category_id": shop_data.category_id,
            })

            # Логотипы и баннер
            if shop_data.shop_logo:
                logo_path = f"uploads/shop_logos/{shop.id}/{shop_data.shop_logo}"
                try: shop_details["shop_logo"] = url_for('static', filename=logo_path, _t=int(time()))
                except: pass # Оставляем дефолтное лого
            if shop_data.shop_banner:
                banner_path = f"uploads/shop_logos/{shop.id}/{shop_data.shop_banner}"
                try: shop_details["shop_banner"] = url_for('static', filename=banner_path, _t=int(time()))
                except: pass
            if shop_data.scheme_logo:
                scheme_logo_path = f"uploads/shop_logos/{shop.id}/{shop_data.scheme_logo}"
                try: shop_details["scheme_logo"] = url_for('static', filename=scheme_logo_path, _t=int(time()))
                except: pass

            # Категория
            if shop_data.category:
                shop_details["category"] = shop_data.category.name
                shop_details["category_color"] = shop_data.category.color
                if shop_data.category.icon_path:
                    icon_path = f"uploads/category_icons/{shop_data.category.icon_path}"
                    try: shop_details["category_icon"] = url_for('static', filename=icon_path, _t=int(time()))
                    except: pass

            # Подкатегории
            if shop_data.subcategories:
                shop_details["subcategories"] = [{"id": sub.id, "name": sub.name} for sub in shop_data.subcategories]

        # Описания (Загружаем отдельно, если не использовали selectinload)
        descriptions = ShopDescription.query.filter_by(shop_id=shop.id).all()
        if descriptions:
            shop_details["descriptions"] = [desc.description for desc in descriptions]

        # Галерея (Загружаем отдельно, если не использовали selectinload)
        gallery = ShopGallery.query.filter_by(shop_id=shop.id).all()
        if gallery:
            gallery_urls = []
            for img in gallery:
                img_path = f"uploads/shop_logos/{shop.id}/{img.image_path}"
                try: gallery_urls.append(url_for('static', filename=img_path, _t=int(time())))
                except: pass
            shop_details["gallery_images"] = gallery_urls

        shops_result.append(shop_details)

    return shops_result


# --- Функции работы с контентом ---
def load_content():
    g.db_used = True
    return {item.key: item.value for item in Content.query.all()}

def save_content(content_dict):
    g.db_used = True
    existing_content = {item.key: item for item in Content.query.all()}
    for key, value in content_dict.items():
        if key in existing_content:
            # Обновляем только если значение изменилось, чтобы избежать лишних записей в БД
            if existing_content[key].value != str(value):
                 existing_content[key].value = str(value)
        else:
            # Добавляем новый элемент контента
            new_item = Content(key=key, value=str(value))
            db.session.add(new_item)
    db.session.commit()

# --- Функции работы с Капчей ---
def generate_captcha():
    length = 5
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    captcha_text = ''.join(random.choice(chars) for _ in range(length))
    image_captcha_generator = ImageCaptcha(width=160, height=60)
    image_data = image_captcha_generator.generate_image(captcha_text)
    buffered = io.BytesIO()
    image_data.save(buffered, format="PNG")
    captcha_img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return captcha_text, captcha_img_b64

# --- Прочие утилиты ---
def get_first_floor_id(maps_data):
    if maps_data and maps_data.get("floors"):
        # Сортируем ключи (этажи), чтобы предсказуемо получить первый (например, '1')
        sorted_floor_ids = sorted(maps_data["floors"].keys(), key=lambda x: int(x) if x.isdigit() else float('inf'))
        if sorted_floor_ids:
            return sorted_floor_ids[0]
    return None # Возвращаем None, если этажей нет