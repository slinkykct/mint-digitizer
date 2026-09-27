import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

import numpy as np

from .core import convert
from .update import check_for_updates, download_latest_windows_release, open_latest_release, perform_update


HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class MazeIntGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MazeInt Logo Digitizer")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.configure(bg="#0f172a")
        self._apply_theme()
        self._set_window_icon()

        self.image_path = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.output_name = tk.StringVar(value="mazeint_logo")
        self.version = tk.StringVar(value="v0.1.0")
        self.release_banner = tk.StringVar(value="Release v0.1.0")
        self.width_mm = tk.DoubleVar(value=100.0)
        self.row_spacing_mm = tk.DoubleVar(value=1.2)
        self.angle_deg = tk.DoubleVar(value=45.0)
        self.thin_threshold_mm = tk.DoubleVar(value=1.4)
        self.running_stitch_len_mm = tk.DoubleVar(value=2.2)
        self.shape_scale = tk.DoubleVar(value=100.0)
        self.shape_rotation_deg = tk.DoubleVar(value=0.0)
        self.shape_offset_x = tk.IntVar(value=0)
        self.shape_offset_y = tk.IntVar(value=0)
        self.shape_mirror_x = tk.BooleanVar(value=False)
        self.shape_mirror_y = tk.BooleanVar(value=False)
        self.artwork_layer_enabled = tk.BooleanVar(value=True)
        self.text_layer_enabled = tk.BooleanVar(value=True)
        self.selected_layer = tk.StringVar(value="Artwork")
        self.grid_snap = tk.BooleanVar(value=True)
        self.stitch_preset = tk.StringVar(value="Standard")
        self.underlay = tk.BooleanVar(value=True)
        self.use_exact_size = tk.BooleanVar(value=True)
        self.thread_color = tk.StringVar(value="#1f2937")
        self.text_value = tk.StringVar(value="")
        self.text_font = tk.StringVar(value="Sans")
        self.text_size_px = tk.IntVar(value=42)
        self.text_color = tk.StringVar(value="#111827")
        self.palette_colors = [tk.StringVar(value=color) for color in ("#1f2937", "#e11d48", "#0f766e", "#f59e0b")]
        self.palette_enabled = [tk.BooleanVar(value=index == 0) for index in range(4)]
        self.palette_buttons = []
        self._layer_transform_state = {
            "Artwork": self._default_layer_transform(),
            "Text": self._default_layer_transform(),
        }

        for var in (
            self.image_path,
            self.output_dir,
            self.output_name,
            self.width_mm,
            self.row_spacing_mm,
            self.angle_deg,
            self.thin_threshold_mm,
            self.running_stitch_len_mm,
            self.shape_scale,
            self.shape_rotation_deg,
            self.shape_offset_x,
            self.shape_offset_y,
            self.shape_mirror_x,
            self.shape_mirror_y,
            self.artwork_layer_enabled,
            self.text_layer_enabled,
            self.selected_layer,
            self.grid_snap,
            self.stitch_preset,
            self.underlay,
            self.use_exact_size,
            self.thread_color,
            self.text_value,
            self.text_font,
            self.text_size_px,
            self.text_color,
        ):
            var.trace_add("write", lambda *_: self._refresh_preview_if_image_loaded())
        for color_var in self.palette_colors:
            color_var.trace_add("write", lambda *_: self._refresh_preview_if_image_loaded())
        for enabled_var in self.palette_enabled:
            enabled_var.trace_add("write", lambda *_: self._refresh_preview_if_image_loaded())

        self._build_widgets()

    def _set_window_icon(self):
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "mazeint-digitizer.svg"
        if icon_path.exists():
            try:
                self.iconphoto(False, tk.PhotoImage(file=str(icon_path)))
            except Exception:
                pass

    def _apply_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("TLabel", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#111827", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("Section.TLabel", background="#111827", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("TEntry", fieldbackground="#f8fafc", foreground="#0f172a", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 10))
        style.configure("TButton", padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[("active", "#2563eb"), ("!disabled", "#1d4ed8")], foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")])
        style.configure("Accent.TButton", background="#1d4ed8", foreground="#ffffff", padding=(12, 8), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#1e40af"), ("!disabled", "#1d4ed8")])
        style.configure("TLabelframe", background="#0f172a", foreground="#e2e8f0")
        style.configure("TLabelframe.Label", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 10, "bold"))
        style.configure("TText", background="#0f172a", foreground="#e2e8f0")

    def _build_widgets(self):
        self._show_splash()
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x")
        header = ttk.Frame(top, style="Card.TFrame")
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="MazeInt Digitizer", style="Header.TLabel").pack(side="left", padx=12, pady=10)
        banner = tk.Label(header, textvariable=self.release_banner, bg="#1d4ed8", fg="#ffffff", font=("Segoe UI", 9, "bold"), padx=12, pady=5)
        banner.pack(side="right", padx=(0, 12), pady=10)
        self.version.set("v0.1.0")
        self.release_banner.set("Release v0.1.0")
        ttk.Label(top, text="1. Choose artwork", style="Section.TLabel").pack(anchor="w", pady=(8, 0))
        row1 = ttk.Frame(top)
        row1.pack(fill="x", pady=(6, 8))
        ttk.Entry(row1, textvariable=self.image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="Browse", command=self.choose_image).pack(side="left", padx=(8, 0))

        content = ttk.Frame(main)
        content.pack(fill="both", expand=True, pady=(8, 0))
        settings = ttk.Frame(content, style="Card.TFrame", padding=12)
        settings.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(settings, text="2. Set output", style="Section.TLabel").pack(anchor="w")

        grid = ttk.Frame(settings)
        grid.pack(fill="x", pady=(8, 0))
        opts = [
            ("Output directory", self.output_dir, "dir"),
            ("Output name", self.output_name, "text"),
            ("Width (mm)", self.width_mm, "float"),
            ("Row spacing (mm)", self.row_spacing_mm, "float"),
            ("Fill angle (deg)", self.angle_deg, "float"),
            ("Thin threshold (mm)", self.thin_threshold_mm, "float"),
            ("Running stitch (mm)", self.running_stitch_len_mm, "float"),
            ("Thread color", self.thread_color, "text"),
        ]

        for i, (label_text, variable, kind) in enumerate(opts):
            ttk.Label(grid, text=label_text).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            if kind == "dir":
                ttk.Entry(grid, textvariable=variable).grid(row=i, column=1, sticky="ew", pady=5)
                ttk.Button(grid, text="Browse", command=self.choose_output_dir).grid(row=i, column=2, padx=(8, 0), pady=5)
            else:
                ttk.Entry(grid, textvariable=variable, width=18).grid(row=i, column=1, sticky="ew", pady=5)
            grid.columnconfigure(1, weight=1)

        ttk.Separator(settings).pack(fill="x", pady=12)
        ttk.Label(settings, text="Shape controls", style="Section.TLabel").pack(anchor="w")
        shape_controls = ttk.Frame(settings)
        shape_controls.pack(fill="x", pady=(4, 8))
        ttk.Label(shape_controls, text="Scale %").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Spinbox(shape_controls, from_=25, to=300, textvariable=self.shape_scale, width=6, command=self._refresh_preview_if_image_loaded).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(shape_controls, text="Rotate").grid(row=0, column=2, sticky="w", padx=(12, 6), pady=4)
        ttk.Spinbox(shape_controls, from_=-180, to=180, textvariable=self.shape_rotation_deg, width=6, command=self._refresh_preview_if_image_loaded).grid(row=0, column=3, sticky="w", pady=4)
        ttk.Label(shape_controls, text="X").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Spinbox(shape_controls, from_=-500, to=500, textvariable=self.shape_offset_x, width=6, command=self._refresh_preview_if_image_loaded).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(shape_controls, text="Y").grid(row=1, column=2, sticky="w", padx=(12, 6), pady=4)
        ttk.Spinbox(shape_controls, from_=-500, to=500, textvariable=self.shape_offset_y, width=6, command=self._refresh_preview_if_image_loaded).grid(row=1, column=3, sticky="w", pady=4)
        ttk.Checkbutton(shape_controls, text="Flip X", variable=self.shape_mirror_x, command=self._refresh_preview_if_image_loaded).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Checkbutton(shape_controls, text="Flip Y", variable=self.shape_mirror_y, command=self._refresh_preview_if_image_loaded).grid(row=2, column=2, sticky="w", pady=(4, 0))
        ttk.Button(shape_controls, text="Reset transform", command=self.reset_shape_transform).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        ttk.Separator(settings).pack(fill="x", pady=8)
        ttk.Label(settings, text="Layers", style="Section.TLabel").pack(anchor="w")
        layer_controls = ttk.Frame(settings)
        layer_controls.pack(fill="x", pady=(4, 6))
        ttk.Checkbutton(layer_controls, text="Artwork layer", variable=self.artwork_layer_enabled, command=self._refresh_preview_if_image_loaded).pack(side="left")
        ttk.Checkbutton(layer_controls, text="Text layer", variable=self.text_layer_enabled, command=self._refresh_preview_if_image_loaded).pack(side="left", padx=(12, 0))

        ttk.Separator(settings).pack(fill="x", pady=8)
        ttk.Label(settings, text="Layer tools", style="Section.TLabel").pack(anchor="w")
        layer_controls = ttk.Frame(settings)
        layer_controls.pack(fill="x", pady=(4, 6))
        ttk.Button(layer_controls, text="Artwork", command=lambda: self.select_edit_layer("Artwork")).pack(side="left")
        ttk.Button(layer_controls, text="Text", command=lambda: self.select_edit_layer("Text")).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(layer_controls, text="Snap", variable=self.grid_snap, command=self._refresh_preview_if_image_loaded).pack(side="left", padx=(12, 0))
        ttk.Button(layer_controls, text="Rot -90", command=lambda: self.rotate_selected_layer(-90)).pack(side="left", padx=(12, 0))
        ttk.Button(layer_controls, text="Rot +90", command=lambda: self.rotate_selected_layer(90)).pack(side="left", padx=(8, 0))

        ttk.Separator(settings).pack(fill="x", pady=8)
        ttk.Label(settings, text="Text layer", style="Section.TLabel").pack(anchor="w")
        ttk.Label(settings, text="Add optional lettering to the embroidery design.", wraplength=255).pack(anchor="w", pady=(4, 6))
        text_entry = ttk.Entry(settings, textvariable=self.text_value, width=28)
        text_entry.pack(fill="x", pady=(0, 6))
        text_entry.bind("<KeyRelease>", lambda _event: self._refresh_text_preview())
        text_controls = ttk.Frame(settings)
        text_controls.pack(fill="x")
        ttk.Label(text_controls, text="Font").pack(side="left")
        font_box = ttk.Combobox(text_controls, textvariable=self.text_font, values=("Sans", "Serif", "Script", "Bold"), state="readonly", width=10)
        font_box.pack(side="left", padx=(6, 8))
        font_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_text_preview())
        ttk.Label(text_controls, text="Size").pack(side="left")
        size_box = ttk.Spinbox(text_controls, from_=12, to=160, textvariable=self.text_size_px, width=5, command=self._refresh_text_preview)
        size_box.pack(side="left", padx=(6, 0))
        size_box.bind("<KeyRelease>", lambda _event: self._refresh_text_preview())
        text_color_button = tk.Button(settings, text="Text color", anchor="w", command=self._edit_text_color, relief="flat")
        text_color_button.pack(fill="x", pady=(8, 0))
        self.text_color_button = text_color_button
        self._update_text_color_button()

        ttk.Separator(settings).pack(fill="x", pady=12)
        ttk.Label(settings, text="Stitch presets", style="Section.TLabel").pack(anchor="w")
        preset_row = ttk.Frame(settings)
        preset_row.pack(fill="x", pady=(4, 8))
        for name in ("Light", "Standard", "Heavy"):
            ttk.Button(preset_row, text=name, command=lambda preset=name: self.apply_stitch_preset(preset)).pack(side="left", padx=(0, 8))
        self._apply_stitch_preset("Standard")

        ttk.Separator(settings).pack(fill="x", pady=12)
        ttk.Label(settings, text="Thread palette", style="Section.TLabel").pack(anchor="w")
        ttk.Label(settings, text="Toggle colors on, then click a swatch to edit it.", wraplength=255).pack(anchor="w", pady=(4, 8))
        self._build_palette(settings)

        tools = ttk.Frame(settings)
        tools.pack(fill="x", pady=(12, 8))
        ttk.Checkbutton(tools, text="Use source image size as exact working size", variable=self.use_exact_size).pack(anchor="w")
        ttk.Checkbutton(tools, text="Use underlay for fills", variable=self.underlay).pack(anchor="w")

        preview_column = ttk.Frame(content)
        preview_column.pack(side="left", fill="both", expand=True)
        preview_frame = ttk.Frame(preview_column, style="Card.TFrame", padding=12)
        preview_frame.pack(fill="both", expand=True)
        ttk.Label(preview_frame, text="3. Preview and export", style="Section.TLabel").pack(anchor="w")
        self.preview_label = ttk.Label(preview_frame, text="Choose an image to preview it", anchor="center")
        self.preview_label.pack(fill="both", expand=True, padx=4, pady=12)
        self.preview_drag_layer = tk.Canvas(preview_frame, width=300, height=220, bg="#111827", highlightthickness=0)
        self.preview_drag_layer.place(in_=self.preview_label, x=0, y=0, relwidth=1, relheight=1)
        self.preview_drag_layer.bind("<ButtonPress-1>", self._start_preview_drag)
        self.preview_drag_layer.bind("<B1-Motion>", self._drag_preview)
        self.preview_drag_layer.bind("<ButtonRelease-1>", self._end_preview_drag)
        self._preview_drag_state = None

        buttons = ttk.Frame(preview_column)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Generate embroidery files", command=self.run_digitize, style="Accent.TButton").pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Check for updates", command=self.check_for_updates).pack(side="left", padx=(10, 0))
        ttk.Button(buttons, text="Windows release", command=self.download_windows_release).pack(side="left", padx=(10, 0))

        self.log = tk.Text(preview_column, height=5, wrap="word", state="disabled", background="#111827", foreground="#cbd5e1", relief="flat")
        self.log.pack(fill="x", pady=(10, 0))

    def _default_layer_transform(self):
        return {
            "scale": 100.0,
            "rotation_deg": 0.0,
            "offset_x": 0,
            "offset_y": 0,
            "mirror_x": False,
            "mirror_y": False,
        }

    def _read_layer_transform_from_controls(self):
        return {
            "scale": float(self.shape_scale.get()),
            "rotation_deg": float(self.shape_rotation_deg.get()),
            "offset_x": int(self.shape_offset_x.get()),
            "offset_y": int(self.shape_offset_y.get()),
            "mirror_x": bool(self.shape_mirror_x.get()),
            "mirror_y": bool(self.shape_mirror_y.get()),
        }

    def _apply_layer_transform_to_controls(self, state):
        self.shape_scale.set(float(state.get("scale", 100.0)))
        self.shape_rotation_deg.set(float(state.get("rotation_deg", 0.0)))
        self.shape_offset_x.set(int(state.get("offset_x", 0)))
        self.shape_offset_y.set(int(state.get("offset_y", 0)))
        self.shape_mirror_x.set(bool(state.get("mirror_x", False)))
        self.shape_mirror_y.set(bool(state.get("mirror_y", False)))

    def _save_active_layer_transform(self):
        self._layer_transform_state[self.selected_layer.get()] = self._read_layer_transform_from_controls()

    def apply_stitch_preset(self, preset_name):
        presets = {
            "Light": {"row_spacing_mm": 1.5, "thin_threshold_mm": 2.0, "running_stitch_len_mm": 2.8, "angle_deg": 45.0, "underlay": False},
            "Standard": {"row_spacing_mm": 1.2, "thin_threshold_mm": 1.4, "running_stitch_len_mm": 2.2, "angle_deg": 45.0, "underlay": True},
            "Heavy": {"row_spacing_mm": 0.8, "thin_threshold_mm": 1.0, "running_stitch_len_mm": 1.6, "angle_deg": 30.0, "underlay": True},
        }
        preset = presets.get(preset_name, presets["Standard"])
        self.stitch_preset.set(preset_name)
        self.row_spacing_mm.set(preset["row_spacing_mm"])
        self.thin_threshold_mm.set(preset["thin_threshold_mm"])
        self.running_stitch_len_mm.set(preset["running_stitch_len_mm"])
        self.angle_deg.set(preset["angle_deg"])
        self.underlay.set(preset["underlay"])
        self._refresh_preview_if_image_loaded()

    def select_edit_layer(self, layer_name):
        self.selected_layer.set(layer_name)
        self._apply_layer_transform_to_controls(self._layer_transform_state.get(layer_name, self._default_layer_transform()))
        self._refresh_preview_if_image_loaded()

    def rotate_selected_layer(self, delta_deg):
        current = float(self.shape_rotation_deg.get())
        if self.grid_snap.get():
            current = round(current / 15.0) * 15.0
        self.shape_rotation_deg.set((current + delta_deg) % 360)
        self._save_active_layer_transform()
        self._refresh_preview_if_image_loaded()

    def _build_palette(self, parent):
        for index, (color_var, enabled_var) in enumerate(zip(self.palette_colors, self.palette_enabled), start=1):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=3)
            ttk.Checkbutton(row, text=f"Color {index}", variable=enabled_var, command=self._refresh_palette_preview).pack(side="left")
            swatch = tk.Button(row, width=3, relief="flat", command=lambda value=color_var: self._edit_color(value))
            swatch.pack(side="right", padx=(8, 0))
            self.palette_buttons.append(swatch)
            color_var.trace_add("write", lambda *_: self._refresh_palette_preview())
            self._update_swatch(index - 1)

    def _edit_color(self, color_var):
        chosen = colorchooser.askcolor(color_var.get(), title="Choose thread color")[1]
        if chosen:
            color_var.set(chosen.lower())

    def _update_swatch(self, index):
        if index < len(self.palette_buttons):
            color = self.palette_colors[index].get()
            self.palette_buttons[index].configure(bg=color if HEX_COLOR_RE.match(color) else "#64748b")

    def _active_colors(self):
        colors = [var.get().strip() for var, enabled in zip(self.palette_colors, self.palette_enabled) if enabled.get()]
        return colors or ["#1f2937"]

    def _update_text_color_button(self):
        color = self.text_color.get()
        self.text_color_button.configure(bg=color if HEX_COLOR_RE.match(color) else "#64748b")

    def _edit_text_color(self):
        chosen = colorchooser.askcolor(self.text_color.get(), title="Choose text thread color")[1]
        if chosen:
            self.text_color.set(chosen.lower())
            self._update_text_color_button()
            self._refresh_text_preview()

    def reset_shape_transform(self):
        layer_name = self.selected_layer.get()
        reset_state = self._default_layer_transform()
        self._layer_transform_state[layer_name] = reset_state
        self._apply_layer_transform_to_controls(reset_state)
        self._refresh_preview_if_image_loaded()

    def _refresh_preview_if_image_loaded(self):
        self._update_text_color_button()
        if self.image_path.get().strip():
            self._save_active_layer_transform()
            self._show_preview(self.image_path.get().strip())

    def _refresh_text_preview(self):
        self._refresh_preview_if_image_loaded()

    def _refresh_palette_preview(self):
        for index in range(len(self.palette_buttons)):
            self._update_swatch(index)
        self._refresh_preview_if_image_loaded()

    def _show_splash(self):
        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.geometry("420x200")
        splash.configure(bg="#0f172a")
        splash.transient(self)
        splash.attributes("-topmost", True)
        splash.geometry(f"+{(self.winfo_screenwidth() // 2) - 210}+{(self.winfo_screenheight() // 2) - 100}")

        icon = tk.Label(splash, text="M", bg="#1d4ed8", fg="#ffffff", font=("Segoe UI", 28, "bold"), width=4, height=2)
        icon.pack(pady=(32, 12))
        tk.Label(splash, text="MazeInt Digitizer", bg="#0f172a", fg="#f8fafc", font=("Segoe UI", 18, "bold")).pack()
        tk.Label(splash, text="Preparing embroidery workspace...", bg="#0f172a", fg="#94a3b8", font=("Segoe UI", 10)).pack(pady=(8, 0))
        splash.update_idletasks()
        self.after(900, splash.destroy)

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Select logo image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp"), ("All files", "*.*")],
        )
        if path:
            self.image_path.set(path)
            self._show_preview(path)

    def choose_output_dir(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir.set(folder)

    def _start_preview_drag(self, event):
        if not self.image_path.get().strip():
            return
        item = self.preview_drag_layer.find_withtag("current")
        if item:
            tag = self.preview_drag_layer.gettags(item[0])
            if "move" in tag:
                handle = "move"
            elif "scale" in tag:
                handle = "scale"
            elif "rotate" in tag:
                handle = "rotate"
            else:
                handle = "move"
        else:
            handle = "move"

        layer_name = self.selected_layer.get()
        state = self._layer_transform_state.setdefault(layer_name, self._default_layer_transform())
        x, y = event.x, event.y
        self._preview_drag_state = {
            "handle": handle,
            "layer": layer_name,
            "start_x": x,
            "start_y": y,
            "offset_x": int(state.get("offset_x", 0)),
            "offset_y": int(state.get("offset_y", 0)),
            "scale": float(state.get("scale", 100.0)),
            "rotation": float(state.get("rotation_deg", 0.0)),
        }

    def _drag_preview(self, event):
        if not self.image_path.get().strip() or not getattr(self, "_preview_drag_state", None):
            return
        delta_x = event.x - self._preview_drag_state["start_x"]
        delta_y = event.y - self._preview_drag_state["start_y"]
        handle = self._preview_drag_state["handle"]
        layer_name = self._preview_drag_state["layer"]
        state = self._layer_transform_state.setdefault(layer_name, self._default_layer_transform())
        if handle == "move":
            state["offset_x"] = int(self._preview_drag_state["offset_x"] + round(delta_x * 0.9))
            state["offset_y"] = int(self._preview_drag_state["offset_y"] + round(delta_y * 0.9))
        elif handle == "scale":
            new_scale = self._preview_drag_state["scale"] + (delta_x + delta_y) * 0.12
            state["scale"] = max(25.0, min(300.0, new_scale))
        elif handle == "rotate":
            cx = self.preview_drag_layer.winfo_width() / 2.0
            cy = self.preview_drag_layer.winfo_height() / 2.0
            angle = (180 / 3.141592653589793) * __import__("math").atan2(event.y - cy, event.x - cx)
            if self.grid_snap.get():
                angle = round(angle / 15.0) * 15.0
            state["rotation_deg"] = angle
        self._apply_layer_transform_to_controls(state)
        self._refresh_preview_if_image_loaded()

    def _end_preview_drag(self, _event):
        self._preview_drag_state = None

    def _show_preview(self, image_path):
        try:
            import cv2
            from .core import load_mask, render_text_mask, transform_mask
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                self.preview_label.config(text="Preview unavailable")
                self.preview_drag_layer.delete("all")
                return
            if img.ndim == 2:
                gray = img
                h, w = gray.shape[:2]
            elif img.shape[-1] == 4:
                gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
                h, w = gray.shape[:2]
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape[:2]

            artwork_state = self._layer_transform_state.get("Artwork", self._default_layer_transform())
            text_state = self._layer_transform_state.get("Text", self._default_layer_transform())
            artwork_scale = max(0.25, float(artwork_state["scale"]) / 100.0)
            text_scale = max(0.25, float(text_state["scale"]) / 100.0)

            mask = load_mask(image_path)
            if self.artwork_layer_enabled.get():
                mask = transform_mask(
                    mask,
                    scale_x=artwork_scale,
                    scale_y=artwork_scale,
                    rotation_deg=float(artwork_state["rotation_deg"]),
                    offset_x=int(artwork_state["offset_x"]),
                    offset_y=int(artwork_state["offset_y"]),
                    mirror_x=bool(artwork_state["mirror_x"]),
                    mirror_y=bool(artwork_state["mirror_y"]),
                )
            else:
                mask = np.zeros_like(mask)
            preview = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
            preview[mask == 255] = (248, 250, 252)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            colors = self._active_colors()
            text = self.text_value.get().strip() if self.text_layer_enabled.get() else ""
            text_hex = self.text_color.get().strip()
            if text and not HEX_COLOR_RE.match(text_hex):
                self.preview_label.config(text="Enter a valid text color")
                return
            for index, contour in enumerate(contours):
                hex_color = colors[index % len(colors)].lstrip("#")
                rgb = tuple(int(hex_color[pos:pos + 2], 16) for pos in (0, 2, 4))
                cv2.drawContours(preview, [contour], -1, rgb, 2)
            if text:
                text_mask = render_text_mask(gray.shape, text, self.text_font.get(), self.text_size_px.get())
                if self.text_layer_enabled.get():
                    text_mask = transform_mask(
                        text_mask,
                        scale_x=text_scale,
                        scale_y=text_scale,
                        rotation_deg=float(text_state["rotation_deg"]),
                        offset_x=int(text_state["offset_x"]),
                        offset_y=int(text_state["offset_y"]),
                        mirror_x=bool(text_state["mirror_x"]),
                        mirror_y=bool(text_state["mirror_y"]),
                    )
                text_contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                text_hex = text_hex.lstrip("#")
                text_rgb = tuple(int(text_hex[pos:pos + 2], 16) for pos in (0, 2, 4))
                for contour in text_contours:
                    cv2.drawContours(preview, [contour], -1, text_rgb, 2)
            max_dim = 300
            scale = max_dim / max(h, w)
            target_h = max(1, int(h * scale))
            target_w = max(1, int(w * scale))
            resized = cv2.resize(preview, (target_w, target_h), interpolation=cv2.INTER_AREA)
            _, encoded = cv2.imencode(".png", resized)
            import base64
            b64 = base64.b64encode(encoded).decode()
            self.preview_image = tk.PhotoImage(data=b64)
            self.preview_label.config(image=self.preview_image, text="")
            self.preview_drag_layer.delete("all")
            self.preview_drag_layer.configure(width=target_w, height=target_h)
            self.preview_drag_layer.create_image(0, 0, anchor="nw", image=self.preview_image)
            cx, cy = target_w / 2, target_h / 2
            self.preview_drag_layer.create_rectangle(10, 10, target_w - 10, target_h - 10, outline="#f8fafc", dash=(5, 5), width=2, tags=("selection-box",))
            for x, y, tag in ((cx, cy, "move"), (cx + target_w * 0.45, cy, "scale"), (cx, cy - target_h * 0.45, "rotate")):
                self.preview_drag_layer.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#f8fafc", outline="#0f172a", tags=(tag, "handle"))
            if self.selected_layer.get() == "Text":
                self.preview_drag_layer.itemconfigure("selection-box", outline="#f59e0b")
            else:
                self.preview_drag_layer.itemconfigure("selection-box", outline="#60a5fa")
        except Exception:
            self.preview_label.config(text="Preview unavailable")
            self.preview_drag_layer.delete("all")

    def log_message(self, text):
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.configure(state="disabled")
        self.log.see(tk.END)

    def check_for_updates(self):
        try:
            info = check_for_updates()
            self.version.set(info.get("current_version", self.version.get()))
            if info.get("error"):
                messagebox.showwarning("Update check", info["error"])
                return
            current = info.get("current_version", self.version.get())
            latest = info.get("latest_version", current)
            self.version.set(current)
            self.release_banner.set(f"Release {current}")
            if info.get("has_update"):
                response = messagebox.askyesno(
                    "Update available",
                    f"A new version is available: {current} -> {latest}\n\nOpen the release page and update now?",
                )
                if response:
                    try:
                        result = perform_update()
                        self.version.set(result.get("latest_version", current))
                        self.release_banner.set(f"Release {result.get('latest_version', current)}")
                        messagebox.showinfo("Update complete", result.get("message", "Update complete."))
                    except Exception as exc:
                        messagebox.showerror("Update failed", str(exc))
            else:
                self.release_banner.set(f"Release {current}")
                messagebox.showinfo("Up to date", f"You are already on the latest version: {current}")
        except Exception as exc:
            messagebox.showerror("Update check failed", str(exc))

    def download_windows_release(self):
        try:
            file_path = download_latest_windows_release(os.getcwd())
            messagebox.showinfo("Windows release ready", f"Downloaded to:\n{file_path}\n\nOpen the file to install the latest Windows build.")
        except Exception as exc:
            try:
                url = open_latest_release()
                messagebox.showinfo("Open GitHub release", f"The latest GitHub release page opened in your browser:\n{url}")
            except Exception:
                messagebox.showerror("Windows release unavailable", str(exc))

    def run_digitize(self):
        image_file = self.image_path.get().strip()
        if not image_file:
            messagebox.showerror("Missing image", "Please choose a logo image first.")
            return

        colors = self._active_colors()
        if any(not HEX_COLOR_RE.match(color) for color in colors):
            messagebox.showerror("Invalid thread color", "Please correct the selected palette colors before exporting.")
            return
        text = self.text_value.get().strip()
        text_color = self.text_color.get().strip()
        if text and not HEX_COLOR_RE.match(text_color):
            messagebox.showerror("Invalid text color", "Please choose a valid text color before exporting.")
            return

        out_dir = self.output_dir.get().strip() or os.getcwd()
        if not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as exc:
                messagebox.showerror("Output folder error", f"Unable to create the output folder:\n{exc}")
                return

        out_name = self.output_name.get().strip() or "mazeint_logo"
        out_prefix = os.path.join(out_dir, out_name)

        try:
            self.log_message("Processing image...")
            self.update_idletasks()
            paths, pattern, n_thin, n_thick = convert(
                image_file,
                out_prefix,
                out_width_mm=float(self.width_mm.get()),
                row_spacing_mm=float(self.row_spacing_mm.get()),
                angle_deg=float(self.angle_deg.get()),
                thin_threshold_mm=float(self.thin_threshold_mm.get()),
                running_stitch_len_mm=float(self.running_stitch_len_mm.get()),
                underlay=bool(self.underlay.get()),
                use_exact_size=bool(self.use_exact_size.get()),
                shape_scale_x=max(0.25, float(self.shape_scale.get()) / 100.0),
                shape_scale_y=max(0.25, float(self.shape_scale.get()) / 100.0),
                shape_rotation_deg=float(self.shape_rotation_deg.get()),
                shape_offset_x=int(self.shape_offset_x.get()),
                shape_offset_y=int(self.shape_offset_y.get()),
                shape_mirror_x=bool(self.shape_mirror_x.get()),
                shape_mirror_y=bool(self.shape_mirror_y.get()),
                include_artwork=bool(self.artwork_layer_enabled.get()),
                include_text=bool(self.text_layer_enabled.get()),
                thread_colors=colors,
                text=text,
                text_font=self.text_font.get(),
                text_size_px=int(self.text_size_px.get()),
                text_color=text_color if text else None,
            )
            self.log_message("Done.")
            self.log_message(f"Files: {', '.join(paths)}")
            self.log_message(f"Thin shapes: {n_thin}, thick shapes: {n_thick}, stitches: {pattern.count_stitches()}")
            preview_path = [p for p in paths if p.endswith("_preview.png")]
            if preview_path:
                self._show_preview(preview_path[0])
            messagebox.showinfo("Success", "Embroidery files generated successfully and centered for stitching.\n\n" + "\n".join(paths))
        except Exception as exc:  # pragma: no cover - UI shows message
            self.log_message(f"Error: {exc}")
            messagebox.showerror("Generation failed", str(exc))


def main():
    app = MazeIntGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
