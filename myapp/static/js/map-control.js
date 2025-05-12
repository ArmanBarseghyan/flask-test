// // static/js/map-control.js

// document.addEventListener('DOMContentLoaded', () => {
//     const svgObject = document.getElementById('floor-map');
//     const container = svgObject.parentElement; // Контейнер для SVG

//     let svgDoc, svgRoot;
//     let transformMatrix = [1, 0, 0, 1, 0, 0]; // [scaleX, skewY, skewX, scaleY, translateX, translateY]
//     const minScale = 0.5;
//     const maxScale = 3;
//     const zoomStep = 0.2;
//     let bounds;

//     // Инициализация SVG
//     svgObject.addEventListener('load', () => {
//         svgDoc = svgObject.contentDocument;
//         svgRoot = svgDoc.documentElement;

//         // Устанавливаем начальные размеры и границы
//         const viewBox = svgRoot.getAttribute('viewBox')?.split(' ').map(Number) || [0, 0, parseFloat(svgRoot.getAttribute('width')) || 1000, parseFloat(svgRoot.getAttribute('height')) || 800];
//         bounds = {
//             minX: viewBox[0] - viewBox[2] * 2, // Расширяем границы
//             maxX: viewBox[0] + viewBox[2] * 3,
//             minY: viewBox[1] - viewBox[3] * 2,
//             maxY: viewBox[1] + viewBox[3] * 3
//         };

//         // Применяем начальную трансформацию
//         applyTransform();

//         // Устанавливаем стиль для перемещения
//         svgObject.style.cursor = 'grab';
//     });

//     // Применение трансформации
//     function applyTransform() {
//         // Ограничиваем масштаб
//         transformMatrix[0] = Math.max(minScale, Math.min(maxScale, transformMatrix[0]));
//         transformMatrix[3] = transformMatrix[0]; // scaleX = scaleY

//         // Вычисляем видимую область с учётом масштаба
//         const scaledWidth = svgRoot.getBBox().width * transformMatrix[0];
//         const scaledHeight = svgRoot.getBBox().height * transformMatrix[3];
//         const containerRect = container.getBoundingClientRect();

//         // Ограничиваем перемещение
//         transformMatrix[4] = Math.max(bounds.minX, Math.min(bounds.maxX - scaledWidth, transformMatrix[4]));
//         transformMatrix[5] = Math.max(bounds.minY, Math.min(bounds.maxY - scaledHeight, transformMatrix[5]));

//         // Применяем матрицу к корневому элементу SVG
//         svgRoot.setAttribute('transform', `matrix(${transformMatrix.join(' ')})`);
//     }

//     // Увеличение
//     document.getElementById('zoom-in').addEventListener('click', () => {
//         transformMatrix[0] += zoomStep;
//         transformMatrix[3] = transformMatrix[0];
//         centerTransform();
//         applyTransform();
//     });

//     // Уменьшение
//     document.getElementById('zoom-out').addEventListener('click', () => {
//         transformMatrix[0] -= zoomStep;
//         transformMatrix[3] = transformMatrix[0];
//         centerTransform();
//         applyTransform();
//     });

//     // Сброс к исходному виду
//     document.getElementById('reset-view').addEventListener('click', () => {
//         transformMatrix = [1, 0, 0, 1, 0, 0];
//         centerTransform();
//         applyTransform();
//     });

//     // Масштабирование через скролл
//     container.addEventListener('wheel', (e) => {
//         e.preventDefault();
//         const scaleChange = e.deltaY < 0 ? zoomStep : -zoomStep;
//         const oldScale = transformMatrix[0];
//         const newScale = Math.max(minScale, Math.min(maxScale, transformMatrix[0] + scaleChange));
//         transformMatrix[0] = newScale;
//         transformMatrix[3] = newScale;

//         // Центрирование на курсоре
//         const rect = container.getBoundingClientRect();
//         const mouseX = e.clientX - rect.left;
//         const mouseY = e.clientY - rect.top;
//         const scaleFactor = newScale / oldScale;
//         transformMatrix[4] = mouseX - (mouseX - transformMatrix[4]) * scaleFactor;
//         transformMatrix[5] = mouseY - (mouseY - transformMatrix[5]) * scaleFactor;

//         applyTransform();
//     }, { passive: false });

//     // Перемещение (drag)
//     let isDragging = false;
//     let startX, startY;

//     container.addEventListener('mousedown', (e) => {
//         isDragging = true;
//         startX = e.clientX - transformMatrix[4];
//         startY = e.clientY - transformMatrix[5];
//         svgObject.style.cursor = 'grabbing';
//     });

//     container.addEventListener('mousemove', (e) => {
//         if (isDragging) {
//             transformMatrix[4] = e.clientX - startX;
//             transformMatrix[5] = e.clientY - startY;
//             applyTransform();
//         }
//     });

//     container.addEventListener('mouseup', () => {
//         isDragging = false;
//         svgObject.style.cursor = 'grab';
//     });

//     container.addEventListener('mouseleave', () => {
//         isDragging = false;
//         svgObject.style.cursor = 'grab';
//     });

//     // Центрирование карты
//     function centerTransform() {
//         const rect = container.getBoundingClientRect();
//         const scaledWidth = svgRoot.getBBox().width * transformMatrix[0];
//         const scaledHeight = svgRoot.getBBox().height * transformMatrix[3];
//         transformMatrix[4] = (rect.width - scaledWidth) / 2;
//         transformMatrix[5] = (rect.height - scaledHeight) / 2;
//     }
// });