import os

def remove_file_force(path):
    try:
        os.remove(path)
        print(f"Deleted: {path}")
    except FileNotFoundError:
        print(f"File not found (already removed): {path}")
    except PermissionError:
        print(f"Permission denied: {path}")
    except Exception as e:
        print(f"Error deleting {path}: {e}")

remove_file_force("slides.mp4")