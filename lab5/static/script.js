const GRID_SIZE = 10;
let grid = Array(GRID_SIZE).fill().map(() => Array(GRID_SIZE).fill(0));
let isDrawing = false;

// Инициализация сетки
function initializeGrid() {
    const container = document.getElementById('gridContainer');
    container.innerHTML = '';

    for (let i = 0; i < GRID_SIZE; i++) {
        for (let j = 0; j < GRID_SIZE; j++) {
            const cell = document.createElement('div');
            cell.className = 'grid-cell';
            cell.dataset.row = i;
            cell.dataset.col = j;

            cell.addEventListener('mousedown', (e) => {
                isDrawing = true;
                toggleCell(i, j);
            });

            cell.addEventListener('mouseover', (e) => {
                if (isDrawing) {
                    toggleCell(i, j);
                }
            });

            cell.addEventListener('mouseup', () => {
                isDrawing = false;
            });

            container.appendChild(cell);
        }
    }
}

function toggleCell(row, col) {
    grid[row][col] = grid[row][col] ? 0 : 1;
    updateGridDisplay();
}

function updateGridDisplay() {
    const cells = document.querySelectorAll('.grid-cell');
    cells.forEach(cell => {
        const row = parseInt(cell.dataset.row);
        const col = parseInt(cell.dataset.col);
        cell.classList.toggle('active', grid[row][col] === 1);
    });
}

function clearCanvas() {
    grid = Array(GRID_SIZE).fill().map(() => Array(GRID_SIZE).fill(0));
    updateGridDisplay();
    document.getElementById('result').textContent = '—';
    document.getElementById('probabilities').innerHTML = '';
}

async function recognize() {
    try {
        const response = await fetch('/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ grid: grid })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('result').textContent = data.result;

            // Отображаем вероятности
            let probsHTML = '<div class="prob-bar-container">';
            for (const [digit, prob] of Object.entries(data.probabilities)) {
                const width = (prob * 100).toFixed(1);
                probsHTML += `
                    <div class="prob-item">
                        <span class="digit">${digit}</span>
                        <div class="prob-bar">
                            <div class="prob-fill" style="width: ${width}%"></div>
                        </div>
                        <span class="prob-value">${width}%</span>
                    </div>
                `;
            }
            probsHTML += '</div>';
            document.getElementById('probabilities').innerHTML = probsHTML;
        } else {
            alert(data.error || 'Ошибка распознавания');
        }
    } catch (error) {
        alert('Ошибка соединения с сервером');
    }
}

async function addToDataset() {
    const label = document.getElementById('labelSelect').value;
    if (!label) {
        alert('Выберите метку цифры');
        return;
    }

    try {
        const response = await fetch('/add_to_dataset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ grid: grid, label: label })
        });

        const data = await response.json();
        if (data.success) {
            alert(`Добавлен пример: ${label}\nВсего примеров: ${data.dataset_size}`);
            loadDataset();
        } else {
            alert(data.error);
        }
    } catch (error) {
        alert('Ошибка добавления примера');
    }
}

async function loadDataset() {
    try {
        const response = await fetch('/dataset');
        const data = await response.json();

        let listHTML = `<p>Всего примеров: ${data.size}</p>`;
        if (data.size > 0) {
            listHTML += '<ul>';
            data.samples.forEach(sample => {
                listHTML += `<li>${sample.id}. ${sample.label} 
                            <button onclick="deleteSample(${sample.id})">Удалить</button></li>`;
            });
            listHTML += '</ul>';
        }

        document.getElementById('datasetList').innerHTML = listHTML;
    } catch (error) {
        console.error('Error loading dataset:', error);
    }
}

async function deleteSample(sampleId) {
    if (!confirm('Удалить этот пример?')) return;

    try {
        const response = await fetch(`/dataset/${sampleId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        if (data.success) {
            loadDataset();
        } else {
            alert(data.error);
        }
    } catch (error) {
        alert('Ошибка удаления примера');
    }
}

async function trainNetwork() {
    if (!confirm('Обучить нейронную сеть? Это может занять некоторое время.')) return;

    try {
        const response = await fetch('/train', {
            method: 'POST'
        });

        const data = await response.json();
        if (data.success) {
            alert(`Сеть успешно обучена!\nИспользовано примеров: ${data.samples_used}`);
            loadNetworkInfo();
        } else {
            alert(data.error);
        }
    } catch (error) {
        alert('Ошибка обучения сети');
    }
}

async function loadNetworkInfo() {
    try {
        const response = await fetch('/network_info');
        const data = await response.json();

        const infoHTML = `
            <p>Архитектура сети:</p>
            <ul>
                <li>Входной слой: ${data.architecture.input_size} нейронов</li>
                <li>Скрытый слой: ${data.architecture.hidden_size} нейронов</li>
                <li>Выходной слой: ${data.architecture.output_size} нейронов</li>
                <li>Функция активации: ${data.architecture.activation}</li>
                <li>Веса загружены: ${data.weights_loaded ? 'Да' : 'Нет'}</li>
            </ul>
        `;

        document.getElementById('networkInfo').innerHTML = infoHTML;
    } catch (error) {
        console.error('Error loading network info:', error);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    initializeGrid();
    loadDataset();
    loadNetworkInfo();

    // Запрещаем перетаскивание изображений с холста
    document.addEventListener('dragstart', (e) => {
        if (e.target.classList.contains('grid-cell')) {
            e.preventDefault();
        }
    });
});