"""Prosta, lokalna tablica do weselnej gry w stylu Familiady.

Uruchom: python familiada.py
Tablica otwiera się w drugim oknie — przeciągnij je na telewizor/projektor
i wciśnij F11 (albo przycisk „Pełny ekran”).
"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
SAVE_FILE = APP_DIR / "pytania.json"
SOUNDS_DIR = APP_DIR / "assets" / "sounds"
MIN_ANSWERS = 4
MAX_ANSWERS = 6
DEFAULT_SOUNDS = {
    "intro": str(SOUNDS_DIR / "intro-familiada.wav"),
    "reveal": str(SOUNDS_DIR / "dobra-odpowiedz.wav"),
    "strike": str(SOUNDS_DIR / "blad.wav"),
    "win": str(SOUNDS_DIR / "przed-i-po-rundzie-familiada.wav"),
    "final_time": str(SOUNDS_DIR / "czas-final-familiada.wav"),
}


class Sound:
    """Krótkie, autorskie sygnały; nie wymaga plików audio ani Internetu."""

    @staticmethod
    def play(kind: str, file_path: str = "") -> None:
        try:
            import winsound
            if file_path and Path(file_path).suffix.lower() == ".wav":
                winsound.PlaySound(file_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
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
        self.bind("<F11>", lambda _: self.toggle_fullscreen())
        self.bind("<Escape>", lambda _: self.attributes("-fullscreen", False))
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.canvas = tk.Canvas(self, bg="#121d55", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw())

    def toggle_fullscreen(self) -> None:
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

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
        # Subtelna siatka obudowy LED.
        cell = max(9, int(min(bw/52, bh/25)))
        for x in range(int(bx)+4, int(bx+bw), cell):
            c.create_line(x, by, x, by+bh, fill="#18222b")
        for y in range(int(by)+4, int(by+bh), cell):
            c.create_line(bx, y, bx+bw, y, fill="#18222b")

        state = self.app.state
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
            points = str(answer["points"]) if answer["shown"] else ""
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
                "final_score2": 0, "final_target": 200, "final_timer": 0}

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
        ttk.Label(answers_header, text="ODPOWIEDZI I PUNKTY", font=("Arial", 11, "bold")).pack(side="left")
        ttk.Label(answers_header, text="Liczba odpowiedzi:").pack(side="left", padx=(20, 4))
        self.answer_count_var = tk.IntVar(value=MIN_ANSWERS)
        ttk.Spinbox(answers_header, from_=MIN_ANSWERS, to=MAX_ANSWERS, width=3,
                    textvariable=self.answer_count_var, command=self.set_answer_count).pack(side="left")
        self.answer_count_var.trace_add("write", lambda *_: self.set_answer_count())
        table = ttk.Frame(root)
        table.pack(fill="x", pady=(4, 8))
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
        ttk.Button(self.final_actions, text="Zawodnik 1 (15 s)", command=lambda: self.select_final_player(1)).grid(row=1, column=0, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="Zawodnik 2 (20 s)", command=lambda: self.select_final_player(2)).grid(row=1, column=1, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="▶ Start czasu", command=self.start_final_timer).grid(row=1, column=2, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="↶ Cofnij odkrycie", command=self.undo_reveal).grid(row=1, column=3, padx=3, pady=3, sticky="ew")
        self.final_reveal_buttons: list[ttk.Button] = []
        for i in range(MAX_ANSWERS):
            button = ttk.Button(self.final_actions, text=f"Odkryj {i + 1}", command=lambda n=i: self.reveal(n))
            button.grid(row=2 if i < 4 else 3, column=i % 4, padx=3, pady=3, sticky="ew")
            self.final_reveal_buttons.append(button)
        ttk.Button(self.final_actions, text="Dodaj punkty pytania", command=self.award_final_question).grid(row=4, column=0, columnspan=2, padx=3, pady=3, sticky="ew")
        ttk.Button(self.final_actions, text="Nowe pytanie finałowe", command=self.clear_final_question).grid(row=4, column=2, columnspan=2, padx=3, pady=3, sticky="ew")
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
        ttk.Button(bottom, text="Pełny ekran tablicy", command=self.fullscreen_board).pack(side="right", padx=5)

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
                            "shown": bool(old[i].get("shown", False)) if unchanged and not question_changed else False})
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

    def set_game_mode(self, final_mode: bool) -> None:
        """Przełącza widoczne sterowanie między rundą zwykłą i finałem."""
        self.state["final_mode"] = final_mode
        if final_mode:
            self.round_actions.pack_forget()
            self.team_scores_frame.pack_forget()
            self.final_actions.pack(fill="x", pady=8, before=self.bottom_controls)
            self.final_mode_button.config(text="← Wróć do rundy zasadniczej")
            self.new_round_button.config(state="disabled")
        else:
            self.final_actions.pack_forget()
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
        self.final_status.set(
            f"FINAŁ — zawodnik {player}, pytanie {self.state.get('final_question_number', 1)} / 5 "
            f"• czas: {time_limit} s • wynik: {self.state.get(f'final_score{player}', 0)}"
        )

    def start_final(self) -> None:
        if self.state.get("final_mode"):
            self.stop_final_timer()
            self.set_game_mode(False)
            self.refresh()
            return
        if not messagebox.askyesno("Runda finałowa", "Rozpocząć finał? Wyniki drużyn zostaną zachowane."):
            return
        self.state.update({"final_mode": True, "final_active_player": 1, "final_question_number": 1,
                           "final_score1": 0, "final_score2": 0, "final_timer": 0})
        self.clear_final_question(advance=False)
        self.set_game_mode(True)
        self.refresh()

    def select_final_player(self, player: int) -> None:
        self.stop_final_timer()
        self.state["final_active_player"] = player
        self.update_final_status()
        self.refresh()

    def clear_final_question(self, advance: bool = True) -> None:
        self.stop_final_timer()
        if advance:
            self.state["final_question_number"] = min(5, self.state["final_question_number"] + 1)
        self.state.update({"question": "", "answers": [], "round_points": 0, "strikes": 0,
                           "reveal_history": [], "final_timer": 0})
        self.question_var.set("")
        self.answer_count_var.set(MIN_ANSWERS)
        for text, points in zip(self.answer_text, self.answer_points):
            text.set("")
            points.set("0")
        self.update_final_status()
        self.refresh()

    def award_final_question(self) -> None:
        self.collect_form()
        player = self.state["final_active_player"]
        self.state[f"final_score{player}"] += self.state["round_points"]
        self.state["round_points"] = 0
        if self.state[f"final_score{player}"] >= self.state["final_target"]:
            Sound.play("win", self.state["sound_files"].get("win", ""))
        if self.state["final_question_number"] < 5:
            self.clear_final_question(advance=True)
        else:
            self.stop_final_timer()
            self.update_final_status()
            self.refresh()

    def stop_final_timer(self) -> None:
        if self._final_timer_after:
            self.after_cancel(self._final_timer_after)
            self._final_timer_after = None

    def start_final_timer(self) -> None:
        self.stop_final_timer()
        self.state["final_timer"] = 15 if self.state["final_active_player"] == 1 else 20
        self._tick_final_timer()

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
            text="🔓 Edycja punktów odblokowana" if unlocked else "Odblokuj edycję punktów"
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
            self.state["round_points"] += answer["points"]
            self.state["reveal_history"].append(index)
            Sound.play("reveal", self.state["sound_files"].get("reveal", ""))
        self.refresh()

    def undo_reveal(self) -> None:
        """Cofa ostatnią faktycznie odkrytą odpowiedź i jej punkty."""
        self.collect_form()
        history = self.state.setdefault("reveal_history", [])
        while history:
            index = history.pop()
            if index < len(self.state["answers"]) and self.state["answers"][index].get("shown"):
                answer = self.state["answers"][index]
                answer["shown"] = False
                self.state["round_points"] = max(0, self.state["round_points"] - answer["points"])
                break
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
        self.board.attributes("-fullscreen", True)

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
