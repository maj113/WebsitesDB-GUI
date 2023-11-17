import re
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

__version__ = "v0.0.1"

class WebsiteCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WebsiteDB Editor")
        self.root.minsize(500, 80)
        self.root.resizable(0, 0)

        position_x = int((self.root.winfo_screenwidth()) / 3)
        position_y = int((self.root.winfo_screenheight()) / 3)
        self.root.geometry(f"+{position_x}+{position_y}")

        # Create a uniform grid
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self.websites = self.load_websites()

        self.website_entry = self.create_entry_with_backdrop(root, "Enter website URL", width=40)
        self.error_entry = self.create_entry_with_backdrop(root, "error reason", width=12)
        self.version_entry = self.create_entry_with_backdrop(root, "version", width=12)

        self.website_entry.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
        self.error_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.version_entry.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

        tk.Button(root, text="Add Website", command=self.add_website).grid(row=1, column=0, padx=10, pady=10, sticky="sw")
        tk.Button(root, text="List Websites", command=self.list_websites).grid(row=1, column=0, padx=100, pady=10, sticky="sw")
        tk.Button(root, text="Save & Quit", command=self.save_and_quit).grid(row=1, column=2, padx=10, pady=10, sticky="se")

        menubar = tk.Menu(root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save & Quit", command=self.save_and_quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About App", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        root.config(menu=menubar)

    def load_websites(self) -> list[str]:
        try:
            with open("websites.txt", "r") as file:
                websites = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            websites = []
        return websites

    def save_websites(self):
        with open("websites.txt", "w") as file:
            for website in self.websites:
                file.write(f"{website}\n")

    def create_entry_with_backdrop(self, parent, backdrop_text, width=25):
        entry = tk.Entry(parent, width=width, justify='left', fg='grey')
        entry.insert(0, backdrop_text)
        entry.configure(insertwidth=1)

        def on_click(event):
            if entry.get() == backdrop_text:
                entry.delete(0, tk.END)
                entry.configure(fg='black', justify='left', insertwidth=1)

        def on_leave(event):
            if not entry.get() or entry.get() == backdrop_text:
                entry.insert(0, backdrop_text)
                entry.configure(fg='grey', justify='left', insertwidth=0)

        entry.bind('<FocusIn>', on_click)
        entry.bind('<FocusOut>', on_leave)

        return entry

    def add_website(self):
        website = self.website_entry.get().strip()
        error_reason = self.error_entry.get().strip()[:12]
        version = self.version_entry.get().strip()[:12]

        if website and website != "Enter website URL":
            website = "https://" + website if not website.startswith(("https://", "http://")) else website
            error_reason = error_reason if error_reason != "error reason" else ""
            version = version if version != "version" else ""

            website_status = f"{website} #{error_reason} on {version}" if error_reason or version else website

            if any(website in w for w in self.websites):
                messagebox.showinfo("Duplicate Website", "This website is already in the list.")
                return

            if error_reason:
                self.websites.insert(0, website_status)
            else:
                self.websites.append(website_status)

            self.websites.sort(key=lambda x: (not ' #' in x, x.lower()))
            self.save_websites()
            self.clear_entry_fields(website=True, error=True)

            messagebox.showinfo("Website Added", "Website has been added to the list.")
        else:
            messagebox.showwarning("Invalid Input", "Please enter a valid website URL.")

    def clear_entry_fields(self, website=False, error=False):
        if website:
            self.website_entry.delete(0, tk.END)
            self.website_entry.configure(fg='grey', justify='left', insertwidth=0)

    def list_websites(self):
        # Create a Toplevel window for listing websites
        list_window = tk.Toplevel(self.root)
        list_window.title(f"List of Websites - {len(self.websites)} Websites")
        list_window.minsize(600, 400)

        # Create a Treeview for displaying websites, errors, and tested on
        tree = ttk.Treeview(list_window, columns=("Website", "Error", "Tested On"), show="headings", height=20)
        tree.pack(expand=True, fill="both")

        # Set column headers
        tree.heading("Website", text="Website")
        tree.heading("Error", text="Error")
        tree.heading("Tested On", text="Tested On")

        # Set column widths
        tree.column("Website", width=300)
        tree.column("Error", width=50)
        tree.column("Tested On", width=50)

        # Insert data into the Treeview
        for website in self.websites:
            # Split each line into website, error, and tested on
            parts = website.split(' #', 1)
            website_name = parts[0].strip()
            error = parts[1].strip() if len(parts) > 1 else ""
            tested_on = ""

            # Check if there is any error, and extract the tested on information
            if " #" in website:
                tested_parts = error.split(' on ', 1)
                error = parts[1].split(' on ', 1)[0].strip()
                tested_on = tested_parts[1].strip() if len(tested_parts) > 1 else ""

            # Insert the data into the Treeview
            tree.insert("", "end", values=(website_name, error, tested_on))

        # Create a Scrollbar
        scrollbar = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")

        # Configure the Treeview to use the Scrollbar
        tree.configure(yscrollcommand=scrollbar.set)

    def validate_websites(self):
        cleaned_websites = set()

        for index, website in enumerate(self.websites, start=1):
            if index % 100 == 0:
                self.root.title(f"WebsiteDB Editor - Cleaning Duplicates - {index}/{len(self.websites)}")

            # Use a regular expression for URL validation
            if not re.match(r'https?://', website):
                website = "https://" + website

            # Split the website into parts and extract error reason and version information
            parts = re.split(r' #| on ', website, maxsplit=2)
            error_reason = parts[1][:12] if len(parts) > 1 else ''
            version_info = f" on {parts[2][:12]}" if len(parts) > 2 else ''

            # Construct the cleaned website string and strip any leading or trailing spaces
            cleaned_website = (
                f"{parts[0]} {'#' + error_reason if error_reason else ''}"
                f"{version_info if version_info else ''}".strip()
            )
            cleaned_websites.add(cleaned_website)

        self.websites = sorted(cleaned_websites, key=lambda x: (not ' #' in x, x.lower()))
        self.root.title("WebsiteDB Editor")

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About App")
        about_window.geometry("450x300")
        about_window.resizable(0, 0)

        # Center the window on the screen
        position_x = int((about_window.winfo_screenwidth()) / 3 + 25)
        position_y = int((about_window.winfo_screenheight()) / 3 - 100)
        about_window.geometry(f"+{position_x}+{position_y}")

        # Set a custom font for the title
        title_font = (("Segoe UI", "Helvetica"), 22, "bold")

        # Create a Label for the app name
        app_name_label = tk.Label(about_window, text="WebsiteDB Editor", font=title_font, pady=20)
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

        about_label = tk.Label(about_window, text=about_text, padx=20, pady=20, justify="left")
        about_label.pack()

    def save_and_quit(self):
        self.validate_websites()
        self.save_websites()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = WebsiteCheckerGUI(root)
    root.mainloop()
