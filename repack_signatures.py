import os
import shutil
import subprocess
from pathlib import Path

CORE_DIR = Path("/Users/revanthnemtoo/project_pacman/core")
TMP_DIR = Path("/Users/revanthnemtoo/project_pacman/tmp_core")
KEY_ID = "276C37EC8DB2DCF235B3EAC02C3E87EC7EC39843"

def main():
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir()

    print("Moving packages to temporary directory...")
    # Only move .pkg.tar.zst files, ignore old .db, .files, .sig
    for pkg in CORE_DIR.glob("*.pkg.tar.zst"):
        shutil.copy(str(pkg), str(TMP_DIR / pkg.name))

    print("Wiping old core directory...")
    shutil.rmtree(CORE_DIR)
    CORE_DIR.mkdir()

    print("Signing packages...")
    for pkg in TMP_DIR.glob("*.pkg.tar.zst"):
        print(f"Signing {pkg.name}...")
        subprocess.run(["gpg", "--batch", "--yes", "--detach-sign", "--use-agent", "--no-armor", "--default-key", KEY_ID, str(pkg)], check=True)
        
        # Move package and signature to core
        shutil.move(str(pkg), str(CORE_DIR / pkg.name))
        sig = pkg.with_name(pkg.name + ".sig")
        if sig.exists():
            shutil.move(str(sig), str(CORE_DIR / sig.name))

    print("Generating signed database...")
    db_file = CORE_DIR / "core.db.tar.gz"
    packages = list(CORE_DIR.glob("*.pkg.tar.zst"))
    
    cmd = ["/opt/pacman/bin/repo-add", "--sign", "--key", KEY_ID, str(db_file)] + [str(p) for p in packages]
    env = os.environ.copy()
    env["PATH"] = "/opt/pacman/bin:" + env.get("PATH", "")
    subprocess.run(cmd, check=True, env=env)
    
    print("Cleanup...")
    shutil.rmtree(TMP_DIR)
    print("Done!")

if __name__ == "__main__":
    main()
