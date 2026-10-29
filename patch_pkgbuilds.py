import os
from pathlib import Path

def patch_pkgbuild(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Skip if already patched
    if "prepare()" in content:
        return

    # Add prepare() function before build()
    prepare_block = """
prepare() {
    cp -a "$startdir"/* "$srcdir/" 2>/dev/null || true
}
"""
    content = content.replace("    build() {", prepare_block + "\n    build() {")
    content = content.replace("build() {", prepare_block + "\nbuild() {")

    # Inject CFLAGS, LDFLAGS, PKG_CONFIG_PATH into build() (supports both Apple Silicon /opt/homebrew and Intel /usr/local)
    env_block = """
        export CFLAGS="${CFLAGS:--g -O2} -I/opt/homebrew/include -I/usr/local/include -I/opt/pacman/include"
        export LDFLAGS="${LDFLAGS} -L/opt/homebrew/lib -L/usr/local/lib -L/opt/pacman/lib"
        export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:/usr/local/lib/pkgconfig:/opt/pacman/lib/pkgconfig"
"""
    content = content.replace('        cd "$srcdir"\n', f'        cd "$srcdir"\n{env_block}')
    content = content.replace('    cd "$srcdir"\n', f'    cd "$srcdir"\n{env_block}')

    with open(filepath, "w") as f:
        f.write(content)

def main():
    fromsource = Path(__file__).resolve().parent / "fromsource"
    count = 0
    for pkgdir in fromsource.glob("*-src"):
        if pkgdir.is_dir():
            pkgbuild = pkgdir / "PKGBUILD"
            if pkgbuild.exists():
                patch_pkgbuild(pkgbuild)
                count += 1
    
    print(f"Patched {count} PKGBUILDs successfully!")

if __name__ == "__main__":
    main()
