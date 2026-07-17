"""
Rewrite Homebrew placeholder paths in Mach-O binaries.

Homebrew bottles contain placeholder paths like:
    @@HOMEBREW_PREFIX@@
    @@HOMEBREW_CELLAR@@

These need to be replaced with actual paths before the
binaries will work. We rewrite them to point to the pacman
install root's usr/ directory.

Uses install_name_tool for dylib references.
Uses sed for text files (e.g., .pc files).
"""

from __future__ import annotations

import subprocess
from pathlib import Path


# Homebrew placeholders found in bottle binaries
HOMEBREW_PLACEHOLDERS = [
    "@@HOMEBREW_PREFIX@@",
    "@@HOMEBREW_CELLAR@@",
]


def is_macho(path: Path) -> bool:
    """Check if a file is a Mach-O binary."""
    if not path.is_file() or path.is_symlink():
        return False

    try:
        with open(path, "rb") as f:
            magic = f.read(4)
            # Mach-O magic numbers
            return magic in (
                b"\xfe\xed\xfa\xce",  # MH_MAGIC (32-bit)
                b"\xfe\xed\xfa\xcf",  # MH_MAGIC_64 (64-bit)
                b"\xce\xfa\xed\xfe",  # MH_CIGAM (32-bit, reversed)
                b"\xcf\xfa\xed\xfe",  # MH_CIGAM_64 (64-bit, reversed)
                b"\xca\xfe\xba\xbe",  # FAT_MAGIC (universal)
            )
    except (OSError, PermissionError):
        return False


def get_dylib_refs(binary: Path) -> list[str]:
    """Get all dylib references from a Mach-O binary."""
    proc = subprocess.run(
        ["otool", "-L", str(binary)],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return []

    refs = []
    for line in proc.stdout.splitlines()[1:]:
        line = line.strip()
        if line:
            # Format: "path (compatibility ...)"
            path = line.split(" (")[0].strip()
            refs.append(path)

    return refs


def get_rpath(binary: Path) -> list[str]:
    """Get rpaths from a Mach-O binary."""
    proc = subprocess.run(
        ["otool", "-l", str(binary)],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        return []

    rpaths = []
    lines = proc.stdout.splitlines()
    for i, line in enumerate(lines):
        if "cmd LC_RPATH" in line:
            # Next non-empty line with "path" has the rpath
            for j in range(i + 1, min(i + 5, len(lines))):
                if "path " in lines[j]:
                    rpath = lines[j].strip().split("path ")[1].split(" (")[0]
                    rpaths.append(rpath)
                    break

    return rpaths


def rewrite_binary(
    binary: Path,
    install_root: str,
    formula_name: str = "",
) -> int:
    """
    Rewrite Homebrew placeholders in a single Mach-O binary.

    Returns the number of changes made.
    """
    changes = 0

    # Get current dylib refs
    refs = get_dylib_refs(binary)

    for ref in refs:
        new_ref = None

        for placeholder in HOMEBREW_PLACEHOLDERS:
            if placeholder in ref:
                # Replace @@HOMEBREW_PREFIX@@/opt/<pkg>/lib/libfoo.dylib
                # with <install_root>/usr/lib/libfoo.dylib
                #
                # Also replace @@HOMEBREW_CELLAR@@/<pkg>/<ver>/lib/libfoo.dylib
                # with <install_root>/usr/lib/libfoo.dylib

                # Extract just the library filename
                lib_name = Path(ref).name

                # For lib/ references, use the install root's lib dir
                if "/lib/" in ref or ref.endswith(".dylib"):
                    new_ref = f"{install_root}/usr/lib/{lib_name}"
                elif "/bin/" in ref:
                    new_ref = f"{install_root}/usr/bin/{lib_name}"
                else:
                    new_ref = f"{install_root}/usr/lib/{lib_name}"

                break

        if new_ref and new_ref != ref:
            cmd = [
                "install_name_tool",
                "-change", ref, new_ref,
                str(binary),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                changes += 1

    # Also fix the install name (LC_ID_DYLIB) if this is a dylib
    if binary.suffix in (".dylib",) or ".dylib" in binary.name:
        refs_self = get_dylib_refs(binary)
        if refs_self:
            # First ref is the install name
            id_ref = refs_self[0] if refs_self else None
            if id_ref:
                for placeholder in HOMEBREW_PLACEHOLDERS:
                    if placeholder in id_ref:
                        lib_name = Path(id_ref).name
                        new_id = f"{install_root}/usr/lib/{lib_name}"

                        subprocess.run(
                            [
                                "install_name_tool",
                                "-id", new_id,
                                str(binary),
                            ],
                            capture_output=True,
                            text=True,
                        )
                        changes += 1
                        break

    # Fix rpaths
    rpaths = get_rpath(binary)
    for rpath in rpaths:
        for placeholder in HOMEBREW_PLACEHOLDERS:
            if placeholder in rpath:
                # Remove the old rpath with placeholder
                subprocess.run(
                    [
                        "install_name_tool",
                        "-delete_rpath", rpath,
                        str(binary),
                    ],
                    capture_output=True,
                    text=True,
                )
                changes += 1
                break

    return changes


def rewrite_text_files(
    directory: Path,
    install_root: str,
) -> int:
    """
    Rewrite Homebrew placeholders in text files (.pc, .la, etc.)

    Returns the number of files modified.
    """
    changes = 0

    text_extensions = {
        ".pc", ".la", ".cmake", ".pri", ".prl",
        ".cfg", ".conf", ".sh",
    }

    for path in directory.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue

        if path.suffix not in text_extensions:
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        original = content

        for placeholder in HOMEBREW_PLACEHOLDERS:
            if placeholder in content:
                content = content.replace(
                    placeholder,
                    install_root,
                )

        if content != original:
            path.write_text(content, encoding="utf-8")
            changes += 1

    return changes


def rewrite_stage(
    stage_dir: Path,
    install_root: str = "/Users/revanthnemtoo/pacman/root",
    formula_name: str = "",
) -> dict:
    """
    Rewrite all Homebrew placeholders in a staged package.

    Returns a summary of changes made.
    """
    stage_dir = Path(stage_dir)
    install_root = install_root.rstrip("/")

    binary_changes = 0
    text_changes = 0

    # Rewrite Mach-O binaries
    for path in stage_dir.rglob("*"):
        if is_macho(path):
            n = rewrite_binary(path, install_root, formula_name)
            if n > 0:
                binary_changes += n

    # Rewrite text config files
    text_changes = rewrite_text_files(stage_dir, install_root)

    total = binary_changes + text_changes

    if total > 0:
        print(f"  -> Rewrote {binary_changes} binary refs, {text_changes} text files")
    else:
        print("  -> No Homebrew placeholders found")

    return {
        "binary_changes": binary_changes,
        "text_changes": text_changes,
    }
