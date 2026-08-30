#!/bin/bash
# Move to project root directory
cd "$(dirname "$0")/.." || exit 1

clear
echo "=================================================="
echo "          📦  IMAGE GRID SLICER SETUP             "
echo "=================================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 was not found on your system."
    echo "Please install Python 3 from https://www.python.org/ or via Homebrew:"
    echo "  brew install python3"
    echo ""
    read -p "Press [Enter] to exit..."
    exit 1
fi

echo "✔ Found $(python3 --version)"
echo ""

if [ ! -d "env" ]; then
    echo "Creating virtual environment in './env'..."
    python3 -m venv env
    echo "✔ Virtual environment created."
else
    echo "✔ Virtual environment './env' already exists."
fi

echo ""
echo "Installing and updating dependencies (requirements.txt)..."
env/bin/python3 -m pip install --upgrade pip
env/bin/python3 -m pip install -r requirements.txt

echo ""
echo "=================================================="
echo "🎉 Setup Complete! You can launch the app via:"
echo "   scripts/run.command"
echo "=================================================="
echo ""
read -p "Press [Enter] to close this window..."
