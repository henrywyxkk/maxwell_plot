"""File list panel with drag-drop support for CSV files (tkinter)."""
import os
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

from core.csv_parser import parse_maxwell_csv


class FileListPanel(ttk.LabelFrame):
    """Panel showing loaded CSV files with add/remove and drag-drop."""

    def __init__(self, parent, on_files_changed=None):
        super().__init__(parent, text="CSV Files", padding=4)
        self._filepaths: list[str] = []
        self._on_files_changed = on_files_changed
        self._setup_ui()

    def _setup_ui(self):
        # Listbox with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                   selectmode=tk.EXTENDED, height=8)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._listbox.yview)

        # Drag-drop on Windows: use tkdnd if available, else just file dialogs
        self._listbox.bind("<Delete>", lambda e: self._on_remove())
        self._listbox.bind("<Double-Button-1>", lambda e: self._on_remove())

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(btn_frame, text="Add Files", command=self._on_add).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Add Folder", command=self._on_add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Remove", command=self._on_remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._on_clear).pack(side=tk.LEFT, padx=2)

    def _on_add(self):
        paths = filedialog.askopenfilenames(
            title="Open Maxwell CSV Files",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        self._add_paths(paths)

    def _on_add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing CSV Files")
        if folder:
            paths = []
            for f in sorted(Path(folder).glob('*')):
                if f.suffix.lower() == '.csv':
                    paths.append(str(f))
            self._add_paths(paths)

    def _add_paths(self, paths):
        """Add multiple paths, skipping duplicates."""
        added = False
        for path in paths:
            if path not in self._filepaths:
                self._filepaths.append(path)
                self._add_item(path)
                added = True
        if added and self._on_files_changed:
            self._on_files_changed()

    def _on_remove(self):
        selected = self._listbox.curselection()
        for idx in reversed(selected):
            self._listbox.delete(idx)
            if idx < len(self._filepaths):
                self._filepaths.pop(idx)
        if selected and self._on_files_changed:
            self._on_files_changed()

    def _on_clear(self):
        self._filepaths.clear()
        self._listbox.delete(0, tk.END)
        if self._on_files_changed:
            self._on_files_changed()

    def _add_item(self, filepath: str):
        try:
            parsed = parse_maxwell_csv(filepath)
            cols = ", ".join(parsed.column_names[:5])
            if len(parsed.column_names) > 5:
                cols += " …"
            label = f"{os.path.basename(filepath)}  [{cols}]"
        except Exception:
            label = f"{os.path.basename(filepath)}  (parse error)"
        self._listbox.insert(tk.END, label)

    @property
    def filepaths(self) -> list[str]:
        return list(self._filepaths)

    @property
    def count(self) -> int:
        return len(self._filepaths)
