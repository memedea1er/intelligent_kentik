#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ФРЕЙМОВАЯ ЭКСПЕРТНАЯ СИСТЕМА ДЛЯ РЕКОМЕНДАЦИИ ВИДЕОИГР
Основана на теории фреймов Марвина Минского
База знаний хранится в формате JSON

Состав системы:
1. frame.py - реализация фреймов согласно теории Минского
2. knowledge_base.py - база знаний с фреймами (хранится в JSON)
3. working_memory.py - рабочая память системы
4. inference_engine.py - механизм логического вывода
5. explanation_component.py - компонента объяснения
6. main.py - основной модуль запуска
"""

import json
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field


# ============================================================================
# МОДУЛЬ 1: ФРЕЙМЫ (frame.py)
# ============================================================================

class InheritanceType(Enum):
    """Типы наследования согласно теории Минского"""
    UNIQUE = "U"  # Unique - уникальное значение для каждого экземпляра
    SAME = "S"  # Same - то же самое значение, что у родителя
    RANGE = "R"  # Range - значение из допустимого диапазона
    OVERRIDE = "O"  # Override - может быть переопределено потомком


class DataType(Enum):
    """Типы данных для слотов"""
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    FRAME = "FRAME"
    LIST = "LIST"


class TriggerType(Enum):
    """Типы триггерных процедур"""
    IF_NEEDED = "IF-NEEDED"  # Вызывается при запросе пустого слота
    IF_ADDED = "IF-ADDED"  # Вызывается при добавлении значения
    IF_REMOVED = "IF-REMOVED"  # Вызывается при удаления значения


class Slot:
    """Слот фрейма согласно теории Минского"""

    def __init__(self, name: str, value: Any = None,
                 data_type: DataType = DataType.TEXT,
                 inheritance: InheritanceType = InheritanceType.OVERRIDE,
                 range_values: List[Any] = None,
                 triggers: Dict[TriggerType, Callable] = None):
        self.name = name
        self.value = value
        self.data_type = data_type
        self.inheritance = inheritance
        self.range_values = range_values or []
        self.triggers = triggers or {}
        self.default_value = value

    def _validate_type(self, value: Any) -> bool:
        """Проверка соответствия типа данных"""
        if value is None:
            return True

        if self.data_type == DataType.INTEGER:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif self.data_type == DataType.TEXT:
            return isinstance(value, str)
        elif self.data_type == DataType.BOOLEAN:
            return isinstance(value, bool)
        elif self.data_type == DataType.FRAME:
            return isinstance(value, Frame)
        elif self.data_type == DataType.LIST:
            return isinstance(value, list)
        return True

    def _validate_range(self, value: Any) -> bool:
        """Проверка соответствия диапазону значений"""
        if not self.range_values:
            return True
        return value in self.range_values

    def set_value(self, frame, value: Any):
        """Установка значения с валидацией и триггерами"""
        # Валидация типа
        if not self._validate_type(value):
            raise ValueError(
                f"Неверный тип данных '{type(value).__name__}' для слота {self.name}. Ожидается {self.data_type.value}")

        # Валидация диапазона
        if not self._validate_range(value):
            raise ValueError(
                f"Значение '{value}' не входит в допустимый диапазон {self.range_values} для слота {self.name}")

        old_value = self.value
        self.value = value

        # Вызов IF-ADDED триггера
        if TriggerType.IF_ADDED in self.triggers:
            self.triggers[TriggerType.IF_ADDED](frame, old_value, value)

    def get_value(self, frame) -> Any:
        """Получение значения с поддержкой IF-NEEDED"""
        if self.value is None and self.default_value is not None:
            # Возвращаем значение по умолчанию
            return self.default_value

        if self.value is None:
            # Вызов IF-NEEDED триггера для вычисления значения
            if TriggerType.IF_NEEDED in self.triggers:
                computed_value = self.triggers[TriggerType.IF_NEEDED](frame)
                # Временно устанавливаем вычисленное значение
                if self._validate_type(computed_value) and self._validate_range(computed_value):
                    self.value = computed_value
                    return computed_value
            return None

        return self.value

    def remove_value(self, frame):
        """Удаление значения с вызовом IF-REMOVED"""
        old_value = self.value
        self.value = None

        if TriggerType.IF_REMOVED in self.triggers:
            self.triggers[TriggerType.IF_REMOVED](frame, old_value)


class Frame:
    """Фрейм согласно теории Марвина Минского"""

    def __init__(self, name: str):
        self.name = name
        self.slots: Dict[str, Slot] = {}

        # Системные слоты
        ako_slot = Slot("AKO", None, DataType.FRAME, InheritanceType.SAME)
        self.slots["AKO"] = ako_slot

    def add_slot(self, slot: Slot):
        """Добавление слота во фрейм"""
        self.slots[slot.name] = slot

    def get_slot(self, slot_name: str) -> Optional[Slot]:
        """Получение слота по имени"""
        return self.slots.get(slot_name)

    def get_slot_value(self, slot_name: str) -> Any:
        """Получение значения слота с полной поддержкой наследования"""
        if slot_name in self.slots:
            slot = self.slots[slot_name]
            value = slot.get_value(self)
            if value is not None:
                return value

        # Наследование через AKO
        ako_frame = self.slots["AKO"].value
        if ako_frame and isinstance(ako_frame, Frame):
            return ako_frame.get_slot_value(slot_name)

        return None

    def set_slot_value(self, slot_name: str, value: Any):
        """Установка значения слота"""
        if slot_name not in self.slots:
            # Создаем новый слот по умолчанию
            data_type = DataType.TEXT
            if isinstance(value, bool):
                data_type = DataType.BOOLEAN
            elif isinstance(value, (int, float)):
                data_type = DataType.INTEGER
            elif isinstance(value, Frame):
                data_type = DataType.FRAME
            elif isinstance(value, list):
                data_type = DataType.LIST

            new_slot = Slot(slot_name, value, data_type)
            self.slots[slot_name] = new_slot
        else:
            self.slots[slot_name].set_value(self, value)

    def set_ako(self, parent_frame: 'Frame'):
        """Установка родительского фрейма через AKO"""
        self.slots["AKO"].value = parent_frame

    def is_a(self, frame_type: str) -> bool:
        """Проверяет, является ли фрейм экземпляром указанного типа"""
        current = self
        while current:
            if current.name == frame_type:
                return True
            ako = current.slots["AKO"].value
            if ako and isinstance(ako, Frame):
                current = ako
            else:
                break
        return False

    def create_proto_frame(self) -> 'Frame':
        """Создает протофрейм (незаполненную копию)"""
        proto = Frame(f"Proto_{self.name}")
        proto.set_ako(self)
        return proto

    def __str__(self):
        slots_info = []
        for slot_name, slot in self.slots.items():
            if slot_name == "AKO":
                ako_name = slot.value.name if slot.value else "None"
                slots_info.append(f"{slot_name}: {ako_name}")
            else:
                value = slot.get_value(self)
                slots_info.append(f"{slot_name}: {value}")

        slots_str = ", ".join(slots_info)
        return f"Frame({self.name}, slots: [{slots_str}])"

    def __repr__(self):
        return self.__str__()


# ============================================================================
# МОДУЛЬ 2: БАЗА ЗНАНИЙ (knowledge_base.py)
# ============================================================================

class KnowledgeBase:
    """База знаний, хранящая фреймы согласно теории Минского в формате JSON"""

    def __init__(self, json_file: str):
        self.frames: Dict[str, Frame] = {}
        self._procedures = {}
        self.load_from_json(json_file)

    def _register_procedures(self):
        """Регистрация встроенных процедур"""
        # IF-NEEDED процедуры
        self._procedures["calculate_compatibility"] = self._calculate_compatibility
        self._procedures["get_recommendation_reason"] = self._get_recommendation_reason
        self._procedures["determine_platform"] = self._determine_platform
        self._procedures["suggest_similar_games"] = self._suggest_similar_games

        # IF-ADDED процедуры
        self._procedures["validate_budget"] = self._validate_budget
        self._procedures["update_genre_compatibility"] = self._update_genre_compatibility
        self._procedures["validate_session_length"] = self._validate_session_length

    def _calculate_compatibility(self, frame) -> float:
        """IF-NEEDED: Вычисляет совместимость игры с пользователем"""
        # Это демонстрационная процедура
        compatibility = 0.0

        # Проверяем платформу
        platform = frame.get_slot_value("платформа")
        if platform:
            compatibility += 0.3

        # Проверяем жанр
        genre = frame.get_slot_value("жанр")
        if genre:
            compatibility += 0.3

        # Проверяем длительность сессий
        session_length = frame.get_slot_value("длина_сессии")
        if session_length:
            compatibility += 0.2

        # Проверяем наличие онлайн
        has_online = frame.get_slot_value("требует_онлайн")
        if has_online is not None:
            compatibility += 0.2

        return compatibility

    def _get_recommendation_reason(self, frame) -> str:
        """IF-NEEDED: Формирует причину рекомендации игры"""
        reasons = []

        platform = frame.get_slot_value("платформа")
        if platform:
            reasons.append(f"Платформа: {platform}")

        genre = frame.get_slot_value("жанр")
        if genre:
            reasons.append(f"Жанр: {genre}")

        session_length = frame.get_slot_value("длина_сессии")
        if session_length:
            reasons.append(f"Длина сессий: {session_length}")

        online_req = frame.get_slot_value("требует_онлайн")
        if online_req:
            reasons.append("Требуется онлайн-доступ")
        elif online_req is False:
            reasons.append("Не требует онлайн-доступа")

        complexity = frame.get_slot_value("сложность")
        if complexity:
            reasons.append(f"Сложность: {complexity}")

        return "; ".join(reasons) if reasons else "Общая совместимость"

    def _determine_platform(self, frame) -> str:
        """IF-NEEDED: Определяет платформу на основе оборудования"""
        return "ПК"  # По умолчанию

    def _suggest_similar_games(self, frame) -> List[str]:
        """IF-NEEDED: Предлагает похожие игры"""
        game_name = frame.name
        similar_map = {
            "Counter-Strike": ["Valorant", "Rainbow Six Siege"],
            "Battlefield": ["Call of Duty", "Titanfall 2"],
            "The_Witcher": ["Skyrim", "Dragon Age"],
            "Skyrim": ["The Witcher", "Fallout 4"],
            "Final_Fantasy": ["Dragon Quest", "Persona 5"],
            "Civilization": ["Age of Empires", "Stellaris"],
            "XCOM": ["Phoenix Point", "Gears Tactics"],
            "Batman_Arkham": ["Spider-Man", "Middle-earth: Shadow of Mordor"],
            "Uncharted": ["Tomb Raider", "The Last of Us"],
            "The_Legend_of_Zelda": ["Okami", "Horizon Zero Dawn"],
            "God_of_War": ["Devil May Cry", "Bayonetta"],
            "Halo": ["Destiny", "Gears of War"],
            "Age_of_Empires": ["StarCraft", "Command & Conquer"]
        }
        return similar_map.get(game_name, [])

    def _validate_budget(self, frame, old_value, new_value):
        """IF-ADDED: Валидирует значение бюджета"""
        if new_value not in ["низкий", "средний", "высокий"]:
            raise ValueError(f"Недопустимое значение бюджета: {new_value}")

    def _update_genre_compatibility(self, frame, old_value, new_value):
        """IF-ADDED: Обновляет совместимость при изменении жанра"""
        print(f"Обновление совместимости для жанра: {new_value}")

    def _validate_session_length(self, frame, old_value, new_value):
        """IF-ADDED: Валидирует длину игровых сессий"""
        if new_value not in ["короткая", "длинная", "средняя"]:
            raise ValueError(f"Недопустимая длина сессии: {new_value}")

    def _parse_triggers(self, trigger_data: Dict[str, Any]) -> Dict[TriggerType, Callable]:
        """Парсит триггеры из JSON"""
        triggers = {}
        if not trigger_data:
            return triggers

        for trigger_str, proc_name in trigger_data.items():
            try:
                trigger_type = TriggerType(trigger_str)
                if proc_name in self._procedures:
                    triggers[trigger_type] = self._procedures[proc_name]
            except ValueError:
                continue  # Пропускаем неизвестные триггеры

        return triggers

    def _resolve_frame_reference(self, frame_objects: Dict[str, Frame], ref: Any) -> Any:
        """Разрешает ссылки на другие фреймы"""
        if isinstance(ref, str) and ref.startswith("!ref:"):
            frame_name = ref[5:]  # Убираем "!ref:"
            return frame_objects.get(frame_name)
        return ref

    def load_from_json(self, json_file: str):
        """Загружает фреймы из JSON файла"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Регистрируем процедуры
        self._register_procedures()

        # Создаем все фреймы
        frame_objects = {}
        for frame_data in data['frames']:
            name = frame_data['name']
            frame_objects[name] = Frame(name)

        # Устанавливаем слоты и AKO связи
        for frame_data in data['frames']:
            name = frame_data['name']
            frame = frame_objects[name]

            # Устанавливаем AKO
            if 'ako' in frame_data and frame_data['ako']:
                parent_name = frame_data['ako']
                if parent_name in frame_objects:
                    frame.set_ako(frame_objects[parent_name])

            # Устанавливаем слоты
            if 'slots' in frame_data:
                for slot_data in frame_data['slots']:
                    slot_name = slot_data['name']

                    # Определяем тип данных
                    data_type = DataType(slot_data.get('data_type', 'TEXT'))

                    # Определяем тип наследования
                    inheritance_str = slot_data.get('inheritance', 'O')
                    inheritance = InheritanceType(inheritance_str)

                    # Получаем значение (разрешаем ссылки на фреймы)
                    raw_value = slot_data.get('value')
                    value = self._resolve_frame_reference(frame_objects, raw_value)

                    # Получаем диапазон значений
                    range_values = slot_data.get('range', [])

                    # Парсим триггеры
                    triggers_data = slot_data.get('triggers', {})
                    triggers = self._parse_triggers(triggers_data)

                    # Создаем слот
                    slot = Slot(
                        name=slot_name,
                        value=value,
                        data_type=data_type,
                        inheritance=inheritance,
                        range_values=range_values,
                        triggers=triggers
                    )

                    frame.add_slot(slot)

        self.frames = frame_objects

    def get_frame(self, name: str) -> Optional[Frame]:
        """Возвращает фрейм по имени"""
        return self.frames.get(name)

    def get_all_frames(self) -> List[Frame]:
        """Возвращает все фреймы"""
        return list(self.frames.values())

    def get_game_frames(self) -> List[Frame]:
        """Возвращает только фреймы конкретных игр"""
        game_names = [
            "Counter-Strike", "Battlefield", "Halo", "God_of_War",
            "The_Witcher", "Skyrim", "Final_Fantasy", "Age_of_Empires",
            "Civilization", "XCOM", "Batman_Arkham", "Uncharted",
            "The_Legend_of_Zelda"
        ]
        return [self.frames[name] for name in game_names if name in self.frames]


# ============================================================================
# МОДУЛЬ 3: РАБОЧАЯ ПАМЯТЬ (working_memory.py)
# ============================================================================

@dataclass
class TraceEntry:
    """Запись в истории вывода"""
    action: str
    frame_name: str
    details: Dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """Рабочая память экспертной системы"""

    def __init__(self):
        self.user_preferences: Dict[str, Any] = {}
        self.proto_frames: List[Frame] = []  # Протофреймы пользователя
        self.exo_frames: List[Frame] = []  # Экзофреймы из БЗ
        self.trace: List[TraceEntry] = []  # История вывода

    def set_preferences(self, preferences: Dict[str, Any]):
        """Устанавливает предпочтения пользователя"""
        self.user_preferences = preferences
        self.add_trace("set_preferences", "System", {"preferences": preferences})

    def add_proto_frame(self, proto_frame: Frame):
        """Добавляет протофрейм"""
        self.proto_frames.append(proto_frame)
        self.add_trace("add_proto_frame", proto_frame.name, {})

    def add_exo_frame(self, exo_frame: Frame):
        """Добавляет экзофрейм"""
        self.exo_frames.append(exo_frame)

    def add_trace(self, action: str, frame_name: str, details: Dict[str, Any]):
        """Добавляет запись в историю вывода"""
        entry = TraceEntry(action, frame_name, details)
        self.trace.append(entry)

    def get_preferences(self) -> Dict[str, Any]:
        """Возвращает предпочтения пользователя"""
        return self.user_preferences

    def get_proto_frames(self) -> List[Frame]:
        """Возвращает протофреймы"""
        return self.proto_frames

    def get_exo_frames(self) -> List[Frame]:
        """Возвращает экзофреймы"""
        return self.exo_frames

    def get_trace(self) -> List[TraceEntry]:
        """Возвращает историю вывода"""
        return self.trace

    def clear(self):
        """Очищает рабочую память"""
        self.user_preferences = {}
        self.proto_frames = []
        self.exo_frames = []
        self.trace = []


# ============================================================================
# МОДУЛЬ 4: МЕХАНИЗМ ЛОГИЧЕСКОГО ВЫВОДА (inference_engine.py)
# ============================================================================

class InferenceEngine:
    """Механизм логического вывода для фреймовой системы"""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base
        self.working_memory = WorkingMemory()

    def reset(self):
        """Сбрасывает рабочую память"""
        self.working_memory.clear()

    def set_user_preferences(self, preferences: Dict[str, Any]):
        """Устанавливает предпочтения пользователя"""
        # Преобразуем ответы в формат для системы
        processed_preferences = {
            "имеет_ПК": preferences.get("имеет_ПК", "нет"),
            "имеет_Playstation": preferences.get("имеет_Playstation", "нет"),
            "имеет_Xbox": preferences.get("имеет_Xbox", "нет"),
            "нравятся_экшены": preferences.get("нравятся_экшены", "нет"),
            "нравятся_RPG": preferences.get("нравятся_RPG", "нет"),
            "нравятся_стратегии": preferences.get("нравятся_стратегии", "нет"),
            "нравятся_симуляторы": preferences.get("нравятся_симуляторы", "нет"),
            "нравятся_приключения": preferences.get("нравятся_приключения", "нет"),
            "имеет_онлайн": preferences.get("имеет_онлайн", "нет"),
            "короткие_сессии": preferences.get("короткие_сессии", "нет")
        }

        self.working_memory.set_preferences(processed_preferences)

    def frame_based_inference(self) -> List[Frame]:
        """Выполняет вывод на основе фреймов"""
        preferences = self.working_memory.get_preferences()
        game_frames = self.kb.get_game_frames()

        # Определяем платформу пользователя
        platform = self._determine_user_platform(preferences)

        # Определяем доступные жанры
        available_genres = self._determine_available_genres(preferences)

        # Создаем протофреймы и оцениваем совместимость
        matched_frames = []

        for game_frame in game_frames:
            # Создаем протофрейм
            proto_frame = game_frame.create_proto_frame()
            self.working_memory.add_proto_frame(proto_frame)
            self.working_memory.add_exo_frame(game_frame)

            # Устанавливаем платформу игры
            game_platform = game_frame.get_slot_value("платформа")
            if game_platform:
                proto_frame.set_slot_value("требуемая_платформа", game_platform)

            # Устанавливаем жанр игры
            game_genre = game_frame.get_slot_value("жанр")
            if game_genre:
                proto_frame.set_slot_value("требуемый_жанр", game_genre)

            # Устанавливаем требования к онлайн
            requires_online = game_frame.get_slot_value("требует_онлайн")
            if requires_online is not None:
                proto_frame.set_slot_value("требует_онлайн", requires_online)

            # Устанавливаем длину сессий
            session_length = game_frame.get_slot_value("длина_сессии")
            if session_length:
                proto_frame.set_slot_value("рекомендуемая_длина_сессии", session_length)

            # Устанавливаем сложность
            complexity = game_frame.get_slot_value("сложность")
            if complexity:
                proto_frame.set_slot_value("сложность", complexity)

            # Вычисляем совместимость
            compatibility = self._calculate_compatibility(
                proto_frame, platform, available_genres, preferences
            )

            if compatibility > 0.3:  # Порог совместимости
                proto_frame.set_slot_value("совместимость", compatibility)
                matched_frames.append(proto_frame)

                self.working_memory.add_trace(
                    "frame_match",
                    proto_frame.name,
                    {
                        "compatibility": compatibility,
                        "platform_match": game_platform == platform,
                        "genre_match": game_genre in available_genres
                    }
                )

        # Сортируем по совместимости
        matched_frames.sort(
            key=lambda f: f.get_slot_value("совместимость") or 0,
            reverse=True
        )

        return matched_frames

    def _determine_user_platform(self, preferences: Dict[str, Any]) -> str:
        """Определяет платформу пользователя"""
        if preferences.get("имеет_ПК") == "да":
            return "ПК"
        elif preferences.get("имеет_Playstation") == "да":
            return "Playstation"
        elif preferences.get("имеет_Xbox") == "да":
            return "Xbox"
        return "неизвестно"

    def _determine_available_genres(self, preferences: Dict[str, Any]) -> List[str]:
        """Определяет доступные жанры"""
        genres = []

        if preferences.get("нравятся_экшены") == "да":
            genres.append("экшен")

        if preferences.get("нравятся_RPG") == "да":
            genres.append("RPG")

        if preferences.get("нравятся_стратегии") == "да" or preferences.get("нравятся_симуляторы") == "да":
            genres.append("стратегия")

        if preferences.get("нравятся_приключения") == "да" and preferences.get("имеет_онлайн") == "да":
            genres.append("приключение")

        return genres

    def _calculate_compatibility(self, proto_frame: Frame, user_platform: str,
                                 available_genres: List[str], preferences: Dict[str, Any]) -> float:
        """Вычисляет совместимость игры с пользователем"""
        score = 0.0
        total_possible = 0.0

        # Проверка платформы (вес 0.35)
        required_platform = proto_frame.get_slot_value("требуемая_платформа")
        if required_platform:
            total_possible += 0.35
            if required_platform == user_platform or required_platform == "мультиплатформа":
                score += 0.35
            elif user_platform == "ПК" and required_platform in ["Playstation", "Xbox"]:
                score += 0.15  # Частичное совпадение

        # Проверка жанра (вес 0.35)
        required_genre = proto_frame.get_slot_value("требуемый_жанр")
        if required_genre:
            total_possible += 0.35
            if required_genre in available_genres:
                score += 0.35

        # Проверка онлайн-требований (вес 0.15)
        requires_online = proto_frame.get_slot_value("требует_онлайн")
        if requires_online is not None:
            total_possible += 0.15
            has_online = preferences.get("имеет_онлайн") == "да"
            if (requires_online and has_online) or (not requires_online and not has_online):
                score += 0.15
            elif not requires_online:  # Игра не требует онлайн, но у пользователя есть
                score += 0.1  # Частичное совпадение

        # Проверка длины сессий (вес 0.15)
        recommended_length = proto_frame.get_slot_value("рекомендуемая_длина_сессии")
        user_prefers_short = preferences.get("короткие_сессии") == "да"
        if recommended_length:
            total_possible += 0.15
            if (recommended_length == "короткая" and user_prefers_short) or \
                    (recommended_length == "длинная" and not user_prefers_short):
                score += 0.15
            else:
                score += 0.05  # Частичное совпадение

        return score / total_possible if total_possible > 0 else 0.0

    def get_best_recommendation(self) -> Optional[str]:
        """Возвращает лучшую рекомендацию"""
        proto_frames = self.working_memory.get_proto_frames()
        if not proto_frames:
            return None

        # Берем наиболее совместимый протофрейм
        best_proto = max(
            proto_frames,
            key=lambda f: f.get_slot_value("совместимость") or 0
        )

        # Получаем имя исходной игры
        ako_frame = best_proto.slots["AKO"].value
        if ako_frame:
            return ako_frame.name

        return None

    def get_all_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Возвращает все рекомендации с деталями"""
        proto_frames = self.working_memory.get_proto_frames()
        recommendations = []

        for proto in proto_frames[:limit]:
            compatibility = proto.get_slot_value("совместимость") or 0
            ako_frame = proto.slots["AKO"].value

            if ako_frame:
                recommendations.append({
                    "game": ako_frame.name,
                    "compatibility": compatibility,
                    "platform": proto.get_slot_value("требуемая_платформа"),
                    "genre": proto.get_slot_value("требуемый_жанр"),
                    "session_length": proto.get_slot_value("рекомендуемая_длина_сессии")
                })

        return recommendations


# ============================================================================
# МОДУЛЬ 5: КОМПОНЕНТА ОБЪЯСНЕНИЯ (explanation_component.py)
# ============================================================================

class ExplanationComponent:
    """Компонента объяснения для фреймовой системы"""

    def __init__(self, inference_engine: InferenceEngine):
        self.ie = inference_engine

    def explain_recommendation(self, game_name: str) -> str:
        """Объясняет, почему данная игра была рекомендована"""
        # Находим соответствующий протофрейм
        proto_frames = self.ie.working_memory.get_proto_frames()
        target_proto = None

        for proto in proto_frames:
            ako_frame = proto.slots["AKO"].value
            if ako_frame and ako_frame.name == game_name:
                target_proto = proto
                break

        if not target_proto:
            return f"Игра '{game_name}' не найдена среди рекомендаций"

        # Получаем сведения о совместимости
        compatibility = target_proto.get_slot_value("совместимость") or 0
        required_platform = target_proto.get_slot_value("требуемая_платформа") or "любая"
        required_genre = target_proto.get_slot_value("требуемый_жанр") or "любой"
        session_length = target_proto.get_slot_value("рекомендуемая_длина_сессии") or "любая"
        requires_online = target_proto.get_slot_value("требует_онлайн")

        # Формируем объяснение
        explanation = f"📊 ОБЪЯСНЕНИЕ РЕКОМЕНДАЦИИ ИГРЫ '{game_name}':\n"
        explanation += f"   Совместимость: {compatibility:.1%}\n\n"
        explanation += "🔍 КРИТЕРИИ СООТВЕТСТВИЯ:\n"

        preferences = self.ie.working_memory.get_preferences()

        # Проверка платформы
        user_platform = self.ie._determine_user_platform(preferences)
        platform_match = required_platform == user_platform or required_platform == "мультиплатформа"
        explanation += f"1. 🎮 Платформа: игра для '{required_platform}', у вас '{user_platform}'"
        explanation += f" {'✓' if platform_match else '✗'}\n"

        # Проверка жанра
        available_genres = self.ie._determine_available_genres(preferences)
        genre_match = required_genre in available_genres
        explanation += f"2. 🎭 Жанр: игра в жанре '{required_genre}', вам нравятся: {', '.join(available_genres) if available_genres else 'нет предпочтений'}"
        explanation += f" {'✓' if genre_match else '✗'}\n"

        # Проверка длины сессий
        user_prefers_short = preferences.get("короткие_сессии") == "да"
        session_match = (session_length == "короткая" and user_prefers_short) or \
                        (session_length == "длинная" and not user_prefers_short)
        explanation += f"3. ⏱️ Длина сессий: игра для '{session_length}' сессий, вы предпочитаете {'короткие' if user_prefers_short else 'длинные'}"
        explanation += f" {'✓' if session_match else '✗'}\n"

        # Проверка онлайн-требований
        if requires_online is not None:
            has_online = preferences.get("имеет_онлайн") == "да"
            online_match = (requires_online and has_online) or (not requires_online)
            explanation += f"4. 🌐 Онлайн: игра {'требует' if requires_online else 'не требует'} онлайн, у вас {'есть' if has_online else 'нет'} доступ"
            explanation += f" {'✓' if online_match else '✗'}\n"

        # Получаем причину через IF-NEEDED процедуру
        reason_slot = target_proto.get_slot("причина_рекомендации")
        if reason_slot:
            reason = target_proto.get_slot_value("причина_рекомендации")
            if reason:
                explanation += f"\n💡 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:\n   {reason}"

        # Похожие игры
        similar_games = self.ie.kb._suggest_similar_games(target_proto.slots["AKO"].value)
        if similar_games:
            explanation += f"\n🎯 ПОХОЖИЕ ИГРЫ:\n   {', '.join(similar_games)}"

        return explanation

    def explain_inference_process(self) -> str:
        """Объясняет процесс вывода согласно теории Минского"""
        explanation = "🧠 ПРОЦЕСС ВЫВОДА ПО ТЕОРИИ ФРЕЙМОВ МИНСКОГО:\n"
        explanation += "═" * 60 + "\n"

        trace = self.ie.working_memory.get_trace()

        if not trace:
            explanation += "Процесс вывода еще не выполнялся.\n"
            return explanation

        explanation += "1. 📥 АНАЛИЗ ВХОДНЫХ ДАННЫХ:\n"
        explanation += "   • Созданы пользовательские предпочтения\n"

        proto_count = len([entry for entry in trace if entry.action == "add_proto_frame"])
        explanation += f"\n2. 🏗️ СОЗДАНИЕ ПРОТОФРЕЙМОВ:\n"
        explanation += f"   • Создано {proto_count} протофреймов (незаполненные шаблоны)\n"

        explanation += "\n3. 🔗 СВЯЗЫВАНИЕ С ЭКЗОФРЕЙМАМИ:\n"
        explanation += "   • Установлены связи AKO от протофреймов к фреймам из БЗ\n"

        explanation += "\n4. 📝 ЗАПОЛНЕНИЕ СЛОТОВ:\n"
        explanation += "   • Заполнены слоты протофреймов на основе предпочтений\n"
        explanation += "   • Активированы IF-NEEDED процедуры для вычисления значений\n"

        frame_matches = [entry for entry in trace if entry.action == "frame_match"]
        explanation += f"\n5. 📊 ОЦЕНКА СОВМЕСТИМОСТИ:\n"
        explanation += f"   • Оценено {len(frame_matches)} совпадений с играми\n"

        explanation += "\n6. 🏆 ВЫБОР РЕКОМЕНДАЦИЙ:\n"
        explanation += "   • Отсортированы игры по уровню совместимости\n"
        explanation += "   • Выбраны наиболее подходящие варианты\n"

        return explanation

    def get_detailed_trace(self) -> str:
        """Возвращает детальную историю вывода"""
        trace = self.ie.working_memory.get_trace()

        if not trace:
            return "История вывода пуста."

        output = "📋 ДЕТАЛЬНАЯ ИСТОРИЯ ВЫВОДА:\n"
        output += "═" * 60 + "\n"

        for i, entry in enumerate(trace, 1):
            output += f"{i}. {entry.action.upper()}: {entry.frame_name}\n"
            if entry.details:
                for key, value in entry.details.items():
                    output += f"   • {key}: {value}\n"

        return output

    def explain_slot_inheritance(self, frame_name: str, slot_name: str) -> str:
        """Объясняет наследование значения слота"""
        # Находим фрейм
        frame = self.ie.kb.get_frame(frame_name)
        if not frame:
            return f"Фрейм '{frame_name}' не найден в базе знаний."

        # Получаем значение с объяснением пути наследования
        value = frame.get_slot_value(slot_name)

        explanation = f"🔗 НАСЛЕДОВАНИЕ ЗНАЧЕНИЯ ДЛЯ СЛОТА '{slot_name}' ВО ФРЕЙМЕ '{frame_name}':\n"

        # Проверяем локальное значение
        local_slot = frame.get_slot(slot_name)
        if local_slot and local_slot.value is not None:
            explanation += f"1. 📍 Локальное значение: {local_slot.value}\n"
            return explanation

        # Ищем значение в цепочке наследования
        current = frame
        level = 1
        inheritance_chain = []

        while current:
            ako = current.slots["AKO"].value
            if not ako:
                break

            parent_slot = ako.get_slot(slot_name)
            if parent_slot and parent_slot.get_value(ako) is not None:
                parent_value = parent_slot.get_value(ako)
                inheritance_chain.append((ako.name, parent_value))

            current = ako

        if inheritance_chain:
            explanation += "📍 Значение получено через наследование:\n"
            for i, (parent_name, parent_value) in enumerate(inheritance_chain, 1):
                explanation += f"   {i}. От '{parent_name}': {parent_value}\n"
            explanation += f"\n🎯 Финальное значение: {inheritance_chain[-1][1]}"
        else:
            explanation += "❌ Значение не найдено ни локально, ни через наследование.\n"

        return explanation

    def explain_frame_hierarchy(self, frame_name: str) -> str:
        """Объясняет иерархию наследования фрейма"""
        frame = self.ie.kb.get_frame(frame_name)
        if not frame:
            return f"Фрейм '{frame_name}' не найден в базе знаний."

        explanation = f"🌳 ИЕРАРХИЯ НАСЛЕДОВАНИЯ ФРЕЙМА '{frame_name}':\n"

        current = frame
        level = 0
        hierarchy = []

        while current:
            hierarchy.append((level, current.name))
            ako = current.slots["AKO"].value
            if not ako:
                break
            current = ako
            level += 1

        for level, name in hierarchy:
            indent = "  " * level
            explanation += f"{indent}• {name}\n"

        return explanation


# ============================================================================
# МОДУЛЬ 6: ОСНОВНОЙ МОДУЛЬ ЗАПУСКА (main.py)
# ============================================================================

import os


def create_json_knowledge_base(filename: str = "game_frames.json"):
    """Создает JSON файл с базой знаний фреймов"""
    knowledge_base = {
        "name": "Фреймовая база знаний видеоигр",
        "description": "База знаний для рекомендации видеоигр на основе теории фреймов Минского",
        "frames": [
            # ==================== АБСТРАКТНЫЕ ФРЕЙМЫ (уровень 1) ====================
            {
                "name": "Игра",
                "ako": None,
                "slots": [
                    {
                        "name": "название",
                        "data_type": "TEXT",
                        "inheritance": "U"
                    },
                    {
                        "name": "разработчик",
                        "data_type": "TEXT",
                        "inheritance": "O"
                    },
                    {
                        "name": "год_выпуска",
                        "data_type": "INTEGER",
                        "inheritance": "O"
                    }
                ]
            },

            # ==================== ТИПЫ ИГР ПО ПЛАТФОРМЕ (уровень 2) ====================
            {
                "name": "Игра_для_ПК",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "платформа",
                        "value": "ПК",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "range": ["ПК"]
                    },
                    {
                        "name": "требования_к_железу",
                        "data_type": "TEXT",
                        "inheritance": "O"
                    }
                ]
            },
            {
                "name": "Консольная_игра",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "платформа",
                        "data_type": "TEXT",
                        "inheritance": "O",
                        "range": ["Playstation", "Xbox", "мультиплатформа"]
                    }
                ]
            },

            # ==================== ТИПЫ ИГР ПО ЖАНРУ (уровень 2) ====================
            {
                "name": "Экшен",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "жанр",
                        "value": "экшен",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "темп",
                        "data_type": "TEXT",
                        "inheritance": "O",
                        "range": ["быстрый", "умеренный", "медленный"]
                    }
                ]
            },
            {
                "name": "RPG",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "жанр",
                        "value": "RPG",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "система_прокачки",
                        "data_type": "TEXT",
                        "inheritance": "O"
                    }
                ]
            },
            {
                "name": "Стратегия",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "жанр",
                        "value": "стратегия",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "тип_стратегии",
                        "data_type": "TEXT",
                        "inheritance": "O",
                        "range": ["пошаговая", "реального времени"]
                    }
                ]
            },
            {
                "name": "Приключение",
                "ako": "Игра",
                "slots": [
                    {
                        "name": "жанр",
                        "value": "приключение",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "сюжетная_направленность",
                        "data_type": "TEXT",
                        "inheritance": "O",
                        "range": ["линейная", "нелинейная", "открытый мир"]
                    }
                ]
            },

            # ==================== КОНКРЕТНЫЕ ИГРЫ (уровень 3) ====================
            # Экшены для ПК
            {
                "name": "Counter-Strike",
                "ako": "Экшен",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": True,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    },
                    {
                        "name": "сложность",
                        "value": "высокая",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "причина_рекомендации",
                        "data_type": "TEXT",
                        "inheritance": "O",
                        "triggers": {
                            "IF-NEEDED": "get_recommendation_reason"
                        }
                    }
                ]
            },
            {
                "name": "Battlefield",
                "ako": "Экшен",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "длинная",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": True,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    },
                    {
                        "name": "сложность",
                        "value": "средняя",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },

            # Экшены для консолей
            {
                "name": "Halo",
                "ako": "Экшен",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "Xbox",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": True,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "God_of_War",
                "ako": "Экшен",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "Playstation",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "длинная",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    }
                ]
            },

            # RPG
            {
                "name": "The_Witcher",
                "ako": "RPG",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    },
                    {
                        "name": "сложность",
                        "value": "средняя",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "Skyrim",
                "ako": "RPG",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "длинная",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    },
                    {
                        "name": "сложность",
                        "value": "низкая",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "Final_Fantasy",
                "ako": "RPG",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "мультиплатформа",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    }
                ]
            },

            # Стратегии
            {
                "name": "Age_of_Empires",
                "ako": "Стратегия",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "тип_стратегии",
                        "value": "реального времени",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "Civilization",
                "ako": "Стратегия",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "длинная",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "тип_стратегии",
                        "value": "пошаговая",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "XCOM",
                "ako": "Стратегия",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "мультиплатформа",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "тип_стратегии",
                        "value": "пошаговая",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },

            # Приключения
            {
                "name": "Batman_Arkham",
                "ako": "Приключение",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Игра_для_ПК",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "требует_онлайн",
                        "value": False,
                        "data_type": "BOOLEAN",
                        "inheritance": "S"
                    },
                    {
                        "name": "сюжетная_направленность",
                        "value": "открытый мир",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "Uncharted",
                "ako": "Приключение",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "Playstation",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "короткая",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "сюжетная_направленность",
                        "value": "линейная",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            },
            {
                "name": "The_Legend_of_Zelda",
                "ako": "Приключение",
                "slots": [
                    {
                        "name": "AKO",
                        "value": "!ref:Консольная_игра",
                        "data_type": "FRAME",
                        "inheritance": "S"
                    },
                    {
                        "name": "платформа",
                        "value": "мультиплатформа",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    },
                    {
                        "name": "длина_сессии",
                        "value": "длинная",
                        "data_type": "TEXT",
                        "inheritance": "S",
                        "triggers": {
                            "IF-ADDED": "validate_session_length"
                        }
                    },
                    {
                        "name": "сюжетная_направленность",
                        "value": "открытый мир",
                        "data_type": "TEXT",
                        "inheritance": "S"
                    }
                ]
            }
        ]
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

    print(f"✓ JSON файл базы знаний создан: {filename}")
    print(f"  Содержит {len(knowledge_base['frames'])} фреймов")


def get_user_input() -> Dict[str, str]:
    """Запрашивает у пользователя предпочтения"""
    print("\n" + "=" * 60)
    print("ВВОД ПРЕДПОЧТЕНИЙ ПОЛЬЗОВАТЕЛЯ")
    print("=" * 60)

    def ask_yes_no(question: str) -> str:
        while True:
            answer = input(f"{question} (да/нет): ").strip().lower()
            if answer in ['да', 'нет']:
                return answer
            print("Пожалуйста, введите 'да' или 'нет'.")

    preferences = {}

    print("\n1. 🎮 ИМЕЮЩЕЕСЯ ОБОРУДОВАНИЕ:")
    preferences["имеет_ПК"] = ask_yes_no("  • Есть ли у вас ПК?")
    preferences["имеет_Playstation"] = ask_yes_no("  • Есть ли у вас Playstation?")
    preferences["имеет_Xbox"] = ask_yes_no("  • Есть ли у вас Xbox?")

    print("\n2. 🎭 ПРЕДПОЧТЕНИЯ ПО ЖАНРАМ:")
    preferences["нравятся_экшены"] = ask_yes_no("  • Нравятся ли вам экшены?")
    preferences["нравятся_RPG"] = ask_yes_no("  • Нравятся ли вам RPG?")
    preferences["нравятся_стратегии"] = ask_yes_no("  • Нравятся ли вам стратегии?")
    preferences["нравятся_симуляторы"] = ask_yes_no("  • Нравятся ли вам симуляторы?")
    preferences["нравятся_приключения"] = ask_yes_no("  • Нравятся ли вам приключения?")

    print("\n3. 📶 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ:")
    preferences["имеет_онлайн"] = ask_yes_no("  • Есть ли у вас доступ к онлайн-играм?")
    preferences["короткие_сессии"] = ask_yes_no("  • Вы предпочитаете короткие игровые сессии?")

    return preferences


def display_welcome():
    """Отображает приветственное сообщение"""
    print("\n" + "=" * 60)
    print("🎮 ФРЕЙМОВАЯ ЭКСПЕРТНАЯ СИСТЕМА: РЕКОМЕНДАЦИЯ ВИДЕОИГР")
    print("📚 Основана на теории фреймов Марвина Минского")
    print("💾 База знаний хранится в формате JSON")
    print("=" * 60)
    print("\nСистема поможет подобрать идеальную игру на основе:")
    print("  • Вашего оборудования (ПК, Playstation, Xbox)")
    print("  • Предпочтений по жанрам")
    print("  • Доступа к онлайн-режиму")
    print("  • Предпочитаемой длины игровых сессий")


def main():
    """Основная функция запуска системы"""
    display_welcome()

    # Создаем файл с базой знаний, если его нет
    JSON_FILE = "game_frames.json"
    if not os.path.exists(JSON_FILE):
        print(f"\nСоздаю JSON файл с базой знаний: {JSON_FILE}")
        create_json_knowledge_base(JSON_FILE)

    try:
        # Создаем компоненты системы
        print("\nЗагрузка базы знаний из JSON...")
        kb = KnowledgeBase(JSON_FILE)
        ie = InferenceEngine(kb)
        ec = ExplanationComponent(ie)

        print(f"✓ Загружено {len(kb.get_all_frames())} фреймов из {JSON_FILE}")

    except FileNotFoundError:
        print(f"✗ Ошибка: Файл {JSON_FILE} не найден!")
        return
    except Exception as e:
        print(f"✗ Ошибка при загрузке базы знаний: {e}")
        return

    # Запрашиваем предпочтения пользователя
    user_preferences = get_user_input()

    print("\n" + "=" * 60)
    print("🔍 ВЫПОЛНЕНИЕ ЛОГИЧЕСКОГО ВЫВОДА")
    print("=" * 60)

    # Устанавливаем предпочтения и выполняем вывод
    ie.set_user_preferences(user_preferences)
    matched_frames = ie.frame_based_inference()

    # Выводим процесс вывода
    print("\n" + ec.explain_inference_process())

    # Выводим результаты
    if matched_frames:
        best_recommendation = ie.get_best_recommendation()
        all_recommendations = ie.get_all_recommendations(limit=5)

        print("\n" + "=" * 60)
        print("🏆 РЕКОМЕНДАЦИИ")
        print("=" * 60)

        print(f"\nНайдено {len(matched_frames)} подходящих игр:")
        for i, rec in enumerate(all_recommendations, 1):
            compatibility_str = f"{rec['compatibility']:.1%}".rjust(6)
            print(f"{i}. {rec['game'].ljust(20)} [совместимость: {compatibility_str}]")

        print(f"\n🎯 Лучшая рекомендация: {best_recommendation}")

        print("\n" + "=" * 60)
        print("📊 ОБЪЯСНЕНИЕ РЕКОМЕНДАЦИИ")
        print("=" * 60)

        detailed_explanation = ec.explain_recommendation(best_recommendation)
        print(f"\n{detailed_explanation}")

        # Дополнительные возможности объяснения
        print("\n" + "=" * 60)
        print("🔧 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ")
        print("=" * 60)

        while True:
            print("\nВыберите опцию:")
            print("1. 📋 Показать детальную историю вывода")
            print("2. 🔗 Объяснить наследование слота для конкретной игры")
            print("3. 🌳 Показать иерархию наследования фрейма")
            print("4. 🎮 Получить все рекомендации с деталями")
            print("5. 🚪 Выход")

            choice = input("\nВаш выбор (1-5): ").strip()

            if choice == "1":
                print("\n" + ec.get_detailed_trace())

            elif choice == "2":
                game_name = input("Введите название игры (например, Counter-Strike): ").strip()
                slot_name = input("Введите название слота (например, платформа): ").strip()
                explanation = ec.explain_slot_inheritance(game_name, slot_name)
                print(f"\n{explanation}")

            elif choice == "3":
                frame_name = input("Введите название фрейма (например, The_Witcher): ").strip()
                explanation = ec.explain_frame_hierarchy(frame_name)
                print(f"\n{explanation}")

            elif choice == "4":
                print("\n" + "=" * 60)
                print("📈 ВСЕ РЕКОМЕНДАЦИИ С ДЕТАЛЯМИ")
                print("=" * 60)
                for rec in all_recommendations:
                    print(f"\n🎮 {rec['game']}:")
                    print(f"   Совместимость: {rec['compatibility']:.1%}")
                    print(f"   Платформа: {rec['platform']}")
                    print(f"   Жанр: {rec['genre']}")
                    print(f"   Длина сессий: {rec['session_length']}")

            elif choice == "5":
                break

            else:
                print("Неверный выбор. Попробуйте снова.")

    else:
        print("\n⚠ Не удалось найти подходящие игры на основе ваших предпочтений.")
        print("Попробуйте изменить предпочтения (например, указать больше жанров).")

    print("\n" + "=" * 60)
    print("✅ РАБОТА СИСТЕМЫ ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    main()