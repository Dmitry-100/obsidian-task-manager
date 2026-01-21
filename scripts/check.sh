#!/bin/bash
# =============================================================================
# check.sh - Скрипт проверки качества кода
# =============================================================================
# Запускает все проверки: тесты, линтер, типы, безопасность
#
# Использование:
#   ./scripts/check.sh          # Все проверки
#   ./scripts/check.sh --fast   # Только быстрые (без тестов)
#   ./scripts/check.sh --fix    # С автоисправлением ruff
#
# Коды выхода:
#   0 - Все проверки прошли
#   1 - Есть ошибки (детали в выводе)
# =============================================================================

set -e  # Остановиться при первой ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для красивого вывода
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Парсинг аргументов
FAST_MODE=false
FIX_MODE=false

for arg in "$@"; do
    case $arg in
        --fast)
            FAST_MODE=true
            ;;
        --fix)
            FIX_MODE=true
            ;;
    esac
done

# Переход в директорию проекта
cd "$(dirname "$0")/.."

# Активация виртуального окружения (если есть)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo ""
echo -e "${BLUE}🔍 Obsidian Task Manager - Quality Check${NC}"
echo -e "${BLUE}==========================================${NC}"

# =============================================================================
# 1. RUFF - Линтер
# =============================================================================
print_header "1. Ruff (Linter)"

if [ "$FIX_MODE" = true ]; then
    echo "Running with --fix..."
    ruff check src/ --fix
fi

if ruff check src/; then
    print_success "Ruff: All checks passed"
else
    print_error "Ruff: Found issues"
    exit 1
fi

# =============================================================================
# 2. RUFF FORMAT - Форматирование
# =============================================================================
print_header "2. Ruff Format"

if [ "$FIX_MODE" = true ]; then
    ruff format src/
    print_success "Ruff format: Applied"
else
    if ruff format src/ --check; then
        print_success "Ruff format: Code is properly formatted"
    else
        print_warning "Ruff format: Code needs formatting (run with --fix)"
    fi
fi

# =============================================================================
# 3. MYPY - Проверка типов
# =============================================================================
print_header "3. Mypy (Type Checker)"

if mypy src/; then
    print_success "Mypy: No type errors"
else
    print_error "Mypy: Found type errors"
    exit 1
fi

# =============================================================================
# 4. BANDIT - Безопасность
# =============================================================================
print_header "4. Bandit (Security)"

if bandit -r src/ -q; then
    print_success "Bandit: No security issues"
else
    print_error "Bandit: Found security issues"
    exit 1
fi

# =============================================================================
# 5. PYTEST - Тесты (пропускается в --fast режиме)
# =============================================================================
if [ "$FAST_MODE" = false ]; then
    print_header "5. Pytest (Tests)"

    if pytest --tb=short -q; then
        print_success "Pytest: All tests passed"
    else
        print_error "Pytest: Some tests failed"
        exit 1
    fi
else
    print_header "5. Pytest (Tests) - SKIPPED (--fast mode)"
    print_warning "Tests skipped in fast mode"
fi

# =============================================================================
# РЕЗУЛЬТАТ
# =============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ ALL CHECKS PASSED!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
