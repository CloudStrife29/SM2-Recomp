# SM2-Recomp

> **Per giocare scarica il pacchetto dalla pagina [Releases](https://github.com/CloudStrife29/SM2-Recomp/releases)** (istruzioni in italiano in `LEGGIMI.md`). Lo zip contiene anche psxrecomp (con le modifiche descritte in `psxrecomp_modifiche.patch`), recomp-ui e gli strumenti di compilazione, che in questo repository non ci sono: qui ci sono il launcher, i documenti e le licenze.
>
> **To play, download the package from the [Releases](https://github.com/CloudStrife29/SM2-Recomp/releases) page.** The zip also contains psxrecomp (with the changes described in `psxrecomp_modifiche.patch`), recomp-ui and the build tools, which are not in this repository: here are the launcher, the documents and the licenses.

Italiano: vedi LEGGIMI.md.

Native PC port of **Spider-Man 2: Enter Electro** (PlayStation, 2001), made by static recompilation with [psxrecomp](https://github.com/mstan/psxrecomp).

The project **contains nothing from the game**: neither data nor translated code. As with OpenGOAL, the PC game is prepared on your computer from **your own disc**.

## What you need

- Windows 10 or 11, 64-bit.
- Free space: about 350 MB for the extracted package, about 1 GB for the build tools (they set themselves up at the first start) and up to about 3 GB for each installed version.
- **No internet connection is needed.** The complete package already contains everything: the build tools (about 200 MB, always version 1.0.14, checked against its SHA-256 hash) and the library that earlier versions downloaded at the first build. Internet is only needed by those who download the project with `git clone` instead of the package: in that case the tools are downloaded at the first start.
- A complete dump of your Spider-Man 2: Enter Electro disc (2352-byte sectors):
  - `.bin` + `.cue`, also with several tracks;
  - CloneCD `.img` + `.ccd` (+ `.sub`);
  - a 2352-byte image without a `.cue`: the launcher writes one.

  "Cooked" `.iso` images with 2048 bytes per sector do not work: they have lost the movie and audio data.

## Recognized versions

| Version | Serial | Language |
|---|---|---|
| USA Rev 1 | SLUS-01378 | English |
| USA, original release (before 11 September 2001) | SLUS-01378 | English |
| Europe, original release (before 11 September 2001) | SLES-03623 | English |
| Europe/Australia Rev 1 | SLES-03623 | English |
| France ("La Revanche d'Electro") | SLES-03624 | French |
| Germany | SLES-03625 | German |
| Japan | SLPM-87073 | Japanese |

The version is recognized from the executable on the disc. The launcher also tells you whether the dump is identical to the one cataloged by Redump; this is not required.

## How to use it

1. Extract the package zip (`SM2-Recomp-<version>.zip`, about 270 MB) into a folder with a short path, for example `C:\Games\SM2-Recomp`: the build creates files with long names. Alternatively, download the project with its submodules: `git clone --recursive …` (in that case, though, the first start needs an internet connection).
2. Double-click **`SM2-Launcher.cmd`**. The first time, it prepares the build tools in `tools\toolchain\cmake-clang-v1\` by extracting them from the zip that is already in the package: about a minute, with no internet. It installs nothing in the system and does not change the Windows PATH or registry.
3. The launcher window opens:
   - **Add a disc...**: choose the `.cue` (or `.ccd`, `.bin`) of your dump. The launcher recognizes it and moves it, with all its files, into the folder `input\<version>\`. It never overwrites anything.
   - **Install**: prepares and builds the chosen version in `giochi\<version>\`. It takes a few minutes; 3 or 4 on a fast PC. For building it uses three quarters of the PC's processors, so that some headroom is left for everything else; from the command line you can choose another number with `--core`. On a slow PC it is worth ticking **Install with PGO** first (see below).
   - **Play**: starts the game with the chosen options.

   The window and the messages are in English or in Italian: the launcher chooses by itself from the Windows display language (Italian if Windows is in Italian, otherwise English). You can change it with the **Lingua / Language** choice in the window, or with `--language it|en` on the command line.

## Options

- **Internal resolution:** the 3D image is drawn at 720p, 1080p, 1440p or 4K instead of 240 lines.
- **Texture filter:** nearest (as it was), bilinear or xBR. xBR is the heaviest for the graphics card: on a laptop with a weak graphics card (tested with a GeForce 920MX) the game slows down at 1080p.
- **PGXP:** more precise geometry and textures; for the full effect, also tick PGXP when you install.
- **Widescreen (experimental):** the window becomes 16:9, 16:10 or 21:9 and during gameplay you really see more at the sides, with the right proportions; menus and 2D screens stay 4:3 in the center. Since launcher version 0.8 the game also draws the floor and the objects in the extra parts at the sides (before, those areas stayed black). Since version 0.9.1 the picture widens only while you play: when a mission fails, the journal, the GAME OVER menu and the retry screen stay 4:3 (before, the journal got garbled). Since version 0.11 the objects that are only in the extra parts at the sides are also drawn right away: before, the game discarded them as if they were off screen, and they appeared late. Because the game then draws more polygons, widescreen also switches on by itself the larger polygon area of the "Draw distance" mod (without moving the fog). To get these improvements in an installation made with an earlier launcher version, press **Install** again. Widescreen remains experimental: in a few places an object very close to the camera may appear cut off at the edge of the original 4:3 picture.
- **Draw distance (experimental):** the fog starts farther away, so more distant buildings are visible. Since launcher version 0.9 the game also has four times more room for the polygons of each frame: with the fog farther away there are many more polygons to draw, and in the busiest spots the original room was almost full. If you installed with an earlier launcher version, press **Install** again.

- **Idle skip** (since launcher version 0.10, on by default): like almost all PlayStation games, the game waits for the next frame by spinning in an empty loop; psxrecomp skips those loops. The game does exactly the same things (checked frame by frame in all 7 versions, for 12,000 frames from power-on to the first level) and the CPU works less (about 9% at normal speed). The launcher writes it into the installation's `game.toml`; it needs an installation made with version 0.10, because it uses two psxrecomp fixes included in the package. If something seems wrong, you can turn it off: untick it and press **Play**.

The options stay saved and can also be changed from the in-game menu. They are psxrecomp mods, stored in the file `mods\state.toml` next to the game (idle skip, instead, is in `game.toml`).

**Quick saves (save states, F7).** Besides the game's memory cards, during play the F7 key opens the quick-save menu, which saves and reloads the exact point where you are. Widescreen and draw distance change the game's memory: a quick save made with these two options set differently does not load (the game refuses it and carries on from where you are). Saves on the memory card do not have this limit.

**Controller.** Since 0.11 the game uses the first connected controller by itself, even if you plug it in while playing; the keyboard always works. To choose another controller or change the buttons, tick **psxrecomp settings before the game** and press **Play**: in the psxrecomp window, "Configure". The choice is saved.

## For slow PCs: install with PGO

Tick **Install with PGO** before pressing **Install** (from the command line: `install --pgo`). The launcher first builds a version of the game that counts how many times it passes through each point of the code, lets it play by itself for about 3 minutes (with the window hidden and no audio: you only see the log moving on), and then builds the real game, optimizing the parts that are used most (PGO, clang's profile-guided optimization). On the test PC the game built this way uses about 15% less CPU (measured on 4 November 2026 with the default options: start-up, movies and title screen) and does the same things. Installing takes a few minutes longer: about 5 on a fast PC, even more than 20 on a slow one. If something goes wrong during the training run, the launcher builds the normal game without PGO.

## PC test

To find out whether the game runs at full speed on your computer (for example a laptop), after adding at least one disc double-click **`PROVA-PC.cmd`** (since launcher version 0.11). If needed, the test installs that version with PGO and with a test executable: on slow PCs this can take more than half an hour, but only once. Then it opens the game for about 3 minutes: it goes to the first level by itself, pressing the buttons, with the audio off (do not touch its window), and measures the speed and how hard the CPU works. At the end it writes the result to `work\prova_pc\rapporto.txt` and prepares a zip to send to whoever follows the project: it contains only text and measurements, nothing from the game. The options you chose stay as they were.

## Without the window

The same commands work from the command line (the Italian command names work too; `--language it|en` chooses the language of the messages):

```
SM2-Launcher.cmd identify
SM2-Launcher.cmd import "D:\dump\Spider-Man 2 - Enter - Electro (USA).cue"
SM2-Launcher.cmd install --profile SLUS-01378-Rev1
SM2-Launcher.cmd install --profile SLUS-01378-Rev1 --pgo
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --resolution 1080p --pgxp yes
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --idle-skip no
SM2-Launcher.cmd play --profile SLUS-01378-Rev1
SM2-Launcher.cmd status
```

## Folders

| Folder | Contents |
|---|---|
| `input\` | your dumps, one folder per version |
| `giochi\` | ("games") the installed versions (generated code and executables: they stay on your PC) |
| `tools\` | the launcher and its tools; in `tools\toolchain\` the build tools and, in `tools\toolchain\sorgenti\` ("sources"), the sources of their programs licensed under the GPL or LGPL |
| `aot\` | only facts about the game (hashes, sizes, addresses), no game data |
| `psxrecomp\`, `recomp-ui\` | psxrecomp and its interface, with their licenses |

## Licenses

The SM2-Recomp launcher is under the MIT license (`LICENSE`). The package also contains psxrecomp, recomp-ui and the build tools, each with its own license: because of psxrecomp's license, the package may be used and distributed **only free of charge and for non-commercial purposes**; for the build-tool programs under the GPL or LGPL, the sources are in `tools\toolchain\sorgenti\`. The details are in `LICENSES.md` (in Italian: `LICENZE.md`); in the package, `PACCHETTO.txt` lists all the files with their SHA-256 hashes.

Status: playable,good gameplay. In all 7 versions the game reaches gameplay from the recompiled code, and in the automated tests all 44 levels start, with the precompiled level modules. The game has been played by a player from start to finish with no issues.

The next development steps are in `ROADMAP.md`.
