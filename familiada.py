"""Prosta, lokalna tablica do weselnej gry w stylu Familiady.

Uruchom: python familiada.py
Tablica otwiera się w drugim oknie — przeciągnij je na telewizor/projektor
i wciśnij F11 (albo przycisk „Pełny ekran”).
"""
from __future__ import annotations

import json
import queue
import sys
import threading
from copy import deepcopy
from pathlib import Path


def enable_windows_dpi_awareness() -> None:
    """Używa prawdziwych pikseli każdego monitora także przy skalowaniu Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # PER_MONITOR_AWARE_V2. Musi zostać wywołane przed utworzeniem Tk().
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            # Zapas dla starszych wersji Windows.
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


enable_windows_dpi_awareness()

# Ważne: Tk ładowany jest dopiero po ustawieniu kontekstu DPI procesu.
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# W wersji EXE pliki pytań i zapisy gry są obok programu, natomiast zasoby
# dołączone przez PyInstaller (np. WAV) pozostają w katalogu pakietu.
BUNDLE_DIR = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else BUNDLE_DIR
SAVE_FILE = APP_DIR / "pytania.json"
SOUNDS_DIR = BUNDLE_DIR / "assets" / "sounds"
MIN_ANSWERS = 4
MAX_ANSWERS = 6
DEFAULT_SOUNDS = {
    "intro": str(SOUNDS_DIR / "intro-familiada.wav"),
    "reveal": str(SOUNDS_DIR / "dobra-odpowiedz.wav"),
    "strike": str(SOUNDS_DIR / "blad.wav"),
    "win": str(SOUNDS_DIR / "przed-i-po-rundzie-familiada.wav"),
    "final_time": str(SOUNDS_DIR / "czas-final-familiada.wav"),
    "bells": str(SOUNDS_DIR / "dzwoneczki-familiada.wav"),
    "repeat": str(SOUNDS_DIR / "powtorzenie-w-finale-familiada.wav"),
}


class Sound:
    """Krótkie, autorskie sygnały; nie wymaga plików audio ani Internetu."""

    _queue: queue.Queue[str] = queue.Queue()
    _worker_started = False

    @classmethod
    def _play_wav_queue(cls) -> None:
        try:
            import winsound
            while True:
                file_path = cls._queue.get()
                try:
                    # Odtwarzanie blokujące we własnym wątku zapobiega ucinaniu
                    # krótkich WAV-ów przez opóźniony głośnik Bluetooth.
                    winsound.PlaySound(file_path, winsound.SND_FILENAME)
                finally:
                    cls._queue.task_done()
        except Exception:
            pass

    @classmethod
    def _enqueue_wav(cls, file_path: str) -> None:
        if not cls._worker_started:
            cls._worker_started = True
            threading.Thread(target=cls._play_wav_queue, daemon=True).start()
        cls._queue.put(file_path)

    @staticmethod
    def play(kind: str, file_path: str = "") -> None:
        try:
            import winsound
            if file_path and Path(file_path).suffix.lower() == ".wav":
                Sound._enqueue_wav(file_path)
                return
            sequences = {
                "reveal": [(740, 75), (988, 120)],
                "strike": [(180, 170), (120, 250)],
                "win": [(523, 90), (659, 90), (784, 100), (1047, 250)],
            }
            for tone, duration in sequences.get(kind, []):
                winsound.Beep(tone, duration)
        except Exception:
            # Na systemach bez winsoundu aplikacja pozostaje w pełni używalna.
            pass


class Board(tk.Toplevel):
    BG = "#07101a"
    DOT = "#dfff22"
    DIM_DOT = "#6a741a"
    RED = "#ec273d"

    def __init__(self, master: "HostApp") -> None:
        super().__init__(master)
        self.app = master
        self.title("Familiada — TABLICA")
        self.configure(bg="#121d55")
        self.geometry("1100x760")
        self.minsize(760, 520)
        self._projector_fullscreen = False
        self._restore_geometry = ""
        self.bind("<F11>", lambda _: self.toggle_fullscreen())
        self.bind("<Escape>", lambda _: self.exit_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.canvas = tk.Canvas(self, bg="#121d55", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())

    def toggle_fullscreen(self) -> None:
        if self._projector_fullscreen or self.attributes("-fullscreen"):
            self.exit_fullscreen()
        else:
            self.attributes("-fullscreen", True)

    def projector_fullscreen(self, left: int, top: int, width: int, height: int) -> None:
        """Pełny ekran na wskazanym monitorze w fizycznych pikselach Windows."""
        if not self._projector_fullscreen:
            self._restore_geometry = self.geometry()
        self.attributes("-fullscreen", False)
        # Tkinterowy fullscreen i geometry() potrafią użyć wirtualnych pikseli
        # przy monitorach o różnym DPI. Ramkę usuwa Tk, a pozycję/natywny rozmiar
        # wymuszamy bezpośrednio przez Windows w pikselach z EnumDisplayMonitors.
        self.overrideredirect(True)
        self.deiconify()
        self.lift()
        self.focus_force()
        self.update_idletasks()
        # Dopiero po deikonizacji: samo pokazanie okna może zmienić jego pozycję.
        self._set_native_window_rect(left, top, width, height)
        # Tkinter może dodać przesunięcie zależne od DPI po mapowaniu okna.
        # Odczytujemy rzeczywiste granice i korygujemy je w tym samym układzie.
        for _ in range(2):
            self.update_idletasks()
            actual = self._native_window_rect()
            if not actual:
                break
            actual_left, actual_top, _actual_width, _actual_height = actual
            delta_x, delta_y = actual_left - left, actual_top - top
            if abs(delta_x) <= 1 and abs(delta_y) <= 1:
                break
            self._set_native_window_rect(left - delta_x, top - delta_y, width, height)
        self._projector_fullscreen = True

    def _set_native_window_rect(self, left: int, top: int, width: int, height: int) -> None:
        """Przesuwa okno bez konwersji współrzędnych wykonywanej przez Tk."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
            user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, wintypes.UINT,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL
            HWND_TOP = wintypes.HWND(0)
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(
                wintypes.HWND(self.winfo_id()), HWND_TOP, left, top, width, height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW | SWP_FRAMECHANGED,
            )
        except Exception:
            # Awaryjnie zachowujemy poprzednie działanie na systemach bez WinAPI.
            self.geometry(f"{width}x{height}{left:+d}{top:+d}")

    def _native_window_rect(self) -> tuple[int, int, int, int] | None:
        try:
            import ctypes
            from ctypes import wintypes

            rect = wintypes.RECT()
            if not ctypes.windll.user32.GetWindowRect(wintypes.HWND(self.winfo_id()), ctypes.byref(rect)):
                return None
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:
            return None

    def exit_fullscreen(self) -> None:
        if self._projector_fullscreen:
            self.overrideredirect(False)
            if self._restore_geometry:
                self.geometry(self._restore_geometry)
            self._projector_fullscreen = False
        self.attributes("-fullscreen", False)

    def refresh(self) -> None:
        self.draw()

    def draw(self) -> None:
        """Rysuje stylizowaną matrycę LED, skalując ją do każdego ekranu."""
        c = self.canvas
        w, h = max(c.winfo_width(), 760), max(c.winfo_height(), 520)
        c.delete("all")
        # Telewizyjna, kolorowa rama — celowo bez znaków programu i stacji.
        c.create_rectangle(0, 0, w, h, fill="#152a89", outline="")
        c.create_rectangle(0, 0, w * .34, h, fill="#e51f3b", outline="")
        c.create_rectangle(w * .67, 0, w, h, fill="#1a2caf", outline="")
        c.create_arc(-w*.08, -h*.1, w*1.08, h*1.07, start=0, extent=180, style="arc",
                     outline="#ff92b9", width=max(5, int(w*.009)))
        c.create_arc(-w*.075, -h*.09, w*1.075, h*1.05, start=0, extent=180, style="arc",
                     outline="#9d87ff", width=max(3, int(w*.004)))

        bx, by, bw, bh = w*.06, h*.20, w*.88, h*.69
        c.create_rectangle(bx-8, by-8, bx+bw+8, by+bh+8, fill="#4e5262", outline="#b7b8c4", width=3)
        c.create_rectangle(bx, by, bx+bw, by+bh, fill=self.BG, outline="#010307", width=3)
        state = self.app.state
        if state.get("final_summary"):
            self.draw_final_summary(c, w, h, bx, by, bw, bh, state)
            return
        if state.get("final_mode"):
            self.draw_final_turn(c, w, h, bx, by, bw, bh, state)
            return
        # Subtelna siatka obudowy LED.
        cell = max(9, int(min(bw/52, bh/25)))
        for x in range(int(bx)+4, int(bx+bw), cell):
            c.create_line(x, by, x, by+bh, fill="#18222b")
        for y in range(int(by)+4, int(by+bh), cell):
            c.create_line(bx, y, bx+bw, y, fill="#18222b")

        question = state["question"] or "FAMILIADA"
        c.create_text(w/2, h*.09, text=question.upper(), fill="white", font=("Arial", max(14, int(w*.021)), "bold"), width=w*.78, justify="center")
        answers = state["answers"]
        active = [(i, a) for i, a in enumerate(answers) if a["text"]]
        row_h = min(bh*.105, (bh*.66 / max(1, len(active))))
        start_y = by + bh*.08
        font_size = max(14, int(row_h*.55))
        led_font = ("Courier New", font_size, "bold")
        for row, (index, answer) in enumerate(active):
            y = start_y + row * row_h
            c.create_line(bx+bw*.12, y+row_h*.43, bx+bw*.90, y+row_h*.43, fill="#252d35", width=1)
            # Stała długość maski nie zdradza długości ukrytej odpowiedzi.
            text = answer["text"].upper() if answer["shown"] else "·" * 24
            points_visible = answer["shown"] and (not state.get("final_mode") or answer.get("points_shown", False))
            points = str(answer["points"]) if points_visible else ""
            c.create_text(bx+bw*.15, y, text=f"{index + 1}", fill=self.DOT, anchor="nw", font=led_font)
            c.create_text(bx+bw*.23, y, text=text, fill=self.DOT if answer["shown"] else self.DIM_DOT,
                          anchor="nw", font=led_font)
            c.create_text(bx+bw*.84, y, text=points, fill=self.DOT, anchor="ne", font=led_font)

        total_y = by + bh*.80
        c.create_text(bx+bw*.60, total_y, text="SUMA", fill=self.DOT, anchor="w", font=led_font)
        c.create_text(bx+bw*.84, total_y, text=str(state["round_points"]), fill=self.DOT, anchor="ne", font=led_font)
        # Błędy po prawej, podobnie jak pionowa kolumna symboli w teleturniejach.
        for i in range(3):
            color = self.RED if i < state["strikes"] else "#252d35"
            c.create_text(bx+bw*.94, by+bh*(.18+i*.18), text="✕", fill=color, font=("Arial", font_size+10, "bold"))
        if state.get("final_mode"):
            c.create_text(w*.5, h*.035, text=f"FINAŁ  •  PYTANIE {state['final_question_number']} / 5", fill="#ffe62b", font=("Arial", max(12, int(w*.016)), "bold"))
            c.create_text(w*.16, h*.94, text=f"ZAWODNIK 1:  {state['final_score1']}", fill="white", font=("Arial", max(11, int(w*.014)), "bold"))
            c.create_text(w*.5, h*.94, text=f"CEL: {state['final_target']}", fill="#ffe62b", font=("Arial", max(11, int(w*.014)), "bold"))
            c.create_text(w*.84, h*.94, text=f"ZAWODNIK 2:  {state['final_score2']}", fill="white", font=("Arial", max(11, int(w*.014)), "bold"))
            c.create_text(w*.90, h*.10, text=f"CZAS\n{state['final_timer']}", fill="#ffef37", font=("Arial", max(13, int(w*.022)), "bold"), justify="center")
        else:
            c.create_text(w*.16, h*.94, text=f"{state['team1_name'].upper()}:  {state['team1']}", fill="white", font=("Arial", max(11, int(w*.014)), "bold"))
            c.create_text(w*.84, h*.94, text=f"{state['team2_name'].upper()}:  {state['team2']}", fill="white", font=("Arial", max(11, int(w*.014)), "bold"))

    def draw_final_summary(self, canvas: tk.Canvas, width: int, height: int, x: float, y: float, board_width: float, board_height: float, state: dict) -> None:
        """Końcowy ekran finału, przeznaczony dla publiczności na drugim ekranie."""
        total = state["final_score1"] + state["final_score2"]
        target = state["final_target"]
        success = total >= target
        team1, team2 = state["team1"], state["team2"]
        name1, name2 = state["team1_name"].upper(), state["team2_name"].upper()
        if team1 == team2:
            winner = "REMIS!"
        else:
            winner = f"ZWYCIĘŻA {name1 if team1 > team2 else name2}!"
        canvas.create_text(width / 2, y + board_height * .11, text="PODSUMOWANIE ROZGRYWKI", fill="#ffe62b", font=("Arial", max(20, int(width*.032)), "bold"))
        canvas.create_text(x + board_width*.26, y + board_height * .33, text=f"{name1}\n{team1}", fill="white", font=("Arial", max(17, int(width*.024)), "bold"), justify="center")
        canvas.create_text(x + board_width*.74, y + board_height * .33, text=f"{name2}\n{team2}", fill="white", font=("Arial", max(17, int(width*.024)), "bold"), justify="center")
        canvas.create_text(width / 2, y + board_height * .54, text=winner, fill="#dfff22", font=("Arial", max(20, int(width*.028)), "bold"))
        canvas.create_text(width / 2, y + board_height * .68, text=f"FINAŁ: {total} / {target}", fill="#dfff22", font=("Courier New", max(18, int(width*.028)), "bold"))
        message = "CEL FINAŁU OSIĄGNIĘTY" if success else f"DO CELU FINAŁU BRAKUJE {target - total} PKT"
        color = "#dfff22" if success else "#ff5e6b"
        canvas.create_text(width / 2, y + board_height * .83, text=message, fill=color, font=("Arial", max(15, int(width*.022)), "bold"))

    def draw_final_turn(self, canvas: tk.Canvas, width: int, height: int, x: float, y: float, board_width: float, board_height: float, state: dict) -> None:
        player = state["final_active_player"]
        canvas.create_text(width / 2, y + board_height*.08, text=f"FINAŁ • PYTANIE {state['final_question_number']} / 5 • CZAS {state['final_timer']}", fill="#ffe62b", font=("Arial", max(16, int(width*.023)), "bold"))
        canvas.create_text(x + board_width*.25, y + board_height*.17, text="ZAWODNIK 1", fill="white", font=("Arial", max(13, int(width*.018)), "bold"))
        canvas.create_text(x + board_width*.75, y + board_height*.17, text="ZAWODNIK 2", fill="white", font=("Arial", max(13, int(width*.018)), "bold"))
        row_height = board_height*.105
        answer_font = ("Courier New", max(13, int(width*.018)), "bold")
        score_font = ("Courier New", max(16, int(width*.024)), "bold")
        for index in range(5):
            row_y = y + board_height*.25 + index * row_height
            canvas.create_text(x + board_width*.06, row_y, text=str(index + 1), fill="#dfff22", anchor="w", font=answer_font)
            for contestant, answer_x, points_x, anchor in ((1, x + board_width*.12, x + board_width*.46, "w"), (2, x + board_width*.54, x + board_width*.94, "w")):
                response = state.get("final_responses", {}).get(f"{contestant}:{index}", {})
                answer = response.get("answer", "") if response.get("answer_shown") else "— — —"
                points = str(response.get("points", 0)) if response.get("points_shown") else ""
                canvas.create_text(answer_x, row_y, text=answer.upper(), fill="#dfff22" if response.get("answer_shown") else "#6a741a", anchor=anchor, font=answer_font)
                canvas.create_text(points_x, row_y, text=points, fill="#dfff22", anchor="e", font=score_font)
            canvas.create_line(x + board_width*.04, row_y + row_height*.43, x + board_width*.96, row_y + row_height*.43, fill="#252d35")
        total = state["final_score1"] + state["final_score2"]
        canvas.create_text(width / 2, y + board_height*.84, text=f"SUMA  {total} / {state['final_target']}", fill="#dfff22", font=("Courier New", max(20, int(width*.032)), "bold"))
        canvas.create_text(width*.18, height*.94, text=f"ZAWODNIK 1: {state['final_score1']}", fill="white", font=("Arial", max(11, int(width*.014)), "bold"))
        canvas.create_text(width*.82, height*.94, text=f"ZAWODNIK 2: {state['final_score2']}", fill="white", font=("Arial", max(11, int(width*.014)), "bold"))
class HostApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Familiada — panel prowadzącego")
        self.geometry("830x720")
        self.minsize(720, 560)
        self.state = self.default_state()
        self.answer_text: list[tk.StringVar] = []
        self.answer_points: list[tk.StringVar] = []
        self._final_timer_after: str | None = None
        self._round_before_final: dict | None = None
        self._build_ui()
        self.board = Board(self)
        self.load_silent()
        self.set_answer_count()
        self.set_game_mode(bool(self.state.get("final_mode", False)))
        self.refresh()

    @staticmethod
    def default_state() -> dict:
        return {"question": "", "answers": [], "team1": 0, "team2": 0,
                "team1_name": "Drużyna 1", "team2_name": "Drużyna 2", "round_points": 0,
                "strikes": 0, "sound_files": DEFAULT_SOUNDS.copy(), "answer_count": MIN_ANSWERS,
                "reveal_history": [], "scores_unlocked": False, "final_mode": False,
                "final_active_player": 1, "final_question_number": 1, "final_score1": 0,
                "final_score2": 0, "final_target": 200, "final_timer": 0, "final_summary": False,
                "final_questions": [], "final_question_index": 0, "final_progress": {}, "final_responses": {},
                "final_phase": "collect1"}

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        top = ttk.Frame(root)
        top.pack(fill="x")
        ttk.Label(top, text="PYTANIE:", font=("Arial", 11, "bold")).pack(anchor="w")
        self.question_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.question_var, font=("Arial", 14)).pack(fill="x", pady=(2, 10))

        answers_header = ttk.Frame(root)
        answers_header.pack(fill="x")
        self.answers_header = answers_header
        ttk.Label(answers_header, text="ODPOWIEDZI I PUNKTY", font=("Arial", 11, "bold")).pack(side="left")
        ttk.Label(answers_header, text="Liczba odpowiedzi:").pack(side="left", padx=(20, 4))
        self.answer_count_var = tk.IntVar(value=MIN_ANSWERS)
        ttk.Spinbox(answers_header, from_=MIN_ANSWERS, to=MAX_ANSWERS, width=3,
                    textvariable=self.answer_count_var, command=self.set_answer_count).pack(side="left")
        self.answer_count_var.trace_add("write", lambda *_: self.set_answer_count())
        table = ttk.Frame(root)
        table.pack(fill="x", pady=(4, 8))
        self.answers_table = table
        ttk.Label(table, text="#", width=3).grid(row=0, column=0)
        ttk.Label(table, text="Odpowiedź").grid(row=0, column=1, sticky="w")
        ttk.Label(table, text="Pkt", width=8).grid(row=0, column=2)
        self.answer_rows: list[list[tk.Widget]] = []
        for i in range(MAX_ANSWERS):
            text_var, points_var = tk.StringVar(), tk.StringVar(value="0")
            self.answer_text.append(text_var)
            self.answer_points.append(points_var)
            number = ttk.Label(table, text=str(i + 1), width=3)
            answer = ttk.Entry(table, textvariable=text_var, font=("Arial", 11))
            points = ttk.Entry(table, textvariable=points_var, width=8)
            number.grid(row=i + 1, column=0, pady=2)
            answer.grid(row=i + 1, column=1, sticky="ew", padx=(0, 8), pady=2)
            points.grid(row=i + 1, column=2, pady=2)
            self.answer_rows.append([number, answer, points])
        table.columnconfigure(1, weight=1)

        actions = ttk.LabelFrame(root, text="Sterowanie rundą", padding=10)
        actions.pack(fill="x", pady=8)
        self.round_actions = actions
        self.reveal_buttons: list[ttk.Button] = []
        for i in range(MAX_ANSWERS):
            button = ttk.Button(actions, text=f"Odkryj {i + 1}", command=lambda n=i: self.reveal(n))
            button.grid(row=0 if i < 4 else 1, column=i % 4, padx=3, pady=3, sticky="ew")
            self.reveal_buttons.append(button)
            actions.columnconfigure(i % 4, weight=1)
        ttk.Button(actions, text="✕  Błąd", command=self.strike).grid(row=2, column=0, padx=3, pady=(8, 3), sticky="ew")
        ttk.Button(actions, text="Wyczyść błędy", command=self.clear_strikes).grid(row=2, column=1, padx=3, pady=(8, 3), sticky="ew")
        ttk.Button(actions, text="Przyznaj rundę → D1", command=lambda: self.award(1)).grid(row=2, column=2, padx=3, pady=(8, 3), sticky="ew")
        ttk.Button(actions, text="Przyznaj rundę → D2", command=lambda: self.award(2)).grid(row=2, column=3, padx=3, pady=(8, 3), sticky="ew")
        ttk.Button(actions, text="↶ Cofnij ostatnie odkrycie", command=self.undo_reveal).grid(row=3, column=0, columnspan=2, padx=3, pady=3, sticky="ew")

        self.final_actions = ttk.LabelFrame(root, text="Sterowanie finałem", padding=10)
        self.final_status = tk.StringVar()
        ttk.Label(self.final_actions, textvariable=self.final_status, font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=4, pady=(0, 6))
        ttk.Button(self.final_actions, text="Importuj 5 pytań finałowych…", command=self.import_final_questions).grid(row=1, column=0, columnspan=2, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="← Poprzednie pytanie", command=lambda: self.navigate_final_question(-1)).grid(row=1, column=2, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="Następne pytanie →", command=lambda: self.navigate_final_question(1)).grid(row=1, column=3, padx=3, pady=3, sticky="ew")
        options = ttk.LabelFrame(self.final_actions, text="Możliwe odpowiedzi i punkty dla bieżącego pytania", padding=5)
        options.grid(row=2, column=0, columnspan=4, padx=3, pady=(8, 5), sticky="ew")
        self.final_option_labels: list[ttk.Label] = []
        for i in range(MAX_ANSWERS):
            label = ttk.Label(options, text="", font=("Arial", 10, "bold"))
            label.grid(row=i // 3, column=i % 3, padx=10, pady=2, sticky="w")
            options.columnconfigure(i % 3, weight=1)
            self.final_option_labels.append(label)

        player_panels = ttk.Frame(self.final_actions)
        player_panels.grid(row=3, column=0, columnspan=4, sticky="ew", pady=3)
        self.final_choice_vars = {1: tk.StringVar(), 2: tk.StringVar()}
        self.final_points_vars = {1: tk.StringVar(value="—"), 2: tk.StringVar(value="—")}
        self.final_selection_labels: dict[int, ttk.Label] = {}
        for player, seconds in ((1, 15), (2, 20)):
            panel = ttk.LabelFrame(player_panels, text=f"Zawodnik {player} — {seconds} s", padding=7)
            panel.pack(side="left", expand=True, fill="both", padx=4)
            ttk.Label(panel, text="Nr odpowiedzi:").grid(row=0, column=0, sticky="w")
            ttk.Spinbox(panel, from_=0, to=MAX_ANSWERS, width=4, textvariable=self.final_choice_vars[player]).grid(row=0, column=1, padx=4, sticky="w")
            selected = ttk.Label(panel, text="—", font=("Arial", 10, "bold"))
            selected.grid(row=0, column=2, padx=4, sticky="w")
            self.final_selection_labels[player] = selected
            ttk.Label(panel, text="Punkty wg listy:").grid(row=1, column=0, sticky="w", pady=(5, 0))
            ttk.Label(panel, textvariable=self.final_points_vars[player], font=("Arial", 11, "bold")).grid(row=1, column=1, sticky="w", pady=(5, 0))
            ttk.Button(panel, text=f"▶ Start {seconds} s", command=lambda p=player: self.start_player_timer(p)).grid(row=2, column=0, padx=2, pady=(7, 2), sticky="ew")
            ttk.Button(panel, text="Zapisz odpowiedź", command=lambda p=player: self.save_final_response(p)).grid(row=2, column=1, padx=2, pady=(7, 2), sticky="ew")
            ttk.Button(panel, text="Odsłoń odpowiedź", command=lambda p=player: self.reveal_final_answer(p)).grid(row=3, column=0, padx=2, pady=2, sticky="ew")
            ttk.Button(panel, text="Odsłoń punkty 🔔", command=lambda p=player: self.reveal_final_score(p)).grid(row=3, column=1, padx=2, pady=2, sticky="ew")
            ttk.Button(panel, text="Wyczyść", command=lambda p=player: self.clear_final_response(p)).grid(row=2, column=2, rowspan=2, padx=2, pady=2, sticky="nsew")
            panel.columnconfigure(1, weight=1)
        ttk.Button(self.final_actions, text="★ Pokaż podsumowanie finału", command=self.show_final_summary).grid(row=4, column=0, columnspan=4, padx=3, pady=(6, 3), sticky="ew")
        for column in range(4):
            self.final_actions.columnconfigure(column, weight=1)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(4, 0))
        self.bottom_controls = bottom
        self.new_round_button = ttk.Button(bottom, text="Nowa runda", command=self.new_round)
        self.new_round_button.pack(side="left", padx=(0, 5))
        self.final_mode_button = ttk.Button(bottom, text="★ Przejdź do finału", command=self.start_final)
        self.final_mode_button.pack(side="left", padx=5)
        ttk.Button(bottom, text="Zapisz pytanie", command=self.save).pack(side="left", padx=5)
        ttk.Button(bottom, text="Wczytaj pytanie", command=self.load).pack(side="left", padx=5)
        ttk.Button(bottom, text="▶ Zagraj intro", command=self.play_intro).pack(side="left", padx=5)
        ttk.Button(bottom, text="Dźwięki WAV…", command=self.configure_sounds).pack(side="left", padx=5)
        ttk.Button(bottom, text="Pokaż tablicę", command=self.show_board).pack(side="right", padx=5)
        ttk.Button(bottom, text="Pełny ekran tablicy (projektor)", command=self.fullscreen_board).pack(side="right", padx=5)

        scores = ttk.LabelFrame(root, text="Wyniki drużyn", padding=7)
        scores.pack(fill="x", pady=(10, 0))
        self.team_scores_frame = scores
        self.score_lock_var = tk.BooleanVar(value=False)
        self.score_lock_button = ttk.Checkbutton(scores, variable=self.score_lock_var,
                                                  command=self.update_score_lock)
        self.score_lock_button.pack(anchor="w", pady=(0, 5))
        score_controls = ttk.Frame(scores)
        score_controls.pack(fill="x")
        self.team_score_vars = {1: tk.StringVar(value="0"), 2: tk.StringVar(value="0")}
        self.team_name_vars = {1: tk.StringVar(value="Drużyna 1"), 2: tk.StringVar(value="Drużyna 2")}
        self.score_edit_widgets: list[tk.Widget] = []
        for team in (1, 2):
            group = ttk.Frame(score_controls)
            group.pack(side="left", expand=True, fill="x", padx=8)
            name = ttk.Entry(group, textvariable=self.team_name_vars[team], width=15, font=("Arial", 10, "bold"))
            name.pack(side="left", padx=(0, 8))
            name.bind("<Return>", lambda _, t=team: self.apply_team_name(t))
            name.bind("<FocusOut>", lambda _, t=team: self.apply_team_name(t))
            minus = ttk.Button(group, text="−1", width=4, command=lambda t=team: self.adjust_team_score(t, -1))
            minus.pack(side="left")
            entry = ttk.Entry(group, textvariable=self.team_score_vars[team], width=7, justify="center", font=("Arial", 12, "bold"))
            entry.pack(side="left", padx=4)
            entry.bind("<Return>", lambda _, t=team: self.apply_team_score(t))
            entry.bind("<FocusOut>", lambda _, t=team: self.apply_team_score(t))
            plus = ttk.Button(group, text="+1", width=4, command=lambda t=team: self.adjust_team_score(t, 1))
            plus.pack(side="left")
            self.score_edit_widgets.extend([minus, entry, plus])
        self.update_score_lock()

        soundbar = ttk.LabelFrame(root, text="Soundbar — efekty", padding=7)
        soundbar.pack(fill="x", pady=(10, 0))
        self.soundbar = soundbar
        sound_files = sorted(SOUNDS_DIR.glob("*.wav"))
        if not sound_files:
            ttk.Label(soundbar, text="Brak plików WAV w assets/sounds").pack(anchor="w")
        for i, path in enumerate(sound_files):
            label = self.sound_label(path)
            ttk.Button(soundbar, text=f"▶ {label}", command=lambda p=path: self.play_sound_file(p)).grid(
                row=i // 3, column=i % 3, padx=3, pady=3, sticky="ew")
            soundbar.columnconfigure(i % 3, weight=1)

    def collect_form(self) -> None:
        answers = []
        old = self.state["answers"]
        question = self.question_var.get().strip()
        question_changed = question != self.state["question"]
        if question_changed:
            self.state["reveal_history"] = []
        for i, (text, points) in enumerate(zip(self.answer_text, self.answer_points)):
            if i >= self.answer_count_var.get():
                break
            try:
                value = max(0, int(points.get() or 0))
            except ValueError:
                value = 0
            answer_text = text.get().strip()
            unchanged = i < len(old) and old[i].get("text") == answer_text
            answers.append({"text": answer_text, "points": value,
                            "shown": bool(old[i].get("shown", False)) if unchanged and not question_changed else False,
                            "points_shown": bool(old[i].get("points_shown", False)) if unchanged and not question_changed else False})
        self.state["question"] = question
        self.state["answers"] = answers
        self.state["answer_count"] = self.answer_count_var.get()

    def set_answer_count(self) -> None:
        try:
            count = min(MAX_ANSWERS, max(MIN_ANSWERS, int(self.answer_count_var.get())))
        except (tk.TclError, ValueError):
            return
        if self.answer_count_var.get() != count:
            self.answer_count_var.set(count)
            return
        for i, row in enumerate(getattr(self, "answer_rows", [])):
            for widget in row:
                (widget.grid if i < count else widget.grid_remove)()
        for i, button in enumerate(getattr(self, "reveal_buttons", [])):
            if i < count:
                button.grid()
            else:
                button.grid_remove()
        for i, button in enumerate(getattr(self, "final_reveal_buttons", [])):
            if i < count:
                button.grid()
            else:
                button.grid_remove()
        for i, button in enumerate(getattr(self, "final_points_buttons", [])):
            if i < count:
                button.grid()
            else:
                button.grid_remove()

    def set_game_mode(self, final_mode: bool) -> None:
        """Przełącza widoczne sterowanie między rundą zwykłą i finałem."""
        self.state["final_mode"] = final_mode
        if final_mode:
            self.round_actions.pack_forget()
            self.team_scores_frame.pack_forget()
            self.answers_header.pack_forget()
            self.answers_table.pack_forget()
            self.final_actions.pack(fill="x", pady=8, before=self.bottom_controls)
            self.final_mode_button.config(text="← Wróć do rundy zasadniczej")
            self.new_round_button.config(state="disabled")
        else:
            self.final_actions.pack_forget()
            # round_actions również było ukryte w finale, więc nie może być
            # kotwicą parametru „before”. Wszystko wstawiamy przed stały dół.
            self.answers_header.pack(fill="x", before=self.bottom_controls)
            self.answers_table.pack(fill="x", pady=(4, 8), before=self.bottom_controls)
            self.round_actions.pack(fill="x", pady=8, before=self.bottom_controls)
            self.team_scores_frame.pack(fill="x", pady=(10, 0), before=self.soundbar)
            self.final_mode_button.config(text="★ Przejdź do finału")
            self.new_round_button.config(state="normal")
        self.update_final_status()

    def update_final_status(self) -> None:
        if not hasattr(self, "final_status"):
            return
        player = self.state.get("final_active_player", 1)
        time_limit = 15 if player == 1 else 20
        imported = len(self.state.get("final_questions", []))
        phase = "ODPOWIEDZI" if self.state.get("final_phase", "collect1").startswith("collect") else "ODSŁANIANIE"
        self.final_status.set(
            f"FINAŁ ({phase}) — zawodnik {player}, pytanie {self.state.get('final_question_number', 1)} / {imported or 5} "
            f"• czas: {time_limit} s • wynik: {self.state.get(f'final_score{player}', 0)}"
        )

    def start_final(self) -> None:
        if self.state.get("final_mode"):
            self.stop_final_timer()
            self.state["final_summary"] = False
            if self._round_before_final is not None:
                self.state.update(deepcopy(self._round_before_final))
            else:
                # Po wczytaniu zapisu już będącego w finale nie ma poprzedniej
                # rundy do odzyskania; wracamy wtedy do pustej rundy zwykłej.
                self.state.update({"question": "", "answers": [], "answer_count": MIN_ANSWERS,
                                   "round_points": 0, "strikes": 0, "reveal_history": []})
            self._round_before_final = None
            self.set_game_mode(False)
            self.sync_round_form()
            self.refresh()
            return
        if not messagebox.askyesno("Runda finałowa", "Rozpocząć finał? Wyniki drużyn zostaną zachowane."):
            return
        self.collect_form()
        self._round_before_final = deepcopy({
            key: self.state[key] for key in ("question", "answers", "answer_count", "round_points", "strikes", "reveal_history")
        })
        self.state.update({"final_mode": True, "final_active_player": 1, "final_question_number": 1,
                           "final_score1": 0, "final_score2": 0, "final_timer": 0, "final_summary": False,
                           "final_questions": [], "final_question_index": 0, "final_progress": {}, "final_responses": {},
                           "final_phase": "collect1"})
        self.clear_final_question(advance=False)
        self.set_game_mode(True)
        self.refresh()

    def sync_round_form(self) -> None:
        """Wpisuje do panelu zwykłą rundę przywróconą po finale."""
        count = min(MAX_ANSWERS, max(MIN_ANSWERS, int(self.state.get("answer_count", MIN_ANSWERS))))
        self.answer_count_var.set(count)
        self.question_var.set(self.state.get("question", ""))
        for i, (text, points) in enumerate(zip(self.answer_text, self.answer_points)):
            answer = self.state.get("answers", [])[i] if i < len(self.state.get("answers", [])) else {"text": "", "points": 0}
            text.set(answer.get("text", ""))
            points.set(str(answer.get("points", 0)))
        self.set_answer_count()

    def select_final_player(self, player: int) -> None:
        self.stop_final_timer()
        self.state["final_active_player"] = player
        self.state["final_phase"] = f"collect{player}"
        self.state["final_summary"] = False
        self.load_final_question(0)

    def clear_final_question(self, advance: bool = True) -> None:
        """Czyści ręcznie wpisywane pytanie, gdy zestaw finałowy nie jest zaimportowany."""
        self.stop_final_timer()
        if advance:
            self.state["final_question_number"] = min(5, self.state["final_question_number"] + 1)
        self.state.update({"question": "", "answers": [], "round_points": 0, "strikes": 0,
                           "reveal_history": [], "final_timer": 0, "final_summary": False})
        self.question_var.set("")
        self.answer_count_var.set(MIN_ANSWERS)
        for text, points in zip(self.answer_text, self.answer_points):
            text.set("")
            points.set("0")
        self.update_final_status()
        self.refresh()

    def award_final_question(self) -> None:
        self.collect_form()
        self.save_final_progress()
        player = self.state["final_active_player"]
        key = self.final_progress_key()
        progress = self.state["final_progress"].setdefault(key, {})
        if progress.get("awarded"):
            return
        self.state[f"final_score{player}"] += self.state["round_points"]
        progress["awarded"] = True
        self.state["round_points"] = 0
        if self.state[f"final_score{player}"] >= self.state["final_target"]:
            Sound.play("win", self.state["sound_files"].get("win", ""))
        if self.state.get("final_questions") and self.state["final_question_index"] < 4:
            self.load_final_question(self.state["final_question_index"] + 1)
        elif not self.state.get("final_questions") and self.state["final_question_number"] < 5:
            self.clear_final_question(advance=True)
        else:
            self.stop_final_timer()
            self.update_final_status()
            self.refresh()

    def final_progress_key(self, player: int | None = None, question_index: int | None = None) -> str:
        player = player or self.state["final_active_player"]
        question_index = self.state.get("final_question_index", 0) if question_index is None else question_index
        return f"{player}:{question_index}"

    def save_final_progress(self) -> None:
        if not self.state.get("final_mode") or not self.state.get("final_questions"):
            return
        key = self.final_progress_key()
        old = self.state["final_progress"].get(key, {})
        self.state["final_progress"][key] = {
            "shown": [i for i, answer in enumerate(self.state["answers"]) if answer.get("shown")],
            "points_shown": [i for i, answer in enumerate(self.state["answers"]) if answer.get("points_shown")],
            "round_points": self.state["round_points"], "awarded": old.get("awarded", False),
        }

    def load_final_question(self, index: int) -> None:
        questions = self.state.get("final_questions", [])
        if not questions:
            self.clear_final_question(advance=False)
            return
        self.stop_final_timer()
        index = min(max(0, index), len(questions) - 1)
        self.state["final_question_index"] = index
        self.state["final_question_number"] = index + 1
        source = questions[index]
        response = self.state.setdefault("final_responses", {}).get(self.final_progress_key(question_index=index), {})
        self.state.update({
            "question": source["question"],
            "answers": [], "round_points": 0, "strikes": 0, "reveal_history": [],
            "final_timer": 0, "final_summary": False,
        })
        self.question_var.set(self.state["question"])
        for player in (1, 2):
            player_response = self.state.setdefault("final_responses", {}).get(self.final_progress_key(player=player, question_index=index), {})
            self.final_choice_vars[player].set(str(player_response["answer_index"] + 1) if "answer_index" in player_response else "")
            self.final_points_vars[player].set(str(player_response["points"]) if player_response.get("answer") else "—")
            self.final_selection_labels[player].config(text=player_response.get("answer", "—"))
        for i, label in enumerate(self.final_option_labels):
            if i < len(source["answers"]):
                answer = source["answers"][i]
                label.config(text=f"{i + 1}. {answer['text']} — {answer['points']} pkt")
                label.grid()
            else:
                label.grid_remove()
        self.update_final_status()
        self.refresh()

    def navigate_final_question(self, direction: int) -> None:
        if not self.state.get("final_questions"):
            messagebox.showinfo("Finał", "Najpierw zaimportuj plik z 5 pytaniami finałowymi.")
            return
        if self.state.get("final_phase", "collect1").startswith("collect") and not self.save_final_response():
            return
        self.load_final_question(self.state["final_question_index"] + direction)

    def current_final_response(self) -> dict:
        key = self.final_progress_key()
        return self.state.setdefault("final_responses", {}).setdefault(
            key, {"answer": "", "answer_index": None, "points": 0, "answer_shown": False, "points_shown": False}
        )

    @staticmethod
    def normalize_answer(value: str) -> str:
        return " ".join(value.casefold().split())

    def save_final_response(self, player: int | None = None) -> bool:
        if not self.state.get("final_questions"):
            messagebox.showinfo("Finał", "Najpierw zaimportuj plik z 5 pytaniami finałowymi.")
            return False
        player = player or self.state["final_active_player"]
        self.state["final_active_player"] = player
        self.state["final_phase"] = f"collect{player}"
        response = self.current_final_response()
        question_index = self.state["final_question_index"]
        source = self.state["final_questions"][question_index]
        raw_choice = self.final_choice_vars[player].get().strip()
        try:
            # Puste pole ma ten sam sens co „0”: zawodnik nie podał odpowiedzi.
            answer_index = -1 if not raw_choice else int(raw_choice) - 1
        except ValueError:
            messagebox.showwarning("Numer odpowiedzi", "Wpisz numer odpowiedzi widoczny na liście.")
            return False
        if answer_index == -1:
            response.update({"answer": "BRAK ODPOWIEDZI", "answer_index": -1, "points": 0,
                             "answer_shown": False, "points_shown": False})
            self.final_points_vars[player].set("0")
            self.final_selection_labels[player].config(text="BRAK ODPOWIEDZI")
            return True
        if not 0 <= answer_index < len(source["answers"]):
            messagebox.showwarning("Numer odpowiedzi", "Wybierz numer istniejącej odpowiedzi dla tego pytania.")
            return False
        selected = source["answers"][answer_index]
        answer = selected["text"]
        if player == 2:
            first = self.state["final_responses"].get(self.final_progress_key(player=1, question_index=question_index), {})
            if answer_index >= 0 and first.get("answer_index") == answer_index:
                Sound.play("repeat", self.state["sound_files"].get("repeat", ""))
                messagebox.showwarning("Powtórzona odpowiedź", "Drugi zawodnik podał tę samą odpowiedź. Musi podać inną.")
                return False
        response.update({"answer": answer, "answer_index": answer_index, "points": selected["points"],
                         "answer_shown": False, "points_shown": False})
        self.final_points_vars[player].set(str(response["points"]))
        self.final_selection_labels[player].config(text=answer)
        self.update_final_status()
        return True

    def finish_final_collection(self) -> None:
        if not self.save_final_response():
            return
        self.stop_final_timer()
        player = self.state["final_active_player"]
        self.state["final_phase"] = f"reveal{player}"
        self.load_final_question(0)

    def reveal_final_answer(self, player: int | None = None) -> None:
        player = player or self.state["final_active_player"]
        self.state["final_active_player"] = player
        self.state["final_phase"] = f"reveal{player}"
        response = self.current_final_response()
        if not response.get("answer"):
            return
        response["answer_shown"] = True
        Sound.play("reveal", self.state["sound_files"].get("reveal", ""))
        self.refresh()

    def reveal_final_score(self, player: int | None = None) -> None:
        player = player or self.state["final_active_player"]
        self.state["final_active_player"] = player
        self.state["final_phase"] = f"reveal{player}"
        response = self.current_final_response()
        if not response.get("answer_shown") or response.get("points_shown"):
            return
        response["points_shown"] = True
        self.state[f"final_score{player}"] += response["points"]
        Sound.play("bells", self.state["sound_files"].get("bells", ""))
        if self.state["final_score1"] + self.state["final_score2"] >= self.state["final_target"]:
            Sound.play("win", self.state["sound_files"].get("win", ""))
        self.refresh()

    def clear_final_response(self, player: int | None = None) -> None:
        player = player or self.state["final_active_player"]
        self.state["final_active_player"] = player
        response = self.current_final_response()
        if response.get("points_shown"):
            self.state[f"final_score{player}"] = max(0, self.state[f"final_score{player}"] - response["points"])
        key = self.final_progress_key()
        self.state["final_responses"].pop(key, None)
        self.final_choice_vars[player].set("")
        self.final_points_vars[player].set("—")
        self.final_selection_labels[player].config(text="—")
        self.refresh()

    def show_final_summary(self) -> None:
        self.stop_final_timer()
        self.state["final_summary"] = True
        self.refresh()

    def stop_final_timer(self) -> None:
        if self._final_timer_after:
            self.after_cancel(self._final_timer_after)
            self._final_timer_after = None

    def start_final_timer(self) -> None:
        self.stop_final_timer()
        self.state["final_timer"] = 15 if self.state["final_active_player"] == 1 else 20
        self._tick_final_timer()

    def start_player_timer(self, player: int) -> None:
        self.state["final_active_player"] = player
        self.state["final_phase"] = f"collect{player}"
        self.state["final_summary"] = False
        self.update_final_status()
        self.start_final_timer()

    def _tick_final_timer(self) -> None:
        self.refresh()
        if self.state["final_timer"] <= 0:
            Sound.play("final_time", self.state["sound_files"].get("final_time", ""))
            self._final_timer_after = None
            return
        self.state["final_timer"] -= 1
        self._final_timer_after = self.after(1000, self._tick_final_timer)

    def refresh(self) -> None:
        self.board.refresh()

    def apply_team_score(self, team: int) -> None:
        """Wpisany ręcznie wynik trafia natychmiast na tablicę."""
        try:
            score = max(0, int(self.team_score_vars[team].get()))
        except ValueError:
            self.team_score_vars[team].set(str(self.state[f"team{team}"]))
            return
        self.state[f"team{team}"] = score
        self.team_score_vars[team].set(str(score))
        self.refresh()

    def apply_team_name(self, team: int) -> None:
        name = self.team_name_vars[team].get().strip() or f"Drużyna {team}"
        self.state[f"team{team}_name"] = name
        self.team_name_vars[team].set(name)
        self.refresh()

    def update_score_lock(self) -> None:
        unlocked = self.score_lock_var.get()
        self.state["scores_unlocked"] = unlocked
        self.score_lock_button.config(
            text="Edycja punktów odblokowana" if unlocked else "Odblokuj edycję punktów"
        )
        for widget in getattr(self, "score_edit_widgets", []):
            widget.config(state="normal" if unlocked else "disabled")

    def adjust_team_score(self, team: int, delta: int) -> None:
        self.apply_team_score(team)
        score = max(0, self.state[f"team{team}"] + delta)
        self.state[f"team{team}"] = score
        self.team_score_vars[team].set(str(score))
        self.refresh()

    def sync_team_score_fields(self) -> None:
        for team in (1, 2):
            self.team_score_vars[team].set(str(self.state[f"team{team}"]))

    def sync_team_name_fields(self) -> None:
        for team in (1, 2):
            self.team_name_vars[team].set(self.state[f"team{team}_name"])

    def reveal(self, index: int) -> None:
        self.collect_form()
        if index >= len(self.state["answers"]):
            return
        answer = self.state["answers"][index]
        if not answer["shown"]:
            answer["shown"] = True
            if self.state.get("final_mode"):
                self.state["reveal_history"].append(["answer", index])
            else:
                self.state["round_points"] += answer["points"]
                self.state["reveal_history"].append(["answer", index])
            Sound.play("reveal", self.state["sound_files"].get("reveal", ""))
        self.save_final_progress()
        self.refresh()

    def reveal_final_points(self, index: int) -> None:
        """W finale odkrywa punktację odpowiedzi wraz z dźwiękiem dzwoneczków."""
        if not self.state.get("final_mode"):
            return
        self.collect_form()
        if index >= len(self.state["answers"]):
            return
        answer = self.state["answers"][index]
        if answer.get("shown") and not answer.get("points_shown", False):
            answer["points_shown"] = True
            self.state["round_points"] += answer["points"]
            self.state["reveal_history"].append(["points", index])
            Sound.play("bells", self.state["sound_files"].get("bells", ""))
        self.save_final_progress()
        self.refresh()

    def undo_reveal(self) -> None:
        """Cofa ostatnią faktycznie odkrytą odpowiedź i jej punkty."""
        self.collect_form()
        history = self.state.setdefault("reveal_history", [])
        while history:
            item = history.pop()
            action, index = item if isinstance(item, list) else ("answer", item)
            if index < len(self.state["answers"]) and self.state["answers"][index].get("shown"):
                answer = self.state["answers"][index]
                if action == "points" and answer.get("points_shown"):
                    answer["points_shown"] = False
                    self.state["round_points"] = max(0, self.state["round_points"] - answer["points"])
                else:
                    if answer.get("points_shown"):
                        self.state["round_points"] = max(0, self.state["round_points"] - answer["points"])
                    answer["shown"] = False
                    answer["points_shown"] = False
                break
        self.save_final_progress()
        self.refresh()

    def strike(self) -> None:
        self.collect_form()
        self.state["strikes"] = min(3, self.state["strikes"] + 1)
        Sound.play("strike", self.state["sound_files"].get("strike", ""))
        self.refresh()

    def clear_strikes(self) -> None:
        self.state["strikes"] = 0
        self.refresh()

    def award(self, team: int) -> None:
        self.collect_form()
        self.state[f"team{team}"] += self.state["round_points"]
        self.sync_team_score_fields()
        self.state["round_points"] = 0
        self.state["strikes"] = 0
        Sound.play("win", self.state["sound_files"].get("win", ""))
        self.refresh()

    def new_round(self) -> None:
        if not messagebox.askyesno("Nowa runda", "Wyczyścić pytanie i odpowiedzi? Wyniki drużyn zostaną."):
            return
        team1, team2 = self.state["team1"], self.state["team2"]
        team1_name, team2_name = self.state["team1_name"], self.state["team2_name"]
        self.state = self.default_state() | {"team1": team1, "team2": team2,
                                              "team1_name": team1_name, "team2_name": team2_name}
        self.score_lock_var.set(False)
        self.update_score_lock()
        self.sync_team_score_fields()
        self.sync_team_name_fields()
        self.answer_count_var.set(MIN_ANSWERS)
        self.question_var.set("")
        for text, points in zip(self.answer_text, self.answer_points):
            text.set("")
            points.set("0")
        self.refresh()

    def save(self) -> None:
        self.collect_form()
        path = filedialog.asksaveasfilename(initialdir=APP_DIR, initialfile="pytania.json", defaultextension=".json", filetypes=[("Plik pytań", "*.json")])
        if path:
            Path(path).write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_silent(self) -> None:
        if SAVE_FILE.exists():
            try:
                self.load_from(SAVE_FILE)
            except (OSError, json.JSONDecodeError, KeyError):
                pass

    def load(self) -> None:
        path = filedialog.askopenfilename(initialdir=APP_DIR / "questions",
                                          filetypes=[("Pytanie tekstowe", "*.txt"), ("Plik gry", "*.json")])
        if path:
            try:
                self.load_from(Path(path))
            except (OSError, json.JSONDecodeError, KeyError) as error:
                messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{error}")

    def load_from(self, path: Path) -> None:
        is_text_question = path.suffix.lower() == ".txt"
        data = self.read_question_text(path) if is_text_question else json.loads(path.read_text(encoding="utf-8"))
        # TXT zawiera wyłącznie pytanie; nie może resetować trybu finału ani wyników gry.
        self.state = (self.state | data) if is_text_question else (self.default_state() | data)
        self.state["sound_files"] = self.default_state()["sound_files"] | self.state.get("sound_files", {})
        # Po wczytaniu rozgrywki ręczna edycja zawsze zaczyna z blokadą.
        self.score_lock_var.set(False)
        self.update_score_lock()
        self.sync_team_score_fields()
        self.sync_team_name_fields()
        self.answer_count_var.set(min(MAX_ANSWERS, max(MIN_ANSWERS, self.state.get("answer_count", MAX_ANSWERS))))
        self.question_var.set(self.state["question"])
        for i, (text, points) in enumerate(zip(self.answer_text, self.answer_points)):
            answer = self.state["answers"][i] if i < len(self.state["answers"]) else {"text": "", "points": 0}
            text.set(answer["text"])
            points.set(str(answer["points"]))
        self.set_game_mode(bool(self.state.get("final_mode", False)))
        self.refresh()

    @staticmethod
    def read_question_text(path: Path) -> dict:
        """Czyta prosty format: PYTANIE: ... oraz 1. ODPOWIEDŹ — 10 pkt."""
        question = ""
        answers = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.upper().startswith("PYTANIE:"):
                question = line.split(":", 1)[1].strip()
                continue
            if line[0].isdigit() and "." in line:
                try:
                    _, content = line.split(".", 1)
                    text, score = content.rsplit("—", 1)
                    points = int(score.lower().replace("pkt", "").strip())
                    answers.append({"text": text.strip(), "points": points, "shown": False})
                except (ValueError, IndexError):
                    continue
        if not question or not MIN_ANSWERS <= len(answers) <= MAX_ANSWERS:
            raise ValueError(f"Plik TXT musi zawierać pytanie i od {MIN_ANSWERS} do {MAX_ANSWERS} poprawnych odpowiedzi.")
        return {"question": question, "answers": answers, "answer_count": len(answers)}

    @staticmethod
    def read_final_questions(path: Path) -> list[dict]:
        """Czyta pięć pytań finałowych z listami odpowiedzi i punktów."""
        questions: list[dict] = []
        current: dict | None = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.upper().startswith("PYTANIE") and ":" in line:
                if current:
                    questions.append(current)
                current = {"question": line.split(":", 1)[1].strip(), "answers": []}
                continue
            if current and line[0].isdigit() and "." in line:
                try:
                    _, content = line.split(".", 1)
                    text, score = content.rsplit("—", 1)
                    current["answers"].append({"text": text.strip(), "points": int(score.lower().replace("pkt", "").strip())})
                except (ValueError, IndexError):
                    continue
        if current:
            questions.append(current)
        valid = len(questions) == 5 and all(question["question"] and MIN_ANSWERS <= len(question["answers"]) <= MAX_ANSWERS for question in questions)
        if not valid:
            raise ValueError("Plik finału musi zawierać 5 pytań, po 4–6 odpowiedzi z punktami każde.")
        return questions

    def import_final_questions(self) -> None:
        paths = filedialog.askopenfilenames(parent=self, initialdir=APP_DIR / "questions",
                                             filetypes=[("Pytania tekstowe", "*.txt")])
        if not paths:
            return
        if len(paths) != 5:
            messagebox.showerror("Błąd importu finału", "Wybierz dokładnie 5 plików TXT z pytaniami rund zasadniczych.")
            return
        try:
            questions = [self.read_question_text(Path(path)) for path in paths]
        except (OSError, ValueError) as error:
            messagebox.showerror("Błąd importu finału", str(error))
            return
        self.stop_final_timer()
        self.state.update({"final_questions": questions, "final_question_index": 0, "final_question_number": 1,
                           "final_progress": {}, "final_score1": 0, "final_score2": 0, "final_summary": False,
                           "final_active_player": 1, "final_responses": {}, "final_phase": "collect1"})
        self.load_final_question(0)

    def play_intro(self) -> None:
        Sound.play("intro", self.state["sound_files"].get("intro", ""))

    @staticmethod
    def sound_label(path: Path) -> str:
        labels = {
            "blad": "Błąd", "dobra-odpowiedz": "Dobra odpowiedź", "intro-familiada": "Intro",
            "czas-final-familiada": "Czas finału", "dzwoneczki-familiada": "Dzwoneczki",
            "po-1-rundzie-finalu-familiada": "Po 1. rundzie finału",
            "powtorzenie-w-finale-familiada": "Powtórzenie w finale",
            "przed-finalem-familiada": "Przed finałem",
            "przed-i-po-rundzie-familiada": "Przed / po rundzie",
        }
        return labels.get(path.stem, path.stem.replace("-", " ").title())

    @staticmethod
    def play_sound_file(path: Path) -> None:
        Sound.play("custom", str(path))

    def show_board(self) -> None:
        self.collect_form()
        self.refresh()
        self.board.deiconify()
        self.board.lift()

    def fullscreen_board(self) -> None:
        self.show_board()
        projector = self.projector_geometry()
        if projector:
            self.board.projector_fullscreen(*projector)
        else:
            # Zapasowe zachowanie dla pojedynczego monitora lub systemu innego
            # niż Windows.
            self.board.attributes("-fullscreen", True)

    def projector_geometry(self) -> tuple[int, int, int, int] | None:
        """Zwraca granice pierwszego monitora innego niż główny (Windows)."""
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                           ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

            displays: list[tuple[int, int, int, int]] = []
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p,
                                                ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

            def collect(monitor: int, _dc: int, _rect: object, _data: int) -> bool:
                info = MonitorInfo()
                info.cbSize = ctypes.sizeof(info)
                if ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)) and not (info.dwFlags & 1):
                    rect = info.rcMonitor
                    displays.append((rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top))
                return True

            ctypes.windll.user32.EnumDisplayMonitors(0, 0, callback_type(collect), 0)
            if not displays:
                return None
            return displays[0]
        except Exception:
            return None

    def configure_sounds(self) -> None:
        """Pozwala podpiąć własne/licencjonowane efekty bez pakowania ich z aplikacją."""
        dialog = tk.Toplevel(self)
        dialog.title("Dźwięki (WAV)")
        dialog.transient(self)
        dialog.resizable(False, False)
        ttk.Label(dialog, text="Wybierz własne WAV.", padding=(14, 12, 14, 4)).grid(row=0, column=0, columnspan=3, sticky="w")
        labels = {"intro": "Intro", "reveal": "Odkrycie odpowiedzi", "strike": "Błąd", "win": "Wygrana runda"}
        paths = self.state["sound_files"]
        for row, (kind, label) in enumerate(labels.items(), 1):
            value = tk.StringVar(value=paths.get(kind, ""))
            ttk.Label(dialog, text=label).grid(row=row, column=0, padx=(14, 8), pady=5, sticky="w")
            ttk.Entry(dialog, textvariable=value, width=48).grid(row=row, column=1, pady=5)
            def choose(k: str = kind, v: tk.StringVar = value) -> None:
                path = filedialog.askopenfilename(parent=dialog, filetypes=[("Dźwięk WAV", "*.wav")])
                if path:
                    paths[k] = path
                    v.set(path)
            ttk.Button(dialog, text="Wybierz…", command=choose).grid(row=row, column=2, padx=(6, 14), pady=5)
        ttk.Label(dialog, text="Puste pola używają wbudowanych sygnałów.", padding=(14, 5, 14, 12)).grid(row=5, column=0, columnspan=3, sticky="w")


if __name__ == "__main__":
    HostApp().mainloop()
