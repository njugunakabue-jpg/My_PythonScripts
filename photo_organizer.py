"""
Photo Organizer GUI
Organize camera photos and videos into folders by the date they were taken.

A Tkinter GUI application that:
- Extracts EXIF date-taken metadata from photos
- Extracts creation date from videos using file metadata
- Organizes them into year/month/day folder structures
- Falls back to file modification date if EXIF data is unavailable
- Shows progress with a progress bar and log window

Supported Formats:
    Photos: JPG, JPEG, PNG, HEIC, HEIF, BMP, GIF, WebP, TIFF
    RAW: CR3, NEF, ARW, DNG, RW2, ORF (Canon, Nikon, Sony, etc.)
    Videos: MP4, MOV, AVI, MKV, FLV, WMV, WebM

Requirements:
    - pillow (PIL): pip install pillow
    - tkinter (included with Python)
"""

import os
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def get_photo_date(file_path: Path) -> Optional[Tuple[datetime, str]]:
    """
    Extract the date a photo/video was taken from EXIF metadata or file modification time.
    
    Args:
        file_path: Path to the image or video file
        
    Returns:
        Tuple of (datetime object, source_method) or (None, None) if unable to determine date
        source_method: "EXIF", "File Modified Time", or "Video File Time"
    
    Supports:
        - Photos: JPG, PNG, HEIC, BMP, GIF, WebP, TIFF, RAW formats (CR3, NEF, ARW, etc.)
        - Videos: MP4, MOV, AVI, MKV, FLV, WMV, WebM
    """
    # Try to get EXIF date first (works for photos and some videos)
    if PILLOW_AVAILABLE:
        try:
            image = Image.open(file_path)
            
            # Try modern Pillow API first (v8.1+)
            try:
                exif_data = image.getexif()
                if exif_data:
                    # Common EXIF tags for datetime
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            try:
                                # EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
                                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S"), "EXIF"
                            except (ValueError, TypeError):
                                continue
            except AttributeError:
                # Fall back to older API
                exif_data = image._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            try:
                                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S"), "EXIF"
                            except (ValueError, TypeError):
                                continue
        except Exception as e:
            # Silently continue to file modification time fallback
            pass
    
    # Fall back to file modification time (used for videos and files without EXIF)
    try:
        mod_time = file_path.stat().st_mtime
        date_source = "Video File Time" if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'] else "File Modified Time"
        return datetime.fromtimestamp(mod_time), date_source
    except OSError:
        return None


def organize_photos(
    source_dir: str,
    destination_dir: str,
    move_files: bool = True,
    date_format: str = "ymd",
    supported_extensions: Tuple[str, ...] = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.heic', '.heif', '.cr3', '.nef', '.arw', '.dng', '.rw2', '.orf', '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm'),
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    should_stop_callback: Optional[Callable[[], bool]] = None
) -> Tuple[int, int]:
    """
    Organize photos from source directory into destination directory by date.
    
    Args:
        source_dir: Path to directory containing photos
        destination_dir: Path to destination root directory
        move_files: If True, move files; if False, copy files
        date_format: Folder structure format ('ymd', 'ym', or 'y')
        supported_extensions: Tuple of file extensions to process
        log_callback: Optional function to call with log messages
        progress_callback: Optional function to call with (current, total)
        should_stop_callback: Optional function that returns True if processing should stop
        
    Returns:
        Tuple of (organized_count, skipped_count)
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
    
    def should_stop():
        return should_stop_callback() if should_stop_callback else False
    
    source_path = Path(source_dir).expanduser()
    dest_path = Path(destination_dir).expanduser()
    
    # Validate source directory
    if not source_path.exists():
        log(f"Error: Source directory does not exist: {source_path}")
        return 0, 0
    
    if not source_path.is_dir():
        log(f"Error: Source path is not a directory: {source_path}")
        return 0, 0
    
    # Create destination directory
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"Error: Could not create destination directory: {e}")
        return 0, 0
    
    # Find all photo files
    photo_files_set = set()
    for ext in supported_extensions:
        photo_files_set.update(source_path.glob(f'*{ext}'))
        photo_files_set.update(source_path.glob(f'*{ext.upper()}'))
    
    photo_files = sorted(photo_files_set)
    
    if not photo_files:
        log(f"No photos found in {source_path}")
        return 0, 0
    
    log(f"Found {len(photo_files)} photo(s) to organize")
    log(f"{'Moving' if move_files else 'Copying'} to: {dest_path}\n")
    
    organized_count = 0
    skipped_count = 0
    
    for idx, photo_file in enumerate(sorted(photo_files)):
        # Check if user requested stop
        if should_stop():
            log("\nProcess stopped by user")
            break
        
        # Update progress
        if progress_callback:
            progress_callback(idx, len(photo_files))
        
        try:
            # Get the date the photo was taken
            result = get_photo_date(photo_file)
            
            if result is None or result[0] is None:
                log(f"⚠ Skipped (no date found): {photo_file.name}")
                skipped_count += 1
                continue
            
            photo_date, date_source = result
            
            # Create folder path based on date format
            if date_format == 'ymd':
                folder_path = dest_path / f"{photo_date.year}" / f"{photo_date.month:02d}" / f"{photo_date.day:02d}"
            elif date_format == 'ym':
                folder_path = dest_path / f"{photo_date.year}" / f"{photo_date.month:02d}"
            elif date_format == 'y':
                folder_path = dest_path / f"{photo_date.year}"
            else:
                log(f"Error: Invalid date format '{date_format}'. Use 'ymd', 'ym', or 'y'.")
                return organized_count, skipped_count
            
            # Create folder if it doesn't exist
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Move or copy file
            destination_file = folder_path / photo_file.name
            
            # Handle duplicate filenames
            if destination_file.exists():
                base_name = photo_file.stem
                extension = photo_file.suffix
                counter = 1
                while destination_file.exists():
                    destination_file = folder_path / f"{base_name}_{counter}{extension}"
                    counter += 1
            
            if move_files:
                shutil.move(str(photo_file), str(destination_file))
            else:
                shutil.copy2(str(photo_file), str(destination_file))
            
            date_str = photo_date.strftime("%Y-%m-%d")
            log(f"✓ {photo_file.name} → {date_str}/ ({date_source})")
            organized_count += 1
            
        except Exception as e:
            log(f"✗ Error processing {photo_file.name}: {e}")
            skipped_count += 1
    
    # Final progress update
    if progress_callback:
        progress_callback(len(photo_files), len(photo_files))
    
    log(f"\n{'='*60}")
    log(f"Organized: {organized_count} photo(s)")
    log(f"Skipped: {skipped_count} photo(s)")
    log(f"Done!")
    
    return organized_count, skipped_count


class PhotoOrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Organizer")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        self.source_dir = tk.StringVar(value=r'C:\Users\tnjug\OneDrive\Pictures\Camera Roll')
        self.dest_dir = tk.StringVar(value=r'C:\Users\tnjug\OneDrive\Pictures\Camera Roll')
        self.date_format = tk.StringVar(value='ymd')
        self.move_mode = tk.BooleanVar(value=True)
        
        self.processing = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the GUI components"""
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Source directory
        ttk.Label(main_frame, text="Source Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.source_dir, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=5)
        
        # Destination directory
        ttk.Label(main_frame, text="Destination Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.dest_dir, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_dest).grid(row=1, column=2, padx=5)
        
        # Date format
        format_frame = ttk.LabelFrame(main_frame, text="Folder Structure", padding="5")
        format_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Radiobutton(format_frame, text="YYYY/MM/DD (default)", variable=self.date_format, value='ymd').pack(anchor=tk.W)
        ttk.Radiobutton(format_frame, text="YYYY/MM", variable=self.date_format, value='ym').pack(anchor=tk.W)
        ttk.Radiobutton(format_frame, text="YYYY", variable=self.date_format, value='y').pack(anchor=tk.W)
        
        # File operation
        ttk.Checkbutton(main_frame, text="Move files (unchecked = copy)", variable=self.move_mode).grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Start button
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Organizing", command=self.start_process)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack(anchor=tk.W, padx=5)
        
        # Log window
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.log_text = ScrolledText(log_frame, height=15, width=80, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
    
    def browse_source(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory")
        if directory:
            self.source_dir.set(directory)
    
    def browse_dest(self):
        """Browse for destination directory"""
        directory = filedialog.askdirectory(title="Select Destination Directory")
        if directory:
            self.dest_dir.set(directory)
    
    def log(self, message: str):
        """Add message to log window"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update()
    
    def update_progress(self, current: int, total: int):
        """Update progress bar"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_var.set(percentage)
            self.progress_label.config(text=f"Processing: {current}/{total} files")
        self.root.update()
    
    def start_process(self):
        """Start organizing photos in a background thread"""
        if not self.source_dir.get() or not self.dest_dir.get():
            messagebox.showerror("Error", "Please select both source and destination directories")
            return
        
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.progress_var.set(0)
        self.progress_label.config(text="Starting...")
        
        # Run in background thread to prevent GUI freeze
        thread = threading.Thread(target=self.process_photos, daemon=True)
        thread.start()
    
    def process_photos(self):
        """Process photos (runs in background thread)"""
        try:
            organized, skipped = organize_photos(
                source_dir=self.source_dir.get(),
                destination_dir=self.dest_dir.get(),
                move_files=self.move_mode.get(),
                date_format=self.date_format.get(),
                log_callback=self.log,
                progress_callback=self.update_progress,
                should_stop_callback=lambda: not self.processing
            )
            
            if self.processing:
                messagebox.showinfo("Success", f"Organized: {organized}\nSkipped: {skipped}")
        
        except Exception as e:
            if self.processing:
                messagebox.showerror("Error", f"An error occurred: {e}")
                self.log(f"ERROR: {e}")
        
        finally:
            self.processing = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def stop_process(self):
        """Stop the organizing process"""
        self.processing = False
        self.log("Process stopped by user")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)


def main():
    root = tk.Tk()
    app = PhotoOrganizerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
