# Licenses

Italiano: vedi LICENZE.md.

This package brings together programs by different authors, each with its own license. **The game is not included**: neither data nor translated code. The PC game is prepared on the user's own computer, from their own disc.

| Part | Folder | Authors | License | Text |
|---|---|---|---|---|
| SM2-Recomp launcher and tools ("Launcher e strumenti di SM2-Recomp" in `LICENZE.md`) | `SM2-Launcher.cmd`, `PROVA-PC.cmd`, `tools\` (except `tools\toolchain\`), `aot\`, `LEGGIMI.md`, `README.md`, `LICENZE.md`, `LICENSES.md`, `PROSSIMI_OBIETTIVI.md`, `ROADMAP.md`, `game_options.toml` | CloudStrife29 (Daniel) | MIT | `LICENSE` |
| psxrecomp | `psxrecomp\` | Matthew Stanley | PolyForm Noncommercial 1.0.0 | `psxrecomp\LICENSE` |
| recomp-net | `psxrecomp\lib\recomp-net\` | recomp-net contributors | MIT | `psxrecomp\lib\recomp-net\LICENSE` |
| retcomm-rbengine | `psxrecomp\lib\retcomm-rbengine\` | retcomm-rbengine contributors | MIT | `psxrecomp\lib\retcomm-rbengine\LICENSE` |
| recomp-ui | `recomp-ui\` | Matthew Stanley | MIT | `recomp-ui\LICENSE` |
| Libraries included in psxrecomp (OpenBIOS, libchdr, libwebp, toml11, stb_image, xxHash, TinyCC and others) | inside `psxrecomp\` | various | their own (MIT, BSD, LGPL-2.1, MPL-2.0…) | `psxrecomp\THIRD_PARTY_ATTRIBUTION.md` and `psxrecomp\runtime\licenses\` |
| libwebp sources for the first build (so that psxrecomp does not download them) | `psxrecomp\third_party\libwebp-4fa21912338357f89e4fd51cf2368325b59e9bd9.tar.gz` | Google and the libwebp authors | BSD-3-Clause, plus Google's patent grant | `COPYING` and `PATENTS` inside the archive |
| Build tools cmake-clang-v1 1.0.14: llvm-mingw 20260616 (LLVM/clang, mingw-w64, GNU make, busybox-w32), CMake, Ninja, ccache, Python, zlib, SDL3 | `tools\toolchain\cmake-clang-v1-windows-x64.zip`, extracted at the first start into `tools\toolchain\cmake-clang-v1\` | RetroPortingToolKit and the original projects | their own: Apache-2.0 with the LLVM exception, BSD-3-Clause, MIT, PSF, zlib; GPL or LGPL for busybox-w32, GNU make, ccache, gendef and widl | inside the zip: `LICENSE.TXT`, `busybox\LICENSE.txt`, `share\make\COPYING.txt` and the others |
| Sources of the GPL and LGPL programs of the build tools: busybox-w32, GNU make 4.4.1, ccache 4.13.6, mingw-w64 (gendef, widl) and the llvm-mingw scripts they were built with | `tools\toolchain\sorgenti\` | the authors of those programs | their own (GPL-2.0, GPL-3.0, LGPL-2.1 and others) | `tools\toolchain\sorgenti\LEGGIMI.txt` (in English: `tools\toolchain\sorgenti\README.txt`) and the license files inside each archive |

## What it means in practice

- **psxrecomp has a non-commercial license**: the package may be used, copied and distributed **only free of charge and for non-commercial purposes**. Whoever distributes it keeps the license files inside: this overview, `LICENSE`, `psxrecomp\LICENSE` and those in the other folders.
- **The launcher is MIT**: its files may be used, changed and distributed also on their own, in any project, keeping the copyright notice and the text of `LICENSE`. The MIT license applies only to the launcher files: the other parts keep their own licenses.
- **Some programs of the build tools are under the GPL or LGPL**: whoever distributes the package with the tools must also provide their sources. They are already in the package, in `tools\toolchain\sorgenti\`: they must be kept together with the tools zip. These programs (busybox-w32, GNU make, ccache, gendef and widl) are only used while building: the compiled game contains nothing from them.
- The other parts are MIT, BSD or similar: they mainly ask that the copyright notice and the license text be kept, and those are already in their folders.

## Changes to psxrecomp

The package contains psxrecomp at the commit given in `PACCHETTO.txt`, with some files changed by SM2-Recomp. The list of files and the differences are in `psxrecomp_modifiche.patch`. The changes are for:

- compiling the level modules ahead of time (Milestone 3);
- fixing idle skip (`runtime\src\psx_cycles.c`): with `idle_skip` an interrupt could arrive late;
- making the CPU work less (since 2 November 2026): shortcuts in the checks the engine makes at every step (interrupts, addresses of the translated code, idle skip), with two new files, `runtime\include\psx_fastpath.h` and `runtime\include\psx_idle_state.h`. The game does exactly the same things: checked frame by frame.

The changes are meant to be proposed to the authors of psxrecomp; until they accept them, they apply only to this package.

The images of other games in the psxrecomp documentation have been removed from the package (`docs\assets\games\`, `docs\assets\widescreen\` and `docs\assets\ui\mod-launcher.png`): they are not needed to build or to play. psxrecomp's `README.md` still refers to them.

## The game

*Spider-Man 2: Enter Electro* belongs to its rights holders: Activision, Marvel and whoever holds the rights to it. SM2-Recomp is not affiliated with them or endorsed by them. To use it you need your own original disc.
