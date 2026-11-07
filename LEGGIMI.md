# SM2-Recomp

> **Per giocare scarica il pacchetto completo dalla pagina [Releases](https://github.com/CloudStrife29/SM2-Recomp/releases)**: è il file `SM2-Recomp-<versione>.zip` nella sezione «Assets» della release. Lo zip contiene anche psxrecomp (con le modifiche descritte in `psxrecomp_modifiche.patch`), recomp-ui e gli strumenti di compilazione, che in questo repository non ci sono: qui ci sono il launcher, i documenti e le licenze. «Code → Download ZIP» e gli archivi «Source code» che GitHub aggiunge a ogni release contengono solo questo repository, senza psxrecomp, recomp-ui e gli strumenti di compilazione: con quelli il launcher non può installare il gioco.

English: see README.md.

Port nativo per PC di **Spider-Man 2: Enter Electro** (PlayStation, 2001), fatto con la ricompilazione statica di [psxrecomp](https://github.com/mstan/psxrecomp).

Il progetto **non contiene niente del gioco**: né dati, né codice tradotto. Come per OpenGOAL, il gioco per PC si prepara sul tuo computer a partire dal **tuo disco**.

## Cosa serve

- Windows 10 o 11, 64 bit.
- Spazio libero: circa 350 MB per il pacchetto estratto, circa 1 GB per gli strumenti di compilazione (si preparano da soli al primo avvio) e fino a circa 3 GB per ogni versione installata.
- **Internet non serve.** Il pacchetto completo contiene già tutto: gli strumenti di compilazione (circa 200 MB, sempre la versione 1.0.14, controllata con la sua impronta SHA-256) e la libreria che le versioni precedenti scaricavano alla prima compilazione. Questo repository da solo (`git clone`, «Code → Download ZIP» o gli archivi «Source code») non basta: psxrecomp, recomp-ui e gli strumenti di compilazione ci sono solo nel pacchetto.
- Il dump del tuo disco di Spider-Man 2: Enter Electro, completo (settori da 2352 byte):
  - `.bin` + `.cue`, anche con più tracce;
  - CloneCD `.img` + `.ccd` (+ `.sub`);
  - un'immagine da 2352 byte senza `.cue`: il launcher ne scrive uno.

  Le immagini `.iso` «cotte» da 2048 byte per settore non vanno bene: hanno perso i dati dei filmati e dell'audio.

## Versioni riconosciute

| Versione | Seriale | Lingua |
|---|---|---|
| USA Rev 1 | SLUS-01378 | inglese |
| USA originale (prima dell'11 settembre 2001) | SLUS-01378 | inglese |
| Europa originale (prima dell'11 settembre 2001) | SLES-03623 | inglese |
| Europa/Australia Rev 1 | SLES-03623 | inglese |
| Francia («La Revanche d'Electro») | SLES-03624 | francese |
| Germania | SLES-03625 | tedesco |
| Giappone | SLPM-87073 | giapponese |

La versione si riconosce dall'eseguibile del disco. Il launcher dice anche se il dump è identico a quello catalogato da Redump; non è obbligatorio.

## Come si usa

1. Scarica lo zip del pacchetto (`SM2-Recomp-<versione>.zip`, circa 270 MB) dalla pagina [Releases](https://github.com/CloudStrife29/SM2-Recomp/releases) ed estrailo in una cartella con un percorso corto, per esempio `C:\Giochi\SM2-Recomp`: la compilazione crea file con nomi lunghi.
2. Fai doppio clic su **`SM2-Launcher.cmd`**. La prima volta prepara gli strumenti di compilazione in `tools\toolchain\cmake-clang-v1\`, estraendoli dallo zip che è già nel pacchetto: circa un minuto, senza internet. Non installa niente nel sistema e non cambia il PATH o il registro di Windows.
3. Si apre la finestra del launcher:
   - **Aggiungi un disco...**: scegli il `.cue` (o `.ccd`, `.bin`) del tuo dump. Il launcher lo riconosce e lo sposta nella cartella `input\<versione>\`, con tutti i suoi file. Non sovrascrive mai niente.
   - **Installa**: prepara e compila la versione scelta in `giochi\<versione>\`. Ci vogliono alcuni minuti; su un PC veloce 3 o 4. Per compilare usa tre quarti dei processori del PC, così resta un po' di margine per il resto; dalla riga di comando si può scegliere un altro numero con `--core`. Su un PC lento conviene spuntare prima **Installa con il PGO** (vedi sotto).
   - **Gioca**: avvia il gioco con le opzioni scelte.

   La finestra e i messaggi sono in italiano o in inglese: il launcher sceglie da solo in base alla lingua di Windows (italiano se Windows è in italiano, altrimenti inglese). Si cambia con la scelta **Lingua / Language** nella finestra, oppure con `--lingua it|en` dalla riga di comando.

## Opzioni

- **Risoluzione interna:** l'immagine 3D viene disegnata a 720p, 1080p, 1440p o 4K invece che a 240 righe.
- **Filtro delle texture:** nearest (com'era), bilinear o xBR. xBR è il più pesante per la scheda video: su un portatile con una scheda video debole (provato con una GeForce 920MX) a 1080p il gioco rallenta.
- **PGXP:** geometria e texture più precise; per l'effetto completo spunta PGXP anche quando installi.
- **Widescreen (sperimentale):** la finestra diventa 16:9, 16:10 o 21:9 e durante il gioco si vede davvero di più ai lati, con le proporzioni giuste; menu e schermate 2D restano in 4:3 al centro. Dalla versione 0.8 del launcher il gioco disegna anche il pavimento e gli oggetti nelle parti in più ai lati (prima lì restavano zone nere). Dalla versione 0.9.1 l'immagine si allarga solo mentre si gioca: quando una missione fallisce il giornale, il menu GAME OVER e la schermata del nuovo tentativo restano in 4:3 (prima il giornale si rovinava). Dalla versione 0.11 anche gli oggetti che stanno solo nelle parti in più ai lati vengono disegnati subito: prima il gioco li scartava come se fossero fuori dallo schermo, e comparivano in ritardo. Poiché così il gioco disegna più poligoni, con il widescreen si accende da sola anche l'area più grande per i poligoni della mod "Distanza visiva" (senza spostare la nebbia). Per avere queste novità in un'installazione fatta con una versione precedente del launcher, premi di nuovo **Installa**. Il widescreen resta sperimentale: in qualche punto un oggetto molto vicino alla telecamera può apparire tagliato al bordo dell'immagine 4:3 originale.
- **Distanza visiva (sperimentale):** la nebbia comincia più lontano, così si vedono palazzi più lontani. Dalla versione 0.9 del launcher il gioco ha anche quattro volte più spazio per i poligoni di ogni immagine: con la nebbia più lontana i poligoni da disegnare sono molti di più, e nei punti più affollati lo spazio originale arrivava quasi pieno. Se hai installato con una versione precedente del launcher, premi di nuovo **Installa**.

- **Salto delle attese** (dalla versione 0.10 del launcher, acceso di default): il gioco, come quasi tutti i giochi PlayStation, aspetta il fotogramma successivo girando a vuoto; psxrecomp salta quei giri. Il gioco fa esattamente le stesse cose (controllato fotogramma per fotogramma in tutte e 7 le versioni, per 12.000 fotogrammi dall'accensione al primo livello) e la CPU lavora meno (circa il 9% a velocità normale). Il launcher lo scrive nel `game.toml` dell'installazione; serve un'installazione fatta con la versione 0.10, perché usa due correzioni di psxrecomp incluse nel pacchetto. Se ti sembra che qualcosa non vada, puoi spegnerlo: togli la spunta e premi **Gioca**.

Le opzioni restano salvate e si cambiano anche dal menu nel gioco. Sono le mod di psxrecomp, nel file `mods\state.toml` accanto al gioco (il salto delle attese invece è nel `game.toml`).

**Salvataggi rapidi (F7).** Oltre alle memory card del gioco, durante la partita il tasto F7 apre il menu dei salvataggi rapidi, che salvano e ricaricano il punto esatto in cui sei. Widescreen e distanza visiva cambiano la memoria del gioco: un salvataggio rapido fatto con queste due opzioni impostate in un altro modo non si carica (il gioco lo rifiuta e continua da dove sei). I salvataggi sulla memory card non hanno questo limite.

**Controller.** Dalla 0.11 il gioco usa da solo il primo controller collegato, anche se lo colleghi a gioco aperto; la tastiera funziona sempre. Per scegliere un altro controller o cambiare i tasti, spunta **Impostazioni di psxrecomp prima del gioco** e premi **Gioca**: nella finestra di psxrecomp, «Configure». La scelta resta salvata.

## Per i PC lenti: installa con il PGO

Spunta **Installa con il PGO** prima di premere **Installa** (dalla riga di comando: `installa --pgo`). Il launcher compila prima una versione del gioco che conta quante volte passa da ogni punto del codice, la fa giocare da sola per circa 3 minuti (con la finestra nascosta e senza audio: si vede solo il registro che va avanti) e poi compila il gioco vero ottimizzando le parti che si usano di più (PGO, ottimizzazione guidata dal profilo, di clang). Sul PC di prova il gioco così usa circa il 15% di CPU in meno (misurato il 4/11/2026 con le opzioni di default: avvio, filmati e titolo) e fa le stesse cose. L'installazione dura qualche minuto in più: su un PC veloce circa 5, su un PC lento anche più di 20. Se qualcosa va storto durante la partita di allenamento, il launcher compila il gioco normale senza PGO.

## Prova del PC

Per sapere se il gioco va a piena velocità sul tuo computer (per esempio un portatile), dopo aver aggiunto almeno un disco fai doppio clic su **`PROVA-PC.cmd`** (dalla versione 0.11 del launcher). Se serve, la prova installa quella versione con il PGO e con un eseguibile di prova: sui PC lenti anche più di mezz'ora, una volta sola. Poi apre il gioco per circa 3 minuti: va da solo fino al primo livello premendo i tasti, con l'audio spento (non toccare la sua finestra), e misura la velocità e quanto lavora la CPU. Alla fine scrive il risultato in `work\prova_pc\rapporto.txt` e prepara uno zip da mandare a chi segue il progetto: contiene solo testi e misure, niente del gioco. Le opzioni che hai scelto restano com'erano.

## Senza finestra

Gli stessi comandi funzionano dalla riga di comando (vanno bene anche i nomi inglesi: `identify`, `import`, `install`, `play`, `options`, `status`, `--profile` e così via; `--lingua it|en` sceglie la lingua dei messaggi):

```
SM2-Launcher.cmd riconosci
SM2-Launcher.cmd importa "D:\dump\Spider-Man 2 - Enter - Electro (USA).cue"
SM2-Launcher.cmd installa --profilo SLUS-01378-Rev1
SM2-Launcher.cmd installa --profilo SLUS-01378-Rev1 --pgo
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --risoluzione 1080p --pgxp si
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --attese no
SM2-Launcher.cmd avvia --profilo SLUS-01378-Rev1
SM2-Launcher.cmd stato
```

## Cartelle

| Cartella | Contenuto |
|---|---|
| `input\` | i tuoi dump, una cartella per versione |
| `giochi\` | le versioni installate (codice generato ed eseguibili: restano sul tuo PC) |
| `tools\` | il launcher e i suoi strumenti; in `tools\toolchain\` gli strumenti di compilazione e, in `tools\toolchain\sorgenti\`, i sorgenti dei loro programmi con licenza GPL o LGPL |
| `aot\` | solo fatti sul gioco (hash, dimensioni, indirizzi), nessun dato del gioco |
| `psxrecomp\`, `recomp-ui\` | psxrecomp e la sua interfaccia, con le loro licenze |

## Licenze

Il launcher di SM2-Recomp ha la licenza MIT (`LICENSE`). Il pacchetto contiene anche psxrecomp, recomp-ui e gli strumenti di compilazione, ognuno con la sua licenza: per quella di psxrecomp il pacchetto si può usare e distribuire **solo gratis e per scopi non commerciali**; per i programmi degli strumenti con licenza GPL o LGPL i sorgenti sono in `tools\toolchain\sorgenti\`. I dettagli sono in `LICENZE.md` (in inglese: `LICENSES.md`); nel pacchetto, `PACCHETTO.txt` elenca tutti i file con le loro impronte SHA-256.

Stato: giocabile, buon gameplay. Quello che il progetto ha documentato per la versione 0.11 (nelle [note della release 0.11](https://github.com/CloudStrife29/SM2-Recomp/releases/tag/v0.11)):

- **Versioni del disco riconosciute:** le 7 della tabella qui sopra.
- **Prove automatiche:** in tutte e 7 le versioni il gioco arriva a giocare dal codice ricompilato e partono tutti i 44 livelli, con i moduli dei livelli compilati in anticipo.
- **Prova manuale:** una partita completa dall'inizio alla fine con la versione USA Rev 1, su un portatile di prova (Core i7-6500U, GeForce 920MX). Per le altre versioni non è documentata una partita completa.
- **Problemi conosciuti:** sono elencati nelle note della release 0.11 e in `PROSSIMI_OBIETTIVI.md` («Difetti conosciuti da correggere»).

I prossimi passi dello sviluppo sono in `PROSSIMI_OBIETTIVI.md`.
