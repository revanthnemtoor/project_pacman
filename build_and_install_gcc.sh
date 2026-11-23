#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/revanth/Projects/Pacman_Arch_Porting"
GCC_PKG_DIR="$PROJECT_DIR/packages/extra/gcc"
export PATH="/opt/pacman/bin:/usr/bin:/bin:/usr/sbin:/sbin"

echo "=================================================="
echo "Starting GCC 14.2.0 Build on Darwin x86_64 (Intel)"
echo "Started at: $(date)"
echo "CPUs: $(sysctl -n hw.ncpu)"
echo "=================================================="

cd "$GCC_PKG_DIR"

# 1. Clean previous package artifacts if any (preserve src/ to avoid rebuilding)
rm -rf pkg *.pkg.tar.*

# 2. Run makepkg
echo "--> Running makepkg..."
if [[ -d src/build ]]; then
    echo "Existing build tree detected, running makepkg -ef --noconfirm..."
    /opt/pacman/bin/makepkg -ef --noconfirm
else
    /opt/pacman/bin/makepkg -f --noconfirm
fi

PKG_FILE=$(ls gcc-14.2.0-1-darwin_x86_64.pkg.tar.zst)
SIG_FILE="${PKG_FILE}.sig"

if [[ ! -f "$PKG_FILE" ]]; then
    echo "ERROR: Package file $PKG_FILE not found!"
    exit 1
fi

# Ensure signature exists (makepkg signs if sign is in BUILDENV)
if [[ ! -f "$SIG_FILE" ]]; then
    echo "--> Signing package with GPG..."
    /opt/pacman/bin/gpg --detach-sign --batch --yes -u CEC5B78775CA4628 "$PKG_FILE"
fi

echo "--> Copying package and signature to extra repository..."
cp -f "$PKG_FILE" "$PROJECT_DIR/extra/"
cp -f "$SIG_FILE" "$PROJECT_DIR/extra/"

echo "--> Installing GCC into /opt/pacman..."
/opt/pacman/bin/pacman -U "$PKG_FILE" --noconfirm

echo "--> Updating repository sync databases..."
cd "$PROJECT_DIR"
python3 update_repo_db.py

echo "--> Verifying installed GCC..."
/opt/pacman/bin/pacman -Qi gcc
/opt/pacman/bin/gcc --version
/opt/pacman/bin/g++ --version

# Test compiling a small C and C++ program with native GCC
echo "--> Testing native GCC compilation..."
echo 'int main(){return 0;}' | /opt/pacman/bin/gcc -x c - -o /tmp/gcc_test_c
/tmp/gcc_test_c && rm -f /tmp/gcc_test_c
echo "C compilation: SUCCESS"

echo '#include <iostream>
int main(){ std::cout << "Hello from GNU GCC on Darwin x86_64!" << std::endl; return 0;}' | /opt/pacman/bin/g++ -x c++ - -o /tmp/gcc_test_cpp
/tmp/gcc_test_cpp && rm -f /tmp/gcc_test_cpp
echo "C++ compilation: SUCCESS"

echo "--> Staging, committing, and pushing to git..."
git add packages/extra/gcc/PKGBUILD \
        extra/gcc-14.2.0-1-darwin_x86_64.pkg.tar.zst \
        extra/gcc-14.2.0-1-darwin_x86_64.pkg.tar.zst.sig \
        extra/extra* \
        configs/ \
        .gitignore

git commit -m "feat(gcc): build and package native GNU GCC 14.2.0 for Intel Darwin

- Mainline GNU GCC 14.2.0 native x86_64-apple-darwin port
- Uses Apple Mach-O ld64 linker via xcrun MacOSX.sdk sysroot
- Includes in-tree math prerequisites (gmp, mpfr, mpc, isl)
- Fixincludes trap pruned to prevent Apple SDK header conflicts
- Provides cc, c++, gcc, and g++ in /opt/pacman/bin
- PGP signed with repo packager key"

git push origin main

# Sync working copy
cd /Users/revanth/project_pacman
git pull origin main

echo "=================================================="
echo "GCC 14.2.0 Build, Installation & Push COMPLETED!"
echo "Finished at: $(date)"
echo "=================================================="
