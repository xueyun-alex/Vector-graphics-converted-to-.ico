"""Tkinter GUI for batch iconfont to ICO conversion."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from src.icon_extractor import (
    IconSvg,
    load_icons_from_dir,
    sanitize_filename,
)
from src.ico_builder import build_ico, image_to_photoimage, preview_image
from src.svg_loader import load_svg_files, load_svgs_from_dir


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _default_dirs() -> tuple[Path, Path, Path]:
    if getattr(sys, "frozen", False):
        bundle = _project_root()
        exe_dir = Path(sys.executable).parent
        return (
            bundle / "ai_icon" / "font_6xww5b6c7bv",
            exe_dir / "output_icons",
            exe_dir / "svg",
        )
    root = _project_root()
    return root / "ai_icon" / "font_6xww5b6c7bv", root / "output_icons", root / "svg"


def _app_icon_path() -> Path | None:
    candidates = [_project_root() / "output_icons" / "draw.ico"]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / "output_icons" / "draw.ico")
    for path in candidates:
        if path.is_file():
            return path
    return None


def _set_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    import ctypes

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IconfontToIco.App.1")


def _apply_window_icon(window: tk.Tk) -> None:
    icon = _app_icon_path()
    if icon is None:
        return
    try:
        window.iconbitmap(default=str(icon))
    except tk.TclError:
        pass


DEFAULT_ICONFONT_INPUT, DEFAULT_OUTPUT, DEFAULT_SVG_INPUT = _default_dirs()

SIZE_OPTIONS = [
    (16, "16×16"),
    (32, "32×32"),
    (48, "48×48"),
    (256, "256×256"),
]


class IconfontToIcoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Iconfont / SVG → ICO 转换器")
        _apply_window_icon(self)
        self.minsize(720, 520)
        self.geometry("900x600")

        self._icons: list[IconSvg] = []
        self._preview_photo: tk.PhotoImage | None = None
        self._exporting = False
        self._svg_file_paths: list[Path] = []

        self.input_mode = tk.StringVar(value="iconfont")
        self.input_dir = tk.StringVar(value=str(DEFAULT_ICONFONT_INPUT))
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT))
        self.background = tk.StringVar(value="white")
        self.size_vars = {size: tk.BooleanVar(value=True) for size, _ in SIZE_OPTIONS}

        self._build_ui()
        self.after(100, self._reload_icons)

    def _build_ui(self) -> None:
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        paths = ttk.LabelFrame(main, text="路径", padding=8)
        paths.pack(fill=tk.X, pady=(0, 8))

        mode_row = ttk.Frame(paths)
        mode_row.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))
        ttk.Label(mode_row, text="输入模式:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            mode_row,
            text="Iconfont",
            variable=self.input_mode,
            value="iconfont",
            command=self._on_mode_change,
        ).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Radiobutton(
            mode_row,
            text="SVG",
            variable=self.input_mode,
            value="svg",
            command=self._on_mode_change,
        ).pack(side=tk.LEFT, padx=4)

        self.input_label = ttk.Label(paths, text="输入目录 (iconfont.js + iconfont.json):")
        self.input_label.grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(paths, textvariable=self.input_dir, width=60).grid(
            row=1, column=1, sticky=tk.EW, padx=6
        )
        input_btns = ttk.Frame(paths)
        input_btns.grid(row=1, column=2)
        self.browse_dir_btn = ttk.Button(input_btns, text="浏览目录…", command=self._browse_input)
        self.browse_dir_btn.pack(side=tk.LEFT)
        self.browse_files_btn = ttk.Button(
            input_btns, text="浏览文件…", command=self._browse_svg_files
        )
        self.browse_files_btn.pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(paths, text="输出目录:").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Entry(paths, textvariable=self.output_dir, width=60).grid(
            row=2, column=1, sticky=tk.EW, padx=6, pady=(6, 0)
        )
        ttk.Button(paths, text="浏览…", command=self._browse_output).grid(
            row=2, column=2, pady=(6, 0)
        )
        paths.columnconfigure(1, weight=1)
        self._update_mode_ui()

        options = ttk.LabelFrame(main, text="导出选项", padding=8)
        options.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(options, text="背景:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            options, text="白底", variable=self.background, value="white", command=self._on_preview_refresh
        ).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Radiobutton(
            options,
            text="透明",
            variable=self.background,
            value="transparent",
            command=self._on_preview_refresh,
        ).pack(side=tk.LEFT, padx=4)

        ttk.Separator(options, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        ttk.Label(options, text="ICO 尺寸:").pack(side=tk.LEFT)
        for size, label in SIZE_OPTIONS:
            ttk.Checkbutton(options, text=label, variable=self.size_vars[size]).pack(
                side=tk.LEFT, padx=4
            )

        ttk.Button(options, text="重新加载", command=self._reload_icons).pack(
            side=tk.RIGHT, padx=(8, 0)
        )

        body = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        list_frame = ttk.LabelFrame(body, text="图标列表", padding=6)
        body.add(list_frame, weight=2)

        list_btns = ttk.Frame(list_frame)
        list_btns.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(list_btns, text="全选", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_btns, text="全不选", command=self._select_none).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_btns, text="反选", command=self._invert_selection).pack(side=tk.LEFT, padx=2)

        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.icon_listbox = tk.Listbox(
            list_container,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            exportselection=False,
        )
        self.icon_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.icon_listbox.yview)
        self.icon_listbox.bind("<<ListboxSelect>>", self._on_list_select)

        self._checked: list[bool] = []

        preview_frame = ttk.LabelFrame(body, text="预览 (256px)", padding=6)
        body.add(preview_frame, weight=1)

        self.preview_label = ttk.Label(preview_frame, text="选择图标以预览", anchor=tk.CENTER)
        self.preview_label.pack(expand=True, fill=tk.BOTH)

        self.preview_name = ttk.Label(preview_frame, text="")
        self.preview_name.pack(pady=4)

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X, pady=(0, 6))

        self.export_btn = ttk.Button(actions, text="批量导出 .ico", command=self._start_export)
        self.export_btn.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        self.status_label = ttk.Label(actions, text="就绪")
        self.status_label.pack(side=tk.RIGHT)

        log_frame = ttk.LabelFrame(main, text="日志", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, height=8, yscrollcommand=log_scroll.set, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

    def _log(self, message: str) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_mode_ui(self) -> None:
        is_svg = self.input_mode.get() == "svg"
        if is_svg:
            self.input_label.config(text="SVG 目录:")
        else:
            self.input_label.config(text="输入目录 (iconfont.js + iconfont.json):")
        if is_svg:
            self.browse_files_btn.state(["!disabled"])
        else:
            self.browse_files_btn.state(["disabled"])

    def _on_mode_change(self) -> None:
        current = Path(self.input_dir.get())
        if self.input_mode.get() == "svg":
            if current == DEFAULT_ICONFONT_INPUT or not current.is_dir():
                self.input_dir.set(str(DEFAULT_SVG_INPUT))
            self._svg_file_paths = []
        else:
            if current == DEFAULT_SVG_INPUT or self._svg_file_paths:
                self.input_dir.set(str(DEFAULT_ICONFONT_INPUT))
            self._svg_file_paths = []
        self._update_mode_ui()
        self._reload_icons()

    def _browse_input(self) -> None:
        path = filedialog.askdirectory(initialdir=self.input_dir.get())
        if path:
            self._svg_file_paths = []
            self.input_dir.set(path)
            self._reload_icons()

    def _browse_svg_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 SVG 文件",
            initialdir=self.input_dir.get(),
            filetypes=[("SVG 文件", "*.svg"), ("所有文件", "*.*")],
        )
        if not paths:
            return
        self._svg_file_paths = [Path(p) for p in paths]
        if len(self._svg_file_paths) == 1:
            self.input_dir.set(str(self._svg_file_paths[0].parent))
        else:
            self.input_dir.set(f"({len(self._svg_file_paths)} 个文件)")
        self._reload_icons()

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get())
        if path:
            self.output_dir.set(path)

    def _reload_icons(self) -> None:
        try:
            if self.input_mode.get() == "svg":
                if self._svg_file_paths:
                    icons, warnings = load_svg_files(self._svg_file_paths)
                else:
                    icons, warnings = load_svgs_from_dir(Path(self.input_dir.get()))
            else:
                icons, warnings = load_icons_from_dir(Path(self.input_dir.get()))
        except (OSError, ValueError) as exc:
            self._icons = []
            self._checked = []
            self.icon_listbox.delete(0, tk.END)
            self._log(f"加载失败: {exc}")
            messagebox.showerror("加载失败", str(exc))
            return

        self._icons = icons
        self._checked = [True] * len(icons)
        self.icon_listbox.delete(0, tk.END)
        for icon in icons:
            self.icon_listbox.insert(tk.END, f"☑ {icon.font_class}  ({icon.name})")

        for w in warnings:
            self._log(f"警告: {w}")

        self._log(f"已加载 {len(icons)} 个图标。")
        self.status_label.config(text=f"已加载 {len(icons)} 个图标")

        if icons:
            self.icon_listbox.selection_set(0)
            self._show_preview(0)

    def _list_index_from_selection(self) -> int | None:
        sel = self.icon_listbox.curselection()
        if not sel:
            return None
        return int(sel[0])

    def _on_list_select(self, _event=None) -> None:
        idx = self._list_index_from_selection()
        if idx is not None:
            self._show_preview(idx)

    def _on_preview_refresh(self) -> None:
        idx = self._list_index_from_selection()
        if idx is not None:
            self._show_preview(idx)

    def _show_preview(self, index: int) -> None:
        if index < 0 or index >= len(self._icons):
            return
        icon = self._icons[index]
        try:
            img = preview_image(icon.svg_bytes, 256, background=self.background.get())
            self._preview_photo = image_to_photoimage(img)
            self.preview_label.config(image=self._preview_photo, text="")
            self.preview_name.config(text=f"{icon.font_class} — {icon.name}")
        except Exception as exc:
            self.preview_label.config(image="", text="预览失败")
            self.preview_name.config(text=str(exc))

    def _refresh_list_labels(self) -> None:
        for i, icon in enumerate(self._icons):
            mark = "☑" if self._checked[i] else "☐"
            self.icon_listbox.delete(i)
            self.icon_listbox.insert(i, f"{mark} {icon.font_class}  ({icon.name})")

    def _toggle_checked(self, index: int) -> None:
        if 0 <= index < len(self._checked):
            self._checked[index] = not self._checked[index]
            self._refresh_list_labels()

    def _select_all(self) -> None:
        self._checked = [True] * len(self._icons)
        self._refresh_list_labels()

    def _select_none(self) -> None:
        self._checked = [False] * len(self._icons)
        self._refresh_list_labels()

    def _invert_selection(self) -> None:
        self._checked = [not c for c in self._checked]
        self._refresh_list_labels()

    def icon_listbox_click(self, event) -> None:
        """Toggle checkbox on single click."""
        index = self.icon_listbox.nearest(event.y)
        if index >= 0:
            self._toggle_checked(index)

    def _get_selected_sizes(self) -> list[int]:
        sizes = [s for s, var in self.size_vars.items() if var.get()]
        if not sizes:
            raise ValueError("请至少选择一个 ICO 尺寸")
        return sorted(sizes)

    def _start_export(self) -> None:
        if self._exporting:
            return

        if not self._icons:
            if self.input_mode.get() == "svg":
                messagebox.showwarning("无图标", "请先加载有效的 SVG 目录或文件。")
            else:
                messagebox.showwarning("无图标", "请先加载有效的 iconfont 目录。")
            return

        try:
            sizes = self._get_selected_sizes()
        except ValueError as exc:
            messagebox.showwarning("选项错误", str(exc))
            return

        indices = [i for i, checked in enumerate(self._checked) if checked]
        if not indices:
            messagebox.showwarning("未选择", "请至少选择一个图标。")
            return

        output_dir = Path(self.output_dir.get())
        self._exporting = True
        self.export_btn.config(state=tk.DISABLED)
        self.progress["maximum"] = len(indices)
        self.progress["value"] = 0
        self.status_label.config(text="导出中…")

        thread = threading.Thread(
            target=self._export_worker,
            args=(indices, output_dir, sizes, self.background.get()),
            daemon=True,
        )
        thread.start()

    def _export_worker(
        self,
        indices: list[int],
        output_dir: Path,
        sizes: list[int],
        background: str,
    ) -> None:
        ok = 0
        failed: list[str] = []

        for n, idx in enumerate(indices):
            icon = self._icons[idx]
            filename = sanitize_filename(icon.font_class) + ".ico"
            out_path = output_dir / filename
            try:
                build_ico(icon.svg_bytes, out_path, sizes, background=background)
                ok += 1
                self.after(0, lambda i=icon, p=out_path: self._log(f"✓ {i.font_class} → {p}"))
            except Exception as exc:
                failed.append(f"{icon.font_class}: {exc}")
                self.after(0, lambda i=icon, e=exc: self._log(f"✗ {i.font_class}: {e}"))

            self.after(0, lambda v=n + 1: self.progress.configure(value=v))

        def _finish() -> None:
            self._exporting = False
            self.export_btn.config(state=tk.NORMAL)
            self.status_label.config(text=f"完成: {ok} 成功, {len(failed)} 失败")
            msg = f"成功导出 {ok} 个 ICO 到:\n{output_dir}"
            if failed:
                msg += f"\n\n失败 {len(failed)} 个:\n" + "\n".join(failed[:5])
                if len(failed) > 5:
                    msg += f"\n… 共 {len(failed)} 个"
            messagebox.showinfo("导出完成", msg)

        self.after(0, _finish)

    def run(self) -> None:
        self.icon_listbox.bind("<Button-1>", self.icon_listbox_click)
        self.mainloop()


def main() -> None:
    _set_app_user_model_id()
    app = IconfontToIcoApp()
    app.run()


if __name__ == "__main__":
    main()
