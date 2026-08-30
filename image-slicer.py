#!/usr/bin/env python3
"""
Image Grid Slicer entrypoint.
Forwards execution to slice_image.py.
"""
import runpy

if __name__ == "__main__":
    runpy.run_module("slice_image", run_name="__main__")
