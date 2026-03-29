import queue
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

try:
    from .chat_core import AesRsaChatClient
except ImportError:
    from chat_core import AesRsaChatClient


class ClientApp:
    BG = "#eef3ff"
    CARD = "#ffffff"
    CARD_ALT = "#f6f9ff"
    TEXT = "#1c2340"
    MUTED = "#576181"
    ACCENT = "#2f6df6"
    ACCENT_DARK = "#214fb7"
    STOP = "#d04a63"
    LOG_BG = "#151a2e"
    LOG_TEXT = "#edf1ff"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TUAN AES-RSA Socket - Client")
        self.root.geometry("860x610")
        self.root.minsize(760, 530)

        self.client = AesRsaChatClient(on_message=self.enqueue_message, on_status=self.enqueue_status)
        self.event_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value="12345")
        self.name_var = tk.StringVar(value="User")
        self.status_var = tk.StringVar(value="Not connected")

        self._setup_styles()
        self._build_ui()
        self._process_events()
        self._set_connected_ui(False)
        self._set_status_chip("Not connected")

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
        self.style.configure("ComposeTitle.TLabel", background=self.CARD_ALT, foreground=self.TEXT, font=("Segoe UI Semibold", 10))

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
        self.style.map("Ghost.TButton", background=[("active", "#ece1d2")])

    def _build_ui(self) -> None:
        app = ttk.Frame(self.root, style="App.TFrame", padding=12)
        app.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(app, style="Card.TFrame", padding=(16, 12))
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="TUAN Secure Chat Client", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Colorful compact UI for AES-RSA socket lab",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        connect_card = ttk.Frame(app, style="CardAlt.TFrame", padding=12)
        connect_card.pack(fill=tk.X, pady=(0, 8))
        for col in (1, 3, 5):
            connect_card.columnconfigure(col, weight=1)

        ttk.Label(connect_card, text="Host", style="Field.TLabel").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(connect_card, textvariable=self.host_var, width=18).grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        ttk.Label(connect_card, text="Port", style="Field.TLabel").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(connect_card, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(connect_card, text="Name", style="Field.TLabel").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(connect_card, textvariable=self.name_var, width=14).grid(row=0, column=5, padx=6, pady=6, sticky="ew")

        self.connect_button = ttk.Button(connect_card, text="Connect", style="Primary.TButton", command=self.connect_server)
        self.connect_button.grid(row=0, column=6, padx=(12, 6), pady=6)

        self.disconnect_button = ttk.Button(
            connect_card,
            text="Disconnect",
            style="Danger.TButton",
            command=self.disconnect_server,
        )
        self.disconnect_button.grid(row=0, column=7, padx=(6, 6), pady=6)

        self.clear_button = ttk.Button(connect_card, text="Clear Chat", style="Ghost.TButton", command=self.clear_chat)
        self.clear_button.grid(row=0, column=8, padx=(6, 6), pady=6)

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
        self.status_badge.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(info, text="Enter to send", style="StatusText.TLabel").pack(side=tk.RIGHT)

        compose_card = ttk.Frame(app, style="CardAlt.TFrame", padding=10)
        compose_card.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(compose_card, text="Message Box (Type Here)", style="ComposeTitle.TLabel").pack(anchor="w", pady=(0, 6))

        compose_row = ttk.Frame(compose_card, style="CardAlt.TFrame")
        compose_row.pack(fill=tk.X)

        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(compose_row, textvariable=self.message_var, font=("Segoe UI", 11))
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", lambda _event: self.send_message())

        self.send_button = ttk.Button(compose_row, text="Send", style="Primary.TButton", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)

        chat_card = ttk.Frame(app, style="Card.TFrame", padding=10)
        chat_card.pack(fill=tk.BOTH, expand=True)
        ttk.Label(chat_card, text="Chat Room", style="SubHeader.TLabel").pack(anchor="w", padx=4, pady=(0, 6))

        self.chat_area = scrolledtext.ScrolledText(
            chat_card,
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
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        self.chat_area.tag_config("time", foreground="#8ab4ff")
        self.chat_area.tag_config("me", foreground="#5de6c1")
        self.chat_area.tag_config("peer", foreground="#ffd166")
        self.chat_area.tag_config("system", foreground="#b9c6ff")

    def _set_connected_ui(self, connected: bool) -> None:
        self.connect_button.configure(state=tk.DISABLED if connected else tk.NORMAL)
        self.disconnect_button.configure(state=tk.NORMAL if connected else tk.DISABLED)
        self.send_button.configure(state=tk.NORMAL if connected else tk.DISABLED)
        self.message_entry.configure(state=tk.NORMAL if connected else tk.DISABLED)
        if connected:
            self.message_entry.focus_set()

    def enqueue_message(self, message: str) -> None:
        self.event_queue.put(("message", message))

    def enqueue_status(self, message: str) -> None:
        self.event_queue.put(("status", message))

    def _process_events(self) -> None:
        while not self.event_queue.empty():
            event_type, payload = self.event_queue.get()
            if event_type == "message":
                self._append_chat(payload)
            elif event_type == "status":
                self.status_var.set(payload)
                self._set_status_chip(payload)
                if payload.lower().startswith("disconnected"):
                    self._set_connected_ui(False)

        self.root.after(100, self._process_events)

    def _append_chat(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = "peer"
        if message.startswith("You:"):
            tag = "me"
        elif message.startswith("[System]"):
            tag = "system"

        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.insert(tk.END, f"[{timestamp}] ", "time")
        self.chat_area.insert(tk.END, message + "\n", tag)
        self.chat_area.see(tk.END)
        self.chat_area.configure(state=tk.DISABLED)

    def clear_chat(self) -> None:
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.configure(state=tk.DISABLED)
        self._append_chat("[System] Chat cleared")

    def _set_status_chip(self, status_text: str) -> None:
        lowered = status_text.lower()
        bg = self.STOP
        if "connected" in lowered and "disconnected" not in lowered:
            bg = self.ACCENT
        elif "closed" in lowered:
            bg = "#9b5d2f"
        self.status_badge.configure(bg=bg)

    def connect_server(self) -> None:
        host = self.host_var.get().strip() or "127.0.0.1"
        name = self.name_var.get().strip() or "User"

        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be an integer.")
            return

        try:
            self.client.connect(host=host, port=port)
            self.client.send(f"/name {name}")
            self._set_connected_ui(True)
            self._append_chat(f"[System] You joined as {name}")
        except Exception as error:
            messagebox.showerror("Connect Error", str(error))

    def disconnect_server(self) -> None:
        try:
            self.client.disconnect(send_exit=True)
        except Exception:
            pass
        self.status_var.set("Disconnected from server")
        self._set_status_chip("Disconnected from server")
        self._set_connected_ui(False)

    def send_message(self) -> None:
        message = self.message_var.get().strip()
        if not message:
            return

        try:
            self.client.send(message)
            self._append_chat(f"You: {message}")
            self.message_var.set("")
        except Exception as error:
            messagebox.showerror("Send Error", str(error))
            self._set_connected_ui(False)

    def on_close(self) -> None:
        self.disconnect_server()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
