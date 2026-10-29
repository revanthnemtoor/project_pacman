"""
Shared constants for project_pacman.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------
# Pacman installation
# ---------------------------------------------------------------

PACMAN_ROOT = Path("/opt/pacman")
PACMAN_BIN = PACMAN_ROOT / "bin" / "pacman"
MAKEPKG_BIN = PACMAN_ROOT / "bin" / "makepkg"
MAKEPKG_CONF = PACMAN_ROOT / "etc" / "makepkg.conf"
PACMAN_CONF = PACMAN_ROOT / "etc" / "pacman.conf"
REPO_ADD_BIN = PACMAN_ROOT / "bin" / "repo-add"

# ---------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

PACKAGES_DIR = PROJECT_ROOT / "packages"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = PROJECT_ROOT / "cache"
STAGING_DIR = PROJECT_ROOT / "staging"
LOGS_DIR = PROJECT_ROOT / "logs"

# Project-specific pacman config (user-writable, no root required)
PROJECT_PACMAN_CONF = PACMAN_ROOT / "etc" / "pacman.conf"

# ---------------------------------------------------------------
# Target install prefix
# ---------------------------------------------------------------

INSTALL_PREFIX = Path("/opt/pacman")

import os
import platform

# ---------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------

# Detect host architecture (arm64 or x86_64)
_host_arch = platform.machine().lower()
if _host_arch in ("aarch64", "arm64"):
    HOST_ARCH = "arm64"
else:
    HOST_ARCH = "x86_64"

# Allow PACMAN_ARCH override, default to host architecture (or arm64)
ARCH = os.environ.get("PACMAN_ARCH", HOST_ARCH)
PLATFORM = "darwin"
DARWIN_ARCH = f"darwin_{ARCH}"
SUPPORTED_ARCHES = ["arm64", "darwin_arm64", "x86_64", "darwin_x86_64"]

# ---------------------------------------------------------------
# GHCR (GitHub Container Registry) for Homebrew bottles
# ---------------------------------------------------------------

GHCR_DOMAIN = "ghcr.io"
GHCR_TOKEN_URL = "https://ghcr.io/token"
GHCR_PACKAGE_SCOPE = "repository:homebrew/core:pull"
