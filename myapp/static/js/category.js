// static/js/category.js

let selectedIcon = '';
let selectedCategoryId = '';
let categoryToDelete = null;

function toggleCreateCategory() {
    const menu = document.getElementById('create-category-menu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

function toggleCreateSubcategory() {
    const menu = document.getElementById('create-subcategory-menu');
    menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
}

function selectIcon(iconPath) {
    selectedIcon = iconPath;
    document.getElementById('selected-icon').value = iconPath;
    const previewModal = document.getElementById('icon-preview');
    const previewIcon = document.getElementById('preview-icon');
    previewIcon.src = `/static/uploads/category_icons/${iconPath}`;
    previewModal.style.display = 'flex';
}

function closeIconPreview() {
    const previewModal = document.getElementById('icon-preview');
    previewModal.style.display = 'none';
}

function saveCategory() {
    const name = document.getElementById('category-name').value.trim();
    const icon = selectedIcon || document.getElementById('selected-icon').value;
    if (!name || !icon) {
        showErrorModal('Пожалуйста, введите название категории и выберите иконку.');
        return;
    }
    fetch('/admin/save_category', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ name: name, icon: icon })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const successModal = document.getElementById('success-modal');
            const successName = document.getElementById('success-category-name');
            const successIcon = document.getElementById('success-category-icon');
            successName.textContent = name;
            successIcon.src = `/static/uploads/category_icons/${icon}`;
            successModal.style.display = 'flex';
            document.getElementById('category-name').value = '';
            document.getElementById('selected-icon').value = '';
            selectedIcon = '';
        } else {
            showErrorModal('Ошибка при сохранении категории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        showErrorModal('Ошибка сохранения категории: ' + error.message);
    });
}

function closeSuccessModal() {
    const successModal = document.getElementById('success-modal');
    successModal.style.display = 'none';
    location.reload();
}

function selectCategoryForSubcategory(categoryId) {
    selectedCategoryId = categoryId;
    document.getElementById('selected-category-id').value = categoryId;
    const dropdown = document.getElementById('category-dropdown');
    const selectedItem = event.target.closest('.categ-item');
    dropdown.querySelectorAll('.categ-item').forEach(item => item.classList.remove('selected'));
    selectedItem.classList.add('selected');

    const selectModal = document.getElementById('subcategory-select-modal');
    const selectName = document.getElementById('selected-category-name');
    const selectIcon = document.getElementById('selected-category-icon');
    const categoryName = selectedItem.querySelector('span').textContent;
    const categoryIconSrc = selectedItem.querySelector('img').src;
    selectName.textContent = categoryName;
    selectIcon.src = categoryIconSrc;
    selectModal.style.display = 'flex';
}

function closeSubcategorySelectModal() {
    const selectModal = document.getElementById('subcategory-select-modal');
    selectModal.style.display = 'none';
}

function saveSubcategory() {
    const name = document.getElementById('subcategory-name').value.trim();
    const categoryId = selectedCategoryId || document.getElementById('selected-category-id').value;
    if (!name || !categoryId) {
        showErrorModal('Пожалуйста, выберите категорию и введите название подкатегории.');
        return;
    }
    fetch('/admin/save_subcategory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ name: name, category_id: categoryId })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const successModal = document.getElementById('subcategory-success-modal');
            const successName = document.getElementById('success-subcategory-name');
            successName.textContent = name;
            successModal.style.display = 'flex';
            document.getElementById('subcategory-name').value = '';
            document.getElementById('selected-category-id').value = '';
            selectedCategoryId = '';
        } else {
            showErrorModal('Ошибка при сохранении подкатегории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        showErrorModal('Ошибка сохранения подкатегории: ' + error.message);
    });
}

function saveNewSubcategory(categoryId) {
    const name = document.getElementById('new-subcategory-name').value.trim();
    if (!name) {
        showErrorModal('Пожалуйста, введите название подкатегории.');
        return;
    }
    fetch('/admin/save_subcategory', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ name: name, category_id: categoryId })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const successModal = document.getElementById('subcategory-success-modal');
            const successName = document.getElementById('success-subcategory-name');
            successName.textContent = name;
            successModal.style.display = 'flex';
            document.getElementById('new-subcategory-name').value = '';
        } else {
            showErrorModal('Ошибка при сохранении подкатегории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        showErrorModal('Ошибка сохранения подкатегории: ' + error.message);
    });
}

function closeSubcategorySuccessModal() {
    const successModal = document.getElementById('subcategory-success-modal');
    successModal.style.display = 'none';
    location.reload();
}

function deleteCategory(categoryId) {
    categoryToDelete = categoryId;
    const confirmModal = document.getElementById('confirm-delete-modal');
    confirmModal.style.display = 'flex';
}

function confirmDeleteCategory() {
    if (categoryToDelete !== null) {
        fetch(`/admin/category/delete/${categoryToDelete}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ошибка! Статус: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                closeConfirmDeleteModal();
                const successModal = document.getElementById('success-modal');
                const successName = document.getElementById('success-category-name');
                const successIcon = document.getElementById('success-category-icon');
                successName.textContent = 'Категория удалена';
                successIcon.style.display = 'none';
                successModal.style.display = 'flex';
            } else {
                showErrorModal('Ошибка при удалении категории: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            showErrorModal('Ошибка удаления категории: ' + error.message);
        });
    }
}

function deleteSubcategory(subcategoryId) {
    fetch(`/admin/delete_subcategory/${subcategoryId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            location.reload(); // Можно заменить на динамическое удаление элемента
        } else {
            showErrorModal('Ошибка при удалении подкатегории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        showErrorModal('Ошибка удаления подкатегории: ' + error.message);
    });
}

function closeConfirmDeleteModal() {
    const confirmModal = document.getElementById('confirm-delete-modal');
    confirmModal.style.display = 'none';
    categoryToDelete = null;
}

function showErrorModal(message) {
    const errorModal = document.getElementById('error-modal');
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = message;
    errorModal.style.display = 'flex';
}

function closeErrorModal() {
    const errorModal = document.getElementById('error-modal');
    errorModal.style.display = 'none';
}

function showIconSelector() {
    alert('Выберите иконку из списка стандартных или загруженных через основную страницу управления категориями!');
    // Здесь можно добавить динамическую загрузку иконок через /admin/get_uploaded_icons
}