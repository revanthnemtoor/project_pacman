"""
Homebrew Formula Interface

This module communicates directly with Homebrew.

It does NOT know anything about our Package class.

Responsibilities

- Read formula metadata
- Read bottle metadata
- Read dependencies
- Read versions

Nothing else.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from pathlib import Path

from pacman_macos.constants import ARCH


class FormulaError(RuntimeError):
    pass


class Formula:

    FORMULA_ALIASES = {
        "openssl": "openssl@3",
        "sed": "gnu-sed",
        "tar": "gnu-tar",
    }

    def __init__(self, name: str):
        self.name = self.FORMULA_ALIASES.get(name, name)

    # ----------------------------------------------------------

    def exists(self) -> bool:
        result = subprocess.run(
            ["brew", "info", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return result.returncode == 0

    # ----------------------------------------------------------

    def json(self) -> dict:
        data = None
        # Try local brew info first
        try:
            proc = subprocess.run(
                [
                    "brew",
                    "info",
                    "--json=v2",
                    self.name,
                ],
                capture_output=True,
                text=True,
            )

            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                formulae = data.get("formulae", [])
                if formulae and formulae[0].get("bottle", {}).get("stable", {}).get("files"):
                    return data
        except Exception:
            pass

        # Fallback to Homebrew public formula JSON API (for full multi-arch bottle metadata)
        try:
            url = f"https://formulae.brew.sh/api/formula/{self.name}.json"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "curl/8.7.1"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                formula_data = json.loads(resp.read().decode())
                return {"formulae": [formula_data]}
        except Exception as e:
            if data:
                return data
            raise FormulaError(f"Could not fetch formula info for '{self.name}': {e}")

    # ----------------------------------------------------------

    def formula(self) -> dict:
        data = self.json()

        formulas = data.get("formulae", [])

        if not formulas:
            raise FormulaError(
                f"No formula named '{self.name}'"
            )

        return formulas[0]

    # ----------------------------------------------------------

    def bottle(self) -> dict:
        return self.formula().get("bottle", {})

    # ----------------------------------------------------------

    def dependencies(self) -> list[str]:
        return self.formula().get("dependencies", [])

    # ----------------------------------------------------------

    def build_dependencies(self) -> list[str]:
        return self.formula().get("build_dependencies", [])

    # ----------------------------------------------------------

    def optional_dependencies(self) -> list[str]:
        return self.formula().get("optional_dependencies", [])

    # ----------------------------------------------------------

    def version(self) -> str:
        # Check if bottle_info resolved a specific OCI tag version for this arch
        info = self.bottle_info()
        if info and info.get("_resolved_version"):
            return info["_resolved_version"]
        return self.formula()["versions"]["stable"]

    # ----------------------------------------------------------

    def homepage(self) -> str:
        return self.formula().get("homepage", "")

    # ----------------------------------------------------------

    def description(self) -> str:
        return self.formula().get("desc", "")

    # ----------------------------------------------------------

    def license(self):
        return self.formula().get("license", "")

    # ----------------------------------------------------------

    def revision(self) -> int:
        return self.formula().get("revision", 0)

    # ----------------------------------------------------------

    def _ghcr_fallback_bottle(self, oci_arch: str) -> dict | None:
        """Query GHCR OCI index in reverse tag order to find the newest darwin/<oci_arch> bottle."""
        if hasattr(self, "_cached_ghcr_bottle"):
            return self._cached_ghcr_bottle

        self._cached_ghcr_bottle = None
        ghcr_repo = self.name.replace("@", "/")
        try:
            tok_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:homebrew/core/{ghcr_repo}:pull"
            tok = json.loads(urllib.request.urlopen(tok_url, timeout=10).read())["token"]

            tags_req = urllib.request.Request(
                f"https://ghcr.io/v2/homebrew/core/{ghcr_repo}/tags/list",
                headers={"Authorization": f"Bearer {tok}"},
            )
            tags = json.loads(urllib.request.urlopen(tags_req, timeout=10).read()).get("tags", [])

            for tag in reversed(tags[-15:]):
                idx_req = urllib.request.Request(
                    f"https://ghcr.io/v2/homebrew/core/{ghcr_repo}/manifests/{tag}",
                    headers={
                        "Authorization": f"Bearer {tok}",
                        "Accept": "application/vnd.oci.image.index.v1+json",
                    },
                )
                idx = json.loads(urllib.request.urlopen(idx_req, timeout=10).read())
                for m in idx.get("manifests", []):
                    plat = m.get("platform", {})
                    if plat.get("os") == "darwin" and plat.get("architecture") in (oci_arch, "all"):
                        digest = m.get("annotations", {}).get("sh.brew.bottle.digest")
                        if digest:
                            ver = tag.split("-")[0]
                            self._cached_ghcr_bottle = {
                                "url": f"https://ghcr.io/v2/homebrew/core/{ghcr_repo}/blobs/sha256:{digest}",
                                "sha256": digest,
                                "_resolved_version": ver,
                            }
                            return self._cached_ghcr_bottle
        except Exception:
            pass

        return None

    def bottle_info(self, arch: str | None = None) -> dict | None:
        files = (
            self.bottle()
            .get("stable", {})
            .get("files", {})
        )

        target_arch = arch or ARCH

        # If targeting arm64 (Apple Silicon)
        if target_arch in ("arm64", "aarch64", "darwin_arm64"):
            for tag, info in files.items():
                if (tag.startswith("arm64") or tag == "all") and not tag.endswith("_linux"):
                    return info
            return self._ghcr_fallback_bottle("arm64")

        # If targeting x86_64 (Intel Mac) - never fall back to arm64 binaries
        if target_arch in ("x86_64", "darwin_x86_64"):
            for tag, info in files.items():
                if not tag.startswith("arm64") and not tag.endswith("_linux"):
                    return info
            return self._ghcr_fallback_bottle("amd64")

        return None


    def bottle_url(self, arch: str | None = None) -> str | None:
        info = self.bottle_info(arch)
        return info.get("url") if info else None


    def bottle_sha256(self, arch: str | None = None) -> str | None:
        info = self.bottle_info(arch)
        return info.get("sha256") if info else None


    # ----------------------------------------------------------

    def cellar(self) -> Path:

        proc = subprocess.run(
            [
                "brew",
                "--cellar",
                self.name,
            ],
            capture_output=True,
            text=True,
        )

        return Path(proc.stdout.strip())
