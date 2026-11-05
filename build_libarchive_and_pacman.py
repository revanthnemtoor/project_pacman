#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
CORE_DIR = PROJECT_DIR / "core"
MAINTAINER = "Revanth Reddy Nemtoor <developerrevanth123@gmail.com>"

BUILD_ENV = os.environ.copy()
BUILD_ENV["PATH"] = f"/opt/pacman/bin:/usr/local/bin:/opt/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_ENV["CFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["CXXFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["LDFLAGS"] = "-L/opt/pacman/lib -arch x86_64"
BUILD_ENV["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
BUILD_ENV["PACKAGER"] = MAINTAINER

def build_libarchive(workdir):
    if (Path("/opt/pacman/lib/libarchive.dylib").exists() and Path("/opt/pacman/lib/pkgconfig/libarchive.pc").exists()):
        print("  -> libarchive is already built and installed in /opt/pacman!")
        return
    print("\n" + "="*60)
    print("Building libarchive 3.7.7 from source...")
    print("="*60)
    
    pkg_work = workdir / "libarchive"
    pkg_work.mkdir(parents=True, exist_ok=True)
    tar_path = pkg_work / "libarchive-3.7.7.tar.xz"
    if not tar_path.exists():
        print("  -> Downloading libarchive-3.7.7...")
        subprocess.run(["curl", "-fsSL", "https://github.com/libarchive/libarchive/releases/download/v3.7.7/libarchive-3.7.7.tar.xz", "-o", str(tar_path)], check=True)
        
    print("  -> Extracting...")
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(pkg_work)], check=True)
    src_dir = pkg_work / "libarchive-3.7.7"
    pkgdir = pkg_work / "pkg"
    pkgdir.mkdir(parents=True, exist_ok=True)
    
    print("  -> Configuring...")
    subprocess.run(["./configure", "--prefix=/opt/pacman", "--with-zlib", "--with-bz2lib", "--with-lzma", "--with-lz4", "--with-zstd", "--with-openssl", "--without-xml2"], cwd=src_dir, env=BUILD_ENV, check=True)
    
    print("  -> Building...")
    subprocess.run(["make", "-j8"], cwd=src_dir, env=BUILD_ENV, check=True)
    
    print("  -> Installing to staging...")
    subprocess.run(["make", f"DESTDIR={pkgdir}", "install"], cwd=src_dir, env=BUILD_ENV, check=True)
    
    print("  -> Codesigning...")
    for f in pkgdir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    subprocess.run(["codesign", "--sign", "-", "--force", str(f)], check=False, capture_output=True)
            except Exception:
                pass
                
    # Also install to live /opt/pacman
    copy_opt = pkgdir / "opt/pacman"
    if copy_opt.exists():
        subprocess.run(f"cp -Rf {copy_opt}/* /opt/pacman/", shell=True, check=False)
        
    print("  -> libarchive installed to /opt/pacman successfully!")

def build_pacman(workdir):
    print("\n" + "="*60)
    print("Building pacman 7.1.0 from source...")
    print("="*60)
    
    pkg_work = workdir / "pacman"
    pkg_work.mkdir(parents=True, exist_ok=True)
    pkgdir = pkg_work / "pkg"
    pkgdir.mkdir(parents=True, exist_ok=True)
    
    build_dir = pkg_work / "build_native"
    shutil.rmtree(build_dir, ignore_errors=True)
    
    pacman_src = PROJECT_DIR / "pacman"
    
    meson_cmd = [
        "meson", "setup", str(build_dir), str(pacman_src),
        "--prefix=/opt/pacman",
        "--sysconfdir=/opt/pacman/etc",
        "--localstatedir=/opt/pacman/var",
        "-Dpkg-ext=.pkg.tar.zst",
        "-Dcrypto=openssl",
        "-Ddoc=disabled",
        "-Dgpgme=disabled",
        "-Dc_link_args=-L/opt/pacman/lib -lintl",
        "-Dbuild.c_link_args=-L/opt/pacman/lib -lintl"
    ]
    print("  -> Meson setup...")
    subprocess.run(meson_cmd, env=BUILD_ENV, check=True)
    
    print("  -> Ninja build...")
    subprocess.run(["ninja", "-C", str(build_dir)], env=BUILD_ENV, check=True)
    
    print("  -> Installing to staging...")
    subprocess.run(["meson", "install", "-C", str(build_dir), "--destdir", str(pkgdir)], env=BUILD_ENV, check=True)
    
    # Remove var
    shutil.rmtree(pkgdir / "opt/pacman/var", ignore_errors=True)
    
    print("  -> Codesigning...")
    for f in pkgdir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    subprocess.run(["codesign", "--sign", "-", "--force", str(f)], check=False, capture_output=True)
            except Exception:
                pass
                
    installed_size = sum(f.stat().st_size for f in pkgdir.rglob("*") if f.is_file() and not f.is_symlink())
    pkginfo = (
        "pkgname = pacman\n"
        "pkgver = 7.1.0-1\n"
        "pkgdesc = A library-based package manager with dependency support (Darwin native port, built from source)\n"
        "url = https://gitlab.archlinux.org/pacman/pacman\n"
        "builddate = 1730764800\n"
        f"packager = {MAINTAINER}\n"
        f"size = {installed_size}\n"
        "arch = darwin_x86_64\n"
        "license = GPL-2.0-or-later\n"
        "depend = openssl\n"
        "depend = zstd\n"
        "depend = bash\n"
    )
    (pkgdir / ".PKGINFO").write_text(pkginfo)
    (pkgdir / ".BUILDINFO").write_text("format = 2\npkgname = pacman\npkgver = 7.1.0-1\n")
    
    dest_pkg = CORE_DIR / "pacman-7.1.0-1-darwin_x86_64.pkg.tar.zst"
    for old_pkg in CORE_DIR.glob("pacman-*-darwin_x86_64.pkg.tar.zst"):
        old_pkg.unlink()
        
    filelist = pkg_work / "filelist.txt"
    with open(filelist, "w") as fl:
        for root, dirs, files in os.walk(pkgdir):
            for file in sorted(files):
                full = Path(root) / file
                rel_f = full.relative_to(pkgdir)
                fl.write(f"{rel_f}\n")
                
    tar_cmd = f"cd {pkgdir} && tar -cf - -T {filelist} | zstd -c -T0 -19 -z > {dest_pkg}"
    subprocess.run(tar_cmd, shell=True, check=True)
    print(f"  -> Package built successfully: {dest_pkg.name} ({dest_pkg.stat().st_size:,} bytes)")
    
    print("  -> Installing to live /opt/pacman prefix...")
    copy_opt = pkgdir / "opt/pacman"
    if copy_opt.exists():
        subprocess.run(f"cp -Rf {copy_opt}/* /opt/pacman/", shell=True, check=False)
        
    return dest_pkg

def main():
    with tempfile.TemporaryDirectory() as workdir:
        workdir = Path(workdir)
        build_libarchive(workdir)
        build_pacman(workdir)
        print("\nSuccessfully built libarchive and pacman natively from source!")

if __name__ == "__main__":
    main()

