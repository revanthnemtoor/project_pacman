# Arch Linux vs. Darwin Native Pacman: Architecture, Differences, and Challenges

> **Document Status**: Draft Proposal & Decision Matrix  
> **Target System**: macOS (Darwin `x86_64` & `arm64`)  
> **Base Standard**: Arch Linux (`pacman` 7.1.x, `libalpm`, `makepkg`)

---

## 1. Executive Summary

This document evaluates the differences between upstream **Arch Linux** and this **Darwin native Pacman port** (`/opt/pacman`). It explores what it takes to achieve parity with Arch Linux conventions, the technical barriers posed by Darwin/Mach-O vs. Linux/ELF, and provides concrete architectural decisions for you to pick how to proceed.

---

## 2. Side-by-Side Comparison: Current Darwin Port vs. Arch Linux

| Feature / Dimension | Arch Linux (x86_64 / aarch64) | Current Darwin Port (`/opt/pacman`) | Parity Gap & Impact |
| :--- | :--- | :--- | :--- |
| **Operating System & Kernel** | Linux (GNU/Linux userspace) | macOS / Darwin (XNU hybrid kernel) | Fundamental kernel syscall & driver boundary |
| **Binary Executable Format** | **ELF64** (`readelf`, `objdump`, `ldd`) | **Mach-O 64-bit** (`otool`, `dyldinfo`, `codesign`) | Linux ELF tools do not parse Darwin Mach-O |
| **C Library (libc)** | `glibc` (`glibc.so.6`) | Apple `libSystem.dylib` (BSD libc + Mach) | `glibc` cannot run bare on Darwin kernel |
| **Shared Libraries** | `.so` (`DT_SONAME`, `DT_NEEDED`, `rpath`) | `.dylib` (`LC_ID_DYLIB`, `LC_LOAD_DYLIB`, `@rpath`) | Library naming and dynamic linker (`dyld`) differ |
| **Service & Init Manager** | `systemd` (`systemctl`, unit files) | Apple `launchd` (`launchctl`, `.plist` files) | Arch packages expecting `systemd` fail on Darwin |
| **Core Toolchain** | GNU `gcc`, GNU `binutils`, GNU `make` | Apple Clang (Xcode CLI) or GCC on Mach-O | Compiler flags (`-install_name` vs `-soname`), linker flags |
| **Package Validation** | `Validated By : PGP Signature` | `Validated By : None` (current default) | Signatures must be generated and verified via `pacman-key` |
| **Shared Library Autodeps** | Auto-detects `libfoo.so=X-64` via `autodeps` | Disabled (`!autodeps` in `makepkg.conf`) | `makepkg` scripts call Linux-only `readelf`/`ldd` |
| **Prefix & Hierarchy** | `/usr`, `/etc`, `/var` (standard FHS) | `/opt/pacman`, `/opt/pacman/etc`, `/opt/pacman/var` | Isolated prefix prevents clashing with macOS system |
| **Privilege & Sandboxing** | `fakeroot` (ptrace/LD_PRELOAD), namespaces | `fakeroot` (macOS SIP blocks `DYLD_INSERT_LIBRARIES`) | Makepkg must use prefix binaries to avoid SIP stripping |
| **Meta-packages** | `base`, `base-devel` | `base`, `base-devel` (created) | **Aligned** (`Required By: base base-devel`) |
| **Virtual Provides** | `libalpm.so=16-64` | `libalpm.so=16-64`, `libalpm.dylib=16` | **Aligned** |

---

## 3. Deep-Dive on Current Gaps

### 3.1 Gap 1: `Validated By : None` vs `Validated By : PGP Signature`

#### Why It Occurs:
In `libalpm`, when `pacman -Qi <pkg>` runs, the `Validated By` field inspects the package's installation record in `/opt/pacman/var/lib/pacman/local/<pkg>-<ver>/desc`:
- If installed directly via `pacman -U <pkg>.pkg.tar.zst` without a corresponding `.sig` detached signature file, or when `LocalFileSigLevel` is set to `Optional TrustAll`, `libalpm` marks validation as `None` (or `Installed from a package file without verification`).
- In Arch Linux, packages from official repositories are synced with a repository signature (`core.db.sig`) and detached package signatures (`<pkg>.pkg.tar.zst.sig`). The local pacman keyring is populated via `pacman-key --init` and `pacman-key --populate archlinux`.

#### How to Match Arch Exactly:
1. **Generate a Dedicated Packaging Key**:
   ```bash
   gpg --batch --passphrase '' --quick-generate-key "Pacman Darwin Packager <maintainer@example.com>" default default never
   KEYID=$(gpg --list-secret-keys --with-colons | grep '^sec' | cut -d: -f5)
   ```
2. **Configure `makepkg.conf`**:
   - In `/opt/pacman/etc/makepkg.conf`:
     ```bash
     BUILDENV=(!distcc color !ccache check !sccache sign)
     GPGKEY="<KEYID>"
     ```
3. **Initialize `pacman-key`**:
   ```bash
   sudo /opt/pacman/bin/pacman-key --init
   sudo /opt/pacman/bin/pacman-key --add /path/to/public-key.asc
   sudo /opt/pacman/bin/pacman-key --lsign-key <KEYID>
   ```
4. **Sign Repository & Packages**:
   - Generate detached signatures: `gpg --detach-sign --use-agent <pkg>.pkg.tar.zst` (emitting `<pkg>.pkg.tar.zst.sig`).
   - Add to repo database with signing: `repo-add -s -k <KEYID> core.db.tar.gz *.pkg.tar.zst`.
   - Update `pacman.conf` to `SigLevel = Required DatabaseOptional`.
5. **Result**:
   - `pacman -S <pkg>` or `pacman -U <pkg>.pkg.tar.zst` (with `.sig` present) displays:
     ```text
     Validated By : PGP Signature
     ```

---

### 3.2 Gap 2: Shared Library Soname Dependencies (`autodeps`)

#### The Arch Linux Behavior:
When Arch builds a package like `pacman`, `makepkg`'s `library_depends.sh` script scans all compiled executables with:
```bash
LC_ALL=C readelf -d "$filename" | sed -nr 's/.*Shared library: \[(.*)\].*/\1/p'
ldd "$filename"
```
If an executable links against `libarchive.so.13`, `makepkg` looks up which package provides `lib:usr/lib:libarchive.so.13`. It then automatically injects soname dependencies into the generated `.PKGINFO`:
```ini
depend = libarchive.so=13-64
depend = libcurl.so=4-64
depend = libgpgme.so=11-64
depend = libcrypto.so=3-64
```
This guarantees ABI safety: if `libcurl` bumps its soname to `libcurl.so.5`, pacman will refuse to run against a broken ABI.

#### Why This Breaks on Darwin:
1. **ELF vs Mach-O**: Darwin binaries do not have ELF `DT_SONAME` or `DT_NEEDED`. They have Mach-O `LC_LOAD_DYLIB` load commands.
2. **Missing Tools**: `readelf` and `ldd` do not exist natively on macOS. Dynamic dependencies are queried via `otool -L` or `dyldinfo -dylibs`.
3. **Prefix Mismatch**: Arch's `makepkg` hardcodes `LIB_DIRS=('lib:usr/lib' 'lib32:usr/lib32')`. Our prefix is `/opt/pacman/lib`.
4. **Library Extension**: macOS shared libraries use `.dylib` instead of `.so` (e.g. `libarchive.13.dylib` vs `libarchive.so.13`).

---

## 4. Challenges: Linux Names vs. macOS/Xcode Toolchain

### 4.1 The `glibc` & `systemd` Reality
Arch Linux's pacman dependencies list `glibc` and `systemd`.
- **Can we install `glibc` on macOS?**  
  **No**. `glibc` is tightly coupled to Linux kernel system calls (`sys_clone`, `sys_epoll`, `sys_futex`). macOS uses the XNU kernel with BSD/Mach syscalls (`mach_msg`, `kqueue`). Running native binaries compiled for macOS requires Apple's `libSystem.dylib`.
- **Can we install `systemd` on macOS?**  
  **No**. `systemd` requires Linux cgroups, namespaces, and netlink sockets. macOS uses `launchd`.

#### Potential Solutions:
1. **Clean Darwin Mapping (Recommended)**: Omit Linux-kernel-only packages (`glibc`, `systemd`) from runtime dependencies on Darwin, exactly as Homebrew and MacPorts do.
2. **Compatibility Shim Meta-Packages**: Create zero-byte meta-packages named `glibc` and `systemd` that depend on `darwin-system` to satisfy unpatched upstream PKGBUILD dependencies if porting raw Arch PKGBUILDs.

---

### 4.2 Compiler & Linker Divergence: GCC/GNU vs. Apple Clang/Xcode

| Aspect | GNU / Linux | Apple Clang / Darwin |
| :--- | :--- | :--- |
| **Compiler** | `gcc`, `g++` | Apple `clang`, `clang++` |
| **Linker** | GNU `ld` (BFD) or `lld` | Apple `ld64` |
| **Shared Lib Option** | `-shared -Wl,-soname,libfoo.so.1` | `-dynamiclib -Wl,-install_name,/opt/pacman/lib/libfoo.1.dylib` |
| **RPATH Flag** | `-Wl,-rpath,/path` | `-Wl,-rpath,/path` (requires absolute ID or `@rpath` handling) |
| **Binary Signing** | Optional | **Mandatory** on Apple Silicon (arm64); unsigned Mach-O binaries get killed by the kernel (`SIGKILL`) |

---

### 4.3 macOS System Integrity Protection (SIP) & `fakeroot`
On Linux, `makepkg` uses `fakeroot` via `LD_PRELOAD` to simulate root file ownership when assembling tar archives.  
On macOS, SIP clears `DYLD_INSERT_LIBRARIES` whenever an Apple system binary (like `/bin/sh` or `/usr/bin/tar`) is executed.  
- **Solution in Port**: All build scripts and makepkg must strictly invoke `/opt/pacman/bin/bash`, `/opt/pacman/bin/bsdtar`, and `/opt/pacman/bin/coreutils` so `DYLD_INSERT_LIBRARIES` is preserved across subprocess calls.

---

## 5. Architectural Choices for You to Pick

Review the options below and pick your preferred path for each track:

### Track 1: Platform Identity & Package Names
- [ ] **Option 1A (Native Darwin Standard - Recommended)**:
  - Keep packages cleanly scoped to Darwin: dependencies list native Darwin equivalents (`bash`, `coreutils`, `libarchive`, `openssl`, `curl`).
  - Do not include `glibc` or `systemd`.
  - Provide both `.dylib` and `.so` virtual aliases where beneficial.
- [ ] **Option 1B (Pure Linux Emulation Shims)**:
  - Create dummy/virtual packages for `glibc` (providing `glibc=2.40`, pointing to `libSystem`) and `systemd` (shim to `launchd`) so that 100% identical package lists match Arch verbatim.

---

### Track 2: Shared Library Dependency Resolution (`Depends On`)
- [ ] **Option 2A (Mach-O Native `autodeps` in `makepkg`)**:
  - Patch `/opt/pacman/share/makepkg/autodep/library_depends.sh` and `library_provides.sh` to use `otool -D` (provides) and `otool -L` (depends) on Darwin.
  - Set `LIB_DIRS=('lib:opt/pacman/lib')`.
  - Automatically emits `depend = libarchive.13.dylib` / `provides = libarchive.13.dylib`.
- [ ] **Option 2B (Arch Soname Cross-Parity via Explicit PKGBUILDs)**:
  - Add explicit `provides=('libarchive.so=13-64' 'libarchive.dylib=13')` across all core libraries (`libarchive`, `curl`, `gpgme`, `openssl`).
  - Add those soname entries to `pacman`'s `depends` array manually.
- [ ] **Option 2C (Hybrid: Mach-O Autodeps with `.so` Aliasing)**:
  - Auto-extract Mach-O dylib versions and also create symlink/virtual provides for both `.dylib` and `.so=X-64`.

---

### Track 3: PGP Package & Database Signing (`Validated By`)
- [ ] **Option 3A (Full Arch PGP Enforcement)**:
  - Generate official project GPG key for `project_pacman`.
  - Initialize local keyring via `pacman-key --init` and `--lsign-key`.
  - Configure `makepkg.conf` with `BUILDENV=(sign)` and `GPGKEY`.
  - Sign all packages (`.sig`) and databases (`.db.sig`), setting `SigLevel = Required DatabaseOptional`.
  - `pacman -Qi` will display `Validated By : PGP Signature`.
- [ ] **Option 3B (Dual-Mode: Signed Repositories with Optional Local)**:
  - Sign repository databases and remote packages.
  - Set `LocalFileSigLevel = Optional TrustAll` for easy local development, while remote installs are verified.

---

### Track 4: Toolchain Integration (`base-devel`)
- [ ] **Option 4A (Apple Clang / Xcode CLI Wrapped)**:
  - Provide wrapper symlinks in `/opt/pacman/bin` (`gcc -> clang`, `g++ -> clang++`, `make -> /opt/pacman/bin/make`).
  - Minimal storage overhead; uses Apple's highly optimized compiler and SDK.
- [ ] **Option 4B (Self-Contained GNU GCC Toolchain from Source)**:
  - Compile GNU GCC 14+ and GNU binutils targeting Darwin Mach-O directly into `/opt/pacman/bin/gcc`.
  - True 100% GNU toolchain independence from Xcode.

---

## 6. Recommended Immediate Next Step

If you want the quickest path to achieving **`Validated By : PGP Signature`** and **shared library soname dependencies** without breaking macOS binary compatibility:
1. **Adopt Track 1A** (Native Darwin packages without glibc/systemd dummy noise).
2. **Adopt Track 2A/2C** (Patch `autodep` in `makepkg` to inspect Mach-O dylibs via `otool`).
3. **Adopt Track 3A** (Setup GPG key and sign packages for PGP Signature validation).

Which options would you like to proceed with?
