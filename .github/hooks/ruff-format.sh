#!/usr/bin/env bash
# Auto-format edited Python files with Ruff after agent file writes.
# Reads the hook JSON from stdin (VS Code hooks) and formats the file that
# was created/edited. Filtering by file extension happens here because VS Code
# ignores hook matchers.
set -u

input=$(cat)

# Extract the edited file path. VS Code hooks use camelCase (tool_input.filePath),
# Claude Code uses snake_case (tool_input.file_path). Parsing with python3 keeps
# this free of a jq dependency (jq is not installed on macOS by default).
file_path="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = data.get("tool_input") or {}
fp = ti.get("filePath") or ti.get("file_path") or ""
print(fp)
')"

case "$file_path" in
  *.py)
    # Resolve the project root: <repo>/.github/hooks/ -> <repo>/
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    project_root="$(dirname "$(dirname "$script_dir")")"
    cd "$project_root" || exit 0

    if command -v uv >/dev/null 2>&1; then
      uv run ruff format "$file_path" >/dev/null 2>&1 || true
      uv run ruff check --fix "$file_path" >/dev/null 2>&1 || true
    elif command -v ruff >/dev/null 2>&1; then
      ruff format "$file_path" >/dev/null 2>&1 || true
      ruff check --fix "$file_path" >/dev/null 2>&1 || true
    fi
    ;;
esac

# Always allow the session to continue.
printf '{"continue": true}\n'
exit 0
