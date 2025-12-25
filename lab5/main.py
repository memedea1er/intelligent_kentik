from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import numpy as np
import pickle
import os
from typing import List, Optional
from neural_network import NeuralNetwork
import json

app = FastAPI(title="Распознавание римских цифр")

# Монтируем статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Константы
ROMAN_DIGITS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
GRID_SIZE = 10
PIXEL_SIZE = 30
DATASET_PATH = 'dataset.pkl'
WEIGHTS_PATH = 'weights.pkl'

# Инициализация нейросети
nn = NeuralNetwork()
if not nn.load_weights(WEIGHTS_PATH):
    nn.save_weights(WEIGHTS_PATH)


# Загрузка датасета
def load_dataset(path=DATASET_PATH):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return pickle.load(f)
    return []


def save_dataset(dataset, path=DATASET_PATH):
    with open(path, 'wb') as f:
        pickle.dump(dataset, f)


dataset = load_dataset()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с холстом для рисования"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "grid_size": GRID_SIZE,
        "pixel_size": PIXEL_SIZE,
        "roman_digits": ROMAN_DIGITS
    })


@app.post("/recognize")
async def recognize_digit(request: Request):
    """Распознавание нарисованной цифры"""
    try:
        data = await request.json()
        grid = data.get("grid", [])

        if not grid:
            return JSONResponse({"error": "Grid is empty"}, status_code=400)

        # Преобразуем в numpy массив
        X = np.array(grid, dtype=float).flatten().reshape(1, -1)

        if X.sum() == 0:
            return JSONResponse({"error": "Draw a digit first!"}, status_code=400)

        # Предсказание
        pred = nn.predict(X)[0]
        result = ROMAN_DIGITS[pred]

        # Получаем вероятности для всех классов
        output = nn.forward(X)[0]
        probabilities = {ROMAN_DIGITS[i]: float(output[i]) for i in range(len(ROMAN_DIGITS))}

        return JSONResponse({
            "result": result,
            "probabilities": probabilities,
            "success": True
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/add_to_dataset")
async def add_to_dataset(request: Request):
    """Добавление примера в обучающую выборку"""
    try:
        data = await request.json()
        grid = data.get("grid", [])
        label = data.get("label", "")

        if not grid:
            return JSONResponse({"error": "Grid is empty"}, status_code=400)

        if label not in ROMAN_DIGITS:
            return JSONResponse({"error": f"Invalid label. Allowed: {', '.join(ROMAN_DIGITS)}"}, status_code=400)

        X = np.array(grid, dtype=float).flatten()
        y = ROMAN_DIGITS.index(label)

        dataset.append((X, y))
        save_dataset(dataset)

        return JSONResponse({
            "success": True,
            "message": f"Sample added as '{label}'",
            "dataset_size": len(dataset)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/dataset")
async def get_dataset():
    """Получение информации о датасете"""
    dataset_info = [{"id": i + 1, "label": ROMAN_DIGITS[y]} for i, (_, y) in enumerate(dataset)]
    return JSONResponse({
        "size": len(dataset),
        "samples": dataset_info
    })


@app.delete("/dataset/{sample_id}")
async def delete_sample(sample_id: int):
    """Удаление примера из датасета"""
    try:
        if 1 <= sample_id <= len(dataset):
            del dataset[sample_id - 1]
            save_dataset(dataset)
            return JSONResponse({
                "success": True,
                "message": f"Sample {sample_id} deleted",
                "dataset_size": len(dataset)
            })
        else:
            return JSONResponse({"error": "Invalid sample ID"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/train")
async def train_network():
    """Обучение нейронной сети"""
    try:
        if len(dataset) < 2:
            return JSONResponse({
                "error": "Not enough data for training (minimum 2 samples)",
                "success": False
            }, status_code=400)

        # Подготовка данных
        X = np.array([item[0] for item in dataset])
        y = np.array([item[1] for item in dataset])

        # One-hot encoding
        Y = np.zeros((y.size, 7))
        Y[np.arange(y.size), y] = 1

        # Обучение
        nn.train(X, Y, epochs=2000, lr=0.3)
        nn.save_weights(WEIGHTS_PATH)

        return JSONResponse({
            "success": True,
            "message": "Network trained and weights saved!",
            "samples_used": len(dataset)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/clear")
async def clear_canvas():
    """Очистка холста (только для логики)"""
    return JSONResponse({"success": True, "message": "Canvas cleared"})


@app.get("/network_info")
async def get_network_info():
    """Получение информации о нейронной сети"""
    return JSONResponse({
        "architecture": {
            "input_size": nn.input_size,
            "hidden_size": nn.hidden_size,
            "output_size": nn.output_size,
            "activation": "sigmoid"
        },
        "weights_loaded": os.path.exists(WEIGHTS_PATH)
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)