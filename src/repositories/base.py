"""Base repository with common CRUD operations."""

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import Base

# TypeVar для Generic класса - позволяет работать с любой моделью
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий с CRUD операциями.

    Generic[ModelType] означает, что этот класс работает с любой моделью,
    наследующейся от Base.

    Пример использования:
        project_repo = BaseRepository[Project](Project, db_session)
        project = await project_repo.get_by_id(1)
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Инициализация репозитория.

        Args:
            model: Класс модели SQLAlchemy (например, Project, Task)
            db: Асинхронная сессия базы данных
        """
        self.model = model
        self.db = db

    async def create(self, obj: ModelType) -> ModelType:
        """
        Создать новую запись в БД.

        Args:
            obj: Экземпляр модели для сохранения

        Returns:
            Созданный объект с заполненным ID

        Пример:
            project = Project(name="Новый проект")
            created_project = await repo.create(project)
            print(created_project.id)  # 1 (автоматически из БД)
        """
        self.db.add(obj)
        await self.db.flush()  # flush() отправляет в БД, но не commit
        await self.db.refresh(obj)  # refresh() обновляет obj данными из БД (ID, timestamps)
        return obj

    async def get_by_id(self, id: int) -> ModelType | None:
        """
        Получить объект по ID.

        Args:
            id: Первичный ключ записи

        Returns:
            Объект модели или None, если не найден

        SQL эквивалент:
            SELECT * FROM table WHERE id = {id} LIMIT 1;
        """
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        Получить все записи с пагинацией.

        Args:
            skip: Сколько записей пропустить (для пагинации)
            limit: Максимальное количество записей

        Returns:
            Список объектов модели

        SQL эквивалент:
            SELECT * FROM table OFFSET {skip} LIMIT {limit};

        Пример пагинации:
            # Страница 1 (первые 10 записей)
            page1 = await repo.get_all(skip=0, limit=10)

            # Страница 2 (записи 11-20)
            page2 = await repo.get_all(skip=10, limit=10)
        """
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs: Any) -> ModelType | None:
        """
        Обновить запись по ID.

        Args:
            id: Первичный ключ записи
            **kwargs: Поля для обновления (name="Новое имя", is_archived=True)

        Returns:
            Обновлённый объект или None, если не найден

        SQL эквивалент:
            UPDATE table SET field1=value1, field2=value2 WHERE id={id};

        Пример:
            # Обновить только имя проекта
            project = await repo.update(1, name="Новое название")

            # Обновить несколько полей
            project = await repo.update(
                1,
                name="Новое название",
                is_archived=True,
                color="#FF0000"
            )
        """
        # Получаем объект
        obj = await self.get_by_id(id)
        if not obj:
            return None

        # Обновляем только переданные поля
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """
        Удалить запись по ID.

        Args:
            id: Первичный ключ записи

        Returns:
            True если удалено, False если не найдено

        SQL эквивалент:
            DELETE FROM table WHERE id={id};
        """
        result = await self.db.execute(delete(self.model).where(self.model.id == id))
        return result.rowcount > 0  # rowcount - количество затронутых строк

    async def exists(self, id: int) -> bool:
        """
        Проверить существование записи.

        Args:
            id: Первичный ключ записи

        Returns:
            True если существует, False если нет

        SQL эквивалент:
            SELECT EXISTS(SELECT 1 FROM table WHERE id={id});
        """
        obj = await self.get_by_id(id)
        return obj is not None

    async def count(self) -> int:
        """
        Подсчитать количество записей.

        Returns:
            Общее количество записей в таблице

        SQL эквивалент:
            SELECT COUNT(*) FROM table;
        """
        from sqlalchemy import func

        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()
