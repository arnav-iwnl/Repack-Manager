# 📦 Repacks Downloader

A powerful, automated download manager with a beautiful GUI for downloading files from web pages. Features intelligent link scraping, download tracking, file integrity verification, and a modern dark-themed interface.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

## ✨ Features

- 🎨 **Modern GUI** - Beautiful dark-themed interface with real-time progress tracking
- 🔍 **Smart Link Scraping** - Automatically finds and processes download links
- 📊 **Statistics Dashboard** - Track downloads, failures, and skipped files
- ✅ **File Integrity** - Automatic checksum verification (MD5) for downloaded files
- 🚫 **Incomplete File Detection** - Automatically excludes `.crdownload` files from verification
- 📁 **File Tracking** - See which files were downloaded from which links with extensions
- ⚡ **Session Management** - Automatic browser session refresh to prevent timeouts
- 🎯 **Duplicate Detection** - Smart file existence checking (handles browser duplicate naming)
- 🌈 **Colorful Logs** - Syntax-highlighted output with color-coded messages

## 🚀 Quick Start

### Option 1: Use the Standalone App (Recommended)

1. Download `Repacks.Manager.exe` from [Releases](../../releases)
2. Run the executable - no installation needed!
3. Use the GUI to download files

### Option 2: Run from Source

#### Prerequisites

- Python 3.8 or higher
- Google Chrome or Chromium browser
- Internet connection

#### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Repack-Manager.git
cd repacks-downloader

# Install dependencies
pip install -r requirements.txt

# Optional: Install as package
pip install -e .
```

#### Run the GUI

```bash
python run_gui.py
```

Or as a module:
```bash
python -m repacks_downloader.gui
```

#### Or use the CLI

```bash
python -m repacks_downloader \
  --out "D:/Downloads" \
  --input-txt urls.txt \
  --headless
```

Or if installed:
```bash
repacks-downloader --out "D:/Downloads" --input-txt urls.txt
```

## 📖 Usage

### GUI Mode

1. **Input URLs**: 
   - Load URLs from a `.txt` file (one URL per line), OR
   - Enter a main page URL to scrape for links

2. **Output Folder**: Choose where to save downloads

3. **Options**:
   - **Headless Mode**: Run browser in background (faster)
   - **Don't Block Images**: Enable if site needs images to render
   - **Filter Links**: Filter scraped links to likely download pages

4. **Start Download**: Click "Start Download" and monitor progress!

### CLI Mode

```bash
python -m repacks_downloader --help
```

**Common Options:**
- `--out <path>` (required): Download directory
- `--input-txt <file>`: Text file with URLs (one per line)
- `--url <url>`: Main page URL to scrape for links
- `--headless`: Run browser in headless mode
- `--max-wait <seconds>`: Max wait time for elements (default: 20)
- `--session-refresh <n>`: Restart browser after N downloads (default: 10)
- `--delay-between <seconds>`: Delay between downloads (default: 2.0)

## 🏗️ Building the App

### Windows

```bash
scripts\build_app.bat
```

### Linux/Mac

```bash
chmod +x scripts/build_app.sh
./scripts/build_app.sh
```

The executable will be in the `dist/` folder.

See [docs/BUILD_INSTRUCTIONS.md](docs/BUILD_INSTRUCTIONS.md) for detailed instructions.

## 📁 Project Structure

```
repacks-downloader/
├── src/
│   └── repacks_downloader/        # Main package
│       ├── __init__.py            # Package exports
│       ├── __main__.py            # Module entry point
│       ├── downloader.py          # Core downloader engine
│       ├── gui.py                  # GUI application
│       └── cli.py                 # CLI entry point
├── docs/                           # Documentation
├── scripts/                        # Build scripts
├── examples/                       # Example files
├── tests/                          # Test files
├── run_gui.py                      # GUI launcher
├── setup.py                        # Package setup
├── requirements.txt                # Dependencies
└── README.md                       # This file
```

See [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) for detailed structure.

## 🎯 Features in Detail

### Intelligent Download Detection

- Waits for `.crdownload`, `.part`, `.tmp` files to disappear
- Verifies file size stability before marking as complete
- Handles Chrome's duplicate file naming (`file (1).rar`, etc.)

### File Integrity Verification

- Automatic MD5 checksum calculation
- Excludes incomplete downloads (`.crdownload` files)
- Verifies file integrity after download

### Smart Link Processing

- Multiple fallback selectors for finding download buttons
- Handles JavaScript-rendered content
- Automatic overlay removal
- Session expiration handling

### Rich User Interface

- Real-time progress bars
- Statistics dashboard
- File list with link tracking
- Color-coded log output
- Status indicators

## 🔧 Requirements

### Runtime Requirements

- **Chrome/Chromium** browser (must be installed)
- **Internet connection**

### Development Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## 📦 Dependencies

- `selenium` - Web automation
- `webdriver-manager` - Automatic ChromeDriver management
- `rich` - Beautiful terminal output
- `rarfile` - RAR file support (optional)
- `tkinter` - GUI framework (usually included with Python)

## 🐛 Troubleshooting

### "Chrome not found" error

Install Google Chrome or Chromium:
- [Download Chrome](https://www.google.com/chrome/)

### Downloads not starting

- Check internet connection
- Try disabling headless mode
- Ensure the website doesn't require JavaScript/images
- Increase `--max-wait` timeout

### Antivirus warning

Some antivirus software may flag the executable. This is a false positive. The app is safe to use.

### First run is slow

The app extracts bundled files on first run. Subsequent runs are faster.

### Build fails

- Ensure Python 3.8+ is installed
- Install dependencies: `pip install -r requirements.txt`
- Check that PyInstaller is installed: `pip install pyinstaller`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal and Ethical Use

**Important**: Use this tool only for content you have the legal right to download. Respect:
- Website terms of service
- `robots.txt` files
- Applicable laws in your jurisdiction
- Copyright and intellectual property rights

The authors are not responsible for misuse of this software.

## 🙏 Acknowledgments

- Built with [Selenium](https://www.selenium.dev/)
- Beautiful output powered by [Rich](https://github.com/Textualize/rich)
- GUI built with [Tkinter](https://docs.python.org/3/library/tkinter.html)

## 📧 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the documentation files

---

**Made with ❤️ for efficient file management**

