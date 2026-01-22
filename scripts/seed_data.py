#!/usr/bin/env python3
"""
Seed script to populate database with real tasks from Obsidian vault.
"""

import requests

API_URL = "http://localhost:8000"
API_KEY = "dev-api-key-change-in-production"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Projects based on vault structure
PROJECTS = [
    {"name": "Здоровье", "description": "Медицинские задачи и врачи", "color": "#EF4444"},
    {"name": "Семья", "description": "Семейные задачи, авто, покупки", "color": "#EC4899"},
    {"name": "Крипто", "description": "Криптовалюты, портфель, анализ", "color": "#F59E0B"},
    {
        "name": "Оплата простоев",
        "description": "Рабочий проект по оплате простоев подрядчиков",
        "color": "#3B82F6",
    },
    {"name": "УТЭЦ-2", "description": "Управляющий комитет, коллизии, аудит", "color": "#6366F1"},
    {"name": "Столовая КХП", "description": "Проект столовой КХП НЛМК", "color": "#8B5CF6"},
    {
        "name": "AI Safety NLMK",
        "description": "Памятка по безопасности AI для НЛМК",
        "color": "#10B981",
    },
    {
        "name": "Вайб-Кодинг",
        "description": "Курс программирования: FastAPI, React",
        "color": "#14B8A6",
    },
    {"name": "Обучение", "description": "AI курсы, книги, статьи", "color": "#06B6D4"},
    {"name": "Тренировки", "description": "Зал, сквош, падел", "color": "#22C55E"},
    {"name": "Творчество", "description": "Гитара, музыка", "color": "#A855F7"},
    {"name": "Работа: Разное", "description": "Прочие рабочие задачи", "color": "#64748B"},
]

# Tasks from TODO file
TASKS = {
    "Здоровье": [
        {
            "title": "Дождаться ответа от страховой по обследованию",
            "priority": "high",
            "due_date": "2026-01-25",
            "tags": ["health", "urgent"],
        },
        {
            "title": "Лечь на обследование (1-2 дня)",
            "priority": "high",
            "due_date": "2026-02-05",
            "tags": ["health", "urgent"],
        },
        {
            "title": "Записаться к нефрологу",
            "priority": "medium",
            "due_date": "2026-02-10",
            "tags": ["health"],
        },
        {
            "title": "Записаться к урологу",
            "priority": "medium",
            "due_date": "2026-02-10",
            "tags": ["health"],
        },
    ],
    "Семья": [
        {
            "title": "Продлить интернет в машине Крис (Мегафон Li-9)",
            "priority": "medium",
            "due_date": "2026-02-22",
            "description": "Пополнить: +79254825804",
            "tags": ["family", "auto"],
        },
        {
            "title": "Сделать семейный доступ к мастер-аккаунту Li-9",
            "priority": "medium",
            "due_date": "2026-02-05",
            "tags": ["family", "tech"],
        },
        {
            "title": "Записать Li-9 на ТО",
            "priority": "medium",
            "due_date": "2026-01-26",
            "description": "Эта неделя (кроме четверга) или следующая (пн/пт)",
            "tags": ["family", "auto"],
        },
        {
            "title": "Узнать про ТО на Zeekr — можно там же пройти?",
            "priority": "medium",
            "due_date": "2026-01-26",
            "tags": ["family", "auto"],
        },
        {
            "title": "Выбрать мотолопату (обзор был, ещё посмотреть Makita)",
            "priority": "medium",
            "due_date": "2026-01-26",
            "tags": ["family", "purchase"],
        },
    ],
    "Крипто": [
        {
            "title": "27 января - Отследить энэктмент Polkadot Hub Revive",
            "priority": "high",
            "due_date": "2026-01-27",
            "tags": ["crypto", "critical"],
        },
        {
            "title": "14 марта - Мониторинг запуска Hard Pressure (ограничение эмиссии DOT)",
            "priority": "medium",
            "due_date": "2026-03-14",
            "tags": ["crypto", "finance"],
        },
        {
            "title": "Изучить анализ криптопортфеля Gemini Deep Research",
            "priority": "medium",
            "due_date": "2026-01-26",
            "tags": ["crypto", "finance"],
        },
        {
            "title": "Определить целевой портфель крипты",
            "priority": "medium",
            "due_date": "2026-01-24",
            "tags": ["crypto", "finance"],
        },
        {
            "title": "Подготовить план ребалансировки",
            "priority": "medium",
            "due_date": "2026-01-26",
            "tags": ["crypto", "finance"],
        },
    ],
    "Оплата простоев": [
        {
            "title": "Пт: Встреча Zoom - анализ всех комментариев + план доработки",
            "priority": "high",
            "due_date": "2026-01-24",
            "tags": ["work", "deadline", "meeting"],
        },
    ],
    "Столовая КХП": [
        {
            "title": "Контроль: Согласование заявки в УЗРИД (Хрюкин)",
            "priority": "medium",
            "due_date": "2026-01-28",
            "tags": ["work", "khp", "control"],
        },
        {
            "title": "Контроль: Обратная засыпка котлованов песком (Власов)",
            "priority": "medium",
            "due_date": "2026-01-30",
            "tags": ["work", "khp", "control"],
        },
        {
            "title": "Контроль: Согласование смет Палантира — 17 из 23 (Власов)",
            "priority": "medium",
            "due_date": "2026-01-30",
            "tags": ["work", "khp", "control"],
        },
        {
            "title": "Контроль: Дорожная карта модели объектов питания (Ласкин)",
            "priority": "medium",
            "due_date": "2026-01-30",
            "tags": ["work", "khp", "control"],
        },
        {
            "title": "Контроль: Запрос на смещение сроков ТИС при необходимости (Ласкин)",
            "priority": "medium",
            "due_date": "2026-02-15",
            "tags": ["work", "khp", "control"],
        },
    ],
    "AI Safety NLMK": [
        {
            "title": "Проконтролировать ответ от сотрудников по AI Safety (письмо 21.01)",
            "priority": "medium",
            "due_date": "2026-01-24",
            "tags": ["work", "ai-safety", "control"],
        },
    ],
    "Вайб-Кодинг": [
        {
            "title": "Продолжить курс Вайб-Кодинг (Неделя 7)",
            "priority": "medium",
            "due_date": "2026-01-27",
            "tags": ["learning", "vibe-coding"],
        },
    ],
    "Обучение": [
        {
            "title": "Начать курс Understanding Agentic AI (1-2 часа)",
            "priority": "medium",
            "due_date": "2026-01-26",
            "tags": ["learning", "ai-agents"],
        },
    ],
    "Тренировки": [
        {
            "title": "Сквош - 1-2 часа",
            "priority": "low",
            "due_date": "2026-01-23",
            "tags": ["fitness", "squash"],
        },
        {
            "title": "Падел",
            "priority": "low",
            "due_date": "2026-01-26",
            "tags": ["fitness", "padel"],
        },
    ],
    "Творчество": [
        {
            "title": "Гитара - 1 час",
            "priority": "low",
            "due_date": "2026-01-26",
            "tags": ["creativity", "guitar"],
        },
    ],
    "Работа: Разное": [
        {
            "title": "Встреча SMS — попытаться сэкономить деньги компании",
            "priority": "medium",
            "due_date": "2026-01-29",
            "tags": ["work", "meeting"],
        },
        {
            "title": "Разобраться с тегированием (документ приложен)",
            "priority": "medium",
            "due_date": "2026-02-05",
            "tags": ["work"],
        },
        {
            "title": "Разобраться с процедурами управления на проекте НГ (и ЦПТ)",
            "priority": "medium",
            "due_date": "2026-01-23",
            "tags": ["work", "procedures"],
        },
    ],
}


def create_project(project_data):
    """Create a project via API."""
    response = requests.post(f"{API_URL}/projects", headers=HEADERS, json=project_data)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error creating project {project_data['name']}: {response.text}")
        return None


def create_task(task_data, project_id):
    """Create a task via API."""
    task_payload = {
        "title": task_data["title"],
        "project_id": project_id,
        "priority": task_data.get("priority", "medium"),
        "status": "todo",
    }

    if "description" in task_data:
        task_payload["description"] = task_data["description"]

    if "due_date" in task_data:
        task_payload["due_date"] = task_data["due_date"]

    if "tags" in task_data:
        task_payload["tags"] = task_data["tags"]

    response = requests.post(f"{API_URL}/tasks", headers=HEADERS, json=task_payload)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error creating task {task_data['title']}: {response.text}")
        return None


def main():
    print("=" * 60)
    print("Seeding database with real tasks from Obsidian vault")
    print("=" * 60)

    # Create projects and store their IDs
    project_ids = {}
    print("\n📁 Creating projects...")
    for project_data in PROJECTS:
        project = create_project(project_data)
        if project:
            project_ids[project_data["name"]] = project["id"]
            print(f"  ✅ {project_data['name']} (id={project['id']})")

    # Create tasks for each project
    print("\n📋 Creating tasks...")
    total_tasks = 0
    for project_name, tasks in TASKS.items():
        if project_name not in project_ids:
            print(f"  ⚠️ Project {project_name} not found, skipping tasks")
            continue

        project_id = project_ids[project_name]
        print(f"\n  📁 {project_name}:")
        for task_data in tasks:
            task = create_task(task_data, project_id)
            if task:
                total_tasks += 1
                due = task_data.get("due_date", "no date")
                print(f"    ✅ {task_data['title'][:50]}... ({due})")

    print("\n" + "=" * 60)
    print(f"✅ Done! Created {len(project_ids)} projects and {total_tasks} tasks")
    print("=" * 60)


if __name__ == "__main__":
    main()
