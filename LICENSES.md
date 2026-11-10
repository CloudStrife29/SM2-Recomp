# Licenses

Italiano: vedi LICENZE.md.

This package brings together programs by different authors, each with its own license. **The game is not included**: neither data nor translated code. The PC game is prepared on the user's own computer, from their own disc.

| Part | Folder | Authors | License | Text |
|---|---|---|---|---|
| EnterElectro-Recomp launcher and tools ("Launcher e strumenti di EnterElectro-Recomp" in `LICENZE.md`) | `SM2-Launcher.cmd`, `PROVA-PC.cmd`, `tools\` (except `tools\toolchain\` and `tools\overlay\`), `aot\`, `LEGGIMI.md`, `README.md`, `LICENZE.md`, `LICENSES.md`, `PROSSIMI_OBIETTIVI.md`, `ROADMAP.md`, `game_options.toml` | CloudStrife29 (Daniel) | MIT | `LICENSE` |
| Launcher window images (background, title lettering, icons), made by a program | `tools\grafica\` | CloudStrife29 (Daniel); title lettering set in the Inter typeface by Rasmus Andersson | MIT (the images); the Inter font (SIL Open Font License 1.1) **is not in the package** and its license does not cover images made with it | `LICENSE` and `tools\grafica\LEGGIMI.txt` |
| Prebuilt engine (compiler cache): objects of psxrecomp, recomp-ui and their libraries, **never game code** | `cache\compilatore\` | built by EnterElectro-Recomp with the tools and from the sources of this package | the same as the sources: PolyForm Noncommercial 1.0.0 (psxrecomp), MIT (recomp-ui), the libraries' own (MIT, BSD, LGPL-2.1…; their sources are in the package) | as for `psxrecomp\` and `recomp-ui\` |
| psxrecomp | `psxrecomp\` | Matthew Stanley | PolyForm Noncommercial 1.0.0 | `psxrecomp\LICENSE` |
| recomp-net | `psxrecomp\lib\recomp-net\` | recomp-net contributors | MIT | `psxrecomp\lib\recomp-net\LICENSE` |
| retcomm-rbengine | `psxrecomp\lib\retcomm-rbengine\` | retcomm-rbengine contributors | MIT | `psxrecomp\lib\retcomm-rbengine\LICENSE` |
| recomp-ui | `recomp-ui\` | Matthew Stanley | MIT | `recomp-ui\LICENSE` |
| Libraries included in psxrecomp (OpenBIOS, libchdr, libwebp, toml11, stb_image, xxHash, TinyCC and others) | inside `psxrecomp\` | various | their own (MIT, BSD, LGPL-2.1, MPL-2.0…) | `psxrecomp\THIRD_PARTY_ATTRIBUTION.md` and `psxrecomp\runtime\licenses\` |
| libwebp sources for the first build (so that psxrecomp does not download them) | `psxrecomp\third_party\libwebp-4fa21912338357f89e4fd51cf2368325b59e9bd9.tar.gz` | Google and the libwebp authors | BSD-3-Clause, plus Google's patent grant | `COPYING` and `PATENTS` inside the archive |
| psxrecomp's overlay toolchain: Python 3.13.1 embeddable and TinyCC 0.9.27 (original archives), to compile on the PC the code that was not compiled in advance; the launcher copies them into every installation, so psxrecomp does not download them | `tools\overlay\` | Python Software Foundation; Fabrice Bellard and the TinyCC authors | Python: PSF License Agreement; TinyCC: LGPL-2.1 | `LICENSE.txt` inside the Python archive; `psxrecomp\runtime\licenses\TinyCC-LICENSE.txt`; TinyCC source: `tools\overlay\tcc-0.9.27.tar.bz2` |
| Build tools cmake-clang-v1 1.0.14: llvm-mingw 20260616 (LLVM/clang, mingw-w64, GNU make, busybox-w32), CMake, Ninja, ccache, Python, zlib, SDL3 | `tools\toolchain\cmake-clang-v1-windows-x64.zip`, extracted at the first start into `tools\toolchain\cmake-clang-v1\` | RetroPortingToolKit and the original projects | their own: Apache-2.0 with the LLVM exception, BSD-3-Clause, MIT, PSF, zlib; GPL or LGPL for busybox-w32, GNU make, ccache, gendef and widl | inside the zip: `LICENSE.TXT`, `busybox\LICENSE.txt`, `share\make\COPYING.txt` and the others |
| Sources of the GPL and LGPL programs of the build tools: busybox-w32, GNU make 4.4.1, ccache 4.13.6, mingw-w64 (gendef, widl) and the llvm-mingw scripts they were built with | `tools\toolchain\sorgenti\` | the authors of those programs | their own (GPL-2.0, GPL-3.0, LGPL-2.1 and others) | `tools\toolchain\sorgenti\LEGGIMI.txt` (in English: `tools\toolchain\sorgenti\README.txt`) and the license files inside each archive |

## AI movies: components downloaded only on request (not in the package)

If you choose the AI movies, the launcher downloads these components into `tools\ia\`, only after asking for your permission. They are not part of the package and keep their own licences, whose texts come with the downloaded files.

| Component | Where it goes | Authors | License | From |
|---|---|---|---|---|
| onnxruntime-directml 1.24.4 | `tools\ia\py\onnxruntime\` | Microsoft | MIT (`LICENSE` and `ThirdPartyNotices.txt` in the same folder); it contains Microsoft's DirectML (`DirectML.dll`), under its own terms | pypi.org |
| numpy 2.5.4 | `tools\ia\py\numpy\` | the NumPy developers | BSD-3-Clause, plus the licences of the libraries it includes, listed in `tools\ia\py\numpy-2.5.4.dist-info\licenses\LICENSE.txt` | pypi.org |
| Swin2SR, "Real-World SR x4" model (PSNR version) | `tools\ia\modelli\` | Marcos V. Conde and the Swin2SR authors; ONNX conversion by Xenova | Apache 2.0 | github.com/mv-lab/swin2sr; the file from huggingface.co/Xenova/swin2SR-realworld-sr-x4-64-bsrgan-psnr |
| Real-ESRGAN general-x4v3 and animevideov3 (weights), converted to ONNX on your PC | `tools\ia\modelli\` | Xintao Wang and the Real-ESRGAN authors | BSD-3-Clause | github.com/xinntao/Real-ESRGAN |

The Windows builds of onnxruntime have Microsoft's telemetry turned on by default (see `tools\ia\py\onnxruntime\Privacy.md`): the launcher turns it off before using them. The prepared AI movies come from your disc: like the enhanced movies, they stay on your PC and must not be distributed.

## What it means in practice

- **psxrecomp has a non-commercial license**: the package may be used, copied and distributed **only free of charge and for non-commercial purposes**. Whoever distributes it keeps the license files inside: this overview, `LICENSE`, `psxrecomp\LICENSE` and those in the other folders.
- **The launcher is MIT**: its files may be used, changed and distributed also on their own, in any project, keeping the copyright notice and the text of `LICENSE`. The MIT license applies only to the launcher files: the other parts keep their own licenses.
- **Some programs of the build tools are under the GPL or LGPL**: whoever distributes the package with the tools must also provide their sources. They are already in the package, in `tools\toolchain\sorgenti\`: they must be kept together with the tools zip. These programs (busybox-w32, GNU make, ccache, gendef and widl) are only used while building: the compiled game contains nothing from them.
- **The prebuilt engine** (`cache\compilatore\`) only holds files that the package's tools rebuild identically from the package's sources: it only makes installing faster and can be deleted. The license of the sources it comes from applies, above all psxrecomp's non-commercial license.
- The other parts are MIT, BSD or similar: they mainly ask that the copyright notice and the license text be kept, and those are already in their folders.

## Changes to psxrecomp

The package contains psxrecomp at the commit given in `PACCHETTO.txt`, with some files changed by EnterElectro-Recomp. The list of files and the differences are in `psxrecomp_modifiche.patch`. The changes are for:

- compiling the level modules ahead of time (Milestone 3);
- fixing idle skip (`runtime\src\psx_cycles.c`): with `idle_skip` an interrupt could arrive late;
- making the CPU work less (since 2 November 2026): shortcuts in the checks the engine makes at every step (interrupts, addresses of the translated code, idle skip), with two new files, `runtime\include\psx_fastpath.h` and `runtime\include\psx_idle_state.h`. The game does exactly the same things: checked frame by frame.

Since 0.12 also:

- enhanced movies: up to 64 movies instead of 16 and 3 sectors of slack (`runtime\src\gpu_fmv_hd.c`);
- start-up volume from the `PSX_VOLUME` variable (`runtime\src\host_osd.c`);
- relative PGO profile path `pgo/default.profdata` when building with Ninja (`runtime\runtime.cmake`), so the compiler cache is reused across folders;
- emitters built from the folder's real path (`psxrecomp_cli.py`), so they are not rebuilt on every install;
- adaptive vertical sync becoming normal sync on screens faster than the game (`runtime\src\main.cpp`): in fullscreen the picture no longer tears;
- the new real-time movie filter, only when the launcher asks for it (`runtime\src\gpu_gl_renderer.c`); `runtime\src\mdec.c` only remembers the quantisation of the last decoded block, decoding does not change.
- PGXP as in DuckStation: depth decided for the whole polygon, quads included ("valid_w", `runtime\src\gpu.c` and `runtime\src\pgxp.cpp`), and the two missing DuckStation items, "Disable on 2D Polygons" (`runtime\src\gpu.c`) and "Depth Test Transparent Polygons" (`runtime\src\gpu_gl_renderer.c`), off by default and turned on only when the launcher asks for them.

The changes are meant to be proposed to the authors of psxrecomp; until they accept them, they apply only to this package.

The images of other games in the psxrecomp documentation have been removed from the package (`docs\assets\games\`, `docs\assets\widescreen\` and `docs\assets\ui\mod-launcher.png`): they are not needed to build or to play. psxrecomp's `README.md` still refers to them.

## The game

*Spider-Man 2: Enter Electro* belongs to its rights holders: Activision, Marvel and whoever holds the rights to it. EnterElectro-Recomp is not affiliated with them or endorsed by them. To use it you need your own original disc.
