import json
import os
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def today_str():
    return datetime.date.today().isoformat()


# -------------------------
# Event definitions by row type
# -------------------------

EVENTS_BY_TYPE = {
    "RUCKS": [
        ("commit_1", "Atk commit 1"),
        ("commit_2", "Atk commit 2"),
        ("commit_3plus", "Atk commit 3+"),
        # Opposition rucks: whether WE contest the ball
        ("opp_uncontested", "Uncontested"),
        ("opp_contest_1", "Contest 1"),
        ("opp_contest_2", "Contest 2"),
        ("own_ruck_lost", "Ruck lost"),
        ("turnover_won", "Turnover won"),
    ],
    "LINEOUTS": [
        ("own_won", "Own won"),
        ("own_lost", "Own lost"),
        ("opp_won", "Opp won"),
        ("opp_lost", "Opp lost"),
    ],
    "SCRUMS": [
        ("own_won", "Own won"),
        ("own_lost", "Own lost"),
        ("opp_won", "Opp won"),
        ("opp_lost", "Opp lost"),
    ],
    "PENALTIES": [
        ("pen_ruck", "At ruck"),
        ("pen_high_tackle", "High tackle"),
        ("pen_scrum", "At scrum"),
        ("pen_not_releasing", "Not releasing"),
        ("pen_not_rolling", "Not rolling"),
        ("pen_other", "Other"),
    ],
    "PLAYER": [
        ("carry_pos", "Carry +"),
        ("carry_neg", "Carry -"),
        ("pass", "Pass"),
        ("ground_pass", "Ground pass"),
        ("offload", "Offload"),
        ("tackle_made", "Tkl made"),
        ("tackle_missed", "Tkl missed"),
        ("tackle_assist", "Tkl assist"),
        ("handling_error", "Handling err"),
        ("dropped_pass", "Dropped pass"),
    ],
}


def default_rows():
    """Stable internal IDs + editable display names."""
    rows = [
        {"id": "RUCKS", "type": "RUCKS", "name": "Rucks"},
        {"id": "LINEOUTS", "type": "LINEOUTS", "name": "Lineouts"},
        {"id": "SCRUMS", "type": "SCRUMS", "name": "Scrums"},
        {"id": "PENALTIES", "type": "PENALTIES", "name": "Penalties"},
    ]
    for i in range(1, 24):
        rows.append({"id": f"P{i:02d}", "type": "PLAYER", "name": f"Player {i}"})
    return rows


AGGREGATE_IDS = {"RUCKS", "LINEOUTS", "SCRUMS", "PENALTIES"}


# -------------------------
# Scrollable frame
# -------------------------

class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)      # Windows
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)  # Linux down

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


# -------------------------
# App
# -------------------------

class RugbyReviewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rugby Video Review Tagger")
        self.geometry("1400x780")

        self.current_file = None

        self.rows = default_rows()  # list of dicts: {id,type,name}

        # counts[row_id][event_key] = int
        self.counts = {
            r["id"]: {ek: 0 for ek, _ in EVENTS_BY_TYPE[r["type"]]}
            for r in self.rows
        }

        # per-row undo stack: list of event_keys
        self.undo_stack = {r["id"]: [] for r in self.rows}

        # UI refs
        self.row_widgets = {}   # row_id -> {event_key: button}
        self.row_namevars = {}  # row_id -> StringVar

        self._build_menu()
        self._build_header()
        self._build_rows()

    # ---------------- UI ----------------

    def _build_menu(self):
        menubar = tk.Menu(self)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.new_session)
        filemenu.add_command(label="Open…", command=self.open_session)
        filemenu.add_command(label="Save", command=self.save_session)
        filemenu.add_command(label="Save As…", command=self.save_session_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=filemenu)

        reportmenu = tk.Menu(menubar, tearoff=0)
        reportmenu.add_command(label="Generate Report…", command=self.generate_report)
        menubar.add_cascade(label="Report", menu=reportmenu)

        self.config(menu=menubar)

    def _build_header(self):
        header = ttk.Frame(self, padding=10)
        header.pack(side="top", fill="x")

        ttk.Label(header, text="Match:").pack(side="left")
        self.match_var = tk.StringVar(value=f"Match {today_str()}")
        ttk.Entry(header, textvariable=self.match_var, width=32).pack(side="left", padx=(5, 15))

        ttk.Label(header, text="Opponent:").pack(side="left")
        self.opp_var = tk.StringVar(value="")
        ttk.Entry(header, textvariable=self.opp_var, width=26).pack(side="left", padx=(5, 15))

        ttk.Button(header, text="Generate report…", command=self.generate_report).pack(side="left", padx=5)
        ttk.Button(header, text="Save", command=self.save_session).pack(side="left", padx=5)

        ttk.Label(header, text="Names are saved. Buttons won’t break on rename.").pack(side="right")

    def _build_rows(self):
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)

        head = ttk.Frame(container, padding=(10, 6))
        head.pack(side="top", fill="x")
        ttk.Label(head, text="Row", width=22).pack(side="left")
        ttk.Label(head, text="Buttons (+1 per click)", width=90).pack(side="left")
        ttk.Label(head, text="Undo", width=6).pack(side="right")

        self.scroll = ScrollableFrame(container)
        self.scroll.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        for r in self.rows:
            self._add_row(self.scroll.inner, r)

    def _add_row(self, parent, rowdef):
        row_id = rowdef["id"]
        rtype = rowdef["type"]
        events = EVENTS_BY_TYPE[rtype]

        row = ttk.Frame(parent, padding=(0, 4))
        row.pack(side="top", fill="x")

        name_var = tk.StringVar(value=rowdef["name"])
        self.row_namevars[row_id] = name_var

        entry = ttk.Entry(row, textvariable=name_var, width=24)
        entry.pack(side="left")

        # aggregates: lock name (optional; if you want them editable, remove this)
        if row_id in AGGREGATE_IDS:
            entry.state(["disabled"])
        else:
            entry.bind("<Return>", lambda e, rid=row_id: self._commit_name(rid))
            entry.bind("<FocusOut>", lambda e, rid=row_id: self._commit_name(rid))

        btn_frame = ttk.Frame(row)
        btn_frame.pack(side="left", fill="x", expand=True, padx=8)

        self.row_widgets.setdefault(row_id, {})
        for ek, label in events:
            b = ttk.Button(
                btn_frame,
                text=self._btn_text(row_id, ek, label),
                command=lambda rid=row_id, k=ek: self.increment(rid, k),
                width=13
            )
            b.pack(side="left", padx=2)
            self.row_widgets[row_id][ek] = b

        undo_btn = ttk.Button(row, text="Undo", command=lambda rid=row_id: self.undo(rid))
        undo_btn.pack(side="right")

    def _commit_name(self, row_id: str):
        """Update display name in self.rows from the entry StringVar."""
        new_name = (self.row_namevars[row_id].get() or "").strip()
        if not new_name:
            # revert to previous stored name
            stored = next(r["name"] for r in self.rows if r["id"] == row_id)
            self.row_namevars[row_id].set(stored)
            return

        # prevent duplicate display names (optional; comment out if you don't care)
        names = [r["name"] for r in self.rows if r["id"] != row_id]
        if new_name in names:
            messagebox.showerror("Name exists", f"'{new_name}' already exists.")
            stored = next(r["name"] for r in self.rows if r["id"] == row_id)
            self.row_namevars[row_id].set(stored)
            return

        for r in self.rows:
            if r["id"] == row_id:
                r["name"] = new_name
                break

    # ---------------- Counts ----------------

    def _btn_text(self, row_id, event_key, label):
        return f"{label}\n{int(self.counts[row_id].get(event_key, 0))}"

    def _refresh_row(self, row_id):
        rtype = next(r["type"] for r in self.rows if r["id"] == row_id)
        for ek, label in EVENTS_BY_TYPE[rtype]:
            self.row_widgets[row_id][ek].configure(text=self._btn_text(row_id, ek, label))

    def increment(self, row_id, event_key):
        self.counts[row_id][event_key] = int(self.counts[row_id].get(event_key, 0)) + 1
        self.undo_stack[row_id].append(event_key)
        self._refresh_row(row_id)

    def undo(self, row_id):
        if not self.undo_stack[row_id]:
            return
        last = self.undo_stack[row_id].pop()
        cur = int(self.counts[row_id].get(last, 0))
        if cur > 0:
            self.counts[row_id][last] = cur - 1
        self._refresh_row(row_id)

    # ---------------- Save / Load ----------------

    def _safe_filename(self, s):
        bad = '<>:"/\\|?*'
        for ch in bad:
            s = s.replace(ch, "_")
        return s.strip().replace(" ", "_")[:80] or "session"

    def _session_dict(self):
        return {
            "version": 3,
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "match": self.match_var.get(),
            "opponent": self.opp_var.get(),
            "rows": self.rows,       # includes ids + display names
            "counts": self.counts,   # keyed by row_id
            "events_by_type": EVENTS_BY_TYPE,
        }

    def new_session(self):
        if not messagebox.askyesno("New session", "Discard current unsaved changes and start a new session?"):
            return
        self.current_file = None
        self.match_var.set(f"Match {today_str()}")
        self.opp_var.set("")

        self.rows = default_rows()
        self.counts = {r["id"]: {ek: 0 for ek, _ in EVENTS_BY_TYPE[r["type"]]} for r in self.rows}
        self.undo_stack = {r["id"]: [] for r in self.rows}

        # rebuild UI
        for w in self.scroll.inner.winfo_children():
            w.destroy()
        self.row_widgets = {}
        self.row_namevars = {}
        for r in self.rows:
            self._add_row(self.scroll.inner, r)

    def save_session(self):
        # Make sure any active name edit is committed
        self.focus()  # forces FocusOut handlers in most cases
        for r in self.rows:
            if r["id"] not in AGGREGATE_IDS:
                self._commit_name(r["id"])

        if self.current_file is None:
            return self.save_session_as()

        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                json.dump(self._session_dict(), f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", f"Saved to:\n{self.current_file}")
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save:\n{e}")

    def save_session_as(self):
        default_name = self._safe_filename(self.match_var.get() or f"match_{today_str()}") + ".json"
        path = filedialog.asksaveasfilename(
            title="Save session as",
            defaultextension=".json",
            initialfile=default_name,
            filetypes=[("Rugby tagger session", "*.json")]
        )
        if not path:
            return
        self.current_file = path
        self.save_session()

    def open_session(self):
        path = filedialog.askopenfilename(
            title="Open session",
            filetypes=[("Rugby tagger session", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.current_file = path
            self.match_var.set(data.get("match", f"Match {today_str()}"))
            self.opp_var.set(data.get("opponent", ""))

            # v3 format (preferred)
            if "rows" in data and "counts" in data:
                self.rows = list(data["rows"])
                loaded_counts = data["counts"]

                # rebuild counts (forward compatible w/ schema changes)
                self.counts = {}
                for r in self.rows:
                    rid = r["id"]
                    rtype = r["type"]
                    self.counts[rid] = {ek: 0 for ek, _ in EVENTS_BY_TYPE[rtype]}
                    if rid in loaded_counts:
                        for ek in self.counts[rid].keys():
                            self.counts[rid][ek] = int(loaded_counts[rid].get(ek, 0))

            else:
                # Older formats: best-effort import
                # Expecting roster as list of names, counts keyed by name.
                roster_names = data.get("roster")
                counts_by_name = data.get("counts", {})

                # Create default rows, then map player names by index
                self.rows = default_rows()
                for idx, r in enumerate(self.rows):
                    if r["id"].startswith("P") and roster_names:
                        # roster_names likely included aggregates at the front in v2,
                        # but if not, this still roughly maps.
                        try:
                            # Find matching "Player X" old name if present
                            old_name = f"Player {int(r['id'][1:])}"
                            # If someone had renamed in old version, we cannot reliably recover.
                            # So we keep default names here.
                            if old_name in roster_names:
                                r["name"] = old_name
                        except Exception:
                            pass

                # counts: initialize then try to map by legacy names when possible
                self.counts = {r["id"]: {ek: 0 for ek, _ in EVENTS_BY_TYPE[r["type"]]} for r in self.rows}

                # Map aggregates by exact name keys
                legacy_map = {
                    "Rucks": "RUCKS",
                    "Lineouts": "LINEOUTS",
                    "Scrums": "SCRUMS",
                    "Penalties": "PENALTIES",
                }
                for legacy_name, rid in legacy_map.items():
                    if legacy_name in counts_by_name:
                        for ek in self.counts[rid].keys():
                            self.counts[rid][ek] = int(counts_by_name[legacy_name].get(ek, 0))

                # Players: map "Player 1" -> P01 etc
                for i in range(1, 24):
                    legacy_name = f"Player {i}"
                    rid = f"P{i:02d}"
                    if legacy_name in counts_by_name:
                        for ek in self.counts[rid].keys():
                            self.counts[rid][ek] = int(counts_by_name[legacy_name].get(ek, 0))

            self.undo_stack = {r["id"]: [] for r in self.rows}

            # rebuild UI
            for w in self.scroll.inner.winfo_children():
                w.destroy()
            self.row_widgets = {}
            self.row_namevars = {}
            for r in self.rows:
                self._add_row(self.scroll.inner, r)

        except Exception as e:
            messagebox.showerror("Open failed", f"Could not open session:\n{e}")

    # ---------------- Reporting ----------------

    def _sum_players(self, key: str) -> int:
        """Sum a stat across all PLAYER rows."""
        total = 0
        for r in self.rows:
            if r["type"] == "PLAYER":
                total += int(self.counts[r["id"]].get(key, 0))
        return total

    def _donut(self, ax, values, labels, title, center_top=None, center_bottom=None):
        """
        Draw a donut chart on ax.
        - values: list of ints
        - labels: list[str]
        - title: str
        - center_*: optional strings for center text
        """
        total = sum(values)
        if total <= 0:
            # Draw an empty ring (so layout stays consistent)
            values = [1]
            labels = ["No data"]
            total = 0

        wedges, _ = ax.pie(
            values,
            startangle=90,
            counterclock=False,
            wedgeprops=dict(width=0.35)  # donut thickness
        )
        ax.set_title(title, fontsize=11)
        ax.axis("equal")

        # Center text
        if center_top is None:
            center_top = str(total) if total > 0 else "0"
        ax.text(0, 0.05, center_top, ha="center", va="center", fontsize=12, fontweight="bold")
        if center_bottom is not None:
            ax.text(0, -0.15, center_bottom, ha="center", va="center", fontsize=9)

        # Small legend per donut (like your reference image)
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=8)

    def _plot_team_recap_donuts(self, out_path: str):
        """
        Create a grid of donuts for the TEAM recap based on your requested set.
        """
        # --- Team totals from players
        carries_pos = self._sum_players("carry_pos")
        carries_neg = self._sum_players("carry_neg")

        tackles_made = self._sum_players("tackle_made")
        tackles_missed = self._sum_players("tackle_missed")

        handling_err = self._sum_players("handling_error")
        dropped_pass = self._sum_players("dropped_pass")

        # --- Aggregates
        rucks = self.counts["RUCKS"]
        lineouts = self.counts["LINEOUTS"]
        scrums = self.counts["SCRUMS"]

        # Own/opp scrums & lineouts
        own_scrum_won = int(scrums.get("own_won", 0))
        own_scrum_lost = int(scrums.get("own_lost", 0))
        opp_scrum_won = int(scrums.get("opp_won", 0))
        opp_scrum_lost = int(scrums.get("opp_lost", 0))

        own_lo_won = int(lineouts.get("own_won", 0))
        own_lo_lost = int(lineouts.get("own_lost", 0))
        opp_lo_won = int(lineouts.get("opp_won", 0))
        opp_lo_lost = int(lineouts.get("opp_lost", 0))

        # Rucks committed & defensive contest (we contest on opp rucks)
        atk_commit_1 = int(rucks.get("commit_1", 0))
        atk_commit_2 = int(rucks.get("commit_2", 0))
        atk_commit_3p = int(rucks.get("commit_3plus", 0))

        def_cont_0 = int(rucks.get("opp_uncontested", 0))
        def_cont_1 = int(rucks.get("opp_contest_1", 0))
        def_cont_2 = int(rucks.get("opp_contest_2", 0))

        # Success % helpers for center text
        def pct(a, b):
            t = a + b
            return f"{(100.0*a/t):.0f}%" if t > 0 else None

        # 9 donuts -> arrange in a 3x3 grid
        fig, axes = plt.subplots(3, 3, figsize=(16, 9))
        axes = axes.flatten()

        self._donut(
            axes[0],
            [carries_pos, carries_neg],
            ["positive", "negative"],
            "Carries",
            center_top=str(carries_pos + carries_neg),
        )

        self._donut(
            axes[1],
            [tackles_made, tackles_missed],
            ["made", "missed"],
            "Tackles",
            center_top=str(tackles_made + tackles_missed),
            center_bottom=pct(tackles_made, tackles_missed),
        )

        self._donut(
            axes[2],
            [handling_err, dropped_pass],
            ["handling", "dropped pass"],
            "Errors",
            center_top=str(handling_err + dropped_pass),
        )

        self._donut(
            axes[3],
            [own_scrum_won, own_scrum_lost],
            ["won", "lost"],
            "Own scrums",
            center_top=str(own_scrum_won + own_scrum_lost),
            center_bottom=pct(own_scrum_won, own_scrum_lost),
        )

        self._donut(
            axes[4],
            [opp_scrum_won, opp_scrum_lost],
            ["won", "lost"],
            "Opp scrums",
            center_top=str(opp_scrum_won + opp_scrum_lost),
            center_bottom=pct(opp_scrum_won, opp_scrum_lost),
        )

        self._donut(
            axes[5],
            [own_lo_won, own_lo_lost],
            ["won", "lost"],
            "Own lineouts",
            center_top=str(own_lo_won + own_lo_lost),
            center_bottom=pct(own_lo_won, own_lo_lost),
        )

        self._donut(
            axes[6],
            [opp_lo_won, opp_lo_lost],
            ["won", "lost"],
            "Opp lineouts",
            center_top=str(opp_lo_won + opp_lo_lost),
            center_bottom=pct(opp_lo_won, opp_lo_lost),
        )

        self._donut(
            axes[7],
            [atk_commit_1, atk_commit_2, atk_commit_3p],
            ["1", "2", "3+"],
            "Attacking rucks: players committed",
            center_top=str(atk_commit_1 + atk_commit_2 + atk_commit_3p),
        )

        self._donut(
            axes[8],
            [def_cont_0, def_cont_1, def_cont_2],
            ["0", "1", "2"],
            "Defensive contest on opp rucks",
            center_top=str(def_cont_0 + def_cont_1 + def_cont_2),
        )

        fig.suptitle(f"{self.match_var.get()}  vs  {self.opp_var.get()}".strip(), fontsize=14)
        plt.tight_layout()
        plt.savefig(out_path, dpi=200)
        plt.close(fig)

    def _plot_player_barplot(self, player_row_id: str, out_path: str):
        """
        One comprehensive barplot per player with all their individual stats.
        """
        # Order + grouping-friendly labels
        items = [
            ("carry_pos", "Carry +"),
            ("carry_neg", "Carry -"),
            ("pass", "Pass"),
            ("ground_pass", "Ground pass"),
            ("offload", "Offload"),
            ("tackle_made", "Tkl made"),
            ("tackle_missed", "Tkl missed"),
            ("tackle_assist", "Tkl assist"),
            ("handling_error", "Handling err"),
            ("dropped_pass", "Dropped pass"),
        ]

        labels = [lbl for _, lbl in items]
        values = [int(self.counts[player_row_id].get(k, 0)) for k, _ in items]

        player_name = self._row_name(player_row_id)

        plt.figure(figsize=(10, 4.6))
        plt.bar(labels, values)
        plt.xticks(rotation=30, ha="right")
        plt.title(player_name)
        plt.tight_layout()
        plt.savefig(out_path, dpi=200)
        plt.close()

    def generate_report(self):
        # commit names before report
        self.focus()
        for r in self.rows:
            if r["id"] not in AGGREGATE_IDS:
                self._commit_name(r["id"])

        out_dir = filedialog.askdirectory(title="Choose output folder for report")
        if not out_dir:
            return

        match_name = self.match_var.get().strip() or f"Match_{today_str()}"
        base = self._safe_filename(match_name)
        report_dir = os.path.join(out_dir, f"{base}_report")
        os.makedirs(report_dir, exist_ok=True)

        # Subfolder for per-player outputs
        players_dir = os.path.join(report_dir, "players")
        os.makedirs(players_dir, exist_ok=True)

        # CSV + summary
        csv_path = os.path.join(report_dir, "stats.csv")
        self._write_csv(csv_path)

        summary_path = os.path.join(report_dir, "summary.txt")
        self._write_summary(summary_path)

        # TEAM RECAP donut grid
        try:
            team_img = os.path.join(report_dir, "team_recap.png")
            self._plot_team_recap_donuts(team_img)
        except Exception as e:
            messagebox.showerror("Report failed", f"CSV/Summary written but team recap failed:\n{e}")
            return

        # PER PLAYER barplots
        try:
            for r in self.rows:
                if r["type"] != "PLAYER":
                    continue
                rid = r["id"]
                safe_name = self._safe_filename(r["name"])
                out_path = os.path.join(players_dir, f"{safe_name}.png")
                self._plot_player_barplot(rid, out_path)
        except Exception as e:
            messagebox.showerror("Report failed", f"Team recap written but player charts failed:\n{e}")
            return

        messagebox.showinfo("Report generated", f"Saved report to:\n{report_dir}")

    def _row_name(self, row_id: str) -> str:
        return next(r["name"] for r in self.rows if r["id"] == row_id)

    def _write_csv(self, path):
        # Union of all keys for columns
        all_event_keys = []
        seen = set()
        for evs in EVENTS_BY_TYPE.values():
            for ek, _ in evs:
                if ek not in seen:
                    seen.add(ek)
                    all_event_keys.append(ek)

        with open(path, "w", encoding="utf-8") as f:
            f.write("row_id,display_name,row_type," + ",".join(all_event_keys) + "\n")
            for r in self.rows:
                rid = r["id"]
                rtype = r["type"]
                display = r["name"]
                row = [rid, display, rtype]
                for ek in all_event_keys:
                    row.append(str(int(self.counts[rid].get(ek, 0))))
                f.write(",".join(row) + "\n")

        mapping_path = os.path.join(os.path.dirname(path), "event_key_mapping.txt")
        with open(mapping_path, "w", encoding="utf-8") as mf:
            for rtype, evs in EVENTS_BY_TYPE.items():
                mf.write(f"[{rtype}]\n")
                for ek, lbl in evs:
                    mf.write(f"{ek} = {lbl}\n")
                mf.write("\n")

    def _write_summary(self, path):
        player_rows = [r for r in self.rows if r["type"] == "PLAYER"]
        tackles_made = sum(int(self.counts[r["id"]].get("tackle_made", 0)) for r in player_rows)
        tackles_missed = sum(int(self.counts[r["id"]].get("tackle_missed", 0)) for r in player_rows)
        attempts = tackles_made + tackles_missed
        success = (tackles_made / attempts * 100.0) if attempts else 0.0

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Match: {self.match_var.get()}\n")
            f.write(f"Opponent: {self.opp_var.get()}\n")
            f.write(f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}\n\n")

            f.write("AGGREGATES\n")
            for rid in ["RUCKS", "LINEOUTS", "SCRUMS", "PENALTIES"]:
                rtype = next(r["type"] for r in self.rows if r["id"] == rid)
                f.write(f"\n{self._row_name(rid).upper()}\n")
                for ek, lbl in EVENTS_BY_TYPE[rtype]:
                    f.write(f"- {lbl}: {int(self.counts[rid].get(ek, 0))}\n")

            f.write("\nPLAYERS (TOTALS)\n")
            f.write(f"- Tackles made: {tackles_made}\n")
            f.write(f"- Tackles missed: {tackles_missed}\n")
            f.write(f"- Tackle success %: {success:.1f}\n")

    def _plot_row(self, row_id, out_path):
        rtype = next(r["type"] for r in self.rows if r["id"] == row_id)
        evs = EVENTS_BY_TYPE[rtype]
        labels = [lbl for _, lbl in evs]
        values = [int(self.counts[row_id].get(ek, 0)) for ek, _ in evs]

        plt.figure(figsize=(12, 4.6))
        plt.bar(labels, values)
        plt.xticks(rotation=30, ha="right")
        plt.title(self._row_name(row_id))
        plt.tight_layout()
        plt.savefig(out_path, dpi=160)
        plt.close()

    def _plot_players_metric(self, metric_key, title, out_path):
        players = [r for r in self.rows if r["type"] == "PLAYER"]
        names = [r["name"] for r in players]
        values = [int(self.counts[r["id"]].get(metric_key, 0)) for r in players]

        plt.figure(figsize=(12, 4.8))
        plt.bar(names, values)
        plt.xticks(rotation=35, ha="right")
        plt.title(title)
        plt.tight_layout()
        plt.savefig(out_path, dpi=160)
        plt.close()


if __name__ == "__main__":
    app = RugbyReviewApp()
    app.mainloop()