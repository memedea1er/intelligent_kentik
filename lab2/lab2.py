#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ЭКСПЕРТНАЯ СИСТЕМА ДЛЯ РЕКОМЕНДАЦИИ ВИДЕОИГР
Оболочка с модульной архитектурой, включающая:
1. Базу знаний (хранится в формате JSON)
2. Механизм логического вывода с тремя стратегиями разрешения конфликтов
3. Компоненту объяснения
4. Рабочую память
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence
import sys


# ============================================================================
# МОДУЛЬ 1: РАБОЧАЯ ПАМЯТЬ
# ============================================================================

@dataclass(frozen=True)
class FactRecord:
    """Метаданные о факте в рабочей памяти."""
    fact: str
    source: str  # "user" или ID правила
    supports: List[str]  # Факты-предпосылки
    timestamp: int


class WorkingMemory:
    """Рабочая память, хранящая факты и их метаданные."""

    def __init__(self) -> None:
        self._facts: Dict[str, FactRecord] = {}
        self._counter: int = 0

    def add_fact(self, fact: str, source: str, supports: Optional[Sequence[str]] = None) -> bool:
        """
        Добавляет новый факт.

        Возвращает True, если факт был добавлен, False если уже присутствовал.
        """
        if fact in self._facts:
            return False

        self._counter += 1
        record = FactRecord(
            fact=fact,
            source=source,
            supports=list(supports or []),
            timestamp=self._counter
        )
        self._facts[fact] = record
        return True

    def has_fact(self, fact: str) -> bool:
        """Проверяет наличие факта."""
        return fact in self._facts

    def get_record(self, fact: str) -> FactRecord:
        """Возвращает метаданные факта."""
        return self._facts[fact]

    def facts(self) -> List[str]:
        """Возвращает список фактов в порядке добавления."""
        return [record.fact for record in sorted(
            self._facts.values(),
            key=lambda item: item.timestamp
        )]

    def items(self) -> List[FactRecord]:
        """Возвращает все записи в порядке добавления."""
        return list(sorted(
            self._facts.values(),
            key=lambda item: item.timestamp
        ))


# ============================================================================
# МОДУЛЬ 2: БАЗА ЗНАНИЙ
# ============================================================================

@dataclass(frozen=True)
class Rule:
    """Одно продукционное правило IF-THEN."""
    id: str
    conditions: Sequence[str]  # Предпосылки
    conclusion: str  # Заключение


class KnowledgeBase:
    """База знаний, содержащая набор продукционных правил."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        if not rules:
            raise ValueError("База знаний не может быть пустой.")
        self._rules: List[Rule] = list(rules)

    @property
    def rules(self) -> Sequence[Rule]:
        """Возвращает правила в исходном порядке."""
        return tuple(self._rules)

    @classmethod
    def from_json(cls, path: Path) -> "KnowledgeBase":
        """Загружает правила из JSON-файла."""
        if not path.exists():
            raise FileNotFoundError(f"Файл с правилами не найден: {path}")

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        raw_rules = data.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError("Некорректный формат: ожидается список 'rules'.")

        rules: List[Rule] = []
        for item in raw_rules:
            try:
                rule = Rule(
                    id=str(item["id"]),
                    conditions=tuple(item["conditions"]),
                    conclusion=str(item["conclusion"])
                )
            except (KeyError, TypeError) as error:
                raise ValueError(f"Ошибка парсинга правила: {item}") from error
            rules.append(rule)

        return cls(rules)


# ============================================================================
# МОДУЛЬ 3: МЕХАНИЗМ ЛОГИЧЕСКОГО ВЫВОДА
# ============================================================================

@dataclass
class AppliedRule:
    """Информация о сработавшем правиле."""
    rule: Rule
    iteration: int


class InferenceEngine:
    """Механизм прямого вывода с поддержкой стратегий разрешения конфликтов."""

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self._kb = knowledge_base

    def infer(self, working_memory: WorkingMemory, strategy: str = "order") -> List[AppliedRule]:
        """
        Выполняет прямой вывод до насыщения.

        Возвращает список сработавших правил в порядке применения.
        """
        applied: List[AppliedRule] = []
        iteration = 0

        while True:
            # Формируем конфликтное множество
            conflict_set = self._collect_conflict_set(working_memory)
            if not conflict_set:
                break

            # Разрешаем конфликт
            rule = self._resolve_conflict(conflict_set, strategy, working_memory)
            if rule is None:
                break

            # Применяем правило
            added = working_memory.add_fact(
                fact=rule.conclusion,
                source=rule.id,
                supports=list(rule.conditions)
            )

            if added:
                iteration += 1
                applied.append(AppliedRule(rule=rule, iteration=iteration))
            else:
                # Если факт уже был, исключаем правило из рассмотрения
                conflict_set.remove(rule)
                if not conflict_set:
                    break

        return applied

    def _collect_conflict_set(self, working_memory: WorkingMemory) -> List[Rule]:
        """Формирует конфликтное множество - правила, условия которых выполнены."""
        conflicts: List[Rule] = []

        for rule in self._kb.rules:
            # Пропускаем правило, если заключение уже есть
            if working_memory.has_fact(rule.conclusion):
                continue

            # Проверяем все условия
            if all(working_memory.has_fact(condition) for condition in rule.conditions):
                conflicts.append(rule)

        return conflicts

    def _resolve_conflict(self, conflicts: Sequence[Rule], strategy: str,
                          working_memory: WorkingMemory) -> Optional[Rule]:
        """
        Выбирает правило из конфликтного множества согласно стратегии.

        Поддерживаемые стратегии:
        - order: правила применяются в порядке объявления в БЗ
        - specificity: правило с наибольшим числом условий
        - recency: правило с наиболее "свежими" фактами в предпосылках
        """
        if not conflicts:
            return None

        strategy = strategy.lower()

        if strategy == "order":
            return conflicts[0]

        if strategy == "specificity":
            return max(conflicts, key=lambda rule: len(rule.conditions))

        if strategy == "recency":
            def recency_score(rule: Rule) -> int:
                timestamps = []
                for condition in rule.conditions:
                    record = working_memory.get_record(condition)
                    timestamps.append(record.timestamp)
                return min(timestamps) if timestamps else 0  # Более свежие = меньше timestamp

            return min(conflicts, key=recency_score)

        raise ValueError(f"Неизвестная стратегия разрешения конфликтов: {strategy}")


# ============================================================================
# МОДУЛЬ 4: КОМПОНЕНТА ОБЪЯСНЕНИЯ
# ============================================================================

class ExplanationComponent:
    """Формирует объяснения выводов на основе цепочек вывода."""

    def __init__(self, working_memory: WorkingMemory) -> None:
        self._wm = working_memory

    def explain(self, fact: str) -> str:
        """Возвращает текстовое объяснение происхождения факта."""
        if not self._wm.has_fact(fact):
            raise ValueError(f"Факт '{fact}' отсутствует в рабочей памяти.")

        lines: List[str] = []
        self._build_explanation(fact, lines, depth=0)
        return "\n".join(lines)

    def _build_explanation(self, fact: str, lines: List[str], depth: int) -> None:
        """Рекурсивно строит цепочку вывода."""
        record = self._wm.get_record(fact)
        indent = "  " * depth

        if record.source == "user":
            lines.append(f"{indent}- Факт '{fact}' введён пользователем.")
            return

        lines.append(f"{indent}- Факт '{fact}' получен по правилу {record.source}.")

        if not record.supports:
            return

        lines.append(f"{indent}  Обоснование:")
        for support in record.supports:
            self._build_explanation(support, lines, depth + 2)


# ============================================================================
# МОДУЛЬ 5: ОБОЛОЧКА (CLI ИНТЕРФЕЙС)
# ============================================================================

class GameExpertSystemShell:
    """CLI-оболочка экспертной системы для рекомендации видеоигр."""

    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.kb = None
        self.wm = None
        self.explainer = None

    def load_knowledge_base(self) -> None:
        """Загружает базу знаний из JSON файла."""
        try:
            self.kb = KnowledgeBase.from_json(self.rules_path)
            print(f"✓ База знаний загружена: {len(self.kb.rules)} правил")
        except Exception as e:
            print(f"✗ Ошибка загрузки базы знаний: {e}")
            sys.exit(1)

    def ask_yes_no(self, prompt: str) -> bool:
        """Запрашивает ответ да/нет."""
        while True:
            answer = input(f"{prompt} (да/нет): ").strip().lower()
            if answer in {"да", "д", "yes", "y"}:
                return True
            if answer in {"нет", "н", "no", "n"}:
                return False
            print("Пожалуйста, введите 'да' или 'нет'.")

    def collect_initial_facts(self) -> None:
        """Собирает исходные факты от пользователя."""
        print("\n" + "=" * 50)
        print("ОПРОС ПОЛЬЗОВАТЕЛЯ")
        print("=" * 50)

        # Платформы
        has_pc = self.ask_yes_no("Есть ли у вас ПК?")
        has_ps = self.ask_yes_no("Есть ли у вас Playstation?")
        has_xbox = self.ask_yes_no("Есть ли у вас Xbox?")

        if has_pc:
            self.wm.add_fact("Есть ПК = да", "user")
        else:
            self.wm.add_fact("Есть ПК = нет", "user")

        if has_ps:
            self.wm.add_fact("Есть Playstation = да", "user")
        else:
            self.wm.add_fact("Есть Playstation = нет", "user")

        if has_xbox:
            self.wm.add_fact("Есть Xbox = да", "user")
        else:
            self.wm.add_fact("Есть Xbox = нет", "user")

        # Жанровые предпочтения
        genres = [
            ("Нравятся ли вам экшены?", "Нравятся экшены"),
            ("Нравятся ли вам RPG?", "Нравятся RPG"),
            ("Нравятся ли вам стратегии?", "Нравятся стратегии"),
            ("Нравятся ли вам симуляторы?", "Нравятся симуляторы"),
            ("Нравятся ли вам приключения?", "Нравятся приключения")
        ]

        for question, fact_name in genres:
            if self.ask_yes_no(question):
                self.wm.add_fact(f"{fact_name} = да", "user")
            else:
                self.wm.add_fact(f"{fact_name} = нет", "user")

        # Дополнительные условия
        if self.ask_yes_no("Есть ли у вас доступ к онлайн-режиму?"):
            self.wm.add_fact("Есть онлайн = да", "user")
        else:
            self.wm.add_fact("Есть онлайн = нет", "user")

        if self.ask_yes_no("Вы предпочитаете короткие игровые сессии?"):
            self.wm.add_fact("Короткие сессии = да", "user")
        else:
            self.wm.add_fact("Короткие сессии = нет", "user")

    def choose_strategy(self) -> str:
        """Предлагает выбрать стратегию разрешения конфликтов."""
        strategies = {
            "1": ("order", "По порядку правил"),
            "2": ("specificity", "По специфичности (больше условий)"),
            "3": ("recency", "По недавности фактов")
        }

        print("\n" + "=" * 50)
        print("СТРАТЕГИЯ РАЗРЕШЕНИЯ КОНФЛИКТОВ")
        print("=" * 50)
        print("Выберите стратегию:")
        for key, (_, description) in strategies.items():
            print(f"  {key}. {description}")

        while True:
            choice = input("Ваш выбор [1-3]: ").strip()
            if choice in strategies:
                return strategies[choice][0]
            print("Недопустимый выбор. Попробуйте снова.")

    def print_results(self) -> None:
        """Выводит результаты работы системы."""
        print("\n" + "=" * 50)
        print("РЕЗУЛЬТАТЫ")
        print("=" * 50)

        print("\nВсе полученные факты:")
        for record in self.wm.items():
            source = "пользователь" if record.source == "user" else f"правило {record.source}"
            print(f"  • {record.fact} (источник: {source})")

        # Ищем рекомендации
        recommendations = [fact for fact in self.wm.facts()
                           if fact.startswith("Рекомендуемая игра = ")]

        if recommendations:
            print("\n" + "=" * 50)
            print("ИТОГОВЫЕ РЕКОМЕНДАЦИИ")
            print("=" * 50)
            for rec in recommendations:
                print(f"  ★ {rec}")
        else:
            print("\n⚠ Рекомендаций получить не удалось.")

    def explanation_loop(self) -> None:
        """Цикл запросов объяснений."""
        print("\n" + "=" * 50)
        print("КОМПОНЕНТА ОБЪЯСНЕНИЯ")
        print("=" * 50)
        print("Введите интересующий факт для объяснения (пустая строка - выход).")

        while True:
            fact = input("\nФакт для объяснения: ").strip()
            if not fact:
                break

            try:
                print("\nОбъяснение:")
                print("-" * 30)
                print(self.explainer.explain(fact))
            except ValueError as e:
                print(f"Ошибка: {e}")

    def run(self) -> None:
        """Основной цикл работы системы."""
        print("\n" + "=" * 50)
        print("ЭКСПЕРТНАЯ СИСТЕМА: РЕКОМЕНДАЦИЯ ВИДЕОИГР")
        print("=" * 50)

        # Загрузка БЗ
        self.load_knowledge_base()

        # Инициализация
        self.wm = WorkingMemory()
        self.explainer = ExplanationComponent(self.wm)

        # Сбор данных
        self.collect_initial_facts()

        # Выбор стратегии
        strategy = self.choose_strategy()

        # Логический вывод
        print("\n" + "=" * 50)
        print("ЛОГИЧЕСКИЙ ВЫВОД")
        print("=" * 50)

        engine = InferenceEngine(self.kb)
        applied_rules = engine.infer(self.wm, strategy=strategy)

        if applied_rules:
            print(f"\nСработало {len(applied_rules)} правил:")
            for applied in applied_rules:
                print(f"  {applied.iteration}. {applied.rule.id} → {applied.rule.conclusion}")
        else:
            print("\nНи одно правило не сработало.")

        # Результаты
        self.print_results()

        # Объяснения
        self.explanation_loop()

        print("\n" + "=" * 50)
        print("РАБОТА СИСТЕМЫ ЗАВЕРШЕНА")
        print("=" * 50)


# ============================================================================
# СОЗДАНИЕ ФАЙЛА С БАЗОЙ ЗНАНИЙ (JSON)
# ============================================================================

def create_knowledge_base_file(filename: str = "game_rules.json") -> None:
    """Создает JSON файл с базой знаний для системы рекомендации игр."""

    rules = [
        # =============== ПРАВИЛА ОПРЕДЕЛЕНИЯ ПЛАТФОРМЫ ===============
        {
            "id": "P1",
            "conditions": ["Есть ПК = да"],
            "conclusion": "Платформа = ПК"
        },
        {
            "id": "P2",
            "conditions": ["Есть Playstation = да"],
            "conclusion": "Платформа = консоль"
        },
        {
            "id": "P3",
            "conditions": ["Есть Xbox = да"],
            "conclusion": "Платформа = консоль"
        },
        {
            "id": "P4",
            "conditions": ["Есть ПК = нет", "Есть Playstation = нет", "Есть Xbox = нет"],
            "conclusion": "Нет платформы = да"
        },

        # ============ ПРАВИЛА ОПРЕДЕЛЕНИЯ ДОСТУПНЫХ ЖАНРОВ ============
        {
            "id": "G1",
            "conditions": ["Нравятся экшены = да"],
            "conclusion": "Экшены доступны = да"
        },
        {
            "id": "G2",
            "conditions": ["Нравятся RPG = да"],
            "conclusion": "RPG доступны = да"
        },
        {
            "id": "G3",
            "conditions": ["Нравятся стратегии = да"],
            "conclusion": "Стратегии доступны = да"
        },
        {
            "id": "G4",
            "conditions": ["Нравятся симуляторы = да"],
            "conclusion": "Стратегии доступны = да"
        },
        {
            "id": "G5",
            "conditions": ["Нравятся приключения = да", "Есть онлайн = да"],
            "conclusion": "Приключения доступны = да"
        },

        # ========== ПРАВИЛА КОМБИНАЦИИ ПЛАТФОРМЫ И ЖАНРОВ ============
        {
            "id": "C1",
            "conditions": ["Платформа = ПК", "Экшены доступны = да"],
            "conclusion": "Экшены для ПК = да"
        },
        {
            "id": "C2",
            "conditions": ["Платформа = консоль", "Экшены доступны = да"],
            "conclusion": "Экшены для консолей = да"
        },
        {
            "id": "C3",
            "conditions": ["Платформа = ПК", "RPG доступны = да"],
            "conclusion": "RPG для ПК = да"
        },
        {
            "id": "C4",
            "conditions": ["Платформа = консоль", "RPG доступны = да"],
            "conclusion": "RPG для консолей = да"
        },
        {
            "id": "C5",
            "conditions": ["Платформа = ПК", "Стратегии доступны = да"],
            "conclusion": "Стратегии для ПК = да"
        },
        {
            "id": "C6",
            "conditions": ["Платформа = консоль", "Стратегии доступны = да"],
            "conclusion": "Стратегии для консолей = да"
        },
        {
            "id": "C7",
            "conditions": ["Платформа = ПК", "Приключения доступны = да"],
            "conclusion": "Приключения для ПК = да"
        },
        {
            "id": "C8",
            "conditions": ["Платформа = консоль", "Приключения доступны = да"],
            "conclusion": "Приключения для консолей = да"
        },

        # ================== ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ ===================
        # Экшены
        {
            "id": "F1",
            "conditions": ["Экшены для ПК = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Counter-Strike"
        },
        {
            "id": "F2",
            "conditions": ["Экшены для ПК = да", "Короткие сессии = нет"],
            "conclusion": "Рекомендуемая игра = Battlefield"
        },
        {
            "id": "F3",
            "conditions": ["Экшены для консолей = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Halo"
        },
        {
            "id": "F4",
            "conditions": ["Экшены для консолей = да", "Короткие сессии = нет"],
            "conclusion": "Рекомендуемая игра = God of War"
        },

        # RPG
        {
            "id": "F5",
            "conditions": ["RPG для ПК = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = The Witcher"
        },
        {
            "id": "F6",
            "conditions": ["RPG для ПК = да", "Короткие сессии = нет"],
            "conclusion": "Рекомендуемая игра = Skyrim"
        },
        {
            "id": "F7",
            "conditions": ["RPG для консолей = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Final Fantasy"
        },

        # Стратегии
        {
            "id": "F8",
            "conditions": ["Стратегии для ПК = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Age of Empires"
        },
        {
            "id": "F9",
            "conditions": ["Стратегии для ПК = да", "Короткие сессии = нет"],
            "conclusion": "Рекомендуемая игра = Civilization"
        },
        {
            "id": "F10",
            "conditions": ["Стратегии для консолей = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = XCOM"
        },

        # Приключения
        {
            "id": "F11",
            "conditions": ["Приключения для ПК = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Batman: Arkham"
        },
        {
            "id": "F12",
            "conditions": ["Приключения для консолей = да", "Короткие сессии = да"],
            "conclusion": "Рекомендуемая игра = Uncharted"
        },
        {
            "id": "F13",
            "conditions": ["Приключения для консолей = да", "Короткие сессии = нет"],
            "conclusion": "Рекомендуемая игра = The Legend of Zelda"
        },

        # ================== ОСОБЫЕ СЛУЧАИ ===================
        {
            "id": "S1",
            "conditions": ["Нет платформы = да"],
            "conclusion": "Рекомендуемая игра = Нет рекомендации"
        }
    ]

    knowledge_base = {
        "name": "Система рекомендации видеоигр",
        "description": "База знаний для экспертной системы рекомендации игр по платформе и жанрам",
        "rules": rules
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, ensure_ascii=False, indent=2)

    print(f"✓ Файл базы знаний создан: {filename}")
    print(f"  Содержит {len(rules)} правил")


# ============================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    """Точка входа в программу."""
    import os

    RULES_FILE = "game_rules.json"

    # Создаем файл с базой знаний, если его нет
    if not os.path.exists(RULES_FILE):
        print("Создаю файл с базой знаний...")
        create_knowledge_base_file(RULES_FILE)

    # Запускаем систему
    try:
        shell = GameExpertSystemShell(Path(RULES_FILE))
        shell.run()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()