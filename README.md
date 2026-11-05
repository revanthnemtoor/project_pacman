# Pacman for macOS (Darwin Native Port)

[![Pacman](https://img.shields.io/badge/pacman-v7.1.0-blue.svg)](https://gitlab.archlinux.org/pacman/pacman)
[![Platform](https://img.shields.io/badge/platform-macOS%20(Darwin)-black.svg)](https://apple.com/macos)
[![Architecture](https://img.shields.io/badge/arch-arm64%20%7C%20x86__64-orange.svg)](#architecture-support)
[![Build](https://img.shields.io/badge/build-100%25%20source--built-green.svg)](#native-toolchain)
[![License](https://img.shields.io/badge/license-GPL--2.0--or--later-blue.svg)](LICENSE)

A fully native, rootless port of Arch Linux's **Pacman (v7.1.0)** and **libalpm (v16.0)** package manager to **macOS (Darwin)**.

Every package in the core repository is compiled directly from upstream source with Apple Clang, Meson, and Ninja. There are **zero Homebrew runtime bottles or dependencies**. All binaries and shared libraries are native Darwin Mach-O executables signed with ad-hoc codesigning (`codesign --sign -`) and operate inside a self-contained `/opt/pacman` prefix.

---

## Table of Contents

- [Features](#features)
- [Architecture Support](#architecture-support)
- [Quick Start Installation](#quick-start-installation)
  - [One-Line Installer (Recommended)](#one-line-installer-recommended)
  - [From Local Git Clone](#from-local-git-clone)
  - [Non-Interactive / CI Mode](#non-interactive--ci-mode)
- [Interactive Installer Options](#interactive-installer-options)
- [Pacman Quick Reference](#pacman-quick-reference)
- [Repository Structure](#repository-structure)
- [Included Packages](#included-packages)
- [Configuration (`pacman.conf`)](#configuration-pacmanconf)
- [Security & Verification](#security--verification)
- [Maintainer & License](#maintainer--license)

---

## Features

* **Real Arch Linux Pacman 7.1.0**: Native `pacman`, `pacman-conf`, `makepkg`, `vercmp`, and `repo-add` powered by `libalpm 16.0`.
* **Rootless Operation**: All binaries, libraries, configs, and caches live under `/opt/pacman`, fully owned by your macOS user. No `sudo` is required for package installations or upgrades.
* **100% Source-Built Base**: Pure upstream releases (Bash 5.3, Readline 8.3, Coreutils 9.6, OpenSSL 3.4.1, Libarchive 3.7.7, etc.) linking strictly against system libraries and native pacman dependencies.
* **Native HTTP/HTTPS Downloader**: Built with native `libcurl` support and configured with `XferCommand` fallback for fast, parallel multi-stream downloads (`ParallelDownloads = 5`).
* **Qt 6 & KDE Frameworks 6**: Includes 16 native Qt 6.12 modules and 34 KDE Frameworks 6 packages, including the Gwenview image viewer.
* **Dual Architecture Awareness**: Automatically serves `darwin_arm64` for Apple Silicon (M1/M2/M3/M4) and `darwin_x86_64` for Intel Macs.
* **SHA-256 Checksum Validation**: Every package downloaded is cryptographically checked against the SHA-256 digest recorded in `core.db` and `extra.db`.

---

## Architecture Support

| Architecture | Platform String | macOS Target | Status |
| :--- | :--- | :--- | :--- |
| **Apple Silicon** | `darwin_arm64` | macOS 12+ (M1 / M2 / M3 / M4) | Supported |
| **Intel x86_64** | `darwin_x86_64` | macOS 12+ (x86_64 Macs) | Supported |

---

## Quick Start Installation

### One-Line Installer (Recommended)

Run the universal bootstrap installer in your terminal:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/install.sh)"
```

### From Local Git Clone

```bash
git clone https://github.com/revanthnemtoor/project_pacman.git
cd project_pacman
./install.sh
```

### Non-Interactive / CI Mode

To install automatically with default settings (Top Priority PATH, no prompt):

```bash
curl -fsSL https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/install.sh | bash -s -- -y
# or locally:
./install.sh -y
```

---

## Interactive Installer Options

After displaying the splash screen and detecting your Mac model and architecture, the installer pauses to ask you two configuration questions:

### 1. Proceed with Installation
```text
Do you want to proceed with the installation?
  [1] Continue with Installation (default)
  [2] Cancel / Exit
```
Pressing **Enter** or typing `1` proceeds with the installation. Selecting `2` safely exits without modifying your system.

### 2. PATH Configuration & Priority
```text
How would you like to configure /opt/pacman/bin in your PATH?
  [1] Top Priority  - Prepend to PATH (/opt/pacman tools take precedence over macOS system tools) [default]
  [2] Add to PATH   - Append to PATH (system tools take precedence, pacman tools used as fallback)
  [3] Skip PATH     - Do not modify shell profile files
```

* **Option 1 (Top Priority)**: Prepends `/opt/pacman/bin` to `PATH` in `~/.zshrc`, `~/.bash_profile`, and `~/.config/fish/config.fish`. Modern GNU utilities (`bash 5.3`, `coreutils 9.6`, `grep 3.12`, `sed 4.10`, etc.) override outdated macOS BSD defaults.
* **Option 2 (Add to PATH / Standard)**: Appends `/opt/pacman/bin` to `PATH`. macOS system utilities take precedence; pacman tools are available without overriding system defaults.
* **Option 3 (Skip PATH)**: Leaves your shell config untouched. You can manually export `PATH="/opt/pacman/bin:$PATH"` when needed.

---

## Pacman Quick Reference

```bash
# Synchronize package databases and perform a full system upgrade
pacman -Syu

# Synchronize and align with repository package versions (permits downgrade from old placeholders)
pacman -Syuu

# Install one or more packages
pacman -S bash coreutils jq

# Search for packages by keyword
pacman -Ss python

# Display detailed package metadata
pacman -Si bash

# List all installed packages
pacman -Q

# Query information about an installed package
pacman -Qi bash

# Remove a package
pacman -R <package_name>

# Update the file-search database
pacman -Fy

# Find which package provides a specific command or file
pacman -F libalpm.dylib
```

---

## Repository Structure

The package repositories mirror Arch Linux's official organization:

```text
project_pacman/
├── core/                                # Core base packages and libraries
│   ├── core.db                          # Sync database (x86_64 default)
│   ├── core.files                       # File list database
│   ├── core-darwin_arm64.db.tar.gz      # Apple Silicon database
│   ├── core-darwin_x86_64.db.tar.gz     # Intel 64-bit database
│   └── *.pkg.tar.zst                    # Package archives
├── extra/                               # Extended CLI tools, GUI libraries, Qt6, KDE
│   ├── extra.db                         # Extra sync database
│   ├── extra.files                      # Extra file list database
│   ├── extra-darwin_arm64.db.tar.gz     # Apple Silicon database
│   ├── extra-darwin_x86_64.db.tar.gz    # Intel 64-bit database
│   └── *.pkg.tar.zst                    # Package archives
├── configs/
│   └── pacman.conf                      # Reference pacman configuration
├── pacman/                              # Pacman 7.1.0 native C source code
├── install.sh                           # Universal interactive installer script
├── update_repo_db.py                    # Script to regenerate repo databases via repo-add
└── README.md                            # Documentation
```

---

## Included Packages

### Core System (`[core]`)
* **Shell & Tools**: `bash 5.3`, `readline 8.3`, `coreutils 9.6`, `diffutils 3.12`, `sed 4.10`, `grep 3.12`, `findutils 4.11.0`, `gawk 5.4.1`, `gzip 1.15`, `make 4.4.1`, `which 2.21`, `less 668`
* **Package Management**: `pacman 7.1.0` (with `libalpm 16.0`), `libarchive 3.7.7`, `pkgconf 2.3.0`
* **Compression**: `zlib 1.3.1`, `bzip2 1.0.8`, `lz4 1.10.0`, `zstd 1.5.7`, `xz 5.6.4`, `brotli 1.1.0`, `lzo 2.10`, `xxhash 0.8.2`
* **Crypto & Core Libraries**: `openssl 3.4.1`, `gmp 6.3.0`, `mpfr 4.2.1`, `expat 2.6.4`, `libffi 3.4.6`, `ncurses 6.5`, `sqlite 3.47.0`, `m4 1.4.20`, `libunistring 1.2`, `libidn2 2.3.7`, `libpsl 0.21.5`, `libtasn1 4.19.0`, `libgcrypt 1.11.0`, `libksba 1.6.7`, `npth 1.7`, `nettle 3.10`, `libxml2 2.13.4`, `gettext 0.22.5`

### Extended Utilities & GUI (`[extra]`)
* **CLI Tools**: `jq 1.7.1`, `nano 8.2`, `tree 2.2.1`, `oniguruma 6.9.9`, `utf8proc 2.9.0`, `libevent 2.1.12`
* **Qt 6 Framework**: 16 native modules (`qt6-base 6.12.0`, `qt6-declarative`, `qt6-svg`, `qt6-tools`, `qt6-multimedia`, etc.)
* **KDE Frameworks 6**: 34 native frameworks (`karchive`, `kcoreaddons`, `kconfig`, `kio`, `kxmlgui`, `solid`, `sonnet`, `breeze-icons`, etc.)
* **Applications**: Gwenview image viewer (`gwenview 26.08.2`)

---

## Configuration (`pacman.conf`)

The primary configuration file is located at `/opt/pacman/etc/pacman.conf`:

```ini
[options]
RootDir     = /
DBPath      = /opt/pacman/var/lib/pacman/
CacheDir    = /opt/pacman/var/cache/pacman/pkg/
LogFile     = /opt/pacman/var/log/pacman.log
GPGDir      = /opt/pacman/etc/pacman.d/gnupg/
HookDir     = /opt/pacman/etc/pacman.d/hooks/
HoldPkg     = pacman
Architecture = auto any

Color
CheckSpace
ParallelDownloads = 5
XferCommand = /usr/bin/curl -L -C - -f -o %o %u

SigLevel    = Optional TrustAll
LocalFileSigLevel = Optional
RemoteFileSigLevel = Optional

[core]
SigLevel = Optional TrustAll
Server = https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/core
Server = https://revanthnemtoor.github.io/project_pacman/core

[extra]
SigLevel = Optional TrustAll
Server = https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/extra
Server = https://revanthnemtoor.github.io/project_pacman/extra
```

---

## Security & Verification

1. **SHA-256 Sums**: All packages are verified against their SHA-256 digests in `core.db` and `extra.db` prior to installation. Corrupted or altered downloads are automatically rejected.
2. **Codesigning**: All Mach-O executables and `.dylib` shared libraries undergo ad-hoc codesigning (`codesign --sign -`) to satisfy macOS Gatekeeper and security frameworks.
3. **Integrity Validation**: Query any installed package to verify its validation mechanism:
   ```bash
   pacman -Qi bash | grep "Validated By"
   # Output: Validated By : SHA-256 Sum
   ```

---

## Maintainer & License

* **Maintainer & Packager**: Revanth Reddy Nemtoor <developerrevanth123@gmail.com>
* **Repository**: [https://github.com/revanthnemtoor/project_pacman](https://github.com/revanthnemtoor/project_pacman)
* **License**: [GPL-2.0-or-later](https://gitlab.archlinux.org/pacman/pacman/-/blob/master/COPYING) (matching upstream GNU / Pacman licensing)

