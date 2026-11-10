# EnterElectro-Recomp

> **Fino alla 0.11 il progetto si chiamava SM2-Recomp.** Dalla 0.12 si chiama EnterElectro-Recomp ed è pubblicato su [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp) e su [GitHub](https://github.com/CloudStrife29/SM2-Recomp), con la stessa cronologia.
>
> **Up to version 0.11 this project was called SM2-Recomp.** Since 0.12 it is called EnterElectro-Recomp and it is published on [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp) and on [GitHub](https://github.com/CloudStrife29/SM2-Recomp), with the same history.

> **Per giocare, con il tuo disco, hai due strade:**
>
> - il **pacchetto completo** `EnterElectro-Recomp-<versione>.zip` (fino alla 0.11 `SM2-Recomp-<versione>.zip`), nella sezione «Assets» della release su [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp/-/releases) o su [GitHub](https://github.com/CloudStrife29/SM2-Recomp/releases): contiene già tutto e funziona anche senza internet;
> - **questo repository** (`git clone`, oppure l'archivio «Source code» di una release): dalla 0.12 contiene anche psxrecomp (con le modifiche descritte in `psxrecomp_modifiche.patch`) e recomp-ui. Non contiene gli strumenti di compilazione (circa 200 MB): al primo avvio `SM2-Launcher.cmd` li scarica da internet, nella versione 1.0.14 controllata con la sua impronta SHA-256. Non contiene nemmeno il motore già compilato del pacchetto, quindi la prima installazione dura qualche minuto in più.
>
> Il resto di questa pagina vale per tutte e due (istruzioni in italiano in `LEGGIMI.md`).
>
> **To play, with your own disc, there are two ways:**
>
> - the **complete package** `EnterElectro-Recomp-<version>.zip` (`SM2-Recomp-<version>.zip` up to 0.11), in the "Assets" section of the release on [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp/-/releases) or on [GitHub](https://github.com/CloudStrife29/SM2-Recomp/releases): it already contains everything and also works without internet;
> - **this repository** (`git clone`, or the "Source code" archive of a release): since 0.12 it also contains psxrecomp (with the changes described in `psxrecomp_modifiche.patch`) and recomp-ui. It does not contain the build tools (about 200 MB): on the first start `SM2-Launcher.cmd` downloads them from the internet, version 1.0.14 checked against its SHA-256 hash. It does not contain the package's precompiled engine either, so the first installation takes a few minutes longer.
>
> The rest of this page applies to both.

Italiano: vedi LEGGIMI.md.

Native PC port of **Spider-Man 2: Enter Electro** (PlayStation, 2001), made by static recompilation with [psxrecomp](https://github.com/mstan/psxrecomp).

The project **contains nothing from the game**: neither data nor translated code. As with OpenGOAL, the PC game is prepared on your computer from **your own disc**.

## What you need

- Windows 10 or 11, 64-bit.
- Free space: about 410 MB for the extracted package, about 1 GB for the build tools (they set themselves up at the first start) and up to about 3 GB for each installed version.
- **With the complete package no internet connection is needed.** The complete package already contains everything: the build tools (about 200 MB, always version 1.0.14, checked against its SHA-256 hash) and the library that earlier versions downloaded at the first build; since 0.12 also the small toolchain psxrecomp uses to compile on your PC, while you play, the game code that was not compiled in advance (Python 3.13.1 embeddable and TinyCC 0.9.27, in `tools\overlay\`: before, with an internet connection, every installation downloaded it by itself). Only the programs and models of the AI movies are downloaded from the internet, and only if you ask for them. With the repository an internet connection is also needed at the first start, to download the build tools.
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

1. Extract the package zip (`EnterElectro-Recomp-<version>.zip`, about 385 MB) into a folder with a short path, for example `C:\Games\EnterElectro-Recomp`: the build creates files with long names. If you use the repository instead (see the note at the top), put it in a folder with a short path in the same way.
2. Double-click **`SM2-Launcher.cmd`**. The first time, it prepares the build tools in `tools\toolchain\cmake-clang-v1\` by extracting them from the zip that is already in the package: about a minute, with no internet. It installs nothing in the system and does not change the Windows PATH or registry. Since 0.12 the launcher has its own icon (a spider web, a lightning bolt and the letters SM2 over the night city, drawn for EnterElectro-Recomp: it is not the game's logo), and on its first start it puts the **EnterElectro-Recomp** shortcut with that icon in the folder: it opens the launcher like `SM2-Launcher.cmd` and can be copied to the desktop or pinned to the taskbar. If you move the folder, start `SM2-Launcher.cmd` once: the shortcut is remade by itself (copies on the desktop have to be made again).
3. The launcher window opens:
   - on the left, the list of the game versions, with a dot: green if installed, yellow if the disc is there but it needs installing, grey if the disc is missing;
   - **Add a disc**: choose the `.cue` (or `.ccd`, `.bin`) of your dump. The launcher recognizes it and moves it, with all its files, into the folder `input\<version>\`. It never overwrites anything;
   - the big button changes by itself: **Add a disc**, then **Install** (prepares and builds the chosen version in `giochi\<version>\`, a few minutes), then **Play**. For building the launcher uses three quarters of the PC's processors, so that some headroom is left for everything else; from the command line you can choose another number with `--core`. On a slow PC it is worth ticking **Install with PGO** first (see below);
   - below it, five actions: **Movies** (prepares the enhanced movies or the AI movies, with test pictures to compare them, see below), **Controls** (controller and keys), **Folder** (opens the installation folder), **Reinstall** and **Options**;
   - at the top, the pages **Game**, **Options**, **Saves** and **Log** (what the launcher is doing).

   The window background is a frame from your disc's enhanced movies, if you prepared them; otherwise a night city drawn for EnterElectro-Recomp. The window fits the screen, also on laptops with Windows scaling at 125% or 150%.

   The window and the messages are in English or in Italian: the launcher chooses by itself from the Windows display language (Italian if Windows is in Italian, otherwise English). You can change it with the **Lingua / Language** choice in the window, or with `--language it|en` on the command line.

## Options

- **Internal resolution:** the 3D image is drawn at 720p, 1080p, 1440p or 4K instead of 240 lines.
- **Texture filter:** nearest (as it was), bilinear or xBR. xBR is the heaviest for the graphics card: on a laptop with a weak graphics card (tested with a GeForce 920MX) the game slows down at 1080p.
- **PGXP:** precise geometry as in DuckStation: polygons stop wobbling and textures stop warping. See "PGXP (precise geometry)" below.
- **Widescreen (experimental):** the window becomes 16:9, 16:10 or 21:9 and during gameplay you really see more at the sides, with the right proportions; menus and 2D screens stay 4:3 in the center. With the "Fit to window" choice (since 0.12) the picture instead takes the shape of the window and follows it when you resize it, from 4:3 up with no limit (the idea comes from the widescreen mod by Matthew Stanley, the author of psxrecomp). Since launcher version 0.8 the game also draws the floor and the objects in the extra parts at the sides (before, those areas stayed black). Since version 0.9.1 the picture widens only while you play: when a mission fails, the journal, the GAME OVER menu and the retry screen stay 4:3 (before, the journal got garbled). Since version 0.11 the objects that are only in the extra parts at the sides are also drawn right away: before, the game discarded them as if they were off screen, and they appeared late. Because the game then draws more polygons, widescreen also switches on by itself the larger polygon area of the "Draw distance" mod (without moving the fog). To get these improvements in an installation made with an earlier launcher version, press **Install** again. Widescreen remains experimental: in a few places an object very close to the camera may appear cut off at the edge of the original 4:3 picture.
- **Draw distance (experimental):** the fog starts farther away, so more distant buildings are visible. Since launcher version 0.9 the game also has four times more room for the polygons of each frame: with the fog farther away there are many more polygons to draw, and in the busiest spots the original room was almost full. If you installed with an earlier launcher version, press **Install** again.

- **Idle skip** (since launcher version 0.10, on by default): like almost all PlayStation games, the game waits for the next frame by spinning in an empty loop; psxrecomp skips those loops. The game does exactly the same things (checked frame by frame in all 7 versions, for 12,000 frames from power-on to the first level) and the CPU works less (about 9% at normal speed). The launcher writes it into the installation's `game.toml`; it needs an installation made with version 0.10, because it uses two psxrecomp fixes included in the package. If something seems wrong, you can turn it off: untick it and press **Play**.

The options stay saved and are changed from the launcher's **Options** page: during play the game has no options menu, only the quick-save menu (F7) and the volume (+ and − on the numeric keypad). They are psxrecomp mods, stored in the file `mods\state.toml` next to the game (idle skip, instead, is in `game.toml`).

**Quick saves (save states, F7).** Besides the game's memory cards, during play the F7 key opens the quick-save menu, which saves and reloads the exact point where you are. Widescreen and draw distance change the game's memory: a quick save made with these two options set differently does not load (the game refuses it and carries on from where you are). The same goes for a quick save made with another version of the engine, for example with 0.11. Saves on the memory card do not have this limit.

**Volume.** On the Options page, **Volume at start** chooses the volume the game starts with (100% = as the game). In the game you can still change it with the keypad + and − keys. It needs an installation made with 0.12.

## PGXP (precise geometry)

The PlayStation computes the on-screen positions of polygons with integers: that is why in the original game polygons wobble by a pixel when the camera moves and textures warp on large surfaces (floors, walls), which shows a lot at high resolution. PGXP keeps the precise values of the calculations and draws with them, as in DuckStation. It changes only the drawing, never the game: with the same buttons the game does exactly the same things.

**How to turn it on.** On the Options page tick **PGXP (precise geometry)** and press **Play**. PGXP really works only if the game is built with its *hooks* (small pieces of code that hand PGXP the precise values of the game's calculations): if the installation does not have them, **Play** asks whether to build it again, only once (a few minutes, like a reinstall; saves and options stay). With PGO the package has the ready-made profile for the game with the hooks too, for the three main versions. From the command line: `install --profile <VERSION> --pgxp` (also together with `--pgo`) and then `options --profile <VERSION> --pgxp yes`.

**The items** are chosen with **PGXP options...**: they are all the items of DuckStation's PGXP settings, the latest two included (Depth Bias and Normalize Depth Scale), with the values DuckStation uses for Spider-Man 2 (the **DuckStation defaults** button puts them back): its default settings, plus CPU Mode on and Geometry Tolerance 3, which its game database sets by itself for all five versions of Spider-Man 2.

| Item | What it does | Default |
|---|---|---|
| Texture Correction | floors and walls stop warping when the camera moves | on |
| Color Correction | colour shading follows the perspective too (usually subtle); only with Texture Correction | off |
| Culling Correction | the game chooses which faces to hide from the precise positions: no gaps between far polygons | on |
| Preserve Projection Precision | the exact projection instead of the PS1's rounded one: removes the last wobble near the camera | off |
| CPU Mode | follows the precision through the processor's calculations too: more polygons corrected, more processor work | on (DuckStation turns it on by itself for Spider-Man 2: "Reduces jitter slightly") |
| Vertex Cache | for vertices without a history, uses the last precise position seen at the same point of the screen; it can wrongly move text and menus | off |
| Depth Buffer | decides what is in front from the vertices' depth instead of the game's drawing order; in Spider-Man 2 it wrongly hides pieces of Spider-Man, so leave it off; only with Texture Correction (the clear threshold, the seams and the item below are chosen with it) | off |
| Depth Test Transparent Polygons | with the depth buffer, semi-transparent shadows and effects are depth tested too; shadows often clip into the floor | off |
| Disable on 2D Polygons | polygons without depth on every vertex (interface, text, polygons built by the processor) stay whole at the PS1 position: it can fix a misaligned interface, but cracks can open next to precise polygons | off |
| Geometry Tolerance | discards precise positions further than this many pixels from the PS1 ones; -1 = no limit | 3 (DuckStation for Spider-Man 2: "Fixes glitch polygons due to sign bit flip and lightning effects") |
| Depth Bias | with the depth buffer, each polygon moves a little closer to the camera than the ones drawn before it, in millionths of depth (counted per polygon as in DuckStation: a quad is a single step): overlapping polygons stay in drawing order; high values can make polygons show through the ones in front | 1 |
| Normalize Depth Scale | removes the scale of each object's transform from the depth (Spider-Man 2 scales its transforms in 34 levels out of 44, models included: with the depth buffer some objects show through walls and floor, so here it stays off as in DuckStation); "depth buffer only" or "always", which applies it to Texture Correction too | automatic: as in DuckStation, off for Spider-Man 2 |

As in DuckStation, PGXP decides for the whole polygon whether it has depth: a polygon has it only if all its vertices have it, and only with Texture Correction on. Without it, that polygon is drawn without perspective and without the depth buffer and, with Disable on 2D Polygons, at the PS1 position. That is why, with Texture Correction off, the window also greys out Color Correction and the depth buffer.

As in DuckStation, with PGXP on **lines** are drawn at their precise positions too: Spider-Man 2 draws them in 34 levels out of 44, for example the rain. In the 44-level test the engine drew 46,965 of them, 99.88% with both ends at their precise positions, and in 4x pictures the rain is no longer snapped to the PS1 pixels: with the previous engine (and with PGXP off) 87-89% of the raindrops start and end on the edge of a PS1 pixel, now 24-27%, that is anywhere. The same with Vulkan: with PGXP off 64-86% of the raindrops start and end on the edge of a PS1 pixel, with PGXP on 26-31%. With smooth motion, lines stay precise in the generated frames too.

**What it does and what it costs** (measured on 6 November 2026 on the test PC with USA Rev 1, in the first level, with Spider-Man moving on the roof): with PGXP on and the defaults, 83% of the triangles drawn have every vertex at its precise position (with the game without hooks only 0.2%; without CPU Mode, that is with DuckStation's general defaults, 70%), and 77% of the textured triangles are perspective-correct. The processor works 5.52 ms per frame instead of 3.23 (+70.8%; a frame has 16.7 available; without CPU Mode 4.93); the game with the hooks but PGXP off costs +10.2%, which is why the launcher adds them only when you turn PGXP on. With the depth buffer, Depth Bias is counted per polygon as in DuckStation (in the first level 52,422 steps for 85,572 triangles in 7 seconds of play); in the 273 test pictures of the first level (13 short paths, exact frames: two identical runs give identical pictures) the depth buffer changes 144 of them, Depth Bias 1 (the default) instead of 0 changes 4, 6 pixels in all, because it only matters where two overlapping polygons have almost the same depth, and 1000 changes 125; Normalize Depth Scale changes the depth of about 690,000 vertices in 450 frames (7.5 seconds of play). With PGXP on and the defaults, the usual automatic partial play went through all 44 levels with no crashes or hangs, and the replayed sessions are identical frame by frame.

**Limits.** PGXP works with OpenGL; with Vulkan (experimental) polygon geometry and textures apply, and lines at their precise positions too (no depth buffer and no colour correction); the "software" renderer has no PGXP. Spider-Man visible through low walls is as in the original game (see `ROADMAP.md`): PGXP does not change it.

## Movies

The **Movies** choice (Options page) has six entries:

- **Original**: as on the PlayStation, enlarged in blocks;
- **Real-time filter**: with no preparation; it softens the compression blocks, interpolates the colour between pixels and upscales following the edges, with a little sharpening and no halos (small text stays as it is);
- **Enhanced**: frames cleaned of the compression blocks and upscaled 4 times, prepared once on your PC from your disc with the **Movies** action (from the command line `prepare-movies`). One version takes about 1.1 GB and, on a fast PC, a little over a minute. The game shows them instead of the originals; audio, timing and skipping stay the game's own. Tested on the three main versions: up to the first level more than 99.9% of the movie frames are replaced;
- **AI: Swin2SR**, **AI: Real-ESRGAN general** and **AI: Real-ESRGAN anime** (optional, since 0.12): frames upscaled 4 times by an artificial intelligence, see below.

The filters and the prepared movies work only with OpenGL (the normal renderer). Where prepared frames are missing, the game uses the Enhanced movies or the real-time filter. The prepared movies stay in your installation folder (`giochi\<version>\filmati_hd\` and `giochi\<version>\filmati_ia_<model>\`): they come from your disc and must not be distributed.

### AI movies (optional)

The **Movies** action opens the movies window of the chosen version. For the Enhanced movies and for each of the three AI models you find an explanation, the **possible defects**, the time it takes on your PC, two **test pictures** made from your disc (hold the left mouse button on the picture to see the original) and the buttons to prepare, stop and resume. **Use these movies in the game** puts the choice in the options; it is saved with **Play**.

| Model | What it is like | Possible defects | Time on the test PC (GeForce RTX 4060 Laptop) |
|---|---|---|---|
| **Swin2SR** (faithful) | the most faithful: it does not invent detail; sharper than Enhanced on faces, edges and large text | surfaces with fine texture (skin, walls, buildings) a little smoothed, a "painted" look; tiny text with a few crooked letters; in a few scenes colours a little more saturated | about 5 and a half hours; with an integrated graphics card, days |
| **Real-ESRGAN general-x4v3** (sharp) | very sharp and fast | it invents detail that was not there (small textures, creases, highlights); small text may change or become unreadable; light or dark halos around some edges | about 11 minutes |
| **Real-ESRGAN animevideov3** (cartoon) | the fastest and crispest, made for cartoons | it flattens shading: faces may look like plastic; it invents detail and may change small text; edges sometimes too strong | about 9 minutes |

For all three: small moving text may wobble a little. To reduce it the launcher stabilises the frames over time, like the temporal anti-aliasing of games: in the laboratory of the opening movie the text wobble drops by about 10-12%. Each model takes about 1-2 GB per game version.

**What is downloaded.** The AI movies need programs and models that are not in the package: they are downloaded **only once and only if you ask** (button **Download and make the test pictures**), after a question listing sizes, sites and licences. They are onnxruntime-directml 1.24.4 and numpy 2.5.4 from pypi.org (about 38 MB), Swin2SR from huggingface.co (53 MB) and the two Real-ESRGAN models from github.com (7 MB): about 100 MB in total, into `tools\ia\`. Every file is checked with its SHA-256 fingerprint; the two Real-ESRGAN models are converted to the ONNX format on your PC, without other programs. If the PC you play on has no internet, you can copy the `tools\ia\` folder from another PC where you already downloaded everything with the same launcher: the launcher checks the files and downloads nothing. The movies are prepared with the graphics card through DirectML (NVIDIA, AMD or Intel); without a suitable card the processor is used, much more slowly. The Windows builds of onnxruntime have Microsoft's telemetry turned on: the launcher turns it off.

**Preparation.** Before starting, the launcher tells you how long it will take on your PC (it measures it with the test pictures). Meanwhile you can use the launcher; **Stop** interrupts at the end of the current frame and **Resume** continues where it was. Closing the launcher also stops the preparation, which resumes the next time. While it works the PC does not go to sleep; for Swin2SR it is better to keep a laptop plugged in.

## Controls, controller and rumble

The game uses the first connected controller by itself, even if you plug it in while playing; the keyboard always works. The **Controls** action opens player 1's controls window:

- which controller to use (a specific one, the first connected or the keyboard only), analog or digital, stick dead zone;
- for every PlayStation button, the controller button and the keyboard key: click, then press the button to use within 5 seconds (Esc cancels); a warning says if a key already does another command; **Restore defaults** puts everything back;
- the live test: the commands light up when you press the buttons.

Xbox and PlayStation controllers (DualShock 4 and 5) are recognized with the same library as the game (SDL3). **Rumble:** the game looks for the DualShock only when it starts, so to get rumble connect the controller before pressing **Play**. **If the controller does not respond** (for example over Bluetooth), check that no program is hiding it from games, such as HidHide (usually installed together with DS4Windows): in HidHide stop hiding the controller, or add the game's executable (`SpiderMan2EnterElectro.exe` in the installation's `build-release` folder) to the allowed applications.

With **psxrecomp settings before the game** (Options page) the psxrecomp window opens first, even if you had hidden it from there.

## Saves

The **Saves** page shows, for the chosen version, the saves on each memory card (title, version, blocks and icon) and the quick saves (F7) with their preview, slot and date. **Back up the memory cards** copies them to the version's `saves\copie\` ("copies"); **Restore a backup...** puts back one of the copies; **Use another memory card...** puts in a file from another emulator (`.mcd`, `.mcr`, `.gme`). In both cases the launcher first backs up the current memory card. From the command line: `saves`.

**Copy the saved games to another version...** copies the Spider-Man 2 saved games of the chosen version to the memory card of another installed version, with the name that version looks for: for example from USA to Europe or the other way round. The saved games stay the same; the launcher only adjusts the screen height, which the European versions save differently (without the adjustment the picture would stay shorter), and first backs up the memory card that changes. The two US versions already share their saved games, and so do the two English European ones. Tested in the game with LOAD GAME from Europe to USA Rev 1 and from USA Rev 1 to Europe, France, Germany and Japan. From the command line: `saves --profile <VERSION> --copy-to <OTHER VERSION>`.

## Updating from an earlier version

Extract the new version into a new folder, next to the old one, and on the Options page press **Import from an earlier version...** (from the command line `import-folder`): the launcher moves discs, installations and saves from the old folder, without deleting anything. The installations stay playable; those built with a different engine show the note "earlier version: reinstall for the new features". **Reinstall** keeps options and saves. Going from 0.11 to 0.12 needs one reinstall; from then on only when the engine changes. Quick saves (F7) made with the previous engine no longer load: to carry on a game, use the memory cards.

## For slow PCs: install with PGO

Tick **Install with PGO** before pressing **Install** (from the command line: `install --pgo`). The game is built optimizing the parts of the code that are used most (PGO, clang's profile-guided optimization): on the test PC it uses about 15% less CPU (measured on 4 November 2026 with the default options: start-up, movies and title screen) and does the same things.

Since 0.12 the package contains the ready-made profile for the three main versions (USA Rev 1, original USA, original Europe), also for the game with the PGXP hooks: no training run and a single build, so with PGO installing takes almost as long as a normal install. For the other versions the launcher first builds a version of the game that counts how many times it passes through each point of the code, lets it play by itself for about 3 minutes (with the window hidden and no audio), and then builds the real game; if something goes wrong during the training run, it builds the normal game without PGO.

**Faster installation.** Since 0.12 the package also carries the engine already built (in `cache\compilatore\`: engine, interface and libraries only, never game code), and the launcher keeps there what it builds, so reinstalls rebuild only what changed. If the disc, the engine and the translation settings did not change, a reinstall also skips translating the game code (from the command line `install --regenerate` redoes it anyway). The package's engine is ready for all seven versions without PGO and for the three main ones with the ready PGO profile, also with the PGXP hooks. The longest part is the game's final link, which the cache does not shorten: since 0.12 it uses as many threads as the build cores (by itself it used one per physical core). On a PC with 4 processors, like a laptop (measured on 7 November 2026 on the test PC limited to 4 processors): Europe without PGO installs in about 220 seconds, USA Rev 1 with PGO in about 355 seconds.

## PC test

To find out whether the game runs at full speed on your computer (for example a laptop), after adding at least one disc double-click **`PROVA-PC.cmd`** (since launcher version 0.11). If needed, the test installs that version with PGO and with a test executable: on slow PCs this can take more than half an hour, but only once. Then it opens the game for about 3 minutes: it goes to the first level by itself, pressing the buttons, with the audio off (do not touch its window), and measures the speed and how hard the CPU works. At the end it writes the result to `work\prova_pc\rapporto.txt` and prepares a zip to send to whoever follows the project: it contains only text and measurements, nothing from the game. The options you chose stay as they were.

## Without the window

The same commands work from the command line (the Italian command names work too; `--language it|en` chooses the language of the messages):

```
SM2-Launcher.cmd identify
SM2-Launcher.cmd import "D:\dump\Spider-Man 2 - Enter - Electro (USA).cue"
SM2-Launcher.cmd install --profile SLUS-01378-Rev1
SM2-Launcher.cmd install --profile SLUS-01378-Rev1 --pgo
SM2-Launcher.cmd install --profile SLUS-01378-Rev1 --pgo --pgxp
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --resolution 1080p --pgxp yes
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --pgxp-projection yes --pgxp-cpu no
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --idle-skip no
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --movies enhanced --volume 80
SM2-Launcher.cmd prepare-movies --profile SLUS-01378-Rev1
SM2-Launcher.cmd ai-download --yes
SM2-Launcher.cmd ai-previews --profile SLUS-01378-Rev1
SM2-Launcher.cmd prepare-ai-movies --profile SLUS-01378-Rev1 --model anime
SM2-Launcher.cmd options --profile SLUS-01378-Rev1 --movies ai-anime
SM2-Launcher.cmd saves --profile SLUS-01378-Rev1 --backup
SM2-Launcher.cmd saves --profile SLES-03623 --copy-to SLUS-01378-Rev1
SM2-Launcher.cmd import-folder "C:\Games\SM2-Recomp-0.11"
SM2-Launcher.cmd play --profile SLUS-01378-Rev1
SM2-Launcher.cmd status
```

From 0.12 `SM2-Launcher.cmd` returns the launcher's exit code: 0 when the command worked, another number otherwise (for example 2 for `ai-download` without `--yes`), so it can be used in scripts too.

## Folders

| Folder | Contents |
|---|---|
| `input\` | your dumps, one folder per version |
| `giochi\` | ("games") the installed versions (generated code and executables, saves in `saves\`, enhanced movies in `filmati_hd\`, AI movies in `filmati_ia_<model>\` and their test pictures in `anteprime_ia\`: they stay on your PC) |
| `tools\ia\` | only if you choose the AI movies: the downloaded programs and models (onnxruntime-directml, numpy, Swin2SR, Real-ESRGAN), with their licences. It can be deleted |
| `cache\` | the compiler cache: the package's prebuilt engine and what the launcher builds. It only makes installing faster; it can be deleted |
| `tools\` | the launcher and its tools; in `tools\toolchain\` the build tools and, in `tools\toolchain\sorgenti\` ("sources"), the sources of their programs licensed under the GPL or LGPL; in `tools\overlay\` psxrecomp's overlay toolchain (Python 3.13.1 embeddable and TinyCC 0.9.27, with the TinyCC source), which the launcher copies into every installation |
| `aot\` | only facts about the game (hashes, sizes, addresses) and, in `aot\pgo\`, the ready-made PGO profiles (only counters on functions), no game data |
| `psxrecomp\`, `recomp-ui\` | psxrecomp and its interface, with their licenses |

## Licenses

The EnterElectro-Recomp launcher is under the MIT license (`LICENSE`). The package also contains psxrecomp, recomp-ui and the build tools, each with its own license: because of psxrecomp's license, the package may be used and distributed **only free of charge and for non-commercial purposes**; for the build-tool programs under the GPL or LGPL, the sources are in `tools\toolchain\sorgenti\`. The programs and models of the AI movies are not in the package: they are downloaded only if the player asks, each with its own licence (MIT, BSD-3-Clause, Apache 2.0). The details are in `LICENSES.md` (in Italian: `LICENZE.md`); in the package, `PACCHETTO.txt` lists all the files with their SHA-256 hashes.

Status: playable, good gameplay. What the project has documented so far:

- **Recognized disc versions:** the 7 in the "Recognized versions" table.
- **Automated tests:** in all 7 versions the game reaches gameplay from the recompiled code and all 44 levels start, with the precompiled level modules; the 0.12 features are tested automatically on the test PC.
- **Manual test:** with 0.11, a complete playthrough from start to finish with USA Rev 1, on a test laptop (Core i7-6500U, GeForce 920MX). No complete playthrough is documented for the other versions. With 0.12, a complete playthrough from start to finish with USA Rev 1, recorded (about two and a half hours of play in 10 sessions), on a PC with a Core i9 and a GeForce RTX 4060, with an original DualShock 4: the controls work with the USB cable and over Bluetooth. Rumble in 0.12 is still waiting for a specific test.
- **Known issues:** listed in `ROADMAP.md` ("Known issues in 0.12").

The next development steps are in `ROADMAP.md`.
