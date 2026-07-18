import json
import os
import shutil
import urllib.request
import tarfile
from pathlib import Path
import textwrap

SOURCES_FILE = Path("/Users/revanthnemtoo/project_pacman/fromsource/sources.json")
FROMSOURCE_DIR = Path("/Users/revanthnemtoo/project_pacman/fromsource")

def generate_pkgbuild(pkg_name, data):
    pkg_version = data.get("version", "1.0")
    pkg_desc = data.get("desc", "Package description")
    depends = data.get("depends", [])
    system = data.get("system", "autotools")
    url = data.get("url", "")
    
    depends_str = " ".join([f"'{d}'" for d in depends]) if depends else ""
    depends_line = f"depends=({depends_str})"
    
    build_cmds = ""
    if system == "autotools":
        build_cmds = textwrap.dedent("""\
            ./configure --prefix=/opt/pacman
            make
        """)
    elif system == "cmake":
        build_cmds = textwrap.dedent("""\
            cmake -B build -DCMAKE_INSTALL_PREFIX=/opt/pacman
            cmake --build build
        """)
    elif system == "meson":
        build_cmds = textwrap.dedent("""\
            meson setup build --prefix=/opt/pacman
            ninja -C build
        """)
    elif system == "cargo":
        build_cmds = textwrap.dedent("""\
            cargo build --release
        """)
    elif system == "go":
        build_cmds = textwrap.dedent("""\
            go build -trimpath -o build/
        """)
    else:
        build_cmds = "make\n"

    package_cmds = ""
    if system == "autotools":
        package_cmds = "make DESTDIR=\"$pkgdir/\" install\n"
    elif system == "cmake":
        package_cmds = "DESTDIR=\"$pkgdir/\" cmake --install build\n"
    elif system == "meson":
        package_cmds = "DESTDIR=\"$pkgdir/\" ninja -C build install\n"
    elif system == "cargo":
        package_cmds = "install -Dm755 target/release/* -t \"$pkgdir/opt/pacman/bin/\"\n"
    elif system == "go":
        package_cmds = "install -Dm755 build/* -t \"$pkgdir/opt/pacman/bin/\"\n"
    else:
        package_cmds = "make DESTDIR=\"$pkgdir/\" install\n"

    pkgbuild_content = textwrap.dedent(f"""\
        pkgname={pkg_name}
        pkgver={pkg_version}
        pkgrel=1
        pkgdesc="{pkg_desc}"
        arch=('darwin_arm64')
        url="{url}"
        license=('GPL')
        {depends_line}
        
        build() {{
            cd "$srcdir"
            {textwrap.indent(build_cmds, '    ').strip()}
        }}
        
        package() {{
            cd "$srcdir"
            {textwrap.indent(package_cmds, '    ').strip()}
        }}
    """)
    return pkgbuild_content

def download_and_extract(pkg_name, data):
    url = data.get("url")
    if not url:
        return False
        
    dest_dir = FROMSOURCE_DIR / f"{pkg_name}-src"
    if dest_dir.exists():
        # Already downloaded
        return True
        
    filename = url.split('/')[-1]
    tarball = FROMSOURCE_DIR / filename
    
    print(f"Downloading {pkg_name} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response, open(tarball, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print(f"Extracting {tarball.name}...")
        try:
            with tarfile.open(tarball, "r:*") as tar:
                tar.extractall(path=FROMSOURCE_DIR)
        except Exception as e:
            # Fallback to shell tar command
            print(f"tarfile failed ({e}), trying shell tar...")
            import subprocess
            subprocess.run(["tar", "-xf", str(tarball)], cwd=str(FROMSOURCE_DIR), check=True)
            
        # Find extracted directory
        extracted_dirs = [d for d in FROMSOURCE_DIR.iterdir() if d.is_dir() and pkg_name in d.name.lower() and d.name != f"{pkg_name}-src"]
        
        if extracted_dirs:
            extracted = extracted_dirs[0]
            print(f"Renaming {extracted.name} to {dest_dir.name}...")
            extracted.rename(dest_dir)
        else:
            print(f"Could not cleanly find extracted directory for {pkg_name}. Check manually.")
            
        # Generate PKGBUILD
        pkgbuild_content = generate_pkgbuild(pkg_name, data)
        with open(dest_dir / "PKGBUILD", "w") as f:
            f.write(pkgbuild_content)
            
        if tarball.exists():
            tarball.unlink()
        return True
    except Exception as e:
        print(f"Failed to download {pkg_name}: {e}")
        if tarball.exists():
            tarball.unlink()
        return False

def main():
    with open(SOURCES_FILE, "r") as f:
        sources = json.load(f)
        
    success = 0
    total = len(sources)
    print(f"Found {total} packages in sources.json. Starting mass download...")
    
    for pkg_name, data in sources.items():
        if download_and_extract(pkg_name, data):
            success += 1
            
    print(f"\nSuccessfully downloaded and prepared {success}/{total} packages.")

if __name__ == "__main__":
    main()
