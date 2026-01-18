"""Task comment repository with specific queries."""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import TaskComment
from .base import BaseRepository


class TaskCommentRepository(BaseRepository[TaskComment]):
    """
    Репозиторий для работы с комментариями к задачам.

    Комментарии поддерживают Markdown форматирование.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(TaskComment, db)

    async def get_by_task(
        self,
        task_id: int,
        limit: Optional[int] = None
    ) -> List[TaskComment]:
        """
        Получить все комментарии для задачи.

        Args:
            task_id: ID задачи
            limit: Максимальное количество комментариев (None = все)

        Returns:
            Список комментариев, отсортированных по дате создания

        SQL эквивалент:
            SELECT * FROM task_comments
            WHERE task_id = {task_id}
            ORDER BY created_at DESC
            LIMIT {limit};

        Пример:
            # Получить все комментарии
            all_comments = await repo.get_by_task(1)

            # Получить последние 5 комментариев
            recent_comments = await repo.get_by_task(1, limit=5)
        """
        query = (
            select(TaskComment)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_comments(
        self,
        days: int = 7,
        limit: int = 50
    ) -> List[TaskComment]:
        """
        Получить недавние комментарии.

        Args:
            days: За сколько дней
            limit: Максимальное количество

        Returns:
            Список недавних комментариев

        SQL эквивалент:
            SELECT * FROM task_comments
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            ORDER BY created_at DESC
            LIMIT {limit};

        Пример:
            # Комментарии за последние 3 дня
            recent = await repo.get_recent_comments(days=3)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(TaskComment)
            .where(TaskComment.created_at >= cutoff_date)
            .order_by(TaskComment.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_comments(
        self,
        search_term: str,
        task_id: Optional[int] = None
    ) -> List[TaskComment]:
        """
        Поиск по содержимому комментариев.

        Args:
            search_term: Поисковый запрос
            task_id: Опционально - искать только в комментариях конкретной задачи

        Returns:
            Список найденных комментариев

        SQL эквивалент (с task_id):
            SELECT * FROM task_comments
            WHERE content ILIKE '%{search_term}%'
            AND task_id = {task_id};

        Пример:
            # Найти все комментарии со словом "bug"
            bug_comments = await repo.search_comments("bug")

            # Найти "bug" только в комментариях задачи #5
            task_bug_comments = await repo.search_comments("bug", task_id=5)
        """
        conditions = [TaskComment.content.ilike(f"%{search_term}%")]

        if task_id is not None:
            conditions.append(TaskComment.task_id == task_id)

        result = await self.db.execute(
            select(TaskComment).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def count_by_task(self, task_id: int) -> int:
        """
        Подсчитать количество комментариев у задачи.

        Args:
            task_id: ID задачи

        Returns:
            Количество комментариев

        SQL эквивалент:
            SELECT COUNT(*) FROM task_comments WHERE task_id = {task_id};
        """
        from sqlalchemy import func

        result = await self.db.execute(
            select(func.count())
            .select_from(TaskComment)
            .where(TaskComment.task_id == task_id)
        )
        return result.scalar_one()

    async def delete_by_task(self, task_id: int) -> int:
        """
        Удалить все комментарии задачи.

        Args:
            task_id: ID задачи

        Returns:
            Количество удалённых комментариев

        Обычно не нужен, так как cascade удалит комментарии
        при удалении задачи, но может быть полезен для очистки.
        """
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(TaskComment).where(TaskComment.task_id == task_id)
        )
        return result.rowcount
