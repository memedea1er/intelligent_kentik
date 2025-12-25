# main.py
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
from itertools import combinations
import os

app = FastAPI(
    title="Экспертная система коллективных решений",
    description="Система для анализа коллективных решений с различными методами голосования",
    version="1.0.0"
)

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Модели данных
class VotingProfile(BaseModel):
    alternatives: List[str] = Field(..., min_length=2, description="Варианты голосования")
    voters: List[str] = Field(..., min_length=1, description="Имена избирателей")
    rankings: Dict[str, List[str]] = Field(..., description="Ранжирования по избирателям")


class VotingResult(BaseModel):
    method: str
    winner: str
    scores: Dict[str, float]
    details: Optional[str] = None


class AllResults(BaseModel):
    profile: VotingProfile
    results: List[VotingResult]
    has_condorcet_winner: bool


# Вспомогательные функции для методов голосования
def pairwise_comparison(profile: List[List[str]], a: str, b: str) -> int:
    """Возвращает разность: сколько предпочитают a над b минус наоборот."""
    score = 0
    for ranking in profile:
        if a in ranking and b in ranking:
            if ranking.index(a) < ranking.index(b):
                score += 1
            else:
                score -= 1
    return score


class VotingMethods:
    """Класс для различных методов голосования."""

    @staticmethod
    def relative_majority(profile: List[List[str]], alternatives: List[str]) -> Tuple[str, Dict[str, int]]:
        """Относительное большинство: побеждает тот, кто чаще стоит на 1-м месте."""
        first_choices = [ranking[0] for ranking in profile]
        counts = Counter(first_choices)
        winner = max(counts, key=counts.get)
        return winner, dict(counts)

    @staticmethod
    def condorcet_winner(profile: List[List[str]], alternatives: List[str]) -> Optional[str]:
        """Явный победитель Кондорсе: побеждает всех в попарных сравнениях."""
        for a in alternatives:
            if all(pairwise_comparison(profile, a, b) > 0
                   for b in alternatives if a != b):
                return a
        return None

    @staticmethod
    def copeland_score(profile: List[List[str]], alternatives: List[str]) -> Dict[str, int]:
        """Правило Копленда: +1 за победу, -1 за поражение, 0 за ничью."""
        scores = {a: 0 for a in alternatives}
        for a, b in combinations(alternatives, 2):
            diff = pairwise_comparison(profile, a, b)
            if diff > 0:
                scores[a] += 1
                scores[b] -= 1
            elif diff < 0:
                scores[a] -= 1
                scores[b] += 1
        return scores

    @staticmethod
    def simpson_score(profile: List[List[str]], alternatives: List[str]) -> Dict[str, int]:
        """Правило Симпсона: минимальное число голосов, с которым кандидат побеждает любого другого."""
        scores = {}
        for a in alternatives:
            min_wins = float('inf')
            for b in alternatives:
                if a == b:
                    continue
                wins = sum(1 for ranking in profile
                           if ranking.index(a) < ranking.index(b))
                min_wins = min(min_wins, wins)
            scores[a] = min_wins
        return scores

    @staticmethod
    def borda_count(profile: List[List[str]], alternatives: List[str]) -> Dict[str, int]:
        """Модель Борда: p-1 очков за 1-е место, ..., 0 за последнее."""
        p = len(alternatives)
        scores = defaultdict(int)
        for ranking in profile:
            for i, alt in enumerate(ranking):
                scores[alt] += (p - 1 - i)
        # Убедимся, что все альтернативы присутствуют
        for alt in alternatives:
            scores.setdefault(alt, 0)
        return dict(scores)


# Анализ профиля голосования
def analyze_voting_profile(profile: VotingProfile) -> AllResults:
    """Анализирует профиль голосования всеми методами."""
    # Подготовка данных
    alternatives = profile.alternatives
    rankings_list = [profile.rankings[voter] for voter in profile.voters]

    voting = VotingMethods()
    results = []

    # 1. Относительное большинство
    maj_winner, maj_counts = voting.relative_majority(rankings_list, alternatives)
    results.append(VotingResult(
        method="Относительное большинство",
        winner=maj_winner,
        scores=maj_counts,
        details="Победитель определяется по наибольшему количеству первых мест"
    ))

    # 2. Победитель Кондорсе
    cond_winner = voting.condorcet_winner(rankings_list, alternatives)
    cond_scores = {}
    if cond_winner:
        for alt in alternatives:
            wins = sum(1 for other in alternatives
                       if other != alt and
                       pairwise_comparison(rankings_list, alt, other) > 0)
            cond_scores[alt] = wins

    results.append(VotingResult(
        method="Победитель Кондорсе",
        winner=cond_winner if cond_winner else "Не найден",
        scores=cond_scores if cond_winner else {},
        details="Победитель Кондорсе — кандидат, который побеждает всех остальных в попарных сравнениях"
    ))

    # 3. Правило Копленда
    cop_scores = voting.copeland_score(rankings_list, alternatives)
    cop_winner = max(cop_scores, key=cop_scores.get)
    results.append(VotingResult(
        method="Правило Копленда",
        winner=cop_winner,
        scores=cop_scores,
        details="+1 за каждую победу, -1 за каждое поражение в попарных сравнениях"
    ))

    # 4. Правило Симпсона
    sim_scores = voting.simpson_score(rankings_list, alternatives)
    sim_winner = max(sim_scores, key=sim_scores.get)
    results.append(VotingResult(
        method="Правило Симпсона",
        winner=sim_winner,
        scores=sim_scores,
        details="Минимальное число голосов, с которым кандидат побеждает любого другого"
    ))

    # 5. Модель Борда
    bor_scores = voting.borda_count(rankings_list, alternatives)
    bor_winner = max(bor_scores, key=bor_scores.get)
    results.append(VotingResult(
        method="Модель Борда",
        winner=bor_winner,
        scores=bor_scores,
        details="p-1 очков за 1-е место, p-2 за 2-е, ..., 0 за последнее"
    ))

    return AllResults(
        profile=profile,
        results=results,
        has_condorcet_winner=cond_winner is not None
    )


# Маршруты API
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/methods")
async def get_voting_methods():
    """Возвращает список доступных методов голосования."""
    methods = [
        {
            "id": "relative_majority",
            "name": "Относительное большинство",
            "description": "Побеждает кандидат с наибольшим количеством первых мест"
        },
        {
            "id": "condorcet",
            "name": "Победитель Кондорсе",
            "description": "Кандидат, побеждающий всех остальных в попарных сравнениях"
        },
        {
            "id": "copeland",
            "name": "Правило Копленда",
            "description": "+1 за победу, -1 за поражение в попарных сравнениях"
        },
        {
            "id": "simpson",
            "name": "Правило Симпсона",
            "description": "Минимальное число голосов против самого сильного соперника"
        },
        {
            "id": "borda",
            "name": "Модель Борда",
            "description": "Взвешенные очки за позиции в рейтинге"
        }
    ]
    return JSONResponse(content={"methods": methods})


@app.post("/api/analyze")
async def analyze_profile(profile: VotingProfile):
    """Анализирует профиль голосования всеми методами."""
    try:
        # Проверка валидности данных
        if len(profile.alternatives) != len(set(profile.alternatives)):
            return JSONResponse(
                status_code=400,
                content={"error": "Альтернативы должны быть уникальными"}
            )

        if len(profile.voters) != len(set(profile.voters)):
            return JSONResponse(
                status_code=400,
                content={"error": "Имена избирателей должны быть уникальными"}
            )

        for voter, ranking in profile.rankings.items():
            if voter not in profile.voters:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Избиратель {voter} не найден в списке избирателей"}
                )

            if set(ranking) != set(profile.alternatives):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Ранжирование для {voter} содержит не все альтернативы"}
                )

        results = analyze_voting_profile(profile)
        return JSONResponse(content=results.dict())

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Ошибка при анализе: {str(e)}"}
        )


@app.get("/api/example")
async def get_example_profile():
    """Возвращает пример профиля для тестирования."""
    example_profile = {
        "alternatives": ["A", "B", "C", "D"],
        "voters": ["Иван", "Мария", "Петр", "Анна", "Сергей"],
        "rankings": {
            "Иван": ["A", "B", "C", "D"],
            "Мария": ["B", "C", "D", "A"],
            "Петр": ["C", "D", "A", "B"],
            "Анна": ["D", "A", "B", "C"],
            "Сергей": ["A", "C", "B", "D"]
        }
    }
    return JSONResponse(content=example_profile)


@app.get("/about")
async def about_page(request: Request):
    """Страница с информацией о системе."""
    return templates.TemplateResponse("about.html", {"request": request})