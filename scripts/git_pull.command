#!/bin/bash
# Move to project root directory
cd "$(dirname "$0")/.." || exit 1

clear
echo "=================================================="
echo "          🔄  UPDATING IMAGE GRID SLICER          "
echo "=================================================="
echo ""

echo "Pulling latest changes from GitHub..."
git pull
PULL_STATUS=$?
echo ""

if [ $PULL_STATUS -eq 0 ]; then
    echo "✔ Git pull successful!"
    echo ""
    echo "Updating dependencies (pip install -r requirements.txt)..."
    
    if [ -d "env" ] && [ -f "env/bin/python3" ]; then
        env/bin/python3 -m pip install -r requirements.txt
    elif [ -d "venv" ] && [ -f "venv/bin/python3" ]; then
        venv/bin/python3 -m pip install -r requirements.txt
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m pip install -r requirements.txt
    fi
    
    echo ""
    echo "=================================================="
    echo "🎉 Update Complete! Everything is up to date."
    echo "=================================================="
else
    echo "❌ Git pull encountered an issue. Please check your git status."
fi

echo ""
read -p "Press [Enter] to close this window..."
