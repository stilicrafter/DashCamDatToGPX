import os
import tkinter as tk
from tkinter import filedialog, messagebox

# Kleine, einfache GUI zum Auswählen einer .dat-Datei und eines Ausgabepfads (.gpx)
def select_dat_file(entry_widget):
    path = filedialog.askopenfilename(title="DAT-Datei wählen", filetypes=[("DAT-Dateien", "*.dat"), ("Alle Dateien", "*.*")])
    if path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path)

def select_output_file(entry_widget):
    path = filedialog.asksaveasfilename(title="GPX-Ausgabedatei", defaultextension=".gpx", filetypes=[("GPX-Dateien", "*.gpx"), ("Alle Dateien", "*.*")])
    if path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path)

def do_convert(dat_entry, out_entry):
    dat_path = dat_entry.get().strip()
    out_path = out_entry.get().strip()
    if not dat_path or not os.path.isfile(dat_path):
        messagebox.showerror("Fehler", "Bitte gültige .dat-Datei wählen.")
        return
    if not out_path:
        messagebox.showerror("Fehler", "Bitte einen Ausgabepfad angeben.")
        return
    try:
        from pyFiles.convert import convert
        convert(dat_path, out_path)
        messagebox.showinfo("Erfolg", f"Konvertierung abgeschlossen:\n{out_path}")
    except Exception as e:
        messagebox.showerror("Fehler", f"Konvertierung fehlgeschlagen:\n{e}")

def create_gui():
    root = tk.Tk()
    root.title("DAT -> GPX Konverter")

    # .dat Datei
    tk.Label(root, text="Quell-Datei (.dat):").grid(row=0, column=0, sticky="w", padx=6, pady=6)
    dat_entry = tk.Entry(root, width=60)
    dat_entry.grid(row=0, column=1, padx=6, pady=6)
    tk.Button(root, text="Öffnen...", command=lambda: select_dat_file(dat_entry)).grid(row=0, column=2, padx=6, pady=6)

    # Ausgabe Pfad
    tk.Label(root, text="Ausgabe (.gpx):").grid(row=1, column=0, sticky="w", padx=6, pady=6)
    out_entry = tk.Entry(root, width=60)
    out_entry.grid(row=1, column=1, padx=6, pady=6)
    tk.Button(root, text="Speichern unter...", command=lambda: select_output_file(out_entry)).grid(row=1, column=2, padx=6, pady=6)

    # Convert Button
    tk.Button(root, text="Konvertieren", width=20, command=lambda: do_convert(dat_entry, out_entry)).grid(row=2, column=1, pady=12)

    root.mainloop()

if __name__ == "__main__":
    create_gui()