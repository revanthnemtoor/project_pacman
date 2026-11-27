# Pacman for macOS (`darwin`) — Popular `[extra]` Repository Tools

This document curates the most popular **100% open-source** packages from Arch Linux's `[extra]` ecosystem that build and run natively on **macOS (Darwin)** under the rootless `/opt/pacman` prefix and can be tracked automatically via upstream Git release tags in `arch_builder.py`.

> ** Inclusion Criteria**
> - **100% FOSS Licenses Only**: GPL, LGPL, MIT, BSD, Apache-2.0, MPL-2.0, ISC (no proprietary, shareware, or source-available/BSL tools).
> - **macOS Darwin Native**: Compiles cleanly to Mach-O (`darwin_x86_64` / `darwin_arm64`) without Linux-kernel (`io_uring`, `netlink`, `procfs`-only) or X11/Wayland-only dependencies.
> - **Upstream Git Tag Trackable**: Publishes clean semantic release tags for `arch_builder.py update-all`.

---

## Already Built & Signed in `[extra]` (Current Highlights)

| Package | Category | Description |
| :--- | :--- | :--- |
| `git`, `gh` | Git & VCS | Distributed version control and official GitHub CLI |
| `fzf`, `ripgrep`, `fd`, `tree` | Search & Navigation | Fuzzy finder, fast regex search (`rg`), fast `find`, directory tree |
| `yazi` | File Manager | Blazing-fast terminal file manager written in Rust |
| `fish`, `tmux` | Shell & Multiplexer | Friendly interactive shell and terminal multiplexer |
| `vim` | Editor | Vi Improved text editor |
| `jq`, `yq`, `yyjson` | JSON / YAML | Command-line JSON, YAML, XML, and TOML processors |
| `wget`, `rsync` | Networking & Sync | Network downloader and incremental file transfer utility |
| `fastfetch` | System Info | Fast neofetch-style macOS/Darwin system information tool |
| `imagemagick`, `libheif`, `aom`, `dav1d`, `libwebp`, `libraw`, `openjpeg2` | Media & Codecs | Full source-built image processing and AVIF/HEIC/WebP/RAW/JP2 codecs |
| `qt6-*` (15 modules), `kf6` (34 frameworks), `gwenview` | Desktop / GUI | Native macOS Cocoa Qt 6 + KDE Frameworks 6 + Gwenview image viewer |

---

## Most Popular `[extra]` Tools to Add

### 1. Modern CLI Replacements & Terminal Power Tools
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `bat` | `bat` | MIT / Apache-2.0 | `cat` clone with syntax highlighting and Git integration | `https://github.com/sharkdp/bat.git` |
| `eza` | `eza` | MIT | Modern, maintained replacement for `ls` (fork of `exa`) | `https://github.com/eza-community/eza.git` |
| `zoxide` | `zoxide` | MIT | Smarter `cd` command that learns your most-used directories | `https://github.com/ajeetdsouza/zoxide.git` |
| `starship` | `starship` | ISC | Minimal, blazing-fast, customizable cross-shell prompt | `https://github.com/starship/starship.git` |
| `atuin` | `atuin` | MIT | Magical shell history backed by SQLite with fuzzy search | `https://github.com/atuinsh/atuin.git` |
| `btop` | `btop` | Apache-2.0 | Resource monitor with native macOS CPU, memory, disk, and net stats | `https://github.com/aristocratos/btop.git` |
| `htop` | `htop` | GPL-2.0 | Interactive process viewer with Darwin Mach host support | `https://github.com/htop-dev/htop.git` |
| `bottom` | `btm` | MIT | Cross-platform graphical process/system monitor in Rust | `https://github.com/ClementTsang/bottom.git` |
| `git-delta` | `delta` | MIT | Syntax-highlighting pager for `git`, `diff`, and `grep` | `https://github.com/dandavison/delta.git` |
| `dust` | `dust` | Apache-2.0 | Intuitive `du` disk usage visualizer in Rust | `https://github.com/bootandy/dust.git` |
| `duf` | `duf` | MIT | Better `df` disk free/mountpoint overview utility in Go | `https://github.com/muesli/duf.git` |
| `procs` | `procs` | MIT | Modern replacement for `ps` with colored, searchable output | `https://github.com/dalance/procs.git` |
| `hyperfine` | `hyperfine` | MIT / Apache-2.0 | Command-line benchmarking tool with statistical analysis | `https://github.com/sharkdp/hyperfine.git` |
| `tokei` | `tokei` | MIT / Apache-2.0 | Ultra-fast lines-of-code (`cloc`) counter by language | `https://github.com/XAMPPRocky/tokei.git` |
| `tealdeer` | `tldr` | MIT / Apache-2.0 | Fast Rust client for community-driven `tldr` man page examples | `https://github.com/tealdeer-rs/tealdeer.git` |
| `sd` | `sd` | MIT | Intuitive find-and-replace CLI (`sed` alternative) | `https://github.com/chmln/sd.git` |
| `just` | `just` | CC0-1.0 | Handy command runner for project-specific tasks (`Justfile`) | `https://github.com/casey/just.git` |
| `watchexec` | `watchexec` | Apache-2.0 | Executes commands automatically in response to file modifications | `https://github.com/watchexec/watchexec.git` |
| `entr` | `entr` | ISC | Run arbitrary commands when files change (`kqueue` native on macOS) | `https://github.com/eradman/entr.git` |
| `glow` | `glow` | MIT | Render Markdown beautifully on the CLI | `https://github.com/charmbracelet/glow.git` |

---

### 2. Editors, Multiplexers & Terminal File Managers
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `neovim` | `nvim` | Apache-2.0 | Hyperextensible Vim-based text editor with built-in LSP & Lua | `https://github.com/neovim/neovim.git` |
| `helix` | `hx` | MPL-2.0 | Post-modern modal text editor with built-in Tree-sitter & LSP | `https://github.com/helix-editor/helix.git` |
| `micro` | `micro` | MIT | Modern and intuitive terminal-based text editor with mouse/keybindings | `https://github.com/zyedidia/micro.git` |
| `kakoune` | `kak` | Unlicense | Modal code editor inspired by Vim with multiple selections | `https://github.com/mawww/kakoune.git` |
| `emacs-nox` | `emacs` | GPL-3.0 | Extensible, customizable, self-documenting text editor | `https://git.savannah.gnu.org/git/emacs.git` |
| `zellij` | `zellij` | MIT | Terminal workspace and multiplexer with layouts and floating panes | `https://github.com/zellij-org/zellij.git` |
| `screen` | `screen` | GPL-3.0 | Classic GNU full-screen window manager / terminal multiplexer | `https://git.savannah.gnu.org/git/screen.git` |
| `lf` | `lf` | MIT | Fast, single-binary terminal file manager written in Go | `https://github.com/gokcehan/lf.git` |
| `nnn` | `nnn` | BSD-2-Clause | Tiny, lightning-fast C terminal file manager | `https://github.com/jarun/nnn.git` |
| `mc` | `mc` | GPL-3.0 | Midnight Commander orthodox dual-pane file manager | `https://github.com/MidnightCommander/mc.git` |

---

### 3. Build Systems, Compilers & Language Toolchains
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `cmake` | `cmake`, `ctest` | BSD-3-Clause | Cross-platform C/C++ build system generator (removes external CMake need!) | `https://gitlab.kitware.com/cmake/cmake.git` |
| `ninja` | `ninja` | Apache-2.0 | Small build system with a focus on speed | `https://github.com/ninja-build/ninja.git` |
| `meson` | `meson` | Apache-2.0 | High-productivity Python-based build system | `https://github.com/mesonbuild/meson.git` |
| `ccache` | `ccache` | GPL-3.0 | Fast C/C++/ObjC compiler cache to speed up rebuilds | `https://github.com/ccache/ccache.git` |
| `sccache` | `sccache` | Apache-2.0 | Compiler cache supporting C, C++, and Rust | `https://github.com/mozilla/sccache.git` |
| `llvm` / `clang` | `clang`, `lldb` | Apache-2.0 | Modular LLVM compiler infrastructure, Clang, `clangd`, and `clang-format` | `https://github.com/llvm/llvm-project.git` |
| `rust` | `rustc`, `cargo` | MIT / Apache-2.0 | Rust systems programming compiler and Cargo package manager | `https://github.com/rust-lang/rust.git` |
| `go` | `go` | BSD-3-Clause | Go programming language compiler and toolchain | `https://github.com/golang/go.git` |
| `nodejs` | `node`, `npm` | MIT | JavaScript runtime built on V8 | `https://github.com/nodejs/node.git` |
| `deno` | `deno` | MIT | Secure TypeScript and JavaScript runtime | `https://github.com/denoland/deno.git` |
| `bun` | `bun` | MIT | Fast all-in-one JavaScript runtime, bundler, and package manager | `https://github.com/oven-sh/bun.git` |
| `zig` | `zig` | MIT | General-purpose systems programming language and drop-in C cross-compiler | `https://github.com/ziglang/zig.git` |
| `lua` / `luajit` | `lua`, `luajit` | MIT | Lightweight embeddable scripting language and JIT compiler | `https://github.com/LuaJIT/LuaJIT.git` |
| `ruby` | `ruby`, `gem` | BSD-2-Clause | Dynamic, object-oriented scripting language | `https://github.com/ruby/ruby.git` |
| `uv` | `uv`, `uvx` | MIT / Apache-2.0 | Extremely fast Python package and project manager written in Rust | `https://github.com/astral-sh/uv.git` |
| `ruff` | `ruff` | MIT | Extremely fast Python linter and code formatter in Rust | `https://github.com/astral-sh/ruff.git` |
| `shellcheck` | `shellcheck` | GPL-3.0 | Static analysis tool for `sh`/`bash` scripts | `https://github.com/koalaman/shellcheck.git` |
| `shfmt` | `shfmt` | BSD-3-Clause | Shell parser, formatter, and interpreter | `https://github.com/mvdan/sh.git` |

---

### 4. Git, Dotfiles, Secrets, Backup & DevOps Utilities
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `lazygit` | `lazygit` | MIT | Simple terminal UI for Git commands | `https://github.com/jesseduffield/lazygit.git` |
| `tig` | `tig` | GPL-2.0 | Text-mode ncurses interface for Git | `https://github.com/jonas/tig.git` |
| `git-lfs` | `git-lfs` | MIT | Git extension for versioning large binary files | `https://github.com/git-lfs/git-lfs.git` |
| `glab` | `glab` | MIT | Official GitLab CLI tool | `https://gitlab.com/gitlab-org/cli.git` |
| `jujutsu` | `jj` | Apache-2.0 | Git-compatible DVCS that is both simple and powerful | `https://github.com/jj-vcs/jj.git` |
| `direnv` | `direnv` | MIT | Per-directory `.envrc` environment switcher for shells | `https://github.com/direnv/direnv.git` |
| `mise` | `mise` | MIT | Polyglot dev tool version manager & task runner (`asdf` replacement) | `https://github.com/jdx/mise.git` |
| `stow` | `stow` | GPL-3.0 | Symlink farm manager widely used for dotfiles | `https://git.savannah.gnu.org/git/stow.git` |
| `chezmoi` | `chezmoi` | MIT | Manage your dotfiles securely across multiple machines | `https://github.com/twpayne/chezmoi.git` |
| `age` | `age`, `age-keygen` | BSD-3-Clause | Simple, modern, and secure file encryption tool | `https://github.com/FiloSottile/age.git` |
| `sops` | `sops` | MPL-2.0 | Simple and flexible tool for managing encrypted secrets (`YAML`/`JSON`/`.env`) | `https://github.com/getsops/sops.git` |
| `pass` | `pass` | GPL-2.0 | Standard Unix password manager backed by GnuPG + Git | `https://git.zx2c4.com/password-store` |
| `rclone` | `rclone` | MIT | `"rsync for cloud storage"` supporting 70+ backends | `https://github.com/rclone/rclone.git` |
| `restic` | `restic` | BSD-2-Clause | Fast, deduplicated, encrypted backup program | `https://github.com/restic/restic.git` |
| `borg` | `borg` | BSD-3-Clause | Deduplicating archiver with compression and authenticated encryption | `https://github.com/borgbackup/borg.git` |

---

### 5. Networking, HTTP Clients, Servers & Diagnostics
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `xh` | `xh` | MIT | Friendly and fast Rust tool for sending HTTP requests (`httpie` clone) | `https://github.com/ducaale/xh.git` |
| `httpie` | `http`, `https` | BSD-3-Clause | Human-friendly CLI HTTP client for testing APIs | `https://github.com/httpie/cli.git` |
| `aria2` | `aria2c` | GPL-2.0 | Lightweight multi-protocol & multi-source command-line downloader | `https://github.com/aria2/aria2.git` |
| `nmap` | `nmap`, `ncat` | NPSL (FOSS) | Network exploration and security auditing utility | `https://github.com/nmap/nmap.git` |
| `mtr` | `mtr` | GPL-2.0 | Combines `traceroute` and `ping` into a single real-time diagnostic tool | `https://github.com/traviscross/mtr.git` |
| `iperf3` | `iperf3` | BSD-3-Clause | TCP, UDP, and SCTP network bandwidth measurement tool | `https://github.com/esnet/iperf.git` |
| `socat` | `socat` | GPL-2.0 | Multipurpose bidirectional byte-stream relay (`netcat++`) | `https://repo.or.cz/socat.git` |
| `doggo` | `doggo` | GPL-3.0 | Command-line DNS client for humans supporting DoH, DoT, DoQ | `https://github.com/mr-karan/doggo.git` |
| `tcpdump` | `tcpdump` | BSD-3-Clause | Classic packet analyzer powered by `core/libpcap` | `https://github.com/the-tcpdump-group/tcpdump.git` |
| `wireguard-tools` | `wg`, `wg-quick` | GPL-2.0 | Next-generation secure VPN configuration utilities | `https://git.zx2c4.com/wireguard-tools` |
| `caddy` | `caddy` | Apache-2.0 | Fast, multi-platform web server with automatic HTTPS | `https://github.com/caddyserver/caddy.git` |
| `nginx` | `nginx` | BSD-2-Clause | High-performance HTTP server and reverse proxy | `https://github.com/nginx/nginx.git` |

---

### 6. Media, Audio/Video, Documents & Graphics
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `ffmpeg` | `ffmpeg`, `ffprobe` | LGPL / GPL | Complete cross-platform solution to record, convert, and stream audio/video | `https://git.ffmpeg.org/ffmpeg.git` |
| `yt-dlp` | `yt-dlp` | Unlicense | Feature-rich command-line audio/video downloader for thousands of sites | `https://github.com/yt-dlp/yt-dlp.git` |
| `mpv` | `mpv` | GPL-2.0 / LGPL | Free, open-source, cross-platform command-line media player | `https://github.com/mpv-player/mpv.git` |
| `flac` / `opus` / `lame` | `flac`, `opusenc` | BSD / LGPL | Core lossless and lossy open audio codecs | `https://github.com/xiph/flac.git` |
| `pandoc` | `pandoc` | GPL-2.0 | Universal document converter (Markdown, HTML, LaTeX, DOCX, EPUB, PDF) | `https://github.com/jgm/pandoc.git` |
| `typst` | `typst` | Apache-2.0 | Modern markup-based typesetting system (fast LaTeX alternative in Rust) | `https://github.com/typst/typst.git` |
| `poppler` | `pdftotext`, `pdfinfo` | GPL-2.0 | PDF rendering library and command-line PDF inspection utilities | `https://gitlab.freedesktop.org/poppler/poppler.git` |
| `qpdf` | `qpdf` | Apache-2.0 | Content-preserving PDF transformation, splitting, merging, and decryption | `https://github.com/qpdf/qpdf.git` |
| `graphviz` | `dot` | EPL-1.0 | Graph visualization software (`dot`, `neato`, `fdp`) | `https://gitlab.com/graphviz/graphviz.git` |
| `chafa` | `chafa` | LGPL-3.0 | Terminal graphics renderer (Sixel, Kitty, iTerm2, ANSI blocks) | `https://github.com/hpjansson/chafa.git` |
| `oxipng` / `pngquant` | `oxipng`, `pngquant` | MIT / GPL-3.0 | Multithreaded lossless and lossy PNG optimizers | `https://github.com/shssoichiro/oxipng.git` |
| `perl-image-exiftool` | `exiftool` | Artistic / GPL | Read, write, and edit metadata across hundreds of media formats | `https://github.com/exiftool/exiftool.git` |

---

### 7. Databases, Data Engineering & Archives
| Package | Command | License | Description | Upstream Git |
| :--- | :--- | :--- | :--- | :--- |
| `duckdb` | `duckdb` | MIT | Fast in-process analytical SQL OLAP database (Parquet/CSV/JSON native) | `https://github.com/duckdb/duckdb.git` |
| `postgresql` | `psql`, `postgres` | PostgreSQL | World's most advanced open-source relational database | `https://github.com/postgres/postgres.git` |
| `valkey` | `valkey-cli`, `valkey-server` | BSD-3-Clause | Fully open-source high-performance key-value store (Linux Foundation Redis fork) | `https://github.com/valkey-io/valkey.git` |
| `miller` | `mlr` | BSD-2-Clause | Like `awk`, `sed`, `cut`, `join`, and `sort` for CSV, TSV, and JSON | `https://github.com/johnkerl/miller.git` |
| `qsv` / `xsv` | `qsv` | MIT / Unlicense | Blazing-fast CSV data-wrangling toolkit written in Rust | `https://github.com/dathere/qsv.git` |
| `7zip` | `7zz` | LGPL-2.1 | Official 7-Zip file archiver with high compression ratio | `https://github.com/ip7z/7zip.git` |
| `unzip` / `zip` | `unzip`, `zip` | Info-ZIP (BSD-like) | Standard `.zip` extraction and creation utilities | `https://github.com/madler/unzip.git` |
| `pigz` | `pigz` | Zlib | Parallel implementation of `gzip` exploiting all CPU cores | `https://github.com/madler/pigz.git` |

---

## Recommended Build Order (First Batch for `/opt/pacman`)

If you want to start building `[extra]` next, the highest-leverage **Tier 1 bootstrap batch** is:
1. **Self-Hosted Build Tools** (eliminates needing `/usr/local/bin/cmake` or external Rust/Go):
   `cmake`, `ninja`, `meson`, `ccache`, `pkgconf` *(already in core)*, `rust`, `go`
2. **Everyday CLI Essentials**:
   `neovim`, `helix`, `bat`, `eza`, `zoxide`, `starship`, `git-delta`, `btop`, `htop`, `lazygit`, `direnv`, `just`, `7zip`, `pigz`, `unzip`, `zip`
3. **Media & Data Powerhouses**:
   `ffmpeg`, `yt-dlp`, `pandoc`, `typst`, `duckdb`, `poppler`, `qpdf`, `chafa`
