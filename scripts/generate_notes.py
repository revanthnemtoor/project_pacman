#!/usr/bin/env python3
"""Generate comprehensive MD5 checksums and pipeline architectural notes."""

import os
import glob
import hashlib
import json

os.makedirs('notes', exist_ok=True)

def calculate_md5(filepath):
    h = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"Error: {e}"

categories = {
    'Root Workspace Python Scripts': sorted(glob.glob('*.py')),
    'builder/src Pipeline Modules': sorted(glob.glob('builder/src/*.py') + glob.glob('builder/src/*.Md') + glob.glob('builder/src/*.md')),
    'fromsource Pipeline Modules': sorted(glob.glob('fromsource/*.py') + glob.glob('fromsource/*.json')),
    'Shell Scripts': sorted(glob.glob('*.sh') + glob.glob('scripts/*.sh'))
}

# 1. Write MD5 Checksums
lines = [
    '# Project Pacman Port: MD5 Checksums & Source Inventory',
    '',
    'This registry records the exact MD5 hashes and file sizes of all build scripts, modules,',
    'and pipeline orchestrators across the project before consolidation into the unified builder.',
    ''
]

for cat_name, file_list in categories.items():
    lines.append(f'## {cat_name}')
    lines.append('')
    lines.append('| File | MD5 Checksum | Size (bytes) | Role / Purpose |')
    lines.append('| :--- | :--- | :--- | :--- |')
    for filepath in file_list:
        size = os.path.getsize(filepath)
        checksum = calculate_md5(filepath)
        
        # Determine purpose summary
        purpose = "Pipeline Component"
        if filepath.startswith("build_native_core"):
            purpose = "Native compiler recipe runner for Core Phase 1"
        elif filepath.startswith("build_native_tier2"):
            purpose = "Native compiler recipe runner for Core Phase 2"
        elif filepath.startswith("build_native_tier3"):
            purpose = "Native compiler recipe runner for Core Phase 3"
        elif filepath.startswith("build_all_latest"):
            purpose = "GNU upstream source build recipe collection (30 packages)"
        elif filepath.startswith("build_libarchive"):
            purpose = "Specific build script for libarchive & pacman"
        elif filepath.startswith("package_arch_standard"):
            purpose = "Arch-standard packaging for curl, gpgme, pacman, base-devel"
        elif filepath.startswith("env_loader"):
            purpose = "Secure environment / packager loader (.env)"
        elif filepath.startswith("update_repo_db"):
            purpose = "repo-add / repo-remove pacman database indexer and signer"
        elif "makepkg.py" in filepath:
            purpose = "Darwin makepkg executor with environment wrapping"
        elif "repo_manager.py" in filepath:
            purpose = "Repository database updater wrapping repo-add"
        elif "detector.py" in filepath:
            purpose = "Source tree build system detector (Autotools/CMake/Meson)"
        elif "generator.py" in filepath:
            purpose = "Automatic PKGBUILD generator from detected sources"
        elif "verifier.py" in filepath:
            purpose = "Post-build package Mach-O and install-tree validator"
        
        lines.append(f'| `{filepath}` | `{checksum}` | {size:,} | {purpose} |')
    lines.append('')

with open('notes/MD5_CHECKSUMS.md', 'w') as f:
    f.write('\n'.join(lines))

print("Created notes/MD5_CHECKSUMS.md")

# 2. Write BUILD_PIPELINE_ANALYSIS.md
analysis = [
    '# Comprehensive Build Pipeline Architectural Analysis',
    '',
    '> **Location:** `notes/BUILD_PIPELINE_ANALYSIS.md`',
    '> **Purpose:** In-depth documentation of existing build subsystems (`builder/src`, `fromsource`, and root scripts) so that the architecture, flags, recipes, and caveats are preserved without repetitive scanning.',
    '',
    '---',
    '',
    '## 1. Overview of Existing Build Subsystems',
    '',
    'Prior to consolidation, the repository contained three separate historical build attempts:',
    '',
    '1. **`builder/src/` (Homebrew Bottle Repackager):**',
    '   - An early attempt to translate Homebrew Formulae and bottles into Arch `.pkg.tar.zst` packages.',
    '   - Modules: `main.py`, `makepkg.py`, `repo_manager.py`, `database.py`, `resolver.py`, `install.py`, `query.py`, `remove.py`, `verify.py`.',
    '   - **Limitation:** Depended on a non-existent `converter/src` package and extracted pre-built bottles that had hardcoded Homebrew rpaths and broken dynamic library linkages on macOS.',
    '',
    '2. **`fromsource/` (Generic Source Detector & Generator):**',
    '   - A generic build generator that scanned source trees to detect build systems.',
    '   - Modules: `detector.py` (checked for `configure.ac`, `CMakeLists.txt`, `meson.build`), `generator.py` (generated naive PKGBUILDs), `verifier.py` (checked Mach-O binaries and codesigning), `builder.py` (orchestrator).',
    '   - **Limitation:** Generated generic Linux-style PKGBUILDs without Darwin SDK sysroot flags, leading to build failures when headers or frameworks were missing.',
    '',
    '3. **Root Script Collections (`build_all_latest.py`, `package_arch_standard.py`, etc.):**',
    '   - Explicit recipe-based Python scripts compiling clean upstream GNU source code directly with `-isysroot $(xcrun --show-sdk-path)`.',
    '   - **Strengths:** Contained exact, battle-tested compilation flags, dependencies, and URLs for bash, coreutils, diffutils, sed, grep, gzip, xz, openssl, gnutls, libarchive, and pacman.',
    '   - **Limitation:** Scattered across 15+ different files with redundant logic and hardcoded recipe lists.',
    '',
    '---',
    '',
    '## 2. Deep Dive: `builder/src` Modules',
    '',
    '### `builder/src/makepkg.py` (MD5: `addd4d27fa9c4a01754db97ea392aba8`)',
    '- **What it did:** Wrapped `/opt/pacman/bin/makepkg` execution.',
    '- **Key Parameters:**',
    '  - `PKGDEST`: Set to output repository directory.',
    '  - `--noconfirm --clean --syncdeps`: Flags passed to makepkg.',
    '- **Darwin Handling:** Lacked automatic Mach-O codesigning or `-Wl,-rpath` injection. Relied on whatever flags were in `/opt/pacman/etc/makepkg.conf`.',
    '',
    '### `builder/src/repo_manager.py` (MD5: `13a53785f5b4310ddf96a2588c6c8212`)',
    '- **What it did:** Wrapped `/opt/pacman/bin/repo-add` and `/opt/pacman/bin/repo-remove`.',
    '- **Key Behavior:** Filtered files ending with `.pkg.tar.zst` matching the Darwin architecture.',
    '- **Limitation:** Failed to generate detached PGP signatures (`.sig`) for the sync database files (`.db.tar.gz`), causing signature verification errors during `pacman -Sy`.',
    '',
    '### `builder/src/resolver.py` (MD5: `c3fad5f245fc627771eb253a210b5de2`)',
    '- **What it did:** Topological sort of package dependencies to compute a build queue.',
    '- **Logic:** Simple Depth-First Search (DFS) graph resolution with cycle detection.',
    '',
    '---',
    '',
    '## 3. Deep Dive: `fromsource` Modules',
    '',
    '### `fromsource/detector.py` (MD5: `0583e96d0704635aed96964ebb839932`)',
    '- **Build System Detection Logic:**',
    '  - `CMake`: Detected if `CMakeLists.txt` present.',
    '  - `Meson`: Detected if `meson.build` present.',
    '  - `Autotools`: Detected if `configure.ac` or `configure.in` or `configure` present.',
    '  - `Make`: Detected if `Makefile` present.',
    '  - `Rust/Cargo`: Detected if `Cargo.toml` present.',
    '  - `Go`: Detected if `go.mod` present.',
    '',
    '### `fromsource/verifier.py` (MD5: `e397c9b5477cac8e4cf9e1b954307078`)',
    '- **Validation Steps:**',
    '  - Unpacked `.pkg.tar.zst` to a temporary directory.',
    '  - Inspected Mach-O header magic bytes: `0xfeedface`, `0xfeedfacf`, `0xcefaedfe`, `0xcffaedfe`, `0xcafebabe`.',
    '  - Checked dylib ID and dependencies via `otool -L`.',
    '  - Verified codesign status via `codesign -v`.',
    '',
    '---',
    '',
    '## 4. Key Recipes Harvested from Root Scripts',
    '',
    'The compilation parameters and upstream source URLs harvested from the root scripts include:',
    '',
    '| Package | Source URL | Build System | Essential Darwin Flags |',
    '| :--- | :--- | :--- | :--- |',
    '| `bash` | `https://ftp.gnu.org/gnu/bash/bash-5.3.tar.gz` | Autotools | `--with-installed-readline=/opt/pacman --with-curses` |',
    '| `coreutils` | `https://ftp.gnu.org/gnu/coreutils/coreutils-9.6.tar.xz` | Autotools | `TIME_T_32_BIT_OK=yes`, disable selinux |',
    '| `diffutils` | `https://ftp.gnu.org/gnu/diffutils/diffutils-3.12.tar.xz` | Autotools | Standard autotools with Darwin sysroot |',
    '| `findutils` | `https://ftp.gnu.org/gnu/findutils/findutils-4.11.0.tar.xz` | Autotools | Standard autotools with Darwin sysroot |',
    '| `grep` | `https://ftp.gnu.org/gnu/grep/grep-3.12.tar.xz` | Autotools | `--with-libiconv-prefix=/opt/pacman` |',
    '| `sed` | `https://ftp.gnu.org/gnu/sed/sed-4.10.tar.xz` | Autotools | Standard autotools |',
    '| `gawk` | `https://ftp.gnu.org/gnu/gawk/gawk-5.4.1.tar.xz` | Autotools | Linked with readline and gmp |',
    '| `gzip` | `https://ftp.gnu.org/gnu/gzip/gzip-1.15.tar.xz` | Autotools | Standard autotools |',
    '| `xz` | `https://github.com/tukaani-project/xz/releases/download/v5.6.4/xz-5.6.4.tar.xz` | Autotools | `--disable-nls` |',
    '| `zstd` | `https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz` | Make / CMake | `PREFIX=/opt/pacman` |',
    '| `openssl` | `https://github.com/openssl/openssl/releases/download/openssl-3.4.1/openssl-3.4.1.tar.gz` | Perl Configure | `./Configure darwin64-x86_64-cc --prefix=/opt/pacman` |',
    '| `libarchive`| `https://github.com/libarchive/libarchive/releases/download/v3.7.7/libarchive-3.7.7.tar.gz` | CMake | `-DENABLE_OPENSSL=ON -DENABLE_ZSTD=ON` |',
    '| `curl` | `https://curl.se/download/curl-8.12.0.tar.xz` | Autotools | `--with-openssl=/opt/pacman --with-zstd=/opt/pacman` |',
    '| `pacman` | Local / Git upstream pacman 7.1.0 | Meson | `-Dgpgme=enabled -Dc_args="-I/opt/pacman/include"` |',
    '',
    '---',
    '',
    '## 5. Architectural Blueprint for Unified `arch_builder.py`',
    '',
    'The unified build package system implements a 5-stage sequential lifecycle:',
    '',
    '```',
    '  [Upstream Arch API / Release Feed]',
    '                 │ (Fast Scan)',
    '                 ▼',
    '       [1. Scan / Compare]',
    '                 │',
    '                 ▼',
    '       [2. Clone / Fetch]  --> Verifies SHA256 / GPG Signature',
    '                 │',
    '                 ▼',
    '       [3. Native Build]   --> Configures with Darwin sysroot & -rpath',
    '                 │             Codesigns all Mach-O binaries & dylibs',
    '                 ▼',
    '       [4. Package]        --> Creates standard Arch .pkg.tar.zst archive',
    '                 │',
    '                 ▼',
    '       [5. Sign & Install] --> Generates GPG detached signature (.sig)',
    '                               Installs into /opt/pacman & updates repo DB',
    '```',
    ''
]

with open('notes/BUILD_PIPELINE_ANALYSIS.md', 'w') as f:
    f.write('\n'.join(analysis))

print("Created notes/BUILD_PIPELINE_ANALYSIS.md")
