#!/bin/bash

# Get the directory where this script is located
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "------------------------------------------------"
echo "🚀 Preparing Image Grid Slicer..."
echo "------------------------------------------------"

# Clear macOS quarantine flags on the app bundle
if [ -d "$DIR/dist/slice_image.app" ]; then
    echo "🔑 Bypassing Gatekeeper restrictions..."
    xattr -cr "$DIR/dist/slice_image.app" 2>/dev/null
    
    echo "🎉 Launching App..."
    open "$DIR/dist/slice_image.app"
else
    echo "❌ Error: Could not find dist/slice_image.app"
    echo "Make sure dist/slice_image.app is present in the same directory."
    read -p "Press Enter to exit..."
fi
