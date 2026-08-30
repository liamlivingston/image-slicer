#!/bin/bash
# Resolve physical script directory (dereferencing symlinks)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Project root is 2 levels up from scripts/commands/
PROJECT_ROOT="$( cd -P "$SCRIPT_DIR/../.." >/dev/null 2>&1 && pwd )"
cd "$PROJECT_ROOT" || exit 1

clear
echo "=================================================="
echo "          🖼️  IMAGE GRID SLICER & ANIMATOR         "
echo "=================================================="
echo ""

# Locate Python 3
PYTHON_BIN=""
if [ -d "env" ] && [ -f "env/bin/python3" ]; then
    PYTHON_BIN="env/bin/python3"
    echo "✔ Using virtual environment: env"
elif [ -d "venv" ] && [ -f "venv/bin/python3" ]; then
    PYTHON_BIN="venv/bin/python3"
    echo "✔ Using virtual environment: venv"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    echo "✔ Using system Python: $(python3 --version)"
else
    echo "❌ Error: python3 could not be found!"
    echo "Please install Python 3 from https://www.python.org/ or Homebrew."
    echo ""
    read -p "Press [Enter] to exit..."
    exit 1
fi

# Ensure required libraries are installed
if ! "$PYTHON_BIN" -c "import PIL, numpy" >/dev/null 2>&1; then
    echo "📦 Checking and installing dependencies (requirements.txt)..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
fi

echo ""
echo "🚀 Launching Image Grid Slicer..."
echo ""

"$PYTHON_BIN" slice_image.py "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "⚠️  App exited with code $EXIT_CODE."
    read -p "Press [Enter] to close..."
fi
