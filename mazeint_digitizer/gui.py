import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .core import convert


class MazeIntGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MazeInt Logo Digitizer")
        self.geometry("920x700")
        self.minsize(820, 560)

        self.image_path = tk.StringVar(value="")
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.output_name = tk.StringVar(value="mazeint_logo")
        self.width_mm = tk.DoubleVar(value=100.0)
        self.row_spacing_mm = tk.DoubleVar(value=1.2)
        self.angle_deg = tk.DoubleVar(value=45.0)
        self.thin_threshold_mm = tk.DoubleVar(value=1.4)
        self.running_stitch_len_mm = tk.DoubleVar(value=2.2)
        self.underlay = tk.BooleanVar(value=True)
        self.use_exact_size = tk.BooleanVar(value=True)
        self.thread_color = tk.StringVar(value="#1f2937")

        self._build_widgets()

    def _build_widgets(self):
        main = ttk.Frame(self, padding=16)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x")
        ttk.Label(top, text="Image file", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        row1 = ttk.Frame(top)
        row1.pack(fill="x", pady=(6, 8))
        ttk.Entry(row1, textvariable=self.image_path).pack(side="left", fill="x", expand=True)
        ttk.Button(row1, text="Browse", command=self.choose_image).pack(side="left", padx=(8, 0))

        settings = ttk.Frame(main)
        settings.pack(fill="x", pady=(8, 0))
        ttk.Label(settings, text="Output settings", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        grid = ttk.Frame(settings)
        grid.pack(fill="x", pady=8)
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

        ttk.Button(main, text="Generate embroidery files", command=self.run_digitize, style="Accent.TButton").pack(fill="x", pady=(0, 10))

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

    def run_digitize(self):
        image_file = self.image_path.get().strip()
        if not image_file:
            messagebox.showerror("Missing image", "Please choose a logo image first.")
            return

        out_dir = self.output_dir.get().strip() or os.getcwd()
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
                thread_colors=[self.thread_color.get()],
            )
            self.log_message("Done.")
            self.log_message(f"Files: {', '.join(paths)}")
            self.log_message(f"Thin shapes: {n_thin}, thick shapes: {n_thick}, stitches: {pattern.count_stitches()}")
            preview_path = [p for p in paths if p.endswith("_preview.png")]
            if preview_path:
                self._show_preview(preview_path[0])
            messagebox.showinfo("Success", f"Embroidery files generated:\n{chr(10).join(paths)}")
        except Exception as exc:  # pragma: no cover - UI shows message
            self.log_message(f"Error: {exc}")
            messagebox.showerror("Generation failed", str(exc))


def main():
    app = MazeIntGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
