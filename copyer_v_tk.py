import glob
import os
import pandas as pd
import shutil
import tkinter as tk
import sv_ttk
import pywinstyles
from tkinter import filedialog
from tkinter import ttk  # Import ttk for Progressbar
from tkinter import messagebox  # Import messagebox for error windows

# Function to copy files
def copyFiles(targetDir, dir, progress_bar=None, progress_label=None, total_dirs=None, update_progress=None):
    if os.path.exists(targetDir):
        return
    metaData = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.split('.')[-1] == 'csv']
    if len(metaData) != 1:
        show_error(f"Found more than one metadata file in {dir}. Skipping this directory.")
        return
    niftifs = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.endswith('.nii.gz')]
    metafile = metaData[0]
    df = pd.read_csv(metafile)
    nameVals = []
    if len(niftifs) != len(df):
        show_error(f"Number of nii.gz files do not match dataframe rows in {dir}. Skipping this directory.")
        return
    os.makedirs(targetDir, exist_ok=True)
    if '3D_annotation' in df:
        nameVals = df['3D_annotation'].tolist()
        nameVals = map(lambda el: el.strip(), nameVals)
    else:
        show_error(f'Annotation name not found in {dir}. Skipping this directory.')
        return
    niftifs.sort(key=lambda f: int(os.path.basename(f).split('.')[0].split('-')[1]))

    # Copy nii.gz files
    for i, (nf, areaName) in enumerate(zip(niftifs, nameVals)):
        shutil.copyfile(nf, os.path.join(targetDir, f'{areaName}.nii.gz'))
        if progress_bar:
            progress_bar.step(1)  # Update the progress bar for nii.gz files
            if progress_label and total_dirs:
                update_progress(progress_bar['value'], total_dirs)

    # Copy DCM files
    dcmfs = [f for f in glob.glob(f'{dir}/**', recursive=True) if f.split('.')[-1] == 'dcm']
    os.makedirs(os.path.join(targetDir, 'DCM'), exist_ok=True)
    for i, dcmfile in enumerate(dcmfs):
        shutil.copyfile(dcmfile, os.path.join(targetDir, 'DCM', os.path.basename(dcmfile)))
        if progress_bar:
            progress_bar.step(1)  # Update the progress bar for dcm files
            if progress_label and total_dirs:
                update_progress(progress_bar['value'], total_dirs)

# Function to show an error message box and terminate the program
def show_error(message):
    messagebox.showerror("Error", message)
    exit()  # Terminate the program

# Main Tkinter application
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Liver export format copyer")

        self.origin_dir = ""
        self.target_dir = ""

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        # Origin directory label and entry
        self.origin_label = ttk.Label(self, text="Origin Directory:")
        self.origin_label.grid(row=0, column=0, padx=10, pady=5)

        self.origin_entry = ttk.Entry(self, width=50)
        self.origin_entry.grid(row=0, column=1, padx=10, pady=5)

        self.origin_button = ttk.Button(self, text="Choose Origin", command=self.choose_origin)
        self.origin_button.grid(row=0, column=2, padx=10, pady=5)

        # Target directory label and entry
        self.target_label = ttk.Label(self, text="Target Directory:")
        self.target_label.grid(row=1, column=0, padx=10, pady=5)

        self.target_entry = ttk.Entry(self, width=50)
        self.target_entry.grid(row=1, column=1, padx=10, pady=5)

        self.target_button = ttk.Button(self, text="Choose Target", command=self.choose_target)
        self.target_button.grid(row=1, column=2, padx=10, pady=5)

        # Go button to start processing
        self.go_button = ttk.Button(self, text="Go", command=self.run_program)
        self.go_button.grid(row=2, column=0, columnspan=3, ipadx=5, pady=10)

        # Progress bar (use ttk Progressbar for progress tracking)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.grid(row=3, column=0, columnspan=3, padx=10, pady=5)

        # Label to display progress text
        self.progress_label = ttk.Label(self, text="Copied 0 / 0 directories")
        self.progress_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5)

        sv_ttk.use_dark_theme()
        # pywinstyles.change_header_color(self,'#1c1c1c')
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

    def update_progress(self, copied, total):
        """Updates the progress label text."""
        self.progress_label.config(text=f"Copied {copied} / {total} directories")

    def run_program(self):
        originDir = self.origin_dir
        targetDir = self.target_dir

        if not os.path.exists(originDir) or not os.path.exists(targetDir):
            show_error("Invalid directories! Please select valid origin and target directories.")

        rootdirs = [f for f in glob.glob(f'{originDir}/**') if os.path.isdir(f)]
        # print("from", originDir)
        # print(f'Copying {len(rootdirs)} directories')
        # print("to", targetDir)

        self.progress_bar["value"] = 0  # Reset progress bar value
        self.progress_bar["maximum"] = len(rootdirs)  # Set the max value to number of directories

        # Variable to track the number of directories copied
        copied_dirs = 0

        for dir in rootdirs:
            subdirs = [f for f in glob.glob(f'{dir}/**') if os.path.isdir(f)]
            if len(subdirs) > 1:
                for sbdr in subdirs:
                    copyFiles(os.path.join(targetDir, os.path.basename(dir), os.path.basename(sbdr)), sbdr, 
                              self.progress_bar, self.progress_label, len(rootdirs), self.update_progress)
            else:
                copyFiles(os.path.join(targetDir, os.path.basename(dir)), dir, 
                          self.progress_bar, self.progress_label, len(rootdirs), self.update_progress)

            # Update the progress bar after processing each directory
            copied_dirs += 1
            self.progress_bar["value"] = copied_dirs
            self.update_progress(copied_dirs, len(rootdirs))

        # print("File copy completed!")

# Run the application
if __name__ == "__main__":
    app = Application()
    app.mainloop()
