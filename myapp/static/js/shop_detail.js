// static/js/shop_detail.js

let selectedCategoryId = '';        // ID выбранной основной категории
let selectedSubcategoryIds = [];    // Массив ID выбранных подкатегорий
let categoriesData = [];            // Кэш данных категорий и подкатегорий

/**
 * Добавляет новое поле textarea для описания магазина.
 */
function addTextarea() {
    const container = document.querySelector('.textarea-box');
    if (!container) return;

    const newTextareaContainer = document.createElement('div');
    newTextareaContainer.className = 'textarea-item';
    newTextareaContainer.innerHTML = `
        <textarea name="description" rows="5" placeholder="Введите описание..."></textarea>
        <button type="button" class="button button-danger button-sm" onclick="this.parentElement.remove()">Удалить</button>
    `;
    container.appendChild(newTextareaContainer);
}

/**
 * Отправляет запрос на удаление изображения из галереи магазина.
 * @param {number} imageId - ID изображения галереи.
 * @param {string} shopId - ID магазина.
 */
function deleteImage(imageId, shopId) {
    if (!imageId || !shopId) return;
    if (confirm('Вы уверены, что хотите удалить это изображение?')) {
        const url = `/admin/shop/${shopId}/delete_gallery_image/${imageId}`;
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(response => {
            if (response.ok) {
                const imageElement = document.querySelector(`.image[data-image-id="${imageId}"]`);
                if (imageElement) {
                    imageElement.remove();
                }
                showToast('Изображение успешно удалено.'); // Используем toast
            } else {
                response.json().then(errData => {
                    showToast(`Ошибка удаления: ${errData.error || response.statusText}`, 'error');
                }).catch(() => {
                     showToast(`Ошибка удаления: ${response.statusText}`, 'error');
                });
            }
        })
        .catch(error => {
             console.error('Ошибка fetch при удалении изображения:', error);
             showToast('Произошла ошибка сети при удалении изображения.', 'error');
        });
    }
}

/**
 * Отправляет запрос на очистку папки с файлами магазина.
 * @param {string} shopId - ID магазина.
 */
function clearShopFolder(shopId) {
    if (!shopId) return;
    if (confirm('ВНИМАНИЕ!\nВы уверены, что хотите УДАЛИТЬ ВСЕ ФАЙЛЫ (логотипы, баннеры, галерею) для этого магазина?\n\nЗаписи в базе данных об этих файлах также будут очищены.\nЭто действие НЕОБРАТИМО!')) {
        const url = `/admin/shop/${shopId}/clear_folder`;
        fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() }
        })
        .then(response => {
            if (response.ok) {
                showToast('Папка магазина и связанные записи очищены. Перезагрузка...');
                setTimeout(() => location.reload(), 1500); // Перезагрузка с небольшой задержкой
            } else {
                 response.json().then(errData => {
                     showToast(`Ошибка очистки папки: ${errData.error || response.statusText}`, 'error');
                 }).catch(() => {
                      showToast(`Ошибка очистки папки: ${response.statusText}`, 'error');
                 });
            }
        })
        .catch(error => {
             console.error('Ошибка fetch при очистке папки:', error);
             showToast('Произошла ошибка сети при очистке папки.', 'error');
        });
    }
}

/**
 * Отображает информацию о выбранных файлах в указанном элементе.
 * @param {HTMLInputElement} input - Элемент input[type=file].
 * @param {HTMLElement} infoElement - Элемент для вывода информации.
 */
function updateFileInfo(input, infoElement) {
    if (!input || !infoElement) return;
    if (input.files && input.files.length > 0) {
        let fileList = '';
        const maxFilesToShow = 5;
        for (let i = 0; i < Math.min(input.files.length, maxFilesToShow); i++) {
            fileList += `<div class='select-load-file'>Выбран файл: <span>${input.files[i].name}</span></div>`;
        }
        if (input.files.length > maxFilesToShow) {
             fileList += `<div class='select-load-file'>... и еще ${input.files.length - maxFilesToShow}</div>`;
        }
        infoElement.innerHTML = `${fileList} <span class="form-hint">Не забудьте сохранить изменения (основной кнопкой)!</span>`; // Уточнили подсказку
    } else {
        infoElement.innerHTML = '';
    }
}

/**
 * Переключает видимость меню выбора категорий.
 */
function toggleCategoryMenu() {
    const menu = document.getElementById('category-menu');
    if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'grid' : 'none';
    }
}

/**
 * Обрабатывает выбор основной категории магазина.
 * Обновляет интерфейс и отправляет AJAX-запрос на сохранение.
 * @param {string|null} categoryId - ID выбранной категории или null/пустая строка для "Без категории".
 */
function selectCategory(categoryId) {
    selectedCategoryId = categoryId || '';
    document.getElementById('category_id').value = selectedCategoryId;
    updateCategoryDisplay();

    // Отправляем AJAX-запрос на сохранение ТОЛЬКО категории
    saveShopCategory(); // ИСПОЛЬЗУЕМ ЭТУ ФУНКЦИЮ

    toggleCategoryMenu();

    if (selectedCategoryId) {
        loadSubcategories(selectedCategoryId);
    } else {
        document.getElementById('subcategory-list').style.display = 'none';
        selectedSubcategoryIds = [];
        updateSubcategoryDisplay();
        // Отправляем AJAX-запрос на сохранение пустого списка подкатегорий
        saveShopSubcategories(); // ИСПОЛЬЗУЕМ ЭТУ ФУНКЦИЮ
    }

    const selectBtn = document.querySelector('.category-select-btn');
    if (selectBtn) {
        selectBtn.textContent = selectedCategoryId ? 'Изменить категорию' : 'Выбрать категорию';
    }
}

/**
 * Отправляет AJAX-запрос для немедленного сохранения выбранной основной категории магазина.
 */
function saveShopCategory() {
    const shopForm = document.getElementById('shopForm');
    const shopId = shopForm ? shopForm.dataset.shopId : null;
    if (!shopId) {
        console.error("Не найден ID магазина для сохранения категории");
        alert("Ошибка: Не удалось определить ID магазина.");
        return;
    }
    const url = `/admin/shop/${shopId}/set_category`; // Новый URL
    console.log(`Отправка категории [${selectedCategoryId || 'None'}] на ${url}`);

    fetch(url, {
        method: 'POST',
        body: JSON.stringify({ category_id: selectedCategoryId }), // Отправляем JSON
        headers: {
            'Content-Type': 'application/json', // Указываем тип контента JSON
            'X-CSRFToken': getCsrfToken()
         }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                 throw new Error(errData.error || `HTTP ошибка! Статус: ${response.status}`);
            }).catch(() => {
                 throw new Error(`HTTP ошибка! Статус: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('Категория успешно сохранена:', data.message);
            showToast('Категория сохранена');
        } else {
            console.error('Ошибка сохранения категории (ответ сервера):', data.error);
            alert(`Ошибка сохранения категории: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Ошибка fetch при сохранении категории:', error);
        alert(`Ошибка сети или сервера при сохранении категории: ${error.message}`);
    });
}

/**
 * Загружает и отображает список подкатегорий для выбранной основной категории.
 * @param {string} categoryId - ID основной категории.
 */
function loadSubcategories(categoryId) {
    const subcategoryListDiv = document.getElementById('subcategory-options');
    const subcategoryContainer = document.getElementById('subcategory-list');

    if (!categoryId || !subcategoryListDiv || !subcategoryContainer) return;

    if (!categoriesData || categoriesData.length === 0) {
        console.error("Данные категорий не загружены для loadSubcategories");
        subcategoryListDiv.innerHTML = '<p>Ошибка: Данные категорий недоступны.</p>';
        subcategoryContainer.style.display = 'grid';
        return;
    }

    const category = categoriesData.find(c => String(c.id) === String(categoryId));

    if (category && category.subcategories && category.subcategories.length > 0) {
        subcategoryListDiv.innerHTML = '';
        category.subcategories.forEach(sub => {
            const subIdStr = String(sub.id);
            const isSelected = selectedSubcategoryIds.includes(subIdStr);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'subcategory-option ' + (isSelected ? 'selected' : '');
            button.dataset.subcategoryId = sub.id;
            button.innerHTML = `
                <span class="subcategory-name">${sub.name}</span>
                <span class="subcategory-toggle-icon">${isSelected ? '✓' : '+'}</span>
            `;
            button.onclick = () => toggleSubcategory(sub.id);
            subcategoryListDiv.appendChild(button);
        });
        subcategoryContainer.style.display = 'grid';
    } else {
        subcategoryListDiv.innerHTML = '<p>Нет доступных подкатегорий.</p>';
        subcategoryContainer.style.display = 'grid';
    }
}

/**
 * Переключает выбор подкатегории (добавляет/удаляет из массива selectedSubcategoryIds).
 * Обновляет интерфейс и отправляет AJAX-запрос на сохранение.
 * @param {string|number} subId - ID подкатегории.
 */
function toggleSubcategory(subId) {
    const subIdStr = String(subId);
    const index = selectedSubcategoryIds.indexOf(subIdStr);
    if (index === -1) {
        selectedSubcategoryIds.push(subIdStr);
    } else {
        selectedSubcategoryIds.splice(index, 1);
    }
    updateSubcategoryDisplay();
    // Отправляем AJAX на сохранение НОВОГО списка подкатегорий
    saveShopSubcategories(); // ИСПОЛЬЗУЕМ ЭТУ ФУНКЦИЮ
    // Обновляем вид кнопок в списке выбора
    if (selectedCategoryId) {
        loadSubcategories(selectedCategoryId);
    }
}

/**
 * Удаляет подкатегорию из списка выбранных (вызывается из блока "Текущие подкатегории").
 * @param {string|number} subId - ID подкатегории.
 */
function removeSubcategory(subId) {
    const subIdStr = String(subId);
    const index = selectedSubcategoryIds.indexOf(subIdStr);
    if (index !== -1) {
        selectedSubcategoryIds.splice(index, 1);
        updateSubcategoryDisplay();
        // Отправляем AJAX на сохранение нового списка
        saveShopSubcategories(); // ИСПОЛЬЗУЕМ ЭТУ ФУНКЦИЮ
        // Обновляем вид кнопок в списке выбора
        if (selectedCategoryId) {
            loadSubcategories(selectedCategoryId);
        }
    }
}

/**
 * Отправляет AJAX-запрос для немедленного сохранения текущего списка
 * выбранных подкатегорий магазина.
 */
function saveShopSubcategories() {
    const shopForm = document.getElementById('shopForm');
    const shopId = shopForm ? shopForm.dataset.shopId : null;
    if (!shopId) {
        console.error("Не найден ID магазина для сохранения подкатегорий");
        alert("Ошибка: Не удалось определить ID магазина.");
        return;
    }
    const url = `/admin/shop/${shopId}/set_subcategories`; // Новый URL
    const subIdsString = selectedSubcategoryIds.join(',');
    console.log(`Отправка подкатегорий [${subIdsString || 'пусто'}] на ${url}`);

    fetch(url, {
        method: 'POST',
        body: JSON.stringify({ subcategory_ids: subIdsString }), // Отправляем JSON
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
         }
    })
    .then(response => {
        if (!response.ok) {
             return response.json().then(errData => {
                 throw new Error(errData.error || `HTTP ошибка! Статус: ${response.status}`);
             }).catch(() => {
                  throw new Error(`HTTP ошибка! Статус: ${response.status}`);
             });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log('Подкатегории успешно сохранены:', data.message);
            showToast('Подкатегории сохранены');
        } else {
            console.error('Ошибка сохранения подкатегорий (ответ сервера):', data.error);
            alert(`Ошибка сохранения подкатегорий: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Ошибка fetch при сохранении подкатегорий:', error);
        alert(`Ошибка сети или сервера при сохранении подкатегорий: ${error.message}`);
    });
}

/**
 * Обновляет отображение выбранной основной категории в блоке "Текущая категория".
 */
function updateCategoryDisplay() {
    const selectedCategoryDiv = document.getElementById('selected-category');
    const noCategoryDiv = document.getElementById('no-category');
    const categoryIdInput = document.getElementById('category_id');

    if (!selectedCategoryDiv || !noCategoryDiv || !categoryIdInput) return;

    categoryIdInput.value = selectedCategoryId;

    if (selectedCategoryId && categoriesData && categoriesData.length > 0) {
        const category = categoriesData.find(c => String(c.id) === String(selectedCategoryId));
        if (category) {
            const imgElement = selectedCategoryDiv.querySelector('img');
            const spanElement = selectedCategoryDiv.querySelector('span');
            const iconUrl = category.icon_url || '{{ url_for("static", filename="images/vector/default-icon.svg") }}';
            const categoryName = category.name || 'Категория';

            if (imgElement) {
                 imgElement.src = iconUrl;
                 imgElement.alt = categoryName;
            }
            if (spanElement) {
                 spanElement.textContent = categoryName;
            }
            selectedCategoryDiv.style.display = 'flex';
            noCategoryDiv.style.display = 'none';
        } else {
             selectedCategoryDiv.style.display = 'none';
             noCategoryDiv.style.display = 'grid';
             console.warn(`Категория с ID ${selectedCategoryId} не найдена в categoriesData`);
        }
    } else {
        selectedCategoryDiv.style.display = 'none';
        noCategoryDiv.style.display = 'grid';
    }
}

/**
 * Обновляет список выбранных подкатегорий в блоке "Текущие подкатегории"
 * и значение скрытого поля subcategory_ids.
 */
function updateSubcategoryDisplay() {
    const subListUl = document.getElementById('selected-subcategories');
    const subcategoryIdsInput = document.getElementById('subcategory_ids');

    if (!subListUl || !subcategoryIdsInput) return;

    subListUl.innerHTML = '';

    if (!categoriesData || categoriesData.length === 0) {
         console.warn("Данные категорий недоступны для updateSubcategoryDisplay");
         subcategoryIdsInput.value = '';
         return;
    }

    const allSubcategories = categoriesData.flatMap(c => c.subcategories || []);

    selectedSubcategoryIds.forEach(subIdStr => {
        const sub = allSubcategories.find(s => String(s.id) === subIdStr);
        if (sub) {
            const li = document.createElement('li');
            li.className = 'selected-subcategory-item';
            li.dataset.subcategoryId = sub.id;
            li.innerHTML = `
                <span class="subcategory-name">[${sub.name}]</span>
                <button type="button" class="remove-subcategory-button" onclick="removeSubcategory('${sub.id}')">Удалить</button>
            `;
            subListUl.appendChild(li);
        } else {
             console.warn(`Подкатегория с ID ${subIdStr} не найдена в allSubcategories`);
        }
    });
    subcategoryIdsInput.value = selectedSubcategoryIds.join(',');
}


/**
 * Инициализация страницы редактирования магазина при загрузке DOM.
 */
document.addEventListener('DOMContentLoaded', () => {
    const shopForm = document.getElementById('shopForm');
    if (!shopForm) {
         console.error("Форма #shopForm не найдена!");
         return;
    }

    // Инициализация начальных значений из data-атрибутов
    selectedCategoryId = shopForm.dataset.categoryId || '';
    selectedSubcategoryIds = (shopForm.dataset.subcategoryIds || '')
                              .split(',')
                              .map(id => id.trim()) // Убираем пробелы
                              .filter(id => id); // Убираем пустые строки

    console.log('Initial Load - Category ID:', selectedCategoryId);
    console.log('Initial Load - Subcategory IDs:', selectedSubcategoryIds);

    // Загружаем категории и подкатегории через AJAX
    fetch('/admin/get_categories')
        .then(response => {
             if (!response.ok) { throw new Error(`HTTP ошибка! Статус: ${response.status}`); }
             return response.json();
        })
        .then(data => {
            if (data && data.categories) {
                 categoriesData = data.categories;
                 console.log('Categories loaded:', categoriesData);
                 // Первичное обновление интерфейса
                 populateCategoryDropdown(); // Заполняем выпадающее меню
                 updateCategoryDisplay();    // Показываем выбранную категорию
                 updateSubcategoryDisplay(); // Показываем выбранные подкатегории
                 // Загружаем опции подкатегорий, ЕСЛИ категория выбрана
                 if (selectedCategoryId) {
                     loadSubcategories(selectedCategoryId);
                 }
            } else {
                 console.error('Некорректный формат ответа от /admin/get_categories');
                 alert('Ошибка: Не удалось загрузить список категорий.');
                 categoriesData = [];
            }
        })
        .catch(error => {
            console.error('Ошибка загрузки категорий:', error);
            alert(`Не удалось загрузить список категорий: ${error.message}`);
            categoriesData = [];
        });

    // Обработчики для полей загрузки файлов (логотип, баннер и т.д.)
    const galleryInput = document.getElementById('gallery_images');
    const galleryInfo = document.querySelector('.gallery-info');
    if (galleryInput && galleryInfo) {
        galleryInput.addEventListener('change', () => updateFileInfo(galleryInput, galleryInfo));
    }
    // ... (аналогично для shop_logo, shop_banner, scheme_logo) ...
    const logoInput = document.getElementById('shop_logo');
    const logoInfo = document.querySelector('.logo-info');
    if (logoInput && logoInfo) {
        logoInput.addEventListener('change', () => updateFileInfo(logoInput, logoInfo));
    }
    const bannerInput = document.getElementById('shop_banner');
    const bannerInfo = document.querySelector('.banner-info');
    if (bannerInput && bannerInfo) {
        bannerInput.addEventListener('change', () => updateFileInfo(bannerInput, bannerInfo));
    }
    const schemeLogoInput = document.getElementById('scheme_logo');
    if (schemeLogoInput) {
         schemeLogoInput.addEventListener('change', () => console.log('Scheme logo file selected:', schemeLogoInput.files));
    }


    // НЕ ПЕРЕХВАТЫВАЕМ основную кнопку "Сохранить изменения"
    // Пусть она отправляет форму стандартным образом
    // const saveButton = document.getElementById('saveButton');
    // if (saveButton) {
    //     saveButton.addEventListener('click', (e) => {
    //         e.preventDefault(); // НЕ ПРЕДОТВРАЩАЕМ ОТПРАВКУ
    //         // Отправка всей формы через AJAX (убрана)
    //     });
    // }
});

/**
 * Заполняет выпадающее меню выбора категорий данными из кэша categoriesData.
 */
function populateCategoryDropdown() {
     const menu = document.getElementById('category-menu');
     if (!menu || !categoriesData) return;

     menu.innerHTML = ''; // Очищаем

     // Кнопка "Без категории"
     const noCategoryButton = document.createElement('button');
     noCategoryButton.type = 'button';
     noCategoryButton.className = 'category-option';
     noCategoryButton.dataset.categoryId = ''; // Пустое значение
     noCategoryButton.textContent = 'Без категории';
     noCategoryButton.onclick = () => selectCategory(null); // Передаем null
     menu.appendChild(noCategoryButton);

     // Кнопки для каждой категории
     categoriesData.forEach(category => {
         const button = document.createElement('button');
         button.type = 'button';
         button.className = 'category-option';
         button.dataset.categoryId = category.id;
         const iconUrl = category.icon_url || '{{ url_for("static", filename="images/vector/default-icon.svg") }}';
         button.innerHTML = `
             <img src="${iconUrl}" alt="${category.name || ''}" class="category-icon">
             <span class="category-name">${category.name || 'Без имени'}</span>
         `;
         button.onclick = () => selectCategory(category.id); // Передаем ID
         menu.appendChild(button);
     });
}

/**
 * Получает CSRF-токен из мета-тега.
 * @returns {string} CSRF-токен или пустая строка.
 */
function getCsrfToken() {
    const tokenElement = document.querySelector('meta[name="csrf-token"]');
    return tokenElement ? tokenElement.content : '';
}

/**
 * Показывает короткое всплывающее уведомление (toast).
 * @param {string} message - Сообщение для отображения.
 * @param {string} type - Тип уведомления ('success', 'error', 'info').
 * @param {number} duration - Длительность отображения в мс.
 */
function showToast(message, type = 'success', duration = 3000) {
    // Проверяем, есть ли уже такой toast, чтобы не спамить
    const existingToast = document.querySelector(`.toast-notification.toast-${type}`);
    if (existingToast && existingToast.textContent === message) {
        return; // Не показываем дубликат
    }

    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    // Форсируем перерисовку для анимации появления
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Удаляем уведомление
    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, duration);
}

