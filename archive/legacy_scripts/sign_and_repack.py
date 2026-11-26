import os
import subprocess
import tempfile
import glob
import sys
import shutil

def is_macho(path):
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca")
    except Exception:
        return False

def process(pkg_dir):
    files = glob.glob(f"{pkg_dir}/*.pkg.tar.zst")
    if not files:
        print(f"No package found in {pkg_dir}")
        return
    # Use newest
    pkg_file = max(files, key=os.path.getmtime)
    print(f"Processing {pkg_file}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["tar", "-xf", pkg_file, "-C", tmpdir], check=True)

        signed = 0
        for root, _, files in os.walk(tmpdir):
            for file in files:
                path = os.path.join(root, file)
                if not os.path.islink(path) and is_macho(path):
                    res = subprocess.run(["codesign", "--sign", "-", "--force", path], capture_output=True)
                    if res.returncode == 0:
                        signed += 1

        print(f"  Signed {signed} binaries")
        
        pack_cmd = (
            f"cd {tmpdir} && "
            f"tar -cf - .PKGINFO .BUILDINFO .MTREE * 2>/dev/null | "
            f"/opt/pacman/bin/zstd -c -T0 -19 -z > {os.path.abspath(pkg_file)}"
        )
        subprocess.run(pack_cmd, shell=True, check=True)
        print(f"  Repacked {pkg_file}")
        
        # Move to output
        shutil.copy(pkg_file, "output/")
        output_file = os.path.join("output", os.path.basename(pkg_file))
        subprocess.run(["/opt/pacman/bin/repo-add", "--sign", "output/pacman.db.tar.gz", output_file], check=True)

for p in ["fromsource/git", "fromsource/nano", "fromsource/ncurses"]:
    process(p)

os.chdir("output")
subprocess.run(["rm", "-f", "pacman.db", "pacman.db.sig", "pacman.files", "pacman.files.sig"])
subprocess.run(["cp", "pacman.db.tar.gz", "pacman.db"])
subprocess.run(["cp", "pacman.db.tar.gz.sig", "pacman.db.sig"])
subprocess.run(["cp", "pacman.files.tar.gz", "pacman.files"])
subprocess.run(["cp", "pacman.files.tar.gz.sig", "pacman.files.sig"])
