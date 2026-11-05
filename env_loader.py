#!/usr/bin/env python3
"""Environment loader and maintainer/packager configuration helper.

Loads environment variables from .env files and resolves package maintainer identity.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


def load_env(env_path: Optional[Path] = None) -> None:
    """Load key-value pairs from a .env file into os.environ if not already set."""
    if env_path is None:
        # Search starting from current directory up to git/project root
        current = Path(__file__).resolve().parent
        for directory in [current, *current.parents]:
            candidate = directory / ".env"
            if candidate.is_file():
                env_path = candidate
                break

    if not env_path or not env_path.is_file():
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()
                    if (val.startswith('"') and val.endswith('"')) or (
                        val.startswith("'") and val.endswith("'")
                    ):
                        val = val[1:-1]
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass


def get_packager(default: str = "Pacman Packager <packager@localhost>") -> str:
    """Resolve maintainer / packager identity.

    Priority:
    1. os.environ['PACKAGER'] (loaded from .env or shell environment)
    2. os.environ['MAINTAINER']
    3. git config user.name and user.email
    4. Fallback default
    """
    load_env()

    if os.environ.get("PACKAGER"):
        return os.environ["PACKAGER"].strip()

    if os.environ.get("MAINTAINER"):
        return os.environ["MAINTAINER"].strip()

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
        if name:
            return name
    except Exception:
        pass

    return default


# Preload .env upon import
load_env()
