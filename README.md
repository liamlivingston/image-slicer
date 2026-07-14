# Image Grid Slicer

A modern Python GUI tool to split a grid of images (like a 3x3 layout) into individual separate images, with smart border removal options and a live preview.

## Features

- **Graphical User Interface (GUI)**: Built with Python's native Tkinter (`ttk`) library.
- **File Finder Popups**: Native system popups to select the image file and choose an optional custom output directory (opens to the current directory by default).
- **One-Click Border Auto-Detection**: Automatically analyzes the image to find uniform solid-color or transparent borders, identifying the layout type ("all" vs. "between"), border width in pixels, and row/column grid dimensions. Robust to anti-aliased and compressed images.
- **Interactive Live Preview**:
  - Displays a scaled version of your image.
  - Automatically draws green outlines around the regions that will be kept.
  - Shows discarded border margins as red outlines.
  - Dynamically updates as you adjust settings, and supports scrolling to Zoom and left-click drag to Pan.
- **Divider Interactive Nudging**: Double-click any divider line on the Live Preview to enter a manual pixel shift offset, allowing fine-grained alignment control.
- **Advanced Border Crop Options**:
  - **Border Size (px)**: Specify separate border widths (**Width (X)**) and border heights (**Height (Y)**) for asymmetric grids. Outer edges are aligned flush against the image boundaries, ensuring zero border leakage at the crop limits.
  - **Border Layout**:
    - *Between cells only (exclude outer edges)*: Assumes borders only exist as vertical/horizontal divider lines inside the grid.
    - *Around all cells (includes outer edges)*: Assumes a border wraps around the entire image frame and surrounds every individual cell.
- **Custom Naming Schemes**:
  - **Subfolder Naming**: Enter a subfolder name template (defaults to `{filename}_sliced`).
  - **File Prefix**: Customize file prefixes (defaults to `{filename}_`).
  - **Scheme Options**: Choose between:
    - *Row & Column*: Slices are named by layout indices (e.g., `img_1_1.png`, `img_1_2.png`).
    - *Sequential*: Slices are named sequentially from left-to-right, top-to-bottom (e.g., `img_01.png`, `img_02.png` with auto-padded zero-filling).

## Prerequisites

Make sure you have `Pillow` installed for image processing. You can install it using pip:

```bash
pip install Pillow
```

## How to Run

Execute the script from your terminal:

```bash
python3 slice_image.py
```

## How to Use

1. Click **Browse...** to select your image.
2. Click **Auto-Detect Grid & Borders** to let the tool identify the layout, cell dimensions, and border spaces automatically.
3. (Optional) Adjust the **Grid Columns**, **Grid Rows**, and **Border Size (px)** manually if you wish to override the detection.
4. Look at the Live Preview to inspect the alignment (use mouse wheel to zoom, left-click drag to pan):
   - Green boxes outline active cell regions to keep.
   - Red boxes outline margins to discard.
   - **Manual Correction**: If any divider is slightly off-center due to scanned sheet skew, double-click directly on the divider line to enter a manual pixel offset shift.
5. (Optional) Under **File & Folder Naming**, customize folder name patterns, file prefixes, or toggle between Row/Col and Sequential schemes. Use the `{filename}` placeholder to reference the input image name.
6. (Optional) Customize the parent output directory by clicking **Change...**.
7. Click **Slice Image** to process the grid.
