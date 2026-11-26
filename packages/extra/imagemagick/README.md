# imagemagick

Native macOS Pacman port of ImageMagick (`7.1.2-36`, Q16 HDRI) built for `/opt/pacman`.

## Source

Cloned from upstream tag `7.1.2-36` (`https://github.com/ImageMagick/ImageMagick.git`) into `./ImageMagick`.

## Building Package

From `/Users/revanth/Projects/imagemagick`:

```sh
CARCH="darwin_x86_64" /opt/pacman/bin/makepkg --config /opt/pacman/etc/makepkg.conf -f -C --nodeps
```

## Installation & Removal

Install from the local `.pkg.tar.zst` (or `.pkg.zst` symlink) archive:

```sh
/opt/pacman/bin/pacman -U /Users/revanth/Projects/imagemagick/imagemagick-7.1.2.36-1-darwin_x86_64.pkg.tar.zst
```

Or install / remove via the `[extra]` Pacman repository:

```sh
/opt/pacman/bin/pacman -S imagemagick
/opt/pacman/bin/pacman -R imagemagick
```

*(Run `/opt/pacman/bin/pacman` without `sudo` to preserve rootless `revanth:admin` ownership under `/opt/pacman`.)*

## Usage

```sh
magick --version
magick input.png -resize 50% output.jpg
magick identify image.png
```
