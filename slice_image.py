#!/usr/bin/env python3
import os
import sys
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw

# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------
BG        = "#f0f2f5"  # Soft light grey background
SURFACE   = "#ffffff"  # Crisp white for main surface cards and canvas background
CARD      = "#e5e5ea"  # Muted grey for containers/panels
ACCENT    = "#007aff"  # Beautiful system blue
ACCENT2   = "#5856d6"  # Indigo for secondary actions
TEXT      = "#1c1c1e"  # Dark grey/black for primary text
SUBTEXT   = "#3a3a3c"  # Darker medium grey for secondary readable text (highly readable!)
GREEN     = "#28a745"  # Forest green for lines/borders
BORDER    = "#d1d1d6"  # Muted divider borders
CANVAS_BG = "#e5e5ea"  # Muted light grey background for the preview canvas


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

        # Apply light style
        self.apply_light_style()

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
    # DARK STYLE
    # -----------------------------------------------------------------------
    def apply_light_style(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame",            background=BG)
        self.style.configure("TLabel",            background=BG, foreground=TEXT)
        self.style.configure("TButton",           background=SURFACE, foreground=TEXT,
                                                  bordercolor=BORDER, focuscolor=ACCENT, padding=6)
        self.style.map("TButton",                 background=[("active", CARD), ("pressed", ACCENT)])
        self.style.configure("Accent.TButton",    background=ACCENT, foreground="white",
                                                  font=("Helvetica", 10, "bold"), padding=8)
        self.style.map("Accent.TButton",          background=[("active", "#005ecb"), ("pressed", "#004b9b")])
        self.style.configure("Secondary.TButton", background=ACCENT2, foreground="white", padding=6)
        self.style.map("Secondary.TButton",       background=[("active", "#4745ab")])
        self.style.configure("TEntry",            fieldbackground=SURFACE, foreground=TEXT,
                                                  insertcolor=TEXT, bordercolor=BORDER)
        self.style.configure("TNotebook",         background=BG, bordercolor=BORDER)
        self.style.configure("TNotebook.Tab",     background=CARD, foreground=SUBTEXT,
                                                  padding=[12, 6])
        self.style.map("TNotebook.Tab",           background=[("selected", SURFACE)],
                                                  foreground=[("selected", TEXT)])
        self.style.configure("TScrollbar",        background=SURFACE, troughcolor=BG,
                                                  bordercolor=BORDER, arrowcolor=TEXT)
        self.style.configure("TSpinbox",          fieldbackground=SURFACE, foreground=TEXT,
                                                  bordercolor=BORDER, arrowcolor=TEXT)
        self.style.configure("TLabelframe",       background=BG, bordercolor=BORDER)
        self.style.configure("TLabelframe.Label", background=BG, foreground=ACCENT)
        self.style.configure("TRadiobutton",      background=BG, foreground=TEXT)
        self.style.configure("TCheckbutton",      background=BG, foreground=TEXT)
        self.style.configure("TSeparator",        background=BORDER)

    # -----------------------------------------------------------------------
    # BUILD LEFT PANEL (scrollable)
    # -----------------------------------------------------------------------
    def _build_left_panel(self):
        left_outer = tk.Frame(self.paned, bg=BG, width=375)
        left_outer.pack_propagate(False)
        self.paned.add(left_outer, minsize=320)

        scroll_canvas = tk.Canvas(left_outer, bg=BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(left_outer, orient="vertical", command=scroll_canvas.yview)
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
        self.tab_settings = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_slice,    text="✂ Slice")
        self.notebook.add(self.tab_animate,  text="🎬 Animate")
        self.notebook.add(self.tab_settings, text="⚙ Settings")

        self._build_slice_tab(self.tab_slice)
        self._build_animate_tab(self.tab_animate)
        self._build_settings_tab(self.tab_settings)

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

    def _dark_entry(self, parent, textvariable, width=12):
        return tk.Entry(
            parent, textvariable=textvariable, width=width,
            bg=CARD, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=("Helvetica", 9),
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT
        )

    def _dark_btn(self, parent, text, command, bg=None, fg=None,
                  font=None, padx=None, pady=None, default=None):
        return ttk.Button(parent, text=text, command=command, default=default)

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
        tk.Entry(out_f, textvariable=self.output_dir_var,
                 bg=CARD, fg=SUBTEXT, insertbackground=TEXT,
                 relief="flat", font=("Helvetica", 9), state="disabled",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, disabledbackground=CARD,
                 disabledforeground=SUBTEXT
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
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
        tk.Entry(name_card, textvariable=self.subfolder_var,
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Helvetica", 9),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT
                 ).grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=3)

        tk.Label(name_card, text="File Prefix:", bg=CARD, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=1, column=0, sticky=tk.W, pady=3)
        self.prefix_var = tk.StringVar(value="{filename}_")
        tk.Entry(name_card, textvariable=self.prefix_var,
                 bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Helvetica", 9),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT
                 ).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=3)

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
        ttk.Button(parent, text="✂  Slice Image", command=self.slice_image,
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

        ttk.Button(parent, text="🎬  Export GIF", command=self.export_gif,
                   default="active"
                   ).pack(fill=tk.X, padx=12, pady=(4, 14), ipady=5)

    # -----------------------------------------------------------------------
    # TAB 3: SETTINGS
    # -----------------------------------------------------------------------
    def _build_settings_tab(self, parent):
        card = tk.Frame(parent, bg=CARD, padx=14, pady=14)
        card.pack(fill=tk.X, padx=12, pady=(18, 8))
        tk.Label(card, text="⚙  Settings coming soon...",
                 bg=CARD, fg=ACCENT, font=("Helvetica", 12, "bold")
                 ).pack(anchor=tk.W, pady=(0, 8))
        tk.Label(card, bg=CARD, fg=SUBTEXT, font=("Helvetica", 9), justify=tk.LEFT,
                 text=(
                     "Future options:\n"
                     "  • Default output format\n"
                     "  • Detection sensitivity\n"
                     "  • Preview quality\n"
                     "  • Keyboard shortcuts"
                 )).pack(anchor=tk.W)

    # -----------------------------------------------------------------------
    # BUILD RIGHT PANEL
    # -----------------------------------------------------------------------
    def _build_right_panel(self):
        right_outer = tk.Frame(self.paned, bg=BG)
        self.paned.add(right_outer, minsize=400)
        right_outer.columnconfigure(0, weight=1)
        right_outer.rowconfigure(1, weight=1)
        right_outer.rowconfigure(0, weight=0)
        right_outer.rowconfigure(2, weight=0)

        # Header strip
        header = tk.Frame(right_outer, bg=SURFACE, height=34)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="Live Preview",
                 bg=SURFACE, fg=TEXT, font=("Helvetica", 11, "bold")
                 ).pack(side=tk.LEFT, padx=14, pady=6)

        # Canvas container
        self.canvas_container = tk.Frame(right_outer, bg=CANVAS_BG)
        self.canvas_container.grid(row=1, column=0, sticky="nsew")
        self.canvas_container.rowconfigure(0, weight=1)
        self.canvas_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self.canvas_container, bg=CANVAS_BG, bd=0, highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas_container.bind("<Configure>", self.on_canvas_resize)

        # Bottom bar
        self.bottom_bar = tk.Frame(right_outer, bg=SURFACE, height=36)
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
        self.timeline_frame = tk.Frame(right_outer, bg=SURFACE, height=36)
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
        self.canvas.config(scrollregion=(0, 0, 400, 400))
        cw = max(400, self.canvas.winfo_width())
        ch = max(400, self.canvas.winfo_height())
        self.canvas.create_text(
            cw // 2, ch // 2,
            text="No Image Loaded\nClick 'Browse…' in the Slice tab to select an image.",
            justify=tk.CENTER, fill=SUBTEXT, font=("Helvetica", 11)
        )

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
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Grid Image to Slice",
            filetypes=(("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                       ("All files", "*.*")),
            initialdir=os.getcwd()
        )
        if filename:
            self.file_path_var.set(filename)
            try:
                self.original_img = Image.open(filename)
                self.zoom_level = 1.0
                self.detected_col_groups       = None
                self.detected_row_groups       = None
                self.detected_border_x_val     = None
                self.detected_border_y_val     = None
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
            except Exception as e:
                self.original_img = None
                self.preview_base_img = None
                self.draw_placeholder()
                messagebox.showerror("Error", f"Failed to load image:\n{e}")
            if not self.custom_output_dir:
                self.output_dir_var.set("[sliced-images/ in app directory]")

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

        def check_col(x):
            sample_y = [0, H // 4, H // 2, 3 * H // 4, H - 1]
            samples  = [img.getpixel((x, y)) for y in sample_y]
            ref = samples[0]
            for p in samples[1:]:
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
                if is_unif and dist <= 245:
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
                if is_unif and dist <= 245:
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
                if is_unif and dist <= 245:
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
                if is_unif and dist <= 245:
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

        has_left_outer  = False
        has_right_outer = False
        if col_groups:
            if any(i in col_groups[0] for i in range(5)):
                has_left_outer = True
            if any((W - 1 - i) in col_groups[-1] for i in range(5)):
                has_right_outer = True

        has_top_outer    = False
        has_bottom_outer = False
        if row_groups:
            if any(i in row_groups[0] for i in range(5)):
                has_top_outer = True
            if any((H - 1 - i) in row_groups[-1] for i in range(5)):
                has_bottom_outer = True

        col_widths = [len(g) for g in expanded_col_groups]
        row_widths = [len(g) for g in expanded_row_groups]

        detected_border_x = (int(sorted(col_widths)[len(col_widths) // 2])
                              if col_widths else 0)
        detected_border_y = (int(sorted(row_widths)[len(row_widths) // 2])
                              if row_widths else 0)

        N_col_groups = len(col_groups)
        if N_col_groups > 0:
            if has_left_outer and has_right_outer:
                detected_cols = N_col_groups - 1
                border_layout = "all"
            elif not has_left_outer and not has_right_outer:
                detected_cols = N_col_groups + 1
                border_layout = "between"
            else:
                detected_cols = N_col_groups
                border_layout = "all"
        else:
            detected_cols = 1
            border_layout = "between"

        N_row_groups = len(row_groups)
        if N_row_groups > 0:
            if has_top_outer and has_bottom_outer:
                detected_rows = N_row_groups - 1
            elif not has_top_outer and not has_bottom_outer:
                detected_rows = N_row_groups + 1
            else:
                detected_rows = N_row_groups
        else:
            detected_rows = 1

        return {
            "cols":       detected_cols,
            "rows":       detected_rows,
            "border_x":   detected_border_x,
            "border_y":   detected_border_y,
            "layout":     border_layout,
            "col_groups": col_groups,
            "row_groups": row_groups,
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
        if has_outer_start:
            start_idx     = 1
            current_start = borders[0][1] + 1
        else:
            start_idx     = 0
            current_start = 0

        for i in range(start_idx, N_g):
            cell_end = borders[i][0] - 1
            cells.append((current_start, cell_end))
            current_start = borders[i][1] + 1

        if not has_outer_end:
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

    def load_frames_for_animation(self):
        initial = os.getcwd()
        default_parent = os.path.join(get_app_run_dir(), "sliced-images")
        if self.last_output_dir:
            initial = os.path.dirname(self.last_output_dir)
        elif os.path.exists(default_parent):
            initial = default_parent
        elif self.custom_output_dir and os.path.exists(self.custom_output_dir):
            initial = self.custom_output_dir
        elif self.file_path_var.get().strip():
            in_img = self.file_path_var.get().strip()
            if os.path.exists(in_img):
                initial = os.path.dirname(in_img)

        folder  = filedialog.askdirectory(
            title="Select Folder Containing Frames", initialdir=initial)
        if not folder:
            return
        exts  = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        found = []
        try:
            for fname in os.listdir(folder):
                if os.path.splitext(fname)[1].lower() in exts:
                    found.append(os.path.join(folder, fname))
        except OSError as e:
            messagebox.showerror("Error", f"Could not read folder:\n{e}")
            return
        found.sort()
        if not found:
            messagebox.showinfo("No Frames",
                "No image files found in the selected folder.")
            return
        self.animation_frames      = found
        self.animation_frame_order = list(range(len(found)))
        self.refresh_frame_listbox()
        
        n = len(found)
        self.range_start_spin.config(from_=1, to=n)
        self.range_end_spin.config(from_=1, to=n)
        self.range_start_var.set("1")
        self.range_end_var.set(str(n))
        self.timeline_slider.config(from_=1.0, to=float(n))
        self.timeline_slider_var.set(1.0)
        self.current_anim_frame_idx = 1
        
        self.status_label.config(
            text=f"Loaded {n} animation frame{'s' if n != 1 else ''} from folder.",
            fg=GREEN
        )
        self.update_preview()

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
            
        ordered_paths = ordered_paths[start - 1:end]

        use_bg = self.use_bg_var.get() and len(self.animation_frames) > 0

        if use_bg:
            try:
                bg_idx = int(self.bg_frame_index_var.get())
                if bg_idx < 1: bg_idx = 1
                if bg_idx > len(self.animation_frames): bg_idx = len(self.animation_frames)
            except ValueError:
                bg_idx = 1
            bg_path = self.animation_frames[self.animation_frame_order[bg_idx - 1]]
            try:
                background = Image.open(bg_path).convert("RGBA")
            except Exception as e:
                messagebox.showerror("Error",
                    f"Could not open background frame image:\n{bg_path}\n{e}")
                return
            bg_w, bg_h = background.size
            frames = []
            for frame_path in ordered_paths:
                try:
                    sprite    = Image.open(frame_path).convert("RGBA")
                    composite = background.copy()
                    x = (bg_w - sprite.width)  // 2
                    y = (bg_h - sprite.height) // 2
                    composite.paste(sprite, (x, y), sprite)
                    frames.append(composite)
                except Exception as e:
                    messagebox.showerror("Error",
                        f"Could not open frame:\n{frame_path}\n{e}")
                    return
        else:
            frames = []
            for frame_path in ordered_paths:
                try:
                    frames.append(Image.open(frame_path).convert("RGBA"))
                except Exception as e:
                    messagebox.showerror("Error",
                        f"Could not open frame:\n{frame_path}\n{e}")
                    return

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
        self.preview_gif_btn.config(text="▶ Preview GIF", default="active")
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
        self.preview_gif_btn.config(text="▶ Preview GIF", default="normal")
        
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
            ordered_idx = self.animation_frame_order[frame_idx]
            frame_path = self.animation_frames[ordered_idx]
            try:
                frame_img = Image.open(frame_path).convert("RGBA")
                
                if self.use_bg_var.get() and len(self.animation_frames) > 0:
                    try:
                        bg_idx = int(self.bg_frame_index_var.get())
                        if bg_idx < 1: bg_idx = 1
                        if bg_idx > len(self.animation_frames): bg_idx = len(self.animation_frames)
                    except ValueError:
                        bg_idx = 1
                    bg_path = self.animation_frames[self.animation_frame_order[bg_idx - 1]]
                    background = Image.open(bg_path).convert("RGBA")
                    bg_w, bg_h = background.size
                    comp = background.copy()
                    x = (bg_w - frame_img.width) // 2
                    y = (bg_h - frame_img.height) // 2
                    comp.paste(frame_img, (x, y), frame_img)
                    frame_img = comp
                
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
    def on_tab_changed(self, event):
        tab_idx = self.notebook.index(self.notebook.select())
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
            self.preview_gif_btn.config(text="▶ Preview GIF", default="normal")
            self.bottom_bar.grid_remove()
            self.timeline_frame.grid(row=2, column=0, sticky="ew")
            
            # Configure timeline bounds
            n = len(self.animation_frames)
            if n > 0:
                self.range_start_spin.config(from_=1, to=n)
                self.range_end_spin.config(from_=1, to=n)
                self.timeline_slider.config(from_=1.0, to=float(n))
                
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
                img = Image.open(frame_path).convert("RGBA")
                
                if self.use_bg_var.get() and len(self.animation_frames) > 0:
                    try:
                        bg_idx = int(self.bg_frame_index_var.get())
                        if bg_idx < 1: bg_idx = 1
                        if bg_idx > len(self.animation_frames): bg_idx = len(self.animation_frames)
                    except ValueError:
                        bg_idx = 1
                    bg_path = self.animation_frames[self.animation_frame_order[bg_idx - 1]]
                    try:
                        bg = Image.open(bg_path).convert("RGBA")
                        bg_w, bg_h = bg.size
                        comp = bg.copy()
                        bx = (bg_w - img.width) // 2
                        by = (bg_h - img.height) // 2
                        comp.paste(img, (bx, by), img)
                        img = comp
                    except Exception:
                        pass
                
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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    app  = ImageSlicerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
