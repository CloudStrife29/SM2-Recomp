# Licenze

English: see LICENSES.md.

Questo pacchetto mette insieme programmi di autori diversi, ognuno con la sua licenza. **Il gioco non c'è**: né dati né codice tradotto. Il gioco per PC si prepara sul computer di chi lo usa, a partire dal suo disco.

| Parte | Cartella | Autori | Licenza | Testo |
|---|---|---|---|---|
| Launcher e strumenti di EnterElectro-Recomp | `SM2-Launcher.cmd`, `PROVA-PC.cmd`, `tools\` (tranne `tools\toolchain\` e `tools\overlay\`), `aot\`, `LEGGIMI.md`, `README.md`, `LICENZE.md`, `LICENSES.md`, `PROSSIMI_OBIETTIVI.md`, `ROADMAP.md`, `game_options.toml` | CloudStrife29 (Daniel) | MIT | `LICENSE` |
| Immagini della finestra del launcher (sfondo, lettere del titolo, icone), fatte da un programma | `tools\grafica\` | CloudStrife29 (Daniel); lettere del titolo scritte con il carattere Inter di Rasmus Andersson | MIT (le immagini); il carattere Inter (SIL Open Font License 1.1) **non è nel pacchetto** e la sua licenza non riguarda le immagini fatte con esso | `LICENSE` e `tools\grafica\LEGGIMI.txt` |
| Motore già compilato (cache del compilatore): oggetti di psxrecomp, recomp-ui e delle loro librerie, **mai il codice del gioco** | `cache\compilatore\` | compilati da EnterElectro-Recomp con gli strumenti e dai sorgenti di questo pacchetto | le stesse dei sorgenti: PolyForm Noncommercial 1.0.0 (psxrecomp), MIT (recomp-ui), quelle delle librerie (MIT, BSD, LGPL-2.1…; i loro sorgenti sono nel pacchetto) | come per `psxrecomp\` e `recomp-ui\` |
| psxrecomp | `psxrecomp\` | Matthew Stanley | PolyForm Noncommercial 1.0.0 | `psxrecomp\LICENSE` |
| recomp-net | `psxrecomp\lib\recomp-net\` | recomp-net contributors | MIT | `psxrecomp\lib\recomp-net\LICENSE` |
| retcomm-rbengine | `psxrecomp\lib\retcomm-rbengine\` | retcomm-rbengine contributors | MIT | `psxrecomp\lib\retcomm-rbengine\LICENSE` |
| recomp-ui | `recomp-ui\` | Matthew Stanley | MIT | `recomp-ui\LICENSE` |
| Librerie incluse in psxrecomp (OpenBIOS, libchdr, libwebp, toml11, stb_image, xxHash, TinyCC e altre) | dentro `psxrecomp\` | vari | le loro (MIT, BSD, LGPL-2.1, MPL-2.0…) | `psxrecomp\THIRD_PARTY_ATTRIBUTION.md` e `psxrecomp\runtime\licenses\` |
| Sorgenti di libwebp per la prima compilazione (così psxrecomp non li scarica) | `psxrecomp\third_party\libwebp-4fa21912338357f89e4fd51cf2368325b59e9bd9.tar.gz` | Google e gli autori di libwebp | BSD-3-Clause, più la concessione sui brevetti di Google | `COPYING` e `PATENTS` dentro l'archivio |
| Toolchain degli overlay di psxrecomp: Python 3.13.1 incorporabile e TinyCC 0.9.27 (archivi originali), per compilare sul PC il codice non compilato in anticipo; il launcher li copia in ogni installazione, così psxrecomp non li scarica | `tools\overlay\` | Python Software Foundation; Fabrice Bellard e gli autori di TinyCC | Python: PSF License Agreement; TinyCC: LGPL-2.1 | `LICENSE.txt` dentro l'archivio di Python; `psxrecomp\runtime\licenses\TinyCC-LICENSE.txt`; sorgente di TinyCC: `tools\overlay\tcc-0.9.27.tar.bz2` |
| Strumenti di compilazione cmake-clang-v1 1.0.14: llvm-mingw 20260616 (LLVM/clang, mingw-w64, GNU make, busybox-w32), CMake, Ninja, ccache, Python, zlib, SDL3 | `tools\toolchain\cmake-clang-v1-windows-x64.zip`, estratto al primo avvio in `tools\toolchain\cmake-clang-v1\` | RetroPortingToolKit e i progetti originali | le loro: Apache-2.0 con l'eccezione di LLVM, BSD-3-Clause, MIT, PSF, zlib; GPL o LGPL per busybox-w32, GNU make, ccache, gendef e widl | dentro lo zip: `LICENSE.TXT`, `busybox\LICENSE.txt`, `share\make\COPYING.txt` e gli altri |
| Sorgenti dei programmi GPL e LGPL degli strumenti: busybox-w32, GNU make 4.4.1, ccache 4.13.6, mingw-w64 (gendef, widl) e gli script di llvm-mingw con cui sono stati compilati | `tools\toolchain\sorgenti\` | gli autori di quei programmi | le loro (GPL-2.0, GPL-3.0, LGPL-2.1 e altre) | `tools\toolchain\sorgenti\LEGGIMI.txt` (in inglese: `tools\toolchain\sorgenti\README.txt`) e i file di licenza dentro ogni archivio |

## Filmati IA: componenti scaricati solo su richiesta (non nel pacchetto)

Se scegli i filmati IA, il launcher scarica questi componenti in `tools\ia\`, solo dopo averti chiesto il permesso. Non fanno parte del pacchetto e restano con le loro licenze, i cui testi arrivano insieme ai file scaricati.

| Componente | Dove finisce | Autori | Licenza | Da dove |
|---|---|---|---|---|
| onnxruntime-directml 1.24.4 | `tools\ia\py\onnxruntime\` | Microsoft | MIT (`LICENSE` e `ThirdPartyNotices.txt` nella stessa cartella); contiene DirectML (`DirectML.dll`) di Microsoft, con le sue condizioni | pypi.org |
| numpy 2.5.4 | `tools\ia\py\numpy\` | gli sviluppatori di NumPy | BSD-3-Clause, più le licenze delle librerie che include, elencate in `tools\ia\py\numpy-2.5.4.dist-info\licenses\LICENSE.txt` | pypi.org |
| Swin2SR, modello «Real-World SR x4» (versione PSNR) | `tools\ia\modelli\` | Marcos V. Conde e gli autori di Swin2SR; conversione ONNX di Xenova | Apache 2.0 | github.com/mv-lab/swin2sr; il file da huggingface.co/Xenova/swin2SR-realworld-sr-x4-64-bsrgan-psnr |
| Real-ESRGAN general-x4v3 e animevideov3 (pesi), convertiti in ONNX sul tuo PC | `tools\ia\modelli\` | Xintao Wang e gli autori di Real-ESRGAN | BSD-3-Clause | github.com/xinntao/Real-ESRGAN |

Le versioni di onnxruntime per Windows hanno la telemetria di Microsoft accesa di default (vedi `tools\ia\py\onnxruntime\Privacy.md`): il launcher la spegne prima di usarle. I filmati IA preparati vengono dal tuo disco: come i filmati migliorati, restano sul tuo PC e non vanno distribuiti.

## Cosa vuol dire, in pratica

- **psxrecomp ha una licenza non commerciale**: il pacchetto si può usare, copiare e distribuire **solo gratis e per scopi non commerciali**. Chi lo distribuisce lascia dentro i file delle licenze: questo, `LICENSE`, `psxrecomp\LICENSE` e quelli nelle altre cartelle.
- **Il launcher è MIT**: i suoi file si possono usare, cambiare e distribuire anche da soli, in qualunque progetto, lasciando l'avviso di copyright e il testo di `LICENSE`. La licenza MIT vale solo per i file del launcher: le altre parti restano con le loro licenze.
- **Alcuni programmi degli strumenti di compilazione hanno licenze GPL o LGPL**: chi distribuisce il pacchetto con gli strumenti deve dare anche i loro sorgenti. Sono già nel pacchetto, in `tools\toolchain\sorgenti\`: vanno lasciati insieme allo zip degli strumenti. Questi programmi (busybox-w32, GNU make, ccache, gendef e widl) servono solo durante la compilazione: il gioco compilato non contiene niente di loro.
- **Il motore già compilato** (`cache\compilatore\`) contiene solo file che gli strumenti del pacchetto rifanno uguali dai sorgenti del pacchetto: serve solo a installare più in fretta e si può cancellare. Vale la licenza dei sorgenti da cui viene, soprattutto quella non commerciale di psxrecomp.
- Le altre parti sono MIT, BSD o simili: chiedono soprattutto di conservare l'avviso di copyright e il testo della licenza, che sono già nelle loro cartelle.

## Modifiche a psxrecomp

Il pacchetto contiene psxrecomp al commit indicato in `PACCHETTO.txt`, con alcuni file cambiati da EnterElectro-Recomp. L'elenco dei file e le differenze sono in `psxrecomp_modifiche.patch`. Le modifiche servono a:

- compilare in anticipo i moduli dei livelli (Milestone 3);
- correggere il salto delle attese (`runtime\src\psx_cycles.c`): con `idle_skip` un interrupt poteva arrivare in ritardo;
- far lavorare meno la CPU (dal 2/11/2026): scorciatoie nei controlli che il motore fa a ogni passo (interrupt, indirizzi del codice tradotto, salto delle attese), con due file nuovi, `runtime\include\psx_fastpath.h` e `runtime\include\psx_idle_state.h`. Il gioco fa esattamente le stesse cose: controllato fotogramma per fotogramma.

Dalla 0.12 anche:

- filmati migliorati: fino a 64 filmati invece di 16 e 3 settori di margine (`runtime\src\gpu_fmv_hd.c`);
- volume all'avvio dalla variabile `PSX_VOLUME` (`runtime\src\host_osd.c`);
- profilo PGO con il percorso relativo `pgo/default.profdata` quando si compila con Ninja (`runtime\runtime.cmake`), per riusare la cache del compilatore tra cartelle diverse;
- emettitori compilati dal percorso vero della cartella (`psxrecomp_cli.py`), per non ricompilarli a ogni installazione;
- sincronia verticale adattiva che diventa normale sugli schermi più veloci del gioco (`runtime\src\main.cpp`): a schermo intero l'immagine non strappa più;
- filtro dei filmati in tempo reale nuovo, solo quando lo chiede il launcher (`runtime\src\gpu_gl_renderer.c`); `runtime\src\mdec.c` ricorda soltanto la quantizzazione dell'ultimo blocco decodificato, la decodifica non cambia.
- PGXP come in DuckStation: la profondità decisa per tutto il poligono, anche per i quadrilateri («valid_w», `runtime\src\gpu.c` e `runtime\src\pgxp.cpp`), e le due voci di DuckStation che mancavano, «Disable on 2D Polygons» (`runtime\src\gpu.c`) e «Depth Test Transparent Polygons» (`runtime\src\gpu_gl_renderer.c`), spente di partenza e accese solo quando lo chiede il launcher.

Le modifiche sono pensate per essere proposte agli autori di psxrecomp; finché non le accettano, valgono solo per questo pacchetto.

Dal pacchetto sono state tolte le immagini di altri giochi della documentazione di psxrecomp (`docs\assets\games\`, `docs\assets\widescreen\` e `docs\assets\ui\mod-launcher.png`): non servono per compilare né per giocare. Il `README.md` di psxrecomp le cita ancora.

## Il gioco

*Spider-Man 2: Enter Electro* appartiene ai suoi titolari: Activision, Marvel e chi ne detiene i diritti. EnterElectro-Recomp non è collegato a loro né approvato da loro. Per usarlo serve il proprio disco originale.
