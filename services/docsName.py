
import re
from datetime import datetime
from pathlib import Path


def generate_path(
    folder,
    prefix="worksummary",
    extension=".xlsx",
    companion_extensions=(),
    now=None,
):
    """this provide a timestamped path """
    folder = Path(folder)
    cleaned_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", str(prefix)).strip("._-")
    if not cleaned_prefix:
        cleaned_prefix = "worksummary"
    extension = extension if extension.startswith(".") else f".{extension}"
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    base = f"{cleaned_prefix}_{timestamp}"
    candidate = folder / f"{base}{extension}"
    # The unsuffixed filename is version 1; collisions start at version 2.
    version = 2
    def path_is_taken(path):
        if path.exists():
            return True
        return any((path.parent / f"{path.stem}{suffix}").exists() for suffix in companion_extensions)

    while path_is_taken(candidate):
        candidate = folder / f"{base}_{version}{extension}"
        version += 1
    return candidate
