document.addEventListener('DOMContentLoaded', () => {
    const svgObject = document.getElementById('floor-map');
    const popup = document.getElementById('shop-popup');
    const closeBtn = document.getElementById('popup-close');
    const mapLoader = document.getElementById('map-loader');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressInfo = document.getElementById('progress-info');
    const mapsData = JSON.parse(document.getElementById('maps-data').textContent);

    let selectedGroup = null;
    let svgDoc = null;
    let totalGroups = 0;
    let loadedGroups = 0;
    let highlightedCategory = null;

    const COLORS = {
        DEFAULT: '#404957',
        HOVER: '#5680BB',
        SELECTED: '#0B51B4',
    };

    const CACHE_KEY = 'shopDataCache';
    const CACHE_VERSION_KEY = 'shopDataCacheVersion';
    const CACHE_EXPIRY = 24 * 60 * 60 * 1000; // 24 часа

    function updateProgress(loaded, total, message = null) {
        const percentage = Math.round((loaded / total) * 100);
        progressBar.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}%`;
        if (message) progressInfo.textContent = message;
        if (loaded >= total) {
            setTimeout(() => mapLoader.style.display = 'none', 500);
        }
    }

    function closePopup() {
        popup.style.display = 'none';
        if (selectedGroup) {
            const shopId = selectedGroup.getAttribute('id');
            const shop = shopData.find(s => s.id === shopId);
            setGroupColor(selectedGroup, (highlightedCategory && shop && shop.category_id === parseInt(highlightedCategory)) ? (shop.category_color || COLORS.DEFAULT) : COLORS.DEFAULT);
            selectedGroup = null;
        }
    }

    function setGroupColor(group, color) {
        const elements = group.querySelectorAll('path, rect');
        elements.forEach(el => el.setAttribute('fill', color || COLORS.DEFAULT));
    }

    function createLogo(group, logoUrl, options = {}) {
        const bbox = group.getBBox();
        const logoWidth = options.width || 30;
        const logoHeight = options.height || 30;
        const logoXOffset = options.xOffset || 0;
        const logoYOffset = options.yOffset || 0;
        
        const x = bbox.x + (bbox.width - logoWidth) / 2 + logoXOffset;
        const y = bbox.y + (bbox.height - logoHeight) / 2 + logoYOffset;

        const logoImage = document.createElementNS('http://www.w3.org/2000/svg', 'image');
        logoImage.setAttribute('href', logoUrl);
        logoImage.setAttribute('x', x);
        logoImage.setAttribute('y', y);
        logoImage.setAttribute('width', logoWidth);
        logoImage.setAttribute('height', logoHeight);
        logoImage.setAttribute('preserveAspectRatio', 'xMidYMid meet');
        logoImage.setAttribute('pointer-events', 'none');
        
        group.appendChild(logoImage);
        return logoImage;
    }

    function getCachedShopData() {
        const cachedData = localStorage.getItem(CACHE_KEY);
        const cachedVersion = localStorage.getItem(CACHE_VERSION_KEY);
        const now = Date.now();
        if (cachedData && cachedVersion && (now - cachedVersion < CACHE_EXPIRY)) {
            return JSON.parse(cachedData);
        }
        return null;
    }

    function saveShopDataToCache(data) {
        const version = Date.now(); // Или хэш из данных
        localStorage.setItem(CACHE_KEY, JSON.stringify(data));
        localStorage.setItem(CACHE_VERSION_KEY, version);
    }

    function fetchShopData(shopId) {
        return fetch(`/shop/${shopId}`, { 
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            cache: 'no-store'
        })
        .then(response => response.json());
    }

    function fetchAllShopsData() {
        return fetch('/shops/all', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(response => response.json());
    }

    function displayShopData(data) {
        document.getElementById('popup-logo').src = data.shop_logo || '/static/uploads/vector/static-logo.svg';
        document.querySelector('.banner-web img').src = data.shop_banner || '/static/images/default-banner.svg';
        document.getElementById('popup-name').textContent = data.shop_name || 'Без названия';
        document.getElementById('popup-description').textContent = data.descriptions[0] || 'Нет описания';
        document.getElementById('popup-worktime').textContent = data.work_time || 'Не указано';
        
        const categoryRow = document.getElementById('category-row');
        const categoryIcon = document.getElementById('category-icon');
        const categoryText = document.getElementById('category-text');
        if (data.category && data.category.trim()) {
            categoryIcon.style.display = data.category_icon ? 'inline' : 'none';
            if (data.category_icon) categoryIcon.src = data.category_icon;
            categoryText.textContent = data.category;
            categoryRow.style.display = '';
        } else {
            categoryRow.style.display = 'none';
        }
        
        const subcategoriesRow = document.getElementById('subcategories-row');
        const subcategoriesContainer = document.getElementById('popup-subcategories');
        subcategoriesContainer.innerHTML = '';
        if (data.subcategories && data.subcategories.length > 0) {
            const fragment = document.createDocumentFragment();
            data.subcategories.forEach(sub => {
                const span = document.createElement('span');
                span.className = 'subcategory-item';
                span.textContent = sub.name;
                fragment.appendChild(span);
            });
            subcategoriesContainer.appendChild(fragment);
            subcategoriesRow.style.display = '';
        } else {
            subcategoriesRow.style.display = 'none';
        }
        
        const websiteRow = document.getElementById('website-row');
        const websiteLink = document.getElementById('popup-website');
        websiteRow.style.display = data.web_url && data.web_url.trim() ? '' : 'none';
        if (data.web_url && data.web_url.trim()) {
            websiteLink.href = data.web_url;
            websiteLink.textContent = data.web_text || 'Перейти на сайт';
        }
        
        document.getElementById('shop-page-link').href = `/shop/${data.id}`;
        
        const pavilionLink = document.getElementById('pavilion-link');
        if (pavilionLink) {
            pavilionLink.style.display = data.is_admin ? 'block' : 'none';
            if (data.is_admin) pavilionLink.href = `/admin/shop/${data.id}`;
        }
        
        popup.style.display = 'flex';
    }

    function handleShopClick(group) {
        if (selectedGroup && selectedGroup !== group) {
            setGroupColor(selectedGroup, highlightedCategory ? COLORS.HIGHLIGHTED : COLORS.DEFAULT);
        }
        
        setGroupColor(group, COLORS.SELECTED);
        selectedGroup = group;
        
        const shopId = group.getAttribute('id');
        updateProgress(loadedGroups, totalGroups, `Загрузка данных для ${shopId}...`);
        
        fetchShopData(shopId)
            .then(displayShopData)
            .catch(error => console.error('Ошибка загрузки данных магазина:', error));
    }

    function addBackgroundImage(svgRoot) {
        updateProgress(0, totalGroups + 1, 'Загрузка фонового изображения...');
        
        const dataAttr = svgObject.getAttribute('data');
        const floorIdMatch = dataAttr && dataAttr.match(/(\d+)\.svg/);
        if (!floorIdMatch) {
            updateProgress(1, totalGroups + 1);
            return null;
        }
        
        const floorId = floorIdMatch[1];
        const backgroundFilename = mapsData.floors[floorId]?.background_filename; // Имя файла из данных
    
        // --- ИСПРАВЛЕНО ЗДЕСЬ ---
        const backgroundPath = backgroundFilename
            ? `/static/uploads/backgrounds/${backgroundFilename}` // Добавили /backgrounds/
            : null;
        // --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    
        if (!backgroundPath) {
            console.log(`Фон для этажа ${floorId} не найден в mapsData.`); // Добавил лог
            updateProgress(1, totalGroups + 1); // Обновляем прогресс, т.к. фона нет
            return null;
        }
        console.log(`Добавляем фон: ${backgroundPath}`); // Лог для отладки пути
        
        const backgroundImage = document.createElementNS('http://www.w3.org/2000/svg', 'image');
        backgroundImage.setAttribute('href', backgroundPath);
        backgroundImage.setAttribute('x', '0');
        backgroundImage.setAttribute('y', '0');
        backgroundImage.setAttribute('width', svgRoot.getAttribute('width') || '100%');
        backgroundImage.setAttribute('height', svgRoot.getAttribute('height') || '100%');
        backgroundImage.setAttribute('preserveAspectRatio', 'xMinYMin meet');
        backgroundImage.setAttribute('pointer-events', 'none');
        
        backgroundImage.onload = () => updateProgress(1, totalGroups + 1);
        backgroundImage.onerror = () => {
            console.error('Ошибка загрузки фонового изображения');
            updateProgress(1, totalGroups + 1);
        };
        
        svgRoot.insertBefore(backgroundImage, svgRoot.firstChild);
        return backgroundImage;
    }

    window.highlightCategory = function(categoryId) {
        if (!svgDoc) return;
        const groups = svgDoc.getElementsByTagName('g');
        highlightedCategory = categoryId === 'all' ? null : categoryId;
    
        Array.from(groups).forEach(group => {
            const shopId = group.getAttribute('id');
            const shop = shopData.find(s => s.id === shopId);
            if (!shop) {
                setGroupColor(group, COLORS.DEFAULT);
                return;
            }
            if (categoryId === 'all') {
                setGroupColor(group, COLORS.DEFAULT);
            } else if (shop.category_id === parseInt(categoryId)) {
                setGroupColor(group, shop.category_color || COLORS.DEFAULT);
            } else {
                setGroupColor(group, COLORS.DEFAULT);
            }
        });
    };

    function initShopGroup(group, index, cachedData = null) {
        const shopId = group.getAttribute('id');
        updateProgress(loadedGroups, totalGroups, `Загрузка павильона ${shopId} (${index+1}/${totalGroups})...`);
        
        group.style.cursor = 'pointer';
        setGroupColor(group, COLORS.DEFAULT);
        
        const elements = group.querySelectorAll('path, rect');
        elements.forEach(el => el.style.transition = 'fill 0.3s ease');
        
        group.addEventListener('mouseover', () => {
            if (selectedGroup !== group) setGroupColor(group, COLORS.HOVER);
        });
        group.addEventListener('mouseout', () => {
            if (selectedGroup !== group) {
                const shopId = group.getAttribute('id');
                const shop = shopData.find(s => s.id === shopId);
                const defaultColor = (highlightedCategory && shop && shop.category_id === parseInt(highlightedCategory)) 
                    ? (shop.category_color || COLORS.DEFAULT) 
                    : COLORS.DEFAULT;
                setGroupColor(group, defaultColor);
            }
        });
        
        group.addEventListener('click', () => handleShopClick(group));
        
        const cachedShop = cachedData ? cachedData.find(s => s.id === shopId) : null;
        if (cachedShop) {
            const logoUrl = cachedShop.scheme_logo || '/static/images/vector/static-logo.svg';
            const logoOptions = {
                width: cachedShop.scheme_logo_width || 30,
                height: cachedShop.scheme_logo_height || 30,
                xOffset: cachedShop.scheme_logo_x || 0,
                yOffset: cachedShop.scheme_logo_y || 0
            };
            createLogo(group, logoUrl, logoOptions);
            setGroupColor(group, COLORS.DEFAULT);
            
            loadedGroups++;
            updateProgress(loadedGroups, totalGroups, 
                loadedGroups === totalGroups ? 'Карта загружена из кеша!' : `Загрузка павильонов: ${loadedGroups}/${totalGroups}`);
            
            return Promise.resolve(cachedShop);
        } else {
            return fetchShopData(shopId)
                .then(data => {
                    const logoUrl = data.scheme_logo || '/static/images/vector/static-logo.svg';
                    const logoOptions = {
                        width: data.scheme_logo_width || 30,
                        height: data.scheme_logo_height || 30,
                        xOffset: data.scheme_logo_x || 0,
                        yOffset: data.scheme_logo_y || 0
                    };
                    createLogo(group, logoUrl, logoOptions);
                    setGroupColor(group, COLORS.DEFAULT);
                    
                    loadedGroups++;
                    updateProgress(loadedGroups, totalGroups, 
                        loadedGroups === totalGroups ? 'Карта загружена!' : `Загрузка павильонов: ${loadedGroups}/${totalGroups}`);
                    
                    return data;
                })
                .catch(error => {
                    console.error(`Ошибка загрузки логотипа для ${shopId}:`, error);
                    createLogo(group, '/static/images/vector/static-logo.svg');
                    
                    loadedGroups++;
                    updateProgress(loadedGroups, totalGroups,
                        loadedGroups === totalGroups ? 'Карта загружена!' : `Загрузка павильонов: ${loadedGroups}/${totalGroups}`);
                });
        }
    }

    function highlightShopFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        const shopIdToHighlight = urlParams.get('highlight_shop');
        if (shopIdToHighlight && svgDoc) {
            const group = svgDoc.getElementById(shopIdToHighlight);
            if (group) {
                setGroupColor(group, COLORS.SELECTED);
                selectedGroup = group;
            } else {
                console.warn(`Павильон с ID ${shopIdToHighlight} не найден на карте`);
            }
        }
    }

    function checkCacheValidity(cachedData, serverData) {
        return cachedData.every(cachedShop => {
            const serverShop = serverData.find(s => s.id === cachedShop.id);
            return serverShop && cachedShop.data_version === serverShop.data_version;
        });
    }

    function initSVG() {
        svgDoc = svgObject.contentDocument;
        if (!svgDoc) {
            console.error('SVG document not loaded');
            return;
        }
        
        const svgRoot = svgDoc.documentElement;
        const groups = Array.from(svgDoc.getElementsByTagName('g'));
        totalGroups = groups.length;
        loadedGroups = 0;
        
        console.log(`Found ${totalGroups} groups in SVG`);
        updateProgress(0, totalGroups + 1, 'Инициализация карты...');
        
        addBackgroundImage(svgRoot);
        
        const cachedData = getCachedShopData();
        if (cachedData) {
            fetchAllShopsData().then(serverData => {
                if (checkCacheValidity(cachedData, serverData)) {
                    const logoPromises = groups.map((group, index) => initShopGroup(group, index, cachedData));
                    Promise.allSettled(logoPromises).then(() => {
                        console.log('All logos processed from cache');
                        updateProgress(totalGroups, totalGroups, 'Карта загружена из кеша!');
                        highlightShopFromUrl();
                    });
                } else {
                    saveShopDataToCache(serverData);
                    const logoPromises = groups.map((group, index) => initShopGroup(group, index, serverData));
                    Promise.allSettled(logoPromises).then(() => {
                        console.log('All logos processed from server (cache updated)');
                        updateProgress(totalGroups, totalGroups, 'Карта загружена!');
                        highlightShopFromUrl();
                    });
                }
            });
        } else {
            fetchAllShopsData().then(data => {
                saveShopDataToCache(data);
                const logoPromises = groups.map((group, index) => initShopGroup(group, index, data));
                Promise.allSettled(logoPromises).then(() => {
                    console.log('All logos processed from server');
                    updateProgress(totalGroups, totalGroups, 'Карта загружена!');
                    highlightShopFromUrl();
                });
            });
        }
    }

    svgObject.addEventListener('load', () => {
        console.log('SVG loaded event triggered');
        initSVG();
    });
    
    const retryTimeout = setTimeout(() => {
        if (svgDoc === null) {
            console.log('Retrying SVG initialization...');
            initSVG();
        }
        clearTimeout(retryTimeout);
    }, 1000);
    
    updateProgress(0, 1, 'Ожидание загрузки SVG...');
    
    closeBtn.addEventListener('click', closePopup);
    popup.addEventListener('click', (e) => {
        if (e.target === popup) closePopup();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && popup.style.display === 'flex') closePopup();
    });
});