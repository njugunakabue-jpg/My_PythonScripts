"""
Photo Diagnostics Tool
Analyze photos to diagnose date extraction issues
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Error: Pillow not installed. Run: pip install pillow")
    exit(1)


def diagnose_photo_date(file_path: Path) -> dict:
    """
    Diagnose date extraction for a single photo
    
    Returns:
        Dictionary with diagnostic information
    """
    info = {
        'filename': file_path.name,
        'path': str(file_path),
        'extension': file_path.suffix.lower(),
        'exists': file_path.exists(),
        'size_bytes': None,
        'file_mod_time': None,
        'exif_data': None,
        'exif_datetime_tags': {},
        'extracted_date': None,
        'extracted_source': None,
        'errors': []
    }
    
    if not file_path.exists():
        info['errors'].append('File does not exist')
        return info
    
    try:
        info['size_bytes'] = file_path.stat().st_size
        mod_time = file_path.stat().st_mtime
        info['file_mod_time'] = datetime.fromtimestamp(mod_time).strftime("%Y:%m:%d %H:%M:%S")
    except Exception as e:
        info['errors'].append(f"Error reading file stats: {e}")
    
    # Check if it's a CR3 file (Canon RAW)
    if file_path.suffix.lower() == '.cr3':
        info['exif_data'] = "CR3 (Canon RAW) - Pillow does not support this format"
        info['errors'].append("CR3 files require special RAW image library (piexif or rawpy)")
    else:
        # Try to read EXIF
        try:
            image = Image.open(file_path)
            
            # Try modern Pillow API
            try:
                exif_data = image.getexif()
                if exif_data:
                    info['exif_data'] = f"Found {len(exif_data)} EXIF tags"
                    
                    # Extract all datetime-related tags
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if 'date' in tag_name.lower() or 'time' in tag_name.lower():
                            info['exif_datetime_tags'][tag_name] = value
                            
                            # Try to parse common datetime tags
                            if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                try:
                                    dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    info['extracted_date'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                                    info['extracted_source'] = f"EXIF - {tag_name}"
                                except (ValueError, TypeError):
                                    info['errors'].append(f"Could not parse {tag_name}: {value}")
                else:
                    info['exif_data'] = "No EXIF data found"
            except AttributeError:
                info['errors'].append("getexif() not available, trying fallback method")
                try:
                    exif_data = image._getexif()
                    if exif_data:
                        info['exif_data'] = f"Found {len(exif_data)} EXIF tags (via _getexif)"
                        for tag_id, value in exif_data.items():
                            tag_name = TAGS.get(tag_id, tag_id)
                            if 'date' in tag_name.lower() or 'time' in tag_name.lower():
                                info['exif_datetime_tags'][tag_name] = value
                                if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                    try:
                                        dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                        info['extracted_date'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                                        info['extracted_source'] = f"EXIF (fallback) - {tag_name}"
                                    except (ValueError, TypeError):
                                        info['errors'].append(f"Could not parse {tag_name}: {value}")
                    else:
                        info['exif_data'] = "No EXIF data found (via fallback)"
                except Exception as e:
                    info['errors'].append(f"Error reading EXIF (fallback): {e}")
        
        except Exception as e:
            info['errors'].append(f"Error opening image: {e}")
    
    # If no date found from EXIF, use file modification time
    if not info['extracted_date'] and info['file_mod_time']:
        info['extracted_date'] = info['file_mod_time']
        info['extracted_source'] = "File Modification Time"
    
    return info


def run_diagnostics(folder_path: str):
    """Run diagnostics on all photos in a folder"""
    
    path = Path(folder_path).expanduser()
    
    if not path.exists():
        print(f"Error: Folder does not exist: {folder_path}")
        return
    
    if not path.is_dir():
        print(f"Error: Path is not a directory: {folder_path}")
        return
    
    # Find all photo files
    extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.heic', '.heif', '.cr3', '.nef', '.arw', '.dng', '.rw2', '.orf', '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm')
    photo_files_set = set()
    for ext in extensions:
        photo_files_set.update(path.glob(f'*{ext}'))
        photo_files_set.update(path.glob(f'*{ext.upper()}'))
    
    photo_files = sorted(photo_files_set)
    
    if not photo_files:
        print(f"No photos found in {path}")
        return
    
    print(f"Analyzing {len(photo_files)} photo(s) in: {path}\n")
    print("=" * 100)
    
    successful = 0
    failed = 0
    cr3_files = 0
    
    for photo_file in sorted(photo_files):
        info = diagnose_photo_date(photo_file)
        
        # Print file info
        print(f"\nFile: {info['filename']}")
        print(f"  Extension: {info['extension']}")
        print(f"  Size: {info['size_bytes']} bytes")
        print(f"  File Mod Time: {info['file_mod_time']}")
        print(f"  EXIF Data: {info['exif_data']}")
        
        if info['exif_datetime_tags']:
            print(f"  DateTime Tags Found:")
            for tag_name, tag_value in info['exif_datetime_tags'].items():
                print(f"    - {tag_name}: {tag_value}")
        
        if info['extracted_date']:
            print(f"  [OK] Extracted Date: {info['extracted_date']}")
            print(f"       Source: {info['extracted_source']}")
            successful += 1
        else:
            print(f"  [FAIL] NO DATE FOUND")
            failed += 1
        
        if 'CR3 (Canon RAW)' in str(info['exif_data']):
            cr3_files += 1
        
        if info['errors']:
            print(f"  Errors/Warnings:")
            for error in info['errors']:
                print(f"    - {error}")
    
    print(f"\n{'=' * 100}")
    print(f"Summary:")
    print(f"  Successfully extracted dates: {successful}")
    print(f"  Failed to extract dates: {failed}")
    print(f"  CR3 (Canon RAW) files found: {cr3_files}")
    print(f"  Total files: {len(photo_files)}")
    
    if cr3_files > 0:
        print(f"\n[NOTE] CR3 files cannot be read by Pillow (standard Python image library).")
        print(f"       To handle CR3 files, you would need additional libraries like:")
        print(f"       - piexif: pip install piexif (for EXIF data only, CR3 format not supported)")
        print(f"       - rawpy: pip install rawpy (experimental CR3 support)")
        print(f"       - Canon's Digital Photo Professional (external tool)")
        print(f"\n       As a workaround, your app will use file modification time for CR3 files.")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = r'C:\Users\tnjug\OneDrive\Pictures\Cannon'
    
    run_diagnostics(folder)
