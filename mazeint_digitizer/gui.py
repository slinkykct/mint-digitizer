import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

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

        self.image_path.trace_add("write", lambda *_: self._refresh_text_preview())
        self.text_value.trace_add("write", lambda *_: self._refresh_text_preview())
        self.text_font.trace_add("write", lambda *_: self._refresh_text_preview())
        self.text_size_px.trace_add("write", lambda *_: self._refresh_text_preview())
        self.text_color.trace_add("write", lambda *_: self._refresh_text_preview())

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

        buttons = ttk.Frame(preview_column)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Generate embroidery files", command=self.run_digitize, style="Accent.TButton").pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Check for updates", command=self.check_for_updates).pack(side="left", padx=(10, 0))
        ttk.Button(buttons, text="Windows release", command=self.download_windows_release).pack(side="left", padx=(10, 0))

        self.log = tk.Text(preview_column, height=5, wrap="word", state="disabled", background="#111827", foreground="#cbd5e1", relief="flat")
        self.log.pack(fill="x", pady=(10, 0))

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

    def _refresh_text_preview(self):
        self._update_text_color_button()
        if self.image_path.get().strip():
            self._show_preview(self.image_path.get().strip())

    def _refresh_palette_preview(self):
        for index in range(len(self.palette_buttons)):
            self._update_swatch(index)
        if self.image_path.get().strip():
            self._show_preview(self.image_path.get().strip())

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

    def _show_preview(self, image_path):
        try:
            import cv2
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                self.preview_label.config(text="Preview unavailable")
                return
            _, mask = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            if (mask == 255).mean() > 0.5:
                mask = cv2.bitwise_not(mask)
            preview = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
            preview[mask == 255] = (248, 250, 252)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            colors = self._active_colors()
            text = self.text_value.get().strip()
            text_hex = self.text_color.get().strip()
            if text and not HEX_COLOR_RE.match(text_hex):
                self.preview_label.config(text="Enter a valid text color")
                return
            for index, contour in enumerate(contours):
                hex_color = colors[index % len(colors)].lstrip("#")
                rgb = tuple(int(hex_color[pos:pos + 2], 16) for pos in (0, 2, 4))
                cv2.drawContours(preview, [contour], -1, rgb, 2)
            if text:
                from .core import render_text_mask
                text_mask = render_text_mask(img.shape, text, self.text_font.get(), self.text_size_px.get())
                text_contours, _ = cv2.findContours(text_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                text_hex = text_hex.lstrip("#")
                text_rgb = tuple(int(text_hex[pos:pos + 2], 16) for pos in (0, 2, 4))
                for contour in text_contours:
                    cv2.drawContours(preview, [contour], -1, text_rgb, 2)
            h, w = img.shape[:2]
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
        except Exception:
            self.preview_label.config(text="Preview unavailable")

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
