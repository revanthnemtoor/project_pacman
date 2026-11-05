#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
FROMSOURCE_DIR = PROJECT_DIR / "fromsource"
PACMAN_ROOT = Path("/opt/pacman")

from env_loader import get_packager

MAINTAINER = get_packager()

# Environment: strictly use /opt/pacman and macOS system SDK, never Homebrew
BUILD_ENV = os.environ.copy()
BUILD_ENV["PATH"] = f"/opt/pacman/bin:/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_ENV["CFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["CXXFLAGS"] = "-O2 -I/opt/pacman/include -arch x86_64"
BUILD_ENV["LDFLAGS"] = "-L/opt/pacman/lib -arch x86_64"
BUILD_ENV["PKG_CONFIG_PATH"] = "/opt/pacman/lib/pkgconfig"
BUILD_ENV["PACKAGER"] = MAINTAINER

RECIPES = [
    {
        "name": "zlib",
        "repo": "core",
        "version": "1.3.1",
        "rel": "1",
        "desc": "Compression library implementing deflate found in gzip/PKZIP",
        "url": "https://zlib.net/",
        "license": "Zlib",
        "src_url": "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz",
        "src_dir": "zlib-1.3.1",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "bzip2",
        "repo": "core",
        "version": "1.0.8",
        "rel": "1",
        "desc": "Freely available high-quality data compressor",
        "url": "https://sourceware.org/bzip2/",
        "license": "BSD-like",
        "src_url": "https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz",
        "src_dir": "bzip2-1.0.8",
        "custom_build": True,
    },
    {
        "name": "lz4",
        "repo": "core",
        "version": "1.10.0",
        "rel": "1",
        "desc": "Extremely Fast Compression algorithm",
        "url": "https://lz4.org/",
        "license": "BSD-2-Clause",
        "src_url": "https://github.com/lz4/lz4/archive/refs/tags/v1.10.0.tar.gz",
        "src_dir": "lz4-1.10.0",
        "build": ["make", "PREFIX=/opt/pacman", "-j8"],
        "install": ["make", "PREFIX=/opt/pacman", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "zstd",
        "repo": "core",
        "version": "1.5.7",
        "rel": "1",
        "desc": "Zstandard - Fast real-time compression algorithm",
        "url": "https://facebook.github.io/zstd/",
        "license": "BSD-3-Clause",
        "src_url": "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
        "src_dir": "zstd-1.5.7",
        "build": ["make", "PREFIX=/opt/pacman", "-j8"],
        "install": ["make", "PREFIX=/opt/pacman", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "m4",
        "repo": "core",
        "version": "1.4.19",
        "rel": "1",
        "desc": "GNU macro processor",
        "url": "https://www.gnu.org/software/m4/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/m4/m4-1.4.19.tar.gz",
        "src_dir": "m4-1.4.19",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "make",
        "repo": "core",
        "version": "4.4.1",
        "rel": "1",
        "desc": "GNU make utility to maintain groups of programs",
        "url": "https://www.gnu.org/software/make/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz",
        "src_dir": "make-4.4.1",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "diffutils",
        "repo": "core",
        "version": "3.10",
        "rel": "1",
        "desc": "GNU diff utilities",
        "url": "https://www.gnu.org/software/diffutils/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/diffutils/diffutils-3.10.tar.xz",
        "src_dir": "diffutils-3.10",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "sed",
        "repo": "core",
        "version": "4.9",
        "rel": "1",
        "desc": "GNU stream editor",
        "url": "https://www.gnu.org/software/sed/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/sed/sed-4.9.tar.xz",
        "src_dir": "sed-4.9",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "grep",
        "repo": "core",
        "version": "3.11",
        "rel": "1",
        "desc": "GNU grep, egrep and fgrep",
        "url": "https://www.gnu.org/software/grep/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/grep/grep-3.11.tar.xz",
        "src_dir": "grep-3.11",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "tar",
        "repo": "core",
        "version": "1.35",
        "rel": "1",
        "desc": "GNU archiving utility",
        "url": "https://www.gnu.org/software/tar/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/tar/tar-1.35.tar.xz",
        "src_dir": "tar-1.35",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "gzip",
        "repo": "core",
        "version": "1.13",
        "rel": "1",
        "desc": "GNU popular data compression program",
        "url": "https://www.gnu.org/software/gzip/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/gzip/gzip-1.13.tar.xz",
        "src_dir": "gzip-1.13",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "less",
        "repo": "core",
        "version": "668",
        "rel": "1",
        "desc": "A terminal based program for viewing text files",
        "url": "https://www.greenwoodsoftware.com/less/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://www.greenwoodsoftware.com/less/less-668.tar.gz",
        "src_dir": "less-668",
        "configure": ["./configure", "--prefix=/opt/pacman", "--sysconfdir=/opt/pacman/etc"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "tree",
        "repo": "extra",
        "version": "2.2.1",
        "rel": "1",
        "desc": "A recursive directory listing command",
        "url": "https://gitlab.com/OldManProgrammer/unix-tree",
        "license": "GPL-2.0-or-later",
        "src_url": "https://gitlab.com/OldManProgrammer/unix-tree/-/archive/2.2.1/unix-tree-2.2.1.tar.gz",
        "src_dir": "unix-tree-2.2.1",
        "build": ["make", "PREFIX=/opt/pacman", "-j8"],
        "install": ["make", "PREFIX=/opt/pacman", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "which",
        "repo": "core",
        "version": "2.21",
        "rel": "1",
        "desc": "Utility that prints the full path of executables",
        "url": "https://carlowood.github.io/which/",
        "license": "GPL-3.0-or-later",
        "src_url": "https://ftp.gnu.org/gnu/which/which-2.21.tar.gz",
        "src_dir": "which-2.21",
        "configure": ["./configure", "--prefix=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "oniguruma",
        "repo": "extra",
        "version": "6.9.9",
        "rel": "1",
        "desc": "Regular expressions library",
        "url": "https://github.com/kkos/oniguruma",
        "license": "BSD-2-Clause",
        "src_url": "https://github.com/kkos/oniguruma/releases/download/v6.9.9/onig-6.9.9.tar.gz",
        "src_dir": "onig-6.9.9",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    },
    {
        "name": "jq",
        "repo": "extra",
        "version": "1.7.1",
        "rel": "1",
        "desc": "Command-line JSON processor",
        "url": "https://jqlang.github.io/jq/",
        "license": "MIT",
        "src_url": "https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-1.7.1.tar.gz",
        "src_dir": "jq-1.7.1",
        "configure": ["./configure", "--prefix=/opt/pacman", "--disable-dependency-tracking", "--with-oniguruma=/opt/pacman"],
        "build": ["make", "-j8"],
        "install": ["make", "DESTDIR={pkgdir}", "install"],
    }
]

def build_package(recipe, workdir):
    name = recipe["name"]
    version = recipe["version"]
    rel = recipe["rel"]
    repo = recipe["repo"]
    target_dir = EXTRA_DIR if repo == "extra" else CORE_DIR
    
    print(f"\n{'='*60}")
    print(f"Building {name} {version}-{rel} from source for {repo}...")
    print(f"{'='*60}")
    
    pkg_work = workdir / name
    pkg_work.mkdir(parents=True, exist_ok=True)
    
    # 1. Download source tarball
    tar_name = recipe["src_url"].split("/")[-1]
    tar_path = pkg_work / tar_name
    if not tar_path.exists():
        print(f"  -> Downloading {tar_name}...")
        subprocess.run(["curl", "-fsSL", recipe["src_url"], "-o", str(tar_path)], check=True)
        
    # 2. Extract
    print(f"  -> Extracting {tar_name}...")
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(pkg_work)], check=True)
    src_dir = pkg_work / recipe["src_dir"]
    
    # 3. Build & Install into staging pkgdir
    pkgdir = pkg_work / "pkg"
    pkgdir.mkdir(parents=True, exist_ok=True)
    
    if recipe.get("custom_build") and name == "bzip2":
        # bzip2 has custom makefile
        makefile_dylib = (
            "CC = clang\n"
            "AR = ar\n"
            "RANLIB = ranlib\n"
            "CFLAGS = -O2 -arch x86_64 -fPIC\n"
            "OBJS= blocksort.o huffman.o crctable.o randtable.o compress.o decompress.o bzlib.o\n"
            "all: libbz2.dylib bzip2 bzip2recover\n"
            "bzip2: libbz2.dylib bzip2.o\n\t$(CC) $(CFLAGS) -o bzip2 bzip2.o -L. -lbz2\n"
            "bzip2recover: bzip2recover.o\n\t$(CC) $(CFLAGS) -o bzip2recover bzip2recover.o\n"
            "libbz2.dylib: $(OBJS)\n\t$(CC) -dynamiclib -install_name /opt/pacman/lib/libbz2.1.0.dylib -compatibility_version 1.0 -current_version 1.0.8 -o libbz2.1.0.8.dylib $(OBJS)\n"
            "\tln -sf libbz2.1.0.8.dylib libbz2.1.0.dylib\n\tln -sf libbz2.1.0.dylib libbz2.dylib\n"
            "\t$(AR) cq libbz2.a $(OBJS)\n\t$(RANLIB) libbz2.a\n"
        )
        (src_dir / "Makefile-darwin").write_text(makefile_dylib)
        subprocess.run(["make", "-f", "Makefile-darwin", "-j8"], cwd=src_dir, env=BUILD_ENV, check=True)
        dest_bin = pkgdir / "opt/pacman/bin"
        dest_lib = pkgdir / "opt/pacman/lib"
        dest_inc = pkgdir / "opt/pacman/include"
        dest_man = pkgdir / "opt/pacman/share/man/man1"
        for d in [dest_bin, dest_lib, dest_inc, dest_man]:
            d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_dir / "bzip2", dest_bin / "bzip2")
        shutil.copy2(src_dir / "bzip2recover", dest_bin / "bzip2recover")
        shutil.copy2(src_dir / "bzlib.h", dest_inc / "bzlib.h")
        shutil.copy2(src_dir / "bzip2.1", dest_man / "bzip2.1")
        shutil.copy2(src_dir / "libbz2.1.0.8.dylib", dest_lib / "libbz2.1.0.8.dylib")
        shutil.copy2(src_dir / "libbz2.a", dest_lib / "libbz2.a")
        (dest_lib / "libbz2.1.0.dylib").symlink_to("libbz2.1.0.8.dylib")
        (dest_lib / "libbz2.dylib").symlink_to("libbz2.1.0.dylib")
        for sym in ["bunzip2", "bzcat"]:
            (dest_bin / sym).symlink_to("bzip2")
    else:
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

    # 4. Ad-hoc codesign all Mach-O binaries in staging
    print(f"  -> Codesigning Mach-O binaries...")
    for f in pkgdir.rglob("*"):
        if f.is_file() and not f.is_symlink():
            try:
                res = subprocess.run(["file", str(f)], capture_output=True, text=True)
                if "Mach-O" in res.stdout:
                    subprocess.run(["codesign", "--sign", "-", "--force", str(f)], check=False, capture_output=True)
            except Exception:
                pass

    # 5. Generate package metadata: .PKGINFO, .BUILDINFO, .MTREE
    print(f"  -> Packaging native .pkg.tar.zst archive...")
    pkginfo = (
        f"pkgname = {name}\n"
        f"pkgver = {version}-{rel}\n"
        f"pkgdesc = {recipe['desc']} (built from source for macOS)\n"
        f"url = {recipe['url']}\n"
        f"builddate = 1730764800\n"
        f"packager = {MAINTAINER}\n"
        f"size = 1000000\n"
        f"arch = darwin_x86_64\n"
        f"license = {recipe['license']}\n"
    )
    (pkgdir / ".PKGINFO").write_text(pkginfo)
    (pkgdir / ".BUILDINFO").write_text(f"format = 2\npkgname = {name}\npkgver = {version}-{rel}\n")
    
    # Generate .MTREE with bsdtar
    subprocess.run(
        "tar -czf .MTREE --format=mtree --options='!all,use-set,type,uid,gid,mode,time,size,md5,sha256,link' *",
        cwd=pkgdir,
        shell=True,
        check=False
    )
    
    # Pack into .pkg.tar.zst
    pkg_filename = f"{name}-{version}-{rel}-darwin_x86_64.pkg.tar.zst"
    dest_pkg = target_dir / pkg_filename
    
    # Remove old version if present
    for old_pkg in target_dir.glob(f"{name}-*-darwin_x86_64.pkg.tar.zst"):
        old_pkg.unlink()
        
    filelist = pkg_work / "filelist.txt"
    with open(filelist, "w") as fl:
        for root, dirs, files in os.walk(pkgdir):
            for file in sorted(files):
                full = Path(root) / file
                rel = full.relative_to(pkgdir)
                fl.write(f"{rel}\n")
                
    tar_cmd = f"cd {pkgdir} && tar -cf - -T {filelist} | zstd -c -T0 -19 -z > {dest_pkg}"
    subprocess.run(tar_cmd, shell=True, check=True)
    print(f"  -> Package built successfully: {dest_pkg.name} ({dest_pkg.stat().st_size:,} bytes)")
    
    # Also install to live /opt/pacman prefix so subsequent packages can link against it!
    print(f"  -> Installing to live /opt/pacman prefix...")
    copy_opt = pkgdir / "opt/pacman"
    if copy_opt.exists():
        subprocess.run(f"cp -Rf {copy_opt}/* /opt/pacman/", shell=True, check=False)
        
    return dest_pkg

def main():
    with tempfile.TemporaryDirectory() as workdir:
        workdir = Path(workdir)
        built = []
        for recipe in RECIPES:
            try:
                pkg = build_package(recipe, workdir)
                built.append(pkg)
            except Exception as e:
                print(f"ERROR building {recipe['name']}: {e}")
                
        print(f"\nSuccessfully built {len(built)} packages from source!")

if __name__ == "__main__":
    main()
