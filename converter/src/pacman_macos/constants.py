"""
Shared constants for project_pacman.
"""

from __future__ import annotations

import os
import platform
import subprocess
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
CORE_DIR = PROJECT_ROOT / "core"
EXTRA_DIR = PROJECT_ROOT / "extra"
OUTPUT_DIR = PROJECT_ROOT / "extra"
CACHE_DIR = PROJECT_ROOT / "cache"
STAGING_DIR = PROJECT_ROOT / "staging"
LOGS_DIR = PROJECT_ROOT / "logs"

# Project-specific pacman config (user-writable, no root required)
PROJECT_PACMAN_CONF = PACMAN_ROOT / "etc" / "pacman.conf"

# ---------------------------------------------------------------
# Target install prefix
# ---------------------------------------------------------------

INSTALL_PREFIX = Path("/opt/pacman")

# Default packager / maintainer resolution:
# 1. $PACKAGER environment variable
# 2. git config (user.name <user.email>)
# 3. Fallback author default
def get_default_packager() -> str:
    if os.environ.get("PACKAGER"):
        return os.environ["PACKAGER"].strip()
    try:
        name = subprocess.check_output(
            ["git", "config", "user.name"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        email = subprocess.check_output(
            ["git", "config", "user.email"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if name and email:
            return f"{name} <{email}>"
        elif name:
            return name
    except Exception:
        pass
    return "Revanth Reddy Nemtoor <developerrevanth123@gmail.com>"

DEFAULT_PACKAGER = get_default_packager()

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
