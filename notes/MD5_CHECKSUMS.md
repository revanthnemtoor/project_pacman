# Project Pacman Port: MD5 Checksums & Source Inventory

This registry records the exact MD5 hashes and file sizes of all build scripts, modules,
and pipeline orchestrators across the project before consolidation into the unified builder.

## Root Workspace Python Scripts

| File | MD5 Checksum | Size (bytes) | Role / Purpose |
| :--- | :--- | :--- | :--- |
| `build_all.py` | `3cbb92b9039e165b4af2b3105a1bcf37` | 5,282 | Pipeline Component |
| `build_all_latest.py` | `f546fd8dfe96f28f5b453582ac9226c7` | 22,454 | GNU upstream source build recipe collection (30 packages) |
| `build_all_sources.py` | `319b7ef171313e997c3e21f04e8ef383` | 6,373 | Pipeline Component |
| `build_fromsource.py` | `7d4e9f9d7b764d2f54050e18a79164d0` | 3,480 | Pipeline Component |
| `build_libarchive_and_pacman.py` | `093a70eef8c8e376aab81ccd61071c9f` | 7,808 | Specific build script for libarchive & pacman |
| `build_native_core.py` | `94288efb34a74e1f33203b635743704a` | 16,085 | Native compiler recipe runner for Core Phase 1 |
| `build_native_tier2.py` | `41ae6f4f9dea553fd0cb0bc632e84ee8` | 16,650 | Native compiler recipe runner for Core Phase 2 |
| `build_native_tier3.py` | `0d1d36acfe24d45f42cc6ee2bfa01eb0` | 15,630 | Native compiler recipe runner for Core Phase 3 |
| `build_readline_and_bash.py` | `3bde4382f93ee177a47d57a570366826` | 5,876 | Pipeline Component |
| `download_tarballs.py` | `b29d8bfa57783e768112aea76bd8ff02` | 5,040 | Pipeline Component |
| `env_loader.py` | `b66b19ce6cef9c9e4ffd5d6d2c97cb5f` | 2,559 | Secure environment / packager loader (.env) |
| `generate_sources.py` | `7aabb4242cf9fee755284aeb75001a99` | 5,642 | Pipeline Component |
| `package_arch_standard.py` | `0e0d005760467561262d41e45dfbd2a5` | 20,733 | Arch-standard packaging for curl, gpgme, pacman, base-devel |
| `patch_pkgbuilds.py` | `c2d44791d7425318bb6b66b37e3c89b2` | 1,611 | Pipeline Component |
| `repack.py` | `5bf01713cf4165f81b553364a4756957` | 2,356 | Pipeline Component |
| `repack_packages.py` | `1055293405bee007af6c81a0af71c7b8` | 2,813 | Pipeline Component |
| `repack_signatures.py` | `0fa535312339240accc547f0fef7b4d7` | 1,642 | Pipeline Component |
| `sign_and_repack.py` | `573396a71938518bba3ce09a5943e3a6` | 2,232 | Pipeline Component |
| `update_repo_db.py` | `7a28dbc3bde51c2745a3f5e2f7a43532` | 2,515 | repo-add / repo-remove pacman database indexer and signer |

## builder/src Pipeline Modules

| File | MD5 Checksum | Size (bytes) | Role / Purpose |
| :--- | :--- | :--- | :--- |
| `builder/src/__init__.py` | `d41d8cd98f00b204e9800998ecf8427e` | 0 | Pipeline Component |
| `builder/src/database.py` | `56ffae1d01535f24225374f3abf9f195` | 815 | Pipeline Component |
| `builder/src/install.py` | `944fef9f91709178456f73b434f2f326` | 1,005 | Pipeline Component |
| `builder/src/logger.py` | `466cd3e86c6f85124b59edbbf411414f` | 183 | Pipeline Component |
| `builder/src/main.py` | `b0a02a3c77dedbabc7263577f7b5b6c2` | 7,206 | Pipeline Component |
| `builder/src/makepkg.py` | `addd4d27fa9c4a01754db97ea392aba8` | 3,049 | Darwin makepkg executor with environment wrapping |
| `builder/src/plan.Md` | `0ec263d2d29a50e2523bdfab0b46221d` | 5,747 | Pipeline Component |
| `builder/src/query.py` | `137913096048b02482dc4e8d3d6f3d8f` | 818 | Pipeline Component |
| `builder/src/remove.py` | `e472c17df9611536882f1dcc0544b1a4` | 595 | Pipeline Component |
| `builder/src/repo_manager.py` | `13a53785f5b4310ddf96a2588c6c8212` | 4,225 | Repository database updater wrapping repo-add |
| `builder/src/resolver.py` | `c3fad5f245fc627771eb253a210b5de2` | 1,301 | Pipeline Component |
| `builder/src/verify.py` | `5b3979b15e49774ac5edf37ed2194d98` | 299 | Pipeline Component |

## fromsource Pipeline Modules

| File | MD5 Checksum | Size (bytes) | Role / Purpose |
| :--- | :--- | :--- | :--- |
| `fromsource/__init__.py` | `d6a3c5b178eff4410812b534a49b8753` | 367 | Pipeline Component |
| `fromsource/builder.py` | `329d00f728490dbd00722d82fb6b8450` | 12,221 | Pipeline Component |
| `fromsource/detector.py` | `0583e96d0704635aed96964ebb839932` | 4,609 | Source tree build system detector (Autotools/CMake/Meson) |
| `fromsource/generator.py` | `7cdd707d63a0884754fb66e88bc3aab0` | 9,039 | Automatic PKGBUILD generator from detected sources |
| `fromsource/sources.json` | `a3969cfd067e47e6b1e7655687277d3b` | 2,770 | Pipeline Component |
| `fromsource/verifier.py` | `e397c9b5477cac8e4cf9e1b954307078` | 6,214 | Post-build package Mach-O and install-tree validator |

## Shell Scripts

| File | MD5 Checksum | Size (bytes) | Role / Purpose |
| :--- | :--- | :--- | :--- |
| `build_and_install_gcc.sh` | `aab7062e0e3956c4ea2922de5386f896` | 3,167 | Pipeline Component |
| `install.sh` | `a1f5a7950eb95f0ed7f2cf51c92a3b3a` | 25,071 | Pipeline Component |
| `run_tests.sh` | `ee39cb22b1565224f70e34e7924371a1` | 1,730 | Pipeline Component |
| `scripts/bootstrap.sh` | `2a404d78b117de62b1319108a08d7260` | 19,332 | Pipeline Component |
| `scripts/build_and_install.sh` | `11be745ab1126c7223791595725866ff` | 2,562 | Pipeline Component |
| `scripts/build_repo.sh` | `d41d8cd98f00b204e9800998ecf8427e` | 0 | Pipeline Component |
| `scripts/test_package.sh` | `d41d8cd98f00b204e9800998ecf8427e` | 0 | Pipeline Component |
| `scripts/update_packages.sh` | `d41d8cd98f00b204e9800998ecf8427e` | 0 | Pipeline Component |
