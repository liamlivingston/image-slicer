# 🚀 Quick Launch & Helper Scripts

The **`scripts/`** folder provides intuitive, double-clickable shortcuts for running and updating the Image Grid Slicer.

---

### 📂 Folder Layout

* **`scripts/`** (Main Folder): Contains clean, intuitive **aliases / shortcuts** for 1-click double-clicking.
* **`scripts/commands/`** (Subfolder): Houses the underlying execution scripts.

---

### 🍏 On macOS (Double-Click in Finder)

Just double-click any of the aliases in the **`scripts/`** folder:

| Double-Click Alias | Action |
| :--- | :--- |
| **`Run App.command`** | Launches the app. Automatically detects your virtual environment (`env`), verifies dependencies, and opens the GUI. |
| **`Update (Git Pull).command`** | Pulls the newest updates from GitHub (`git pull`) and updates any new dependencies. |
| **`Install & Setup.command`** | Creates the `env` virtual environment from scratch and installs all dependencies. |

---

### 🪟 On Windows (Double-Click in File Explorer)

| Double-Click Shortcut | Action |
| :--- | :--- |
| **`Run App.bat`** | Launches the app in Python. |
| **`Update (Git Pull).bat`** | Pulls latest changes and updates dependencies. |
