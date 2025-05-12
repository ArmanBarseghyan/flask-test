# myapp/models.py
from . import db # Импортируем db из __init__.py текущего пакета
from datetime import datetime

# --- ТАБЛИЦА СВЯЗИ Many-to-Many ---
# Ее нужно определить ДО моделей, которые ее используют
shop_subcategory = db.Table('shop_subcategory',
    db.Column('shop_id', db.String(50), db.ForeignKey('shop_data.id'), primary_key=True),
    db.Column('subcategory_id', db.Integer, db.ForeignKey('subcategory.id'), primary_key=True)
)

# --- МОДЕЛИ ---
class Floor(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(100), default="")
    background_filename = db.Column(db.String(100), default="")

class CurrentFloor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.String(10), db.ForeignKey('floor.id'), nullable=False)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Shop(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    floor_id = db.Column(db.String(10), db.ForeignKey('floor.id'), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    x = db.Column(db.String(10), nullable=True)
    y = db.Column(db.String(10), nullable=True)
    width = db.Column(db.String(10), nullable=True)
    height = db.Column(db.String(10), nullable=True)
    d = db.Column(db.Text, nullable=True)
    # Связи
    shop_data = db.relationship("ShopData", uselist=False, backref="shop")
    shop_descriptions = db.relationship("ShopDescription", backref="shop", lazy='dynamic')
    shop_gallery_images = db.relationship("ShopGallery", backref="shop", lazy='dynamic')
    news_items = db.relationship('NewsItem', backref='shop', lazy=True) # Добавлено backref из NewsItem

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    icon_path = db.Column(db.String(100), nullable=True)
    color = db.Column(db.String(7), default="#FF5733")
    # Связи
    subcategories = db.relationship('Subcategory', backref='category', lazy=True)
    shops = db.relationship('ShopData', backref='category', lazy='dynamic') # Используем lazy='dynamic' если много магазинов

class Subcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    icon_path = db.Column(db.String(100), nullable=True)
    # Связь с ShopData (через shop_subcategory) определена в ShopData

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class NewsItem(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.String(10), nullable=False) # 'news' или 'promo'
    title = db.Column(db.String(200), nullable=False)
    short_description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), nullable=True) # Для отображения в списках (если нужно)
    banner_image = db.Column(db.String(100), nullable=True) # Главное изображение для списка/деталей
    content_blocks = db.Column(db.JSON, nullable=False, default=lambda: []) # Структурированный контент
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    published_at = db.Column(db.DateTime, index=True, default=datetime.utcnow) # Для сортировки опубликованных
    is_published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    shop_id = db.Column(db.String(50), db.ForeignKey('shop.id'), nullable=True) # Связь с магазином (если новость/акция от него)
    # Связь shop определена через backref в модели Shop

class ShopData(db.Model):
    id = db.Column(db.String(50), db.ForeignKey('shop.id'), primary_key=True)
    shop_name = db.Column(db.String(100), default="Свободный павильон")
    shop_logo = db.Column(db.String(100), nullable=True)
    shop_banner = db.Column(db.String(100), nullable=True)
    scheme_logo = db.Column(db.String(100), nullable=True)
    # Размеры и позиция логотипа на схеме (если нужны прямо здесь)
    shop_logo_width = db.Column(db.Integer, default=100)
    shop_logo_height = db.Column(db.Integer, default=100)
    shop_logo_x = db.Column(db.Integer, default=0)
    shop_logo_y = db.Column(db.Integer, default=0)
    # Размеры и позиция баннера (если нужны)
    shop_banner_width = db.Column(db.Integer, default=300)
    shop_banner_height = db.Column(db.Integer, default=150)
    shop_banner_x = db.Column(db.Integer, default=0)
    shop_banner_y = db.Column(db.Integer, default=0)
    # Размеры и позиция лого на схеме
    scheme_logo_width = db.Column(db.Integer, default=30)
    scheme_logo_height = db.Column(db.Integer, default=30)
    scheme_logo_x = db.Column(db.Integer, default=0)
    scheme_logo_y = db.Column(db.Integer, default=0)
    web_text = db.Column(db.String(100), default="Сайт")
    web_url = db.Column(db.String(200), nullable=True)
    work_time = db.Column(db.String(50), default="10:00-22:00")
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    visibility = db.Column(db.Boolean, default=False) # Видимость на карте/в поиске
    visible_in_tenants = db.Column(db.Boolean, default=False) # Видимость в разделе "Арендаторам"
    # Связи
    # category определена через backref в Category
    # shop определена через backref в Shop
    subcategories = db.relationship('Subcategory', secondary=shop_subcategory, backref='shops')

class ShopDescription(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shop_id = db.Column(db.String(50), db.ForeignKey('shop.id'), nullable=False)
    description = db.Column(db.Text, default="Свободный павильон — отличная возможность для вашего бизнеса или проекта.")
    # shop определена через backref в Shop

class ShopGallery(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    shop_id = db.Column(db.String(50), db.ForeignKey('shop.id'), nullable=False)
    image_path = db.Column(db.String(100), nullable=False)
    # shop определена через backref в Shop