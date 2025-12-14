import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.font import Font
import threading
import queue
import os
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import webbrowser

# Import your existing selenium downloader functions
# Ensure cli.py is in the same directory
try:
    from cli import (
        setup_driver, scrape_links, click_download_button, 
        check_file_exists, get_filename_from_url, read_urls_from_txt
    )
except ImportError:
    # Fallback for testing UI without the cli module
    def setup_driver(*args, **kwargs): return None
    def scrape_links(*args): return []
    def click_download_button(*args): return True
    def check_file_exists(*args): return False
    def get_filename_from_url(url): return "test_file.zip"
    def read_urls_from_txt(*args): return []

class DownloadStatus:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DownloadItem:
    def __init__(self, url: str, filename: str = None):
        self.url = url
        self.filename = filename or get_filename_from_url(url) or url[:50]
        self.status = DownloadStatus.PENDING
        self.progress = 0
        self.size = 0
        self.checksum = None
        self.error = None
        self.start_time = None
        self.end_time = None


class DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🔥 Repack Manager")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 700)
        
        # --- THEME COLORS (VS Code Style) ---
        self.colors = {
            'bg_dark': '#1e1e1e',       # Main Background
            'bg_panel': '#252526',      # Panel/Container Background
            'fg_primary': '#cccccc',    # Main Text
            'fg_secondary': '#858585',  # Subtitle/Log Text
            'accent': '#007acc',        # Blue Accent
            'accent_hover': '#0098ff',  # Blue Highlight
            'success': '#4ec9b0',       # Soft Green
            'warning': '#dcdcaa',       # Soft Yellow
            'error': '#f48771',         # Soft Red
            'border': '#3e3e42',        # Border Color
            'entry_bg': '#3c3c3c',      # Input Field Background
            'select_bg': '#094771'      # Selection Background
        }

        # Apply main background immediately
        self.root.configure(bg=self.colors['bg_dark'])

        # Queue for thread-safe GUI updates
        self.gui_queue = queue.Queue()
        
        # Download state
        self.download_items: List[DownloadItem] = []
        self.is_downloading = False
        self.driver = None
        self.download_thread = None
        
        # Settings
        self.settings = {
            'headless': True,
            'session_refresh': 10,
            'max_wait': 20,
            'delay_between': 2.0,
            'verify_checksum': True,
            'clean_crdownload': True
        }
        
        self.configure_styles()
        self.setup_ui()
        self.load_settings()
        self.check_queue()

    def configure_styles(self):
        """Configure TTK styles for a Flat Dark Theme"""
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' provides the most control over colors

        # General Styles
        style.configure('.', 
            background=self.colors['bg_dark'], 
            foreground=self.colors['fg_primary'],
            font=('Segoe UI', 10)
        )

        # Label Frames
        style.configure('TLabelframe', 
            background=self.colors['bg_dark'], 
            relief='solid', 
            borderwidth=1,
            bordercolor=self.colors['border']
        )
        style.configure('TLabelframe.Label', 
            background=self.colors['bg_dark'], 
            foreground=self.colors['accent'],
            font=('Segoe UI', 11, 'bold')
        )

        # Frames
        style.configure('TFrame', background=self.colors['bg_dark'])
        style.configure('Panel.TFrame', background=self.colors['bg_panel'])

        # Buttons (Flat Modern)
        style.configure('TButton', 
            background=self.colors['entry_bg'],
            foreground='white',
            borderwidth=0,
            padding=8,
            font=('Segoe UI', 10)
        )
        style.map('TButton', 
            background=[('active', self.colors['accent']), ('pressed', self.colors['select_bg'])],
            foreground=[('active', 'white')]
        )

        # Accent Button
        style.configure('Accent.TButton', 
            background=self.colors['accent'],
            foreground='white',
            font=('Segoe UI', 10, 'bold')
        )
        style.map('Accent.TButton', 
            background=[('active', self.colors['accent_hover']), ('pressed', self.colors['select_bg'])]
        )

        # Entries
        style.configure('TEntry', 
            fieldbackground=self.colors['entry_bg'],
            foreground='white',
            insertcolor='white',
            borderwidth=1,
            relief='flat'
        )

        # Treeview (The Queue Table)
        style.configure('Treeview', 
            background=self.colors['bg_dark'],
            fieldbackground=self.colors['bg_dark'],
            foreground=self.colors['fg_primary'],
            borderwidth=0,
            rowheight=25,
            font=('Segoe UI', 10)
        )
        style.map('Treeview', background=[('selected', self.colors['select_bg'])])
        
        style.configure('Treeview.Heading', 
            background=self.colors['bg_panel'],
            foreground=self.colors['fg_primary'],
            relief='flat',
            font=('Segoe UI', 9, 'bold'),
            padding=5
        )

        # Progress Bar
        style.configure('TProgressbar', 
            background=self.colors['accent'], 
            troughcolor=self.colors['entry_bg'],
            borderwidth=0
        )

        # Checkbuttons
        style.configure('TCheckbutton', 
            background=self.colors['bg_dark'],
            foreground=self.colors['fg_primary'],
            indicatorcolor=self.colors['entry_bg']
        )
        style.map('TCheckbutton', indicatorcolor=[('selected', self.colors['accent'])])

    def setup_ui(self):
        """Create the main UI"""
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['bg_panel'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Header line accent
        tk.Frame(header_frame, bg=self.colors['accent'], height=2).pack(side=tk.BOTTOM, fill=tk.X)
        
        title_label = tk.Label(
            header_frame, 
            text="Repack Manager",
            font=('Segoe UI', 16, 'bold'),
            fg='white',
            bg=self.colors['bg_panel'],
            pady=10
        )
        title_label.pack()
        
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_container, style='Panel.TFrame')
        main_container.add(left_panel, weight=1)
        
        # Right panel - Queue and Logs
        right_panel = ttk.Frame(main_container, style='Panel.TFrame')
        main_container.add(right_panel, weight=3)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
        
        # Status bar
        self.setup_status_bar()
        
    def setup_left_panel(self, parent):
        """Setup control panel"""
        # Container frame for left side padding
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Input section
        input_frame = ttk.LabelFrame(container, text="INPUT SOURCE", padding=15)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        
        # URL input
        ttk.Label(input_frame, text="Main Page URL").pack(anchor=tk.W, pady=(0,5))
        self.url_entry = ttk.Entry(input_frame, width=40)
        self.url_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Text file input
        ttk.Label(input_frame, text="URLs Text File").pack(anchor=tk.W, pady=(0,5))
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.txt_file_var = tk.StringVar()
        txt_entry = ttk.Entry(file_frame, textvariable=self.txt_file_var)
        txt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="Browse", width=8, command=self.browse_txt_file).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Output directory
        ttk.Label(input_frame, text="Output Directory").pack(anchor=tk.W, pady=(0,5))
        output_frame = ttk.Frame(input_frame)
        output_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(output_frame, text="Browse", width=8, command=self.browse_output_dir).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Load URLs button
        load_btn = ttk.Button(input_frame, text="🔍 SCAN / LOAD URLS", command=self.load_urls)
        load_btn.pack(fill=tk.X, pady=(5, 0))
        
        # Settings section
        settings_frame = ttk.LabelFrame(container, text="CONFIGURATION", padding=15)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Headless Mode (Hidden)", variable=self.headless_var).pack(anchor=tk.W, pady=2)
        
        self.checksum_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Verify File Integrity", variable=self.checksum_var).pack(anchor=tk.W, pady=2)
        
        self.clean_cr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Auto-clean .crdownload", variable=self.clean_cr_var).pack(anchor=tk.W, pady=2)
        
        # Session refresh
        refresh_frame = ttk.Frame(settings_frame)
        refresh_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(refresh_frame, text="Restart Browser Every:").pack(side=tk.LEFT)
        self.session_refresh_var = tk.IntVar(value=10)
        spin = ttk.Spinbox(refresh_frame, from_=5, to=50, textvariable=self.session_refresh_var, width=5)
        spin.pack(side=tk.RIGHT)
        ttk.Label(refresh_frame, text="files").pack(side=tk.RIGHT, padx=5)
        
        # Actions section
        actions_frame = ttk.LabelFrame(container, text="CONTROLS", padding=15)
        actions_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_btn = ttk.Button(actions_frame, text="▶ START DOWNLOADS", command=self.start_downloads, style='Accent.TButton')
        self.start_btn.pack(fill=tk.X, pady=4)
        
        # HBox for pause/stop
        control_hbox = ttk.Frame(actions_frame)
        control_hbox.pack(fill=tk.X, pady=4)
        
        self.pause_btn = ttk.Button(control_hbox, text="PAUSE", command=self.pause_downloads, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,2))
        
        self.stop_btn = ttk.Button(control_hbox, text="STOP", command=self.stop_downloads, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2,0))
        
        ttk.Button(actions_frame, text="Open Folder", command=self.open_output_folder).pack(fill=tk.X, pady=4)
        
        # Statistics
        stats_frame = ttk.LabelFrame(container, text="STATISTICS", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # Styled Text widget for stats
        self.stats_text = tk.Text(
            stats_frame, 
            height=8, 
            width=30,
            wrap=tk.WORD, 
            font=('Consolas', 9),
            bg=self.colors['bg_panel'],
            fg=self.colors['fg_primary'],
            bd=0,
            highlightthickness=0,
            state=tk.DISABLED
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.update_statistics()
        
    def setup_right_panel(self, parent):
        """Setup queue and log panel"""
        container = ttk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Queue section
        queue_frame = ttk.LabelFrame(container, text="DOWNLOAD QUEUE", padding=5)
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Treeview for queue
        columns = ('filename', 'status', 'progress', 'size')
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show='headings', selectmode='browse')
        
        # Configure headings
        self.queue_tree.heading('filename', text='File Name', anchor=tk.W)
        self.queue_tree.heading('status', text='Status', anchor=tk.W)
        self.queue_tree.heading('progress', text='Progress', anchor=tk.CENTER)
        self.queue_tree.heading('size', text='Size', anchor=tk.E)
        
        self.queue_tree.column('filename', width=300)
        self.queue_tree.column('status', width=120)
        self.queue_tree.column('progress', width=100, anchor=tk.CENTER)
        self.queue_tree.column('size', width=80, anchor=tk.E)
        
        # Scrollbar
        queue_scroll = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        queue_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags for status colors
        self.queue_tree.tag_configure('pending', foreground=self.colors['fg_secondary'])
        self.queue_tree.tag_configure('downloading', foreground=self.colors['accent'])
        self.queue_tree.tag_configure('completed', foreground=self.colors['success'])
        self.queue_tree.tag_configure('failed', foreground=self.colors['error'])
        self.queue_tree.tag_configure('skipped', foreground=self.colors['warning'])
        
        # Log section
        log_frame = ttk.LabelFrame(container, text="ACTIVITY LOG", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=10,
            font=('Consolas', 9),
            bg='#000000', # Slightly darker for log terminal feel
            fg=self.colors['fg_primary'],
            insertbackground='white',
            bd=0,
            highlightthickness=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags
        self.log_text.tag_config('info', foreground=self.colors['accent'])
        self.log_text.tag_config('success', foreground=self.colors['success'])
        self.log_text.tag_config('warning', foreground=self.colors['warning'])
        self.log_text.tag_config('error', foreground=self.colors['error'])
        self.log_text.tag_config('timestamp', foreground=self.colors['fg_secondary'])
        
    def setup_status_bar(self):
        """Setup bottom status bar"""
        status_frame = tk.Frame(self.root, bg=self.colors['accent'], height=30)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready",
            anchor=tk.W,
            padx=15,
            bg=self.colors['accent'],
            fg='white',
            font=('Segoe UI', 9)
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_bar = ttk.Progressbar(
            status_frame,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=15, pady=5)

    def update_statistics(self):
        """Update statistics display"""
        total = len(self.download_items)
        completed = sum(1 for item in self.download_items if item.status == DownloadStatus.COMPLETED)
        failed = sum(1 for item in self.download_items if item.status == DownloadStatus.FAILED)
        skipped = sum(1 for item in self.download_items if item.status == DownloadStatus.SKIPPED)
        pending = sum(1 for item in self.download_items if item.status == DownloadStatus.PENDING)
        downloading = sum(1 for item in self.download_items if item.status == DownloadStatus.DOWNLOADING)
        
        rate = (completed/(total or 1))*100
        
        stats = f"""
 TOTAL FILES : {total}
 ──────────────────────
 COMPLETED   : {completed}
 DOWNLOADING : {downloading}
 PENDING     : {pending}
 SKIPPED     : {skipped}
 FAILED      : {failed}
 ──────────────────────
 SUCCESS RATE: {rate:.1f}%
        """
        
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats)
        self.stats_text.config(state=tk.DISABLED)

    # -------------------------------------------------------------------------
    #  LOGIC METHODS (Unchanged functionality, slightly adapted for styling)
    # -------------------------------------------------------------------------

    def browse_txt_file(self):
        filename = filedialog.askopenfilename(
            title="Select URLs Text File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            self.txt_file_var.set(filename)
            
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_var.set(directory)
            
    def log(self, message: str, level: str = 'info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f'{timestamp} ', 'timestamp')
        self.log_text.insert(tk.END, f'{message}\n', level)
        self.log_text.see(tk.END)
        
    def update_status(self, message: str):
        self.status_label.config(text=message)
        
    def load_urls(self):
        urls = []
        
        # Load from text file
        txt_file = self.txt_file_var.get()
        if txt_file and os.path.exists(txt_file):
            urls.extend(read_urls_from_txt(txt_file))
            self.log(f"Loaded {len(urls)} URLs from text file", 'success')
        
        # Scrape from main page
        main_url = self.url_entry.get().strip()
        if main_url:
            self.log("Scraping main page...", 'info')
            
            # Run scraping in a separate thread to prevent UI freezing
            def scrape_worker():
                try:
                    # Temporary driver just for scraping
                    temp_dir = Path(self.output_var.get() or "./downloads")
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.gui_queue.put(('status', "Initializing scraper..."))
                    driver = setup_driver(temp_dir, headless=True)
                    
                    self.gui_queue.put(('status', f"Scraping {main_url}..."))
                    scraped = scrape_links(driver, main_url)
                    
                    driver.quit()
                    self.gui_queue.put(('scrape_result', scraped))
                except Exception as e:
                    self.gui_queue.put(('log', f"Error scraping: {e}", 'error'))
                    self.gui_queue.put(('status', "Scraping failed"))

            threading.Thread(target=scrape_worker, daemon=True).start()
            return
            
        if not urls and not main_url:
            messagebox.showwarning("No Input", "Please provide a text file or URL.")
            return

        self.process_loaded_urls(urls)

    def process_loaded_urls(self, urls):
        urls = list(dict.fromkeys(urls)) # Deduplicate
        self.download_items.clear()
        for url in urls:
            item = DownloadItem(url)
            self.download_items.append(item)
        
        self.update_queue_display()
        self.update_statistics()
        self.log(f"Queue populated with {len(self.download_items)} items", 'success')
        
    def update_queue_display(self):
        # Clear existing
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add items
        for idx, item in enumerate(self.download_items, 1):
            size_str = f"{item.size:.1f} MB" if item.size > 0 else "-"
            progress_str = f"{item.progress}%" if item.progress > 0 else "-"
            
            # Status icon mapping
            status_map = {
                DownloadStatus.PENDING: "⏳",
                DownloadStatus.DOWNLOADING: "⬇",
                DownloadStatus.COMPLETED: "✔",
                DownloadStatus.FAILED: "✖",
                DownloadStatus.SKIPPED: "⏭"
            }
            s_icon = status_map.get(item.status, "")
            
            self.queue_tree.insert(
                '',
                tk.END,
                text=str(idx),
                values=(item.filename, f"{s_icon} {item.status.upper()}", progress_str, size_str),
                tags=(item.status,)
            )
        
    def calculate_checksum(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.log(f"Checksum error: {e}", 'error')
            return None
    
    def start_downloads(self):
        if not self.download_items:
            messagebox.showwarning("No Items", "Queue is empty. Load URLs first.")
            return
        
        output_dir = self.output_var.get()
        if not output_dir:
            messagebox.showwarning("No Output", "Please select an output directory.")
            return
        
        self.is_downloading = True
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Starting batch download...", 'info')
        
        self.download_thread = threading.Thread(target=self.download_worker, daemon=True)
        self.download_thread.start()
        
    def download_worker(self):
        download_dir = Path(self.output_var.get())
        download_dir.mkdir(parents=True, exist_ok=True)
        
        if self.clean_cr_var.get():
            self.gui_queue.put(('log', 'Cleaning temp files...', 'info'))
            for file in os.listdir(download_dir):
                if file.endswith(('.crdownload', '.part', '.tmp')):
                    try:
                        os.remove(download_dir / file)
                    except: pass
        
        try:
            self.driver = setup_driver(
                download_dir,
                headless=self.headless_var.get(),
            )
            
            downloads_since_refresh = 0
            session_refresh = self.session_refresh_var.get()
            
            for idx, item in enumerate(self.download_items):
                if not self.is_downloading:
                    break
                
                # Check exist
                existing = check_file_exists(download_dir, item.url)
                if existing and not existing.endswith(('.crdownload', '.part')):
                    item.status = DownloadStatus.SKIPPED
                    file_path = download_dir / existing
                    if file_path.exists():
                        item.size = os.path.getsize(file_path) / (1024 * 1024)
                    self.gui_queue.put(('log', f"Skipped (exists): {item.filename}", 'warning'))
                    self.gui_queue.put(('update_queue', None))
                    self.gui_queue.put(('progress', int((idx/len(self.download_items))*100)))
                    continue

                # Refresh session logic
                if downloads_since_refresh >= session_refresh:
                    self.gui_queue.put(('log', 'Refreshing browser session...', 'info'))
                    self.driver.quit()
                    time.sleep(1)
                    self.driver = setup_driver(download_dir, headless=self.headless_var.get())
                    downloads_since_refresh = 0

                # Start Download
                item.status = DownloadStatus.DOWNLOADING
                item.start_time = time.time()
                self.gui_queue.put(('status', f"Downloading: {item.filename}"))
                self.gui_queue.put(('update_queue', None))
                
                result = click_download_button(self.driver, item.url, download_dir)
                
                if result is True:
                    item.status = DownloadStatus.COMPLETED
                    downloads_since_refresh += 1
                    
                    downloaded = check_file_exists(download_dir, item.url)
                    if downloaded:
                        file_path = download_dir / downloaded
                        item.size = os.path.getsize(file_path) / (1024 * 1024)
                        
                        if self.checksum_var.get():
                            self.gui_queue.put(('log', f'Verifying: {downloaded}', 'info'))
                            item.checksum = self.calculate_checksum(str(file_path))
                            
                        self.gui_queue.put(('log', f"Success: {item.filename}", 'success'))
                else:
                    item.status = DownloadStatus.FAILED
                    self.gui_queue.put(('log', f"Failed: {item.filename}", 'error'))
                
                item.end_time = time.time()
                self.gui_queue.put(('update_queue', None))
                self.gui_queue.put(('update_stats', None))
                self.gui_queue.put(('progress', int(((idx+1)/len(self.download_items))*100)))
                
        except Exception as e:
            self.gui_queue.put(('log', f"Critical Error: {e}", 'error'))
        finally:
            if self.driver:
                self.driver.quit()
            self.gui_queue.put(('download_complete', None))

    def pause_downloads(self):
        self.is_downloading = False
        self.pause_btn.config(state=tk.DISABLED)
        self.log("Pausing after current download...", 'warning')
        
    def stop_downloads(self):
        self.is_downloading = False
        self.log("Stopping all operations...", 'error')
        if self.driver:
            try: self.driver.quit()
            except: pass
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        
    def open_output_folder(self):
        output_dir = self.output_var.get()
        if output_dir and os.path.exists(output_dir):
            if os.name == 'nt': os.startfile(output_dir)
            else: os.system(f'xdg-open "{output_dir}"')
            
    def check_queue(self):
        try:
            while True:
                msg_type, *args = self.gui_queue.get_nowait()
                
                if msg_type == 'log': self.log(*args)
                elif msg_type == 'status': self.update_status(args[0])
                elif msg_type == 'progress': self.progress_bar['value'] = args[0]
                elif msg_type == 'update_queue': self.update_queue_display()
                elif msg_type == 'update_stats': self.update_statistics()
                elif msg_type == 'scrape_result': self.process_loaded_urls(args[0])
                elif msg_type == 'download_complete': self.on_download_complete()
                    
        except queue.Empty:
            pass
        self.root.after(100, self.check_queue)
        
    def on_download_complete(self):
        self.is_downloading = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 100
        self.update_status("Batch operation complete")
        self.log("All operations finished", 'success')
        
    def load_settings(self):
        try:
            if os.path.exists('downloader_settings.json'):
                with open('downloader_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.output_var.set(settings.get('output_dir', ''))
                    self.headless_var.set(settings.get('headless', True))
                    self.session_refresh_var.set(settings.get('session_refresh', 10))
        except: pass
        
    def save_settings(self):
        try:
            settings = {
                'output_dir': self.output_var.get(),
                'headless': self.headless_var.get(),
                'session_refresh': self.session_refresh_var.get()
            }
            with open('downloader_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except: pass

def main():
    root = tk.Tk()

    
    # --- ADD THIS BLOCK ---
    try:
        # Use a high-quality png (e.g., 64x64 or 128x128)
        icon_image = tk.PhotoImage(file='app.png')
        root.iconphoto(True, icon_image)
    except Exception as e:
        print(f"Icon image not found: {e}")
    # ----------------------

    # Configure global font...
    default_font = Font(family="Segoe UI", size=10)
    root.option_add("*Font", default_font)
    
    app = DownloaderGUI(root)
    
    def on_closing():
        app.save_settings()
        if app.is_downloading:
            if messagebox.askokcancel("Quit", "Downloads in progress. Quit anyway?"):
                app.stop_downloads()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()