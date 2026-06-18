#!/usr/bin/env python3
"""
PCS Scrubber (Windows) — Process raw CSV contact files, strip prefixes,
assign channels, and output a clean 3-column CSV.
"""

import os
import sys
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread
from datetime import datetime
import platform

HAS_DND = False
if platform.system() == "Windows":
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        HAS_DND = True
    except Exception:
        pass


def process_csv(filepath, out_dir, output_name=None, progress_cb=None):
    """Process raw CSV: strip prefixes, assign channels, output 3-column CSV."""
    if output_name:
        if not output_name.endswith(".csv"):
            output_name += ".csv"
        out_path = os.path.join(out_dir, output_name)
    else:
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(out_dir, f"{base_name}_PCS_Scrubbed.csv")

    rows_written = 0
    rows_skipped = 0
    skip_reasons = {}

    with open(filepath, newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames or []
        results = []

        # Detect format
        fieldnames_lower = [f.strip().lower() for f in fieldnames]
        is_e2e = "contact id" in fieldnames_lower
        # Pre-scrubbed format: has "channel" + "contact_id" (underscore) with plain UUIDs
        is_prescrubbed = ("channel" in fieldnames_lower and "contact_id" in fieldnames_lower
                          and "contact id" not in fieldnames_lower)

        for row in reader:
            if is_prescrubbed:
                # Already has channel column and clean UUID contact_id
                raw_channel = (row.get("channel") or "").strip().upper()
                if raw_channel == "VOICE":
                    channel = "VOICE"
                elif raw_channel == "CHAT":
                    channel = "CHAT"
                else:
                    reason = f"Unsupported channel: {raw_channel}"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue
                clean_id = (row.get("contact_id") or "").strip()
                date_str = (row.get("connect_to_agent_date") or row.get("contact_day") or "").strip()
            elif is_e2e:
                # E2E format: bare UUID in "Contact ID", channel in "Channel"
                clean_id = (row.get("Contact ID") or row.get("contact id") or
                            next((v for k, v in row.items() if k.strip().lower() == "contact id"), "")).strip()
                raw_channel = (row.get("Channel") or row.get("channel") or
                               next((v for k, v in row.items() if k.strip().lower() == "channel"), "")).strip().upper()
                if raw_channel == "VOICE":
                    channel = "VOICE"
                elif raw_channel == "CHAT":
                    channel = "CHAT"
                else:
                    reason = f"Unsupported channel: {raw_channel}"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue
                # Date from "Initiation timestamp"
                date_str = (row.get("Initiation timestamp") or
                            next((v for k, v in row.items() if k.strip().lower() == "initiation timestamp"), "")).strip()
            else:
                # RVOC format: prefixed contact_id, date in contact_day/contact_create_time
                contact_id = row.get("contact_id", "")
                date_str = ""
                for col in ("contact_day", "contact_create_time", "connect_to_agent_date"):
                    if col in row and row[col]:
                        date_str = row[col].strip()
                        break

                if contact_id.startswith("IN_CALL-"):
                    channel = "VOICE"
                    clean_id = contact_id[len("IN_CALL-"):]
                elif contact_id.startswith("OUT_CALL-"):
                    channel = "VOICE"
                    clean_id = contact_id[len("OUT_CALL-"):]
                elif contact_id.startswith("CHAT-"):
                    channel = "CHAT"
                    clean_id = contact_id[len("CHAT-"):]
                else:
                    prefix = contact_id.split("-")[0] if "-" in contact_id else contact_id
                    reason = f"Unsupported channel: {prefix}"
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    rows_skipped += 1
                    continue

            # Parse date, output as M/D/YY
            formatted_date = date_str
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    formatted_date = f"{dt.month}/{dt.day}/{dt.year % 100:02d}"
                    break
                except ValueError:
                    continue

            results.append((channel, formatted_date, clean_id))
            rows_written += 1

            if progress_cb and rows_written % 100 == 0:
                progress_cb(rows_written, rows_skipped)

    # Deduplicate by contact_id (column 3), keeping first occurrence
    seen_ids = set()
    unique_results = []
    dupes_removed = 0
    for r in results:
        if r[2] not in seen_ids:
            seen_ids.add(r[2])
            unique_results.append(r)
        else:
            dupes_removed += 1

    with open(out_path, "w", newline="", encoding="utf-8-sig") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["channel", "connect_to_agent_date", "contact_id"])
        writer.writerows(unique_results)

    rows_written = len(unique_results)

    if progress_cb:
        progress_cb(rows_written, rows_skipped)

    return out_path, rows_written, rows_skipped, skip_reasons, dupes_removed


# ── GUI ──────────────────────────────────────────────────────────────────────

def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title("PCS Scrubber")

    # Set icon
    try:
        if getattr(sys, 'frozen', False):
            ico_path = os.path.join(sys._MEIPASS, "icon.ico")
        else:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
        root.iconbitmap(ico_path)
    except Exception:
        pass

    # ── Dark theme ──
    BG = "#1e1e1e"
    CARD = "#2a2a2a"
    FG = "#f0f0f0"
    DIM = "#888888"
    ACCENT = "#28b253"
    ACCENT_ACTIVE = "#34c964"
    FONT_FAMILY = "Consolas"

    root.configure(bg=BG)
    root.resizable(False, False)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=FG, font=(FONT_FAMILY, 12))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG, font=(FONT_FAMILY, 12))
    style.configure("Dim.TLabel", foreground=DIM)
    style.configure("Accent.TLabel", foreground=ACCENT, font=(FONT_FAMILY, 12, "bold"))
    style.configure("Card.TButton", background=CARD, foreground=FG,
                    font=(FONT_FAMILY, 12), padding=(12, 10), borderwidth=0, relief="flat")
    style.map("Card.TButton", background=[("active", "#363636")], foreground=[("active", FG)])
    style.configure("Run.TButton", background=ACCENT, foreground="#000000",
                    font=(FONT_FAMILY, 14, "bold"), padding=(12, 14), borderwidth=0, relief="flat")
    style.map("Run.TButton",
              background=[("active", ACCENT_ACTIVE), ("disabled", "#555555")],
              foreground=[("active", "#000000"), ("disabled", "#999999")])

    state = {"input": "", "output": ""}
    _placeholder = "Example: Project_Name_PCS"

    # ── Header with icon ──
    header_frame = tk.Frame(root, bg=BG)
    header_frame.pack(fill="x", padx=16, pady=(16, 8))

    try:
        if getattr(sys, 'frozen', False):
            _hdr_path = os.path.join(sys._MEIPASS, "icon.png")
        else:
            _hdr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        from PIL import Image, ImageTk
        _hdr_img = Image.open(_hdr_path).resize((64, 64), Image.LANCZOS)
        _hdr_photo = ImageTk.PhotoImage(_hdr_img)
        _icon_lbl = tk.Label(header_frame, image=_hdr_photo, bg=BG)
        _icon_lbl.image = _hdr_photo
        _icon_lbl.pack(pady=(0, 4))
    except Exception:
        pass

    tk.Label(header_frame, text="PCS Scrubber", bg=BG, fg=FG,
             font=(FONT_FAMILY, 18, "bold")).pack()

    # Separator
    tk.Frame(root, bg="#333333", height=1).pack(fill="x", padx=16, pady=(8, 8))

    # ── Input File Button ──
    tk.Label(root, text="Drop A Dirty File:", bg=BG, fg=FG,
             font=(FONT_FAMILY, 12)).pack(anchor="w", padx=18, pady=(4, 4))

    btn_input = ttk.Button(root, text="Select Input File…", style="Card.TButton")
    btn_input.pack(fill="x", padx=16, pady=(16, 4))

    def browse_file():
        path = filedialog.askopenfilename(
            title="Select raw CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            set_input(path)

    def set_input(path):
        state["input"] = path
        btn_input.config(text=f"📄 {os.path.basename(path)}")
        entry_name.delete(0, "end")
        entry_name.config(fg=DIM)
        entry_name.insert(0, _placeholder)

    btn_input.config(command=browse_file)

    # ── Windows drag-and-drop ──
    if HAS_DND:
        def on_drop(event):
            path = event.data.strip("{}")
            if os.path.isfile(path) and path.lower().endswith(".csv"):
                set_input(path)

        btn_input.drop_target_register(DND_FILES)
        btn_input.dnd_bind("<<Drop>>", on_drop)
        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", on_drop)

    # ── Output Directory Button ──
    tk.Label(root, text="Send Squeaky Clean File Here:", bg=BG, fg=FG,
             font=(FONT_FAMILY, 12)).pack(anchor="w", padx=18, pady=(12, 4))

    btn_output = ttk.Button(root, text="Select Output Directory…", style="Card.TButton")
    btn_output.pack(fill="x", padx=16, pady=(4, 4))

    def browse_dir():
        d = filedialog.askdirectory(title="Select output directory")
        if d:
            state["output"] = d
            btn_output.config(text=f"📁 {os.path.basename(d)}/")

    btn_output.config(command=browse_dir)

    # ── Output Filename Entry ──
    tk.Label(root, text="Scrubbed Filename:", bg=BG, fg=FG,
             font=(FONT_FAMILY, 12)).pack(anchor="w", padx=18, pady=(10, 4))

    name_frame = tk.Frame(root, bg=CARD, highlightbackground="#333333", highlightthickness=1)
    name_frame.pack(fill="x", padx=16, pady=(0, 4))

    entry_name = tk.Entry(name_frame, bg=CARD, fg=FG, font=(FONT_FAMILY, 12),
                          insertbackground=FG, borderwidth=0, relief="flat")
    entry_name.pack(fill="x", padx=8, pady=8)

    # Placeholder
    entry_name.insert(0, _placeholder)
    entry_name.config(fg=DIM)

    def _on_focus_in(e):
        if entry_name.get() == _placeholder:
            entry_name.delete(0, "end")
            entry_name.config(fg=FG)

    def _on_focus_out(e):
        if not entry_name.get():
            entry_name.insert(0, _placeholder)
            entry_name.config(fg=DIM)

    entry_name.bind("<FocusIn>", _on_focus_in)
    entry_name.bind("<FocusOut>", _on_focus_out)

    # ── Log/Progress Display ──
    ttk.Label(root, text="Log", style="Dim.TLabel").pack(anchor="w", padx=18, pady=(12, 4))

    log_frame = tk.Frame(root, bg=CARD, highlightbackground="#333333", highlightthickness=1)
    log_frame.pack(fill="both", padx=16, pady=(0, 12), expand=True)

    log_text = tk.Text(log_frame, bg=CARD, fg=FG, font=(FONT_FAMILY, 11),
                       height=10, width=55, wrap="word", borderwidth=0,
                       insertbackground=FG, state="disabled")
    log_text.pack(fill="both", expand=True, padx=8, pady=8)

    def log_msg(msg):
        log_text.config(state="normal")
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        log_text.config(state="disabled")

    # ── Scrub Button ──
    btn_run = ttk.Button(root, text="Deploy Scrubbing Bubbles", style="Run.TButton")
    btn_run.pack(fill="x", padx=16, pady=(0, 16))

    def run_scrub():
        src = state["input"]
        out = state["output"]
        if not src:
            messagebox.showwarning("Missing input", "Please select an input CSV file.")
            return
        if not out:
            messagebox.showwarning("Missing output", "Please select an output directory.")
            return

        fname = entry_name.get().strip()
        if not fname or fname == _placeholder:
            messagebox.showwarning("Missing filename", "Please enter a scrubbed filename.")
            return

        btn_run.config(state="disabled", text="Processing…")
        log_text.config(state="normal")
        log_text.delete("1.0", "end")
        log_text.config(state="disabled")

        def work():
            try:
                root.after(0, lambda: log_msg(f"Processing: {os.path.basename(src)}"))

                def on_progress(written, skipped):
                    root.after(0, lambda: log_msg(f"  Processed {written} rows ({skipped} skipped)"))

                out_path, written, skipped, skip_reasons, dupes_removed = process_csv(src, out,
                    output_name=fname, progress_cb=on_progress)
                root.after(0, lambda: log_msg(f"\n✓ Complete!"))
                root.after(0, lambda: log_msg(f"  Output: {os.path.basename(out_path)}"))
                root.after(0, lambda: log_msg(f"  Rows written: {written}"))
                root.after(0, lambda: log_msg(f"  Rows skipped: {skipped}"))
                if dupes_removed:
                    root.after(0, lambda: log_msg(f"  Duplicates removed: {dupes_removed}"))
                if skip_reasons:
                    root.after(0, lambda: log_msg(f"\n  Skip reasons:"))
                    for reason, count in skip_reasons.items():
                        root.after(0, lambda r=reason, c=count: log_msg(f"    • {r}: {c} row(s)"))
                root.after(0, lambda: messagebox.showinfo("Done",
                    f"Scrubbing complete!\n\n{written} rows written, {skipped} skipped.\n\nOutput: {os.path.basename(out_path)}"))
            except Exception as e:
                root.after(0, lambda: log_msg(f"\n✗ Error: {e}"))
                root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                root.after(0, lambda: btn_run.config(state="normal", text="Deploy Scrubbing Bubbles"))

        Thread(target=work, daemon=True).start()

    btn_run.config(command=run_scrub)

    root.update_idletasks()
    root.lift()
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))
    root.mainloop()


if __name__ == "__main__":
    main()
