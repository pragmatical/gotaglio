import os
from pathlib import Path

from ..constants import log_folder
import time

def show_history():
  records = get_files_sorted_by_creation(log_folder)
  for r in records:
      local_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r[1]))
      print(f"{r[0]}: {local_time}")


def get_files_sorted_by_creation(folder_path):
    """
    Get a list of file names in a folder, sorted by creation date.

    Args:
        folder_path (str or Path): Path to the folder.

    Returns:
        list: File names sorted by creation date.
    """
    # Ensure the folder path is a Path object
    folder = Path(folder_path)

    # Get a list of files in the folder (excluding directories)
    files = [(f.stem, f.stat().st_birthtime) for f in folder.iterdir() if f.is_file()]

    # Sort files by creation time
    sorted_files = sorted(files, key=lambda f: f[1])
    # sorted_files = sorted(files, key=lambda f: f.stat().st_birthtime)

    # Return only the file names
    # return [f.name for f in sorted_files]
    return sorted_files
