#!/usr/bin/env bash
# =============================================================================
# Pacman for macOS - Universal Installer & Bootstrapper (ARM64 & x86_64)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/install.sh | bash
#   or locally:
#   ./install.sh
# =============================================================================

set -euo pipefail

PACMAN_PREFIX="${PACMAN_PREFIX:-/opt/pacman}"
PROJECT_REPO_URL="${PROJECT_REPO_URL:-https://github.com/revanthnemtoor/project_pacman.git}"
PACMAN_GIT_URL="${PACMAN_GIT_URL:-https://gitlab.archlinux.org/pacman/pacman.git}"

# Determine script/project directory if running from a local clone
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    SCRIPT_DIR=""
fi

if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/core" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
else
    PROJECT_DIR="${PROJECT_DIR:-$HOME/project_pacman}"
fi

# -----------------------------------------------------------------------------
# 1. Detect OS & Architecture (Apple Silicon arm64 & Intel x86_64)
# -----------------------------------------------------------------------------
OS_NAME="$(uname -s)"
if [ "$OS_NAME" != "Darwin" ]; then
    echo "Error: This installer is only for macOS (detected: $OS_NAME)."
    exit 1
fi

HOST_ARCH="$(uname -m)"
HW_MODEL="$(sysctl -n hw.model 2>/dev/null || echo 'Mac')"
case "$HOST_ARCH" in
    arm64|aarch64)
        HOST_ARCH="arm64"
        DARWIN_ARCH="darwin_arm64"
        OTHER_ARCH="darwin_x86_64"
        ;;
    x86_64)
        HOST_ARCH="x86_64"
        DARWIN_ARCH="darwin_x86_64"
        OTHER_ARCH="darwin_arm64"
        ;;
    *)
        echo "Error: Unsupported architecture '$HOST_ARCH'. Supported: arm64 (Apple Silicon), x86_64 (Intel)."
        exit 1
        ;;
esac

CHOST="$(cc -dumpmachine 2>/dev/null || echo "${HOST_ARCH}-apple-darwin")"

echo "========================================================"
echo "  Installing Pacman for macOS ($DARWIN_ARCH / Rootless)"
echo "========================================================"
echo "  Mac Model     : $HW_MODEL"
echo "  Host Arch     : $HOST_ARCH ($DARWIN_ARCH)"
echo "  Install Prefix: $PACMAN_PREFIX"
echo "  Project Dir   : $PROJECT_DIR"
echo "========================================================"

# -----------------------------------------------------------------------------
# 2. Clone project_pacman if running via curl | bash
# -----------------------------------------------------------------------------
if [ ! -d "$PROJECT_DIR/core" ]; then
    echo "-> Cloning project_pacman repository to $PROJECT_DIR..."
    git clone "$PROJECT_REPO_URL" "$PROJECT_DIR"
fi

# -----------------------------------------------------------------------------
# 3. Set up /opt/pacman owned by current user (rootless operation)
# -----------------------------------------------------------------------------
CURRENT_USER="$(whoami)"
CURRENT_GROUP="$(id -gn)"

if [ ! -d "$PACMAN_PREFIX" ] || [ ! -w "$PACMAN_PREFIX" ]; then
    echo "-> Setting up $PACMAN_PREFIX owned by $CURRENT_USER:$CURRENT_GROUP..."
    if sudo -n true 2>/dev/null; then
        sudo mkdir -p "$PACMAN_PREFIX"
        sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$PACMAN_PREFIX"
    elif command -v osascript >/dev/null 2>&1; then
        osascript -e "do shell script \"mkdir -p '$PACMAN_PREFIX' && chown -R '$CURRENT_USER:$CURRENT_GROUP' '$PACMAN_PREFIX'\" with administrator privileges" || {
            sudo mkdir -p "$PACMAN_PREFIX"
            sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$PACMAN_PREFIX"
        }
    else
        sudo mkdir -p "$PACMAN_PREFIX"
        sudo chown -R "$CURRENT_USER:$CURRENT_GROUP" "$PACMAN_PREFIX"
    fi
fi

mkdir -p \
    "$PACMAN_PREFIX/bin" \
    "$PACMAN_PREFIX/etc/pacman.d/gnupg" \
    "$PACMAN_PREFIX/etc/pacman.d/hooks" \
    "$PACMAN_PREFIX/var/lib/pacman" \
    "$PACMAN_PREFIX/var/cache/pacman/pkg" \
    "$PACMAN_PREFIX/var/log"

# -----------------------------------------------------------------------------
# 4. Clone & Patch Pacman Source inside $PROJECT_DIR/pacman
# -----------------------------------------------------------------------------
PACMAN_SRC_DIR="$PROJECT_DIR/pacman"
if [ ! -d "$PACMAN_SRC_DIR/src" ]; then
    echo "-> Cloning upstream pacman source into $PACMAN_SRC_DIR..."
    git clone --depth 1 "$PACMAN_GIT_URL" "$PACMAN_SRC_DIR"
fi

echo "-> Ensuring macOS rootless & multi-arch patches in $PACMAN_SRC_DIR..."
python3 - "$PACMAN_SRC_DIR" << 'PYEOF'
import sys
from pathlib import Path

src = Path(sys.argv[1])

# 1. src/pacman/util.c: needs_root() -> return 0 on macOS
util_c = src / "src/pacman/util.c"
if util_c.exists():
    txt = util_c.read_text()
    if "#ifdef __APPLE__" not in txt and "int needs_root(void)" in txt:
        txt = txt.replace(
            "int needs_root(void)\n{",
            "int needs_root(void)\n{\n#ifdef __APPLE__\n\treturn 0;\n#endif",
            1,
        )
        util_c.write_text(txt)

# 2. src/pacman/conf.c: auto-detect darwin_<arch> & allow running without gpgme
conf_c = src / "src/pacman/conf.c"
if conf_c.exists():
    txt = conf_c.read_text()
    if "darwin_%s" not in txt and 'strcmp(arch, "auto") == 0' in txt:
        txt = txt.replace(
            "\t\tarch = newarch;\n\t}",
            '\t\tarch = newarch;\n#ifdef __APPLE__\n\t\tchar darwin_arch[64];\n\t\tsnprintf(darwin_arch, sizeof(darwin_arch), "darwin_%s", arch);\n\t\tconfig->architectures = alpm_list_add(config->architectures, strdup(darwin_arch));\n#endif\n\t}',
            1,
        )
    if "level = 0;" not in txt and "ALPM_CAPABILITY_SIGNATURES" in txt:
        old_block = """\tif(!(alpm_capabilities() & ALPM_CAPABILITY_SIGNATURES) &&
\t\t\tlevel & (ALPM_SIG_PACKAGE | ALPM_SIG_DATABASE)) {
\t\tpm_printf(ALPM_LOG_ERROR,
\t\t\t\t_("config file %s, line %d: '%s' option invalid, no signature support\\n"),
\t\t\t\tfile, linenum, "SigLevel");
\t\tret = 1;
\t}"""
        new_block = """\tif(!(alpm_capabilities() & ALPM_CAPABILITY_SIGNATURES)) {
#ifdef __APPLE__
\t\tlevel = 0;
#else
\t\tif(level & (ALPM_SIG_PACKAGE | ALPM_SIG_DATABASE)) {
\t\t\tpm_printf(ALPM_LOG_ERROR,
\t\t\t\t\t_("config file %s, line %d: '%s' option invalid, no signature support\\n"),
\t\t\t\t\tfile, linenum, "SigLevel");
\t\t\tret = 1;
\t\t}
#endif
\t}"""
        txt = txt.replace(old_block, new_block)
    conf_c.write_text(txt)

# 3. lib/libalpm/add.c: only use ARCHIVE_EXTRACT_OWNER when getuid() == 0
add_c = src / "lib/libalpm/add.c"
if add_c.exists():
    txt = add_c.read_text()
    old_flags = """\tconst int archive_flags = ARCHIVE_EXTRACT_OWNER |
\t                          ARCHIVE_EXTRACT_PERM |
\t                          ARCHIVE_EXTRACT_TIME |
\t                          ARCHIVE_EXTRACT_UNLINK |
\t                          ARCHIVE_EXTRACT_XATTR |
\t                          ARCHIVE_EXTRACT_SECURE_SYMLINKS;"""
    new_flags = """\tint archive_flags = ARCHIVE_EXTRACT_PERM |
\t                    ARCHIVE_EXTRACT_TIME |
\t                    ARCHIVE_EXTRACT_UNLINK |
\t                    ARCHIVE_EXTRACT_XATTR |
\t                    ARCHIVE_EXTRACT_SECURE_SYMLINKS;
\tif(getuid() == 0) {
\t\tarchive_flags |= ARCHIVE_EXTRACT_OWNER;
\t}"""
    if old_flags in txt:
        add_c.write_text(txt.replace(old_flags, new_flags))

# 4. scripts/pacman-key.sh.in: disable EUID != 0 requirement
pkey = src / "scripts/pacman-key.sh.in"
if pkey.exists():
    txt = pkey.read_text()
    txt = txt.replace("&& EUID != 0 )); then", "&& false && EUID != 0 )); then")
    pkey.write_text(txt)

# 5. scripts/repo-add.sh.in: bsdtar -tqf -> bsdtar -tf & shasum fallback
repoadd = src / "scripts/repo-add.sh.in"
if repoadd.exists():
    txt = repoadd.read_text()
    txt = txt.replace("bsdtar -tqf", "bsdtar -tf")
    txt = txt.replace('csize=$(wc -c < "$pkgfile")', 'csize=$(wc -c < "$pkgfile" | tr -d \'[:space:]\')')
    txt = txt.replace('sha256sum=$(sha256sum "$pkgfile")', 'sha256sum=$(sha256sum "$pkgfile" 2>/dev/null || shasum -a 256 "$pkgfile")')
    repoadd.write_text(txt)

# 6. scripts/libmakepkg/executable/fakeroot.sh.in: optional fakeroot on Darwin
froot = src / "scripts/libmakepkg/executable/fakeroot.sh.in"
if froot.exists():
    txt = froot.read_text()
    if 'uname -s' not in txt:
        txt = txt.replace(
            "executable_fakeroot() {\n",
            'executable_fakeroot() {\n\tif [[ "$(uname -s)" == "Darwin" ]]; then return 0; fi\n',
        )
        froot.write_text(txt)

# 7. scripts/libmakepkg/util/dirsize.sh.in: strip whitespace from BSD wc -c
dsize = src / "scripts/libmakepkg/util/dirsize.sh.in"
if dsize.exists():
    txt = dsize.read_text()
    if "tr -d" not in txt:
        txt = txt.replace("} | wc -c", "} | wc -c | tr -d '[:space:]'")
        dsize.write_text(txt)

# 8. lib/libalpm/be_sync.c: request <repo>-darwin_<arch>.db.tar.gz from remote servers
besync = src / "lib/libalpm/be_sync.c"
if besync.exists():
    txt = besync.read_text()
    if "sys/utsname.h" not in txt:
        txt = txt.replace("#include <sys/stat.h>\n", "#include <sys/stat.h>\n#include <sys/utsname.h>\n", 1)
    old_sync = """\t\tlen = strlen(db->treename) + strlen(dbext) + 1;
\t\tMALLOC(payload->filepath, len,
\t\t\tFREE(payload); GOTO_ERR(handle, ALPM_ERR_MEMORY, cleanup));
\t\tsnprintf(payload->filepath, len, "%s%s", db->treename, dbext);

\t\tSTRDUP(payload->remote_name, payload->filepath,
\t\t\t_alpm_dload_payload_reset(payload); FREE(payload);
\t\t\tGOTO_ERR(handle, ALPM_ERR_MEMORY, cleanup));"""
    new_sync = """#ifdef __APPLE__
\t\tstruct utsname un;
\t\tuname(&un);
\t\tconst char *mac_arch = (strcmp(un.machine, "arm64") == 0 || strcmp(un.machine, "aarch64") == 0) ? "darwin_arm64" : "darwin_x86_64";
\t\tconst char *ext_arch = (strcmp(dbext, ".files") == 0) ? ".files.tar.gz" : ".db.tar.gz";
\t\tlen = strlen(db->treename) + 1 + strlen(mac_arch) + strlen(ext_arch) + 1;
\t\tMALLOC(payload->filepath, len,
\t\t\tFREE(payload); GOTO_ERR(handle, ALPM_ERR_MEMORY, cleanup));
\t\tsnprintf(payload->filepath, len, "%s-%s%s", db->treename, mac_arch, ext_arch);

\t\tsize_t rlen = strlen(db->treename) + strlen(dbext) + 1;
\t\tMALLOC(payload->remote_name, rlen,
\t\t\t_alpm_dload_payload_reset(payload); FREE(payload);
\t\t\tGOTO_ERR(handle, ALPM_ERR_MEMORY, cleanup));
\t\tsnprintf(payload->remote_name, rlen, "%s%s", db->treename, dbext);
#else
""" + old_sync + "\n#endif"
    if "#ifdef __APPLE__" not in txt and old_sync in txt:
        txt = txt.replace(old_sync, new_sync, 1)
    besync.write_text(txt)
PYEOF

# -----------------------------------------------------------------------------
# 5. Build and Install Pacman via Meson + Ninja
# -----------------------------------------------------------------------------
echo "-> Building and installing pacman to $PACMAN_PREFIX..."

PKG_DIRS=""
for d in \
    /opt/homebrew/opt/libarchive/lib/pkgconfig \
    /opt/homebrew/opt/curl/lib/pkgconfig \
    /opt/homebrew/opt/openssl@3/lib/pkgconfig \
    /opt/homebrew/opt/openssl@4/lib/pkgconfig \
    /opt/homebrew/lib/pkgconfig \
    /usr/local/opt/libarchive/lib/pkgconfig \
    /usr/local/opt/curl/lib/pkgconfig \
    /usr/local/opt/openssl@3/lib/pkgconfig \
    /usr/local/opt/openssl@4/lib/pkgconfig \
    /usr/local/lib/pkgconfig \
    /opt/local/lib/pkgconfig; do
    if [ -d "$d" ]; then
        PKG_DIRS="${PKG_DIRS:+$PKG_DIRS:}$d"
    fi
done
export PKG_CONFIG_PATH="${PKG_DIRS}${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

CFLAGS_EXTRA=""
LDFLAGS_EXTRA="-liconv -lintl"
for p in /opt/homebrew /usr/local /opt/local /opt/homebrew/opt/gettext /usr/local/opt/gettext /opt/homebrew/opt/libarchive /usr/local/opt/libarchive; do
    [ -d "$p/include" ] && CFLAGS_EXTRA="$CFLAGS_EXTRA -I$p/include"
    [ -d "$p/lib" ] && LDFLAGS_EXTRA="$LDFLAGS_EXTRA -L$p/lib"
done
export CFLAGS="${CFLAGS:-} $CFLAGS_EXTRA"
export LDFLAGS="${LDFLAGS:-} $LDFLAGS_EXTRA"

cd "$PACMAN_SRC_DIR"
if [ ! -f build/build.ninja ]; then
    meson setup build \
        --prefix="$PACMAN_PREFIX" \
        --sysconfdir="$PACMAN_PREFIX/etc" \
        --localstatedir="$PACMAN_PREFIX/var" \
        -Dpkg-ext=.pkg.tar.zst \
        -Dcrypto=openssl \
        -Ddoc=disabled \
        -Dgpgme=disabled
fi
ninja -C build install

# -----------------------------------------------------------------------------
# 6. Activate Pre-Built Architecture Repo Databases (No repo-add Needed)
# -----------------------------------------------------------------------------
echo "-> Activating pre-built $DARWIN_ARCH databases in core/ and output/..."
# Remove incompatible packages from pacman cache and sync state
rm -f "$PACMAN_PREFIX/var/cache/pacman/pkg/"*-"${OTHER_ARCH}".pkg.tar.zst* 2>/dev/null || true
rm -f "$PACMAN_PREFIX/var/lib/pacman/sync/"*.db* 2>/dev/null || true

# If running via curl | bash (or if CLEAN_OTHER_ARCH=1), remove other-arch packages from disk
if [ -z "$SCRIPT_DIR" ] || [ "${CLEAN_OTHER_ARCH:-0}" = "1" ]; then
    echo "   Removing $OTHER_ARCH packages from local clone..."
    rm -f "$PROJECT_DIR/core/"*-"${OTHER_ARCH}".pkg.tar.zst* 2>/dev/null || true
    rm -f "$PROJECT_DIR/output/"*-"${OTHER_ARCH}".pkg.tar.zst* 2>/dev/null || true
fi

activate_prebuilt_db() {
    local repo_dir="$1"
    local repo_name="$2"
    mkdir -p "$repo_dir"

    if [ -f "$repo_dir/${repo_name}-${DARWIN_ARCH}.db.tar.gz" ]; then
        rm -f "$repo_dir/${repo_name}.db" "$repo_dir/${repo_name}.db.tar.gz"
        cp "$repo_dir/${repo_name}-${DARWIN_ARCH}.db.tar.gz" "$repo_dir/${repo_name}.db.tar.gz"
        cp "$repo_dir/${repo_name}-${DARWIN_ARCH}.db.tar.gz" "$repo_dir/${repo_name}.db"
    fi
    if [ -f "$repo_dir/${repo_name}-${DARWIN_ARCH}.files.tar.gz" ]; then
        rm -f "$repo_dir/${repo_name}.files" "$repo_dir/${repo_name}.files.tar.gz"
        cp "$repo_dir/${repo_name}-${DARWIN_ARCH}.files.tar.gz" "$repo_dir/${repo_name}.files.tar.gz"
        cp "$repo_dir/${repo_name}-${DARWIN_ARCH}.files.tar.gz" "$repo_dir/${repo_name}.files"
    fi
}

activate_prebuilt_db "$PROJECT_DIR/core" "core"
activate_prebuilt_db "$PROJECT_DIR/output" "pacman"

# -----------------------------------------------------------------------------
# 7. Configure pacman.conf & makepkg.conf Exclusively for Current Architecture
# -----------------------------------------------------------------------------
echo "-> Writing $PACMAN_PREFIX/etc/pacman.conf (Architecture = $DARWIN_ARCH $HOST_ARCH any)..."
cat << EOF > "$PACMAN_PREFIX/etc/pacman.conf"
#
# $PACMAN_PREFIX/etc/pacman.conf
# Native macOS Pacman Configuration ($DARWIN_ARCH Only - Prevents Cross-Arch Crashes)
#

[options]
RootDir     = /
DBPath      = $PACMAN_PREFIX/var/lib/pacman/
CacheDir    = $PACMAN_PREFIX/var/cache/pacman/pkg/
LogFile     = $PACMAN_PREFIX/var/log/pacman.log
GPGDir      = $PACMAN_PREFIX/etc/pacman.d/gnupg/
HookDir     = $PACMAN_PREFIX/etc/pacman.d/hooks/
HoldPkg     = pacman
Architecture = $DARWIN_ARCH $HOST_ARCH any

Color
CheckSpace
ParallelDownloads = 5

SigLevel    = Optional TrustAll
LocalFileSigLevel = Optional
RemoteFileSigLevel = Optional
NoExtract   = opt/pacman/share/info/dir

[pacman]
SigLevel = Optional TrustAll
Server = https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/output
Server = https://revanthnemtoor.github.io/project_pacman/output

[core]
SigLevel = Optional TrustAll
Server = https://raw.githubusercontent.com/revanthnemtoor/project_pacman/main/core
Server = https://revanthnemtoor.github.io/project_pacman/core
EOF

cp "$PACMAN_PREFIX/etc/pacman.conf" "$PROJECT_DIR/configs/pacman.conf" 2>/dev/null || true

# Ensure makepkg.conf has CARCH set to current darwin architecture and !strip
if [ -f "$PACMAN_PREFIX/etc/makepkg.conf" ]; then
    sed -i '' "s/^CARCH=.*/CARCH=\"$DARWIN_ARCH\"/" "$PACMAN_PREFIX/etc/makepkg.conf" || true
    sed -i '' "s/^CHOST=.*/CHOST=\"$CHOST\"/" "$PACMAN_PREFIX/etc/makepkg.conf" || true
    sed -i '' "s/^OPTIONS=(strip /OPTIONS=(!strip /" "$PACMAN_PREFIX/etc/makepkg.conf" || true
fi

# -----------------------------------------------------------------------------
# 8. Prepend /opt/pacman/bin to Top of PATH (Fish, Zsh, Bash)
# -----------------------------------------------------------------------------
echo "-> Putting $PACMAN_PREFIX/bin at highest priority in PATH (fish, zsh, bash)..."

# Fish shell (prepend & move to front of PATH)
FISH_CONFIG="$HOME/.config/fish/config.fish"
mkdir -p "$(dirname "$FISH_CONFIG")"
if [ -f "$FISH_CONFIG" ]; then
    grep -v "$PACMAN_PREFIX/bin" "$FISH_CONFIG" | grep -v "# Pacman for macOS" > "${FISH_CONFIG}.tmp" || true
    {
        echo "# Pacman for macOS (Highest Priority in PATH)"
        echo "fish_add_path -g -p -m -P $PACMAN_PREFIX/bin $PACMAN_PREFIX/sbin"
        echo "set -gx GIT_EXEC_PATH $PACMAN_PREFIX/libexec/git-core"
        echo "set -gx GIT_TEMPLATE_DIR $PACMAN_PREFIX/share/git-core/templates"
        echo ""
        cat "${FISH_CONFIG}.tmp"
    } > "$FISH_CONFIG"
    rm -f "${FISH_CONFIG}.tmp"
else
    {
        echo "# Pacman for macOS (Highest Priority in PATH)"
        echo "fish_add_path -g -p -m -P $PACMAN_PREFIX/bin $PACMAN_PREFIX/sbin"
        echo "set -gx GIT_EXEC_PATH $PACMAN_PREFIX/libexec/git-core"
        echo "set -gx GIT_TEMPLATE_DIR $PACMAN_PREFIX/share/git-core/templates"
    } > "$FISH_CONFIG"
fi
echo "   Prepended $PACMAN_PREFIX/bin to $FISH_CONFIG"

# Zsh & Bash
for RC_FILE in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    if [ -f "$RC_FILE" ] || [ "$RC_FILE" = "$HOME/.zshrc" ] || [ "$RC_FILE" = "$HOME/.bash_profile" ]; then
        touch "$RC_FILE"
        if ! grep -q "$PACMAN_PREFIX/bin" "$RC_FILE"; then
            {
                echo ""
                echo "# Pacman for macOS (Highest Priority in PATH)"
                echo "export PATH=\"$PACMAN_PREFIX/bin:$PACMAN_PREFIX/sbin:\$PATH\""
                echo "export GIT_EXEC_PATH=\"$PACMAN_PREFIX/libexec/git-core\""
                echo "export GIT_TEMPLATE_DIR=\"$PACMAN_PREFIX/share/git-core/templates\""
            } >> "$RC_FILE"
            echo "   Prepended $PACMAN_PREFIX/bin to $RC_FILE"
        fi
    fi
done

# -----------------------------------------------------------------------------
# 8. Sync Package Databases
# -----------------------------------------------------------------------------
echo "-> Synchronizing package databases..."
"$PACMAN_PREFIX/bin/pacman" -Sy

echo ""
echo "========================================================"
echo "  Pacman v7.1.0 Installed Successfully!"
echo "  Binary      : $PACMAN_PREFIX/bin/pacman"
echo "  Config      : $PACMAN_PREFIX/etc/pacman.conf"
echo "  Architecture: $DARWIN_ARCH (Apple Silicon & Intel enabled)"
echo "========================================================"
