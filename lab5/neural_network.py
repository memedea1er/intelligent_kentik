import numpy as np
import pickle
import os

class NeuralNetwork:
    """
    Многослойный персептрон с одним скрытым слоем.
    Используется сигмоидная функция активации.
    """

    def __init__(self, input_size=100, hidden_size=30, output_size=7):
        """
        input_size: количество входов (10x10 изображение = 100 пикселей)
        hidden_size: количество нейронов в скрытом слое
        output_size: количество выходов (римские цифры I, II, III, IV, V, VI, VII → 7 классов)
        """
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        # Инициализация весов случайными значениями
        self.W1 = np.random.randn(self.input_size, self.hidden_size) * 0.1
        self.b1 = np.zeros((1, self.hidden_size))
        self.W2 = np.random.randn(self.hidden_size, self.output_size) * 0.1
        self.b2 = np.zeros((1, self.output_size))

    def sigmoid(self, x):
        # Ограничение аргумента для избежания переполнения
        x = np.clip(x, -500, 500)
        return 1 / (1 + np.exp(-x))

    def sigmoid_derivative(self, x):
        return x * (1 - x)

    def forward(self, X):
        """Прямое распространение"""
        self.z1 = np.dot(X, self.W1) + self.b1
        self.a1 = self.sigmoid(self.z1)
        self.z2 = np.dot(self.a1, self.W2) + self.b2
        self.a2 = self.sigmoid(self.z2)
        return self.a2

    def train(self, X, y, epochs=1000, lr=0.1):
        """Обучение методом обратного распространения ошибки"""
        m = X.shape[0]
        for epoch in range(epochs):
            # Прямой проход
            output = self.forward(X)

            # Ошибка на выходе
            error_output = y - output
            d_output = error_output * self.sigmoid_derivative(output)

            # Ошибка на скрытом слое
            error_hidden = d_output.dot(self.W2.T)
            d_hidden = error_hidden * self.sigmoid_derivative(self.a1)

            # Обновление весов
            self.W2 += self.a1.T.dot(d_output) * lr
            self.b2 += np.sum(d_output, axis=0, keepdims=True) * lr
            self.W1 += X.T.dot(d_hidden) * lr
            self.b1 += np.sum(d_hidden, axis=0, keepdims=True) * lr

    def predict(self, X):
        """Предсказание метки класса"""
        output = self.forward(X)
        return np.argmax(output, axis=1)

    def save_weights(self, filepath='weights.pkl'):
        """Сохранение весов в файл"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'W1': self.W1,
                'b1': self.b1,
                'W2': self.W2,
                'b2': self.b2
            }, f)

    def load_weights(self, filepath='weights.pkl'):
        """Загрузка весов из файла"""
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                params = pickle.load(f)
                self.W1 = params['W1']
                self.b1 = params['b1']
                self.W2 = params['W2']
                self.b2 = params['b2']
            return True
        else:
            print("Файл весов не найден. Инициализация случайными весами.")
            return False

    def print_architecture(self):
        """Вывод архитектуры сети в консоль"""
        print("Архитектура нейронной сети:")
        print(f"  Входной слой: {self.input_size} нейронов")
        print(f"  Скрытый слой: {self.hidden_size} нейронов")
        print(f"  Выходной слой: {self.output_size} нейронов")
        print("  Функция активации: сигмоида")
        print("  Алгоритм обучения: обратное распространение ошибки")