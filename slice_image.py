#!/usr/bin/env python3
import os
import sys
import math
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw

# ---------------------------------------------------------------------------
# Light & Dark Color Palettes
# ---------------------------------------------------------------------------
LIGHT_PALETTE = {
    "BG":        "#f2f2f7",  # macOS system grouped background
    "SURFACE":   "#ffffff",  # Crisp pure white for cards and panels
    "CARD":      "#ffffff",  # Card container background
    "ACCENT":    "#007aff",  # Apple system blue
    "ACCENT2":   "#5856d6",  # Apple indigo
    "TEXT":      "#1c1c1e",  # Primary dark text (high contrast)
    "SUBTEXT":   "#48484a",  # Secondary readable dark gray text
    "GREEN":     "#28a745",  # Forest green
    "BORDER":    "#d1d1d6",  # Clean divider border
    "CANVAS_BG": "#e5e5ea",  # Canvas neutral gray
}

DARK_PALETTE = {
    "BG":        "#1a1a2e",  # Very dark navy background
    "SURFACE":   "#16213e",  # Dark blue-gray surface panel
    "CARD":      "#0f3460",  # Section card containers
    "ACCENT":    "#e94560",  # Vibrant red-pink for primary actions / highlights
    "ACCENT2":   "#533483",  # Deep purple for secondary actions
    "TEXT":      "#ffffff",  # Crisp white text
    "SUBTEXT":   "#a0a0b0",  # Muted readable text
    "GREEN":     "#00ff88",  # Neon green for grid lines / success
    "BORDER":    "#2a2a4a",  # Crisp borders
    "CANVAS_BG": "#0d1117",  # Deep dark canvas background
}

CONFIG_PATH = os.path.expanduser("~/.image_slicer_config.json")

def get_system_theme():
    try:
        cmd = ["defaults", "read", "-g", "AppleInterfaceStyle"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1)
        if res.stdout.strip() == "Dark":
            return "dark"
    except Exception:
        pass
    return "light"

def load_user_theme():
    import json
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                if cfg.get("theme") in ("light", "dark"):
                    return cfg["theme"]
        except Exception:
            pass
    return get_system_theme()

def save_user_theme(theme_mode):
    import json
    try:
        cfg = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        cfg["theme"] = theme_mode
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f)
    except Exception:
        pass

DEFAULT_THEME = load_user_theme()
_active_pal = DARK_PALETTE if DEFAULT_THEME == "dark" else LIGHT_PALETTE

BG        = _active_pal["BG"]
SURFACE   = _active_pal["SURFACE"]
CARD      = _active_pal["CARD"]
ACCENT    = _active_pal["ACCENT"]
ACCENT2   = _active_pal["ACCENT2"]
TEXT      = _active_pal["TEXT"]
SUBTEXT   = _active_pal["SUBTEXT"]
GREEN     = _active_pal["GREEN"]
BORDER    = _active_pal["BORDER"]
CANVAS_BG = _active_pal["CANVAS_BG"]


# ---------------------------------------------------------------------------
# App run directory helper
# ---------------------------------------------------------------------------
def get_app_run_dir():
    if getattr(sys, 'frozen', False):
        exe_path = os.path.abspath(sys.executable)
        app_dir = os.path.dirname(exe_path)
        if "Contents/MacOS" in app_dir:
            app_dir = os.path.abspath(os.path.join(app_dir, "../../.."))
            app_dir = os.path.dirname(app_dir)
        return app_dir
    else:
        return os.getcwd()


class ImageSlicerApp:
    # -----------------------------------------------------------------------
    # __init__
    # -----------------------------------------------------------------------
    def __init__(self, root):
        self.root = root
        self.root.title("Image Grid Slicer")
        self.root.geometry("1280x820")
        self.root.resizable(True, True)
        self.root.minsize(950, 600)
        self.root.configure(bg=BG)

        # --- Instance variables ---
        self.original_img             = None
        self.preview_base_img         = None
        self.custom_output_dir        = None
        self.preview_tk               = None
        self.preview_w                = 400
        self.preview_h                = 400
        self.detected_col_groups      = None
        self.detected_row_groups      = None
        self.detected_border_x_val    = None
        self.detected_border_y_val    = None
        self.manual_col_left_offsets  = []
        self.manual_col_right_offsets = []
        self.manual_row_top_offsets   = []
        self.manual_row_bottom_offsets = []
        self.is_auto_detecting        = False
        self.zoom_level               = 1.0
        self.selected_line            = None
        self.animation_frames         = []
        self.animation_frame_order    = []
        self.last_output_dir          = None
        self.bg_image_path            = None
        self.preview_gif_job          = None
        self.drag_start_index         = None
        self.preview_mode             = "grid"
        self.is_playing_anim          = True
        self.is_scrubbing             = False
        self.current_anim_frame_idx   = 1
        self.storyboard_cells         = []
        self.storyboard_photos        = []
        self.dragged_cell_idx         = -1

        # Animation Stabilization variables
        self.stabilize_var             = tk.BooleanVar(value=False)
        self.stabilize_crop_slider_var = tk.DoubleVar(value=0.0)
        self.stabilize_cache           = {}

        # Sprite Extractor variables
        self.extracted_sprite_img     = None
        self.extract_source_var       = tk.StringVar()
        self.extract_mode_var         = tk.StringVar(value="color")
        self.extract_bg_var           = tk.StringVar()
        self.extract_color_var        = tk.StringVar(value="#ffffff")
        self.extract_tol_var          = tk.DoubleVar(value=30.0)

        self.current_theme            = DEFAULT_THEME

        # Apply style
        self.apply_style()

        # Root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main paned window (horizontal split)
        self.paned = tk.PanedWindow(
            self.root, orient=tk.HORIZONTAL,
            bg=BG, sashwidth=6, sashrelief=tk.FLAT,
            sashpad=2, relief=tk.FLAT, bd=0
        )
        self.paned.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self._build_left_panel()
        self._build_right_panel()

        # Configure pane weights: left fixed, right expands
        self.paned.paneconfig(self.left_outer, minsize=350, stretch="never")
        self.paned.paneconfig(self.right_outer, minsize=400, stretch="always")

        # Variable traces
        self.bind_trace(self.cols_var,        self.on_grid_dim_changed)
        self.bind_trace(self.rows_var,        self.on_grid_dim_changed)
        self.bind_trace(self.border_x_var,    self.on_grid_dim_changed)
        self.bind_trace(self.border_y_var,    self.on_grid_dim_changed)
        self.bind_trace(self.border_type_var, self.on_grid_dim_changed)

        # Canvas bindings
        self.canvas.bind("<MouseWheel>",    self.on_zoom)
        self.canvas.bind("<Button-4>",      self.on_zoom)
        self.canvas.bind("<Button-5>",      self.on_zoom)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>",     self.on_pan_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.draw_placeholder()

    # -----------------------------------------------------------------------
    # THEME & STYLES (Light Mode & Dark Mode)
    # -----------------------------------------------------------------------
    def toggle_theme(self):
        new_mode = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_mode)

    def apply_theme(self, mode):
        global BG, SURFACE, CARD, ACCENT, ACCENT2, TEXT, SUBTEXT, GREEN, BORDER, CANVAS_BG
        self.current_theme = mode
        pal = DARK_PALETTE if mode == "dark" else LIGHT_PALETTE
        BG        = pal["BG"]
        SURFACE   = pal["SURFACE"]
        CARD      = pal["CARD"]
        ACCENT    = pal["ACCENT"]
        ACCENT2   = pal["ACCENT2"]
        TEXT      = pal["TEXT"]
        SUBTEXT   = pal["SUBTEXT"]
        GREEN     = pal["GREEN"]
        BORDER    = pal["BORDER"]
        CANVAS_BG = pal["CANVAS_BG"]

        self.apply_style()
        self.update_widget_colors()
        if hasattr(self, "theme_btn"):
            self.theme_btn.config(text="☀️ Light" if mode == "dark" else "🌙 Dark")
        save_user_theme(mode)
        self.update_preview()

    def update_widget_colors(self):
        self.root.configure(bg=BG)
        self.paned.configure(bg=BG)
        self.canvas.configure(bg=CANVAS_BG)
        self.canvas_container.configure(bg=CANVAS_BG)

        def _recolor(w):
            cls = w.winfo_class()
            try:
                if cls == "Frame":
                    curr = w.cget("bg")
                    if curr in (LIGHT_PALETTE["CARD"], DARK_PALETTE["CARD"]):
                        w.configure(bg=CARD)
                    elif curr in (LIGHT_PALETTE["SURFACE"], DARK_PALETTE["SURFACE"]):
                        w.configure(bg=SURFACE)
                    else:
                        w.configure(bg=BG)
                elif cls == "Label":
                    curr = w.cget("bg")
                    curr_fg = w.cget("fg")
                    if curr in (LIGHT_PALETTE["CARD"], DARK_PALETTE["CARD"]):
                        w.configure(bg=CARD)
                    elif curr in (LIGHT_PALETTE["SURFACE"], DARK_PALETTE["SURFACE"]):
                        w.configure(bg=SURFACE)
                    else:
                        w.configure(bg=BG)
                    if curr_fg in (LIGHT_PALETTE["ACCENT"], DARK_PALETTE["ACCENT"]):
                        w.configure(fg=ACCENT)
                    elif curr_fg in (LIGHT_PALETTE["SUBTEXT"], DARK_PALETTE["SUBTEXT"]):
                        w.configure(fg=SUBTEXT)
                    elif curr_fg in (LIGHT_PALETTE["GREEN"], DARK_PALETTE["GREEN"]):
                        w.configure(fg=GREEN)
                    else:
                        w.configure(fg=TEXT)
                elif cls == "Entry":
                    w.configure(bg=CARD if self.current_theme == "dark" else SURFACE,
                                fg=TEXT, insertbackground=TEXT,
                                highlightbackground=BORDER, highlightcolor=ACCENT)
                elif cls == "Listbox":
                    w.configure(bg=SURFACE, fg=TEXT, selectbackground=ACCENT)
                elif cls == "Radiobutton":
                    w.configure(bg=BG if w.cget("bg") in (LIGHT_PALETTE["BG"], DARK_PALETTE["BG"]) else CARD,
                                fg=TEXT, activebackground=BG, activeforeground=ACCENT)
                elif cls == "Checkbutton":
                    w.configure(bg=CARD, fg=TEXT, activebackground=CARD, activeforeground=ACCENT)
                elif cls == "Scale":
                    w.configure(bg=CARD, fg=TEXT, troughcolor=SURFACE, activebackground=ACCENT)
                elif cls == "Canvas" and w != self.canvas:
                    w.configure(bg=BG)
            except Exception:
                pass
            for child in w.winfo_children():
                _recolor(child)

        _recolor(self.root)

    def apply_style(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame",            background=BG)
        self.style.configure("TLabel",            background=BG, foreground=TEXT)
        self.style.configure("TButton",           background=CARD if self.current_theme == "dark" else "#ffffff",
                                                  foreground=TEXT, bordercolor=BORDER, focuscolor=ACCENT, padding=6)
        self.style.map("TButton",                 background=[("active", BORDER if self.current_theme == "light" else ACCENT2),
                                                              ("pressed", CARD if self.current_theme == "light" else ACCENT)],
                                                  foreground=[("active", TEXT if self.current_theme == "light" else "white")])
        self.style.configure("Accent.TButton",    background=ACCENT, foreground="white",
                                                  font=("Helvetica", 10, "bold"), padding=8, bordercolor=ACCENT)
        self.style.map("Accent.TButton",          background=[("active", "#005ecb" if self.current_theme == "light" else "#d6304d"),
                                                              ("pressed", "#004b9b" if self.current_theme == "light" else "#b8243c")],
                                                  foreground=[("active", "white")])
        self.style.configure("Stop.TButton",      background="#ff3b30", foreground="white",
                                                  font=("Helvetica", 9, "bold"), padding=6)
        self.style.map("Stop.TButton",            background=[("active", "#ff453a"), ("pressed", "#d6241a")])
        self.style.configure("Secondary.TButton", background=ACCENT2, foreground="white", padding=6)
        self.style.map("Secondary.TButton",       background=[("active", "#4745ab" if self.current_theme == "light" else "#6c45ab")])
        self.style.configure("TEntry",            fieldbackground=CARD if self.current_theme == "dark" else "#ffffff",
                                                  foreground=TEXT, insertcolor=TEXT, bordercolor=BORDER)
        self.style.configure("TNotebook",         background=BG, bordercolor=BORDER)
        self.style.configure("TNotebook.Tab",     background=CARD if self.current_theme == "dark" else "#e5e5ea",
                                                  foreground=TEXT, padding=[12, 6])
        self.style.map("TNotebook.Tab",           background=[("selected", SURFACE if self.current_theme == "light" else ACCENT)],
                                                  foreground=[("selected", ACCENT if self.current_theme == "light" else "white")])
        self.style.configure("TScrollbar",        background=CARD if self.current_theme == "dark" else "#ffffff",
                                                  troughcolor=BG, bordercolor=BORDER, arrowcolor=TEXT)
        self.style.configure("TSpinbox",          fieldbackground=CARD if self.current_theme == "dark" else "#ffffff",
                                                  foreground=TEXT, bordercolor=BORDER, arrowcolor=TEXT)
        self.style.configure("TLabelframe",       background=BG, bordercolor=BORDER)
        self.style.configure("TLabelframe.Label", background=BG, foreground=ACCENT)
        self.style.configure("TRadiobutton",      background=BG, foreground=TEXT)
        self.style.configure("TCheckbutton",      background=BG, foreground=TEXT)
        self.style.configure("TSeparator",        background=BORDER)

    # -----------------------------------------------------------------------
    # BUILD LEFT PANEL (scrollable)
    # -----------------------------------------------------------------------
    def _build_left_panel(self):
        self.left_outer = tk.Frame(self.paned, bg=BG, width=375)
        self.left_outer.pack_propagate(False)
        self.paned.add(self.left_outer, minsize=350)

        scroll_canvas = tk.Canvas(self.left_outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.left_outer, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(scroll_canvas, bg=BG)
        scroll_win = scroll_canvas.create_window((0, 0), window=self.left_frame, anchor="nw")

        def _on_frame_cfg(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def _on_canvas_cfg(event):
            scroll_canvas.itemconfig(scroll_win, width=event.width)

        self.left_frame.bind("<Configure>", _on_frame_cfg)
        scroll_canvas.bind("<Configure>",   _on_canvas_cfg)

        def _mw(event):
            if event.num == 4:
                scroll_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                scroll_canvas.yview_scroll(1, "units")
            else:
                scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        for w in (scroll_canvas, self.left_frame):
            w.bind("<MouseWheel>", _mw)
            w.bind("<Button-4>",   _mw)
            w.bind("<Button-5>",   _mw)

        # Title
        tk.Label(self.left_frame, text="Image Grid Slicer",
                 bg=BG, fg=TEXT, font=("Helvetica", 15, "bold")
                 ).pack(fill=tk.X, padx=14, pady=(14, 2))
        tk.Frame(self.left_frame, bg=ACCENT, height=2).pack(fill=tk.X, padx=14, pady=(0, 8))

        # Notebook with 3 tabs
        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 8))

        self.tab_slice    = tk.Frame(self.notebook, bg=BG)
        self.tab_animate  = tk.Frame(self.notebook, bg=BG)
        self.tab_extract  = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_slice,    text="✂ Slice")
        self.notebook.add(self.tab_animate,  text="🎬 Animate")
        self.notebook.add(self.tab_extract,  text="🧪 Extract")

        self._build_slice_tab(self.tab_slice)
        self._build_animate_tab(self.tab_animate)
        self._build_extract_tab(self.tab_extract)

        # Recursively bind MouseWheel events to all children of self.notebook
        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", _mw, add="+")
            widget.bind("<Button-4>", _mw, add="+")
            widget.bind("<Button-5>", _mw, add="+")
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        bind_mousewheel_recursive(self.notebook)

    # -----------------------------------------------------------------------
    # WIDGET HELPERS
    # -----------------------------------------------------------------------
    def _section_label(self, parent, text):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, padx=12, pady=(10, 2))
        tk.Label(f, text=text, bg=BG, fg=ACCENT,
                 font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        tk.Frame(f, bg=BORDER, height=1).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=4)

    def _dark_entry(self, parent, textvariable, width=12, state="normal"):
        return tk.Entry(
            parent, textvariable=textvariable, width=width,
            bg=CARD if self.current_theme == "dark" else SURFACE,
            fg=TEXT, insertbackground=TEXT,
            relief="solid", bd=1, font=("Helvetica", 9),
            highlightthickness=0, highlightbackground=BORDER,
            highlightcolor=ACCENT, state=state,
            disabledbackground=CARD if self.current_theme == "dark" else "#e5e5ea",
            disabledforeground=SUBTEXT
        )

    def _dark_btn(self, parent, text, command, bg=None, fg=None,
                  font=None, padx=None, pady=None, default=None, style=None):
        btn_style = style or "TButton"
        if default == "active" or bg == ACCENT:
            btn_style = "Accent.TButton"
        elif bg == ACCENT2:
            btn_style = "Secondary.TButton"
        return ttk.Button(parent, text=text, command=command, style=btn_style)

    # -----------------------------------------------------------------------
    # TAB 1: SLICE
    # -----------------------------------------------------------------------
    def _build_slice_tab(self, parent):
        pad = dict(padx=12, pady=4)

        # Input Image
        self._section_label(parent, "Input Image")
        row_f = tk.Frame(parent, bg=BG)
        row_f.pack(fill=tk.X, **pad)
        self.file_path_var = tk.StringVar()
        self._dark_entry(row_f, self.file_path_var, width=26).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._dark_btn(row_f, "Browse…", self.browse_file).pack(
            side=tk.LEFT, padx=(6, 0))
        self._dark_btn(row_f, "Demo", self.load_demo_grid).pack(
            side=tk.LEFT, padx=(4, 0))

        # Grid Dimensions
        self._section_label(parent, "Grid Dimensions")
        dim_f = tk.Frame(parent, bg=BG)
        dim_f.pack(fill=tk.X, **pad)
        tk.Label(dim_f, text="Columns:", bg=BG, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.cols_var = tk.StringVar(value="3")
        self._dark_entry(dim_f, self.cols_var, width=6).grid(
            row=0, column=1, sticky=tk.W, padx=(4, 16), pady=3)
        tk.Label(dim_f, text="Rows:", bg=BG, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=2, sticky=tk.W, pady=3)
        self.rows_var = tk.StringVar(value="3")
        self._dark_entry(dim_f, self.rows_var, width=6).grid(
            row=0, column=3, sticky=tk.W, padx=(4, 0), pady=3)

        # Auto-detect button
        self._dark_btn(parent, "⚡ Auto-Detect Grid & Borders",
                       self.auto_detect_borders,
                       default="active"
                       ).pack(fill=tk.X, padx=12, pady=(8, 4), ipady=3)

        # Border Crop Settings
        self._section_label(parent, "Border Crop Settings")
        bdr_f = tk.Frame(parent, bg=BG)
        bdr_f.pack(fill=tk.X, **pad)
        tk.Label(bdr_f, text="Border X (px):", bg=BG, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.border_x_var = tk.StringVar(value="0")
        self._dark_entry(bdr_f, self.border_x_var, width=6).grid(
            row=0, column=1, sticky=tk.W, padx=(4, 16), pady=3)
        tk.Label(bdr_f, text="Border Y (px):", bg=BG, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=2, sticky=tk.W, pady=3)
        self.border_y_var = tk.StringVar(value="0")
        self._dark_entry(bdr_f, self.border_y_var, width=6).grid(
            row=0, column=3, sticky=tk.W, padx=(4, 0), pady=3)

        tk.Label(parent, text="Border Layout:", bg=BG, fg=TEXT,
                 font=("Helvetica", 9)).pack(anchor=tk.W, padx=12, pady=(6, 2))
        self.border_type_var = tk.StringVar(value="all")
        radio_f = tk.Frame(parent, bg=BG)
        radio_f.pack(fill=tk.X, padx=20, pady=2)
        for lbl, val in [("Between cells only (no outer edges)", "between"),
                         ("Around all cells (includes outer edges)", "all")]:
            tk.Radiobutton(radio_f, text=lbl, variable=self.border_type_var, value=val,
                           bg=BG, fg=TEXT, selectcolor=CARD,
                           activebackground=BG, activeforeground=ACCENT,
                           font=("Helvetica", 9)).pack(anchor=tk.W, pady=1)

        # Compat booleans (used internally by slice logic)
        self.border_top_var    = tk.BooleanVar(value=True)
        self.border_bottom_var = tk.BooleanVar(value=True)
        self.border_left_var   = tk.BooleanVar(value=True)
        self.border_right_var  = tk.BooleanVar(value=True)

        # Output Folder
        self._section_label(parent, "Output Folder")
        out_f = tk.Frame(parent, bg=BG)
        out_f.pack(fill=tk.X, **pad)
        self.output_dir_var = tk.StringVar(value="[sliced-images/ in app directory]")
        self._dark_entry(out_f, self.output_dir_var, width=26, state="disabled").pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._dark_btn(out_f, "Change…", self.browse_output_dir).pack(
            side=tk.LEFT, padx=(6, 0))

        # File & Folder Naming
        self._section_label(parent, "File & Folder Naming")
        name_card = tk.Frame(parent, bg=CARD, padx=10, pady=8)
        name_card.pack(fill=tk.X, padx=12, pady=4)
        name_card.columnconfigure(1, weight=1)

        tk.Label(name_card, text="Folder Name:", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.subfolder_var = tk.StringVar(value="{filename}_sliced")
        self._dark_entry(name_card, self.subfolder_var, width=20).grid(
            row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        tk.Label(name_card, text="File Prefix:", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.prefix_var = tk.StringVar(value="{filename}_")
        self._dark_entry(name_card, self.prefix_var, width=20).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=3)

        tk.Label(name_card, text="Scheme:", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=2, column=0, sticky=tk.W, pady=3)
        self.naming_scheme_var = tk.StringVar(value="sequential")
        sc_f = tk.Frame(name_card, bg=CARD)
        sc_f.grid(row=2, column=1, sticky=tk.W, padx=(8, 0), pady=3)
        for lbl, val in [("Row/Col  (prefix_1_2.png)", "row_col"),
                         ("Sequential  (prefix_01.png)", "sequential")]:
            tk.Radiobutton(sc_f, text=lbl, variable=self.naming_scheme_var, value=val,
                           bg=CARD, fg=TEXT, selectcolor=SURFACE,
                           activebackground=CARD, activeforeground=ACCENT,
                           font=("Helvetica", 9)).pack(anchor=tk.W)

        # Slice button
        tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=(12, 8))
        self._dark_btn(parent, "✂  Slice Image", self.slice_image,
                       default="active"
                       ).pack(fill=tk.X, padx=12, pady=(0, 6), ipady=6)

        self.status_label = tk.Label(
            parent, text="Select an image file to begin.",
            bg=BG, fg=SUBTEXT, font=("Helvetica", 9, "italic"),
            wraplength=300, justify=tk.LEFT
        )
        self.status_label.pack(anchor=tk.W, padx=12, pady=(2, 14))

    # -----------------------------------------------------------------------
    # TAB 2: ANIMATE
    # -----------------------------------------------------------------------
    def _build_animate_tab(self, parent):
        pad = dict(padx=12, pady=4)

        # Frame Order
        self._section_label(parent, "Frame Order")
        list_card = tk.Frame(parent, bg=CARD, padx=8, pady=8)
        list_card.pack(fill=tk.X, **pad)
        lb_scroll = ttk.Scrollbar(list_card, orient=tk.VERTICAL)
        self.frame_listbox = tk.Listbox(
            list_card, bg=SURFACE, fg=TEXT,
            selectbackground=ACCENT, selectforeground="white",
            font=("Helvetica", 9), relief="flat",
            highlightthickness=0, activestyle="none", height=8,
            yscrollcommand=lb_scroll.set
        )
        lb_scroll.config(command=self.frame_listbox.yview)
        lb_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.frame_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.frame_listbox.bind("<ButtonPress-1>",   self.on_frame_drag_start)
        self.frame_listbox.bind("<ButtonRelease-1>", self.on_frame_drag_release)

        self._dark_btn(parent, "📂 Load Frames from Folder",
                       self.load_frames_for_animation
                       ).pack(fill=tk.X, padx=12, pady=(4, 2), ipady=2)

        order_grid = tk.Frame(parent, bg=BG)
        order_grid.pack(fill=tk.X, **pad)
        order_grid.columnconfigure((0, 1, 2), weight=1)
        
        buttons = [
            ("▲ Move Up", self.move_frame_up),
            ("▼ Move Down", self.move_frame_down),
            ("🗑 Delete", self.delete_selected_frame),
            ("⇅ Reverse", self.reverse_frame_order),
            ("↺ Reset", self.reset_frame_order),
            ("❌ Clear All", self.clear_animation_frames)
        ]
        
        for idx, (lbl, cmd) in enumerate(buttons):
            r = idx // 3
            c = idx % 3
            ttk.Button(order_grid, text=lbl, command=cmd).grid(
                row=r, column=c, padx=2, pady=2, sticky="ew"
            )

        # Stabilization & Framing
        self._section_label(parent, "Stabilization & Framing")
        stab_card = tk.Frame(parent, bg=CARD, padx=10, pady=8)
        stab_card.pack(fill=tk.X, **pad)
        
        top_row = tk.Frame(stab_card, bg=CARD)
        top_row.pack(fill=tk.X, pady=(0, 4))
        
        self.stab_cb = tk.Checkbutton(
            top_row, text="Stabilize & Match Aspect",
            variable=self.stabilize_var,
            bg=CARD, fg=TEXT, selectcolor=SURFACE,
            activebackground=CARD, activeforeground=ACCENT,
            font=("Helvetica", 9, "bold"),
            command=self.on_stabilize_toggled
        )
        self.stab_cb.pack(side=tk.LEFT)
        
        self.auto_stab_btn = ttk.Button(
            top_row, text="⚡ Auto-Align",
            command=self.run_auto_stabilization,
            style="Accent.TButton"
        )
        self.auto_stab_btn.pack(side=tk.RIGHT)
        
        slider_label_row = tk.Frame(stab_card, bg=CARD)
        slider_label_row.pack(fill=tk.X, pady=(4, 2))
        tk.Label(
            slider_label_row, text="Crop Level:",
            bg=CARD, fg=TEXT, font=("Helvetica", 9)
        ).pack(side=tk.LEFT)
        
        self.crop_level_label = tk.Label(
            slider_label_row, text="Min Crop (0% extra)",
            bg=CARD, fg=SUBTEXT, font=("Helvetica", 8, "bold")
        )
        self.crop_level_label.pack(side=tk.RIGHT)
        
        self.stab_scale = tk.Scale(
            stab_card, from_=0.0, to=50.0, resolution=1.0,
            orient=tk.HORIZONTAL, showvalue=0,
            variable=self.stabilize_crop_slider_var,
            bg=CARD, fg=TEXT, troughcolor=SURFACE,
            highlightthickness=0, bd=0, activebackground=ACCENT,
            command=self.on_stabilize_slider_changed
        )
        self.stab_scale.pack(fill=tk.X, pady=(0, 2))
        
        min_max_row = tk.Frame(stab_card, bg=CARD)
        min_max_row.pack(fill=tk.X)
        tk.Label(min_max_row, text="Min (Aspect Match)", bg=CARD, fg=SUBTEXT, font=("Helvetica", 7)).pack(side=tk.LEFT)
        tk.Label(min_max_row, text="Tighter Crop (+50%)", bg=CARD, fg=SUBTEXT, font=("Helvetica", 7)).pack(side=tk.RIGHT)
        
        self.stab_info_label = tk.Label(
            stab_card, text="Loads frames to detect and align object motion.",
            bg=CARD, fg=SUBTEXT, font=("Helvetica", 8),
            wraplength=290, justify=tk.LEFT
        )
        self.stab_info_label.pack(fill=tk.X, pady=(4, 4))
        
        self._dark_btn(
            stab_card, "💾 Save Stabilized Frames…",
            self.save_stabilized_frames_dialog
        ).pack(fill=tk.X, pady=(2, 0))

        # Timing
        self._section_label(parent, "Timing")
        timing_card = tk.Frame(parent, bg=CARD, padx=10, pady=8)
        timing_card.pack(fill=tk.X, **pad)
        timing_card.columnconfigure(1, weight=1)
        tk.Label(timing_card, text="Frame Delay (ms):", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=0, column=0, sticky=tk.W, pady=3)
        self.frame_delay_var = tk.StringVar(value="100")
        tk.Spinbox(timing_card, from_=20, to=5000, increment=10,
                   textvariable=self.frame_delay_var,
                   bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                   buttonbackground=CARD, relief="flat",
                   font=("Helvetica", 9), width=8
                   ).grid(row=0, column=1, sticky=tk.W, padx=(8, 0), pady=3)
        tk.Label(timing_card, text="Loop Count (0=infinite):", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.loop_count_var = tk.StringVar(value="0")
        tk.Spinbox(timing_card, from_=0, to=99, increment=1,
                   textvariable=self.loop_count_var,
                   bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                   buttonbackground=CARD, relief="flat",
                   font=("Helvetica", 9), width=8
                   ).grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=3)

        # Background & Sprites
        self._section_label(parent, "Background & Sprites")
        bg_card = tk.Frame(parent, bg=CARD, padx=10, pady=8)
        bg_card.pack(fill=tk.X, **pad)
        bg_card.columnconfigure(1, weight=1)
        
        self.use_bg_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bg_card, text="Use Background Frame",
                       variable=self.use_bg_var,
                       bg=CARD, fg=TEXT, selectcolor=SURFACE,
                       activebackground=CARD, activeforeground=ACCENT,
                       font=("Helvetica", 9),
                       command=self.update_preview
                       ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
                       
        tk.Label(bg_card, text="Background Frame Index:",
                 bg=CARD, fg=TEXT, font=("Helvetica", 9)
                 ).grid(row=1, column=0, sticky=tk.W, pady=3)
                 
        self.bg_frame_index_var = tk.StringVar(value="1")
        bg_spin = tk.Spinbox(bg_card, from_=1, to=999, increment=1,
                    textvariable=self.bg_frame_index_var,
                    bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                    buttonbackground=CARD, relief="flat",
                    font=("Helvetica", 9), width=6,
                    command=self.update_preview
                    )
        bg_spin.grid(row=1, column=1, sticky=tk.W, padx=(8, 0), pady=3)
        bg_spin.bind("<KeyRelease>", lambda e: self.update_preview())
        tk.Label(bg_card,
                 text="Sprites are composited on the background per frame.",
                 bg=CARD, fg=SUBTEXT, font=("Helvetica", 8, "italic"),
                 wraplength=280, justify=tk.LEFT
                 ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))

        # Export Section
        self._section_label(parent, "Export GIF")
        gif_out_f = tk.Frame(parent, bg=BG)
        gif_out_f.pack(fill=tk.X, **pad)
        self.gif_output_path_var = tk.StringVar(value="")
        self._dark_entry(gif_out_f, self.gif_output_path_var, width=22).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._dark_btn(gif_out_f, "…", self.browse_gif_output, padx=6).pack(
            side=tk.LEFT, padx=(6, 0))

        self.preview_gif_btn = self._dark_btn(
            parent, "▶ Preview GIF", self.toggle_gif_preview
        )
        self.preview_gif_btn.pack(fill=tk.X, padx=12, pady=(6, 2), ipady=2)

        self._dark_btn(parent, "🎬  Export GIF", self.export_gif,
                       default="active"
                       ).pack(fill=tk.X, padx=12, pady=(4, 14), ipady=5)

    # -----------------------------------------------------------------------
    # TAB 3: SETTINGS
    # -----------------------------------------------------------------------
    def _build_extract_tab(self, parent):
        pad = dict(padx=12, pady=4)
        
        # Source Image Section
        self._section_label(parent, "Source Image (Frame)")
        row_f = tk.Frame(parent, bg=BG)
        row_f.pack(fill=tk.X, **pad)
        self._dark_entry(row_f, self.extract_source_var, width=26).pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._dark_btn(row_f, "Browse…", self.browse_extract_source).pack(
            side=tk.LEFT, padx=(6, 0))
            
        # Key Mode Section
        self._section_label(parent, "Keying Mode")
        mode_frame = tk.Frame(parent, bg=BG)
        mode_frame.pack(fill=tk.X, **pad)
        
        r1 = ttk.Radiobutton(mode_frame, text="Solid Color Key", variable=self.extract_mode_var, value="color", command=self.on_extract_mode_changed)
        r1.pack(side=tk.LEFT, padx=(0, 20))
        r2 = ttk.Radiobutton(mode_frame, text="Difference Key", variable=self.extract_mode_var, value="diff", command=self.on_extract_mode_changed)
        r2.pack(side=tk.LEFT)
        
        # Color Key Panel (Container)
        self.color_key_container = tk.Frame(parent, bg=BG)
        self.color_key_container.pack(fill=tk.X, **pad)
        
        tk.Label(self.color_key_container, text="Key Color:", bg=BG, fg=TEXT, font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(0, 6))
        self.color_entry = self._dark_entry(self.color_key_container, self.extract_color_var, width=10)
        self.color_entry.pack(side=tk.LEFT, padx=(0, 6))
        
        self._dark_btn(self.color_key_container, "Pick Color…", self.pick_key_color).pack(side=tk.LEFT)
        
        # Difference Key Panel (Container)
        self.diff_key_container = tk.Frame(parent, bg=BG)
        
        tk.Label(self.diff_key_container, text="Reference BG:", bg=BG, fg=TEXT, font=("Helvetica", 9)).pack(side=tk.LEFT, padx=(0, 6))
        self._dark_entry(self.diff_key_container, self.extract_bg_var, width=18).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self._dark_btn(self.diff_key_container, "Browse…", self.browse_extract_bg).pack(side=tk.LEFT, padx=(6, 0))
        
        # Settings Card
        self._section_label(parent, "Settings")
        settings_card = tk.Frame(parent, bg=CARD, padx=14, pady=14)
        settings_card.pack(fill=tk.X, padx=12, pady=(8, 8))
        
        # Tolerance Slider
        tol_row = tk.Frame(settings_card, bg=CARD)
        tol_row.pack(fill=tk.X, pady=4)
        tk.Label(tol_row, text="Color Tolerance (1-255):", bg=CARD, fg=TEXT, font=("Helvetica", 9)).pack(side=tk.LEFT)
        
        self.tol_scale = tk.Scale(
            settings_card, from_=1, to=255, orient=tk.HORIZONTAL,
            variable=self.extract_tol_var, bg=CARD, fg=TEXT,
            highlightbackground=CARD, activebackground=ACCENT,
            troughcolor=BG, relief="flat", font=("Helvetica", 9)
        )
        self.tol_scale.pack(fill=tk.X, pady=(0, 8))
        
        # Action Buttons
        self._section_label(parent, "Actions")
        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill=tk.X, **pad)
        
        self._dark_btn(btn_row, "👀 Preview Sprite", self.preview_extracted_sprite).pack(fill=tk.X, pady=4)
        self._dark_btn(btn_row, "💾 Save Sprite (PNG)", self.save_extracted_sprite, default="active").pack(fill=tk.X, pady=4)
        
        self.on_extract_mode_changed()

    def on_extract_mode_changed(self):
        mode = self.extract_mode_var.get()
        if mode == "color":
            self.diff_key_container.pack_forget()
            self.color_key_container.pack(fill=tk.X, padx=12, pady=4)
        else:
            self.color_key_container.pack_forget()
            self.diff_key_container.pack(fill=tk.X, padx=12, pady=4)

    def browse_extract_source(self):
        filename = filedialog.askopenfilename(
            title="Select Source Frame Image",
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                       ("All files", "*.*")),
            initialdir=os.getcwd()
        )
        if filename:
            self.extract_source_var.set(filename)
            
    def browse_extract_bg(self):
        filename = filedialog.askopenfilename(
            title="Select Reference Background Image",
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                       ("All files", "*.*")),
            initialdir=os.getcwd()
        )
        if filename:
            self.extract_bg_var.set(filename)
            
    def pick_key_color(self):
        from tkinter import colorchooser
        color_code = colorchooser.askcolor(title="Choose Key Color")
        if color_code and color_code[1]:
            self.extract_color_var.set(color_code[1])

    # -----------------------------------------------------------------------
    # BUILD RIGHT PANEL
    # -----------------------------------------------------------------------
    def _build_right_panel(self):
        self.right_outer = tk.Frame(self.paned, bg=BG)
        self.paned.add(self.right_outer, minsize=400)
        self.right_outer.columnconfigure(0, weight=1)
        self.right_outer.rowconfigure(1, weight=1)
        self.right_outer.rowconfigure(0, weight=0)
        self.right_outer.rowconfigure(2, weight=0)

        # Header strip
        header = tk.Frame(self.right_outer, bg=SURFACE, height=34)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="Live Preview",
                 bg=SURFACE, fg=TEXT, font=("Helvetica", 11, "bold")
                 ).pack(side=tk.LEFT, padx=14, pady=6)

        self.theme_btn = ttk.Button(
            header,
            text="☀️ Light" if self.current_theme == "dark" else "🌙 Dark",
            command=self.toggle_theme,
            width=8
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=10, pady=4)

        # Canvas container
        self.canvas_container = tk.Frame(self.right_outer, bg=CANVAS_BG)
        self.canvas_container.grid(row=1, column=0, sticky="nsew")
        self.canvas_container.rowconfigure(0, weight=1)
        self.canvas_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.canvas_container, bg=CANVAS_BG, bd=0, highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_container.bind("<Configure>", self.on_canvas_resize)

        # Bottom bar
        self.bottom_bar = tk.Frame(self.right_outer, bg=SURFACE, height=36)
        self.bottom_bar.grid(row=2, column=0, sticky="ew")
        self.bottom_bar.columnconfigure(0, weight=1)
        self.hint_label = tk.Label(
            self.bottom_bar,
            text="💡 Scroll to Zoom • Drag to Pan • Click divider line to nudge",
            bg=SURFACE, fg=SUBTEXT, font=("Helvetica", 8, "italic")
        )
        self.hint_label.grid(row=0, column=0, sticky=tk.W, padx=10)
        for col_i, (txt, cmd) in enumerate(
            [(" − ", self.zoom_out), (" + ", self.zoom_in), ("⌂", self.zoom_reset)], 1
        ):
            ttk.Button(self.bottom_bar, text=txt, command=cmd, width=4
                       ).grid(row=0, column=col_i, padx=(2, 4), pady=4)

        # Timeline bar (hidden by default)
        self.timeline_frame = tk.Frame(self.right_outer, bg=SURFACE, height=36)
        self.timeline_frame.columnconfigure(1, weight=1)
        
        self.play_pause_btn = ttk.Button(self.timeline_frame, text="⏸", command=self.toggle_play_pause, width=3)
        self.play_pause_btn.grid(row=0, column=0, padx=6, pady=4)
        
        self.timeline_slider_var = tk.DoubleVar(value=1.0)
        self.timeline_slider = tk.Scale(
            self.timeline_frame, from_=1.0, to=1.0, orient=tk.HORIZONTAL,
            variable=self.timeline_slider_var, command=self.on_timeline_slide,
            bg=SURFACE, fg=TEXT, highlightthickness=0, bd=0, troughcolor=CARD,
            activebackground=ACCENT, showvalue=False
        )
        self.timeline_slider.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        self.timeline_slider.bind("<ButtonPress-1>", lambda e: self.on_slider_press())
        self.timeline_slider.bind("<ButtonRelease-1>", lambda e: self.on_slider_release())
        
        self.range_start_var = tk.StringVar(value="1")
        self.range_end_var = tk.StringVar(value="1")
        
        range_f = tk.Frame(self.timeline_frame, bg=SURFACE)
        range_f.grid(row=0, column=2, padx=6, pady=4)
        
        tk.Label(range_f, text="Range:", bg=SURFACE, fg=TEXT, font=("Helvetica", 9)).pack(side=tk.LEFT)
        
        self.range_start_spin = tk.Spinbox(
            range_f, from_=1, to=1, increment=1, width=4,
            textvariable=self.range_start_var, command=self.on_range_changed,
            bg=SURFACE, fg=TEXT, buttonbackground=CARD, relief="flat"
        )
        self.range_start_spin.pack(side=tk.LEFT, padx=2)
        self.range_start_spin.bind("<KeyRelease>", lambda e: self.on_range_changed())
        
        tk.Label(range_f, text="to", bg=SURFACE, fg=TEXT, font=("Helvetica", 9)).pack(side=tk.LEFT, padx=2)
        
        self.range_end_spin = tk.Spinbox(
            range_f, from_=1, to=1, increment=1, width=4,
            textvariable=self.range_end_var, command=self.on_range_changed,
            bg=SURFACE, fg=TEXT, buttonbackground=CARD, relief="flat"
        )
        self.range_end_spin.pack(side=tk.LEFT, padx=2)
        self.range_end_spin.bind("<KeyRelease>", lambda e: self.on_range_changed())
        
        self.frame_counter_lbl = tk.Label(
            self.timeline_frame, text="Frame 1 / 1",
            bg=SURFACE, fg=SUBTEXT, font=("Helvetica", 9, "italic")
        )
        self.frame_counter_lbl.grid(row=0, column=3, padx=10, pady=4)

    # -----------------------------------------------------------------------
    # TRACE / GRID DIM CHANGED
    # -----------------------------------------------------------------------
    def bind_trace(self, var, callback):
        if hasattr(var, "trace_add"):
            var.trace_add("write", lambda *args: callback())
        else:
            var.trace("w", lambda *args: callback())

    def on_grid_dim_changed(self):
        if not getattr(self, "is_auto_detecting", False):
            self.detected_col_groups       = None
            self.detected_row_groups       = None
            self.detected_border_x_val     = None
            self.detected_border_y_val     = None
            self.manual_col_left_offsets   = []
            self.manual_col_right_offsets  = []
            self.manual_row_top_offsets    = []
            self.manual_row_bottom_offsets = []
            self.selected_line = None
        self.update_preview()

    # -----------------------------------------------------------------------
    # PLACEHOLDER
    # -----------------------------------------------------------------------
    def draw_placeholder(self):
        self.canvas.delete("all")
        cw = max(500, self.canvas.winfo_width())
        ch = max(450, self.canvas.winfo_height())
        self.canvas.config(scrollregion=(0, 0, cw, ch))

        cx, cy = cw // 2, ch // 2
        card_w, card_h = 480, 290
        x1, y1 = cx - card_w // 2, cy - card_h // 2
        x2, y2 = cx + card_w // 2, cy + card_h // 2

        # Card shadow
        shadow_fill = "#c7c7cc" if self.current_theme == "light" else "#0a0a14"
        self.canvas.create_rectangle(
            x1 + 4, y1 + 4, x2 + 4, y2 + 4,
            fill=shadow_fill, outline=""
        )

        # Main Card surface
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=SURFACE, outline=BORDER, width=2
        )

        # Top Accent Stripe
        self.canvas.create_rectangle(
            x1, y1, x2, y1 + 5,
            fill=ACCENT, outline=""
        )

        # Title & Subtitle
        self.canvas.create_text(
            cx, y1 + 42,
            text="Image Grid Slicer",
            fill=TEXT, font=("Helvetica", 16, "bold")
        )
        self.canvas.create_text(
            cx, y1 + 70,
            text="Auto grid detection, border cropping, and GIF animation",
            fill=SUBTEXT, font=("Helvetica", 10)
        )

        # Divider line
        self.canvas.create_line(
            x1 + 30, y1 + 90, x2 - 30, y1 + 90,
            fill=BORDER, width=1
        )

        # Quick guide steps
        guide_text = (
            "1. Click 'Browse…' on the left (or below) to select an image\n"
            "2. Click '⚡ Auto-Detect Grid & Borders' to scan cells\n"
            "3. Preview & fine-tune divider lines directly on this canvas\n"
            "4. Click '✂ Slice Image' or switch to '🎬 Animate' for GIF"
        )
        self.canvas.create_text(
            x1 + 40, y1 + 150,
            text=guide_text, anchor="w",
            fill=TEXT, font=("Helvetica", 10), justify=tk.LEFT
        )

        # Direct Browse button and Load Demo Grid button inside placeholder card
        self.placeholder_btn = ttk.Button(
            self.canvas, text="📂  Browse File…",
            command=self.browse_file, style="Accent.TButton"
        )
        self.demo_btn = ttk.Button(
            self.canvas, text="🎮  Load Demo Grid",
            command=self.load_demo_grid
        )
        self.canvas.create_window(cx - 105, y2 - 40, window=self.placeholder_btn, width=170, height=36)
        self.canvas.create_window(cx + 105, y2 - 40, window=self.demo_btn, width=170, height=36)

    # -----------------------------------------------------------------------
    # ZOOM / PAN
    # -----------------------------------------------------------------------
    def on_zoom(self, event):
        if not self.original_img:
            return
        mouse_x  = event.x
        mouse_y  = event.y
        canvas_x = self.canvas.canvasx(mouse_x)
        canvas_y = self.canvas.canvasy(mouse_y)

        w_z_old  = int(self.preview_w * self.zoom_level)
        h_z_old  = int(self.preview_h * self.zoom_level)
        canvas_w = max(self.preview_w, self.canvas.winfo_width())
        canvas_h = max(self.preview_h, self.canvas.winfo_height())
        dx_old   = max(0, (canvas_w - w_z_old) // 2)
        dy_old   = max(0, (canvas_h - h_z_old) // 2)

        rel_x = (canvas_x - dx_old) / w_z_old if w_z_old > 0 else 0.5
        rel_y = (canvas_y - dy_old) / h_z_old if h_z_old > 0 else 0.5

        if event.num == 4 or event.delta > 0:
            self.zoom_level = min(10.0, self.zoom_level * 1.1)
        elif event.num == 5 or event.delta < 0:
            self.zoom_level = max(0.2, self.zoom_level / 1.1)

        w_z_new  = int(self.preview_w * self.zoom_level)
        h_z_new  = int(self.preview_h * self.zoom_level)
        canvas_w = max(self.preview_w, self.canvas.winfo_width())
        canvas_h = max(self.preview_h, self.canvas.winfo_height())
        dx_new   = max(0, (canvas_w - w_z_new) // 2)
        dy_new   = max(0, (canvas_h - h_z_new) // 2)

        canvas_x_new = dx_new + rel_x * w_z_new
        canvas_y_new = dy_new + rel_y * h_z_new

        scroll_w = max(canvas_w, w_z_new)
        scroll_h = max(canvas_h, h_z_new)

        fraction_x = (canvas_x_new - mouse_x) / scroll_w if scroll_w > 0 else 0
        fraction_y = (canvas_y_new - mouse_y) / scroll_h if scroll_h > 0 else 0

        self.canvas.config(scrollregion=(0, 0, scroll_w, scroll_h))
        self.canvas.xview_moveto(max(0.0, min(1.0, fraction_x)))
        self.canvas.yview_moveto(max(0.0, min(1.0, fraction_y)))
        self.update_preview()

    def on_pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def on_pan_drag(self, event):
        if self.preview_mode == "storyboard":
            self.on_storyboard_drag(event)
            return
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.update_preview()

    def zoom_in(self):
        if not self.original_img:
            return
        self.zoom_level = min(10.0, self.zoom_level * 1.2)
        self.update_preview()

    def zoom_out(self):
        if not self.original_img:
            return
        self.zoom_level = max(0.2, self.zoom_level / 1.2)
        self.update_preview()

    def zoom_reset(self):
        if not self.original_img:
            return
        self.zoom_level = 1.0
        self.update_preview()

    def on_canvas_resize(self, event):
        if self.preview_mode == "storyboard":
            self.draw_storyboard_grid()
            return
        if self.preview_mode == "gif":
            self.draw_gif_frame()
            return
        if self.preview_mode == "extract":
            self.draw_extract_preview()
            return
        if self.original_img:
            self.rescale_preview_image()
            self.update_preview()
        else:
            self.draw_placeholder()

    def rescale_preview_image(self):
        if not self.original_img:
            return
        cw = self.canvas_container.winfo_width()
        ch = self.canvas_container.winfo_height()
        if cw < 100: cw = 450
        if ch < 100: ch = 450
        max_w = max(100, cw - 20)
        max_h = max(100, ch - 20)
        W, H  = self.original_img.size
        ratio = min(max_w / W, max_h / H)
        self.preview_w = int(W * ratio)
        self.preview_h = int(H * ratio)
        resample = (Image.Resampling.LANCZOS if hasattr(Image, "Resampling")
                    else Image.ANTIALIAS)
        self.preview_base_img = self.original_img.resize(
            (self.preview_w, self.preview_h), resample)

    # -----------------------------------------------------------------------
    # BROWSE HELPERS
    # -----------------------------------------------------------------------
    def load_file_path(self, filename):
        if not filename:
            return False
        self.file_path_var.set(filename)
        try:
            self.original_img = Image.open(filename)
            self.zoom_level = 1.0
            self.detected_col_groups       = None
            self.detected_row_groups       = None
            self.detected_border_x_val     = None
            self.detected_border_y_val     = None
            self.detected_outer_borders    = None
            self.manual_col_left_offsets   = []
            self.manual_col_right_offsets  = []
            self.manual_row_top_offsets    = []
            self.manual_row_bottom_offsets = []
            self.selected_line = None
            self.rescale_preview_image()
            self.update_preview()
            self.status_label.config(
                text=(f"Loaded: {os.path.basename(filename)} "
                      f"({self.original_img.width}x{self.original_img.height})"),
                fg=GREEN
            )
            if not self.custom_output_dir:
                self.output_dir_var.set("[sliced-images/ in app directory]")
            return True
        except Exception as e:
            self.original_img = None
            self.preview_base_img = None
            self.draw_placeholder()
            messagebox.showerror("Error", f"Failed to load image:\n{e}")
            return False

    def load_demo_grid(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(script_dir, "demo_grid.png"),
            os.path.join(get_app_run_dir(), "demo_grid.png"),
            os.path.join(script_dir, "ChatGPT Image Aug 13, 2026 at 08_52_50 PM.png"),
            os.path.join(get_app_run_dir(), "ChatGPT Image Aug 13, 2026 at 08_52_50 PM.png")
        ]
        for p in candidates:
            if os.path.exists(p):
                if self.load_file_path(p):
                    self.auto_detect_borders()
                return
        messagebox.showinfo("Demo Grid", "demo_grid.png was not found in the application directory.")

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Grid Image to Slice",
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                       ("All files", "*.*")),
            initialdir=os.getcwd()
        )
        if filename:
            self.load_file_path(filename)

    def browse_output_dir(self):
        directory = filedialog.askdirectory(
            title="Select Output Folder", initialdir=os.getcwd())
        if directory:
            self.custom_output_dir = directory
            self.output_dir_var.set(directory)

    def browse_bg_image(self):
        pass

    def browse_gif_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save GIF As…",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")],
            initialdir=self.last_output_dir or os.getcwd()
        )
        if filename:
            self.gif_output_path_var.set(filename)

    # -----------------------------------------------------------------------
    # DRAW CLEAN PREVIEW (no grid)
    # -----------------------------------------------------------------------
    def draw_clean_preview(self):
        if not self.original_img:
            self.draw_placeholder()
            return
        w_z = int(self.preview_w * self.zoom_level)
        h_z = int(self.preview_h * self.zoom_level)
        if self.zoom_level >= 2.0:
            resample = (Image.Resampling.NEAREST if hasattr(Image, "Resampling")
                        else Image.NEAREST)
        else:
            resample = (Image.Resampling.BILINEAR if hasattr(Image, "Resampling")
                        else Image.BILINEAR)
        zoomed = self.original_img.resize((w_z, h_z), resample)
        self.preview_tk = ImageTk.PhotoImage(zoomed)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.preview_tk)
        self.canvas.config(scrollregion=(0, 0, w_z, h_z))

    # -----------------------------------------------------------------------
    # UPDATE PREVIEW
    # -----------------------------------------------------------------------
    def update_preview(self):
        if self.preview_mode == "storyboard":
            self.draw_storyboard_grid()
            return
        if self.preview_mode == "gif":
            self.draw_gif_frame()
            return
        if self.preview_mode == "extract":
            self.draw_extract_preview()
            return
        if not self.original_img:
            self.draw_placeholder()
            return

        try:
            cols     = int(self.cols_var.get().strip())
            rows     = int(self.rows_var.get().strip())
            border_x = int(self.border_x_var.get().strip())
            border_y = int(self.border_y_var.get().strip())
            if cols <= 0 or rows <= 0 or border_x < 0 or border_y < 0:
                raise ValueError()
        except ValueError:
            self.draw_clean_preview()
            return

        W, H        = self.original_img.size
        border_type = self.border_type_var.get()

        self.ensure_grid_groups()

        has_left  = (border_type == "all")
        has_right = (border_type == "all")
        col_bounds = self.get_cells_from_border_groups(
            W, self.detected_col_groups, has_left, has_right, border_x,
            self.manual_col_left_offsets, self.manual_col_right_offsets, is_col=True
        )
        has_top    = (border_type == "all")
        has_bottom = (border_type == "all")
        row_bounds = self.get_cells_from_border_groups(
            H, self.detected_row_groups, has_top, has_bottom, border_y,
            self.manual_row_top_offsets, self.manual_row_bottom_offsets, is_col=False
        )

        self.status_label.config(text="Adjust settings and click Slice Image.", fg=SUBTEXT)

        w_z = int(self.preview_w * self.zoom_level)
        h_z = int(self.preview_h * self.zoom_level)

        canvas_w = max(self.preview_w, self.canvas.winfo_width())
        canvas_h = max(self.preview_h, self.canvas.winfo_height())
        dx = max(0, (canvas_w - w_z) // 2)
        dy = max(0, (canvas_h - h_z) // 2)

        vx0 = self.canvas.canvasx(0)
        vy0 = self.canvas.canvasy(0)
        vx1 = self.canvas.canvasx(canvas_w)
        vy1 = self.canvas.canvasy(canvas_h)

        vis_left   = max(0.0, vx0 - dx)
        vis_top    = max(0.0, vy0 - dy)
        vis_right  = min(float(w_z), vx1 - dx)
        vis_bottom = min(float(h_z), vy1 - dy)

        pad_px = 200
        render_left   = int(max(0.0, vis_left   - pad_px))
        render_top    = int(max(0.0, vis_top    - pad_px))
        render_right  = int(min(float(w_z), vis_right  + pad_px))
        render_bottom = int(min(float(h_z), vis_bottom + pad_px))

        if render_right <= render_left or render_bottom <= render_top:
            render_left   = 0
            render_top    = 0
            render_right  = w_z
            render_bottom = h_z

        scale_x = w_z / W
        scale_y = h_z / H

        orig_left   = int(math.floor(render_left   / scale_x))
        orig_top    = int(math.floor(render_top    / scale_y))
        orig_right  = int(math.ceil( render_right  / scale_x))
        orig_bottom = int(math.ceil( render_bottom / scale_y))

        orig_left   = max(0, min(W, orig_left))
        orig_top    = max(0, min(H, orig_top))
        orig_right  = max(0, min(W, orig_right))
        orig_bottom = max(0, min(H, orig_bottom))

        crop_offset_x = int(round(orig_left  * scale_x))
        crop_offset_y = int(round(orig_top   * scale_y))

        cropped_orig = self.original_img.crop(
            (orig_left, orig_top, orig_right, orig_bottom))
        render_w = int(round(orig_right  * scale_x)) - crop_offset_x
        render_h = int(round(orig_bottom * scale_y)) - crop_offset_y

        if render_w <= 0 or render_h <= 0:
            return

        if self.zoom_level >= 2.0:
            resample = (Image.Resampling.NEAREST  if hasattr(Image, "Resampling")
                        else Image.NEAREST)
        else:
            resample = (Image.Resampling.BILINEAR if hasattr(Image, "Resampling")
                        else Image.BILINEAR)

        zoomed_img      = cropped_orig.resize((render_w, render_h), resample)
        preview_overlay = zoomed_img.convert("RGBA")
        draw            = ImageDraw.Draw(preview_overlay, "RGBA")

        v_lines = set()
        h_lines = set()
        for c in range(cols):
            v_lines.add(col_bounds[c][0])
            v_lines.add(col_bounds[c][1] + 1)
        for r in range(rows):
            h_lines.add(row_bounds[r][0])
            h_lines.add(row_bounds[r][1] + 1)

        for val in v_lines:
            x = int(round(val * scale_x)) - crop_offset_x
            draw.line([(x, 0), (x, render_h)], fill=(0, 255, 136, 200), width=1)
            for y_h in [0, render_h - 1]:
                draw.rectangle([x - 3, y_h - 3, x + 3, y_h + 3],
                                fill=(0, 255, 136, 220))

        for val in h_lines:
            y = int(round(val * scale_y)) - crop_offset_y
            draw.line([(0, y), (render_w, y)], fill=(0, 255, 136, 200), width=1)
            for x_h in [0, render_w - 1]:
                draw.rectangle([x_h - 3, y - 3, x_h + 3, y + 3],
                                fill=(0, 255, 136, 220))

        if getattr(self, "selected_line", None) is not None:
            ltype, idx, side = self.selected_line
            if (ltype == "col" and self.detected_col_groups is not None
                    and idx < len(self.detected_col_groups)):
                g      = self.detected_col_groups[idx]
                offset = (self.manual_col_left_offsets[idx]
                          if side == "left" else self.manual_col_right_offsets[idx])
                val    = g[0] if side == "left" else (g[-1] + 1)
                x      = int(round((val + offset) * scale_x)) - crop_offset_x
                draw.line([(x, 0), (x, render_h)], fill=(255, 59, 48, 255), width=2)
            elif (ltype == "row" and self.detected_row_groups is not None
                    and idx < len(self.detected_row_groups)):
                g      = self.detected_row_groups[idx]
                offset = (self.manual_row_top_offsets[idx]
                          if side == "top" else self.manual_row_bottom_offsets[idx])
                val    = g[0] if side == "top" else (g[-1] + 1)
                y      = int(round((val - offset) * scale_y)) - crop_offset_y
                draw.line([(0, y), (render_w, y)], fill=(255, 59, 48, 255), width=2)

        self.preview_tk = ImageTk.PhotoImage(preview_overlay.convert("RGB"))
        self.canvas.delete("all")
        self.canvas.create_image(
            dx + crop_offset_x, dy + crop_offset_y,
            anchor=tk.NW, image=self.preview_tk
        )
        self.canvas.config(
            scrollregion=(0, 0, max(canvas_w, w_z), max(canvas_h, h_z))
        )

    # -----------------------------------------------------------------------
    # SLICE IMAGE
    # -----------------------------------------------------------------------
    def slice_image(self):
        image_path = self.file_path_var.get().strip()
        if not image_path or not os.path.exists(image_path) or not self.original_img:
            messagebox.showerror("Error", "Please select a valid input image file first.")
            return

        try:
            cols     = int(self.cols_var.get().strip())
            rows     = int(self.rows_var.get().strip())
            border_x = int(self.border_x_var.get().strip())
            border_y = int(self.border_y_var.get().strip())
            if cols <= 0 or rows <= 0 or border_x < 0 or border_y < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error",
                "Grid Columns, Rows, and Border sizes must be positive numbers.")
            return

        W, H        = self.original_img.size
        border_type = self.border_type_var.get()

        w_border_count = cols + 1 if border_type == "all" else cols - 1
        h_border_count = rows + 1 if border_type == "all" else rows - 1

        if (W - w_border_count * border_x) <= 0 or (H - h_border_count * border_y) <= 0:
            messagebox.showerror("Error",
                "Border size is too large for the current grid/image dimensions.")
            return

        self.ensure_grid_groups()

        has_left  = (border_type == "all")
        has_right = (border_type == "all")
        col_bounds = self.get_cells_from_border_groups(
            W, self.detected_col_groups, has_left, has_right, border_x,
            self.manual_col_left_offsets, self.manual_col_right_offsets, is_col=True
        )
        has_top    = (border_type == "all")
        has_bottom = (border_type == "all")
        row_bounds = self.get_cells_from_border_groups(
            H, self.detected_row_groups, has_top, has_bottom, border_y,
            self.manual_row_top_offsets, self.manual_row_bottom_offsets, is_col=False
        )
        using_custom_bounds = True

        img_dir   = os.path.dirname(image_path)
        img_name, _ = os.path.splitext(os.path.basename(image_path))
        subfolder_name = self.subfolder_var.get().strip().replace("{filename}", img_name)
        default_parent = os.path.join(get_app_run_dir(), "sliced-images")
        parent_dir = self.custom_output_dir if self.custom_output_dir else default_parent
        output_dir = os.path.join(parent_dir, subfolder_name) if subfolder_name else parent_dir
        os.makedirs(output_dir, exist_ok=True)

        remove_left   = self.border_left_var.get()
        remove_right  = self.border_right_var.get()
        remove_top    = self.border_top_var.get()
        remove_bottom = self.border_bottom_var.get()

        base_name, ext = os.path.splitext(os.path.basename(image_path))
        save_ext = (ext if ext.lower() in
                    [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"]
                    else ".png")

        count = 0
        for r in range(rows):
            for c in range(cols):
                if using_custom_bounds:
                    l_active = col_bounds[c][0]
                    r_active = col_bounds[c][1] + 1
                    t_active = row_bounds[r][0]
                    b_active = row_bounds[r][1] + 1
                    l_slot   = col_bounds[c - 1][1] + 1 if c > 0 else 0
                    r_slot   = col_bounds[c + 1][0]     if c < cols - 1 else W
                    t_slot   = row_bounds[r - 1][1] + 1 if r > 0 else 0
                    b_slot   = row_bounds[r + 1][0]     if r < rows - 1 else H
                else:
                    if border_type == "all":
                        l_active = border_x + c * (w_cell + border_x)
                        t_active = border_y + r * (h_cell + border_y)
                    else:
                        l_active = c * (w_cell + border_x)
                        t_active = r * (h_cell + border_y)
                    r_active = l_active + w_cell
                    b_active = t_active + h_cell
                    l_slot = l_active - border_x if (border_type == "all" or c > 0) else 0
                    r_slot = r_active + border_x if (border_type == "all" or c < cols - 1) else W
                    t_slot = t_active - border_y if (border_type == "all" or r > 0) else 0
                    b_slot = b_active + border_y if (border_type == "all" or r < rows - 1) else H

                l_crop = l_active if remove_left   else l_slot
                r_crop = r_active if remove_right  else r_slot
                t_crop = t_active if remove_top    else t_slot
                b_crop = b_active if remove_bottom else b_slot

                l_crop_i = int(max(0, min(W, round(l_crop))))
                r_crop_i = int(max(0, min(W, round(r_crop))))
                t_crop_i = int(max(0, min(H, round(t_crop))))
                b_crop_i = int(max(0, min(H, round(b_crop))))

                if r_crop_i <= l_crop_i or b_crop_i <= t_crop_i:
                    continue

                cropped = self.original_img.crop(
                    (l_crop_i, t_crop_i, r_crop_i, b_crop_i))
                prefix  = self.prefix_var.get().replace("{filename}", base_name)
                scheme  = self.naming_scheme_var.get()
                if scheme == "sequential":
                    pad_len  = len(str(rows * cols))
                    out_name = f"{prefix}{str(count + 1).zfill(pad_len)}{save_ext}"
                else:
                    out_name = f"{prefix}{r + 1}_{c + 1}{save_ext}"

                cropped.save(os.path.join(output_dir, out_name))
                count += 1

        self.last_output_dir = output_dir
        self.load_frames_from_directory(output_dir)
        self.status_label.config(
            text=f"Sliced {count} images saved to: {os.path.basename(output_dir)}", fg=GREEN
        )
        messagebox.showinfo(
            "Success",
            f"Successfully split the grid into {count} images!\n\nSaved to:\n{output_dir}"
        )

    # -----------------------------------------------------------------------
    # AUTO DETECT
    # -----------------------------------------------------------------------
    def auto_detect_borders(self):
        if not self.original_img:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        self.status_label.config(text="Detecting borders… please wait…", fg=ACCENT)
        self.root.update_idletasks()
        result = self.detect_borders_algorithm(self.original_img)
        if result and (result["border_x"] > 0 or result["border_y"] > 0
                       or result["cols"] > 1 or result["rows"] > 1):
            self.is_auto_detecting = True
            try:
                self.cols_var.set(str(result["cols"]))
                self.rows_var.set(str(result["rows"]))
                self.border_x_var.set(str(result["border_x"]))
                self.border_y_var.set(str(result["border_y"]))
                self.border_type_var.set(result["layout"])
                self.detected_col_groups       = result["col_groups"]
                self.detected_row_groups       = result["row_groups"]
                self.detected_border_x_val     = result["border_x"]
                self.detected_border_y_val     = result["border_y"]
                self.detected_outer_borders    = result.get("outer_borders", {})
                self.manual_col_left_offsets   = [0] * len(result["col_groups"])
                self.manual_col_right_offsets  = [0] * len(result["col_groups"])
                self.manual_row_top_offsets    = [0] * len(result["row_groups"])
                self.manual_row_bottom_offsets = [0] * len(result["row_groups"])
                self.selected_line = None
            finally:
                self.is_auto_detecting = False
            self.status_label.config(
                text=(f"Auto-detected: {result['cols']}x{result['rows']} grid "
                      f"(Borders: X={result['border_x']}px, Y={result['border_y']}px)"),
                fg=GREEN
            )
            self.update_preview()
        else:
            self.status_label.config(
                text="No clear border grid detected. Adjust settings manually.", fg=ACCENT
            )
            messagebox.showinfo(
                "Detection Result",
                "No uniform solid color grid borders were automatically detected.\n\n"
                "Please configure the columns, rows, and borders manually."
            )

    # -----------------------------------------------------------------------
    # DETECT BORDERS ALGORITHM  (preserved exactly)
    # -----------------------------------------------------------------------
    def detect_borders_algorithm(self, pil_img, color_tolerance=45, match_ratio=0.95):
        img  = pil_img.convert("RGBA")
        W, H = img.size

        # --- Crosshairs Grid Detection Pass ---
        try:
            pixels = img.convert("L")
            dark_pixels = set()
            for y in range(H):
                for x in range(W):
                    if pixels.getpixel((x, y)) < 80:
                        dark_pixels.add((x, y))
                        
            # Flood fill to find blobs
            visited = set()
            candidates = []
            for (x, y) in sorted(dark_pixels):
                if (x, y) in visited:
                    continue
                blob = []
                queue = [(x, y)]
                visited.add((x, y))
                while queue:
                    cx, cy = queue.pop(0)
                    blob.append((cx, cy))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) in dark_pixels and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append((nx, ny))
                            
                xs = [p[0] for p in blob]
                ys = [p[1] for p in blob]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                w = max_x - min_x + 1
                h = max_y - min_y + 1
                
                # Filter blobs of crosshair sizes (e.g. 12x12 to 25x25 pixels)
                if 12 <= w <= 25 and 12 <= h <= 25:
                    if 25 <= len(blob) <= 60:
                        aspect = w / h
                        if 0.7 <= aspect <= 1.4:
                            cx = (min_x + max_x) // 2
                            cy = (min_y + max_y) // 2
                            candidates.append({"cx": cx, "cy": cy, "w": w, "h": h})
                            
            if len(candidates) >= 4:
                col_bins = []
                for cand in candidates:
                    placed = False
                    for bin_list in col_bins:
                        avg_x = sum(c["cx"] for c in bin_list) / len(bin_list)
                        if abs(cand["cx"] - avg_x) < 30:
                            bin_list.append(cand)
                            placed = True
                            break
                    if not placed:
                        col_bins.append([cand])
                        
                row_bins = []
                for cand in candidates:
                    placed = False
                    for bin_list in row_bins:
                        avg_y = sum(c["cy"] for c in bin_list) / len(bin_list)
                        if abs(cand["cy"] - avg_y) < 30:
                            bin_list.append(cand)
                            placed = True
                            break
                    if not placed:
                        row_bins.append([cand])
                        
                max_col = max(len(b) for b in col_bins) if col_bins else 0
                max_row = max(len(b) for b in row_bins) if row_bins else 0
                
                if max_col >= 2 and max_row >= 2:
                    min_col_crosses = max(2, max_col - 1) if max_col > 2 else 2
                    min_row_crosses = max(2, max_row - 1) if max_row > 2 else 2
                    
                    robust_col_bins = [b for b in col_bins if len(b) >= min_col_crosses]
                    robust_row_bins = [b for b in row_bins if len(b) >= min_row_crosses]
                    
                    valid_crosses = []
                    for cand in candidates:
                        in_col = any(abs(cand["cx"] - sum(c["cx"] for c in b)/len(b)) < 30 for b in robust_col_bins)
                        in_row = any(abs(cand["cy"] - sum(c["cy"] for c in b)/len(b)) < 30 for b in robust_row_bins)
                        if in_col and in_row:
                            valid_crosses.append(cand)
                            
                    if len(valid_crosses) >= 4:
                        final_cols = []
                        for c in valid_crosses:
                            placed = False
                            for bin_list in final_cols:
                                avg_x = sum(item["cx"] for item in bin_list) / len(bin_list)
                                if abs(c["cx"] - avg_x) < 30:
                                    bin_list.append(c)
                                    placed = True
                                    break
                            if not placed:
                                final_cols.append([c])
                                
                        final_rows = []
                        for c in valid_crosses:
                            placed = False
                            for bin_list in final_rows:
                                avg_y = sum(item["cy"] for item in bin_list) / len(bin_list)
                                if abs(c["cy"] - avg_y) < 30:
                                    bin_list.append(c)
                                    placed = True
                                    break
                            if not placed:
                                final_rows.append([c])
                                
                        col_centers = sorted([int(sum(c["cx"] for c in b) / len(b)) for b in final_cols])
                        row_centers = sorted([int(sum(c["cy"] for c in b) / len(b)) for b in final_rows])
                        
                        if len(col_centers) >= 2 and len(row_centers) >= 2:
                            avg_w = sum(c["w"] for c in valid_crosses) / len(valid_crosses)
                            avg_h = sum(c["h"] for c in valid_crosses) / len(valid_crosses)
                            
                            border_x = int(avg_w)
                            border_y = int(avg_h)
                            
                            avg_cell_w = (col_centers[-1] - col_centers[0]) / (len(col_centers) - 1)
                            has_left = (col_centers[0] < avg_cell_w * 0.6)
                            has_right = ((W - col_centers[-1]) < avg_cell_w * 0.6)
                            
                            avg_cell_h = (row_centers[-1] - row_centers[0]) / (len(row_centers) - 1)
                            has_top = (row_centers[0] < avg_cell_h * 0.6)
                            has_bottom = ((H - row_centers[-1]) < avg_cell_h * 0.6)
                            
                            if has_left and has_right:
                                layout = "all"
                                cols = len(col_centers) - 1
                            elif not has_left and not has_right:
                                layout = "between"
                                cols = len(col_centers) + 1
                            else:
                                layout = "all"
                                cols = len(col_centers)
                                
                            if has_top and has_bottom:
                                rows = len(row_centers) - 1
                            elif not has_top and not has_bottom:
                                rows = len(row_centers) + 1
                            else:
                                rows = len(row_centers)
                                
                            col_groups = [list(range(cx - border_x//2, cx + border_x//2 + 1)) for cx in col_centers]
                            row_groups = [list(range(cy - border_y//2, cy + border_y//2 + 1)) for cy in row_centers]
                            
                            return {
                                "cols": cols,
                                "rows": rows,
                                "border_x": border_x,
                                "border_y": border_y,
                                "layout": layout,
                                "col_groups": col_groups,
                                "row_groups": row_groups
                            }
        except Exception:
            pass

        def check_col(x):
            sample_y = [0, H // 4, H // 2, 3 * H // 4, H - 1]
            samples  = [img.getpixel((x, y)) for y in sample_y]
            ref = samples[0]
            for p in samples[1:]:
                if p[3] < 10 and ref[3] < 10:
                    dist = 0
                else:
                    dist = (abs(ref[0] - p[0]) + abs(ref[1] - p[1]) +
                            abs(ref[2] - p[2]) + abs(ref[3] - p[3]))
                if dist > color_tolerance * 1.5:
                    return False, None
            pixels = [img.getpixel((x, y)) for y in range(H)]
            r_sorted = sorted(p[0] for p in pixels)
            g_sorted = sorted(p[1] for p in pixels)
            b_sorted = sorted(p[2] for p in pixels)
            a_sorted = sorted(p[3] for p in pixels)
            median_color = (r_sorted[H // 2], g_sorted[H // 2],
                            b_sorted[H // 2], a_sorted[H // 2])
            matches = 0
            for p in pixels:
                if p[3] < 10 and median_color[3] < 10:
                    dist = 0
                else:
                    dist = (abs(p[0] - median_color[0]) + abs(p[1] - median_color[1]) +
                            abs(p[2] - median_color[2]) + abs(p[3] - median_color[3]))
                if dist <= color_tolerance:
                    matches += 1
            ratio = matches / H
            return ratio >= match_ratio, median_color

        def check_row(y):
            sample_x = [0, W // 4, W // 2, 3 * W // 4, W - 1]
            samples  = [img.getpixel((x, y)) for x in sample_x]
            ref = samples[0]
            for p in samples[1:]:
                if p[3] < 10 and ref[3] < 10:
                    dist = 0
                else:
                    dist = (abs(ref[0] - p[0]) + abs(ref[1] - p[1]) +
                            abs(ref[2] - p[2]) + abs(ref[3] - p[3]))
                if dist > color_tolerance * 1.5:
                    return False, None
            pixels = [img.getpixel((x, y)) for x in range(W)]
            r_sorted = sorted(p[0] for p in pixels)
            g_sorted = sorted(p[1] for p in pixels)
            b_sorted = sorted(p[2] for p in pixels)
            a_sorted = sorted(p[3] for p in pixels)
            median_color = (r_sorted[W // 2], g_sorted[W // 2],
                            b_sorted[W // 2], a_sorted[W // 2])
            matches = 0
            for p in pixels:
                if p[3] < 10 and median_color[3] < 10:
                    dist = 0
                else:
                    dist = (abs(p[0] - median_color[0]) + abs(p[1] - median_color[1]) +
                            abs(p[2] - median_color[2]) + abs(p[3] - median_color[3]))
                if dist <= color_tolerance:
                    matches += 1
            ratio = matches / W
            return ratio >= match_ratio, median_color

        solid_cols, col_colors = [], []
        for x in range(W):
            is_solid, color = check_col(x)
            if is_solid:
                solid_cols.append(x)
                col_colors.append(color)

        solid_rows, row_colors = [], []
        for y in range(H):
            is_solid, color = check_row(y)
            if is_solid:
                solid_rows.append(y)
                row_colors.append(color)

        def group_indices(indices):
            if not indices:
                return []
            groups = []
            current_group = [indices[0]]
            for idx in indices[1:]:
                if idx == current_group[-1] + 1:
                    current_group.append(idx)
                else:
                    groups.append(current_group)
                    current_group = [idx]
            groups.append(current_group)
            return groups

        color_candidates = set()
        for c in col_colors + row_colors:
            rounded = (round(c[0] / 15) * 15, round(c[1] / 15) * 15,
                       round(c[2] / 15) * 15, round(c[3] / 15) * 15)
            color_candidates.add(rounded)

        if not color_candidates:
            return None

        best_color = None
        best_score = -1
        best_layout_info = None

        for candidate in color_candidates:
            valid_cols = []
            for x, color in zip(solid_cols, col_colors):
                rounded = (round(color[0] / 15) * 15, round(color[1] / 15) * 15,
                           round(color[2] / 15) * 15, round(color[3] / 15) * 15)
                if rounded == candidate:
                    valid_cols.append(x)
            valid_rows = []
            for y, color in zip(solid_rows, row_colors):
                rounded = (round(color[0] / 15) * 15, round(color[1] / 15) * 15,
                           round(color[2] / 15) * 15, round(color[3] / 15) * 15)
                if rounded == candidate:
                    valid_rows.append(y)

            col_groups = group_indices(valid_cols)
            row_groups = group_indices(valid_rows)
            N_cols     = len(col_groups)
            N_rows     = len(row_groups)

            if N_cols > 0 and N_rows > 0:
                score = N_cols * N_rows * 10
            else:
                score = max(N_cols, N_rows)

            if score > best_score:
                best_score = score
                best_color = candidate
                best_layout_info = (col_groups, row_groups)

        if not best_color or best_score <= 0:
            return None

        col_groups, row_groups = best_layout_info

        def is_line_uniform_col(x, tol=55):
            pixels = [img.getpixel((x, y)) for y in range(H)]
            r_sorted = sorted(p[0] for p in pixels)
            g_sorted = sorted(p[1] for p in pixels)
            b_sorted = sorted(p[2] for p in pixels)
            a_sorted = sorted(p[3] for p in pixels)
            median_color = (r_sorted[H // 2], g_sorted[H // 2],
                            b_sorted[H // 2], a_sorted[H // 2])
            matches = sum(
                1 for p in pixels
                if (abs(p[0] - median_color[0]) + abs(p[1] - median_color[1]) +
                    abs(p[2] - median_color[2]) + abs(p[3] - median_color[3])) <= tol
            )
            return (matches / H) >= 0.80, median_color

        def is_line_uniform_row(y, tol=55):
            pixels = [img.getpixel((x, y)) for x in range(W)]
            r_sorted = sorted(p[0] for p in pixels)
            g_sorted = sorted(p[1] for p in pixels)
            b_sorted = sorted(p[2] for p in pixels)
            a_sorted = sorted(p[3] for p in pixels)
            median_color = (r_sorted[W // 2], g_sorted[W // 2],
                            b_sorted[W // 2], a_sorted[W // 2])
            matches = sum(
                1 for p in pixels
                if (abs(p[0] - median_color[0]) + abs(p[1] - median_color[1]) +
                    abs(p[2] - median_color[2]) + abs(p[3] - median_color[3])) <= tol
            )
            return (matches / W) >= 0.80, median_color

        expanded_col_groups = []
        for idx_g, g in enumerate(col_groups):
            start      = g[0]
            end        = g[-1]
            prev_end   = col_groups[idx_g - 1][-1] if idx_g > 0 else -1
            next_start = col_groups[idx_g + 1][0]  if idx_g < len(col_groups) - 1 else W
            last_med   = best_color
            while start > prev_end + 1:
                is_unif, med = is_line_uniform_col(start - 1)
                dist = (abs(med[0] - best_color[0]) + abs(med[1] - best_color[1]) +
                        abs(med[2] - best_color[2]) + abs(med[3] - best_color[3]))
                if is_unif and dist <= 40:
                    med_diff = (abs(med[0] - last_med[0]) + abs(med[1] - last_med[1]) +
                                abs(med[2] - last_med[2]) + abs(med[3] - last_med[3]))
                    if med_diff < 15 and dist > 80:
                        break
                    start -= 1
                    last_med = med
                else:
                    break
            last_med = best_color
            while end < next_start - 1:
                is_unif, med = is_line_uniform_col(end + 1)
                dist = (abs(med[0] - best_color[0]) + abs(med[1] - best_color[1]) +
                        abs(med[2] - best_color[2]) + abs(med[3] - best_color[3]))
                if is_unif and dist <= 40:
                    med_diff = (abs(med[0] - last_med[0]) + abs(med[1] - last_med[1]) +
                                abs(med[2] - last_med[2]) + abs(med[3] - last_med[3]))
                    if med_diff < 15 and dist > 80:
                        break
                    end += 1
                    last_med = med
                else:
                    break
            expanded_col_groups.append(list(range(start, end + 1)))
        col_groups = expanded_col_groups

        expanded_row_groups = []
        for idx_g, g in enumerate(row_groups):
            start      = g[0]
            end        = g[-1]
            prev_end   = row_groups[idx_g - 1][-1] if idx_g > 0 else -1
            next_start = row_groups[idx_g + 1][0]  if idx_g < len(row_groups) - 1 else H
            last_med   = best_color
            while start > prev_end + 1:
                is_unif, med = is_line_uniform_row(start - 1)
                dist = (abs(med[0] - best_color[0]) + abs(med[1] - best_color[1]) +
                        abs(med[2] - best_color[2]) + abs(med[3] - best_color[3]))
                if is_unif and dist <= 40:
                    med_diff = (abs(med[0] - last_med[0]) + abs(med[1] - last_med[1]) +
                                abs(med[2] - last_med[2]) + abs(med[3] - last_med[3]))
                    if med_diff < 15 and dist > 80:
                        break
                    start -= 1
                    last_med = med
                else:
                    break
            last_med = best_color
            while end < next_start - 1:
                is_unif, med = is_line_uniform_row(end + 1)
                dist = (abs(med[0] - best_color[0]) + abs(med[1] - best_color[1]) +
                        abs(med[2] - best_color[2]) + abs(med[3] - best_color[3]))
                if is_unif and dist <= 40:
                    med_diff = (abs(med[0] - last_med[0]) + abs(med[1] - last_med[1]) +
                                abs(med[2] - last_med[2]) + abs(med[3] - last_med[3]))
                    if med_diff < 15 and dist > 80:
                        break
                    end += 1
                    last_med = med
                else:
                    break
            expanded_row_groups.append(list(range(start, end + 1)))
        row_groups = expanded_row_groups

        # Classify outer edge borders vs internal dividers
        has_left_outer = False
        has_right_outer = False
        internal_col_groups = []
        outer_left = None
        outer_right = None
        for g in col_groups:
            if g[0] <= 5 or any(i in g for i in range(6)):
                has_left_outer = True
                outer_left = g
            elif g[-1] >= W - 6 or any((W - 1 - i) in g for i in range(6)):
                has_right_outer = True
                outer_right = g
            else:
                internal_col_groups.append(g)

        has_top_outer = False
        has_bottom_outer = False
        internal_row_groups = []
        outer_top = None
        outer_bottom = None
        for g in row_groups:
            if g[0] <= 5 or any(i in g for i in range(6)):
                has_top_outer = True
                outer_top = g
            elif g[-1] >= H - 6 or any((H - 1 - i) in g for i in range(6)):
                has_bottom_outer = True
                outer_bottom = g
            else:
                internal_row_groups.append(g)

        # A grid has layout "all" only if outer borders enclose both sides of both dimensions
        if (has_left_outer and has_right_outer) and (has_top_outer and has_bottom_outer):
            border_layout = "all"
            final_col_groups = col_groups
            final_row_groups = row_groups
            detected_cols = max(1, len(final_col_groups) - 1)
            detected_rows = max(1, len(final_row_groups) - 1)
        else:
            border_layout = "between"
            final_col_groups = internal_col_groups
            final_row_groups = internal_row_groups
            detected_cols = len(final_col_groups) + 1 if final_col_groups else 1
            detected_rows = len(final_row_groups) + 1 if final_row_groups else 1

        col_widths = [len(g) for g in final_col_groups]
        row_widths = [len(g) for g in final_row_groups]

        detected_border_x = (int(sorted(col_widths)[len(col_widths) // 2])
                              if col_widths else 0)
        detected_border_y = (int(sorted(row_widths)[len(row_widths) // 2])
                              if row_widths else 0)

        return {
            "cols":          detected_cols,
            "rows":          detected_rows,
            "border_x":      detected_border_x,
            "border_y":      detected_border_y,
            "layout":        border_layout,
            "col_groups":    final_col_groups,
            "row_groups":    final_row_groups,
            "outer_borders": {
                "left":   outer_left,
                "right":  outer_right,
                "top":    outer_top,
                "bottom": outer_bottom
            }
        }

    # -----------------------------------------------------------------------
    # ENSURE GRID GROUPS  (preserved exactly)
    # -----------------------------------------------------------------------
    def ensure_grid_groups(self):
        if not self.original_img:
            return
        try:
            cols     = int(self.cols_var.get().strip())
            rows     = int(self.rows_var.get().strip())
            border_x = int(self.border_x_var.get().strip())
            border_y = int(self.border_y_var.get().strip())
            if cols <= 0 or rows <= 0 or border_x < 0 or border_y < 0:
                return
        except ValueError:
            return

        W, H        = self.original_img.size
        border_type = self.border_type_var.get()
        expected_cols = cols + 1 if border_type == "all" else cols - 1
        expected_rows = rows + 1 if border_type == "all" else rows - 1

        if (self.detected_col_groups is None
                or len(self.detected_col_groups) != expected_cols
                or not self.manual_col_left_offsets
                or len(self.manual_col_left_offsets) != expected_cols
                or not self.manual_col_right_offsets
                or len(self.manual_col_right_offsets) != expected_cols):
            w_border_count = cols + 1 if border_type == "all" else cols - 1
            w_cell = (W - w_border_count * border_x) / cols if cols > 0 else W
            col_groups = []
            for c in range(expected_cols):
                if border_type == "all":
                    start = c * (w_cell + border_x)
                else:
                    start = (c + 1) * w_cell + c * border_x
                end = max(start, start + border_x - 1)
                col_groups.append(
                    list(range(int(round(start)), int(round(end)) + 1)))
            self.detected_col_groups      = col_groups
            self.manual_col_left_offsets  = [0] * expected_cols
            self.manual_col_right_offsets = [0] * expected_cols

        if (self.detected_row_groups is None
                or len(self.detected_row_groups) != expected_rows
                or not self.manual_row_top_offsets
                or len(self.manual_row_top_offsets) != expected_rows
                or not self.manual_row_bottom_offsets
                or len(self.manual_row_bottom_offsets) != expected_rows):
            h_border_count = rows + 1 if border_type == "all" else rows - 1
            h_cell = (H - h_border_count * border_y) / rows if rows > 0 else H
            row_groups = []
            for r in range(expected_rows):
                if border_type == "all":
                    start = r * (h_cell + border_y)
                else:
                    start = (r + 1) * h_cell + r * border_y
                end = max(start, start + border_y - 1)
                row_groups.append(
                    list(range(int(round(start)), int(round(end)) + 1)))
            self.detected_row_groups       = row_groups
            self.manual_row_top_offsets    = [0] * expected_rows
            self.manual_row_bottom_offsets = [0] * expected_rows

    # -----------------------------------------------------------------------
    # GET CELLS FROM BORDER GROUPS  (preserved exactly)
    # -----------------------------------------------------------------------
    def get_cells_from_border_groups(self, dim_size, groups, has_outer_start,
                                     has_outer_end, target_border_size,
                                     left_offsets=None, right_offsets=None,
                                     is_col=True):
        if not groups:
            return [(0, dim_size - 1)]

        default_size = (getattr(self, "detected_border_x_val", None)
                        if is_col else getattr(self, "detected_border_y_val", None))
        use_actual_bounds = (default_size is not None
                             and target_border_size == default_size)

        borders = []
        N_g     = len(groups)

        for idx, g in enumerate(groups):
            l_off = left_offsets[idx]  if (left_offsets  and idx < len(left_offsets))  else 0
            r_off = right_offsets[idx] if (right_offsets and idx < len(right_offsets)) else 0
            if not is_col:
                l_off = -l_off
                r_off = -r_off

            if use_actual_bounds:
                start = g[0] + l_off
                end   = g[-1] + r_off
            else:
                center = ((g[0] + l_off) + (g[-1] + r_off)) / 2.0
                if idx == 0 and has_outer_start:
                    start = 0
                    end   = target_border_size - 1
                elif idx == N_g - 1 and has_outer_end:
                    start = dim_size - target_border_size
                    end   = dim_size - 1
                else:
                    half  = target_border_size / 2.0
                    start = round(center - half)
                    end   = round(center + half) - 1

            if end < start:
                end = start
            borders.append((start, end))

        cells = []
        outer_borders = getattr(self, "detected_outer_borders", {}) or {}
        outer_start = outer_borders.get("left" if is_col else "top")
        outer_end = outer_borders.get("right" if is_col else "bottom")

        if has_outer_start:
            start_idx     = 1
            current_start = borders[0][1] + 1
        elif outer_start:
            start_idx     = 0
            current_start = outer_start[-1] + 1
        else:
            start_idx     = 0
            current_start = 0

        for i in range(start_idx, N_g):
            cell_end = borders[i][0] - 1
            cells.append((current_start, cell_end))
            current_start = borders[i][1] + 1

        if not has_outer_end:
            if outer_end:
                cells.append((current_start, outer_end[0] - 1))
            else:
                cells.append((current_start, dim_size - 1))

        return cells

    # -----------------------------------------------------------------------
    # ON CANVAS CLICK  (preserved exactly)
    # -----------------------------------------------------------------------
    def on_canvas_click(self, event):
        if self.preview_mode == "storyboard":
            self.on_storyboard_press(event)
            return
        if not self.original_img:
            return

        try:
            cols     = int(self.cols_var.get().strip())
            rows     = int(self.rows_var.get().strip())
            border_x = int(self.border_x_var.get().strip())
            border_y = int(self.border_y_var.get().strip())
            if cols <= 0 or rows <= 0 or border_x < 0 or border_y < 0:
                raise ValueError()
        except ValueError:
            self.on_pan_start(event)
            return

        W, H        = self.original_img.size
        border_type = self.border_type_var.get()
        self.ensure_grid_groups()

        expected_col_groups = (cols + 1) if border_type == "all" else (cols - 1)
        expected_row_groups = (rows + 1) if border_type == "all" else (rows - 1)

        w_z      = int(self.preview_w * self.zoom_level)
        h_z      = int(self.preview_h * self.zoom_level)
        canvas_w = max(self.preview_w, self.canvas.winfo_width())
        canvas_h = max(self.preview_h, self.canvas.winfo_height())
        dx       = max(0, (canvas_w - w_z) // 2)
        dy       = max(0, (canvas_h - h_z) // 2)
        scale_x  = w_z / W
        scale_y  = h_z / H

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        min_dist_x   = 999999
        best_col_idx = -1
        col_side     = None

        if True:
            for idx, g in enumerate(self.detected_col_groups):
                l_off = (self.manual_col_left_offsets[idx]
                         if (self.manual_col_left_offsets
                             and idx < len(self.manual_col_left_offsets)) else 0)
                r_off = (self.manual_col_right_offsets[idx]
                         if (self.manual_col_right_offsets
                             and idx < len(self.manual_col_right_offsets)) else 0)
                x_left  = dx + (g[0] + l_off)      * scale_x
                x_right = dx + (g[-1] + r_off + 1) * scale_x

                is_near_l_top    = abs(canvas_x - x_left) <= 15 and abs(canvas_y - dy) <= 15
                is_near_l_bottom = abs(canvas_x - x_left) <= 15 and abs(canvas_y - (dy + h_z)) <= 15
                is_near_l_line   = abs(canvas_x - x_left) <= 8  and dy <= canvas_y <= dy + h_z
                if is_near_l_top or is_near_l_bottom or is_near_l_line:
                    dist = abs(canvas_x - x_left)
                    if dist < min_dist_x:
                        min_dist_x   = dist
                        best_col_idx = idx
                        col_side     = "left"

                is_near_r_top    = abs(canvas_x - x_right) <= 15 and abs(canvas_y - dy) <= 15
                is_near_r_bottom = abs(canvas_x - x_right) <= 15 and abs(canvas_y - (dy + h_z)) <= 15
                is_near_r_line   = abs(canvas_x - x_right) <= 8  and dy <= canvas_y <= dy + h_z
                if is_near_r_top or is_near_r_bottom or is_near_r_line:
                    dist = abs(canvas_x - x_right)
                    if dist < min_dist_x:
                        min_dist_x   = dist
                        best_col_idx = idx
                        col_side     = "right"

        min_dist_y   = 999999
        best_row_idx = -1
        row_side     = None

        if True:
            for idx, g in enumerate(self.detected_row_groups):
                t_off = (self.manual_row_top_offsets[idx]
                         if (self.manual_row_top_offsets
                             and idx < len(self.manual_row_top_offsets)) else 0)
                b_off = (self.manual_row_bottom_offsets[idx]
                         if (self.manual_row_bottom_offsets
                             and idx < len(self.manual_row_bottom_offsets)) else 0)
                y_top    = dy + (g[0] - t_off)      * scale_y
                y_bottom = dy + (g[-1] - b_off + 1) * scale_y

                is_near_t_left  = abs(canvas_x - dx)          <= 15 and abs(canvas_y - y_top) <= 15
                is_near_t_right = abs(canvas_x - (dx + w_z))  <= 15 and abs(canvas_y - y_top) <= 15
                is_near_t_line  = abs(canvas_y - y_top)        <= 8  and dx <= canvas_x <= dx + w_z
                if is_near_t_left or is_near_t_right or is_near_t_line:
                    dist = abs(canvas_y - y_top)
                    if dist < min_dist_y:
                        min_dist_y   = dist
                        best_row_idx = idx
                        row_side     = "top"

                is_near_b_left  = abs(canvas_x - dx)          <= 15 and abs(canvas_y - y_bottom) <= 15
                is_near_b_right = abs(canvas_x - (dx + w_z))  <= 15 and abs(canvas_y - y_bottom) <= 15
                is_near_b_line  = abs(canvas_y - y_bottom)     <= 8  and dx <= canvas_x <= dx + w_z
                if is_near_b_left or is_near_b_right or is_near_b_line:
                    dist = abs(canvas_y - y_bottom)
                    if dist < min_dist_y:
                        min_dist_y   = dist
                        best_row_idx = idx
                        row_side     = "bottom"

        threshold   = 12
        clicked_col = (best_col_idx != -1 and min_dist_x <= threshold)
        clicked_row = (best_row_idx != -1 and min_dist_y <= threshold)

        if clicked_col and (not clicked_row or min_dist_x < min_dist_y):
            self.selected_line = ("col", best_col_idx, col_side)
            self.update_preview()
            self.root.update_idletasks()
            if col_side == "left":
                curr_val = (self.manual_col_left_offsets[best_col_idx]
                            if (self.manual_col_left_offsets
                                and best_col_idx < len(self.manual_col_left_offsets)) else 0)
                offset = simpledialog.askinteger(
                    "Adjust Divider Line",
                    f"Shift Left Line of divider #{best_col_idx + 1} by how many pixels?\n"
                    "(Negative = shift left, Positive = shift right)",
                    initialvalue=curr_val
                )
                if offset is not None:
                    if not self.manual_col_left_offsets:
                        self.manual_col_left_offsets = [0] * expected_col_groups
                    self.manual_col_left_offsets[best_col_idx] = offset
            else:
                curr_val = (self.manual_col_right_offsets[best_col_idx]
                            if (self.manual_col_right_offsets
                                and best_col_idx < len(self.manual_col_right_offsets)) else 0)
                offset = simpledialog.askinteger(
                    "Adjust Divider Line",
                    f"Shift Right Line of divider #{best_col_idx + 1} by how many pixels?\n"
                    "(Negative = shift left, Positive = shift right)",
                    initialvalue=curr_val
                )
                if offset is not None:
                    if not self.manual_col_right_offsets:
                        self.manual_col_right_offsets = [0] * expected_col_groups
                    self.manual_col_right_offsets[best_col_idx] = offset
            self.selected_line = None
            self.update_preview()
            return "break"

        elif clicked_row:
            self.selected_line = ("row", best_row_idx, row_side)
            self.update_preview()
            self.root.update_idletasks()
            if row_side == "top":
                curr_val = (self.manual_row_top_offsets[best_row_idx]
                            if (self.manual_row_top_offsets
                                and best_row_idx < len(self.manual_row_top_offsets)) else 0)
                offset = simpledialog.askinteger(
                    "Adjust Divider Line",
                    f"Shift Top Line of divider #{best_row_idx + 1} by how many pixels?\n"
                    "(Positive = shift UP, Negative = shift DOWN)",
                    initialvalue=curr_val
                )
                if offset is not None:
                    if not self.manual_row_top_offsets:
                        self.manual_row_top_offsets = [0] * expected_row_groups
                    self.manual_row_top_offsets[best_row_idx] = offset
            else:
                curr_val = (self.manual_row_bottom_offsets[best_row_idx]
                            if (self.manual_row_bottom_offsets
                                and best_row_idx < len(self.manual_row_bottom_offsets)) else 0)
                offset = simpledialog.askinteger(
                    "Adjust Divider Line",
                    f"Shift Bottom Line of divider #{best_row_idx + 1} by how many pixels?\n"
                    "(Positive = shift UP, Negative = shift DOWN)",
                    initialvalue=curr_val
                )
                if offset is not None:
                    if not self.manual_row_bottom_offsets:
                        self.manual_row_bottom_offsets = [0] * expected_row_groups
                    self.manual_row_bottom_offsets[best_row_idx] = offset
            self.selected_line = None
            self.update_preview()
            return "break"

        self.on_pan_start(event)

    # -----------------------------------------------------------------------
    # ANIMATE TAB: FRAME LIST HELPERS
    # -----------------------------------------------------------------------
    def refresh_frame_listbox(self):
        self.frame_listbox.delete(0, tk.END)
        for idx in self.animation_frame_order:
            self.frame_listbox.insert(
                tk.END, os.path.basename(self.animation_frames[idx]))

    def load_frames_from_directory(self, folder):
        if not folder or not os.path.exists(folder):
            return False
        exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        found = []
        try:
            for fname in os.listdir(folder):
                if os.path.splitext(fname)[1].lower() in exts:
                    found.append(os.path.join(folder, fname))
        except OSError:
            return False
        found.sort()
        if not found:
            return False
        self.animation_frames = found
        self.animation_frame_order = list(range(len(found)))
        self.stabilize_cache = {}
        self.refresh_frame_listbox()

        n = len(found)
        self.range_start_spin.config(from_=1, to=n)
        self.range_end_spin.config(from_=1, to=n)
        self.range_start_var.set("1")
        self.range_end_var.set(str(n))
        self.timeline_slider.config(from_=1.0, to=float(n))
        self.timeline_slider_var.set(1.0)
        self.current_anim_frame_idx = 1

        if self.stabilize_var.get():
            self.run_auto_stabilization()
        else:
            self.status_label.config(
                text=f"Loaded {n} animation frame{'s' if n != 1 else ''} from folder.",
                fg=GREEN
            )
            self.update_preview()
        return True

    def load_frames_for_animation(self):
        initial = os.getcwd()
        default_parent = os.path.join(get_app_run_dir(), "sliced-images")
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            initial = os.path.dirname(self.last_output_dir)
        elif os.path.exists(default_parent):
            initial = default_parent
        elif self.custom_output_dir and os.path.exists(self.custom_output_dir):
            initial = self.custom_output_dir
        elif self.file_path_var.get().strip():
            in_img = self.file_path_var.get().strip()
            if os.path.exists(in_img):
                initial = os.path.dirname(in_img)

        folder = filedialog.askdirectory(
            title="Select Folder Containing Frames", initialdir=initial)
        if not folder:
            return
        if not self.load_frames_from_directory(folder):
            messagebox.showinfo("No Frames",
                "No image files found in the selected folder.")

    # -----------------------------------------------------------------------
    # STABILIZATION & CROPPING METHODS
    # -----------------------------------------------------------------------
    def _has_numpy(self):
        try:
            import numpy as np
            from numpy.fft import fft2, ifft2
            return True
        except ImportError:
            return False

    def on_stabilize_toggled(self):
        if self.stabilize_var.get():
            if not self.stabilize_cache.get("shifts"):
                self.run_auto_stabilization()
            else:
                self.update_preview()
        else:
            self.update_preview()

    def on_stabilize_slider_changed(self, val=None):
        if not self.stabilize_cache.get("W_base"):
            if self.stabilize_var.get():
                self.run_auto_stabilization()
            return
        self.update_stabilize_crop_dimensions()
        if self.preview_mode == "gif":
            self.draw_gif_frame()
        else:
            self.update_preview()

    def update_stabilize_crop_dimensions(self):
        if not self.stabilize_cache.get("W_base"):
            return
        W_base = self.stabilize_cache["W_base"]
        H_base = self.stabilize_cache["H_base"]
        try:
            slider_val = float(self.stabilize_crop_slider_var.get())
        except (ValueError, TypeError):
            slider_val = 0.0
        scale = max(0.1, 1.0 - (slider_val / 100.0))
        cw = max(10, int(round(W_base * scale)))
        ch = max(10, int(round(H_base * scale)))
        self.stabilize_cache["current_w"] = cw
        self.stabilize_cache["current_h"] = ch

        if slider_val <= 0.5:
            self.crop_level_label.config(text=f"Min Crop ({cw}x{ch})")
        else:
            self.crop_level_label.config(text=f"+{int(slider_val)}% ({cw}x{ch})")

    def run_auto_stabilization(self):
        if not self.animation_frames:
            if self.last_output_dir and os.path.exists(self.last_output_dir):
                self.load_frames_from_directory(self.last_output_dir)
        if not self.animation_frames:
            messagebox.showwarning("No Frames", "Please load animation frames first.")
            return

        self.status_label.config(text="Stabilizing frames using objects… please wait…", fg=ACCENT)
        self.root.update_idletasks()

        success, info = self.calculate_stabilization()
        if success:
            self.stabilize_var.set(True)
            self.stab_info_label.config(
                text=f"Aligned {info['count']} frames | Aspect: {info['ar']:.2f} ({info['w']}x{info['h']}) | Jitter: X ±{info['max_dx']}px, Y ±{info['max_dy']}px",
                fg=GREEN
            )
            self.status_label.config(text="Frames stabilized and aligned successfully.", fg=GREEN)
            self.update_preview()
        else:
            messagebox.showerror("Stabilization Failed", info.get("error", "Failed to compute stabilization."))

    def calculate_stabilization(self):
        n = len(self.animation_frames)
        if n == 0:
            return False, {"error": "No frames loaded"}

        ordered_paths = [self.animation_frames[i] for i in self.animation_frame_order]

        loaded_images = []
        for p in ordered_paths:
            try:
                loaded_images.append(Image.open(p).convert("RGBA"))
            except Exception as e:
                return False, {"error": f"Failed to load frame {p}: {e}"}

        shifts = [(0, 0)]
        has_np = self._has_numpy()

        if has_np:
            import numpy as np
            from numpy.fft import fft2, ifft2
            ref_arr = np.array(loaded_images[0].convert("L"), dtype=float)
            rh, rw = ref_arr.shape
            for i in range(1, n):
                f_arr = np.array(loaded_images[i].convert("L"), dtype=float)
                min_h = min(rh, f_arr.shape[0])
                min_w = min(rw, f_arr.shape[1])
                ch0, ch1 = int(min_h * 0.05), int(min_h * 0.95)
                cw0, cw1 = int(min_w * 0.05), int(min_w * 0.95)
                r_sub = ref_arr[ch0:ch1, cw0:cw1]
                f_sub = f_arr[ch0:ch1, cw0:cw1]
                win = np.hanning(ch1 - ch0)[:, None] * np.hanning(cw1 - cw0)[None, :]
                F1 = fft2(r_sub * win)
                F2 = fft2(f_sub * win)
                cross = (F1 * F2.conj()) / (np.abs(F1 * F2.conj()) + 1e-10)
                corr = np.real(ifft2(cross))
                sh, sw = corr.shape
                my, mx = np.unravel_index(np.argmax(corr), corr.shape)
                if my > sh // 2: my -= sh
                if mx > sw // 2: mx -= sw
                shifts.append((-int(mx), -int(my)))

            # Pass 2: Consecutive motion minimization refinement
            refined_shifts = [shifts[0]]
            h_box, w_box = int(rh * 0.65), int(rw * 0.65)
            for i in range(1, n):
                prev_f = np.array(loaded_images[i - 1].convert("L"), dtype=float)
                curr_f = np.array(loaded_images[i].convert("L"), dtype=float)
                prev_dx, prev_dy = refined_shifts[i - 1]
                base_dx, base_dy = shifts[i]

                best_energy = 1e12
                best_shift = (base_dx, base_dy)

                cx_prev = int(prev_f.shape[1] / 2 + prev_dx)
                cy_prev = int(prev_f.shape[0] / 2 + prev_dy)
                box_prev = prev_f[max(0, cy_prev - h_box // 2):min(prev_f.shape[0], cy_prev + h_box // 2),
                                  max(0, cx_prev - w_box // 2):min(prev_f.shape[1], cx_prev + w_box // 2)]

                cx_ref = int(ref_arr.shape[1] / 2)
                cy_ref = int(ref_arr.shape[0] / 2)
                box_ref = ref_arr[max(0, cy_ref - h_box // 2):min(ref_arr.shape[0], cy_ref + h_box // 2),
                                  max(0, cx_ref - w_box // 2):min(ref_arr.shape[1], cx_ref + w_box // 2)]

                for ddx in range(-4, 5):
                    for ddy in range(-4, 5):
                        tdx = base_dx + ddx
                        tdy = base_dy + ddy
                        cx_curr = int(curr_f.shape[1] / 2 + tdx)
                        cy_curr = int(curr_f.shape[0] / 2 + tdy)

                        box_curr = curr_f[max(0, cy_curr - h_box // 2):min(curr_f.shape[0], cy_curr + h_box // 2),
                                          max(0, cx_curr - w_box // 2):min(curr_f.shape[1], cx_curr + w_box // 2)]

                        if box_curr.shape == box_prev.shape and box_curr.shape == box_ref.shape:
                            inter_diff = np.mean(np.abs(box_curr - box_prev))
                            anchor_diff = np.mean(np.abs(box_curr - box_ref))
                            energy = 0.7 * inter_diff + 0.3 * anchor_diff
                            if energy < best_energy:
                                best_energy = energy
                                best_shift = (tdx, tdy)
                refined_shifts.append(best_shift)
            shifts = refined_shifts

        else:
            from PIL import ImageChops, ImageStat
            ref_l = loaded_images[0].convert("L")
            for i in range(1, n):
                cur_l = loaded_images[i].convert("L")
                s_ref = ref_l.resize((max(1, ref_l.width // 4), max(1, ref_l.height // 4)), Image.Resampling.BILINEAR)
                s_cur = cur_l.resize((max(1, cur_l.width // 4), max(1, cur_l.height // 4)), Image.Resampling.BILINEAR)
                best_diff = 1e12
                best_dx, best_dy = 0, 0
                for dx in range(-8, 9):
                    for dy in range(-8, 9):
                        diff = ImageStat.Stat(ImageChops.difference(s_ref, ImageChops.offset(s_cur, dx, dy))).sum[0]
                        if diff < best_diff:
                            best_diff = diff
                            best_dx = dx * 4
                            best_dy = dy * 4
                fine_best = best_diff
                fine_dx, fine_dy = best_dx, best_dy
                for dx in range(best_dx - 3, best_dx + 4):
                    for dy in range(best_dy - 3, best_dy + 4):
                        diff = ImageStat.Stat(ImageChops.difference(ref_l, ImageChops.offset(cur_l, dx, dy))).sum[0]
                        if diff < fine_best:
                            fine_best = diff
                            fine_dx = dx
                            fine_dy = dy
                shifts.append((-fine_dx, -fine_dy))

        aspect_ratios = [im.width / im.height for im in loaded_images]
        target_ar = sorted(aspect_ratios)[len(aspect_ratios) // 2]

        cx0 = loaded_images[0].width / 2.0
        cy0 = loaded_images[0].height / 2.0

        max_left_margins = [cx0 + shifts[i][0] for i in range(n)]
        max_right_margins = [loaded_images[i].width - (cx0 + shifts[i][0]) for i in range(n)]
        max_top_margins = [cy0 + shifts[i][1] for i in range(n)]
        max_bottom_margins = [loaded_images[i].height - (cy0 + shifts[i][1]) for i in range(n)]

        hw_max = max(10, min(min(max_left_margins), min(max_right_margins)))
        hh_max = max(10, min(min(max_top_margins), min(max_bottom_margins)))

        W_avail = int(2 * hw_max)
        H_avail = int(2 * hh_max)

        if W_avail / H_avail > target_ar:
            H_base = H_avail
            W_base = int(round(H_base * target_ar))
        else:
            W_base = W_avail
            H_base = int(round(W_base / target_ar))

        self.stabilize_cache = {
            "shifts": shifts,
            "target_ar": target_ar,
            "W_base": W_base,
            "H_base": H_base,
            "cx0": cx0,
            "cy0": cy0,
            "image_sizes": [(im.width, im.height) for im in loaded_images]
        }

        max_dx = max(abs(s[0]) for s in shifts)
        max_dy = max(abs(s[1]) for s in shifts)

        self.update_stabilize_crop_dimensions()

        return True, {
            "count": n,
            "ar": target_ar,
            "w": self.stabilize_cache["current_w"],
            "h": self.stabilize_cache["current_h"],
            "max_dx": max_dx,
            "max_dy": max_dy
        }

    def get_processed_frame(self, frame_idx):
        if not self.animation_frames or frame_idx >= len(self.animation_frame_order):
            return None
        ordered_idx = self.animation_frame_order[frame_idx]
        frame_path = self.animation_frames[ordered_idx]
        img = Image.open(frame_path).convert("RGBA")

        if self.stabilize_var.get() and self.stabilize_cache.get("shifts"):
            shifts = self.stabilize_cache["shifts"]
            if frame_idx < len(shifts):
                dx, dy = shifts[frame_idx]
                cx0 = self.stabilize_cache["cx0"]
                cy0 = self.stabilize_cache["cy0"]
                cx = cx0 + dx
                cy = cy0 + dy
                cw = self.stabilize_cache.get("current_w", img.width)
                ch = self.stabilize_cache.get("current_h", img.height)

                x0 = int(round(cx - cw / 2.0))
                y0 = int(round(cy - ch / 2.0))
                x1 = x0 + cw
                y1 = y0 + ch

                # Clamp within frame bounds
                if x0 < 0:
                    x1 -= x0
                    x0 = 0
                if y0 < 0:
                    y1 -= y0
                    y0 = 0
                if x1 > img.width:
                    x0 -= (x1 - img.width)
                    x1 = img.width
                if y1 > img.height:
                    y0 -= (y1 - img.height)
                    y1 = img.height
                x0 = max(0, x0)
                y0 = max(0, y0)

                img = img.crop((x0, y0, x1, y1))

        if self.use_bg_var.get() and len(self.animation_frames) > 0:
            try:
                bg_idx = int(self.bg_frame_index_var.get())
                if bg_idx < 1: bg_idx = 1
                if bg_idx > len(self.animation_frames): bg_idx = len(self.animation_frames)
            except ValueError:
                bg_idx = 1
            bg_path = self.animation_frames[self.animation_frame_order[bg_idx - 1]]
            try:
                background = Image.open(bg_path).convert("RGBA")
                if self.stabilize_var.get() and self.stabilize_cache.get("shifts") and (bg_idx - 1) < len(self.stabilize_cache["shifts"]):
                    bg_dx, bg_dy = self.stabilize_cache["shifts"][bg_idx - 1]
                    bg_cx = self.stabilize_cache["cx0"] + bg_dx
                    bg_cy = self.stabilize_cache["cy0"] + bg_dy
                    bg_cw = self.stabilize_cache.get("current_w", background.width)
                    bg_ch = self.stabilize_cache.get("current_h", background.height)
                    bg_x0 = int(round(bg_cx - bg_cw / 2.0))
                    bg_y0 = int(round(bg_cy - bg_ch / 2.0))
                    background = background.crop((bg_x0, bg_y0, bg_x0 + bg_cw, bg_y0 + bg_ch))
                bg_w, bg_h = background.size
                composite = background.copy()
                bx = (bg_w - img.width) // 2
                by = (bg_h - img.height) // 2
                composite.paste(img, (bx, by), img)
                img = composite
            except Exception:
                pass

        return img

    def save_stabilized_frames_dialog(self):
        if not self.animation_frames:
            messagebox.showwarning("No Frames", "No frames loaded to stabilize.")
            return
        if not self.stabilize_cache.get("shifts"):
            self.run_auto_stabilization()
            if not self.stabilize_cache.get("shifts"):
                return
        out_dir = filedialog.askdirectory(title="Select Folder to Save Stabilized Frames")
        if not out_dir:
            return
        cw = self.stabilize_cache.get("current_w", "unknown")
        ch = self.stabilize_cache.get("current_h", "unknown")
        count = 0
        for i in range(len(self.animation_frame_order)):
            frame = self.get_processed_frame(i)
            if frame:
                pad_len = len(str(len(self.animation_frame_order)))
                fname = f"stabilized_{str(count + 1).zfill(pad_len)}.png"
                frame.save(os.path.join(out_dir, fname))
                count += 1
        messagebox.showinfo("Stabilized Frames Saved", f"Successfully saved {count} stabilized frames ({cw}x{ch}) to:\n{out_dir}")

    def move_frame_up(self):
        sel = self.frame_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        (self.animation_frame_order[idx - 1],
         self.animation_frame_order[idx]) = (
            self.animation_frame_order[idx],
            self.animation_frame_order[idx - 1]
        )
        self.refresh_frame_listbox()
        self.frame_listbox.selection_set(idx - 1)

    def move_frame_down(self):
        sel = self.frame_listbox.curselection()
        if not sel or sel[0] >= len(self.animation_frame_order) - 1:
            return
        idx = sel[0]
        (self.animation_frame_order[idx],
         self.animation_frame_order[idx + 1]) = (
            self.animation_frame_order[idx + 1],
            self.animation_frame_order[idx]
        )
        self.refresh_frame_listbox()
        self.frame_listbox.selection_set(idx + 1)

    def reverse_frame_order(self):
        self.animation_frame_order.reverse()
        self.refresh_frame_listbox()

    def reset_frame_order(self):
        self.animation_frame_order = list(range(len(self.animation_frames)))
        self.refresh_frame_listbox()

    def clear_animation_frames(self):
        self.animation_frames = []
        self.animation_frame_order = []
        self.bg_image_path = None
        if hasattr(self, "bg_label_var"):
            self.bg_label_var.set("No background selected")
        self.refresh_frame_listbox()

    def on_frame_drag_start(self, event):
        self.drag_start_index = self.frame_listbox.nearest(event.y)

    def on_frame_drag_release(self, event):
        end_idx = self.frame_listbox.nearest(event.y)
        if (self.drag_start_index is not None
                and end_idx != self.drag_start_index
                and 0 <= end_idx < len(self.animation_frame_order)):
            (self.animation_frame_order[self.drag_start_index],
             self.animation_frame_order[end_idx]) = (
                self.animation_frame_order[end_idx],
                self.animation_frame_order[self.drag_start_index]
            )
            self.refresh_frame_listbox()
            self.frame_listbox.selection_set(end_idx)
        self.drag_start_index = None

    # -----------------------------------------------------------------------
    # EXPORT GIF
    # -----------------------------------------------------------------------
    def export_gif(self):
        if not self.animation_frames:
            messagebox.showwarning("No Frames",
                "Load frames first using 'Load Frames from Folder'.")
            return

        out_path = self.gif_output_path_var.get().strip()
        if not out_path:
            out_path = filedialog.asksaveasfilename(
                title="Save GIF As…",
                defaultextension=".gif",
                filetypes=[("GIF files", "*.gif"), ("All files", "*.*")],
                initialdir=self.last_output_dir or os.getcwd()
            )
            if not out_path:
                return
            self.gif_output_path_var.set(out_path)

        try:
            delay = int(self.frame_delay_var.get())
        except ValueError:
            delay = 100
        try:
            loop = int(self.loop_count_var.get())
        except ValueError:
            loop = 0

        ordered_paths = [
            self.animation_frames[i] for i in self.animation_frame_order
        ]
        
        # Restrict export to timeline range (smaller region)
        n = len(ordered_paths)
        try:
            start = int(self.range_start_var.get())
        except ValueError:
            start = 1
        try:
            end = int(self.range_end_var.get())
        except ValueError:
            end = n
            
        start = max(1, min(n, start))
        end = max(1, min(n, end))
        if start > end:
            start, end = end, start
            
        frames = []
        for idx in range(start - 1, end):
            frame_img = self.get_processed_frame(idx)
            if frame_img:
                frames.append(frame_img)

        if not frames:
            messagebox.showwarning("No Frames", "No frames to export.")
            return

        converted = [
            f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=256)
            for f in frames
        ]

        try:
            converted[0].save(
                out_path,
                save_all=True,
                append_images=converted[1:],
                duration=delay,
                loop=loop,
                optimize=False
            )
            messagebox.showinfo(
                "GIF Exported",
                f"GIF saved to:\n{out_path}\n\n"
                f"{len(converted)} frames  •  {delay}ms delay  •  loop={loop}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save GIF:\n{e}")

    # -----------------------------------------------------------------------
    # INTEGRATED GIF PREVIEW AND TIMELINE METHODS
    # -----------------------------------------------------------------------
    def toggle_gif_preview(self):
        if not self.animation_frames:
            # Try to auto-load frames from the last output directory if available
            if self.last_output_dir and os.path.exists(self.last_output_dir):
                exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
                found = []
                try:
                    for fname in os.listdir(self.last_output_dir):
                        if os.path.splitext(fname)[1].lower() in exts:
                            found.append(os.path.join(self.last_output_dir, fname))
                except Exception:
                    pass
                found.sort()
                if found:
                    self.animation_frames = found
                    self.animation_frame_order = list(range(len(found)))
                    self.refresh_frame_listbox()
            
            if not self.animation_frames:
                messagebox.showwarning("No Frames", "Please load frames from a folder first.")
                return

        if self.preview_mode == "storyboard":
            self.start_gif_preview()
        else:
            self.stop_gif_preview()

    def start_gif_preview(self):
        self.preview_mode = "gif"
        self.is_playing_anim = True
        self.play_pause_btn.config(text="⏸")
        self.preview_gif_btn.config(text="🛑 Stop Preview", style="Stop.TButton")
        self.canvas_img_id = None
        
        n = len(self.animation_frames)
        self.range_start_spin.config(from_=1, to=n)
        self.range_end_spin.config(from_=1, to=n)
        
        # Pre-fill range if defaults
        if self.range_start_var.get() == "1" and self.range_end_var.get() == "1":
            self.range_end_var.set(str(n))
        
        self.timeline_slider.config(from_=1.0, to=float(n))
        
        if self.preview_gif_job:
            try:
                self.root.after_cancel(self.preview_gif_job)
            except Exception:
                pass
            self.preview_gif_job = None
            
        try:
            start_val = int(self.range_start_var.get())
        except ValueError:
            start_val = 1
        self.current_anim_frame_idx = start_val
        
        self.animate_step()

    def stop_gif_preview(self):
        self.preview_mode = "storyboard"
        self.preview_gif_btn.config(text="▶ Preview GIF", style="TButton")
        
        if self.preview_gif_job:
            try:
                self.root.after_cancel(self.preview_gif_job)
            except Exception:
                pass
            self.preview_gif_job = None
            
        self.update_preview()

    # -----------------------------------------------------------------------
    # TIMELINE & PLAY/PAUSE METHODS
    # -----------------------------------------------------------------------
    def toggle_play_pause(self):
        self.is_playing_anim = not self.is_playing_anim
        if self.is_playing_anim:
            self.play_pause_btn.config(text="⏸")
            self.animate_step()
        else:
            self.play_pause_btn.config(text="▶")

    def on_timeline_slide(self, val):
        self.current_anim_frame_idx = int(float(val))
        if self.preview_mode == "gif":
            if self.is_scrubbing or not self.is_playing_anim:
                self.draw_gif_frame()
        else:
            if self.is_scrubbing or not self.is_playing_anim:
                self.update_preview()

    def on_slider_press(self):
        self.is_scrubbing = True
        if self.preview_gif_job:
            try:
                self.root.after_cancel(self.preview_gif_job)
            except Exception:
                pass
            self.preview_gif_job = None

    def on_slider_release(self):
        self.is_scrubbing = False
        if self.is_playing_anim:
            self.animate_step()

    def on_range_changed(self):
        n = len(self.animation_frames)
        if n == 0:
            return
        try:
            start = int(self.range_start_var.get())
        except ValueError:
            start = 1
        try:
            end = int(self.range_end_var.get())
        except ValueError:
            end = n
            
        start = max(1, min(n, start))
        end = max(1, min(n, end))
        
        if start > end:
            start = end
            self.range_start_var.set(str(start))
            
        self.range_start_spin.config(to=end)
        self.range_end_spin.config(from_=start)
        
        if self.current_anim_frame_idx < start or self.current_anim_frame_idx > end:
            self.current_anim_frame_idx = start
            self.animate_step()

    def draw_gif_frame(self):
        if not self.animation_frames:
            return
        n = len(self.animation_frames)
        frame_idx = self.current_anim_frame_idx - 1
        if 0 <= frame_idx < n:
            try:
                frame_img = self.get_processed_frame(frame_idx)
                if not frame_img:
                    return
                
                cw = self.canvas_container.winfo_width()
                ch = self.canvas_container.winfo_height()
                if cw < 100: cw = 600
                if ch < 100: ch = 500
                
                fw, fh = frame_img.size
                scale = min(cw / fw, ch / fh, 1.0)
                nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
                
                resamp = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
                resized_img = frame_img.resize((nw, nh), resamp)
                
                self.preview_tk = ImageTk.PhotoImage(resized_img)
                
                canvas_w = max(cw, self.canvas.winfo_width())
                canvas_h = max(ch, self.canvas.winfo_height())
                dx = max(0, (canvas_w - nw) // 2)
                dy = max(0, (canvas_h - nh) // 2)
                
                cid = getattr(self, "canvas_img_id", None)
                if cid is None or cid not in self.canvas.find_all():
                    self.canvas.delete("all")
                    self.canvas_img_id = self.canvas.create_image(dx, dy, anchor=tk.NW, image=self.preview_tk)
                else:
                    self.canvas.coords(self.canvas_img_id, dx, dy)
                    self.canvas.itemconfig(self.canvas_img_id, image=self.preview_tk)
                    
                self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))
            except Exception as e:
                self.canvas.delete("all")
                self.canvas_img_id = None
                self.canvas.create_text(
                    self.canvas.winfo_width() // 2, self.canvas.winfo_height() // 2,
                    text=f"Error loading frame {self.current_anim_frame_idx}:\n{e}",
                    justify=tk.CENTER, fill=SUBTEXT, font=("Helvetica", 10)
                )

    def animate_step(self):
        if self.preview_mode != "gif" or not self.animation_frames:
            return

        n = len(self.animation_frames)
        try:
            start = int(self.range_start_var.get())
        except ValueError:
            start = 1
        try:
            end = int(self.range_end_var.get())
        except ValueError:
            end = n
            
        start = max(1, min(n, start))
        end = max(1, min(n, end))
        if start > end:
            start, end = end, start

        self.frame_counter_lbl.config(text=f"Frame {self.current_anim_frame_idx} / {n}")

        self.timeline_slider.config(from_=1.0, to=float(n))
        self.timeline_slider_var.set(float(self.current_anim_frame_idx))

        self.draw_gif_frame()

        if self.is_playing_anim and not self.is_scrubbing:
            try:
                delay = int(self.frame_delay_var.get())
            except ValueError:
                delay = 100
            
            next_idx = self.current_anim_frame_idx + 1
            if next_idx > end:
                next_idx = start
            self.current_anim_frame_idx = next_idx
            
            self.preview_gif_job = self.root.after(delay, self.animate_step)

    # -----------------------------------------------------------------------
    # STORYBOARD GRID METHODS
    # -----------------------------------------------------------------------
    def on_tab_changed(self, event=None):
        try:
            sel = self.notebook.select()
            if not sel:
                return
            tab_idx = self.notebook.index(sel)
        except Exception:
            return
        if tab_idx == 0:  # Slice tab
            if self.preview_gif_job:
                try:
                    self.root.after_cancel(self.preview_gif_job)
                except Exception:
                    pass
                self.preview_gif_job = None
            self.preview_mode = "grid"
            self.timeline_frame.grid_remove()
            self.bottom_bar.grid(row=2, column=0, sticky="ew")
            self.update_preview()
        elif tab_idx == 1:  # Animate tab
            if self.preview_gif_job:
                try:
                    self.root.after_cancel(self.preview_gif_job)
                except Exception:
                    pass
                self.preview_gif_job = None
            self.preview_mode = "storyboard"
            self.preview_gif_btn.config(text="▶ Preview GIF", style="TButton")
            self.bottom_bar.grid_remove()
            self.timeline_frame.grid(row=2, column=0, sticky="ew")
            
            # Configure timeline bounds
            n = len(self.animation_frames)
            if n > 0:
                self.range_start_spin.config(from_=1, to=n)
                self.range_end_spin.config(from_=1, to=n)
                self.timeline_slider.config(from_=1.0, to=float(n))
                
            self.update_preview()
        elif tab_idx == 2:  # Extract tab
            if self.preview_gif_job:
                try:
                    self.root.after_cancel(self.preview_gif_job)
                except Exception:
                    pass
                self.preview_gif_job = None
            self.preview_mode = "extract"
            self.timeline_frame.grid_remove()
            self.bottom_bar.grid_remove()
            self.update_preview()

    def delete_selected_frame(self):
        sel = self.frame_listbox.curselection()
        if not sel:
            return
        self.delete_frame_by_index(sel[0])

    def delete_frame_by_index(self, index):
        if 0 <= index < len(self.animation_frame_order):
            self.animation_frame_order.pop(index)
            self.refresh_frame_listbox()
            
            n = len(self.animation_frame_order)
            if n > 0:
                self.range_start_spin.config(from_=1, to=n)
                self.range_end_spin.config(from_=1, to=n)
                self.timeline_slider.config(from_=1.0, to=float(n))
                
                try:
                    start = int(self.range_start_var.get())
                except ValueError:
                    start = 1
                try:
                    end = int(self.range_end_var.get())
                except ValueError:
                    end = n
                start = max(1, min(n, start))
                end = max(1, min(n, end))
                if start > end: start = end
                self.range_start_var.set(str(start))
                self.range_end_var.set(str(end))
                
                if self.current_anim_frame_idx > n:
                    self.current_anim_frame_idx = n
            else:
                self.current_anim_frame_idx = 1
                self.range_start_var.set("1")
                self.range_end_var.set("1")
                
            self.update_preview()

    def draw_storyboard_grid(self):
        self.canvas.delete("all")
        self.storyboard_cells = []
        self.storyboard_photos = []
        
        if not self.animation_frames:
            cw = max(400, self.canvas.winfo_width())
            ch = max(400, self.canvas.winfo_height())
            self.canvas.create_text(
                cw // 2, ch // 2,
                text="No Frames Loaded\nClick 'Load Frames from Folder' in the Animate tab.",
                justify=tk.CENTER, fill=SUBTEXT, font=("Helvetica", 11)
            )
            self.canvas.config(scrollregion=(0, 0, cw, ch))
            return

        n = len(self.animation_frames)
        cw = self.canvas_container.winfo_width()
        ch = self.canvas_container.winfo_height()
        if cw < 100: cw = 600
        if ch < 100: ch = 500

        try:
            cols = int(self.cols_var.get())
            if cols <= 0: cols = 3
        except ValueError:
            cols = 3
        rows = math.ceil(n / cols)

        margin = 15
        cell_w = max(60, (cw - margin * (cols + 1)) // cols)
        cell_h = max(60, (ch - margin * (rows + 1)) // rows)
        
        cell_w = min(180, cell_w)
        cell_h = min(180, cell_h)
        
        scroll_w = max(cw, cols * (cell_w + margin) + margin)
        scroll_h = max(ch, rows * (cell_h + margin) + margin)
        self.canvas.config(scrollregion=(0, 0, scroll_w, scroll_h))

        for i in range(n):
            ordered_idx = self.animation_frame_order[i]
            frame_path = self.animation_frames[ordered_idx]
            
            col = i % cols
            row = i // cols
            
            x1 = margin + col * (cell_w + margin)
            y1 = margin + row * (cell_h + margin)
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            
            self.storyboard_cells.append({
                "bbox": (x1, y1, x2, y2),
                "del_bbox": (x2 - 25, y1 + 3, x2 - 3, y1 + 25),
                "index": i
            })
            
            try:
                img = self.get_processed_frame(i)
                if not img:
                    continue
                
                img.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                
                # Shaded translucent layer (140 opacity)
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 140))
                shaded = Image.alpha_composite(img, overlay)
                
                photo = ImageTk.PhotoImage(shaded)
                self.storyboard_photos.append(photo)
                
                tx = x1 + (cell_w - shaded.width) // 2
                ty = y1 + (cell_h - shaded.height) // 2
                
                self.canvas.create_image(tx, ty, anchor=tk.NW, image=photo)
                
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                
                # Draw circular badge backing
                self.canvas.create_oval(
                    cx - 18, cy - 18, cx + 18, cy + 18,
                    fill="#1c1c1e", outline="#ffffff", width=1.5
                )
                self.canvas.create_text(
                    cx, cy, text=str(i + 1), fill="white",
                    font=("Helvetica", 12, "bold")
                )
                
                # Draw small delete '✕' button in top-right corner
                self.canvas.create_oval(
                    x2 - 22, y1 + 6, x2 - 6, y1 + 22,
                    fill="#e94560", outline="#ffffff", width=1.5
                )
                self.canvas.create_text(
                    x2 - 14, y1 + 14, text="✕", fill="white",
                    font=("Helvetica", 9, "bold")
                )
                
                # Draw border highlight if active
                is_active = (i + 1 == self.current_anim_frame_idx)
                outline_color = ACCENT if is_active else BORDER
                outline_width = 3 if is_active else 1
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline=outline_color, width=outline_width
                )
            except Exception:
                self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=CARD, outline=BORDER, width=1
                )
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                self.canvas.create_text(
                    cx, cy, text=f"Err\n{i+1}", fill=TEXT,
                    font=("Helvetica", 10, "bold")
                )

    def on_storyboard_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        self.dragged_cell_idx = -1
        if hasattr(self, "storyboard_cells"):
            for cell in self.storyboard_cells:
                idx = cell["index"]
                
                # Check delete button click first
                dx1, dy1, dx2, dy2 = cell["del_bbox"]
                if dx1 <= cx <= dx2 and dy1 <= cy <= dy2:
                    self.delete_frame_by_index(idx)
                    return
                
                # Check cell dragging click
                x1, y1, x2, y2 = cell["bbox"]
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    self.dragged_cell_idx = idx
                    self.drag_start_x = cx
                    self.drag_start_y = cy
                    break
                    
        if self.dragged_cell_idx != -1:
            x1, y1, x2, y2 = self.storyboard_cells[self.dragged_cell_idx]["bbox"]
            self.drag_rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline=ACCENT, width=3
            )

    def on_storyboard_drag(self, event):
        if getattr(self, "dragged_cell_idx", -1) == -1:
            return
            
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        dx = cx - self.drag_start_x
        dy = cy - self.drag_start_y
        
        x1, y1, x2, y2 = self.storyboard_cells[self.dragged_cell_idx]["bbox"]
        self.canvas.coords(self.drag_rect_id, x1 + dx, y1 + dy, x2 + dx, y2 + dy)

    def on_canvas_release(self, event):
        if self.preview_mode == "storyboard":
            self.on_storyboard_release(event)

    def on_storyboard_release(self, event):
        if getattr(self, "dragged_cell_idx", -1) == -1:
            return
            
        self.canvas.delete(self.drag_rect_id)
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        
        target_idx = -1
        if hasattr(self, "storyboard_cells"):
            for cell in self.storyboard_cells:
                x1, y1, x2, y2 = cell["bbox"]
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    target_idx = cell["index"]
                    break
                    
        if target_idx != -1 and target_idx != self.dragged_cell_idx:
            item = self.animation_frame_order.pop(self.dragged_cell_idx)
            self.animation_frame_order.insert(target_idx, item)
            self.refresh_frame_listbox()
            self.update_preview()
            
        self.dragged_cell_idx = -1

    # -----------------------------------------------------------------------
    # SPRITE EXTRACTOR METHODS
    # -----------------------------------------------------------------------
    def extract_sprite_logic(self):
        source_path = self.extract_source_var.get().strip()
        if not source_path or not os.path.exists(source_path):
            messagebox.showerror("Error", "Please select a valid source frame image first.")
            return None
            
        try:
            src_img = Image.open(source_path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load source image:\n{e}")
            return None
            
        tol = int(self.extract_tol_var.get())
        mode = self.extract_mode_var.get()
        
        from PIL import ImageChops
        
        if mode == "color":
            color_hex = self.extract_color_var.get().strip().lstrip('#')
            if len(color_hex) != 6:
                messagebox.showerror("Error", "Key color must be a valid 6-character hex string (e.g. #FFFFFF).")
                return None
            try:
                target_r = int(color_hex[0:2], 16)
                target_g = int(color_hex[2:4], 16)
                target_b = int(color_hex[4:6], 16)
            except ValueError:
                messagebox.showerror("Error", "Invalid key color format.")
                return None
                
            r, g, b, a = src_img.split()
            dr = r.point(lambda p: abs(p - target_r))
            dg = g.point(lambda p: abs(p - target_g))
            db = b.point(lambda p: abs(p - target_b))
            dist = ImageChops.add(ImageChops.add(dr, dg), db)
            mask = dist.point(lambda p: 0 if p <= tol else 255)
            new_a = ImageChops.darker(a, mask)
            extracted = Image.merge("RGBA", (r, g, b, new_a))
            return extracted
            
        elif mode == "diff":
            bg_path = self.extract_bg_var.get().strip()
            if not bg_path or not os.path.exists(bg_path):
                messagebox.showerror("Error", "Please select a valid reference background image first.")
                return None
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load background image:\n{e}")
                return None
                
            if bg_img.size != src_img.size:
                resamp = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
                bg_img = bg_img.resize(src_img.size, resamp)
                
            sr, sg, sb, sa = src_img.split()
            br, bg, bb, ba = bg_img.split()
            dr = ImageChops.difference(sr, br)
            dg = ImageChops.difference(sg, bg)
            db = ImageChops.difference(sb, bb)
            dist = ImageChops.add(ImageChops.add(dr, dg), db)
            mask = dist.point(lambda p: 0 if p <= tol else 255)
            new_a = ImageChops.darker(sa, mask)
            extracted = Image.merge("RGBA", (sr, sg, sb, new_a))
            return extracted
            
        return None

    def preview_extracted_sprite(self):
        extracted = self.extract_sprite_logic()
        if extracted:
            self.extracted_sprite_img = extracted
            self.preview_mode = "extract"
            self.update_preview()
            
    def save_extracted_sprite(self):
        extracted = self.extract_sprite_logic()
        if not extracted:
            return
            
        filename = filedialog.asksaveasfilename(
            title="Save Extracted Sprite",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            initialdir=os.getcwd()
        )
        if filename:
            try:
                extracted.save(filename, "PNG")
                messagebox.showinfo("Success", f"Extracted sprite saved successfully to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save sprite:\n{e}")

    def create_checkerboard(self, width, height, tile_size=12):
        bg = Image.new("RGBA", (width, height), "#ffffff")
        draw = ImageDraw.Draw(bg)
        for y in range(0, height, tile_size):
            for x in range(0, width, tile_size):
                if ((x // tile_size) + (y // tile_size)) % 2 == 1:
                    draw.rectangle([x, y, x + tile_size, y + tile_size], fill="#d1d1d6")
        return bg

    def draw_extract_preview(self):
        if not self.extracted_sprite_img:
            return
        cw = self.canvas_container.winfo_width()
        ch = self.canvas_container.winfo_height()
        if cw < 100: cw = 600
        if ch < 100: ch = 500
        
        fw, fh = self.extracted_sprite_img.size
        scale = min(cw / fw, ch / fh, 1.0)
        nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
        
        resamp = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.ANTIALIAS
        resized_img = self.extracted_sprite_img.resize((nw, nh), resamp)
        
        checkerboard = self.create_checkerboard(nw, nh)
        preview_img = Image.new("RGBA", (nw, nh))
        preview_img.paste(checkerboard, (0, 0))
        preview_img.paste(resized_img, (0, 0), resized_img)
        
        self.preview_tk = ImageTk.PhotoImage(preview_img)
        self.canvas.delete("all")
        
        canvas_w = max(cw, self.canvas.winfo_width())
        canvas_h = max(ch, self.canvas.winfo_height())
        dx = max(0, (canvas_w - nw) // 2)
        dy = max(0, (canvas_h - nh) // 2)
        
        self.canvas.create_image(dx, dy, anchor=tk.NW, image=self.preview_tk)
        self.canvas.config(scrollregion=(0, 0, canvas_w, canvas_h))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app  = ImageSlicerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
