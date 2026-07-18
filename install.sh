#!/usr/bin/env bash
# macOS Pacman Installer
# curl -fsSL https://.../install.sh | bash

set -e

PACMAN_PREFIX="/opt/pacman"
REPO_URL="file:///Users/revanthnemtoo/project_pacman/core"
BOOTSTRAP_URL="file:///Users/revanthnemtoo/project_pacman/pacman-bootstrap.tar.gz"

echo "========================================="
echo "  Installing Pacman for macOS (ARM64)  "
echo "========================================="

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Error: This installer is only for macOS."
    exit 1
fi

if [ "$(uname -m)" != "arm64" ]; then
    echo "Error: This installer currently requires Apple Silicon (arm64)."
    exit 1
fi

echo "-> Requesting sudo privileges for installation..."
sudo -v

echo "-> Setting up $PACMAN_PREFIX directory..."
sudo mkdir -p "$PACMAN_PREFIX"
sudo chown -R $(whoami) "$PACMAN_PREFIX"

echo "-> Downloading bootstrap environment..."
# In production, this would be a real URL
curl -fsSL "$BOOTSTRAP_URL" -o /tmp/pacman-bootstrap.tar.gz || {
    echo "For local testing, assuming /opt/pacman is already populated or bootstrap tarball is available."
}

if [ -f /tmp/pacman-bootstrap.tar.gz ]; then
    echo "-> Extracting bootstrap to $PACMAN_PREFIX..."
    tar -xzf /tmp/pacman-bootstrap.tar.gz -C /
    rm /tmp/pacman-bootstrap.tar.gz
fi

echo "-> Configuring pacman.conf..."
cat << EOF > "$PACMAN_PREFIX/etc/pacman.conf"
[options]
HoldPkg     = pacman glibc
Architecture = auto
CheckSpace
SigLevel    = Required DatabaseOptional
LocalFileSigLevel = Optional
NoExtract   = opt/pacman/share/info/dir

[core]
Server = $REPO_URL
EOF

echo "-> Initializing Pacman keyring..."
sudo "$PACMAN_PREFIX/bin/pacman-key" --init
sudo "$PACMAN_PREFIX/bin/pacman-key" --populate archlinux || true

echo "-> Synchronizing package databases..."
sudo "$PACMAN_PREFIX/bin/pacman" -Sy

echo "========================================="
echo "  Installation Complete!"
echo "  Please add $PACMAN_PREFIX/bin to your PATH:"
echo "  echo 'export PATH=\"$PACMAN_PREFIX/bin:\$PATH\"' >> ~/.zshrc"
echo "========================================="
