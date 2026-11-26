# sitecheck

Minimal native macOS Pacman CLI tool to diagnose website availability, DNS resolution, HTTP errors, connection failures, and response times.

## Features

- Compiled native macOS Mach-O CLI executable (`/opt/pacman/bin/sitecheck`) with **zero Pacman runtime dependencies** (`depends=()`), relying only on base macOS `/usr/bin/curl`, `/usr/bin/dig`, and `libSystem.B.dylib`.
- Works identically across `bash`, `zsh`, `sh`, `fish`, scripts, and `which`/`where`.
- Check HTTP/HTTPS URLs or bare hostnames (`sitecheck github.com` defaults to `https://` and falls back to `http://` if `https://` fails with TLS/connection refusal) and supports checking multiple URLs in one command.
- Optional custom DNS resolver (`-dns <IP>`), with built-in labels for Cloudflare (`1.1.1.1`), Google (`8.8.8.8`), and Quad9 (`9.9.9.9`).
- Resolves hostnames via `/usr/bin/dig` and forces connections to resolved IPs using `curl --resolve`, preserving HTTPS SNI and TLS hostname verification.
- Reports HTTP status codes, remote IP, and actual response times.
- Distinguishes HTTP error codes (400, 401, 403, 404, 429, 500, 502, 503, 504) from DNS and TCP/TLS connection failures without fabricating response times on failed connections.

## Building Packages

From the package source directory:

```sh
CARCH="darwin_x86_64" /opt/pacman/bin/makepkg --config /opt/pacman/etc/makepkg.conf -f -C --nodeps
CARCH="darwin_arm64" /opt/pacman/bin/makepkg --config /opt/pacman/etc/makepkg.conf -f -C --nodeps
```

## Installation & Removal

Install from the local `.pkg.tar.zst` package archive (`darwin_x86_64` or `darwin_arm64`):

```sh
# Intel macOS
/opt/pacman/bin/pacman -U sitecheck-1.0.0-1-darwin_x86_64.pkg.tar.zst

# Apple Silicon macOS
/opt/pacman/bin/pacman -U sitecheck-1.0.0-1-darwin_arm64.pkg.tar.zst
```

Or install / remove from the Pacman repository (`[extra]`):

```sh
/opt/pacman/bin/pacman -S sitecheck
/opt/pacman/bin/pacman -R sitecheck
```

## Usage

```sh
sitecheck https://github.com
sitecheck github.com
sitecheck dprkportal.kp airkoryo.com.kp
sitecheck https://citizenx.com
sitecheck -dns 1.1.1.1 https://citizenx.com
sitecheck -dns 8.8.8.8 https://citizenx.com
sitecheck -dns 9.9.9.9 https://citizenx.com
```
