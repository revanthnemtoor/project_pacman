#!/usr/bin/env python3
import glob
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

GPG_KEY = "CEC5B78775CA4628"

def update_repo(repo_name):
    rdir = PROJECT_DIR / repo_name
    print(f"\n" + "="*50)
    print(f"Updating {repo_name} databases...")
    print("="*50)

    # 1. Clean existing db and files symlinks/archives/sigs
    for p in rdir.glob("*.db*"):
        try:
            p.unlink()
        except Exception:
            pass
    for p in rdir.glob("*.files*"):
        try:
            p.unlink()
        except Exception:
            pass

    # 2. Add darwin_x86_64 packages
    x86_pkgs = sorted([str(p) for p in rdir.glob("*-darwin_x86_64.pkg.tar.zst")])
    if x86_pkgs:
        db_x86 = rdir / f"{repo_name}-darwin_x86_64.db.tar.gz"
        print(f"  -> Indexing {len(x86_pkgs)} x86_64 packages into {db_x86.name} (with PGP signatures)...")
        cmd = ["/opt/pacman/bin/repo-add", "-q", "-s", "-k", GPG_KEY, "--include-sigs", str(db_x86)] + x86_pkgs
        subprocess.run(cmd, check=True)

        # Make aliases for default repo name
        for ext in [".db", ".db.tar.gz", ".files", ".files.tar.gz", ".db.sig", ".db.tar.gz.sig", ".files.sig", ".files.tar.gz.sig"]:
            src = rdir / f"{repo_name}-darwin_x86_64{ext}"
            dst = rdir / f"{repo_name}{ext}"
            if src.exists():
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                # Use copy so remote raw git URLs can serve directly
                shutil.copyfile(src.resolve(), dst)

    # 3. Add darwin_arm64 packages
    arm_pkgs = sorted([str(p) for p in rdir.glob("*-darwin_arm64.pkg.tar.zst")])
    if arm_pkgs:
        db_arm = rdir / f"{repo_name}-darwin_arm64.db.tar.gz"
        print(f"  -> Indexing {len(arm_pkgs)} arm64 packages into {db_arm.name} (with PGP signatures)...")
        cmd = ["/opt/pacman/bin/repo-add", "-q", "-s", "-k", GPG_KEY, "--include-sigs", str(db_arm)] + arm_pkgs
        subprocess.run(cmd, check=True)

    # Convert any symlinks created by repo-add into real binary files for GitHub raw compatibility
    for p in list(rdir.glob("*.db*")) + list(rdir.glob("*.files*")):
        if p.is_symlink():
            target = p.resolve()
            p.unlink()
            shutil.copyfile(target, p)

def main():
    update_repo("core")
    update_repo("extra")
    print("\nAll repository sync databases successfully rebuilt!")

if __name__ == "__main__":
    main()
