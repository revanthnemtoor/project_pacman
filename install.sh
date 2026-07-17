#!/bin/bash
# Pacman for macOS - Bootstrap Installer
# Run this script to install and configure Pacman on a new macOS system!

set -e

PACMAN_ROOT="/opt/pacman"
PACMAN_DB_URL="https://revanthnemtoor.github.io/project_pacman/output"

echo "============================================================"
echo "  Pacman for macOS (ARM64) Installer"
echo "============================================================"
echo ""

if [ "$EUID" -ne 0 ]; then
  echo "Please run this script with sudo:"
  echo "sudo bash install.sh"
  exit 1
fi

echo "==> Configuring Pacman..."
if [ ! -f "${PACMAN_ROOT}/etc/pacman.conf" ]; then
    echo "Error: /opt/pacman not found. Please install the base bootstrap tarball first."
    exit 1
fi

# Enable Color and ILoveCandy easter egg
sed -i '' 's/#Color/Color\nILoveCandy/' "${PACMAN_ROOT}/etc/pacman.conf"

# Set ParallelDownloads to 10
sed -i '' 's/#ParallelDownloads = 5/ParallelDownloads = 10/' "${PACMAN_ROOT}/etc/pacman.conf"
sed -i '' 's/ParallelDownloads = 5/ParallelDownloads = 10/' "${PACMAN_ROOT}/etc/pacman.conf"

# Disable SigLevel for LocalFiles and TrustAll
sed -i '' 's/SigLevel = Required DatabaseOptional/SigLevel = Optional TrustAll/' "${PACMAN_ROOT}/etc/pacman.conf"

# Set Server URL to GitHub Pages
sed -i '' "s|Server = file:///.*|Server = ${PACMAN_DB_URL}|" "${PACMAN_ROOT}/etc/pacman.conf"

echo "==> Setting up system PATH..."
echo "${PACMAN_ROOT}/bin" > /etc/paths.d/pacman

echo "==> Synchronizing package databases..."
${PACMAN_ROOT}/bin/pacman -Sy

echo ""
echo "============================================================"
echo "  Installation Complete!"
echo "============================================================"
echo "You can now install packages using:"
echo "  sudo pacman -S <package_name>"
echo ""
echo "Please restart your terminal to update your PATH!"
