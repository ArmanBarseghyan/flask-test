// static/js/admin_news_detail_editor.js
// ТОЛЬКО ДЛЯ СТРАНИЦЫ РЕДАКТИРОВАНИЯ (news_detail.html)

// --- Вспомогательные функции для редактора (копируем нужные) ---

// Функция добавления блока контента ИЗ СУЩЕСТВУЮЩИХ ДАННЫХ
function addContentBlockFromData(blockData, contentBlocksContainer, addBlockButtonsContainer) {
    // ... (Код функции addContentBlockFromData из твоего оригинального admin_news_editor.js) ...
     if (!contentBlocksContainer || !addBlockButtonsContainer || !blockData || !blockData.type) {
        console.error("Ошибка: неверные данные или контейнеры для addContentBlockFromData", blockData, contentBlocksContainer, addBlockButtonsContainer);
        return;
    }
    const type = blockData.type;
    const blockId = `block-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`; // Генерируем новый ID
    const blockElement = document.createElement('div');
    blockElement.classList.add('content-block-item', `content-block-${type}`);
    blockElement.dataset.blockId = blockId;
    blockElement.dataset.blockType = type;

    let blockHTML = `<div class="block-inner-content"><span class="block-type-label">[${type}]</span>`;

    switch (type) {
        case 'heading':
            blockHTML += `<input type="text" name="${blockId}_content" placeholder="Введите заголовок..." class="form-control block-input block-heading-input" value="${blockData.content || ''}">`;
            break;
        case 'text':
            blockHTML += `<textarea name="${blockId}_content" placeholder="Введите текст..." class="form-control block-input block-text-input" rows="4">${blockData.content || ''}</textarea>`;
            break;
        case 'image':
            // Используем url_display для превью, url_saved для hidden input
            const imageUrl = blockData.url_display || ''; // Полный URL для <img>
            const savedUrl = blockData.url_saved || '';   // Только имя файла для <input type="hidden">
            blockHTML += `
                <input type="file" class="form-control-file block-image-input" accept="image/png, image/jpeg, image/gif" style="${imageUrl ? 'display: none;' : ''}">
                <input type="hidden" name="${blockId}_content" class="block-image-url" value="${savedUrl}"> {/* Сохраняем только имя файла */}
                <div class="image-preview-container" style="margin-top: 5px;">
                    ${imageUrl ? `<img src="${imageUrl}" alt="Превью" style="max-width: 200px; max-height: 100px;"><button type="button" class="button button-sm button-danger change-image-btn" style="margin-left: 10px;">Заменить</button>` : ''}
                </div>
                <small class="image-upload-status"></small>
            `;
            break;
        case 'list':
            blockHTML += `<ul class="block-list-ul" style="list-style: disc; margin-left: 20px;">`;
            if (blockData.items && Array.isArray(blockData.items) && blockData.items.length > 0) {
                blockData.items.forEach((item, index) => {
                    blockHTML += `<li><input type="text" name="${blockId}_item_${index + 1}" placeholder="Пункт списка ${index + 1}" class="form-control block-input block-list-item-input" value="${item || ''}"></li>`;
                });
            } else {
                blockHTML += `<li><input type="text" name="${blockId}_item_1" placeholder="Пункт списка 1" class="form-control block-input block-list-item-input" value=""></li>`;
            }
            blockHTML += `</ul><button type="button" class="button button-sm button-add-list-item" style="margin-left: 20px;">+ Добавить пункт</button>`;
            break;
        case 'link':
            blockHTML += `
                <input type="text" name="${blockId}_text" placeholder="Текст ссылки" class="form-control block-input block-link-text-input" style="margin-bottom: 5px;" value="${blockData.text || ''}">
                <input type="url" name="${blockId}_url" placeholder="URL (https://...)" class="form-control block-input block-link-url-input" value="${blockData.url || ''}">
            `;
            break;
        default:
            console.warn("Неизвестный тип блока при инициализации:", type);
            blockHTML += `<span>Неизвестный тип блока: ${type}</span>`;
    }

    blockHTML += `</div>`; // Закрываем .block-inner-content

    blockHTML += `
        <div class="block-controls" style="margin-top: 5px;">
            <button type="button" class="button button-sm button-danger button-delete-block">Удалить</button>
            <button type="button" class="button button-sm button-move-up-block">↑ Вверх</button>
            <button type="button" class="button button-sm button-move-down-block">↓ Вниз</button>
        </div>
    `;
    blockElement.innerHTML = blockHTML;

    contentBlocksContainer.appendChild(blockElement);

    addBlockEventListeners(blockElement, contentBlocksContainer, addBlockButtonsContainer);

    // Добавляем обработчик для кнопки "Заменить" у картинки
    const changeImageBtn = blockElement.querySelector('.change-image-btn');
    if (changeImageBtn) {
        changeImageBtn.addEventListener('click', (e) => {
            const currentBlock = e.target.closest('.content-block-item');
            if (!currentBlock) return;
            const fileInput = currentBlock.querySelector('.block-image-input');
            const urlInput = currentBlock.querySelector('.block-image-url');
            const previewContainer = currentBlock.querySelector('.image-preview-container');
            if (fileInput) fileInput.style.display = '';
            if (fileInput) fileInput.value = '';
            if (urlInput) urlInput.value = '';
            if (previewContainer) previewContainer.innerHTML = '';
        });
    }
}

// Функция добавления НОВОГО блока (нужна и при редактировании)
function addContentBlock(type, contentBlocksContainer, addBlockButtonsContainer) {
    // ... (Код функции addContentBlock из твоего оригинального admin_news_editor.js) ...
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
    // ... (Код функции addBlockEventListeners из твоего оригинального admin_news_editor.js) ...
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
    // ... (Код функции moveBlock из твоего оригинального admin_news_editor.js) ...
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

// Функция получения CSRF токена (пример)
function getCsrfToken() {
    // Пробуем найти в мета-теге
    const tokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (tokenMeta) {
        return tokenMeta.content;
    }
    // Пробуем найти в скрытом поле (если оно есть с таким id/name)
    const tokenInput = document.querySelector('input[name="csrf_token"]');
     if (tokenInput) {
        return tokenInput.value;
    }
    console.error("CSRF токен не найден!");
    return null;
}


// Функция загрузки изображения
async function handleImageUpload(event) {
    // ... (Код функции handleImageUpload из твоего оригинального admin_news_editor.js, но используем getCsrfToken) ...
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

// Функция для загрузки и установки иконок
async function fetchAndSetIcons(url, selectedIconFilename) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        const iconSelect = document.getElementById('news-icon');
        const iconPreview = document.getElementById('icon-preview');

        if (!iconSelect || !iconPreview) {
            console.error("Элементы для иконок не найдены!");
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
                if (iconName === selectedIconFilename) { // Выбираем нужную иконку
                    option.selected = true;
                }
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

        // Устанавливаем превью для изначально выбранной иконки
        if (selectedIconFilename) {
            iconPreview.innerHTML = `<img src="/static/uploads/category_icons/${selectedIconFilename}" alt="Preview" style="max-width: 50px; max-height: 50px; vertical-align: middle;">`;
        } else {
            iconPreview.innerHTML = '';
        }

    } catch (error) {
        console.error('Ошибка загрузки иконок:', error);
    }
}


// --- Инициализация при загрузке страницы ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("ЗАГРУЖЕН: admin_news_detail_editor.js");

    // Проверяем, что мы точно в режиме редактирования и есть данные
    if (typeof editMode === 'undefined' || editMode !== true || typeof existingNewsData === 'undefined') {
        console.error("Критическая ошибка: Скрипт редактирования загружен не на странице редактирования или отсутствуют данные (editMode, existingNewsData).");
        return; // Прекращаем выполнение, если что-то не так
    }

    // Получаем элементы DOM, необходимые для страницы редактирования
    const newsContentEditor = document.getElementById('news-content-editor');
    const contentTypeDisplay = document.getElementById('content-type-display'); // Находим для отображения типа
    const addBlockButtonsContainer = document.getElementById('add-block-buttons');
    const contentBlocksContainer = document.getElementById('content-blocks-container');
    const newsForm = document.getElementById('news-edit-form'); // Ищем форму РЕДАКТИРОВАНИЯ
    const contentBlocksDataInput = document.getElementById('content-blocks-data-input');

    // Проверяем наличие всех ключевых элементов
    if ( !newsContentEditor || !addBlockButtonsContainer || !contentBlocksContainer || !newsForm || !contentBlocksDataInput || !contentTypeDisplay) {
        console.error("Один или несколько ключевых элементов редактора ДЛЯ РЕДАКТИРОВАНИЯ не найдены!");
        return;
    }

     // Устанавливаем отображаемый тип контента
    const newsType = document.getElementById('news-type')?.value; // Получаем тип из hidden input
    if (contentTypeDisplay && newsType) {
         contentTypeDisplay.textContent = newsType === 'news' ? 'Новость' : 'Акция';
    }

    // --- Инициализация иконок ---
    // Используем глобальную переменную iconListUrl из шаблона
    if (typeof iconListUrl !== 'undefined') {
        fetchAndSetIcons(iconListUrl, existingNewsData.icon);
    } else {
        console.warn("Переменная iconListUrl не определена в шаблоне!");
    }

    // --- Инициализация блоков контента ---
    if (Array.isArray(existingNewsData.contentBlocks)) {
        console.log("Загрузка существующих блоков:", existingNewsData.contentBlocks.length);
        existingNewsData.contentBlocks.forEach(blockData => {
            addContentBlockFromData(blockData, contentBlocksContainer, addBlockButtonsContainer);
        });
        // Перемещаем кнопки "Добавить" в конец после добавления всех блоков
        contentBlocksContainer.appendChild(addBlockButtonsContainer);
    } else {
        console.error("existingNewsData.contentBlocks не является массивом!");
        contentBlocksContainer.appendChild(addBlockButtonsContainer); // Все равно добавляем кнопки
    }

     // --- Обработчики для кнопок "Добавить блок" ---
    const addButtons = addBlockButtonsContainer.querySelectorAll('.add-block-btn');
    addButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const blockType = event.target.dataset.blockType;
            console.log("Добавляем блок типа:", blockType);
            // Используем функцию добавления НОВОГО блока
            addContentBlock(blockType, contentBlocksContainer, addBlockButtonsContainer);
        });
    });


    // --- Обработчик отправки формы (с улучшенной обратной связью) ---
    const saveButton = newsForm.querySelector('button[type="submit"]');
    let originalButtonText = 'Сохранить изменения'; // Текст по умолчанию для редактора
    if (saveButton) {
        originalButtonText = saveButton.textContent;
    } else {
        console.error("Кнопка submit не найдена в форме редактирования!");
    }

    newsForm.addEventListener('submit', function(event) {
        console.log("Форма редактирования отправляется...");

        // Сброс кнопки
        if (saveButton) {
            saveButton.textContent = originalButtonText;
            saveButton.disabled = false;
        }

        try {
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

            console.log("Все блоки для сохранения (редактирование):", blocksData);
            contentBlocksDataInput.value = JSON.stringify(blocksData);
            console.log("JSON данных блоков (редактирование):", contentBlocksDataInput.value);

            // 2. Валидация заголовка
            const titleInput = document.getElementById('news-title');
            if (!titleInput || !titleInput.value.trim()) {
                console.warn("Валидация заголовка не пройдена (редактирование).");
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
            console.log("Все проверки пройдены, разрешаем отправку формы (редактирование)...");
            if (saveButton) {
                saveButton.textContent = 'Сохранение...';
                saveButton.disabled = true;
            }

        } catch (error) {
            console.error("Критическая ошибка при подготовке формы редактирования к отправке:", error);
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

}); // Конец DOMContentLoaded