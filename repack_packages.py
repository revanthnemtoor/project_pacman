import os
import subprocess
import tempfile
from pathlib import Path
import shutil

CORE_DIR = Path("/Users/revanthnemtoo/project_pacman/core")
PACMAN_ROOT = Path("/opt/pacman")
REPO_DB = CORE_DIR / "core.db.tar.gz"

def is_broken(pkg_file: Path) -> bool:
    # Check if the tarball has 'opt/pacman' in its root
    result = subprocess.run(["tar", "-tf", str(pkg_file)], capture_output=True, text=True)
    if result.returncode != 0:
        return False
    
    # We only care about top-level directories in the archive
    # A correct package has opt/pacman/...
    # A broken package has bin/, lib/, share/, etc.
    lines = result.stdout.splitlines()
    for line in lines:
        if line.startswith("opt/pacman"):
            return False
    return True

def repack(pkg_file: Path):
    print(f"Repacking {pkg_file.name}...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Extract the archive
        subprocess.run(["tar", "-xf", str(pkg_file), "-C", str(tmpdir)], check=True)
        
        # Create opt/pacman directory
        opt_pacman = tmpdir / "opt" / "pacman"
        opt_pacman.mkdir(parents=True, exist_ok=True)
        
        # Move everything EXCEPT .PKGINFO, .BUILDINFO, .MTREE, and opt into opt/pacman
        for item in tmpdir.iterdir():
            if item.name in [".PKGINFO", ".BUILDINFO", ".MTREE", "opt"]:
                continue
            
            dest = opt_pacman / item.name
            shutil.move(str(item), str(dest))
            
        # Re-create .MTREE since the paths changed!
        # Or better, just delete .MTREE because pacman can install without it
        mtree_file = tmpdir / ".MTREE"
        if mtree_file.exists():
            mtree_file.unlink()
            
        # Repack the archive
        # Use zstd to compress it back
        pack_cmd = (
            f"cd {tmpdir} && "
            f"tar -cf - .PKGINFO .BUILDINFO opt/ 2>/dev/null | "
            f"/opt/pacman/bin/zstd -c -T0 -19 -z > {pkg_file.absolute()}"
        )
        subprocess.run(pack_cmd, shell=True, check=True)
        
        # Remove old signature
        sig = pkg_file.with_name(pkg_file.name + ".sig")
        if sig.exists():
            sig.unlink()

def main():
    broken = []
    for pkg_file in CORE_DIR.glob("*.pkg.tar.zst"):
        if is_broken(pkg_file):
            broken.append(pkg_file)
            
    print(f"Found {len(broken)} broken packages.")
    
    for pkg in broken:
        repack(pkg)
        
    print("Updating repository database...")
    for pkg in CORE_DIR.glob("*.pkg.tar.zst"):
        subprocess.run(["/opt/pacman/bin/repo-add", str(REPO_DB), str(pkg)], check=True, capture_output=True)
        
    print("Done!")

if __name__ == "__main__":
    main()
