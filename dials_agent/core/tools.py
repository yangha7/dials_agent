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
        try:
            rel_path = item.relative_to(working_path)
        except ValueError:
            rel_path = os.path.relpath(item, working_path)
        data_files.append({
            "path": str(rel_path),
            "type": suffix[1:].upper(),
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
                if item.is_file() and item.suffix.lower() in DATA_FILE_EXTENSIONS:
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
                if item.is_file() and item.suffix.lower() in DATA_FILE_EXTENSIONS:
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
