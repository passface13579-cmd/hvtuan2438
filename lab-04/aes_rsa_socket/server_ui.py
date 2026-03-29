import queue
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

try:
    from .chat_core import AesRsaChatServer
except ImportError:
    from chat_core import AesRsaChatServer


class ServerApp:
    BG = "#eef3ff"
    CARD = "#ffffff"
    CARD_ALT = "#f6f9ff"
    TEXT = "#1c2340"
    MUTED = "#576181"
    ACCENT = "#2f6df6"
    ACCENT_DARK = "#214fb7"
    SUCCESS = "#2c9d72"
    STOP = "#d04a63"
    LOG_BG = "#151a2e"
    LOG_TEXT = "#edf1ff"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TUAN AES-RSA Socket - Server")
        self.root.geometry("860x600")
        self.root.minsize(760, 530)

        self.server: AesRsaChatServer | None = None
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="12345")
        self.status_var = tk.StringVar(value="Stopped")
        self.client_count_var = tk.StringVar(value="Clients: 0")

        self._setup_styles()
        self._build_ui()
        self._process_events()
        self._set_status("Stopped", is_running=False)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_styles(self) -> None:
        self.root.configure(bg=self.BG)
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.style.configure("App.TFrame", background=self.BG)
        self.style.configure("Card.TFrame", background=self.CARD)
        self.style.configure("CardAlt.TFrame", background=self.CARD_ALT)
        self.style.configure("Header.TLabel", background=self.CARD, foreground=self.TEXT, font=("Segoe UI Semibold", 18))
        self.style.configure("SubHeader.TLabel", background=self.CARD, foreground=self.MUTED, font=("Segoe UI", 10))
        self.style.configure("Field.TLabel", background=self.CARD_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 10))
        self.style.configure("StatusText.TLabel", background=self.CARD_ALT, foreground=self.MUTED, font=("Segoe UI", 10))
        self.style.configure("Count.TLabel", background=self.CARD_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 10))

        self.style.configure(
            "TEntry",
            fieldbackground="#fffdf8",
            foreground=self.TEXT,
            borderwidth=1,
            relief="flat",
            padding=7,
        )

        self.style.configure(
            "Primary.TButton",
            background=self.ACCENT,
            foreground="#ffffff",
            borderwidth=0,
            padding=(12, 8),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map("Primary.TButton", background=[("active", self.ACCENT_DARK), ("disabled", "#9eb9bc")])

        self.style.configure(
            "Danger.TButton",
            background=self.STOP,
            foreground="#ffffff",
            borderwidth=0,
            padding=(12, 8),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map("Danger.TButton", background=[("active", "#6e2d35"), ("disabled", "#c1a5aa")])

        self.style.configure(
            "Ghost.TButton",
            background=self.CARD_ALT,
            foreground=self.ACCENT_DARK,
            borderwidth=0,
            padding=(10, 8),
            font=("Segoe UI Semibold", 10),
        )
        self.style.map("Ghost.TButton", background=[("active", "#dfe8ff")])

    def _build_ui(self) -> None:
        app = ttk.Frame(self.root, style="App.TFrame", padding=12)
        app.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(app, style="Card.TFrame", padding=(16, 12))
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="TUAN Secure Chat Server", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Colorful compact dashboard for AES-RSA socket lab",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        control = ttk.Frame(app, style="CardAlt.TFrame", padding=12)
        control.pack(fill=tk.X, pady=(0, 8))
        for col in (1, 3):
            control.columnconfigure(col, weight=1)

        ttk.Label(control, text="Host", style="Field.TLabel").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(control, textvariable=self.host_var, width=24).grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        ttk.Label(control, text="Port", style="Field.TLabel").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(control, textvariable=self.port_var, width=12).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        self.start_button = ttk.Button(control, text="Start Server", style="Primary.TButton", command=self.start_server)
        self.start_button.grid(row=0, column=4, padx=(12, 6), pady=6)

        self.stop_button = ttk.Button(
            control,
            text="Stop Server",
            style="Danger.TButton",
            command=self.stop_server,
            state=tk.DISABLED,
        )
        self.stop_button.grid(row=0, column=5, padx=(6, 6), pady=6)

        self.clear_button = ttk.Button(control, text="Clear Log", style="Ghost.TButton", command=self.clear_log)
        self.clear_button.grid(row=0, column=6, padx=(6, 6), pady=6)

        info = ttk.Frame(app, style="CardAlt.TFrame", padding=(12, 8))
        info.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(info, text="Status", style="StatusText.TLabel").pack(side=tk.LEFT)
        self.status_badge = tk.Label(
            info,
            textvariable=self.status_var,
            bg=self.STOP,
            fg="#ffffff",
            padx=10,
            pady=4,
            font=("Segoe UI Semibold", 9),
        )
        self.status_badge.pack(side=tk.LEFT, padx=(8, 12))
        ttk.Label(info, textvariable=self.client_count_var, style="Count.TLabel").pack(side=tk.RIGHT)
        ttk.Label(info, text="Server Console", style="StatusText.TLabel").pack(side=tk.RIGHT, padx=(0, 10))

        log_card = ttk.Frame(app, style="Card.TFrame", padding=10)
        log_card.pack(fill=tk.BOTH, expand=True)
        ttk.Label(log_card, text="Server Activity", style="SubHeader.TLabel").pack(anchor="w", padx=4, pady=(0, 6))

        self.log_area = scrolledtext.ScrolledText(
            log_card,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.LOG_BG,
            fg=self.LOG_TEXT,
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_config("time", foreground="#8ab4ff")
        self.log_area.tag_config("event", foreground=self.LOG_TEXT)
        self.log_area.tag_config("warn", foreground="#ffd166")
        self.log_area.tag_config("error", foreground="#ff7a90")

    def enqueue_log(self, message: str) -> None:
        self.event_queue.put(("log", message))

    def enqueue_client_count(self, count: int) -> None:
        self.event_queue.put(("count", count))

    def _process_events(self) -> None:
        while not self.event_queue.empty():
            event_type, payload = self.event_queue.get()
            if event_type == "log":
                self._append_log(str(payload))
            elif event_type == "count":
                self.client_count_var.set(f"Clients: {payload}")

        self.root.after(100, self._process_events)

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        lowered = message.lower()
        tag = "event"
        if "error" in lowered:
            tag = "error"
        elif "stopped" in lowered or "disconnected" in lowered:
            tag = "warn"

        self.log_area.configure(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.log_area.insert(tk.END, message + "\n", tag)
        self.log_area.see(tk.END)
        self.log_area.configure(state=tk.DISABLED)

    def clear_log(self) -> None:
        self.log_area.configure(state=tk.NORMAL)
        self.log_area.delete("1.0", tk.END)
        self.log_area.configure(state=tk.DISABLED)
        self._append_log("Log cleared")

    def _set_status(self, text: str, is_running: bool) -> None:
        self.status_var.set(text)
        self.status_badge.configure(bg=self.SUCCESS if is_running else self.STOP)

    def start_server(self) -> None:
        host = self.host_var.get().strip() or "127.0.0.1"

        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            return

        self.server = AesRsaChatServer(
            host=host,
            port=port,
            on_log=self.enqueue_log,
            on_client_count=self.enqueue_client_count,
        )

        try:
            self.server.start()
            self._set_status(f"Running at {host}:{port}", is_running=True)
            self.start_button.configure(state=tk.DISABLED)
            self.stop_button.configure(state=tk.NORMAL)
        except OSError as error:
            messagebox.showerror("Server Error", str(error))
            self.server = None

    def stop_server(self) -> None:
        if not self.server:
            return
        self.server.stop()
        self.server = None
        self._set_status("Stopped", is_running=False)
        self.client_count_var.set("Clients: 0")
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def on_close(self) -> None:
        self.stop_server()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = ServerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
