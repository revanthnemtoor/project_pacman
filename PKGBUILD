pkgname=git
pkgver=2.55.0
pkgrel=1
pkgdesc="Distributed revision control system"

url="https://git-scm.com"
arch=(
    'arm64'
)
license=(
    'GPL-2.0-only AND GPL-2.0-or-later AND LGPL-2.1-or-later AND BSD-3-Clause AND MIT'
)
depends=(
    'gettext'
    'pcre2'
)
makedepends=(
    'gettext'
    'pkgconf'
)
options=('!strip')
source=()
sha256sums=()

package() {
    local _stage="$startdir/stage"
    local _dest="$pkgdir/usr"
    mkdir -p "$_dest"

    local _dirs=(bin sbin lib lib64 include share etc var libexec)
    for _d in "${_dirs[@]}"; do
        if [ -d "$_stage/$_d" ]; then
            cp -a "$_stage/$_d" "$_dest/"
        fi
    done
}