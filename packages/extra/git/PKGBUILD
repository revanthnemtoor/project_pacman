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
source=(
    'https://mirrors.edge.kernel.org/pub/software/scm/git/git-2.55.0.tar.xz'
)
sha256sums=(
    '457fdb04dc8728e007d4688695e6912e6f680727920f2a40bf11eacc17505357'
)

package() {
    cp -a "$srcdir/stage/"* "$pkgdir/usr/"
}