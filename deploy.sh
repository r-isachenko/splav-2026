#!/usr/bin/env bash
# Пересобрать сайт из заметок и опубликовать одной командой.
#
#   ./deploy.sh            # rebuild + commit + push
#   ./deploy.sh --dry      # только rebuild, без git (для проверки)
#
# Источник истины — заметки в vault. Скрипт запускает build.py, и если
# index.html/assets изменились — коммитит и пушит в origin.
set -euo pipefail

SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SITE_DIR/../../.." && pwd)"

# Python из vault-окружения, иначе системный
PY="$VAULT_ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "→ Сборка сайта из заметок…"
"$PY" "$SITE_DIR/build.py"

if [ "${1:-}" = "--dry" ]; then
  echo "✓ Dry-run: git пропущен."
  exit 0
fi

cd "$SITE_DIR"
git add -A

if git diff --cached --quiet; then
  echo "✓ Изменений нет — сайт уже актуален."
  exit 0
fi

STAMP="$(date '+%Y-%m-%d %H:%M')"
git commit -m "Обновление сайта: $STAMP"
echo "→ Пуш в origin…"
git push
echo "✓ Опубликовано. Через ~1 мин обновится на github.io."
