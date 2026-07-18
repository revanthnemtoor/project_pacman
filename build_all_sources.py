import os
import subprocess
import tempfile
import shutil
from pathlib import Path

FROMSOURCE_DIR = Path("/Users/revanthnemtoo/project_pacman/fromsource")
CORE_DIR = Path("/Users/revanthnemtoo/project_pacman/core")
PACMAN_BIN = Path("/opt/pacman/bin/pacman")
MAKEPKG_BIN = Path("/opt/pacman/bin/makepkg")
MAKEPKG_CONF = Path("/opt/pacman/etc/makepkg.conf")
REPO_ADD_BIN = Path("/opt/pacman/bin/repo-add")
REPO_DB = CORE_DIR / "core.db.tar.gz"

def codesign_and_repack(pkg_file: Path) -> None:
    """Extract, codesign Mach-O binaries, and repack."""
    print(f"  -> Codesigning binaries in {pkg_file.name}...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        subprocess.run(["tar", "-xf", str(pkg_file), "-C", str(tmpdir)], capture_output=True)
        
        signed = 0
        for path in tmpdir.rglob("*"):
            if path.is_file() and not path.is_symlink():
                # Simple check for Mach-O
                try:
                    with open(path, "rb") as f:
                        magic = f.read(4)
                        if magic in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe'):
                            result = subprocess.run(["codesign", "--sign", "-", "--force", str(path)], capture_output=True)
                            if result.returncode == 0:
                                signed += 1
                except Exception:
                    pass
                    
        if signed > 0:
            pack_cmd = (
                f"cd {tmpdir} && "
                f"tar -cf - .PKGINFO .BUILDINFO opt/ 2>/dev/null | "
                f"/opt/homebrew/bin/zstd -c -T0 -19 -z > {pkg_file.absolute()}"
            )
            subprocess.run(pack_cmd, shell=True, check=True)
            print(f"  -> Signed {signed} binaries")
            
            sig_file = pkg_file.with_name(pkg_file.name + ".sig")
            if sig_file.exists():
                sig_file.unlink()
        else:
            print(f"  -> No Mach-O binaries found to sign")

def build_package(pkgbuild_dir: Path):
    print(f"\n{'='*60}")
    print(f"Building {pkgbuild_dir.name} from source")
    print(f"{'='*60}")
    
    env = os.environ.copy()
    env["PKGDEST"] = str(CORE_DIR)
    
    # Path for gnubin (make, grep, etc during compilation)
    gnubin = "/opt/homebrew/opt/libtool/libexec/gnubin:/opt/homebrew/opt/bison/bin:/opt/homebrew/opt/make/libexec/gnubin:/opt/homebrew/opt/gettext/bin"
    if "PATH" in env:
        env["PATH"] = f"{gnubin}:{env['PATH']}"
    else:
        env["PATH"] = gnubin
        
    cmd = [
        str(MAKEPKG_BIN),
        "--config", str(MAKEPKG_CONF),
        "--sign",
        "--skipchecksums",
        "--skipinteg",
        "--nodeps",
        "-f",
        "-c" # Clean up after build
    ]
    
    result = subprocess.run(cmd, cwd=str(pkgbuild_dir), env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  -> ERROR: makepkg failed for {pkgbuild_dir.name}")
        print(f"  -> Output:\n{result.stderr[-500:]}")
        return None
        
    base_name = pkgbuild_dir.name
    if base_name.endswith('-src'):
        base_name = base_name[:-4]
    elif base_name.endswith('-mac'):
        base_name = base_name[:-4]
    
    pkg_files = list(CORE_DIR.glob(f"*{base_name}*.pkg.tar.zst"))
    if not pkg_files:
        print(f"  -> ERROR: Output package not found")
        return None
        
    # Get the newest one
    pkg_file = sorted(pkg_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    print(f"  -> Package built: {pkg_file.name}")
    
    # Codesign
    codesign_and_repack(pkg_file)
    
    # Re-sign the package for pacman
    print(f"  -> Signing package...")
    sig_file = pkg_file.with_name(pkg_file.name + ".sig")
    if sig_file.exists():
        sig_file.unlink()
    subprocess.run(["gpg", "--detach-sign", "--local-user", "276C37EC8DB2DCF235B3EAC02C3E87EC7EC39843", "--no-armor", str(pkg_file)], check=True)
    
    return pkg_file

def main():
    CORE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all directories with PKGBUILD
    pkgs_to_build = []
    for d in FROMSOURCE_DIR.iterdir():
        if d.is_dir() and (d / "PKGBUILD").exists():
            pkgs_to_build.append(d)
            
    print(f"Found {len(pkgs_to_build)} packages to build from source.")
    
    built_pkgs = []
    for pkg_dir in pkgs_to_build:
        # Check if already built in core
        base_name = pkg_dir.name
        if base_name.endswith('-src'):
            base_name = base_name[:-4]
        elif base_name.endswith('-mac'):
            base_name = base_name[:-4]
            
        existing = list(CORE_DIR.glob(f"{base_name}-*.pkg.tar.zst"))
        if existing:
            print(f"Package {pkg_dir.name} already built. Skipping.")
            built_pkgs.append(existing[0])
            continue
            
        pkg = build_package(pkg_dir)
        if pkg:
            built_pkgs.append(pkg)
            
    print(f"\n==> Updating repository database")
    for pkg in built_pkgs:
        try:
            subprocess.run([str(REPO_ADD_BIN), "--sign", str(REPO_DB), str(pkg)], check=True, capture_output=True)
            print(f"  -> Added {pkg.name}")
        except subprocess.CalledProcessError as e:
            print(f"  -> ERROR: Failed to add {pkg.name} to database: {e}")
        
    print("\nDONE! All packages rebuilt from source and database updated.")

if __name__ == "__main__":
    main()
