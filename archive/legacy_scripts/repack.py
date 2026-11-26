import os
import subprocess
import tempfile
import glob

def repack(pkg_name):
    # Find the package file
    files = glob.glob(f"output/{pkg_name}-*.pkg.tar.zst")
    if not files:
        print(f"No package found for {pkg_name}")
        return
    pkg_file = files[0]
    print(f"Processing {pkg_file}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract
        subprocess.run(["tar", "-xf", pkg_file, "-C", tmpdir], check=True)

        opt_pacman = os.path.join(tmpdir, "opt", "pacman")
        if os.path.exists(opt_pacman):
            print(f"  Found opt/pacman prefix in {pkg_file}, stripping it...")
            # Move everything from opt/pacman/* to tmpdir/
            for item in os.listdir(opt_pacman):
                src = os.path.join(opt_pacman, item)
                dst = os.path.join(tmpdir, item)
                if os.path.exists(dst):
                    subprocess.run(["rm", "-rf", dst])
                subprocess.run(["mv", src, tmpdir])
            
            # Remove opt/
            subprocess.run(["rm", "-rf", os.path.join(tmpdir, "opt")])

            # Delete old package and signature
            os.remove(pkg_file)
            sig_file = pkg_file + ".sig"
            if os.path.exists(sig_file):
                os.remove(sig_file)

            # Repack and zstd
            pack_cmd = (
                f"cd {tmpdir} && "
                f"tar -cf - .PKGINFO .BUILDINFO .MTREE * 2>/dev/null | "
                f"/opt/pacman/bin/zstd -c -T0 -19 -z > {os.path.abspath(pkg_file)}"
            )
            subprocess.run(pack_cmd, shell=True, check=True)
            print(f"  Repacked {pkg_file}")
            
            # repo-add
            subprocess.run(["/opt/pacman/bin/repo-add", "--sign", "output/pacman.db.tar.gz", pkg_file], check=True)
        else:
            print(f"  No opt/pacman prefix found in {pkg_file}")

for pkg in ["git", "nano", "ncurses"]:
    repack(pkg)

# Fix symlinks again for GitHub pages
os.chdir("output")
subprocess.run(["rm", "-f", "pacman.db", "pacman.db.sig", "pacman.files", "pacman.files.sig"])
subprocess.run(["cp", "pacman.db.tar.gz", "pacman.db"])
subprocess.run(["cp", "pacman.db.tar.gz.sig", "pacman.db.sig"])
subprocess.run(["cp", "pacman.files.tar.gz", "pacman.files"])
subprocess.run(["cp", "pacman.files.tar.gz.sig", "pacman.files.sig"])
