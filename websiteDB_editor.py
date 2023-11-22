from itertools import islice
import os
import re
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from typing import Any, Generator, Optional, Set, TextIO, Tuple


__version__ = "v0.0.2"

class WebsiteCheckerGUI():
    def __init__(self, root):
        self.root = root
        self.root.title("WebsiteDB Editor")
        self.root.minsize(500, 80)
        self.root.resizable(0, 0)

        self.position_x = int((self.root.winfo_screenwidth()) / 3)
        self.position_y = int((self.root.winfo_screenheight()) / 3)
        self.root.geometry(f"+{self.position_x}+{self.position_y}")

        # Create a uniform grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        # Create buttons
        self.add_button = ttk.Button(root, text="Add Website", command=self.add_website)
        self.list_button = ttk.Button(root, text="List Websites", command=self.list_websites)
        self.save_quit_button = ttk.Button(root, text="Save & Quit", command=self.save_and_quit)

        # Grid buttons
        self.add_button.grid(row=1, column=0, padx=10, pady=10, sticky="sw")
        self.list_button.grid(row=1, column=0, padx=100, pady=10, sticky="sw")
        self.save_quit_button.grid(row=1, column=2, padx=10, pady=10, sticky="se")
        
        # Validator Defines
        self.length_thread = None
        self.websites_path = "websites.txt" # Or whatever gets specified in open_websites_file
        self.total_lines = self.open_websites_file(True)
        self.progress_window = None
        self.progress_label = None
        self.progress = 0
        self.url_pattern = re.compile(r'^\w+://')
        self.pattern = re.compile(r'(?<=\S)( #| on\b).*')
        self.needs_cleanup = False

        self.website_entry = self.create_entry_with_backdrop(root, "Enter website URL", width=40)
        self.error_entry = self.create_entry_with_backdrop(root, "error reason", width=12)
        self.version_entry = self.create_entry_with_backdrop(root, "version", width=12)

        self.large_file_label = ttk.Label(root, text="Large file opened, live duplication checking disabled!", foreground="orange")

        self.website_entry.grid(row=0, column=0, padx=10, pady=12, sticky="ew")
        self.error_entry.grid(row=0, column=1, padx=5, pady=12, sticky="ew")
        self.version_entry.grid(row=0, column=2, padx=10, pady=12, sticky="ew")

        # Create tooltips for the labels
        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open file", command=self.open_websites_file)
        file_menu.add_command(label="Validate DB", command=self.validate_websites)
        file_menu.add_command(label="Save & Quit", command=self.save_and_quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About App", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        root.config(menu=menubar)
    
    def open_websites_file(self, only_load=False):
        if not only_load:
            file_path = filedialog.askopenfilename(
                initialdir=os.getcwd(),
                title="Open Website.txt",
                filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
            )
            if file_path:
                self.websites_path = file_path
            
        # Cancel any ongoing thread and start a new one
        if self.length_thread and self.length_thread.is_alive():
            self.length_thread.cancel()
        self.length_thread = threading.Thread(target=self.get_file_length)
        self.length_thread.start()
    
    def get_file_length(self):
        self.root.title(f"Loading - {self.websites_path}...")
        self.list_button['state'] = 'disabled'
        self.add_button['state'] = 'disabled'

        try:
            mode = 'rb' if os.path.exists(self.websites_path) else 'wb'
            with open(self.websites_path, mode, buffering=(2 << 16) + 8) as file:
                if mode == 'rb':
                    self.total_lines = sum(1 for _ in file)
                else:
                    # If the file didn't exist, set total lines to 0
                    self.total_lines = 0
        finally:
            # Update the GUI with the total lines
            self.root.after(0, self.update_total_lines)
    
    def update_total_lines(self):
        # Update the total lines in the label
        self.length_thread = None
        self.list_button['state'] = 'normal'
        self.add_button['state'] = 'normal'
        self.root.title(f"WebsiteDB - Lines: {self.total_lines}")
        if self.total_lines > 50000:
            # Show the large file label
            self.large_file_label.grid(row=1, column=0, padx=10, pady=(0, 40),sticky="nsew")
        else:
            # Hide the large file label
            self.large_file_label.grid_forget()


    def create_entry_with_backdrop(self, parent, backdrop_text, width=25) -> ttk.Entry:
        entry = ttk.Entry(parent, width=width, justify='left', foreground='grey')
        entry.insert(0, backdrop_text)
        entry.configure()

        def on_click(event):
            if entry.get() == backdrop_text:
                entry.delete(0, tk.END)
                entry.configure(foreground='black', justify='left')

        def on_leave(event):
            if not entry.get() or entry.get() == backdrop_text:
                entry.insert(0, backdrop_text)
                entry.configure(foreground='grey', justify='left')

        entry.bind('<FocusIn>', on_click)
        entry.bind('<FocusOut>', on_leave)

        return entry
    
    def process_single_website(self, website: str) -> Tuple[Optional[str], Optional[str]]:
        error_site = None
        
        # Use a less resource intensive check first, then also check with regex
        if not website.startswith(("https://", "http://")):
            if not self.url_pattern.match(website):
                website = "https://" + website
                
        # Check for the presence of both " #" and " on " in the website
        if " #" in website and " on" in website:
            error_site = website.strip()
        elif " #" in website or " on" in website:
            website = self.pattern.sub('', website)

        # Return result based on whether there is an error or not
        if error_site:
            return None, error_site
        else:
            return website, None

    def add_website(self):
        website = self.website_entry.get().strip()
        error_reason = self.error_entry.get().strip()[:12]
        version = self.version_entry.get().strip()[:12]

        if not website or website == "Enter website URL":
            messagebox.showwarning("Invalid Input", "Please enter a valid website URL.")
            return

        error_reason = error_reason if error_reason != "error reason" else ""
        version = version if version != "version" else ""

        website_status = f"{website} #{error_reason} on {version}" if error_reason and version else website

        cleaned_site, error_site = self.process_single_website(website_status)

        # If we load the entire file and it's hundreds of megabytes long, this would lag too much
        if self.total_lines < 50000:
            
            with open(self.websites_path, "r", buffering=(2<<16) + 8, encoding="ascii") as file:
                websites = file.readlines()

            # Check if the website is already in the list
            if any(website_status in line for line in websites):
                messagebox.showwarning("Duplicate", "This website is already in the list.")
                return

            if cleaned_site or error_site:
                if error_site:
                    websites.insert(0, error_site + "\n")
                else:
                    websites.append(cleaned_site + "\n")

                with open(self.websites_path, "w", buffering=(2<<16) + 8, encoding="ascii") as file:
                    file.writelines(websites)

                self.clear_entry_fields(website=True)
                message = "Website has been added to the list."
                self.open_websites_file(True)
            else:
                message = "Please enter a valid website URL."
            
        else:
            # Handle the case when the line count exceeds 50000 without loading the entire file
            with open(self.websites_path, "a", encoding="ascii") as file:
                file.write((cleaned_site or error_site) + "\n")
                if error_site:
                    self.needs_cleanup = True

            self.clear_entry_fields(website=True)
            message = "Website has been added to the list."

        # Show messagebox only once with the appropriate message
        if cleaned_site or error_site:
            messagebox.showinfo("Website Added", message)
        else:
            messagebox.showwarning("Invalid Input", message)

    def clear_entry_fields(self, website=False):
        if website:
            self.website_entry.delete(0, tk.END)
            self.website_entry.configure(foreground='grey', justify='left')

    def list_websites(self, elements_per_page=5000):
        # Open the file to get its length

        # Create a Toplevel window for listing websites
        list_window = tk.Toplevel(self.root)
        list_window.title(f"List of Websites - {self.total_lines} Websites")
        list_window.minsize(600, 400)
        list_window.geometry(f"+{self.position_x}+{self.position_y}")

        # Create a Treeview for displaying websites, errors, and tested on
        tree = ttk.Treeview(list_window, columns=("Website", "Error", "Tested On"), show="headings", height=20)
        tree.pack(expand=True, fill="both", padx=(15, 0), pady=10)

        # Set column headers
        tree.heading("Website", text="Website")
        tree.heading("Error", text="Error")
        tree.heading("Tested On", text="Tested On")

        # Set column widths
        tree.column("Website", width=280)
        tree.column("Error", width=1)
        tree.column("Tested On", width=1)

        # Insert data into the Treeview based on pagination
        total_pages = (self.total_lines + elements_per_page - 1) // elements_per_page
        current_page = 1

        current_page_label = ttk.Label(list_window, text=f"Page: {current_page}/{total_pages}")

        # Page switcher
        def show_page(page):
            nonlocal current_page
            current_page = page
            tree.delete(*tree.get_children())  # Clear the tree

            start_index = (page - 1) * elements_per_page
            end_index = page * elements_per_page

            with open(self.websites_path, 'r', buffering=(2<<16) + 8, encoding="ascii") as file:
                line_iterator = islice(file, start_index, end_index)

                for line in line_iterator:
                    parts = line.split(' #', 1)
                    website_name = parts[0].strip()[:500]
                    error, tested_on = "", ""
                    if len(parts) > 1:
                        
                        error, _, tested_on = parts[1].partition(' on ')

                    tree.insert("", "end", values=(website_name, error, tested_on))

            # Update the current page label
            current_page_label.config(text=f"Page: {current_page}/{total_pages}")

        show_page(current_page)

        # Page switcher
        def next_page():
            if current_page < total_pages:
                show_page(current_page + 1)

        def prev_page():
            if current_page > 1:
                show_page(current_page - 1)

        # Page switcher buttons
        prev_button = ttk.Button(list_window, text="Previous", command=prev_page)
        prev_button.pack(side="left", padx=5, pady=5)

        next_button = ttk.Button(list_window, text="Next", command=next_page)
        next_button.pack(side="right", padx=5, pady=5)

        current_page_label.pack(side="top", pady=7)

        # Create a Scrollbar
        scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")

        # Configure the Treeview to use the Scrollbar
        tree.configure(yscrollcommand=scrollbar.set)

    def create_progress_window(self):
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Please Wait")
        self.progress_window.geometry(f"+{self.position_x}+{self.position_y}")
        self.progress_window.minsize(400, 100)
        self.progress_window.resizable(0, 0)

        self.progress_label = ttk.Label(self.progress_window, text="Validating websites: 0/0")
        self.progress_label.pack(pady=20)

    def update_progress_label(self, labeltext=None):
        if self.progress_window and self.progress_label:
            if not labeltext:
                self.progress_label.config(text=f"Validating websites: {self.progress}/{self.total_lines}")
            else:
                self.progress_label.config(text=labeltext)
            self.progress_window.update_idletasks()

    def destroy_progress_window(self):
        if self.progress_window:
            self.progress_window.destroy()
            self.progress_window = None
            self.progress_label = None

    def validate_websites(self, quit_after=False):
        # Create a separate thread for the validation process
        validation_thread = threading.Thread(target=self.validate_websites_threaded, args=(True if quit_after else False,))
        validation_thread.daemon = True
        validation_thread.start()
            # Create progress window
        self.create_progress_window()

    def generate_cleaned_websites(self, input_file: TextIO, chunk_size: int) -> Generator[Tuple[set[str], set[str], int], Any, None]:
        start_index: int  = 0

        while True:
            current_chunk = list(islice(input_file, chunk_size))
            if not any(current_chunk):
                break  # End of file

            cleaned_websites: Set[str] = set()
            error_sites: Set[str] = set()

            for website in current_chunk:
                if not website:
                    break  # End of file within the chunk

                cleaned_site, error_site = self.process_single_website(website)
                if cleaned_site:
                    cleaned_websites.add(cleaned_site)
                if error_site:
                    error_sites.add(error_site)

            start_index += chunk_size
            yield cleaned_websites, error_sites, start_index

    def validate_websites_threaded(self, quit_after=False):
        total_lines = self.total_lines

        # Determine dynamic chunk size based on total lines
        if total_lines <= 50000:
            chunk_size = total_lines
        elif total_lines <= 500000:
            chunk_size = int(total_lines * 0.5)
        elif total_lines <= 1000000:
            chunk_size = int(total_lines * 0.1)
        elif total_lines <= 10000000:
            chunk_size = int(total_lines * 0.005)
        else:
            chunk_size = int(total_lines * 0.002)


        error_sites_full: Set[str] = set()
        with(
            open(self.websites_path, 'r', buffering=(2<<16) + 8, encoding="ascii") as input_file,
            tempfile.NamedTemporaryFile('w', buffering=(2<<16) + 8, encoding="ascii", delete=False) as output_file
        ):
            for cleaned_websites, error_sites, start_index in self.generate_cleaned_websites(input_file, chunk_size):
                # Update progress and handle other logic as needed
                self.progress = start_index
                self.update_progress_label()

                # Save the batch of cleaned websites to the temporary output file
                output_file.writelines(cleaned_websites)

                # Accumulate lines with errors
                error_sites_full.update(error_sites)

        # Sort and check duplicates after the file is formed
        # Replace the original file with the temporary output file
        os.replace(output_file.name, self.websites_path)

        if error_sites_full and len(error_sites_full) > 0:
            # Insert lines with errors at the top of the file
            self.update_progress_label("Sorting websites, Please wait...")

            with open(self.websites_path, 'r', buffering=(2<<16) + 8, encoding="ascii") as sorted_file:
                sorted_content = sorted_file.read()

            with open(self.websites_path, 'w', buffering=(2<<16) + 8, encoding="ascii") as sorted_file:
                sorted_file.write('\n'.join(error_sites_full) + '\n' + sorted_content)
        if not quit_after:
            self.open_websites_file(True)
            self.destroy_progress_window()
        else:
            self.root.destroy()
    
    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About App")
        about_window.geometry("450x300")
        about_window.resizable(0, 0)

        # Center the window on the screen
        about_window.geometry(f"+{self.position_x + 25}+{self.position_y - 100}")

        # Set a custom font for the title
        title_font = (("Segoe UI", "Helvetica"), 22, "bold")

        # Create a Label for the app name
        app_name_label = ttk.Label(
            about_window, text="WebsiteDB Editor", font=title_font, padding=(20)
            )
        app_name_label.pack()

        # Create a Separator bar
        separator = ttk.Separator(about_window, orient="horizontal")
        separator.pack(fill="x", padx=20, pady=5)

        # About text
        about_text = (
            f"Made by May113\n\n"
            f"WebsiteDB Editor is a tool designed for managing a database of websites.\n"
            f"Add, validate, and journal website entries with error and version information.\n\n"
            f"App Version: {__version__}"
            f"  Tkinter Version: {tk.TkVersion}"
            f"  Python Version: {sys.version.split()[0]}\n"
            f"Working Directory: {os.getcwd()}\n\n"
            f"Copyright (c) 2023 May113. All rights reserved.\n"
            f"This work is licensed under the terms of the MIT license.\n"
            f"For a copy, see https://opensource.org/licenses/MIT"
        )

        about_label = ttk.Label(
            about_window, text=about_text, justify="left", padding=5
        )
        about_label.pack()

    def save_and_quit(self):
        if self.needs_cleanup:
            self.validate_websites(True)
        else:    
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WebsiteCheckerGUI(root)
    root.mainloop()
