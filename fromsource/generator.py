"""
PKGBUILD generator.

Takes a BuildProfile from the detector and generates a complete,
Arch-style PKGBUILD file tailored to the detected build system.

All generated PKGBUILDs target --prefix=/opt/pacman and use
macOS-compatible flags (clang, dylib, etc.).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

from fromsource.detector import BuildProfile, BuildSystem


INSTALL_PREFIX = "/opt/pacman"


class PKGBUILDGenerator:
    """Generates Arch-style PKGBUILD files from a BuildProfile."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str = "",
        url: str = "",
        license: str = "custom",
        depends: list[str] | None = None,
        source_dir: Path | None = None,
    ):
        self.name = name
        self.version = version
        self.description = description or f"{name} package"
        self.url = url
        self.license = license
        self.depends = depends or []
        self.source_dir = source_dir

    def generate(self, profile: BuildProfile) -> str:
        """Generate a complete PKGBUILD string for the given profile."""

        generators = {
            BuildSystem.AUTOTOOLS: self._gen_autotools,
            BuildSystem.CMAKE: self._gen_cmake,
            BuildSystem.MESON: self._gen_meson,
            BuildSystem.CARGO: self._gen_cargo,
            BuildSystem.GO: self._gen_go,
            BuildSystem.PYTHON: self._gen_python,
            BuildSystem.MAKE: self._gen_make,
        }

        gen_fn = generators.get(profile.system, self._gen_unknown)
        header = self._gen_header()
        prepare = self._gen_prepare(profile)
        build_and_package = gen_fn(profile)

        return header + prepare + build_and_package

    # -----------------------------------------------------------------
    # Header (common to all)
    # -----------------------------------------------------------------

    def _gen_header(self) -> str:
        deps_str = " ".join(f"'{d}'" for d in self.depends)
        return dedent(f"""\
            # Maintainer: Revanth Reddy Nemtoor
            pkgname={self.name}
            pkgver={self.version}
            pkgrel=1
            pkgdesc="{self.description}"
            arch=('darwin_arm64' 'aarch64' 'arm64')
            url="{self.url}"
            license=('{self.license}')
            depends=({deps_str})
            source=()

        """)

    def _gen_prepare(self, profile: BuildProfile) -> str:
        src_rel = profile.source_dir.name
        return dedent(f"""\
            prepare() {{
              cp -a "$startdir/../{src_rel}" "$srcdir/{self.name}"
            }}

        """)

    # -----------------------------------------------------------------
    # Autotools (configure / autogen.sh / autoreconf)
    # -----------------------------------------------------------------

    def _gen_autotools(self, profile: BuildProfile) -> str:
        autogen_block = ""
        if profile.has_autogen:
            autogen_block = dedent("""\
                  # Source is from git; needs autoreconf
                  if [ -f autogen.sh ]; then
                    ./autogen.sh
                  elif [ -f configure.ac ]; then
                    autoreconf -fiv
                  fi

            """)

        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"

              export CFLAGS="${{CFLAGS:--g -O2}} -I{INSTALL_PREFIX}/include"
              export LDFLAGS="${{LDFLAGS}} -L{INSTALL_PREFIX}/lib -liconv"
              export PKG_CONFIG_PATH="{INSTALL_PREFIX}/lib/pkgconfig"

            {autogen_block}              if [ "{self.name}" = "openssl" ]; then
                chmod +x ./config || true
                ./config --prefix={INSTALL_PREFIX} --openssldir={INSTALL_PREFIX}/etc/ssl
              elif [ -f ./configure ]; then
                chmod +x ./configure || true
                ./configure --prefix={INSTALL_PREFIX} --sysconfdir={INSTALL_PREFIX}/etc --disable-nls
              elif [ -f ./config ]; then
                chmod +x ./config || true
                ./config --prefix={INSTALL_PREFIX}
              fi

              make
            }}

            package() {{
              cd "$srcdir/{self.name}"
              make DESTDIR="$pkgdir" install
            }}
        """)

    # -----------------------------------------------------------------
    # CMake
    # -----------------------------------------------------------------

    def _gen_cmake(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              mkdir -p build && cd build

              cmake .. \\
                -DCMAKE_INSTALL_PREFIX={INSTALL_PREFIX} \\
                -DCMAKE_BUILD_TYPE=Release

              make
            }}

            package() {{
              cd "$srcdir/{self.name}/build"
              make DESTDIR="$pkgdir" install
            }}
        """)

    # -----------------------------------------------------------------
    # Meson
    # -----------------------------------------------------------------

    def _gen_meson(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"

              meson setup build \\
                --prefix={INSTALL_PREFIX} \\
                --buildtype=release

              meson compile -C build
            }}

            package() {{
              cd "$srcdir/{self.name}"
              DESTDIR="$pkgdir" meson install -C build
            }}
        """)

    # -----------------------------------------------------------------
    # Cargo (Rust)
    # -----------------------------------------------------------------

    def _gen_cargo(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              cargo build --release
            }}

            package() {{
              cd "$srcdir/{self.name}"
              install -Dm755 target/release/{self.name} "$pkgdir{INSTALL_PREFIX}/bin/{self.name}"
            }}
        """)

    # -----------------------------------------------------------------
    # Go
    # -----------------------------------------------------------------

    def _gen_go(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              export CGO_ENABLED=0
              go build -ldflags="-s -w" -o {self.name} .
            }}

            package() {{
              cd "$srcdir/{self.name}"
              install -Dm755 {self.name} "$pkgdir{INSTALL_PREFIX}/bin/{self.name}"
            }}
        """)

    # -----------------------------------------------------------------
    # Python
    # -----------------------------------------------------------------

    def _gen_python(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              python3 -m build --wheel --no-isolation
            }}

            package() {{
              cd "$srcdir/{self.name}"
              python3 -m installer --destdir="$pkgdir" dist/*.whl
            }}
        """)

    # -----------------------------------------------------------------
    # Plain Make
    # -----------------------------------------------------------------

    def _gen_make(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              make prefix={INSTALL_PREFIX} PREFIX={INSTALL_PREFIX}
            }}

            package() {{
              cd "$srcdir/{self.name}"
              make prefix={INSTALL_PREFIX} PREFIX={INSTALL_PREFIX} DESTDIR="$pkgdir" install
            }}
        """)

    # -----------------------------------------------------------------
    # Unknown / fallback
    # -----------------------------------------------------------------

    def _gen_unknown(self, profile: BuildProfile) -> str:
        return dedent(f"""\
            build() {{
              cd "$srcdir/{self.name}"
              echo "WARNING: Unknown build system. Manual PKGBUILD required."
              return 1
            }}

            package() {{
              cd "$srcdir/{self.name}"
              return 1
            }}
        """)
