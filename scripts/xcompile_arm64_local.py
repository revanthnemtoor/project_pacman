#!/usr/bin/env python3
"""Local Xcode arm64 Cross-Compiler, Verifier & PGP Signer.
Builds darwin_arm64 packages locally using Xcode's universal MacOSX.sdk (`clang -arch arm64`),
isolated arm64 sysroot (`/tmp/arm64_sysroot/opt/pacman`), Meson cross-file, CMake arm64 toolchain,
Cargo `aarch64-apple-darwin`, and Go `GOARCH=arm64`, without touching the host `/opt/pacman`.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = PROJECT_DIR / "core"
EXTRA_DIR = PROJECT_DIR / "extra"
PACKAGES_DIR = PROJECT_DIR / "packages"

SYSROOT = Path("/tmp/arm64_sysroot")
TC_DIR = Path("/tmp/arm64_toolchain")
WRAP_DIR = TC_DIR / "wrappers"
WORK_ROOT = Path("/tmp/arm64_xbuild")
MAKEDIR_CFG = TC_DIR / "makepkg-arm64.conf"
MESON_CROSS = TC_DIR / "meson-arm64.ini"

GPG_BIN = "/opt/pacman/bin/gpg"
BSDTAR_BIN = "/opt/pacman/bin/bsdtar"
MAKEPKG_BIN = "/opt/pacman/bin/makepkg"
GPG_KEYID = "CEC5B78775CA4628"
PACKAGER = "Revanth Reddy Nemtoor <developerrevanth123@gmail.com>"

META_PACKAGES = {"base", "base-devel", "pacman-mirrorlist", "filesystem"}

# Packages that execute newly built target binaries during compilation (delegated to Apple Silicon CI)
SELF_HOSTING_CI_ONLY = {"perl", "guile", "icu", "nss", "neovim", "gcc", "python"}

ORDERED_QUEUE: list[str] = [
    # Pure data / config first
    "iana-etc", "filesystem", "tzdata",
    # Core libraries needed by downstream tools
    "zstd", "expat", "json-c", "readline",
    "gmp", "mpfr", "libmpc", "libisl",
    "npth", "libgpg-error", "libassuan", "libgcrypt", "libksba", "pinentry",
    "libedit", "dash", "m4", "autoconf", "libtool", "bison", "flex",
    "patch", "file", "which", "fakeroot",
    "nettle", "libtasn1", "gnutls",
    "libssh2", "libnghttp2", "libnghttp3", "libngtcp2",
    "gc", "gdbm", "jansson", "libinih", "libverto", "mpdecimal", "unixodbc",
    "libpcap", "ldns", "leancrypto", "libmicrohttpd",
    "libsasl", "openldap", "openssh",
    "nspr", "glib2", "libsecret",
    "groff", "man-db", "inetutils", "logrotate", "s-nail", "binutils",
    # Extra build tools, codecs & CLI tools
    "ninja", "meson", "ccache", "cmake", "pigz", "7zip",
    "jemalloc", "freetype2", "libwebp", "openjpeg2",
    "libde265", "kvazaar", "dav1d", "aom", "libheif", "libraw",
    "imagemagick", "qpdf", "chafa",
    "git", "htop", "entr", "yt-dlp", "mtr", "tcpdump", "tig", "aria2", "gh",
    "bat", "eza", "zoxide", "starship", "git-delta", "hyperfine",
    "just", "procs", "dust", "sd", "tealdeer", "tokei", "bottom", "xh",
]


def write_exec(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755)


def setup_toolchain_and_sysroot(reset_sysroot: bool = False) -> None:
    """Create /tmp/arm64_sysroot and cross-compiler wrappers."""
    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    TC_DIR.mkdir(parents=True, exist_ok=True)
    WRAP_DIR.mkdir(parents=True, exist_ok=True)

    if reset_sysroot and SYSROOT.exists():
        shutil.rmtree(SYSROOT)
    if not (SYSROOT / "opt/pacman/lib").exists():
        print("Seeding /tmp/arm64_sysroot from existing darwin_arm64 archives...", flush=True)
        SYSROOT.mkdir(parents=True, exist_ok=True)
        for repo_dir in (CORE_DIR, EXTRA_DIR):
            for pkg in sorted(repo_dir.glob("*-darwin_arm64.pkg.tar.zst")):
                subprocess.run([BSDTAR_BIN, "-xf", str(pkg), "-C", str(SYSROOT)], check=False, capture_output=True)

    # Purge any stale libtool .la files in sysroot so libtool never chases /opt/pacman/lib/*.la on host
    if (SYSROOT / "opt/pacman/lib").exists():
        for la in (SYSROOT / "opt/pacman/lib").rglob("*.la"):
            la.unlink(missing_ok=True)

    # 1. Clang / Clang++ cross-wrappers
    clang_wrapper = f"""#!/usr/bin/env python3
import os, sys, subprocess

prog = os.path.basename(sys.argv[0])
real = "/usr/bin/clang++" if ("++" in prog or prog == "g++") else "/usr/bin/clang"
sysroot_opt = "{SYSROOT}/opt/pacman"
sdk = "{sdk}"

args = sys.argv[1:]
is_compile_only = any(a in ("-c", "-E", "-S", "-M", "-MM") for a in args)
has_version_only = args in (["--version"], ["-v"], ["-dumpversion"], ["-dumpmachine"])

if has_version_only:
    if args == ["-dumpmachine"]:
        print("arm64-apple-darwin24.0.0")
        sys.exit(0)
    os.execv(real, [real] + args)

out = ["-arch", "arm64", "-isysroot", sdk, "-mmacosx-version-min=15.0", f"-I{{sysroot_opt}}/include"]
if not is_compile_only:
    out.append(f"-L{{sysroot_opt}}/lib")

i = 0
while i < len(args):
    a = args[i]
    if a == "-arch" and i + 1 < len(args):
        i += 2
        continue
    if a in ("-Wl,-ld_classic", "-ld_classic"):
        i += 1
        continue
    # Preserve Mach-O install_name and runtime rpath pointing to /opt/pacman/lib
    if a in ("-install_name", "-dylib_install_name", "-rpath") and i + 1 < len(args):
        out.extend([a, args[i + 1]])
        i += 2
        continue
    if a == "-Wl,-rpath" and i + 1 < len(args):
        out.extend([a, args[i + 1]])
        i += 2
        continue
    if a.startswith(("-Wl,-rpath,", "-Wl,-install_name,", "-Wl,-dylib_install_name,")):
        out.append(a)
        i += 1
        continue
    if a == "-I/opt/pacman/include":
        out.append(f"-I{{sysroot_opt}}/include")
    elif a.startswith("-I/opt/pacman/"):
        out.append("-I" + a[2:].replace("/opt/pacman/", f"{{sysroot_opt}}/", 1))
    elif a == "-L/opt/pacman/lib":
        out.append(f"-L{{sysroot_opt}}/lib")
    elif a.startswith("-L/opt/pacman/"):
        out.append("-L" + a[2:].replace("/opt/pacman/", f"{{sysroot_opt}}/", 1))
    elif a in ("-I", "-L") and i + 1 < len(args) and args[i + 1].startswith("/opt/pacman"):
        out.extend([a, args[i + 1].replace("/opt/pacman", sysroot_opt, 1)])
        i += 2
        continue
    elif a.startswith(("/opt/pacman/lib/", "/opt/pacman/include/")):
        # Rewrite direct dylib/archive paths injected by GNU libtool to arm64 sysroot
        out.append(a.replace("/opt/pacman/", f"{{sysroot_opt}}/", 1))
    else:
        out.append(a)
    i += 1

if not is_compile_only:
    out.extend(["-Wl,-rpath,/opt/pacman/lib", "-Wl,-headerpad_max_install_names"])

env = os.environ.copy()
env["MACOSX_DEPLOYMENT_TARGET"] = "15.0"
os.execve(real, [real] + out, env)
"""
    for old_w in ("clang", "clang++", "cc", "c++", "gcc", "g++"):
        (WRAP_DIR / old_w).unlink(missing_ok=True)
    for name in ("arm64-clang", "arm64-clang++", "arm64-apple-darwin-clang", "aarch64-apple-darwin-gcc", "aarch64-apple-darwin-g++"):
        write_exec(WRAP_DIR / name, clang_wrapper)

    # 2. pkg-config wrapper pointing exclusively to arm64 sysroot .pc files
    pkgconf_wrapper = f"""#!/usr/bin/env python3
import os, sys, subprocess

sysroot_opt = "{SYSROOT}/opt/pacman"
env = os.environ.copy()
env["PKG_CONFIG_LIBDIR"] = f"{{sysroot_opt}}/lib/pkgconfig:{{sysroot_opt}}/share/pkgconfig"
env.pop("PKG_CONFIG_PATH", None)
env.pop("PKG_CONFIG_SYSROOT_DIR", None)

res = subprocess.run(["/opt/pacman/bin/pkgconf"] + sys.argv[1:], capture_output=True, text=True, env=env)
stdout = res.stdout.replace("/opt/pacman/include", f"{{sysroot_opt}}/include").replace("/opt/pacman/lib", f"{{sysroot_opt}}/lib")
sys.stdout.write(stdout)
sys.stderr.write(res.stderr)
sys.exit(res.returncode)
"""
    for name in ("pkg-config", "pkgconf", "aarch64-apple-darwin-pkg-config"):
        write_exec(WRAP_DIR / name, pkgconf_wrapper)

    # 3. CMake wrapper injecting arm64 cross-compile & sysroot flags on configure
    cmake_wrapper = f"""#!/usr/bin/env python3
import os, sys

real = "/opt/pacman/bin/cmake"
sysroot_opt = "{SYSROOT}/opt/pacman"
sdk = "{sdk}"
args = sys.argv[1:]

is_subcmd = bool(args) and args[0] in ("--build", "--install", "-E", "--version", "--help", "-P")
rewritten = []
for a in args:
    if a.startswith("-DCMAKE_C_COMPILER="):
        rewritten.append("-DCMAKE_C_COMPILER={WRAP_DIR}/arm64-clang")
    elif a.startswith("-DCMAKE_CXX_COMPILER="):
        rewritten.append("-DCMAKE_CXX_COMPILER={WRAP_DIR}/arm64-clang++")
    elif a.startswith("-DCMAKE_PREFIX_PATH="):
        rewritten.append(f"-DCMAKE_PREFIX_PATH={{sysroot_opt}}")
    elif a.startswith("-DCMAKE_SYSTEM_PREFIX_PATH="):
        rewritten.append(f"-DCMAKE_SYSTEM_PREFIX_PATH={{sysroot_opt}};{{sdk}}/usr")
    elif a.startswith("-DCMAKE_OSX_ARCHITECTURES="):
        rewritten.append("-DCMAKE_OSX_ARCHITECTURES=arm64")
    else:
        rewritten.append(a)

if not is_subcmd:
    has_ninja = any(a == "Ninja" or a == "-GNinja" for a in rewritten)
    has_make_prog = any(a.startswith("-DCMAKE_MAKE_PROGRAM=") for a in rewritten)
    make_prog = "/opt/pacman/bin/ninja" if has_ninja else "/opt/pacman/bin/make"
    make_flag = [] if has_make_prog else [f"-DCMAKE_MAKE_PROGRAM={{make_prog}}"]
    rewritten = make_flag + [
        "-DCMAKE_SYSTEM_NAME=Darwin",
        "-DCMAKE_SYSTEM_PROCESSOR=arm64",
        "-DCMAKE_OSX_ARCHITECTURES=arm64",
        f"-DCMAKE_OSX_SYSROOT={{sdk}}",
        "-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
        "-DCMAKE_C_COMPILER={WRAP_DIR}/arm64-clang",
        "-DCMAKE_CXX_COMPILER={WRAP_DIR}/arm64-clang++",
        "-DCMAKE_AR=/usr/bin/ar",
        "-DCMAKE_RANLIB=/usr/bin/ranlib",
        "-DCMAKE_STRIP=/usr/bin/strip",
        "-DCMAKE_NM=/usr/bin/nm",
        "-DCMAKE_LINKER=/usr/bin/ld",
        "-DCMAKE_INSTALL_NAME_TOOL=/usr/bin/install_name_tool",
        f"-DCMAKE_PREFIX_PATH={{sysroot_opt}}",
        f"-DCMAKE_FIND_ROOT_PATH={{sysroot_opt}};{{sdk}}",
        "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER",
        "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY",
        "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY",
        "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=ONLY",
        "-DCMAKE_BUILD_WITH_INSTALL_NAME_DIR=ON",
        "-DCMAKE_INSTALL_NAME_DIR=/opt/pacman/lib",
        "-DCMAKE_INSTALL_RPATH=/opt/pacman/lib",
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        "-DKWSYS_LFS_WORKS=1",
        "-DKWSYS_LFS_WORKS__TRYRUN_OUTPUT=",
        "-DHAVE_POLL_FINE_EXITCODE=0",
        "-DHAVE_POLL_FINE_EXITCODE__TRYRUN_OUTPUT=",
    ] + rewritten

os.execv(real, [real] + rewritten)
"""
    write_exec(WRAP_DIR / "cmake", cmake_wrapper)

    # 4. Meson cross-file & wrapper
    MESON_CROSS.write_text(f"""[binaries]
c = '{WRAP_DIR}/arm64-clang'
cpp = '{WRAP_DIR}/arm64-clang++'
objc = '{WRAP_DIR}/arm64-clang'
ar = '/usr/bin/ar'
strip = '/usr/bin/strip'
pkgconfig = '{WRAP_DIR}/pkg-config'

[properties]
needs_exe_wrapper = true
growing_stack = false

[host_machine]
system = 'darwin'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'
""")
    meson_wrapper = f"""#!/usr/bin/env python3
import os, sys
real = "/opt/pacman/bin/meson"
args = sys.argv[1:]
if args and args[0] == "setup" and "--cross-file" not in args:
    args = ["setup", "--cross-file", "{MESON_CROSS}"] + args[1:]
os.execv(real, [real] + args)
"""
    write_exec(WRAP_DIR / "meson", meson_wrapper)

    # 5. Cargo wrapper (targets aarch64-apple-darwin & symlinks target/release)
    cargo_bin = str(TC_DIR / "cargo/bin/cargo")
    rustc_bin = str(TC_DIR / "cargo/bin/rustc")
    cargo_wrapper = f"""#!/usr/bin/env python3
import os, sys, subprocess
from pathlib import Path

cargo = "{cargo_bin}"
sysroot_opt = "{SYSROOT}/opt/pacman"
args = sys.argv[1:]
env = os.environ.copy()
env["RUSTUP_HOME"] = "{TC_DIR}/rustup"
env["CARGO_HOME"] = "{TC_DIR}/cargo"
env["CARGO_TARGET_AARCH64_APPLE_DARWIN_LINKER"] = "{WRAP_DIR}/arm64-clang"
env["CARGO_TARGET_X86_64_APPLE_DARWIN_LINKER"] = "/usr/bin/clang"
env["CC_aarch64_apple_darwin"] = "{WRAP_DIR}/arm64-clang"
env["CXX_aarch64_apple_darwin"] = "{WRAP_DIR}/arm64-clang++"
env["CC_x86_64_apple_darwin"] = "/usr/bin/clang"
env["CXX_x86_64_apple_darwin"] = "/usr/bin/clang++"
env["HOST_CC"] = "/usr/bin/clang"
env["HOST_CXX"] = "/usr/bin/clang++"
env["CFLAGS_x86_64_apple_darwin"] = ""
env["CXXFLAGS_x86_64_apple_darwin"] = ""
env["CC"] = "/usr/bin/clang"
env["CXX"] = "/usr/bin/clang++"
env["AR_aarch64_apple_darwin"] = "/usr/bin/ar"
env["PKG_CONFIG"] = "{WRAP_DIR}/pkg-config"
env["PKG_CONFIG_ALLOW_CROSS"] = "1"
env["MACOSX_DEPLOYMENT_TARGET"] = "15.0"
rf = env.get("RUSTFLAGS", "")
rf = rf.replace("-L/opt/pacman/lib", f"-L{{sysroot_opt}}/lib")
if "-Wl,-rpath,/opt/pacman/lib" not in rf:
    rf = (rf + f" -C link-arg=-Wl,-rpath,/opt/pacman/lib -C link-arg=-L{{sysroot_opt}}/lib").strip()
env["RUSTFLAGS"] = rf

if args and args[0] == "build" and "--target" not in args:
    for tc_file in ("rust-toolchain.toml", "rust-toolchain"):
        Path(tc_file).unlink(missing_ok=True)
    args = ["build", "--target", "aarch64-apple-darwin"] + args[1:]
    rc = subprocess.call([cargo] + args, env=env)
    if rc == 0:
        tdir = Path("target")
        arm_rel = tdir / "aarch64-apple-darwin" / "release"
        rel = tdir / "release"
        if arm_rel.is_dir():
            if rel.is_symlink():
                rel.unlink()
            elif rel.is_dir():
                for item in arm_rel.iterdir():
                    dest = rel / item.name
                    if item.is_file() and not dest.exists():
                        try:
                            os.symlink(item.resolve(), dest)
                        except Exception:
                            pass
            else:
                os.symlink("aarch64-apple-darwin/release", rel)
    sys.exit(rc)
else:
    os.execve(cargo, [cargo] + args, env)
"""
    write_exec(WRAP_DIR / "cargo", cargo_wrapper)
    if os.path.exists(rustc_bin):
        write_exec(
            WRAP_DIR / "rustc",
            f'#!/bin/sh\nexport RUSTUP_HOME="{TC_DIR}/rustup" CARGO_HOME="{TC_DIR}/cargo"\nexec "{rustc_bin}" "$@"\n',
        )

    # 6. Go wrapper (GOOS=darwin GOARCH=arm64)
    go_bin = str(TC_DIR / "go/bin/go")
    write_exec(
        WRAP_DIR / "go",
        f'#!/bin/sh\nexport GOROOT="{TC_DIR}/go" GOOS=darwin GOARCH=arm64 CGO_ENABLED="${{CGO_ENABLED:-0}}" CC="{WRAP_DIR}/arm64-clang"\nexec "{go_bin}" "$@"\n',
    )

    # 7. *-config scripts inside /tmp/arm64_sysroot/opt/pacman/bin (gpg-error-config, libgcrypt-config, ncursesw6-config, etc.)
    # Expose safe config scripts via wrappers so autotools finds arm64 flags
    refresh_sysroot_config_wrappers()

    # 8. makepkg-arm64.conf
    base_cfg = Path("/opt/pacman/etc/makepkg.conf").read_text()
    base_cfg = re.sub(r'^CARCH=.*$', 'CARCH="darwin_arm64"', base_cfg, flags=re.M)
    base_cfg = re.sub(r'^CHOST=.*$', 'CHOST="arm64-apple-darwin"', base_cfg, flags=re.M)
    base_cfg = re.sub(r'^PKGEXT=.*$', 'PKGEXT=".pkg.tar.zst"', base_cfg, flags=re.M)
    base_cfg = re.sub(r'^#*PACKAGER=.*$', f'PACKAGER="{PACKAGER}"', base_cfg, flags=re.M)
    MAKEDIR_CFG.write_text(base_cfg)


def refresh_sysroot_config_wrappers() -> None:
    """Wrap *-config shell scripts from arm64 sysroot so they emit sysroot paths."""
    sbin = SYSROOT / "opt/pacman/bin"
    if not sbin.is_dir():
        return
    for cfg in sbin.glob("*-config"):
        if cfg.is_symlink() or not cfg.is_file():
            continue
        head = cfg.read_bytes()[:4]
        if head in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"):
            continue  # skip arm64 Mach-O binaries; only wrap shell scripts!
        txt = cfg.read_text(errors="ignore")
        if txt.startswith("#!"):
            w = f"""#!/bin/sh
out="$("/bin/sh" "{cfg}" "$@")"
rc=$?
printf '%s\\n' "$out" | sed 's|-I/opt/pacman|-I{SYSROOT}/opt/pacman|g; s|-L/opt/pacman|-L{SYSROOT}/opt/pacman|g'
exit $rc
"""
            write_exec(WRAP_DIR / cfg.name, w)


def patch_pkgbuild_for_xcompile(src_pb: Path, pkgname: str) -> str:
    """Adapt a PKGBUILD in-memory so hardcoded tool/compiler paths route through WRAP_DIR."""
    txt = src_pb.read_text()
    # Route compilers & build tools through WRAP_DIR
    replacements = [
        ('"/usr/bin/clang++"', f'"{WRAP_DIR}/arm64-clang++"'),
        ("'/usr/bin/clang++'", f"'{WRAP_DIR}/arm64-clang++'"),
        ("=/usr/bin/clang++", f"={WRAP_DIR}/arm64-clang++"),
        ('"/usr/bin/clang"', f'"{WRAP_DIR}/arm64-clang"'),
        ("'/usr/bin/clang'", f"'{WRAP_DIR}/arm64-clang'"),
        ("=/usr/bin/clang", f"={WRAP_DIR}/arm64-clang"),
        ('"/opt/pacman/bin/pkg-config"', f'"{WRAP_DIR}/pkg-config"'),
        ('"/opt/pacman/bin/cmake"', f'"{WRAP_DIR}/cmake"'),
        ('"/opt/pacman/bin/meson"', f'"{WRAP_DIR}/meson"'),
        ('"/opt/pacman/bin/cargo"', f'"{WRAP_DIR}/cargo"'),
        ("for _cg in /opt/pacman/bin/cargo", f"for _cg in {WRAP_DIR}/cargo"),
        ("for _c in /opt/pacman/bin/cmake", f"for _c in {WRAP_DIR}/cmake"),
        ("for _m in /opt/pacman/bin/meson", f"for _m in {WRAP_DIR}/meson"),
        ("for _g in /opt/pacman/bin/go", f"for _g in {WRAP_DIR}/go"),
        ('export PATH="', f'export PATH="{WRAP_DIR}:'),
        ("/opt/pacman/bin/gpg-error-config", f"{WRAP_DIR}/gpg-error-config"),
        ("/opt/pacman/bin/libgcrypt-config", f"{WRAP_DIR}/libgcrypt-config"),
        ("/opt/pacman/bin/libassuan-config", f"{WRAP_DIR}/libassuan-config"),
        ("/opt/pacman/bin/ksba-config", f"{WRAP_DIR}/ksba-config"),
        ("/opt/pacman/bin/npth-config", f"{WRAP_DIR}/npth-config"),
        ("/opt/pacman/bin/curl-config", f"{WRAP_DIR}/curl-config"),
        ("--with-gmp=/opt/pacman", f"--with-gmp={SYSROOT}/opt/pacman"),
        ("--with-mpfr=/opt/pacman", f"--with-mpfr={SYSROOT}/opt/pacman"),
        ("--with-libunistring-prefix=/opt/pacman", f"--with-libunistring-prefix={SYSROOT}/opt/pacman"),
        ("--with-ssl-dir=/opt/pacman", f"--with-ssl-dir={SYSROOT}/opt/pacman"),
        ("--with-libedit=/opt/pacman", f"--with-libedit={SYSROOT}/opt/pacman"),
        ("--with-ldns=/opt/pacman", f"--with-ldns={SYSROOT}/opt/pacman"),
        ("--with-kerberos5=/opt/pacman", f"--with-kerberos5={SYSROOT}/opt/pacman"),
        ("--with-zlib=/opt/pacman", f"--with-zlib={SYSROOT}/opt/pacman"),
        ("CURLDIR=/opt/pacman", f"CURLDIR={SYSROOT}/opt/pacman"),
        ("OPENSSLDIR=/opt/pacman", f"OPENSSLDIR={SYSROOT}/opt/pacman"),
        ("EXPATDIR=/opt/pacman", f"EXPATDIR={SYSROOT}/opt/pacman"),
        ("ZLIB_PATH=/opt/pacman", f"ZLIB_PATH={SYSROOT}/opt/pacman"),
        ("LIBPCREDIR=/opt/pacman", f"LIBPCREDIR={SYSROOT}/opt/pacman"),
        ('C_INCLUDE_PATH="/opt/pacman/include"', f'C_INCLUDE_PATH="{SYSROOT}/opt/pacman/include"'),
        ('LD_LIBRARY_PATH="/opt/pacman/lib"', f'LD_LIBRARY_PATH="{SYSROOT}/opt/pacman/lib"'),
    ]
    for old, new in replacements:
        txt = txt.replace(old, new)

    # Skip running arm64 smoke test binary on x86_64 host in gmp
    if pkgname == "gmp":
        txt = txt.replace('DYLD_LIBRARY_PATH="$PWD/.libs" ./gmp_smoke_test', "true")

    # Inject GNU Autoconf cross-compilation flags (--build=x86_64-apple-darwin --host=aarch64-apple-darwin)
    # whenever ./configure is an Autoconf script and --host is not already specified.
    autoconf_helper = f"""
_orig_configure_xwrap() {{
  local _cfg="$1"; shift
  if grep -q "GNU Autoconf" "$_cfg" 2>/dev/null || grep -q "GNU Autoconf" builds/unix/configure 2>/dev/null; then
    case " $* " in
      *" --host="*|*" --host "*) "$_cfg" "$@" ;;
      *) "$_cfg" --build=x86_64-apple-darwin24.0.0 --host=aarch64-apple-darwin24.0.0 "$@" ;;
    esac
  else
    "$_cfg" "$@"
  fi
}}
"""
    txt = txt + "\n" + autoconf_helper
    txt = re.sub(r'(?<!-x )(?<!-f )(?<!-e )(?<![\w/.-])\./configure(?=\s|\\|$)', '_orig_configure_xwrap ./configure', txt)
    return txt


def verify_arm64_archive(pkg_path: Path) -> None:
    """Ensure every Mach-O inside pkg_path is arm64 and has no /tmp/arm64_sysroot or MacPorts leaks."""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([BSDTAR_BIN, "-xf", str(pkg_path), "-C", td], check=True)
        root = Path(td)
        non_opt = [
            str(p.relative_to(root))
            for p in root.iterdir()
            if not p.name.startswith(".") and p.name != "opt"
        ]
        if non_opt:
            raise RuntimeError(f"Non-/opt/pacman paths in archive: {non_opt}")

        for f in root.rglob("*"):
            if f.is_symlink() or not f.is_file():
                continue
            fout = subprocess.run(["/usr/bin/file", "-b", str(f)], capture_output=True, text=True).stdout
            if "Mach-O" not in fout:
                continue
            if "arm64" not in fout:
                raise RuntimeError(f"Mach-O {f.name} is NOT arm64: {fout.strip()}")
            oout = subprocess.run(["/usr/bin/otool", "-L", str(f)], capture_output=True, text=True).stdout
            for line in oout.splitlines()[1:]:
                dep = line.strip().split(" (")[0].strip()
                if dep.startswith(("/tmp/", "/opt/local", "/usr/local", "/opt/homebrew")):
                    raise RuntimeError(f"External dylib leak in {f.name}: {dep}")


def list_arch_packages(repo_dir: Path, arch: str) -> dict[str, Path]:
    out: dict[str, Path] = {}
    suffix = f"-{arch}.pkg.tar.zst"
    for p in sorted(repo_dir.glob(f"*{suffix}")):
        raw = p.name[: -len(suffix)]
        parts = raw.split("-")
        if len(parts) >= 3:
            out["-".join(parts[:-2])] = p
    return out


def compute_queue(only_pkg: str = "") -> list[tuple[str, str, Path]]:
    if only_pkg and only_pkg != "all":
        for repo in ("core", "extra"):
            pb = PACKAGES_DIR / repo / only_pkg / "PKGBUILD"
            if pb.is_file():
                return [(repo, only_pkg, pb)]
        raise SystemExit(f"No PKGBUILD found for {only_pkg}")

    core_x86 = list_arch_packages(CORE_DIR, "darwin_x86_64")
    core_arm = list_arch_packages(CORE_DIR, "darwin_arm64")
    extra_x86 = list_arch_packages(EXTRA_DIR, "darwin_x86_64")
    extra_arm = list_arch_packages(EXTRA_DIR, "darwin_arm64")

    missing: dict[str, tuple[str, Path]] = {}
    for repo_name, x86_map, arm_map in [("core", core_x86, core_arm), ("extra", extra_x86, extra_arm)]:
        for name in sorted(set(x86_map) - set(arm_map)):
            if name in SELF_HOSTING_CI_ONLY:
                continue
            pb = PACKAGES_DIR / repo_name / name / "PKGBUILD"
            if pb.is_file():
                missing[name] = (repo_name, pb)

    ordered: list[tuple[str, str, Path]] = []
    seen = set()
    for name in ORDERED_QUEUE:
        if name in missing:
            r, pb = missing[name]
            ordered.append((r, name, pb))
            seen.add(name)
    for name in sorted(missing):
        if name not in seen:
            r, pb = missing[name]
            ordered.append((r, name, pb))
    return ordered


def build_one(repo: str, pkgname: str, src_pb: Path) -> Path:
    work_dir = WORK_ROOT / f"{repo}_{pkgname}"
    if work_dir.exists():
        subprocess.run(["chmod", "-R", "u+rwx", str(work_dir)], check=False, capture_output=True)
        shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Copy any companion files (.patch, .c, .h, .1)
    for item in src_pb.parent.iterdir():
        if item.name == "PKGBUILD":
            continue
        if item.is_file() and not item.name.endswith((".zst", ".sig", ".gz", ".xz", ".bz2")):
            shutil.copy2(item, work_dir / item.name)

    (work_dir / "PKGBUILD").write_text(patch_pkgbuild_for_xcompile(src_pb, pkgname))

    sdk = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    env = os.environ.copy()
    env["PATH"] = f"{WRAP_DIR}:/opt/pacman/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["CARCH"] = "darwin_arm64"
    env["CHOST"] = "arm64-apple-darwin"
    env["CC"] = f"{WRAP_DIR}/arm64-clang"
    env["CXX"] = f"{WRAP_DIR}/arm64-clang++"
    env["CC_FOR_BUILD"] = "/usr/bin/clang"
    env["CXX_FOR_BUILD"] = "/usr/bin/clang++"
    env["BUILD_CC"] = "/usr/bin/clang"
    env["PKG_CONFIG"] = f"{WRAP_DIR}/pkg-config"
    env["SDKROOT"] = sdk
    env["MACOSX_DEPLOYMENT_TARGET"] = "15.0"
    env["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    # Prevent configure scripts from failing cross-compile checks when running host helpers
    env["cross_compiling"] = "yes"
    env["ac_cv_func_malloc_0_nonnull"] = "yes"
    env["ac_cv_func_realloc_0_nonnull"] = "yes"

    res = subprocess.run(
        [MAKEPKG_BIN, "--config", str(MAKEDIR_CFG), "-f", "-C", "--noconfirm", "--nodeps"],
        cwd=work_dir,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    if res.returncode != 0:
        raise RuntimeError(f"makepkg exited with {res.returncode}")

    built = sorted(
        list(work_dir.glob("*-darwin_arm64.pkg.tar.zst")) + list(work_dir.glob("*-any.pkg.tar.zst")),
        key=lambda p: p.stat().st_mtime,
    )
    if not built:
        raise FileNotFoundError("No .pkg.tar.zst produced")
    pkg_file = built[-1]
    sz = pkg_file.stat().st_size
    if pkgname not in META_PACKAGES and sz < 4096:
        raise RuntimeError(f"Archive too small ({sz} bytes)")

    verify_arm64_archive(pkg_file)

    dest_dir = CORE_DIR if repo == "core" else EXTRA_DIR
    final_name = pkg_file.name.replace("-any.pkg.tar.zst", "-darwin_arm64.pkg.tar.zst")
    for old in dest_dir.glob(f"{pkgname}-[0-9]*-darwin_arm64.pkg.tar.zst*"):
        old.unlink(missing_ok=True)
    target_pkg = dest_dir / final_name
    shutil.copyfile(pkg_file, target_pkg)

    # Sign with CEC5B78775CA4628
    sig = target_pkg.with_name(target_pkg.name + ".sig")
    sig.unlink(missing_ok=True)
    subprocess.run([GPG_BIN, "--detach-sign", "--batch", "--yes", "-u", GPG_KEYID, str(target_pkg)], check=True)

    # Extract into isolated arm64 sysroot so downstream packages can link against it
    subprocess.run([BSDTAR_BIN, "-xf", str(target_pkg), "-C", str(SYSROOT)], check=True)
    if (SYSROOT / "opt/pacman/lib").exists():
        for la in (SYSROOT / "opt/pacman/lib").rglob("*.la"):
            la.unlink(missing_ok=True)
    refresh_sysroot_config_wrappers()

    shutil.rmtree(work_dir, ignore_errors=True)
    return target_pkg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default="all")
    parser.add_argument("--repo", choices=["all", "core", "extra"], default="all")
    parser.add_argument("--reset-sysroot", action="store_true")
    args = parser.parse_args()

    setup_toolchain_and_sysroot(reset_sysroot=args.reset_sysroot)
    queue = compute_queue(args.package)
    if args.repo != "all":
        queue = [q for q in queue if q[0] == args.repo]

    print(f"Queued {len(queue)} darwin_arm64 package(s) for local Xcode cross-compilation.", flush=True)
    ok, fail = [], []
    for idx, (repo, pkgname, pb) in enumerate(queue, 1):
        t0 = time.time()
        print(f"\n[{idx}/{len(queue)}] >>> Cross-compiling {repo}/{pkgname} (darwin_arm64)...", flush=True)
        try:
            out_pkg = build_one(repo, pkgname, pb)
            dt = time.time() - t0
            print(f"✓ {out_pkg.name} ({out_pkg.stat().st_size / 1024:.1f} KB in {dt:.1f}s)", flush=True)
            ok.append(pkgname)
        except Exception as exc:
            print(f"✗ FAILED {repo}/{pkgname}: {exc}", flush=True)
            fail.append((f"{repo}/{pkgname}", str(exc)))

    print("\n" + "=" * 80)
    print(f"LOCAL XCOMPILE SUMMARY | Succeeded: {len(ok)} | Failed: {len(fail)}")
    if ok:
        print(f"  Succeeded: {', '.join(ok)}")
    if fail:
        for name, err in fail:
            print(f"  Failed   : {name} -> {err}")
    print("=" * 80, flush=True)
    if fail and not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
