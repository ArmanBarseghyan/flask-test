# myapp/routes/user.py
from flask import Blueprint, render_template, request, redirect, url_for, session, \
                  flash, send_from_directory, send_file, make_response, jsonify, \
                  current_app # Используем current_app вместо app
from time import time
import os

from .. import db # Импорт db из __init__.py пакета
from ..models import Floor, CurrentFloor, Content, Shop, Category, Subcategory, \
                     ContactMessage, NewsItem, ShopData, ShopDescription, ShopGallery
from ..utils import load_maps, save_maps, load_content, save_content, load_all_shops, \
                    get_first_floor_id, generate_captcha # Импорт утилит

# Создаем Blueprint
user_bp = Blueprint('user', __name__) # 'user' - имя блюпринта

@user_bp.route("/")
def index():
    maps_data = load_maps()
    content = load_content()
    categories = Category.query.all()
    # shops = load_all_shops() # Не загружаем все магазины здесь, если они не нужны прямо на главной (кроме карты)

    # Загрузка новостей и акций для главной
    published_items = NewsItem.query.filter_by(
        is_published=True
    ).order_by(
        NewsItem.published_at.desc(), NewsItem.created_at.desc()
    ).limit(8).all()

    news_list_for_template = []
    promo_list_for_template = []
    news_count = 0
    promo_count = 0
    max_items_per_type = 4

    for item in published_items:
        item_data = {
            'id': item.id,
            'title': item.title,
            'type': item.type,
            'published_at': item.published_at or item.created_at,
            'banner_url': None,
            'short_description': item.short_description
        }
        if item.banner_image:
            try:
                banner_path = f"uploads/news_content/{item.id}/{item.banner_image}"
                item_data['banner_url'] = url_for('static', filename=banner_path, _external=False, _t=int(time()))
            except Exception:
                item_data['banner_url'] = None

        if item.type == 'news' and news_count < max_items_per_type:
            news_list_for_template.append(item_data)
            news_count += 1
        elif item.type == 'promo' and promo_count < max_items_per_type:
            promo_list_for_template.append(item_data)
            promo_count += 1

        if news_count >= max_items_per_type and promo_count >= max_items_per_type:
            break

    # Логика выбора этажа для карты
    current_floor_id = None
    if maps_data["floors"]:
        floor_id_arg = request.args.get('id')
        if floor_id_arg and floor_id_arg in maps_data["floors"]:
            # Не меняем дефолтный этаж в БД при простом переходе по ссылке
            current_floor_id = floor_id_arg
        elif maps_data.get("current_floor") and maps_data["current_floor"]["id"] in maps_data["floors"]:
             current_floor_id = maps_data["current_floor"]["id"]
        else:
            # Если current_floor указывает на несуществующий этаж, берем первый
            first_floor_id = get_first_floor_id(maps_data)
            current_floor_id = first_floor_id

    # Загрузка магазинов ТОЛЬКО для карты (если map.js их требует)
    shops_for_map = load_all_shops(visibility=True) # Загружаем только видимые для карты

    return render_template(
        "user/index.html", # Путь к шаблону относительно папки templates/
        maps=maps_data,
        current_floor_id=current_floor_id,
        content=content,
        categories=categories,
        shops=shops_for_map, # Передаем магазины для карты
        news_list=news_list_for_template,
        promo_list=promo_list_for_template,
        timestamp=int(time())
    )

@user_bp.route("/how-to-get")
def how_to_get():
    content = load_content()
    return render_template("user/how_to_get.html", content=content)

@user_bp.route("/for_tenants")
def for_tenants():
    content = load_content()
    floor_id = request.args.get('floor_id')
    maps_data = load_maps()

    # Загружаем все магазины, видимые для арендаторов
    all_tenant_shops = load_all_shops() # Загружаем все
    all_tenant_shops = [shop for shop in all_tenant_shops if shop.get("visible_in_tenants")]

    # Фильтруем по этажу, если выбран
    shops_list = all_tenant_shops
    if floor_id and floor_id in maps_data.get("floors", {}):
        shops_list = [shop for shop in all_tenant_shops if shop.get("floor_id") == floor_id]

    shop_count = len(shops_list)
    floors = maps_data.get("floors", {})

    # Считаем количество магазинов (видимых для арендаторов) на каждом этаже
    floor_counts = {}
    for shop in all_tenant_shops:
        f_id = shop.get("floor_id")
        if f_id:
            floor_counts[f_id] = floor_counts.get(f_id, 0) + 1

    return render_template(
        "user/for_tenants.html",
        content=content,
        shops=shops_list,
        shop_count=shop_count,
        floors=floors,
        selected_floor=floor_id,
        floor_counts=floor_counts
    )

@user_bp.route("/contacts", methods=["GET", "POST"])
def contacts():
    content = load_content()
    captcha_img_b64 = None
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message_text = request.form.get('message')
        captcha_input = request.form.get('captcha')
        correct_captcha = session.get('captcha_text')
        session.pop('captcha_text', None) # Удаляем капчу из сессии

        if not all([name, email, phone, message_text, captcha_input]):
            flash("Пожалуйста, заполните все обязательные поля, включая капчу.", "contact_error")
        elif not correct_captcha or captcha_input.lower() != correct_captcha.lower():
            flash("Неверный текст с картинки (CAPTCHA). Попробуйте еще раз.", "contact_error")
        else:
            try:
                new_message = ContactMessage(name=name, email=email, phone=phone, message=message_text)
                db.session.add(new_message)
                db.session.commit()
                flash("Ваше сообщение успешно отправлено! Мы скоро свяжемся с вами.", "contact_success")
                return redirect(url_for('user.contacts')) # Используем имя блюпринта 'user'
            except Exception as e:
                db.session.rollback()
                flash("Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.", "contact_error")
                print(f"Ошибка сохранения ContactMessage: {e}")

        # Если были ошибки или POST неудачный, генерируем новую капчу для повторного показа формы
        captcha_text, captcha_img_b64 = generate_captcha()
        session['captcha_text'] = captcha_text

    else: # GET request
        captcha_text, captcha_img_b64 = generate_captcha()
        session['captcha_text'] = captcha_text

    return render_template("user/contacts.html", content=content, captcha_image=captcha_img_b64)


@user_bp.route('/refresh-captcha')
def refresh_captcha():
    captcha_text, captcha_img_b64 = generate_captcha()
    session['captcha_text'] = captcha_text
    return jsonify({'image_b64': captcha_img_b64})


@user_bp.route("/shops")
def shops():
    content = load_content()
    category_id = request.args.get('category_id')
    # Получаем ID подкатегорий как список строк
    subcategory_ids_str = request.args.get('subcategory_ids', '').split(',')
    # Убираем пустые строки, если они есть (например, если subcategory_ids='')
    subcategory_ids = [sid for sid in subcategory_ids_str if sid]

    # Загружаем только видимые магазины
    shops_list = load_all_shops(visibility=True)

    # Фильтрация по категории
    if category_id:
        try:
            cat_id_int = int(category_id)
            shops_list = [s for s in shops_list if s.get('category_id') == cat_id_int]
        except (ValueError, TypeError):
            pass # Игнорируем невалидный category_id

    # Фильтрация по подкатегориям
    if subcategory_ids:
        # Преобразуем искомые ID в int для сравнения
        try:
            search_sub_ids_int = {int(sid) for sid in subcategory_ids}
            filtered_shops = []
            for shop in shops_list:
                 # Получаем ID подкатегорий магазина (они уже int из load_all_shops)
                 shop_sub_ids = {sub['id'] for sub in shop.get('subcategories', [])}
                 # Проверяем пересечение множеств
                 if shop_sub_ids.intersection(search_sub_ids_int):
                     filtered_shops.append(shop)
            shops_list = filtered_shops
        except (ValueError, TypeError):
            pass # Игнорируем невалидные subcategory_ids

    shop_count = len(shops_list)
    categories = Category.query.order_by(Category.name).all() # Загружаем для фильтров

    return render_template(
        "user/shops.html",
        content=content,
        shops=shops_list,
        shop_count=shop_count,
        categories=categories,
        selected_category_id=category_id, # Передаем для подсветки фильтра
        selected_subcategory_ids=subcategory_ids # Передаем для подсветки фильтра
    )


@user_bp.route("/shop/<shop_id>")
def shop_detail(shop_id):
    content = load_content()
    maps_data = load_maps() # Нужен для floor_name

    # Запрос магазина с предзагрузкой
    shop = db.session.query(Shop).options(
        db.joinedload(Shop.shop_data).joinedload(ShopData.category),
        db.joinedload(Shop.shop_data).joinedload(ShopData.subcategories),
        # db.selectinload(Shop.shop_descriptions), # Если нужно
        # db.selectinload(Shop.shop_gallery_images) # Если нужно
    ).get(shop_id) # Получаем объект Shop по ID

    if not shop:
        return render_template("user/nonfoundpage.html", content=content), 404

    shop_data = shop.shop_data # Доступ к данным через relationship

    # Проверяем видимость магазина для обычных пользователей
    if not shop_data or not shop_data.visibility:
         # Если пользователь не админ, показываем 404
         if "username" not in session:
             return render_template("user/nonfoundpage.html", content=content), 404
         # Админ может видеть невидимые магазины
         flash("Внимание: Этот магазин скрыт для обычных пользователей.", "warning")


    shop_details = {
        "id": shop.id,
        "floor_id": shop.floor_id,
        "floor_name": maps_data.get("floors", {}).get(shop.floor_id, {"name": "Этаж?"})["name"],
        "shop_name": "Название не указано",
        "work_time": "-",
        "web_text": "Сайт",
        "web_url": None,
        "visibility": False, # Дефолт
        "shop_logo": url_for('static', filename='images/vector/static-logo.svg'),
        "shop_banner": None,
        "category": None,
        "category_icon": None,
        "category_color": None, # Добавляем цвет категории
        "subcategories": [],
        "descriptions": ["Описание отсутствует."],
        "gallery_images": [],
        "is_admin": "username" in session,
        "data_version": int(time())
    }

    if shop_data:
        shop_details.update({
            "shop_name": shop_data.shop_name or "Название не указано",
            "work_time": shop_data.work_time or "-",
            "web_text": shop_data.web_text or "Сайт",
            "web_url": shop_data.web_url,
            "visibility": shop_data.visibility
        })

        # Лого и баннер
        if shop_data.shop_logo:
            logo_path = f"uploads/shop_logos/{shop.id}/{shop_data.shop_logo}"
            try: shop_details["shop_logo"] = url_for('static', filename=logo_path, _t=int(time()))
            except: pass
        if shop_data.shop_banner:
            banner_path = f"uploads/shop_logos/{shop.id}/{shop_data.shop_banner}"
            try: shop_details["shop_banner"] = url_for('static', filename=banner_path, _t=int(time()))
            except: pass

        # Категория
        if shop_data.category:
            shop_details["category"] = shop_data.category.name
            shop_details["category_color"] = shop_data.category.color # Получаем цвет
            if shop_data.category.icon_path:
                icon_path = f"uploads/category_icons/{shop_data.category.icon_path}"
                try: shop_details["category_icon"] = url_for('static', filename=icon_path, _t=int(time()))
                except: pass

        # Подкатегории
        shop_details["subcategories"] = [] # Инициализируем пустым списком
        if shop_data and shop_data.subcategories:
            # --- ИЗМЕНЕНО ЗДЕСЬ ---
            # Создаем список словарей {id, name}
            shop_details["subcategories"] = [
                {"id": sub.id, "name": sub.name}
                for sub in shop_data.subcategories
            ]
    # Описания (загружаем отдельно)
    descriptions = ShopDescription.query.filter_by(shop_id=shop.id).all()
    if descriptions:
        shop_details["descriptions"] = [desc.description for desc in descriptions]

    # Галерея (загружаем отдельно)
    gallery_images = ShopGallery.query.filter_by(shop_id=shop.id).all()
    if gallery_images:
        temp_gallery = []
        for img in gallery_images:
            img_path = f"uploads/shop_logos/{shop.id}/{img.image_path}"
            try: temp_gallery.append(url_for('static', filename=img_path, _t=int(time())))
            except: pass
        shop_details["gallery_images"] = temp_gallery

    # Связанные ОПУБЛИКОВАННЫЕ новости/акции
    related_news = NewsItem.query.filter_by(
        shop_id=shop_id,
        is_published=True
    ).order_by(
        NewsItem.published_at.desc(), NewsItem.created_at.desc()
    ).limit(6).all()

    news_for_template = []
    for news_item in related_news:
        item_data = {
            'id': news_item.id,
            'title': news_item.title,
            'type': news_item.type,
            'published_at': news_item.published_at or news_item.created_at,
            'banner_url': None
        }
        if news_item.banner_image:
             try:
                 banner_path = f"uploads/news_content/{news_item.id}/{news_item.banner_image}"
                 item_data['banner_url'] = url_for('static', filename=banner_path, _t=int(time()))
             except: pass
        news_for_template.append(item_data)

    # Ответ на AJAX запрос
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Не включаем is_admin в AJAX ответ для пользователя, если не нужно
        ajax_response = shop_details.copy()
        # ajax_response["is_admin"] = "username" in session # Раскомментировать, если JS это ожидает
        return jsonify(ajax_response)

    # Рендеринг HTML шаблона
    return render_template(
        "user/shop_detail.html",
        shop=shop_details,
        content=content,
        related_news=news_for_template
    )

@user_bp.route("/about")
def about():
    content = load_content()
    about_html = content.get('about_page_content', '<p>Информация о торговом центре.</p>')
    return render_template("user/about.html",
                           content=content,
                           about_html=about_html)

@user_bp.route("/news")
def news_list(): # Переименовал, чтобы не конфликтовать с функцией news()
    content = load_content()
    # Загружаем все опубликованные новости и акции, сортируем
    news_items_query = NewsItem.query.filter_by(is_published=True).order_by(
        NewsItem.published_at.desc(), NewsItem.created_at.desc()
    )
    # Пагинация (пример, можно настроить)
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Количество элементов на странице
    pagination = news_items_query.paginate(page=page, per_page=per_page, error_out=False)
    news_items = pagination.items

    # Подготовка данных для шаблона (генерация URL баннеров)
    items_for_template = []
    for item in news_items:
        item_data = {
            'id': item.id,
            'title': item.title,
            'type': item.type,
            'short_description': item.short_description,
            'published_at': item.published_at or item.created_at,
            'banner_url': None
        }
        if item.banner_image:
            try:
                banner_path = f"uploads/news_content/{item.id}/{item.banner_image}"
                item_data['banner_url'] = url_for('static', filename=banner_path, _t=int(time()))
            except: pass
        items_for_template.append(item_data)


    return render_template(
        "user/news.html",
        content=content,
        news_items=items_for_template, # Передаем подготовленные данные
        pagination=pagination # Передаем объект пагинации
        )

@user_bp.route("/news/<int:news_id>")
def user_news_detail(news_id):
    news_item = NewsItem.query.options(
        db.joinedload(NewsItem.shop).joinedload(Shop.shop_data)
    ).filter_by(id=news_id, is_published=True).first_or_404()

    shop_info_for_template = None
    if news_item.shop and news_item.shop.shop_data:
        shop_info_for_template = {
            'id': news_item.shop_id,
            'name': news_item.shop.shop_data.shop_name or f"Магазин {news_item.shop_id}"
        }

    rendered_blocks = []
    if isinstance(news_item.content_blocks, list):
        for block in news_item.content_blocks:
            if not isinstance(block, dict): continue
            block_copy = block.copy()
            block_type = block_copy.get('type')

            if block_type == 'image' and block_copy.get('url'):
                try:
                    filename_path = f"uploads/news_content/{news_id}/{block_copy['url']}"
                    block_copy['full_url'] = url_for('static', filename=filename_path, _t=int(time()))
                except Exception as e:
                    print(f"Ошибка генерации URL для блока {block_copy.get('url')}: {e}")
                    block_copy['full_url'] = None
            rendered_blocks.append(block_copy)

    content = load_content()
    banner_url = None
    if news_item.banner_image:
        try:
            banner_filename_path = f"uploads/news_content/{news_id}/{news_item.banner_image}"
            banner_url = url_for('static', filename=banner_filename_path, _t=int(time()))
        except Exception as e:
            print(f"Ошибка генерации URL для баннера {news_item.banner_image}: {e}")

    return render_template("user/news_detail.html",
                           item=news_item,
                           rendered_blocks=rendered_blocks,
                           content=content,
                           banner_url=banner_url,
                           shop_info=shop_info_for_template
                          )

@user_bp.route("/shema")
def shema():
    maps_data = load_maps()
    content = load_content()
    # areas = content.get("areas", []) # Ключ 'areas' вроде не используется в коде? Если да, раскомментировать.
    categories = Category.query.all()
    shops_for_map = load_all_shops(visibility=True) # Только видимые для схемы

    current_floor_id = None
    if not maps_data.get("floors"):
        # Случай, когда этажей нет совсем
         pass
    else:
        floor_id_arg = request.args.get('id')
        # Проверяем, валиден ли запрошенный этаж
        if floor_id_arg and floor_id_arg in maps_data["floors"]:
            current_floor_id = floor_id_arg
            # НЕ сохраняем его как дефолтный при обычном GET запросе
            # maps_data["current_floor"]["id"] = floor_id_arg
            # save_maps(maps_data)
        else:
             # Берем дефолтный этаж из БД
             current_floor_data = maps_data.get("current_floor")
             if current_floor_data and current_floor_data["id"] in maps_data["floors"]:
                  current_floor_id = current_floor_data["id"]
             else:
                  # Если дефолтный некорректен, берем первый доступный
                  current_floor_id = get_first_floor_id(maps_data)
                  # Опционально: можно обновить дефолтный в БД, если он был невалиден
                  # if current_floor_id and current_floor_data:
                  #     maps_data["current_floor"]["id"] = current_floor_id
                  #     save_maps(maps_data)


    return render_template(
        "user/shema.html",
        maps=maps_data,
        current_floor_id=current_floor_id,
        # areas=areas, # Если нужно
        categories=categories,
        shops=shops_for_map, # Магазины для отображения на схеме
        timestamp=int(time())
    )

@user_bp.route("/privacy")
def privacy():
    content = load_content()
    # Предполагаем, что текст политики хранится в ключе 'privacy_policy_content'
    privacy_html = content.get('privacy_policy_content', '<p>Политика конфиденциальности не найдена.</p>')
    return render_template("user/privacy.html", content=content, privacy_html=privacy_html)


@user_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Эта функция больше не нужна, если static/uploads настроен правильно
    # Flask автоматически отдает файлы из static
    # Если же UPLOADED_FILES_DEST указывает ВНЕ папки static приложения,
    # то нужен будет такой роут, но настроенный на отдачу из нужной директории.
    # Например, для UPLOADED_BACKGROUNDS_DEST:
    # if filename.startswith('floor_'): # Проверка, что это фон этажа
    #      return send_from_directory(current_app.config['UPLOADED_BACKGROUNDS_DEST'], filename)

    # Для основного UPLOADED_FILES_DEST (SVG карты)
    # return send_from_directory(current_app.config['UPLOADED_FILES_DEST'], filename)

    # Пока закомментируем, т.к. предполагаем, что все в static
    return "Route not configured for this path", 404


# --- AJAX / API Routes (можно вынести в api.py) ---

@user_bp.route("/get_categories")
def user_get_categories():
    try:
        categories = Category.query.options(db.selectinload(Category.subcategories)).order_by(Category.name).all()
        categories_data = [
            {
                "id": cat.id,
                "name": cat.name,
                "icon_url": url_for('static', filename=f"uploads/category_icons/{cat.icon_path}", _t=int(time())) if cat.icon_path else None,
                "color": cat.color, # Добавляем цвет
                "subcategories": [
                    {"id": sub.id, "name": sub.name}
                    for sub in sorted(cat.subcategories, key=lambda s: s.name) # Сортируем подкатегории
                ]
            } for cat in categories
        ]
        return jsonify({"categories": categories_data})
    except Exception as e:
        print(f"Ошибка при получении категорий: {e}")
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/shops/all', methods=['GET'])
def get_all_shops_api():
    try:
        # Загружаем только видимые магазины для карты/поиска
        shops = load_all_shops(visibility=True)
        # Добавляем data_version уже в load_all_shops, здесь просто возвращаем
        return jsonify(shops)
    except Exception as e:
        print(f"Ошибка при получении всех магазинов (API): {e}")
        return jsonify({"error": "Internal server error"}), 500

# Добавь сюда остальные AJAX роуты, если они нужны пользователям