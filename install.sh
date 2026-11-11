#!/bin/bash
set -e

echo "=== Installation TTMC Generator ==="

if ! command -v uv &> /dev/null; then
  echo "Installation de uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

echo "Installation des dépendances Python..."
uv sync

echo ""
echo "Installation terminée. Lance './lancer.sh' pour démarrer."
