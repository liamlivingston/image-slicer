#!/usr/bin/env python3
"""
Screenshot Capture Utility for Image Grid Slicer
------------------------------------------------
Run this script on any macOS computer:
    python3 capture_screenshot.py

It will:
1. Launch the app and bring its window to the front.
2. Wait for all widgets, fonts, and UI elements to fully render.
3. Automatically capture the screen using macOS's built-in `screencapture`.
4. Save the image to 'app_screenshot.png' in the current folder.
5. Automatically close the app once captured.
"""

import os
import sys
import time
import subprocess
import threading
import tkinter as tk

from slice_image import ImageSlicerApp


def main():
    print("🚀 Launching Image Grid Slicer for screenshot capture...")
    root = tk.Tk()
    app = ImageSlicerApp(root)

    # Bring window to front
    root.lift()
    root.attributes("-topmost", True)
    root.after_idle(root.attributes, "-topmost", False)
    root.focus_force()
    root.update()

    output_path = os.path.abspath("app_screenshot.png")

    def capture_and_exit():
        # Wait 1.5s for fonts, ttk styling, and canvas items to settle
        time.sleep(1.5)
        root.update()

        print(f"📸 Capturing screenshot to:\n   {output_path}")
        result = subprocess.run(["screencapture", "-x", output_path])

        if result.returncode == 0 and os.path.exists(output_path):
            file_size_kb = os.path.getsize(output_path) / 1024
            print(f"✅ Success! Saved 'app_screenshot.png' ({file_size_kb:.1f} KB)")
            print("👉 You can now copy 'app_screenshot.png' over.")
        else:
            print("❌ Failed to capture screenshot using 'screencapture'.")

        time.sleep(0.8)
        root.destroy()

    threading.Thread(target=capture_and_exit, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
