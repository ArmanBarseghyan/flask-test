// static/js/category_detail.js

let selectedIcon = '';

function toggleCreateSubcategory() {
    const menu = document.getElementById('create-subcategory-menu');
    menu.style.display = menu.style.display === 'none' ? 'grid' : 'none';
}

function showIconSelector() {
    const iconSelectorModal = document.getElementById('icon-selector-modal');
    iconSelectorModal.style.display = 'flex';
}

function closeIconSelector() {
    const iconSelectorModal = document.getElementById('icon-selector-modal');
    iconSelectorModal.style.display = 'none';
}

function selectIcon(iconPath) {
    selectedIcon = iconPath;
    document.getElementById('category_icon').value = iconPath;
    const previewModal = document.getElementById('icon-preview');
    const previewIcon = document.getElementById('preview-icon');
    previewIcon.src = `/static/uploads/category_icons/${iconPath}`;
    previewModal.style.display = 'flex';
    closeIconSelector();
}

function closeIconPreview() {
    const previewModal = document.getElementById('icon-preview');
    previewModal.style.display = 'none';
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
            location.reload();
        } else {
            showErrorModal('Ошибка при удалении подкатегории: ' + (data.error || 'Неизвестная ошибка'));
        }
    })
    .catch(error => {
        showErrorModal('Ошибка удаления подкатегории: ' + error.message);
    });
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

function showDeleteConfirmModal() {
    const confirmModal = document.getElementById('delete-confirm-modal-detail');
    confirmModal.style.display = 'flex';
}

function closeDeleteConfirmModal() {
    const confirmModal = document.getElementById('delete-confirm-modal-detail');
    confirmModal.style.display = 'none';
}

function confirmDeleteCategoryDetail() {
    const form = document.getElementById('category-form');
    form.elements['action'].value = 'delete_category'; // Устанавливаем значение action
    form.submit(); // Отправляем форму
}

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}