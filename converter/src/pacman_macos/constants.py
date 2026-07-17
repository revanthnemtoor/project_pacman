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

# ---------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------

ARCH = "arm64"
PLATFORM = "darwin"

# ---------------------------------------------------------------
# GHCR (GitHub Container Registry) for Homebrew bottles
# ---------------------------------------------------------------

GHCR_DOMAIN = "ghcr.io"
GHCR_TOKEN_URL = "https://ghcr.io/token"
GHCR_PACKAGE_SCOPE = "repository:homebrew/core:pull"
