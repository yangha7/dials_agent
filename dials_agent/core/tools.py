"""
Shared utilities for DIALS agent tools.

Tool schemas, prompt fragments, and handler logic now live with their
owning skill under `dials_agent/skills/`. This module keeps only the
data-file discovery helpers, which are shared infrastructure used
directly by `ClaudeClient` (to build the dynamic context block) and by
the `data_import` skill — not tied to any single tool call.
"""

import os
from pathlib import Path

# Supported data file extensions for DIALS import
DATA_FILE_EXTENSIONS = {
    ".nxs",      # NeXus files (HDF5-based)
    ".h5",       # HDF5 files
    ".hdf5",     # HDF5 files
    ".cbf",      # Crystallographic Binary Format
    ".img",      # ADSC image files
    ".mccd",     # MAR CCD files
    ".sfrm",     # Bruker frames
    ".osc",      # Oscillation images
}

# dxtbx/DIALS decompresses these transparently on read -- dials.import can be
# pointed directly at e.g. `t1.0001.img.bz2`, no separate decompression step
# needed. (This is distinct from an outer .tar *archive* bundling many such
# files, which does need extracting first -- that's a packaging step, not a
# per-image compression DIALS handles itself.)
COMPRESSED_EXTENSIONS = {".bz2", ".gz"}


def is_recognized_data_file(item: Path) -> bool:
    """
    True if `item` is a diffraction data file DIALS can import directly --
    either matching DATA_FILE_EXTENSIONS itself, or one of those with a
    trailing .bz2/.gz DIALS decompresses on the fly. Path.suffix only ever
    returns the last dotted component, so a compressed file's real "type"
    is the suffix *before* the compression extension (e.g. `.img` in
    `t1.0001.img.bz2`).
    """
    suffix = item.suffix.lower()
    if suffix in DATA_FILE_EXTENSIONS:
        return True
    if suffix in COMPRESSED_EXTENSIONS:
        return item.with_suffix("").suffix.lower() in DATA_FILE_EXTENSIONS
    return False


def directory_has_data_files(directory: Path, max_depth: int = 2) -> bool:
    """Shallow recursive check for any recognized diffraction data file under `directory`."""
    def scan(d: Path, depth: int) -> bool:
        if depth > max_depth:
            return False
        try:
            for item in d.iterdir():
                if item.is_file() and is_recognized_data_file(item):
                    return True
                if item.is_dir() and not item.name.startswith("."):
                    if scan(item, depth + 1):
                        return True
        except PermissionError:
            pass
        return False
    return scan(directory, 0)


def discover_dataset_subdirectories(data_directory: str, max_depth: int = 2) -> list[Path]:
    """
    Find immediate subdirectories of `data_directory` that themselves contain
    a recognized diffraction data file (directly or nested up to max_depth).

    This is the single, shared implementation behind two different callers
    that must never diverge again: auto mode's multi-dataset processing
    (`cli.py`'s `run_auto`) and the `select_dataset` tool used in normal
    conversation when a user names a dataset by keyword rather than a path.
    An earlier version of this check lived duplicated in cli.py and was
    never updated when compressed-image support (.bz2/.gz) was added to
    `is_recognized_data_file` here, so a directory of only .img.bz2 files
    was invisible to multi-dataset discovery -- a real bug found live.
    """
    if not data_directory:
        return []
    base = Path(data_directory)
    if not base.is_dir():
        return []

    found = []
    try:
        for entry in sorted(base.iterdir()):
            if entry.is_dir() and not entry.name.startswith(".") and directory_has_data_files(entry, max_depth):
                found.append(entry)
    except PermissionError:
        pass
    return found


def discover_data_files(
    working_directory: str = ".",
    search_parent: bool = True,
    max_depth: int = 2,
    data_directory: str = "",
    max_files: int = 30,
) -> list[dict[str, str]]:
    """
    Discover diffraction data files that can be imported by DIALS.

    Searches the working directory, the parent directory (files only, not
    recursive), and an explicitly configured data_directory.  Sibling
    directories are intentionally excluded — on a shared RAID they can
    contain thousands of files and blow up the context window.

    Returns at most *max_files* entries so the dynamic context stays small.
    """
    data_files = []
    seen: set = set()
    working_path = Path(working_directory).resolve()

    def add_file(item: Path) -> None:
        resolved = str(item.resolve())
        if resolved in seen:
            return
        seen.add(resolved)
        suffix = item.suffix.lower()
        if suffix in COMPRESSED_EXTENSIONS:
            inner_suffix = item.with_suffix("").suffix.lower()
            type_label = f"{inner_suffix[1:].upper()}.{suffix[1:].upper()}"  # e.g. IMG.BZ2
        else:
            type_label = suffix[1:].upper()
        try:
            rel_path = item.relative_to(working_path)
        except ValueError:
            rel_path = os.path.relpath(item, working_path)
        data_files.append({
            "path": str(rel_path),
            "type": type_label,
            "name": item.name,
            "size_mb": round(item.stat().st_size / (1024 * 1024), 1),
        })

    def scan_directory(directory: Path, current_depth: int = 0) -> None:
        if current_depth > max_depth or len(data_files) >= max_files:
            return
        try:
            for item in sorted(directory.iterdir()):
                if len(data_files) >= max_files:
                    return
                if item.is_file() and is_recognized_data_file(item):
                    add_file(item)
                elif item.is_dir() and not item.name.startswith("."):
                    scan_directory(item, current_depth + 1)
        except PermissionError:
            pass

    # 1. Scan the working directory itself (recursive, up to max_depth)
    scan_directory(working_path)

    # 2. Scan the parent directory — files only, no recursion into siblings.
    #    Siblings can be enormous dataset directories on a shared RAID.
    if search_parent and len(data_files) < max_files:
        parent = working_path.parent
        try:
            for item in sorted(parent.iterdir()):
                if len(data_files) >= max_files:
                    break
                if item.is_file() and is_recognized_data_file(item):
                    add_file(item)
        except PermissionError:
            pass

    # 3. Scan the explicitly configured data directory (recursive).
    if data_directory and len(data_files) < max_files:
        data_path = Path(data_directory).resolve()
        if data_path.exists() and data_path != working_path:
            scan_directory(data_path)

    data_files.sort(key=lambda x: x["path"])
    return data_files


def format_data_files_for_prompt(data_files: list[dict[str, str]]) -> str:
    """
    Format discovered data files into a string for inclusion in the system prompt.

    Args:
        data_files: List of data file info dicts from discover_data_files()

    Returns:
        Formatted string describing available data files
    """
    if not data_files:
        return "No diffraction data files found in the working directory or nearby."

    lines = ["Available diffraction data files:"]
    for f in data_files:
        lines.append(f"- {f['path']} ({f['type']}, {f['size_mb']} MB)")

    return "\n".join(lines)
