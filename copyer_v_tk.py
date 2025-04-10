import glob
import os
import pandas as pd
import shutil
import tkinter as tk
import sv_ttk
import pywinstyles
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox
import threading
import queue

# Function to copy files
def copyFiles(targetDir, dir):
    if os.path.exists(targetDir):
        return
    metaData = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.split('.')[-1] == 'csv']
    if len(metaData) != 1:
        raise LookupError(f"Found more than one metadata file in {dir}.")
    niftifs = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.endswith('.nii.gz')]
    metafile = metaData[0]
    df = pd.read_csv(metafile)
    if len(niftifs) != len(df):
        raise ValueError(f"Number of nii.gz files do not match dataframe rows in {dir}.")
    os.makedirs(targetDir, exist_ok=True)
    if '3D_annotation' in df:
        nameVals = df['3D_annotation'].tolist()
        nameVals = map(lambda el: el.strip() if type(el) == str else el, nameVals)
    else:
        raise LookupError(f'Annotation name not found in {dir}.')
    niftifs.sort(key=lambda f: int(os.path.basename(f).split('.')[0].split('-')[1]))

    # Copy nii.gz files
    for (nf, areaName) in zip(niftifs, nameVals):
        shutil.copyfile(nf, os.path.join(targetDir, f'{areaName}.nii.gz'))

    # Copy DCM files
    dcmfs = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.split('.')[-1] == 'dcm']
    os.makedirs(os.path.join(targetDir,'DCM'), exist_ok=True)
    for dcmfile in dcmfs:
        shutil.copyfile(dcmfile, os.path.join(targetDir, 'DCM', os.path.basename(dcmfile)))

# Main Tkinter application
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Liver export format copyer")

        self.origin_dir = ""
        self.target_dir = ""

        self.queue = queue.Queue()

        self.create_widgets()
        self.after(100, self.process_queue)

    def create_widgets(self):
        self.origin_label = ttk.Label(self, text="Origin Directory:")
        self.origin_label.grid(row=0, column=0, padx=10, pady=5)

        self.origin_entry = ttk.Entry(self, width=50)
        self.origin_entry.grid(row=0, column=1, padx=10, pady=5)

        self.origin_button = ttk.Button(self, text="Choose Origin", command=self.choose_origin)
        self.origin_button.grid(row=0, column=2, padx=10, pady=5)

        self.target_label = ttk.Label(self, text="Target Directory:")
        self.target_label.grid(row=1, column=0, padx=10, pady=5)

        self.target_entry = ttk.Entry(self, width=50)
        self.target_entry.grid(row=1, column=1, padx=10, pady=5)

        self.target_button = ttk.Button(self, text="Choose Target", command=self.choose_target)
        self.target_button.grid(row=1, column=2, padx=10, pady=5)

        self.go_button = ttk.Button(self, text="Go", command=self.run_program)
        self.go_button.grid(row=2, column=0, columnspan=3, ipadx=5, pady=10)

        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

        self.progress_label = ttk.Label(self, text="Copied 0 / 0 directories")
        self.progress_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5)

        sv_ttk.use_dark_theme()
        pywinstyles.apply_style(self,'dark')
        self.wm_attributes("-alpha", 0.99)
        self.wm_attributes("-alpha", 1)

    def choose_origin(self):
        self.origin_dir = filedialog.askdirectory()
        self.origin_entry.delete(0, tk.END)
        self.origin_entry.insert(0, self.origin_dir)

    def choose_target(self):
        self.target_dir = filedialog.askdirectory()
        self.target_entry.delete(0, tk.END)
        self.target_entry.insert(0, self.target_dir)

    def update_gui_progress(self, copied, total):
        self.progress_bar.step()
        self.progress_label.config(text=f"Copied {copied} / {total} directories")

    def run_program(self):
        thread = threading.Thread(target=self.copy_in_thread, daemon=True)
        thread.start()

    def copy_in_thread(self):
        originDir = self.origin_dir
        targetDir = self.target_dir

        if not os.path.exists(originDir) or not os.path.exists(targetDir):
            self.queue.put(lambda: messagebox.showerror("Error", "Invalid directories! Please select valid origin and target directories."))
            return

        rootdirs = [f for f in glob.glob(f'{originDir}/**') if os.path.isdir(f)]

        self.queue.put(lambda: self.progress_bar.config(value=0, maximum=len(rootdirs)))
        copied_dirs = 0

        for dir in rootdirs:
            subdirs = [f for f in glob.glob(f'{dir}/**') if os.path.isdir(f)]
            try:
                if len(subdirs) > 1:
                    for sbdr in subdirs:
                        copyFiles(os.path.join(targetDir, os.path.basename(dir), os.path.basename(sbdr)), sbdr)
                else:
                    copyFiles(os.path.join(targetDir, os.path.basename(dir)), dir)
            except Exception as e:
                self.queue.put(lambda err=str(e): messagebox.showerror("Error", err))
                return

            copied_dirs += 1
            self.queue.put(lambda cd=copied_dirs, total=len(rootdirs): self.update_gui_progress(cd, total))

        self.queue.put(lambda: messagebox.showinfo("Done", "All directories copied successfully!"))

    def process_queue(self):
        try:
            while True:
                task = self.queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(10, self.process_queue)

# Run the application
if __name__ == "__main__":
    app = Application()
    app.mainloop()
