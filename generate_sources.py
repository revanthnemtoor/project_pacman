import json
import subprocess
import os
from pathlib import Path

# Packages to completely ignore (Linux specific or not applicable to macOS pacman core)
BLOCKLIST = {
    'acl', 'amd-ucode', 'archlinux-keyring', 'attr', 'audispd-plugins',
    'audispd-plugins-zos', 'audit', 'b43-fwcutter', 'base', 'base-devel',
    'btrfs-progs', 'cracklib', 'cryptsetup', 'dash', 'dbus', 'dbus-broker',
    'dbus-broker-units', 'dbus-daemon-units', 'dbus-docs', 'dbus-units',
    'debugedit', 'debuginfod', 'device-mapper', 'dmraid', 'dnssec-anchors',
    'dosfstools', 'e2fsprogs', 'efibootmgr', 'efivar', 'elfutils', 'fakeroot',
    'filesystem', 'fuse2fs', 'gcc-ada', 'gcc-d', 'gcc-fortran', 'gcc-gcobol',
    'gcc-go', 'gcc-libs', 'gcc-m2', 'gcc-objc', 'gcc-rust', 'glibc',
    'glibc-locales', 'gnulib-l10n', 'gpm', 'grub', 'gssproxy', 'hdparm',
    'hwdata', 'iana-etc', 'iproute2', 'iptables', 'iptables-legacy', 'iputils',
    'iw', 'jfsutils', 'kbd', 'keyutils', 'kmod', 'ldns', 'leancrypto', 'lemon',
    'lib32-gcc-libs', 'lib32-glibc', 'lib32-libltdl', 'libaio', 'libasan',
    'libbpf', 'libcap', 'libcap-ng', 'libelf', 'libgcc', 'libgccjit',
    'libgcobol', 'libgfortran', 'libgm2', 'libgo', 'libgomp', 'libgphobos',
    'libhwasan', 'libitm', 'liblsan', 'libmakepkg-dropins', 'libmnl',
    'libnetfilter_conntrack', 'libnfnetlink', 'libnftnl', 'libnl', 'libnsl',
    'libobjc', 'libquadmath', 'libseccomp', 'libtsan', 'libubsan', 'linux',
    'linux-api-headers', 'linux-docs', 'linux-firmware', 'linux-firmware-amdgpu',
    'linux-firmware-atheros', 'linux-firmware-broadcom', 'linux-firmware-cirrus',
    'linux-firmware-intel', 'linux-firmware-liquidio', 'linux-firmware-marvell',
    'linux-firmware-mediatek', 'linux-firmware-mellanox', 'linux-firmware-nfp',
    'linux-firmware-nvidia', 'linux-firmware-other', 'linux-firmware-qcom',
    'linux-firmware-qlogic', 'linux-firmware-radeon', 'linux-firmware-realtek',
    'linux-firmware-whence', 'linux-headers', 'linux-lts', 'linux-lts-docs',
    'linux-lts-headers', 'logrotate', 'lto-dump', 'lvm2', 'man-db', 'man-pages',
    'man-pages-utils', 'mdadm', 'mkinitcpio', 'mkinitcpio-busybox',
    'mkinitcpio-nfs-utils', 'net-tools', 'nfs-utils', 'nfsidmap', 'nilfs-utils',
    'openldap', 'pacman', 'pacman-mirrorlist', 'pam', 'pambase', 'pciutils',
    'ppp', 'pptpclient', 'procps-ng', 'psmisc', 'python-audit', 'python-capng',
    'python-libseccomp', 'rpcbind', 'shadow', 'syslinux', 'systemd',
    'systemd-libs', 'systemd-resolvconf', 'systemd-sysvcompat', 'systemd-tests',
    'systemd-ukify', 'thin-provisioning-tools', 'tzdata', 'usbutils',
    'util-linux', 'util-linux-libs', 'voa-verifiers-arch', 'wireless-regdb',
    'wpa_supplicant', 'xfsprogs'
}

def get_brew_info(pkg_name):
    try:
        result = subprocess.run(["brew", "info", "--json=v2", pkg_name], capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "formulae" in data and len(data["formulae"]) > 0:
                return data["formulae"][0]
    except Exception:
        pass
    return None

def main():
    arch_pkgs_file = Path("/Users/revanthnemtoo/project_pacman/arch_core_packages.txt")
    sources_file = Path("/Users/revanthnemtoo/project_pacman/fromsource/sources.json")
    
    with open(arch_pkgs_file, "r") as f:
        arch_pkgs = [line.strip() for line in f if line.strip()]
        
    with open(sources_file, "r") as f:
        sources_data = json.load(f)
        
    existing_pkgs = set(sources_data.keys())
    
    added_count = 0
    print("Querying Homebrew for source tarballs...")
    for pkg in arch_pkgs:
        if pkg in BLOCKLIST or pkg in existing_pkgs:
            continue
            
        info = get_brew_info(pkg)
        if not info:
            continue
            
        urls = info.get("urls", {})
        stable_url = None
        if "stable" in urls and "url" in urls["stable"]:
            stable_url = urls["stable"]["url"]
            
        if not stable_url:
            continue
            
        version = info["versions"]["stable"]
        desc = info.get("desc", f"{pkg} tools")
        
        # Filter dependencies to only include those that are also in our core list
        # to avoid pulling in hundreds of X11/GUI libraries
        brew_deps = info.get("dependencies", [])
        
        # Heuristically detect build system
        system = "autotools"
        if "cmake" in info.get("build_dependencies", []):
            system = "cmake"
        elif "meson" in info.get("build_dependencies", []):
            system = "meson"
        elif "rust" in info.get("build_dependencies", []):
            system = "cargo"
        elif "go" in info.get("build_dependencies", []):
            system = "go"
            
        sources_data[pkg] = {
            "url": stable_url,
            "system": system,
            "version": version,
            "desc": desc,
            "depends": brew_deps
        }
        added_count += 1
        print(f"Added {pkg} {version} ({system})")
        
        # Save every 10 packages in case it crashes
        if added_count % 10 == 0:
            with open(sources_file, "w") as f:
                json.dump(sources_data, f, indent=4)
                
    # Final save
    with open(sources_file, "w") as f:
        json.dump(sources_data, f, indent=4)
        
    print(f"\nSuccessfully added {added_count} new packages to sources.json!")
    print(f"Total packages in sources.json: {len(sources_data)}")

if __name__ == "__main__":
    main()
