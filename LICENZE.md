# Licenze

English: see LICENSES.md.

Questo pacchetto mette insieme programmi di autori diversi, ognuno con la sua licenza. **Il gioco non c'è**: né dati né codice tradotto. Il gioco per PC si prepara sul computer di chi lo usa, a partire dal suo disco.

| Parte | Cartella | Autori | Licenza | Testo |
|---|---|---|---|---|
| Launcher e strumenti di SM2-Recomp | `SM2-Launcher.cmd`, `PROVA-PC.cmd`, `tools\` (tranne `tools\toolchain\`), `aot\`, `LEGGIMI.md`, `README.md`, `LICENZE.md`, `LICENSES.md`, `PROSSIMI_OBIETTIVI.md`, `ROADMAP.md`, `game_options.toml` | CloudStrife29 (Daniel) | MIT | `LICENSE` |
| psxrecomp | `psxrecomp\` | Matthew Stanley | PolyForm Noncommercial 1.0.0 | `psxrecomp\LICENSE` |
| recomp-net | `psxrecomp\lib\recomp-net\` | recomp-net contributors | MIT | `psxrecomp\lib\recomp-net\LICENSE` |
| retcomm-rbengine | `psxrecomp\lib\retcomm-rbengine\` | retcomm-rbengine contributors | MIT | `psxrecomp\lib\retcomm-rbengine\LICENSE` |
| recomp-ui | `recomp-ui\` | Matthew Stanley | MIT | `recomp-ui\LICENSE` |
| Librerie incluse in psxrecomp (OpenBIOS, libchdr, libwebp, toml11, stb_image, xxHash, TinyCC e altre) | dentro `psxrecomp\` | vari | le loro (MIT, BSD, LGPL-2.1, MPL-2.0…) | `psxrecomp\THIRD_PARTY_ATTRIBUTION.md` e `psxrecomp\runtime\licenses\` |
| Sorgenti di libwebp per la prima compilazione (così psxrecomp non li scarica) | `psxrecomp\third_party\libwebp-4fa21912338357f89e4fd51cf2368325b59e9bd9.tar.gz` | Google e gli autori di libwebp | BSD-3-Clause, più la concessione sui brevetti di Google | `COPYING` e `PATENTS` dentro l'archivio |
| Strumenti di compilazione cmake-clang-v1 1.0.14: llvm-mingw 20260616 (LLVM/clang, mingw-w64, GNU make, busybox-w32), CMake, Ninja, ccache, Python, zlib, SDL3 | `tools\toolchain\cmake-clang-v1-windows-x64.zip`, estratto al primo avvio in `tools\toolchain\cmake-clang-v1\` | RetroPortingToolKit e i progetti originali | le loro: Apache-2.0 con l'eccezione di LLVM, BSD-3-Clause, MIT, PSF, zlib; GPL o LGPL per busybox-w32, GNU make, ccache, gendef e widl | dentro lo zip: `LICENSE.TXT`, `busybox\LICENSE.txt`, `share\make\COPYING.txt` e gli altri |
| Sorgenti dei programmi GPL e LGPL degli strumenti: busybox-w32, GNU make 4.4.1, ccache 4.13.6, mingw-w64 (gendef, widl) e gli script di llvm-mingw con cui sono stati compilati | `tools\toolchain\sorgenti\` | gli autori di quei programmi | le loro (GPL-2.0, GPL-3.0, LGPL-2.1 e altre) | `tools\toolchain\sorgenti\LEGGIMI.txt` (in inglese: `tools\toolchain\sorgenti\README.txt`) e i file di licenza dentro ogni archivio |

## Cosa vuol dire, in pratica

- **psxrecomp ha una licenza non commerciale**: il pacchetto si può usare, copiare e distribuire **solo gratis e per scopi non commerciali**. Chi lo distribuisce lascia dentro i file delle licenze: questo, `LICENSE`, `psxrecomp\LICENSE` e quelli nelle altre cartelle.
- **Il launcher è MIT**: i suoi file si possono usare, cambiare e distribuire anche da soli, in qualunque progetto, lasciando l'avviso di copyright e il testo di `LICENSE`. La licenza MIT vale solo per i file del launcher: le altre parti restano con le loro licenze.
- **Alcuni programmi degli strumenti di compilazione hanno licenze GPL o LGPL**: chi distribuisce il pacchetto con gli strumenti deve dare anche i loro sorgenti. Sono già nel pacchetto, in `tools\toolchain\sorgenti\`: vanno lasciati insieme allo zip degli strumenti. Questi programmi (busybox-w32, GNU make, ccache, gendef e widl) servono solo durante la compilazione: il gioco compilato non contiene niente di loro.
- Le altre parti sono MIT, BSD o simili: chiedono soprattutto di conservare l'avviso di copyright e il testo della licenza, che sono già nelle loro cartelle.

## Modifiche a psxrecomp

Il pacchetto contiene psxrecomp al commit indicato in `PACCHETTO.txt`, con alcuni file cambiati da SM2-Recomp. L'elenco dei file e le differenze sono in `psxrecomp_modifiche.patch`. Le modifiche servono a:

- compilare in anticipo i moduli dei livelli (Milestone 3);
- correggere il salto delle attese (`runtime\src\psx_cycles.c`): con `idle_skip` un interrupt poteva arrivare in ritardo;
- far lavorare meno la CPU (dal 2/11/2026): scorciatoie nei controlli che il motore fa a ogni passo (interrupt, indirizzi del codice tradotto, salto delle attese), con due file nuovi, `runtime\include\psx_fastpath.h` e `runtime\include\psx_idle_state.h`. Il gioco fa esattamente le stesse cose: controllato fotogramma per fotogramma.

Le modifiche sono pensate per essere proposte agli autori di psxrecomp; finché non le accettano, valgono solo per questo pacchetto.

Dal pacchetto sono state tolte le immagini di altri giochi della documentazione di psxrecomp (`docs\assets\games\`, `docs\assets\widescreen\` e `docs\assets\ui\mod-launcher.png`): non servono per compilare né per giocare. Il `README.md` di psxrecomp le cita ancora.

## Il gioco

*Spider-Man 2: Enter Electro* appartiene ai suoi titolari: Activision, Marvel e chi ne detiene i diritti. SM2-Recomp non è collegato a loro né approvato da loro. Per usarlo serve il proprio disco originale.
