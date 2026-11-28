# Pacman for macOS (Darwin Native Port)

[![Pacman](https://img.shields.io/badge/pacman-v7.1.0-1793d1.svg)](https://gitlab.archlinux.org/pacman/pacman)
[![libalpm](https://img.shields.io/badge/libalpm-v16.0-1793d1.svg)](https://gitlab.archlinux.org/pacman/pacman)
[![Packages](https://img.shields.io/badge/packages-224%20(112%20core%20%2B%20112%20extra)-brightgreen.svg)](#included-packages)
[![Platform](https://img.shields.io/badge/platform-macOS%20(Darwin)-black.svg)](#architecture-support)
[![Architecture](https://img.shields.io/badge/arch-darwin__x86__64%20%7C%20darwin__arm64-orange.svg)](#architecture-support)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)

A fully native, rootless port of Arch Linux's **Pacman (v7.1.0)** and **libalpm (v16.0)** package manager to **macOS (Darwin)**, complete with **224 open-source packages** (**112 `[core]` + 112 `[extra]`**) and a single-file upstream Git-tag build & auto-update orchestrator (`arch_builder.py`).

Every package is 100% Free & Open-Source Software compiled natively to Darwin Mach-O binaries and `.dylib` shared libraries inside a self-contained, user-owned `/opt/pacman` prefix — with **zero `/opt/local` (MacPorts) or `/usr/local` (Homebrew) runtime library leaks**, full ad-hoc Mach-O codesigning (`codesign --sign -`), and detached PGP signatures (`.sig`) on every package archive and sync database.

---

## Table of Contents

- [Repository Package Counts](#repository-package-counts)
- [Features](#features)
- [Architecture Support](#architecture-support)
- [Quick Start Installation](#quick-start-installation)
- [Interactive Installer Options](#interactive-installer-options)
- [Pacman Quick Reference](#pacman-quick-reference)
- [Unified Build & Auto-Update Pipeline (`arch_builder.py`)](#unified-build--auto-update-pipeline-arch_builderpy)
- [Included Packages (`112 [core]` + `112 [extra]`)](#included-packages)
- [Repository Structure](#repository-structure)
- [Configuration (`pacman.conf` & `mirrorlist`)](#configuration-pacmanconf--mirrorlist)
- [Security & Verification](#security--verification)
- [Maintainer & License](#maintainer--license)

---

## Repository Package Counts

| Repository | `darwin_x86_64` Built | `darwin_arm64` Built | Total Signed Archives | Scope |
| :--- | :---: | :---: | :---: | :--- |
| **`[core]`** | **112** | **94** | **206** | Complete POSIX/GNU userspace, `base-devel` toolchain, shells, TLS/crypto, networking, Python/Perl/Guile runtimes |
| **`[extra]`** | **112** | **99** | **211** | Self-hosted CMake/Ninja/Meson/ccache, Neovim/Vim, modern Rust/C CLI suite, codecs/ImageMagick, Qt 6 (16 modules), KDE Frameworks 6, Gwenview |
| **Total** | **224** | **193** | **417** | 100% open-source, PGP-signed (`CEC5B78775CA4628`), SHA-256 indexed |

---

## Features

- **Real Arch Linux Pacman 7.1.0**: Native `pacman`, `pacman-conf`, `makepkg`, `vercmp`, and `repo-add` powered by `libalpm 16.0`.
- **Rootless `/opt/pacman` Hierarchy**: All binaries, libraries, headers, configs, and ALPM databases live under `/opt/pacman`, owned by your macOS user — **no `sudo` required**.
- **Self-Contained & Zero External Dylib Leaks**: Built against the Apple macOS SDK sysroot and `/opt/pacman/lib` (`-Wl,-rpath,/opt/pacman/lib`), verified clean with zero `/opt/local` or `/usr/local` dynamic library links.
- **Self-Hosted Build Stack**: Includes native `gcc`, `binutils`, `make`, `autoconf`, `automake`, `libtool`, `bison`, `flex`, `pkgconf`, `fakeroot`, `cmake`, `ninja`, `meson`, and `ccache`.
- **Full Media & Image Codec Stack**: Source-built `imagemagick` with `rw+` support for `AVIF`, `HEIC`, `WEBP`, `JP2`, `RAW`, `TIFF`, `PNG`, `JPEG`, and `FreeType`.
- **Native macOS Qt 6 & KDE Frameworks 6**: Ships 16 Qt 6 Cocoa modules, 27 KDE Frameworks 6 libraries (+ `extra-cmake-modules`), and the `gwenview` desktop image viewer.
- **Automated Upstream Git-Tag Builder**: `arch_builder.py` concurrently scans authoritative upstream Git repositories (not Linux Arch databases) for new stable tags, bumps `PKGBUILD` versions, builds from source, signs, indexes, and installs.

---

## Architecture Support

| Architecture | Platform String | macOS Target | Status |
| :--- | :--- | :--- | :--- |
| **Intel x86_64** | `darwin_x86_64` | macOS 12+ (64-bit Intel Macs) | **224 packages** (`112 core` + `112 extra`) |
| **Apple Silicon** | `darwin_arm64` | macOS 15+ (M1 / M2 / M3 / M4) | **193 packages** (`94 core` + `99 extra`) |

---

## Quick Start Installation

### One-Line Installer (Recommended)

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

```bash
curl -fsSL https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/install.sh | bash -s -- -y
# or locally:
./install.sh -y
```

---

## Interactive Installer Options

### 1. Proceed with Installation
```text
Do you want to proceed with the installation?
  [1] Continue with Installation (default)
  [2] Cancel / Exit
```

### 2. PATH Configuration & Priority
```text
How would you like to configure /opt/pacman/bin in your PATH?
  [1] Top Priority  - Prepend to PATH (/opt/pacman tools take precedence over macOS system tools) [default]
  [2] Add to PATH   - Append to PATH (system tools take precedence, pacman tools used as fallback)
  [3] Skip PATH     - Do not modify shell profile files
```

- **Option 1 (Top Priority)**: Prepends `/opt/pacman/bin` to `PATH` in `~/.zshrc`, `~/.bash_profile`, and `~/.config/fish/config.fish` so modern GNU & CLI tools supersede older macOS BSD defaults.
- **Option 2 (Add to PATH)**: Appends `/opt/pacman/bin` to `PATH` as a fallback.
- **Option 3 (Skip PATH)**: Leaves shell profiles untouched.

---

## Pacman Quick Reference

```bash
# Synchronize package databases and upgrade all installed packages
pacman -Syu

# Install packages from [core] or [extra]
pacman -S neovim bat eza zoxide starship ripgrep fzf yazi

# Search available packages across [core] and [extra]
pacman -Ss codec

# Inspect detailed package metadata
pacman -Si cmake

# List all locally installed packages
pacman -Q

# Query metadata and signature validation of an installed package
pacman -Qi guile

# Remove a package
pacman -R <package_name>

# Refresh file database and locate which package owns a file
pacman -Fy
pacman -F libalpm.dylib
```

---

## Unified Build & Auto-Update Pipeline (`arch_builder.py`)

`arch_builder.py` manages the complete Darwin packaging lifecycle (`scan -> fetch -> build -> codesign -> package -> PGP sign -> repo-add -> pacman -U`) directly against upstream Git stable tags:

```bash
# Audit all 112 target FOSS [core] packages in darwin_core_packages.txt
python3 arch_builder.py core-status

# Concurrently scan all local packages against upstream Git release tags
python3 arch_builder.py scan --updates-only --refresh

# Build, codesign, package (.pkg.tar.zst), PGP-sign (.sig), index, and install one package
python3 arch_builder.py build <pkgname>

# Auto-bump PKGBUILDs with newer stable Git tags, rebuild from source, sign, and re-index
python3 arch_builder.py update-all

# Dry-run check without rebuilding
python3 arch_builder.py update-all --dry-run

# Re-index and cryptographically sign core.db and extra.db
python3 arch_builder.py index
```

---

## Included Packages

### Core Repository (`[core]` — 112 Built Packages)

- **Meta & System Layout (4)**: `base`, `base-devel`, `filesystem`, `pacman-mirrorlist`
- **Package Management (3)**: `pacman`, `gpgme`, `libarchive`
- **Compiler Toolchain & Base-Devel (23)**: `autoconf`, `automake`, `binutils`, `bison`, `diffutils`, `fakeroot`, `file`, `findutils`, `flex`, `gawk`, `gcc`, `gettext`, `groff`, `libisl`, `libmpc`, `libtool`, `m4`, `make`, `patch`, `pkgconf`, `sed`, `texinfo`, `which`
- **Shells, Editors & POSIX Userspace (13)**: `bash`, `coreutils`, `dash`, `grep`, `gzip`, `inetutils`, `less`, `libedit`, `man-db`, `nano`, `ncurses`, `readline`, `tar`
- **Compression Libraries & Archivers (7)**: `brotli`, `bzip2`, `lz4`, `lzo`, `xz`, `zlib`, `zstd`
- **Cryptography, TLS, GnuPG & Auth (17)**: `ca-certificates`, `gnupg`, `gnutls`, `krb5`, `leancrypto`, `libassuan`, `libgcrypt`, `libgpg-error`, `libksba`, `libsecret`, `libtasn1`, `libxcrypt`, `nettle`, `npth`, `openssl`, `p11-kit`, `pinentry`
- **Networking, HTTP/2/3, SSH & Directory Services (14)**: `curl`, `iana-etc`, `ldns`, `libidn2`, `libmicrohttpd`, `libnghttp2`, `libnghttp3`, `libngtcp2`, `libpcap`, `libpsl`, `libsasl`, `libssh2`, `openldap`, `openssh`
- **Runtimes, Databases & Core System Libraries (31)**: `expat`, `gc`, `gdbm`, `glib2`, `gmp`, `guile`, `icu`, `jansson`, `json-c`, `libevent`, `libffi`, `libinih`, `libpipeline`, `libunistring`, `libusb`, `libverto`, `libxml2`, `links`, `logrotate`, `mpdecimal`, `mpfr`, `nspr`, `nss`, `pcre2`, `perl`, `popt`, `python`, `s-nail`, `sqlite`, `tzdata`, `unixodbc`

### Extra Repository (`[extra]` — 112 Built Packages)

- **Build Systems & Compiler Cache (5)**: `cmake`, `ninja`, `meson`, `ccache`, `extra-cmake-modules`
- **Editors, Shells, Multiplexers & File Managers (6)**: `neovim`, `vim`, `fish`, `tmux`, `yazi`, `tig`
- **Modern CLI & System Monitoring Suite (25)**: `bat`, `eza`, `fzf`, `ripgrep`, `fd`, `zoxide`, `starship`, `git-delta`, `hyperfine`, `just`, `procs`, `dust`, `sd`, `tealdeer`, `tokei`, `bottom`, `htop`, `entr`, `fastfetch`, `tree`, `jq`, `yq`, `7zip`, `pigz`, `sitecheck`
- **Networking, VCS & Downloaders (9)**: `git`, `gh`, `xh`, `aria2`, `wget`, `rsync`, `mtr`, `tcpdump`, `yt-dlp`
- **Image, PDF, Terminal Graphics & Libraries (23)**: `imagemagick`, `qpdf`, `chafa`, `libheif`, `aom`, `dav1d`, `libde265`, `kvazaar`, `libwebp`, `openjpeg2`, `libraw`, `libjpeg-turbo`, `libpng`, `libtiff`, `freetype2`, `lcms2`, `exiv2`, `jemalloc`, `libsodium`, `oniguruma`, `utf8proc`, `xxhash`, `yyjson`
- **Qt 6 Native macOS Modules (16)**: `qt6-base`, `qt6-connectivity`, `qt6-declarative`, `qt6-imageformats`, `qt6-languageserver`, `qt6-lottie`, `qt6-multimedia`, `qt6-networkauth`, `qt6-quick3d`, `qt6-quick3dphysics`, `qt6-quicktimeline`, `qt6-serialport`, `qt6-shadertools`, `qt6-svg`, `qt6-tools`, `qt6-websockets`
- **KDE Frameworks 6 & Desktop Apps (28)**: `breeze-icons`, `karchive`, `kbookmarks`, `kcodecs`, `kcolorscheme`, `kcompletion`, `kconfig`, `kconfigwidgets`, `kcoreaddons`, `kcrash`, `kdbusaddons`, `kguiaddons`, `ki18n`, `kiconthemes`, `kio`, `kitemmodels`, `kitemviews`, `kjobwidgets`, `knotifications`, `kparts`, `kservice`, `ktextwidgets`, `kwidgetsaddons`, `kwindowsystem`, `kxmlgui`, `solid`, `sonnet`, `gwenview`

---

## Repository Structure

```text
project_pacman/
├── core/                                # 112 [core] packages + signed ALPM sync databases
│   ├── core.db / core.db.sig            # Default sync database + PGP signature
│   ├── core.files / core.files.sig      # File list database + PGP signature
│   ├── core-darwin_x86_64.db.tar.gz*    # Intel x86_64 database + .sig
│   ├── core-darwin_arm64.db.tar.gz*     # Apple Silicon arm64 database + .sig
│   └── *.pkg.tar.zst / *.sig            # Signed binary package archives
├── extra/                               # 112 [extra] packages + signed ALPM sync databases
│   ├── extra.db / extra.db.sig          # Extra sync database + PGP signature
│   ├── extra.files / extra.files.sig    # Extra file list database + PGP signature
│   ├── extra-darwin_x86_64.db.tar.gz*   # Intel x86_64 database + .sig
│   ├── extra-darwin_arm64.db.tar.gz*    # Apple Silicon arm64 database + .sig
│   └── *.pkg.tar.zst / *.sig            # Signed binary package archives
├── packages/
│   ├── core/                            # All 112 canonical [core] PKGBUILD recipes
│   └── extra/                           # Canonical [extra] PKGBUILD recipes
├── configs/
│   └── pacman.conf                      # Reference rootless /opt/pacman configuration
├── darwin_core_packages.txt             # Authoritative 112 FOSS Darwin [core] manifest
├── darwin_extra_packages.md             # Curated FOSS Darwin [extra] package catalog
├── arch_builder.py                      # Single-file Git-tag scanner, builder, signer & indexer
├── env_loader.py                        # Packager environment helper
├── install.sh                           # Interactive universal macOS bootstrap installer
├── index.html                           # Project documentation & wiki portal
└── README.md                            # Complete project documentation
```

---

## Configuration (`pacman.conf` & `mirrorlist`)

Primary configuration at `/opt/pacman/etc/pacman.conf`:

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

SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional
RemoteFileSigLevel = Required

NoExtract   = opt/pacman/share/info/dir

[core]
SigLevel = PackageRequired DatabaseOptional
Include = /opt/pacman/etc/pacman.d/mirrorlist

[extra]
SigLevel = PackageRequired DatabaseOptional
Include = /opt/pacman/etc/pacman.d/mirrorlist
```

Mirrorlist at `/opt/pacman/etc/pacman.d/mirrorlist`:

```ini
# Official project_pacman macOS Mirror List
Server = https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/$repo
Server = https://revanthnemtoor.github.io/project_pacman/$repo
```

---

## Security & Verification

1. **Detached PGP Signatures (`.sig`)**: Every `.pkg.tar.zst` archive and `.db.tar.gz` database in `core/` and `extra/` is signed with official PGP key `CEC5B78775CA4628` and verified by `libalpm` prior to installation.
2. **SHA-256 Digest Verification**: Every downloaded archive is validated against the SHA-256 digest stored inside the signed sync database.
3. **macOS Gatekeeper Ad-Hoc Codesigning**: Every Mach-O binary executable and `.dylib` shared library is signed via `codesign --force --sign -`.
4. **Verify Any Installed Package**:
   ```bash
   pacman -Qi neovim | grep "Validated By"
   # Validated By    : Signature
   ```

---

## Maintainer & License

- **Maintainer & Packager**: Revanth Reddy Nemtoor `<developerrevanth123@gmail.com>`
- **Repository**: [https://github.com/revanthnemtoor/project_pacman](https://github.com/revanthnemtoor/project_pacman)
- **License**: [GPL-3.0-or-later](LICENSE) (GNU General Public License v3.0 or later)
