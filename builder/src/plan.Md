# Project Plan – Arch-Style Pacman Distribution for macOS

## Project Vision

The objective of this project is to build a native package management ecosystem for macOS that closely follows the philosophy, behavior, and workflow of Arch Linux.

Rather than creating another package manager, the goal is to make macOS feel familiar to Arch Linux users. Someone experienced with Arch should be able to sit at a macOS machine and immediately recognize the package layout, configuration, commands, repository structure, and overall workflow.

Homebrew will initially serve as the source of software packages. The system will automatically convert Homebrew formulae and bottles into Arch-compatible pacman packages that can be installed, queried, upgraded, and managed using pacman.

The long-term goal is for users to interact only with pacman.

---

# Design Goals

The project will follow several core principles.

## 1. Arch Compatibility

Whenever practical, behavior should match Arch Linux.

Examples include:

* pacman
* makepkg
* PKGBUILD
* repo-add
* package metadata
* repository layout
* dependency resolution
* package naming
* package database layout

Users should not need to learn a new workflow.

---

## 2. Native macOS Support

Although the interface resembles Arch Linux, the packages are native macOS packages.

Packages should:

* use Homebrew bottles whenever possible
* preserve macOS binaries
* preserve code signatures when possible
* preserve dylib layouts
* install into `/opt/pacman`

The project is **not** intended to emulate Linux or replace macOS.

---

## 3. Automation

Almost every repetitive task should be automated.

Examples include:

* downloading Homebrew metadata
* dependency discovery
* bottle download
* bottle verification
* bottle extraction
* package generation
* PKGBUILD generation
* package building
* repository updates
* GitHub publication
* weekly package refreshes

Human involvement should be limited to reviewing changes and approving releases when necessary.

---

# Repository Layout

The project is divided into several independent components.

```
project_pacman/

builder/
converter/
packages/
repo/
cache/
configs/
bootstrap/
scripts/
tests/
docs/
tools/
```

Each component has a single responsibility.

---

# Converter

The converter transforms Homebrew metadata into an internal package representation.

Responsibilities include:

* reading formula metadata
* reading bottle metadata
* parsing dependencies
* normalizing dependency names
* generating package metadata
* generating PKGBUILDs
* creating package directories

The converter never builds packages.

---

# Builder

The builder creates installable pacman packages.

Pipeline:

```
Formula

↓

Parser

↓

Dependency Resolver

↓

Stage Builder

↓

PKGBUILD

↓

makepkg

↓

.pkg.tar.zst
```

The builder ends after generating a valid package archive.

Package installation is intentionally outside the builder.

---

# Package Manager

The package manager uses pacman itself.

Target workflow:

```
pacman -U package.pkg.tar.zst

pacman -Q

pacman -Qi

pacman -Ql

pacman -R

pacman -S
```

Initially, packages will be installed using `pacman -U`.

Repository-based installation will come later.

---

# Repository System

After local package generation is validated, repository support will be implemented.

The repository will resemble Arch Linux.

```
core

extra
```

Repository databases will be generated using `repo-add`.

Eventually users should be able to execute:

```
pacman -Sy

pacman -S git

pacman -Syu

pacman -Ss vim
```

without needing Homebrew.

---

# Package Sources

Packages should preferably be generated from Homebrew bottles.

Priority order:

1. Homebrew bottles
2. Source build using Homebrew formula
3. Manual build recipes (only if necessary)

Bottle metadata should provide:

* version
* checksum
* download URL
* dependencies
* license
* homepage
* package description

---

# Development Phases

## Phase 1

Build local packages.

Deliverables:

* converter
* builder
* PKGBUILD generation
* makepkg integration
* install packages using `pacman -U`

---

## Phase 2

Local package management.

Deliverables:

* package installation
* package removal
* dependency verification
* package queries
* package upgrades

---

## Phase 3

Repository support.

Deliverables:

* repository generation
* repository databases
* repository synchronization
* package search
* package installation from repositories

---

## Phase 4

Automation.

Deliverables:

* GitHub repository publishing
* automatic package updates
* weekly synchronization with Homebrew
* GitHub Actions
* release automation

---

# Initial Package Set

Core packages include:

* pacman
* libarchive
* zstd
* openssl
* curl
* pcre2
* gettext

Extra packages include:

* git
* tree
* wget
* vim
* nano
* jq
* yq
* fastfetch
* rsync
* ripgrep
* fd
* fzf
* tmux

Additional packages can be added after the build pipeline is stable.

---

# Long-Term Vision

The completed project should provide a complete Arch-like package management experience on macOS.

A user should be able to install the bootstrap package, configure repositories once, and then use familiar commands such as:

```
pacman -Syu

pacman -S git vim tmux

pacman -Ss rust

pacman -Qqn

pacman -Qi git

pacman -Rns nano

makepkg

repo-add
```

The implementation details should remain largely invisible. Users interact with pacman, while Homebrew serves as the upstream source for package generation and updates.

The project's success will be measured by how closely the overall workflow resembles Arch Linux while remaining a native macOS solution.
