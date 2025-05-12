// static/js/admin_news_editor.js
// ТОЛЬКО ДЛЯ СТРАНИЦЫ СОЗДАНИЯ (news_create.html)

// --- Вспомогательные функции (копируем нужные для СОЗДАНИЯ) ---

// Функция для показа редактора
function showEditor(type, newsTypeInput, contentTypeDisplay, newsContentEditor) {
    if (!newsTypeInput || !contentTypeDisplay || !newsContentEditor) return;
    console.log("Показываем редактор для:", type);
    newsTypeInput.value = type;
    contentTypeDisplay.textContent = type === 'news' ? 'Новость' : 'Акция';
    newsContentEditor.style.display = 'block';
    // Может быть, нужно скрыть кнопки выбора типа
    const typeSelector = document.querySelector('.news-type-selector');
    if (typeSelector) typeSelector.style.display = 'none'; // Скрываем кнопки после выбора
}

// Функция добавления НОВОГО блока контента
function addContentBlock(type, contentBlocksContainer, addBlockButtonsContainer) {
    // ... (Код функции addContentBlock из предыдущего шага) ...
     if (!contentBlocksContainer || !addBlockButtonsContainer) {
        console.error("addContentBlock: Не найдены контейнеры!");
        return;
    }
    const blockId = `block-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    const blockElement = document.createElement('div');
    blockElement.classList.add('content-block-item', `content-block-${type}`);
    blockElement.dataset.blockId = blockId;
    blockElement.dataset.blockType = type;

    // Обертка для контента и кнопок управления
    let blockHTML = `<div class="block-inner-content"><span class="block-type-label">[${type}]</span>`;

    switch (type) {
        case 'heading':
            blockHTML += `<input type="text" name="${blockId}_content" placeholder="Введите заголовок..." class="form-control block-input block-heading-input">`;
            break;
        case 'text':
            blockHTML += `<textarea name="${blockId}_content" placeholder="Введите текст..." class="form-control block-input block-text-input" rows="4"></textarea>`;
            break;
        case 'image':
            blockHTML += `
                <input type="file" class="form-control-file block-image-input" accept="image/png, image/jpeg, image/gif">
                <input type="hidden" name="${blockId}_content" class="block-image-url">
                <div class="image-preview-container" style="margin-top: 5px;"></div>
                <small class="image-upload-status"></small>
            `;
            break;
        case 'list':
            blockHTML += `
                <ul class="block-list-ul" style="list-style: disc; margin-left: 20px;">
                    <li><input type="text" name="${blockId}_item_1" placeholder="Пункт списка 1" class="form-control block-input block-list-item-input"></li>
                </ul>
                <button type="button" class="button button-sm button-add-list-item" style="margin-left: 20px;">+ Добавить пункт</button>
            `;
            break;
        case 'link':
            blockHTML += `
                <input type="text" name="${blockId}_text" placeholder="Текст ссылки" class="form-control block-input block-link-text-input" style="margin-bottom: 5px;">
                <input type="url" name="${blockId}_url" placeholder="URL (https://...)" class="form-control block-input block-link-url-input">
            `;
            break;
        default:
            blockHTML += `<span>Неизвестный тип блока: ${type}</span>`;
    }
    blockHTML += `</div>`; // Закрываем .block-inner-content

    // Добавляем кнопки управления ПОСЛЕ контента
    blockHTML += `
        <div class="block-controls" style="margin-top: 5px;">
            <button type="button" class="button button-sm button-danger button-delete-block">Удалить</button>
            <button type="button" class="button button-sm button-move-up-block">↑ Вверх</button>
            <button type="button" class="button button-sm button-move-down-block">↓ Вниз</button>
        </div>
    `;
    blockElement.innerHTML = blockHTML;

    contentBlocksContainer.appendChild(blockElement);

    // Перемещаем кнопки "Добавить" в самый конец
    if (contentBlocksContainer.contains(addBlockButtonsContainer)) {
        contentBlocksContainer.appendChild(addBlockButtonsContainer);
    } else {
        console.warn("Контейнер кнопок 'Добавить' не найден в основном контейнере при добавлении нового блока.");
    }

    addBlockEventListeners(blockElement, contentBlocksContainer, addBlockButtonsContainer);
}

// Функция добавления обработчиков для кнопок внутри блока
function addBlockEventListeners(blockElement, contentBlocksContainer, addBlockButtonsContainer) {
   // ... (Код функции addBlockEventListeners из предыдущего шага) ...
    if (!blockElement || !contentBlocksContainer || !addBlockButtonsContainer) return;

    // Удаление блока
    const deleteBtn = blockElement.querySelector('.button-delete-block');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', () => {
            blockElement.remove();
            // Перемещаем кнопки "Добавить" вниз, если они остались без родителя
            if (!addBlockButtonsContainer.parentNode) {
                contentBlocksContainer.appendChild(addBlockButtonsContainer);
            }
        });
    }

    // Добавление пункта списка
    const addListItemBtn = blockElement.querySelector('.button-add-list-item');
    if (addListItemBtn) {
        addListItemBtn.addEventListener('click', () => {
            const listUl = blockElement.querySelector('.block-list-ul');
            if (!listUl) return;
            const itemCount = listUl.children.length + 1;
            const newItem = document.createElement('li');
            newItem.innerHTML = `<input type="text" name="${blockElement.dataset.blockId}_item_${itemCount}" placeholder="Пункт списка ${itemCount}" class="form-control block-input block-list-item-input">`;
            listUl.appendChild(newItem);
        });
    }

    // Загрузка изображения
    const imageInput = blockElement.querySelector('.block-image-input');
    if (imageInput) {
        imageInput.addEventListener('change', handleImageUpload); // handleImageUpload должна быть определена
    }

    // Перемещение вверх
    const moveUpBtn = blockElement.querySelector('.button-move-up-block');
    if (moveUpBtn) {
        moveUpBtn.addEventListener('click', () => moveBlock(blockElement, 'up')); // moveBlock должна быть определена
    }

    // Перемещение вниз
    const moveDownBtn = blockElement.querySelector('.button-move-down-block');
    if (moveDownBtn) {
        moveDownBtn.addEventListener('click', () => moveBlock(blockElement, 'down')); // moveBlock должна быть определена
    }
}

// Функция перемещения блока
function moveBlock(blockElement, direction) {
    // ... (Код функции moveBlock из предыдущего шага) ...
    if (!blockElement) return;
    const parent = blockElement.parentNode;
    if (!parent) return;
    const index = Array.from(parent.children).indexOf(blockElement);
    const addButtonsContainer = document.getElementById('add-block-buttons'); // Получаем кнопки

    if (direction === 'up' && blockElement.previousElementSibling && blockElement.previousElementSibling.id !== 'add-block-buttons') {
        parent.insertBefore(blockElement, blockElement.previousElementSibling);
    } else if (direction === 'down') {
        let nextRealSibling = blockElement.nextElementSibling;
        // Пропускаем контейнер кнопок "Добавить", если он следующий
        if (nextRealSibling && nextRealSibling.id === 'add-block-buttons') {
            nextRealSibling = nextRealSibling.nextElementSibling;
        }
        if (nextRealSibling) {
            parent.insertBefore(blockElement, nextRealSibling.nextElementSibling); // Вставляем после следующего реального блока
        }
    }

    // Всегда перемещаем кнопки добавления в самый конец после любого перемещения
    if (addButtonsContainer && parent.contains(addButtonsContainer)) {
        parent.appendChild(addButtonsContainer);
    }
}

// Функция получения CSRF токена (оставляем на всякий случай, если понадобится)
function getCsrfToken() {
     const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta) {
        return tokenMeta.content;
    }
    const tokenInput = document.querySelector('input[name="csrf_token"]');
     if (tokenInput) {
        return tokenInput.value;
    }
    // Пробуем взять из глобальной переменной, если она передана из шаблона
    if (typeof csrfToken !== 'undefined') {
        return csrfToken;
    }
    console.error("CSRF токен не найден!");
    return null;
}

// Функция загрузки изображения (нужна и при создании)
async function handleImageUpload(event) {
    // ... (Код функции handleImageUpload из предыдущего шага) ...
     const fileInput = event.target;
    const blockElement = fileInput.closest('.content-block-item');
    if (!blockElement) return;
    const urlInput = blockElement.querySelector('.block-image-url');
    const previewContainer = blockElement.querySelector('.image-preview-container');
    const statusElement = blockElement.querySelector('.image-upload-status');

    if (!urlInput || !previewContainer || !statusElement) return;
    if (!fileInput.files || fileInput.files.length === 0) { return; }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('image', file);

    statusElement.textContent = 'Загрузка...';
    previewContainer.innerHTML = '';

    // Используем глобальную переменную newsImageUploadUrl (должна быть определена в шаблоне)
    const uploadUrl = typeof newsImageUploadUrl !== 'undefined' ? newsImageUploadUrl : '/admin/news/upload_image';
    const token = getCsrfToken(); // Получаем токен через функцию

    if (!token) {
        statusElement.textContent = 'Ошибка: CSRF токен не найден.';
        return;
    }

    try {
        const response = await fetch(uploadUrl, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': token } // Используем токен
        });

        const result = await response.json();

        if (response.ok && result.success && result.temp_filename) {
            console.log("Картинка временно загружена:", result.temp_filename);
            urlInput.value = result.temp_filename;
            const previewUrl = `/static/uploads/news_content/${result.temp_filename}`;
            previewContainer.innerHTML = `<img src="${previewUrl}" alt="Превью" style="max-width: 200px; max-height: 100px;"><button type="button" class="button button-sm button-danger change-image-btn" style="margin-left: 10px;">Заменить</button>`;
            statusElement.textContent = 'Загружено (временно).';
            fileInput.style.display = 'none';

            // Добавляем обработчик для НОВОЙ кнопки "Заменить"
            const changeImageBtn = previewContainer.querySelector('.change-image-btn');
            if (changeImageBtn) {
                changeImageBtn.addEventListener('click', (e) => {
                    const currentBlock = e.target.closest('.content-block-item');
                    if (!currentBlock) return;
                    const fInput = currentBlock.querySelector('.block-image-input');
                    const uInput = currentBlock.querySelector('.block-image-url');
                    const pContainer = currentBlock.querySelector('.image-preview-container');
                    if (fInput) fInput.style.display = '';
                    if (fInput) fInput.value = '';
                    if (uInput) uInput.value = '';
                    if (pContainer) pContainer.innerHTML = '';
                });
            }
        } else {
            console.error("Ошибка загрузки:", result.error);
            statusElement.textContent = `Ошибка: ${result.error || response.statusText}`;
            urlInput.value = '';
        }
    } catch (error) {
        console.error('Сетевая ошибка или ошибка JS при загрузке:', error);
        statusElement.textContent = 'Ошибка сети при загрузке.';
        urlInput.value = '';
    }
}


// --- Инициализация при загрузке страницы СОЗДАНИЯ ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("ЗАГРУЖЕН: admin_news_editor.js (ТОЛЬКО ДЛЯ СОЗДАНИЯ)");

    // Получаем элементы DOM, необходимые для страницы СОЗДАНИЯ
    const createNewsBtn = document.getElementById('create-news-btn');
    const createPromoBtn = document.getElementById('create-promo-btn');
    const newsContentEditor = document.getElementById('news-content-editor');
    const contentTypeDisplay = document.getElementById('content-type-display');
    const newsTypeInput = document.getElementById('news-type');
    const cancelCreationBtn = document.getElementById('cancel-creation-btn');
    const addBlockButtonsContainer = document.getElementById('add-block-buttons');
    const contentBlocksContainer = document.getElementById('content-blocks-container');
    const newsForm = document.getElementById('news-create-form'); // Ищем форму СОЗДАНИЯ
    const contentBlocksDataInput = document.getElementById('content-blocks-data-input');

    // Проверяем наличие ключевых элементов для СОЗДАНИЯ
    // Опционально проверяем кнопки выбора типа, так как они могут отсутствовать, если shop_id передан
    if (!newsContentEditor || !contentTypeDisplay || !newsTypeInput || !addBlockButtonsContainer || !contentBlocksContainer || !newsForm || !contentBlocksDataInput) {
        console.error("Один или несколько ключевых элементов редактора ДЛЯ СОЗДАНИЯ не найдены!");
        return;
    }

    // --- Логика для страницы СОЗДАНИЯ ---
    if (createNewsBtn && createPromoBtn) {
        createNewsBtn.addEventListener('click', () => {
            showEditor('news', newsTypeInput, contentTypeDisplay, newsContentEditor);
        });
        createPromoBtn.addEventListener('click', () => {
            showEditor('promo', newsTypeInput, contentTypeDisplay, newsContentEditor);
        });
    } else if (newsTypeInput && newsTypeInput.value) {
         // Если тип уже установлен (например, при переходе с привязкой к магазину),
         // и кнопок выбора нет, показываем редактор сразу
         console.log("Тип установлен, показываем редактор сразу:", newsTypeInput.value)
         showEditor(newsTypeInput.value, newsTypeInput, contentTypeDisplay, newsContentEditor);
    } else {
        console.log("Кнопки 'Создать новость/акцию' не найдены и тип не установлен.");
    }

    // Кнопка "Отменить"
    if (cancelCreationBtn) {
        cancelCreationBtn.addEventListener('click', () => {
            console.log("Отмена создания");
            if (newsContentEditor) newsContentEditor.style.display = 'none';
            if (newsTypeInput) newsTypeInput.value = '';
            if (contentBlocksContainer) contentBlocksContainer.innerHTML = '';
            // Перемещаем кнопки добавления обратно
            if (addBlockButtonsContainer && !contentBlocksContainer.contains(addBlockButtonsContainer)) {
                 contentBlocksContainer.appendChild(addBlockButtonsContainer);
            }

            // Сброс полей основной формы
            const titleInput = document.getElementById('news-title');
            const descInput = document.getElementById('news-short-description');
            const iconSelect = document.getElementById('news-icon');
            const iconPreview = document.getElementById('icon-preview');
            const bannerInput = document.getElementById('news-banner'); // Поле баннера
            const bannerPreview = document.getElementById('banner-preview'); // Превью баннера

            if (titleInput) titleInput.value = '';
            if (descInput) descInput.value = '';
            if (iconSelect) iconSelect.value = ''; // Сброс выбора иконки
            if (iconPreview) iconPreview.innerHTML = ''; // Очистка превью иконки
            if (bannerInput) bannerInput.value = ''; // Очистка поля файла баннера
            if (bannerPreview) bannerPreview.innerHTML = ''; // Очистка превью баннера

            // Показываем кнопки выбора типа снова, если они есть
            const typeSelector = document.querySelector('.news-type-selector');
            if (typeSelector) typeSelector.style.display = 'block';

             // Сбрасываем текст и состояние кнопки Submit
            const saveButton = newsForm.querySelector('button[type="submit"]');
            if(saveButton) {
                saveButton.textContent = 'Сохранить'; // Восстанавливаем исходный текст
                saveButton.disabled = false;
            }
        });
    }

    // --- Обработчики для кнопок "Добавить блок" ---
     const addButtons = addBlockButtonsContainer.querySelectorAll('.add-block-btn');
     addButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const blockType = event.target.dataset.blockType;
            console.log("Добавляем блок типа:", blockType);
            addContentBlock(blockType, contentBlocksContainer, addBlockButtonsContainer);
        });
    });

    // --- Обработчик отправки формы СОЗДАНИЯ (с обратной связью) ---
    const saveButton = newsForm.querySelector('button[type="submit"]');
    let originalButtonText = 'Сохранить';
    if (saveButton) {
        originalButtonText = saveButton.textContent;
    } else {
        console.error("Кнопка submit не найдена в форме создания!");
    }

    newsForm.addEventListener('submit', function(event) {
        console.log("Форма создания отправляется...");

        // Сброс кнопки
        if (saveButton) {
            saveButton.textContent = originalButtonText;
            saveButton.disabled = false;
        }

        try {
            // 0. Проверка типа (Новость/Акция) - ВАЖНО для создания
            if (!newsTypeInput.value) {
                console.warn("Тип новости/акции не выбран.");
                event.preventDefault();
                 if (saveButton) {
                    saveButton.textContent = 'Не отправлено';
                    saveButton.disabled = true;
                    setTimeout(() => {
                        saveButton.textContent = originalButtonText;
                        saveButton.disabled = false;
                    }, 3000);
                }
                alert('Пожалуйста, выберите тип записи: Новость или Акция.');
                // Можно подсветить кнопки выбора, если они еще видны
                return;
            }

            // 1. Сбор данных блоков
            const blocksData = [];
            const blockElements = contentBlocksContainer.querySelectorAll('.content-block-item');
            let blockCollectionError = false;

            blockElements.forEach(block => {
                 const blockType = block.dataset.blockType;
                const blockId = block.dataset.blockId;
                const blockInfo = { type: blockType };

                try {
                     switch (blockType) {
                         case 'heading':
                            blockInfo.content = block.querySelector('.block-heading-input')?.value ?? '';
                            break;
                        case 'text':
                            blockInfo.content = block.querySelector('.block-text-input')?.value ?? '';
                            break;
                        case 'image':
                            blockInfo.url = block.querySelector('.block-image-url')?.value ?? '';
                            if (!blockInfo.url) return; // Пропускаем итерацию
                            break;
                        case 'list':
                            blockInfo.items = Array.from(block.querySelectorAll('.block-list-item-input'))
                                .map(input => input.value.trim())
                                .filter(value => value !== '');
                            if (blockInfo.items.length === 0) return; // Пропускаем итерацию
                            break;
                        case 'link':
                            blockInfo.text = block.querySelector('.block-link-text-input')?.value ?? '';
                            blockInfo.url = block.querySelector('.block-link-url-input')?.value ?? '';
                            if (!blockInfo.text || !blockInfo.url) return; // Пропускаем итерацию
                            break;
                        default: return; // Пропускаем неизвестные типы
                    }
                    blocksData.push(blockInfo);
                } catch (blockError) {
                    console.error(`Ошибка при обработке блока ${blockId} (${blockType}):`, blockError);
                    blockCollectionError = true;
                }
            });

            if (blockCollectionError) {
                 throw new Error("Обнаружена ошибка при сборе данных блоков контента.");
            }

            console.log("Все блоки для сохранения (создание):", blocksData);
            contentBlocksDataInput.value = JSON.stringify(blocksData);
            console.log("JSON данных блоков (создание):", contentBlocksDataInput.value);

            // 2. Валидация заголовка
            const titleInput = document.getElementById('news-title');
            if (!titleInput || !titleInput.value.trim()) {
                console.warn("Валидация заголовка не пройдена (создание).");
                event.preventDefault();
                 if (saveButton) {
                    saveButton.textContent = 'Не отправлено';
                    saveButton.disabled = true;
                    setTimeout(() => {
                        saveButton.textContent = originalButtonText;
                        saveButton.disabled = false;
                    }, 3000);
                }
                alert('Заголовок новости обязателен для заполнения!');
                if(titleInput) titleInput.focus();
                return;
            }

            // 3. Отправка
            console.log("Все проверки пройдены, разрешаем отправку формы (создание)...");
            if (saveButton) {
                saveButton.textContent = 'Сохранение...';
                saveButton.disabled = true;
            }

        } catch (error) {
            console.error("Критическая ошибка при подготовке формы создания к отправке:", error);
            event.preventDefault();
            if (saveButton) {
                saveButton.textContent = 'Ошибка!';
                saveButton.disabled = true;
                setTimeout(() => {
                    saveButton.textContent = originalButtonText;
                    saveButton.disabled = false;
                }, 4000);
            }
            alert('Произошла ошибка при подготовке данных к отправке. Пожалуйста, проверьте консоль разработчика (F12).');
        }
    }); // Конец обработчика submit

    // --- Загрузка иконок (оставляем для страницы создания) ---
    // Функция для загрузки иконок (взята из шаблона create)
    async function fetchIcons(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            const iconSelect = document.getElementById('news-icon');
            const iconPreview = document.getElementById('icon-preview');

            if (!iconSelect || !iconPreview) {
                 console.warn("Элементы выбора иконки не найдены на странице создания.");
                 return;
            }

            // Очищаем старые опции (кроме первой)
            while (iconSelect.options.length > 1) {
                iconSelect.remove(1);
            }

            // Добавляем иконки
            if (data.icons && data.icons.length > 0) {
                data.icons.forEach(iconName => {
                    const option = document.createElement('option');
                    option.value = iconName;
                    option.textContent = iconName;
                    iconSelect.appendChild(option);
                });
            }

            // Обновление превью при изменении
            iconSelect.addEventListener('change', function() {
                if (this.value) {
                    iconPreview.innerHTML = `<img src="/static/uploads/category_icons/${this.value}" alt="Preview" style="max-width: 50px; max-height: 50px; vertical-align: middle;">`;
                } else {
                    iconPreview.innerHTML = '';
                }
            });

        } catch (error) {
            console.error('Ошибка загрузки иконок:', error);
        }
    }

    // Вызываем загрузку иконок, если URL передан
    if (typeof iconListUrl !== 'undefined') {
        fetchIcons(iconListUrl);
    } else {
         console.warn("Переменная iconListUrl не определена в шаблоне создания!");
    }

     // Добавим обработчик для превью баннера при создании
    const bannerInput = document.getElementById('news-banner');
    const bannerPreview = document.getElementById('banner-preview');
    if (bannerInput && bannerPreview) {
        bannerInput.addEventListener('change', function(e) {
            bannerPreview.innerHTML = ''; // Очищаем старое превью
            if (e.target.files && e.target.files[0]) {
                const reader = new FileReader();
                reader.onload = function(ev) {
                    const img = document.createElement('img');
                    img.src = ev.target.result;
                    img.style.maxWidth = '200px';
                    img.style.maxHeight = '100px';
                    img.style.marginTop = '5px';
                    bannerPreview.appendChild(img);
                }
                reader.readAsDataURL(e.target.files[0]);
            }
        });
    }


}); // Конец DOMContentLoaded