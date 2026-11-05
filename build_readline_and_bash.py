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
BUILD_ENV["PATH"] = f"/opt/pacman/bin:/opt/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_ENV["CFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["CXXFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["LDFLAGS"] = "-L/opt/pacman/lib -arch x86_64"
BUILD_ENV["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
BUILD_ENV["PACKAGER"] = MAINTAINER

RECIPES = [
    {
        "name": "readline",
        "repo": "core",
        "version": "8.3",
        "rel": "1",
        "desc": "GNU readline library",
        "url": "https://tiswww.case.edu/php/chet/readline/rltop.html",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/readline/readline-8.3.tar.gz",
        "src_dir": "readline-8.3",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-curses"],
        "build": ["make", "SHLIB_LIBS=-lncursesw", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "bash",
        "repo": "core",
        "version": "5.3",
        "rel": "1",
        "desc": "Bourne-Again SHell, a UNIX command interpreter",
        "url": "https://www.gnu.org/software/bash/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/bash/bash-5.3.tar.gz",
        "src_dir": "bash-5.3",
        "configure": ["./configure", "--prefix=/opt/pacman", "--with-installed-readline=/opt/pacman", "--with-curses"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    }
]

def build_package(recipe, workdir):
    name = recipe["name"]
    version = recipe["version"]
    rel = recipe["rel"]
    target_dir = CORE_DIR
    
    print(f"\n{'='*60}")
    print(f"Building {name} {version}-{rel} from source...")
    print(f"{'='*60}")
    
    pkg_work = workdir / name
    pkg_work.mkdir(parents=True, exist_ok=True)
    
    tar_name = recipe["src_url"].split("/")[-1]
    tar_path = pkg_work / tar_name
    if not tar_path.exists():
        print(f"  -> Downloading {tar_name}...")
        subprocess.run(["curl", "-fsSL", recipe["src_url"], "-o", str(tar_path)], check=True)
        
    print(f"  -> Extracting {tar_name}...")
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(pkg_work)], check=True)
    src_dir = pkg_work / recipe["src_dir"]
    
    pkgdir = pkg_work / "pkg"
    pkgdir.mkdir(parents=True, exist_ok=True)
    
    if "configure" in recipe:
        print(f"  -> Configuring...")
        subprocess.run(recipe["configure"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "build" in recipe:
        print(f"  -> Building...")
        subprocess.run(recipe["build"], cwd=src_dir, env=BUILD_ENV, check=True)
        
    if "install" in recipe:
        print(f"  -> Installing to staging...")
        inst_cmd = [arg.replace("{pkgdir}", str(pkgdir)) for arg in recipe["install"]]
        subprocess.run(inst_cmd, cwd=src_dir, env=BUILD_ENV, check=True)

    print(f"  -> Codesigning Mach-O binaries...")
    for f in pkgdir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    subprocess.run(["codesign", "--sign", "-", "--force", str(f)], check=False, capture_output=True)
            except Exception:
                pass

    print(f"  -> Packaging native .pkg.tar.zst archive...")
    installed_size = sum(f.stat().st_size for f in pkgdir.rglob("*") if f.is_file() and not f.is_symlink())
    pkginfo = (
        f"pkgname = {name}\n"
        f"pkgver = {version}-{rel}\n"
        f"pkgdesc = {recipe['desc']} (built from source for macOS)\n"
        f"url = {recipe['url']}\n"
        f"builddate = 1730764800\n"
        f"packager = {MAINTAINER}\n"
        f"size = {installed_size}\n"
        f"arch = darwin_x86_64\n"
        f"license = {recipe['license']}\n"
    )
    (pkgdir / ".PKGINFO").write_text(pkginfo)
    (pkgdir / ".BUILDINFO").write_text(f"format = 2\npkgname = {name}\npkgver = {version}-{rel}\n")
    
    subprocess.run(
        "tar -czf .MTREE --format=mtree --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' *",
        cwd=pkgdir,
        shell=True,
        check=False
    )
    
    pkg_filename = f"{name}-{version}-{rel}-darwin_x86_64.pkg.tar.zst"
    dest_pkg = target_dir / pkg_filename
    
    for old_pkg in target_dir.glob(f"{name}-*-darwin_x86_64.pkg.tar.zst"):
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
    
    print(f"  -> Installing to live /opt/pacman prefix...")
    copy_opt = pkgdir / "opt/pacman"
    if copy_opt.exists():
        subprocess.run(f"cp -Rf {copy_opt}/* /opt/pacman/", shell=True, check=False)
        
    return dest_pkg

def main():
    with tempfile.TemporaryDirectory() as workdir:
        workdir = Path(workdir)
        for recipe in RECIPES:
            build_package(recipe, workdir)
        print("\nSuccessfully built Readline 8.3 and Bash 5.3!")

if __name__ == "__main__":
    main()

