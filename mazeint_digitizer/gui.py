import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import convert
from .update import check_for_updates, download_latest_windows_release, open_latest_release, perform_update


HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class MazeIntGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MazeInt Logo Digitizer")
        self.geometry("920x700")
        self.minsize(820, 560)
        self.configure(bg="#0f172a")
        self._apply_theme()

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

        self._build_widgets()

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
        ttk.Label(top, text="Image file", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 0))
        row1 = ttk.Frame(top)
        row1.pack(fill="x", pady=(6, 8))
        ttk.Entry(row1, textvariable=self.image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="Browse", command=self.choose_image).pack(side="left", padx=(8, 0))

        settings = ttk.Frame(main, style="Card.TFrame")
        settings.pack(fill="x", pady=(8, 0))
        ttk.Label(settings, text="Output settings", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 0))

        grid = ttk.Frame(settings, padding=(12, 8, 12, 12))
        grid.pack(fill="x")
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
                ttk.Entry(grid, textvariable=variable).grid(row=i, column=1, sticky="ew", pady=5)
            grid.columnconfigure(1, weight=1)

        tools = ttk.Frame(main)
        tools.pack(fill="x", pady=(4, 8))
        ttk.Checkbutton(tools, text="Use source image size as exact working size", variable=self.use_exact_size).pack(anchor="w")
        ttk.Checkbutton(tools, text="Use underlay for fills", variable=self.underlay).pack(anchor="w")

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="Generate embroidery files", command=self.run_digitize, style="Accent.TButton").pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Check for updates", command=self.check_for_updates).pack(side="left", padx=(10, 0), fill="x")
        ttk.Button(buttons, text="Download Windows release", command=self.download_windows_release).pack(side="left", padx=(10, 0), fill="x")

        preview_frame = ttk.LabelFrame(main, text="Preview")
        preview_frame.pack(fill="both", expand=True)
        self.preview_label = ttk.Label(preview_frame, text="No preview yet", anchor="center")
        self.preview_label.pack(fill="both", expand=True, padx=12, pady=12)

        self.log = tk.Text(main, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(8, 0))

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
            h, w = img.shape[:2]
            max_dim = 300
            scale = max_dim / max(h, w)
            target_h = max(1, int(h * scale))
            target_w = max(1, int(w * scale))
            resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)
            _, encoded = cv2.imencode(".png", resized)
            import base64
            b64 = base64.b64encode(encoded).decode()
            self.preview_image = tk.PhotoImage(data=f"iVB64,{b64}")
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

        color_value = self.thread_color.get().strip()
        if color_value and not HEX_COLOR_RE.match(color_value):
            messagebox.showerror("Invalid thread color", "Please enter a valid hex color such as #1f2937 or #fff.")
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
                thread_colors=[color_value or "#1f2937"],
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
