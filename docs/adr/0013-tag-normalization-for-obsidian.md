# ADR 0013: Tag Normalization for Obsidian Compatibility

## Status
Accepted

## Context
Проект интегрируется с Obsidian Second Brain, где теги имеют специфический формат:
- Должны быть в lowercase
- Пробелы заменяются на дефисы
- Только буквы, цифры, дефисы и подчёркивания
- Не могут начинаться с дефиса

Примеры Obsidian тегов:
- `#python` ✅
- `#web-development` ✅
- `#data_science` ✅
- `#Python Programming` ❌ (пробелы, uppercase)

Без нормализации:
- Пользователь вводит "Python Programming"
- Создаётся тег "Python Programming"
- В Obsidian это становится `#Python` и отдельно слово "Programming"

## Decision
Автоматически **нормализовать названия тегов** в Service Layer при создании:

```python
class TagService:
    def _normalize_tag_name(self, name: str) -> str:
        """
        Нормализация для Obsidian совместимости.

        Examples:
            "Python Programming" → "python-programming"
            "Web Development" → "web-development"
            "Data_Science" → "data_science"
            "API & Backend" → "api-backend"
        """
        import re

        # 1. Lowercase
        normalized = name.lower()

        # 2. Replace spaces with dashes
        normalized = normalized.replace(" ", "-")

        # 3. Remove invalid characters (keep only a-z, 0-9, -, _)
        normalized = re.sub(r'[^a-z0-9\-_]', '', normalized)

        # 4. Replace multiple dashes with single dash
        normalized = re.sub(r'-+', '-', normalized)

        # 5. Remove leading/trailing dashes
        normalized = normalized.strip('-')

        return normalized

    async def create_tag(self, name: str) -> Tag:
        # Normalize before creating
        normalized_name = self._normalize_tag_name(name)

        # Check if normalized tag exists
        existing = await self.tag_repo.get_by_name(normalized_name)
        if existing:
            return existing

        tag = Tag(name=normalized_name)
        tag = await self.tag_repo.create(tag)
        await self.db.flush()
        return tag
```

## Alternatives Considered

### 1. Хранить оригинальное название
```python
class Tag(Base):
    original_name: Mapped[str]  # "Python Programming"
    normalized_name: Mapped[str]  # "python-programming"
```
**Отклонено**:
- ❌ Дублирование данных
- ❌ Путаница - какое имя использовать?
- ❌ Сложность поиска (по какому полю?)
- ❌ В Obsidian всё равно используется нормализованное

### 2. Нормализация на клиенте
```javascript
// Frontend нормализует перед отправкой
const normalizedTag = tagName.toLowerCase().replace(/\s/g, '-');
```
**Отклонено**:
- ❌ Дублирование логики (frontend + backend)
- ❌ Нельзя доверять клиенту
- ❌ API используется из разных клиентов
- ❌ Логика размазана

### 3. Нормализация в БД (trigger)
```sql
CREATE TRIGGER normalize_tag_name
BEFORE INSERT ON tags
FOR EACH ROW
SET NEW.name = LOWER(REPLACE(NEW.name, ' ', '-'));
```
**Отклонено**:
- ❌ БД-specific код
- ❌ Сложнее тестировать
- ❌ Логика скрыта от приложения
- ❌ Не переносится между БД

### 4. Разрешить любые теги
**Отклонено**:
- ❌ Несовместимо с Obsidian
- ❌ Путаница с дублирующимися тегами ("Python" vs "python")
- ❌ Не решает основную цель интеграции

## Consequences

### Positive
- ✅ **Obsidian Compatible**: все теги работают в Obsidian
- ✅ **No Duplicates**: "Python", "python", "PYTHON" → один тег "python"
- ✅ **Consistent**: все теги в одном формате
- ✅ **Automatic**: пользователь не думает о форматировании
- ✅ **Search Friendly**: поиск по тегам проще (case-insensitive)

### Negative
- ❌ **Loss of Original**: оригинальное название теряется
- ❌ **User Surprise**: пользователь вводит "Python Programming", видит "python-programming"
- ❌ **Information Loss**: символы вроде "&" удаляются

### Neutral
- 🔄 **Validation**: нужна валидация что normalized name не пустой
- 🔄 **API Response**: возвращаем normalized name

## Normalization Rules

### Rule 1: Lowercase
```python
"Python" → "python"
"WEB DEVELOPMENT" → "web development"
```

### Rule 2: Spaces → Dashes
```python
"Python Programming" → "python-programming"
"Web Development" → "web-development"
"data science" → "data-science"
```

### Rule 3: Remove Invalid Characters
```python
"API & Backend" → "api-backend"
"C++" → "c"
"Node.js" → "nodejs"
"@mentions" → "mentions"
```

### Rule 4: Collapse Multiple Dashes
```python
"python--programming" → "python-programming"
"web---dev" → "web-dev"
```

### Rule 5: Trim Dashes
```python
"-python-" → "python"
"--web--" → "web"
```

## Examples

### Valid Transformations
| Input | Normalized | Obsidian Tag |
|-------|-----------|--------------|
| "Python" | "python" | `#python` |
| "Python Programming" | "python-programming" | `#python-programming` |
| "Web Development" | "web-development" | `#web-development` |
| "Data_Science" | "data_science" | `#data_science` |
| "API & Backend" | "api-backend" | `#api-backend` |
| "C++" | "c" | `#c` |
| "Node.js 2024" | "nodejs-2024" | `#nodejs-2024` |

### Edge Cases
| Input | Normalized | Valid? |
|-------|-----------|--------|
| "   " | "" | ❌ Empty - reject |
| "123" | "123" | ✅ Valid |
| "---" | "" | ❌ Empty - reject |
| "a" | "a" | ✅ Valid |
| "🚀 Rocket" | "rocket" | ✅ Valid (emoji removed) |

## Implementation

### Service Layer
```python
class TagService:
    async def create_tag(self, name: str) -> Tag:
        # Normalize
        normalized = self._normalize_tag_name(name)

        # Validate not empty
        if not normalized:
            raise ValueError(f"Tag name '{name}' normalizes to empty string")

        # Get or create
        existing = await self.tag_repo.get_by_name(normalized)
        if existing:
            return existing

        tag = Tag(name=normalized)
        await self.tag_repo.create(tag)
        await self.db.flush()
        return tag

    async def bulk_get_or_create(self, tag_names: List[str]) -> List[Tag]:
        # Normalize all names
        normalized_names = [self._normalize_tag_name(name) for name in tag_names]

        # Filter out empty
        valid_names = [n for n in normalized_names if n]

        # Remove duplicates
        unique_names = list(set(valid_names))

        # Get or create
        return await self.tag_repo.bulk_get_or_create(unique_names)
```

### API Response
```json
// Request
POST /tags
{
    "name": "Python Programming"
}

// Response
{
    "id": 1,
    "name": "python-programming",  // Normalized
    "created_at": "2026-01-19T00:00:00"
}
```

### Task Creation
```json
// Request
POST /tasks
{
    "title": "Learn async",
    "tag_names": ["Python Programming", "Web Development", "API & Backend"]
}

// Response
{
    "id": 1,
    "title": "Learn async",
    "tags": [
        {"id": 1, "name": "python-programming"},
        {"id": 2, "name": "web-development"},
        {"id": 3, "name": "api-backend"}
    ]
}
```

## Validation

```python
async def create_tag(self, name: str) -> Tag:
    if not name or not name.strip():
        raise ValueError("Tag name cannot be empty")

    normalized = self._normalize_tag_name(name)

    if not normalized:
        raise ValueError(
            f"Tag name '{name}' contains only invalid characters"
        )

    if len(normalized) > 50:
        raise ValueError(
            f"Tag name too long after normalization: {normalized}"
        )

    # ... create tag
```

## Testing

```python
def test_tag_normalization():
    service = TagService(mock_db)

    # Test cases
    assert service._normalize_tag_name("Python") == "python"
    assert service._normalize_tag_name("Python Programming") == "python-programming"
    assert service._normalize_tag_name("Web Development") == "web-development"
    assert service._normalize_tag_name("API & Backend") == "api-backend"
    assert service._normalize_tag_name("C++") == "c"
    assert service._normalize_tag_name("   ") == ""
    assert service._normalize_tag_name("🚀 Rocket") == "rocket"
```

## Obsidian Integration Example

```markdown
# My Task Note in Obsidian

## Task: Learn Async Programming

Tags: #python-programming #web-development #api-backend

Created tasks in Task Manager with tags:
- "Python Programming" → #python-programming ✅
- "Web Development" → #web-development ✅
- "API & Backend" → #api-backend ✅

All tags work correctly in Obsidian search!
```

## Future Enhancements

### Potential Improvements
1. **Synonym Mapping**: "js" → "javascript", "py" → "python"
2. **Tag Suggestions**: предлагать существующие похожие теги
3. **Internationalization**: поддержка non-ASCII символов
4. **Abbreviation Support**: "ML" → "ml", "AI" → "ai"

```python
# Future: synonym mapping
TAG_SYNONYMS = {
    "js": "javascript",
    "py": "python",
    "ts": "typescript",
}

def _normalize_tag_name(self, name: str) -> str:
    normalized = ...  # Current normalization

    # Apply synonyms
    if normalized in TAG_SYNONYMS:
        normalized = TAG_SYNONYMS[normalized]

    return normalized
```

## Related ADRs
- ADR-0003: Service Layer - нормализация в Service
- ADR-0010: Validation in Service Layer

## Notes
Tag нормализация - критичная feature для Obsidian интеграции. Без неё теги из Task Manager не будут корректно отображаться в Obsidian.

Нормализация в Service Layer (не в API, не в БД) даёт правильный баланс:
- Централизованная логика
- Тестируемость
- Переиспользование в разных API endpoints
