#!/usr/bin/env bash
set -Eeuo pipefail

# ==========================================
# Shutdown (Auto-Commit - Verbose)
# Ubuntu / Bash version
# ==========================================

# Always operate from the git repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"


echo "=========================================================="
echo "[0] Repo + tool sanity"
echo "=========================================================="

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found in PATH."
  read -r -p "Press Enter to exit..." _
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: This folder is not a git repo."
  read -r -p "Press Enter to exit..." _
  exit 1
fi

echo "OK: git repo detected"
echo

echo "=========================================================="
echo "[1] Current changes (before staging)"
echo "=========================================================="
git status
echo
git status --porcelain
echo

# --- Timestamp via Python (preferred), fallback to date ---
if command -v python3 >/dev/null 2>&1; then
  TS="$(python3 -c "from datetime import datetime; print(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))")"
else
  TS="$(date +"%Y-%m-%d_%H-%M-%S")"
fi
MSG="Auto-commit ${TS}"

# --- Commit message file inside .git (never tracked) ---
MSGFILE=".git/COMMIT_MSG_TMP.txt"
printf "%s\n" "$MSG" > "$MSGFILE"

echo "=========================================================="
echo "[2] Commit message"
echo "=========================================================="
echo "MSG    = \"$MSG\""
echo "MSGFILE= \"$MSGFILE\""
cat "$MSGFILE"
echo

echo "=========================================================="
echo "[3] Stage changes (git add .)"
echo "=========================================================="
set +e
git add .
AERR=$?
set -e
echo "git add exit code: $AERR"
if [[ $AERR -ne 0 ]]; then
  echo "ERROR: git add failed."
  rm -f "$MSGFILE" >/dev/null 2>&1 || true
  read -r -p "Press Enter to exit..." _
  exit "$AERR"
fi
echo

echo "--- Staged files ---"
git diff --name-only --cached
echo

# If nothing staged, there is nothing to commit
if git diff --cached --quiet; then
  echo "=========================================================="
  echo "[4] Nothing staged - no commit needed"
  echo "=========================================================="
  rm -f "$MSGFILE" >/dev/null 2>&1 || true
  echo "Done."
  read -r -p "Press Enter to exit..." _
  exit 0
fi

echo "=========================================================="
echo "[4] Commit"
echo "=========================================================="
set +e
git commit -F "$MSGFILE"
CERR=$?
set -e
echo "git commit exit code: $CERR"
if [[ $CERR -ne 0 ]]; then
  echo "ERROR: git commit failed. Common fixes:"
  echo "  git config --global user.name \"Your Name\""
  echo "  git config --global user.email \"you@example.com\""
  echo
  rm -f "$MSGFILE" >/dev/null 2>&1 || true
  read -r -p "Press Enter to exit..." _
  exit "$CERR"
fi

echo
echo "=========================================================="
echo "[5] Push"
echo "=========================================================="
set +e
git push
PERR=$?
set -e
echo "git push exit code: $PERR"

rm -f "$MSGFILE" >/dev/null 2>&1 || true

if [[ $PERR -ne 0 ]]; then
  echo "ERROR: git push failed."
  read -r -p "Press Enter to exit..." _
  exit "$PERR"
fi

echo
echo "Done."
read -r -p "Press Enter to exit..." _
exit 0
