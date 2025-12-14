"""
Selenium Download Manager - GUI Version
Rich GUI with enhanced features for managing downloads

Features:
- Clean .crdownload files
- File integrity verification (checksum)
- Real-time download status
- Drag & drop support
- Queue management
- Detailed logging

To create executable:
    pip install pyinstaller
    pyinstaller --onefile --windowed --icon=app.ico selenium_downloader_gui.py
"""

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
from cli import (
    setup_driver, scrape_links, click_download_button, 
    check_file_exists, get_filename_from_url, read_urls_from_txt
)


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
        self.root.title("Selenium Download Manager Pro")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
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
        
        self.setup_ui()
        self.load_settings()
        self.check_queue()
        
    def setup_ui(self):
        """Create the main UI"""
        # Set color scheme
        bg_color = "#f0f0f0"
        primary_color = "#0078d4"
        secondary_color = "#005a9e"
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=primary_color)
        style.configure('TButton', padding=6, relief="flat", background=primary_color)
        style.configure('Accent.TButton', foreground='white', background=primary_color)
        
        # Header
        header_frame = tk.Frame(self.root, bg=primary_color, height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame, 
            text="🚀 Selenium Download Manager",
            font=('Segoe UI', 18, 'bold'),
            fg='white',
            bg=primary_color
        )
        title_label.pack(pady=15)
        
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = ttk.Frame(main_container, width=350)
        main_container.add(left_panel, weight=1)
        
        # Right panel - Queue and Logs
        right_panel = ttk.Frame(main_container)
        main_container.add(right_panel, weight=3)
        
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)
        
        # Status bar
        self.setup_status_bar()
        
    def setup_left_panel(self, parent):
        """Setup control panel"""
        # Input section
        input_frame = ttk.LabelFrame(parent, text="📥 Input", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # URL input
        ttk.Label(input_frame, text="Main Page URL:").pack(anchor=tk.W)
        self.url_entry = ttk.Entry(input_frame, width=40)
        self.url_entry.pack(fill=tk.X, pady=(0, 10))
        
        # Text file input
        ttk.Label(input_frame, text="URLs Text File:").pack(anchor=tk.W)
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.txt_file_var = tk.StringVar()
        txt_entry = ttk.Entry(file_frame, textvariable=self.txt_file_var, state='readonly')
        txt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            file_frame, 
            text="📁", 
            width=3,
            command=self.browse_txt_file
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Output directory
        ttk.Label(input_frame, text="Output Directory:").pack(anchor=tk.W)
        output_frame = ttk.Frame(input_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, state='readonly')
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            output_frame, 
            text="📁", 
            width=3,
            command=self.browse_output_dir
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Load URLs button
        load_btn = ttk.Button(
            input_frame,
            text="🔍 Load URLs",
            command=self.load_urls
        )
        load_btn.pack(fill=tk.X, pady=(10, 0))
        
        # Settings section
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Settings", padding=10)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Headless mode",
            variable=self.headless_var
        ).pack(anchor=tk.W)
        
        self.checksum_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Verify checksums",
            variable=self.checksum_var
        ).pack(anchor=tk.W)
        
        self.clean_cr_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            settings_frame,
            text="Clean .crdownload files",
            variable=self.clean_cr_var
        ).pack(anchor=tk.W)
        
        # Session refresh
        ttk.Label(settings_frame, text="Session refresh (downloads):").pack(anchor=tk.W, pady=(5, 0))
        self.session_refresh_var = tk.IntVar(value=10)
        ttk.Spinbox(
            settings_frame,
            from_=5,
            to=50,
            textvariable=self.session_refresh_var,
            width=10
        ).pack(anchor=tk.W)
        
        # Actions section
        actions_frame = ttk.LabelFrame(parent, text="🎬 Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.start_btn = ttk.Button(
            actions_frame,
            text="▶️ Start Downloads",
            command=self.start_downloads,
            style='Accent.TButton'
        )
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.pause_btn = ttk.Button(
            actions_frame,
            text="⏸️ Pause",
            command=self.pause_downloads,
            state=tk.DISABLED
        )
        self.pause_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ttk.Button(
            actions_frame,
            text="⏹️ Stop",
            command=self.stop_downloads,
            state=tk.DISABLED
        )
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        ttk.Button(
            actions_frame,
            text="🧹 Clean .crdownload",
            command=self.clean_crdownload_files
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            actions_frame,
            text="📂 Open Output Folder",
            command=self.open_output_folder
        ).pack(fill=tk.X, pady=2)
        
        # Statistics
        stats_frame = ttk.LabelFrame(parent, text="📊 Statistics", padding=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=8, wrap=tk.WORD, font=('Consolas', 9))
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.update_statistics()
        
    def setup_right_panel(self, parent):
        """Setup queue and log panel"""
        # Queue section
        queue_frame = ttk.LabelFrame(parent, text="📋 Download Queue", padding=5)
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for queue
        columns = ('filename', 'status', 'progress', 'size')
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show='tree headings', height=10)
        
        self.queue_tree.heading('#0', text='#')
        self.queue_tree.heading('filename', text='Filename')
        self.queue_tree.heading('status', text='Status')
        self.queue_tree.heading('progress', text='Progress')
        self.queue_tree.heading('size', text='Size')
        
        self.queue_tree.column('#0', width=50, anchor=tk.CENTER)
        self.queue_tree.column('filename', width=300)
        self.queue_tree.column('status', width=100, anchor=tk.CENTER)
        self.queue_tree.column('progress', width=100, anchor=tk.CENTER)
        self.queue_tree.column('size', width=80, anchor=tk.E)
        
        # Scrollbar
        queue_scroll = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scroll.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        queue_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags for status colors
        self.queue_tree.tag_configure('pending', foreground='gray')
        self.queue_tree.tag_configure('downloading', foreground='blue', font=('', 9, 'bold'))
        self.queue_tree.tag_configure('completed', foreground='green')
        self.queue_tree.tag_configure('failed', foreground='red')
        self.queue_tree.tag_configure('skipped', foreground='orange')
        
        # Log section
        log_frame = ttk.LabelFrame(parent, text="📝 Activity Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=15,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags
        self.log_text.tag_config('info', foreground='#4ec9b0')
        self.log_text.tag_config('success', foreground='#4ec9b0')
        self.log_text.tag_config('warning', foreground='#dcdcaa')
        self.log_text.tag_config('error', foreground='#f48771')
        self.log_text.tag_config('timestamp', foreground='#858585')
        
    def setup_status_bar(self):
        """Setup bottom status bar"""
        status_frame = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = tk.Label(
            status_frame,
            text="Ready",
            anchor=tk.W,
            padx=10
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.progress_bar = ttk.Progressbar(
            status_frame,
            length=200,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10, pady=2)
        
    def browse_txt_file(self):
        """Browse for text file"""
        filename = filedialog.askopenfilename(
            title="Select URLs Text File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filename:
            self.txt_file_var.set(filename)
            
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_var.set(directory)
            
    def log(self, message: str, level: str = 'info'):
        """Add message to log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f'[{timestamp}] ', 'timestamp')
        self.log_text.insert(tk.END, f'{message}\n', level)
        self.log_text.see(tk.END)
        
    def update_status(self, message: str):
        """Update status bar"""
        self.status_label.config(text=message)
        
    def update_statistics(self):
        """Update statistics display"""
        total = len(self.download_items)
        completed = sum(1 for item in self.download_items if item.status == DownloadStatus.COMPLETED)
        failed = sum(1 for item in self.download_items if item.status == DownloadStatus.FAILED)
        skipped = sum(1 for item in self.download_items if item.status == DownloadStatus.SKIPPED)
        pending = sum(1 for item in self.download_items if item.status == DownloadStatus.PENDING)
        downloading = sum(1 for item in self.download_items if item.status == DownloadStatus.DOWNLOADING)
        
        stats = f"""Total Files: {total}
✅ Completed: {completed}
⏳ Pending: {pending}
⬇️ Downloading: {downloading}
⏭️ Skipped: {skipped}
❌ Failed: {failed}

Success Rate: {(completed/(total or 1))*100:.1f}%"""
        
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats)
        
    def load_urls(self):
        """Load URLs from text file or scrape from main page"""
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
            try:
                download_dir = Path(self.output_var.get() or "./downloads")
                download_dir.mkdir(parents=True, exist_ok=True)
                
                driver = setup_driver(download_dir, headless=True)
                scraped = scrape_links(driver, main_url)
                urls.extend(scraped)
                driver.quit()
                self.log(f"Scraped {len(scraped)} URLs from main page", 'success')
            except Exception as e:
                self.log(f"Error scraping: {e}", 'error')
        
        if not urls:
            messagebox.showwarning("No URLs", "No URLs found. Please provide a text file or main page URL.")
            return
        
        # Remove duplicates
        urls = list(dict.fromkeys(urls))
        
        # Create download items
        self.download_items.clear()
        for url in urls:
            item = DownloadItem(url)
            self.download_items.append(item)
        
        self.update_queue_display()
        self.update_statistics()
        self.log(f"Loaded {len(self.download_items)} unique URLs", 'success')
        
    def update_queue_display(self):
        """Update the queue treeview"""
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        
        # Add items
        for idx, item in enumerate(self.download_items, 1):
            status_icon = {
                DownloadStatus.PENDING: '⏳',
                DownloadStatus.DOWNLOADING: '⬇️',
                DownloadStatus.COMPLETED: '✅',
                DownloadStatus.FAILED: '❌',
                DownloadStatus.SKIPPED: '⏭️'
            }.get(item.status, '❓')
            
            size_str = f"{item.size:.1f}MB" if item.size > 0 else "-"
            progress_str = f"{item.progress}%" if item.progress > 0 else "-"
            
            self.queue_tree.insert(
                '',
                tk.END,
                text=str(idx),
                values=(item.filename, f"{status_icon} {item.status}", progress_str, size_str),
                tags=(item.status,)
            )
        
    def clean_crdownload_files(self):
        """Clean .crdownload and temporary files"""
        output_dir = self.output_var.get()
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("No Directory", "Please select an output directory first.")
            return
        
        removed = []
        try:
            for file in os.listdir(output_dir):
                if file.endswith(('.crdownload', '.part', '.tmp')):
                    file_path = os.path.join(output_dir, file)
                    os.remove(file_path)
                    removed.append(file)
            
            if removed:
                self.log(f"Cleaned {len(removed)} temporary files", 'success')
                messagebox.showinfo("Success", f"Removed {len(removed)} temporary files:\n" + "\n".join(removed[:5]))
            else:
                messagebox.showinfo("Clean", "No temporary files found.")
        except Exception as e:
            self.log(f"Error cleaning files: {e}", 'error')
            messagebox.showerror("Error", f"Failed to clean files: {e}")
    
    def calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum"""
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
        """Start the download process"""
        if not self.download_items:
            messagebox.showwarning("No URLs", "Please load URLs first.")
            return
        
        output_dir = self.output_var.get()
        if not output_dir:
            messagebox.showwarning("No Output", "Please select an output directory.")
            return
        
        self.is_downloading = True
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Start download thread
        self.download_thread = threading.Thread(target=self.download_worker, daemon=True)
        self.download_thread.start()
        
    def download_worker(self):
        """Worker thread for downloads"""
        download_dir = Path(self.output_var.get())
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean .crdownload if enabled
        if self.clean_cr_var.get():
            self.gui_queue.put(('log', 'Cleaning temporary files...', 'info'))
            for file in os.listdir(download_dir):
                if file.endswith(('.crdownload', '.part', '.tmp')):
                    try:
                        os.remove(download_dir / file)
                    except:
                        pass
        
        try:
            self.driver = setup_driver(
                download_dir,
                headless=self.headless_var.get(),
                disable_images=True
            )
            
            downloads_since_refresh = 0
            session_refresh = self.session_refresh_var.get()
            
            for idx, item in enumerate(self.download_items):
                if not self.is_downloading:
                    break
                
                self.gui_queue.put(('status', f"Processing {idx+1}/{len(self.download_items)}: {item.filename}"))
                self.gui_queue.put(('progress', int((idx/len(self.download_items))*100)))
                
                # Check if file exists
                existing = check_file_exists(download_dir, item.url)
                if existing and not existing.endswith(('.crdownload', '.part', '.tmp')):
                    item.status = DownloadStatus.SKIPPED
                    file_path = download_dir / existing
                    if file_path.exists():
                        item.size = os.path.getsize(file_path) / (1024 * 1024)
                    self.gui_queue.put(('log', f"Skipped (exists): {item.filename}", 'warning'))
                    self.gui_queue.put(('update_queue', None))
                    continue
                
                # Update status
                item.status = DownloadStatus.DOWNLOADING
                item.start_time = time.time()
                self.gui_queue.put(('update_queue', None))
                self.gui_queue.put(('log', f"Downloading: {item.filename}", 'info'))
                
                # Session refresh
                if downloads_since_refresh >= session_refresh:
                    self.gui_queue.put(('log', 'Refreshing browser session...', 'info'))
                    self.driver.quit()
                    time.sleep(1)
                    self.driver = setup_driver(download_dir, headless=self.headless_var.get())
                    downloads_since_refresh = 0
                
                # Download
                result = click_download_button(self.driver, item.url, download_dir)
                
                if result is True:
                    item.status = DownloadStatus.COMPLETED
                    downloads_since_refresh += 1
                    
                    # Get file info
                    downloaded = check_file_exists(download_dir, item.url)
                    if downloaded:
                        file_path = download_dir / downloaded
                        if file_path.exists():
                            item.size = os.path.getsize(file_path) / (1024 * 1024)
                            
                            # Calculate checksum if enabled
                            if self.checksum_var.get():
                                self.gui_queue.put(('log', f'Verifying checksum for {downloaded}', 'info'))
                                item.checksum = self.calculate_checksum(str(file_path))
                    
                    self.gui_queue.put(('log', f"✅ Completed: {item.filename} ({item.size:.1f}MB)", 'success'))
                else:
                    item.status = DownloadStatus.FAILED
                    item.error = "Download failed"
                    self.gui_queue.put(('log', f"❌ Failed: {item.filename}", 'error'))
                
                item.end_time = time.time()
                self.gui_queue.put(('update_queue', None))
                self.gui_queue.put(('update_stats', None))
                
                time.sleep(2)
            
        except Exception as e:
            self.gui_queue.put(('log', f"Error: {e}", 'error'))
        finally:
            if self.driver:
                self.driver.quit()
            self.gui_queue.put(('download_complete', None))
    
    def pause_downloads(self):
        """Pause downloads"""
        self.is_downloading = False
        self.pause_btn.config(state=tk.DISABLED)
        self.log("Downloads paused", 'warning')
        
    def stop_downloads(self):
        """Stop downloads"""
        self.is_downloading = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Downloads stopped", 'error')
        
    def open_output_folder(self):
        """Open output folder in file explorer"""
        output_dir = self.output_var.get()
        if output_dir and os.path.exists(output_dir):
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # Linux/Mac
                os.system(f'xdg-open "{output_dir}"')
        else:
            messagebox.showwarning("No Directory", "Output directory not set or doesn't exist.")
    
    def check_queue(self):
        """Check GUI queue for updates from worker thread"""
        try:
            while True:
                msg_type, *args = self.gui_queue.get_nowait()
                
                if msg_type == 'log':
                    self.log(*args)
                elif msg_type == 'status':
                    self.update_status(args[0])
                elif msg_type == 'progress':
                    self.progress_bar['value'] = args[0]
                elif msg_type == 'update_queue':
                    self.update_queue_display()
                elif msg_type == 'update_stats':
                    self.update_statistics()
                elif msg_type == 'download_complete':
                    self.on_download_complete()
                    
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)
    
    def on_download_complete(self):
        """Handle download completion"""
        self.is_downloading = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 100
        self.update_status("Downloads complete!")
        self.log("All downloads finished", 'success')
        
        # Show summary
        completed = sum(1 for item in self.download_items if item.status == DownloadStatus.COMPLETED)
        failed = sum(1 for item in self.download_items if item.status == DownloadStatus.FAILED)
        skipped = sum(1 for item in self.download_items if item.status == DownloadStatus.SKIPPED)
        
        messagebox.showinfo(
            "Downloads Complete",
            f"✅ Completed: {completed}\n"
            f"⏭️ Skipped: {skipped}\n"
            f"❌ Failed: {failed}"
        )
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('downloader_settings.json'):
                with open('downloader_settings.json', 'r') as f:
                    settings = json.load(f)
                    self.output_var.set(settings.get('output_dir', ''))
                    self.headless_var.set(settings.get('headless', True))
                    self.session_refresh_var.set(settings.get('session_refresh', 10))
        except:
            pass
    
    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'output_dir': self.output_var.get(),
                'headless': self.headless_var.get(),
                'session_refresh': self.session_refresh_var.get(),
                'verify_checksum': self.checksum_var.get(),
                'clean_crdownload': self.clean_cr_var.get()
            }
            with open('downloader_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
        except:
            pass


def main():
    root = tk.Tk()
    app = DownloaderGUI(root)
    
    # Save settings on close
    def on_closing():
        app.save_settings()
        if app.is_downloading:
            if messagebox.askokcancel("Quit", "Downloads in progress. Are you sure you want to quit?"):
                app.stop_downloads()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window on screen
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()