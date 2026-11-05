# SM2-Recomp — roadmap

Italiano: vedi PROSSIMI_OBIETTIVI.md.

This file comes with every published version of the launcher and says what comes next. It is a plan, not a promise: the order can change with what the tests show. Every version is released only after the same complete round of tests: all 7 versions of the game, all 44 levels, long runs and a test of the package without internet.

Current version: 0.11 (November 2026).

## After 0.11: version 0.12

1. **Sharper movies.** The game's movies are 320×240 and heavily compressed. The launcher will have a "Movies" choice with three entries:
   - **Original**, as now;
   - **Real-time filter**: while the movie plays, it removes the compression blocks and upscales it better, with no preparation;
   - **Enhanced**: a button prepares, once, on your PC and from your disc, an upscaled version of every movie, which the game then plays instead of the originals. Like the rest of the PC game, the enhanced movies stay on your computer and are never distributed.
2. **A more polished launcher.** A background picture for each version of the game, as in OpenGOAL, taken from your disc when you install (a frame of the enhanced movies or a scene of the game at 4K), and a cleaner window, divided into tabs.
3. **Controller in the first window.** Choose the controller, test its buttons and assign the game's commands by pressing the button to use; the same for the keyboard.
4. **Known issues to fix:**
   - widescreen: in a few places an object very close to the camera appears cut off at the edge of the original 4:3 picture;
   - the "render thread" option does not start in the game executable;
   - the game recorder (used for testing) stops where the game compiles new code during play;
   - two behaviours seen in the automated tests, to be understood better: a difference at the first start of a new executable, and a slow exit of the Japanese test executable.

## Version 0.13: modern PC game features

- **Controller:** rumble, Xbox and PlayStation controllers recognised automatically.
- **Saves:** managing memory cards from the launcher (backups, moving them between versions) and quick saves with a preview picture.
- **Graphics and audio:** Vulkan as an extra choice (on the test laptop it performs like OpenGL), adjustable volume.

## Always, in parallel

- Proposing to the psxrecomp authors the fixes and optimisations made for SM2-Recomp, so that they can become part of psxrecomp and the package carries fewer changes of its own.
- Automated tests for every version, including real play sessions recorded once and replayed by the program.

## Later

- Gradually replacing the most important parts of the game (camera, drawing, controls) with hand-written code. This is what allows real improvements, for example widescreen without cut-offs, and mods. It is the longest piece of work.
