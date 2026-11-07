# SM2-Recomp — roadmap

Italiano: vedi PROSSIMI_OBIETTIVI.md.

This file comes with every published version of the launcher and says what comes next. It is a plan, not a promise: the order can change with what the tests show. Every version is released only after a complete round of tests: on the main versions of the game all 44 levels, long runs and a test of the package without internet; on the others installation, the start of every level and part of the story. Version 0.11 was fully tested in all 7 versions.

Current version: 0.11 (November 2026). Plan updated on 5 November 2026: 0.12 will be the last version before the game is rewritten (decompilation) and also brings everything that was planned for later.

## After 0.11: version 0.12

1. **Sharper movies.** The game's movies are 320×240 and heavily compressed. The launcher will have a "Movies" choice with these entries:
   - **Original**, as now;
   - **Real-time filter**: while the movie plays, it removes the compression blocks and upscales it better, with no preparation;
   - **Enhanced**: a button prepares, once, on your PC and from your disc, an upscaled version of every movie, which the game then plays instead of the originals. Like the rest of the PC game, the enhanced movies stay on your computer and are never distributed.
   - **AI movies, your choice:** three AI upscalers, Swin2SR (faithful: it does not invent detail), Real-ESRGAN general-x4v3 and Real-ESRGAN animevideov3 (sharper, but they invent some detail). The launcher shows test pictures made with each model from your disc and lists the possible defects of each; the programs and models are downloaded only if you choose this option.
2. **A more polished launcher.** A background picture for each version of the game, as in OpenGOAL, taken from your disc when you install (a frame of the enhanced movies or a scene of the game at 4K), and a cleaner window, divided into tabs.
3. **Controller in the first window.** Choose the controller, test its buttons and assign the game's commands by pressing the button to use; the same for the keyboard. Xbox and PlayStation controllers recognised automatically, rumble.
4. **Saves.** Memory cards managed from the launcher (backups, restoring, copying to another PC) and quick saves with a preview picture.
5. **Volume** adjustable from the launcher.
6. **Faster installation**, above all on PCs with few processors: a ready-made PGO profile in the package (no training game and a single build), full optimisation only for the code the game uses often and, if possible, the engine already compiled. The game must stay as fast as it is now.
7. **Updates without reinstalling.** The new launcher keeps the games already installed and asks to reinstall them only when the engine changes. Going from 0.11 to 0.12 needs one reinstall.
8. **Less stutter and no tearing:** a steadier picture on 60, 120, 144 and 240 Hz screens, also when the game's rate (50 Hz in Europe, 60 Hz in the USA and Japan) does not match the screen's.
9. **Known issues to fix:**
   - on low-end PCs, small slowdowns in a few heavy places (the Create-a-Spidey menu at 1080p, the turrets of "Rooftops By Night", the final battle with Sandman);
   - two reported graphics issues, still to be checked against the original PlayStation: the sky in one spot of the first level, and a light visible through a wall in "In Darkest Night";
   - widescreen: in a few places an object very close to the camera appears cut off at the edge of the original 4:3 picture;
   - the "render thread" option does not start in the game executable;
   - the game recorder (used for testing) stops where the game compiles new code during play;
   - two behaviours seen in the automated tests, to be understood better: a difference at the first start of a new executable, and a slow exit of the Japanese test executable.

New features reach the main versions first: USA Rev 1, the original USA release and one European version. The others (the other European version, France, Germany, Japan) stay installable and playable and get the new features when the extra work is small; features that do not depend on the version, such as the launcher, the controller and memory cards, apply to all of them at once.

## Always, in parallel

- Proposing to the psxrecomp authors the fixes and optimisations made for SM2-Recomp, so that they can become part of psxrecomp and the package carries fewer changes of its own.
- Automated tests for every version, including real play sessions recorded once and replayed by the program.

## Later: the game rewritten by hand

- Gradually replacing the most important parts of the game with hand-written code, starting from USA Rev 1: first drawing (widescreen without cut-offs, real draw distance), then camera and controls, then the menus, with PC options inside the game. The rewritten game will read data, text and voices from the player's own disc, of any version. Every rewritten part must behave like the original, and recorded play sessions will prove it. It is the longest piece of work.
- Vulkan as an extra choice will be considered once drawing is rewritten: today, on the test laptop, it performs like OpenGL.
