## Summary

<!-- Кратко опишите что делает этот PR (1-3 предложения) -->


## Changes

<!-- Список основных изменений -->
-


## Definition of Done

**Перед мержем убедитесь, что все пункты выполнены:**

### Code Quality
- [ ] Ruff linter проходит без ошибок (`ruff check src/`)
- [ ] Ruff format применён (`ruff format src/`)
- [ ] Mypy проверка типов пройдена (`mypy src/`)
- [ ] Bandit security scan пройден (`bandit -r src/ -q`)

### Testing
- [ ] Тесты написаны для новой функциональности
- [ ] Все тесты проходят (`pytest`)
- [ ] Coverage не упал (минимум 70%)

### Code Standards
- [ ] Type hints добавлены для новых функций
- [ ] Docstrings написаны для публичных методов
- [ ] Нет захардкоженных значений (используется config)
- [ ] Ошибки обрабатываются корректно (ValueError, HTTPException)

### Security
- [ ] Нет секретов в коде (API ключи, пароли)
- [ ] Пользовательский ввод валидируется
- [ ] SQL инъекции невозможны (используется ORM)

### Documentation
- [ ] README обновлён (если нужно)
- [ ] API endpoints задокументированы (OpenAPI/docstrings)

---

**Quick check command:**
```bash
./scripts/check.sh
```

## Related Issues

<!-- Ссылки на issues, если есть -->
Closes #
