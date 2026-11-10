# EnterElectro-Recomp

> **Fino alla 0.11 il progetto si chiamava SM2-Recomp.** Dalla 0.12 si chiama EnterElectro-Recomp ed è pubblicato su [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp) e su [GitHub](https://github.com/CloudStrife29/SM2-Recomp), con la stessa cronologia.

> **Per giocare, con il tuo disco, hai due strade:**
>
> - il **pacchetto completo** `EnterElectro-Recomp-<versione>.zip` (fino alla 0.11 `SM2-Recomp-<versione>.zip`), nella sezione «Assets» della release su [GitLab](https://gitlab.com/rdecomp-labs1/EnterElectro-Recomp/-/releases) o su [GitHub](https://github.com/CloudStrife29/SM2-Recomp/releases): contiene già tutto e funziona anche senza internet;
> - **questo repository** (`git clone`, oppure l'archivio «Source code» di una release): dalla 0.12 contiene anche psxrecomp (con le modifiche descritte in `psxrecomp_modifiche.patch`) e recomp-ui. Non contiene gli strumenti di compilazione (circa 200 MB): al primo avvio `SM2-Launcher.cmd` li scarica da internet, nella versione 1.0.14 controllata con la sua impronta SHA-256. Non contiene nemmeno il motore già compilato del pacchetto, quindi la prima installazione dura qualche minuto in più.
>
> Il resto di questa pagina vale per tutte e due.

English: see README.md.

Port nativo per PC di **Spider-Man 2: Enter Electro** (PlayStation, 2001), fatto con la ricompilazione statica di [psxrecomp](https://github.com/mstan/psxrecomp).

Il progetto **non contiene niente del gioco**: né dati, né codice tradotto. Come per OpenGOAL, il gioco per PC si prepara sul tuo computer a partire dal **tuo disco**.

## Cosa serve

- Windows 10 o 11, 64 bit.
- Spazio libero: circa 410 MB per il pacchetto estratto, circa 1 GB per gli strumenti di compilazione (si preparano da soli al primo avvio) e fino a circa 3 GB per ogni versione installata.
- **Con il pacchetto completo internet non serve.** Il pacchetto completo contiene già tutto: gli strumenti di compilazione (circa 200 MB, sempre la versione 1.0.14, controllata con la sua impronta SHA-256) e la libreria che le versioni precedenti scaricavano alla prima compilazione; dalla 0.12 anche il piccolo toolchain con cui psxrecomp compila sul tuo PC, mentre giochi, il codice del gioco non compilato in anticipo (Python 3.13.1 incorporabile e TinyCC 0.9.27, in `tools\overlay\`: prima, con internet, ogni installazione lo scaricava da sola). Da internet si scaricano solo i programmi e i modelli dei filmati IA, e solo se li chiedi. Con il repository internet serve anche al primo avvio, per scaricare gli strumenti di compilazione.
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

1. Estrai lo zip del pacchetto (`EnterElectro-Recomp-<versione>.zip`, circa 385 MB) in una cartella con un percorso corto, per esempio `C:\Giochi\EnterElectro-Recomp`: la compilazione crea file con nomi lunghi. Chi usa il repository (vedi l'avviso in cima) lo mette allo stesso modo in una cartella con un percorso corto.
2. Fai doppio clic su **`SM2-Launcher.cmd`**. La prima volta prepara gli strumenti di compilazione in `tools\toolchain\cmake-clang-v1\`, estraendoli dallo zip che è già nel pacchetto: circa un minuto, senza internet. Non installa niente nel sistema e non cambia il PATH o il registro di Windows. Dalla 0.12 il launcher ha una sua icona (una ragnatela, un fulmine e la scritta SM2 sulla città di notte, disegnata per EnterElectro-Recomp: non è il logo del gioco) e al primo avvio mette nella cartella il collegamento **EnterElectro-Recomp** con quell'icona: apre il launcher come `SM2-Launcher.cmd` e si può copiare sul desktop o aggiungere alla barra delle applicazioni. Se sposti la cartella, avvia una volta `SM2-Launcher.cmd`: il collegamento si rifà da solo (le copie sul desktop vanno rifatte).
3. Si apre la finestra del launcher:
   - a sinistra l'elenco delle versioni del gioco, con un pallino: verde se è installata, giallo se c'è il disco ma va installata, grigio se manca il disco;
   - **Aggiungi un disco**: scegli il `.cue` (o `.ccd`, `.bin`) del tuo dump. Il launcher lo riconosce e lo sposta nella cartella `input\<versione>\`, con tutti i suoi file. Non sovrascrive mai niente;
   - il pulsante grande cambia da solo: **Aggiungi un disco**, poi **Installa** (prepara e compila la versione scelta in `giochi\<versione>\`, alcuni minuti), poi **Gioca**. Per compilare il launcher usa tre quarti dei processori del PC, così resta un po' di margine per il resto; dalla riga di comando si può scegliere un altro numero con `--core`. Su un PC lento conviene spuntare prima **Installa con il PGO** (vedi sotto);
   - sotto, cinque azioni: **Filmati** (prepara i filmati migliorati o i filmati IA, con le immagini di prova per confrontarli, vedi sotto), **Comandi** (controller e tasti), **Cartella** (apre la cartella dell'installazione), **Reinstalla** e **Opzioni**;
   - in alto le pagine **Gioco**, **Opzioni**, **Salvataggi** e **Registro** (quello che il launcher sta facendo).

   Lo sfondo della finestra è un fotogramma dei filmati migliorati del tuo disco, se li hai preparati; altrimenti una città di notte disegnata per EnterElectro-Recomp. La finestra si adatta allo schermo, anche sui portatili con l'ingrandimento di Windows al 125% o al 150%.

   La finestra e i messaggi sono in italiano o in inglese: il launcher sceglie da solo in base alla lingua di Windows (italiano se Windows è in italiano, altrimenti inglese). Si cambia con la scelta **Lingua / Language** nella finestra, oppure con `--lingua it|en` dalla riga di comando.

## Opzioni

- **Risoluzione interna:** l'immagine 3D viene disegnata a 720p, 1080p, 1440p o 4K invece che a 240 righe.
- **Filtro delle texture:** nearest (com'era), bilinear o xBR. xBR è il più pesante per la scheda video: su un portatile con una scheda video debole (provato con una GeForce 920MX) a 1080p il gioco rallenta.
- **PGXP:** geometria precisa come in DuckStation: i poligoni non tremano più e le texture non si deformano. Vedi «PGXP (geometria precisa)» qui sotto.
- **Widescreen (sperimentale):** la finestra diventa 16:9, 16:10 o 21:9 e durante il gioco si vede davvero di più ai lati, con le proporzioni giuste; menu e schermate 2D restano in 4:3 al centro. Con la scelta «Adatta alla finestra» (dalla 0.12) l'immagine prende invece la forma della finestra e la segue quando la ridimensioni, da 4:3 in su senza limite (l'idea viene dalla mod widescreen di Matthew Stanley, l'autore di psxrecomp). Dalla versione 0.8 del launcher il gioco disegna anche il pavimento e gli oggetti nelle parti in più ai lati (prima lì restavano zone nere). Dalla versione 0.9.1 l'immagine si allarga solo mentre si gioca: quando una missione fallisce il giornale, il menu GAME OVER e la schermata del nuovo tentativo restano in 4:3 (prima il giornale si rovinava). Dalla versione 0.11 anche gli oggetti che stanno solo nelle parti in più ai lati vengono disegnati subito: prima il gioco li scartava come se fossero fuori dallo schermo, e comparivano in ritardo. Poiché così il gioco disegna più poligoni, con il widescreen si accende da sola anche l'area più grande per i poligoni della mod "Distanza visiva" (senza spostare la nebbia). Per avere queste novità in un'installazione fatta con una versione precedente del launcher, premi di nuovo **Installa**. Il widescreen resta sperimentale: in qualche punto un oggetto molto vicino alla telecamera può apparire tagliato al bordo dell'immagine 4:3 originale.
- **Distanza visiva (sperimentale):** la nebbia comincia più lontano, così si vedono palazzi più lontani. Dalla versione 0.9 del launcher il gioco ha anche quattro volte più spazio per i poligoni di ogni immagine: con la nebbia più lontana i poligoni da disegnare sono molti di più, e nei punti più affollati lo spazio originale arrivava quasi pieno. Se hai installato con una versione precedente del launcher, premi di nuovo **Installa**.

- **Salto delle attese** (dalla versione 0.10 del launcher, acceso di default): il gioco, come quasi tutti i giochi PlayStation, aspetta il fotogramma successivo girando a vuoto; psxrecomp salta quei giri. Il gioco fa esattamente le stesse cose (controllato fotogramma per fotogramma in tutte e 7 le versioni, per 12.000 fotogrammi dall'accensione al primo livello) e la CPU lavora meno (circa il 9% a velocità normale). Il launcher lo scrive nel `game.toml` dell'installazione; serve un'installazione fatta con la versione 0.10, perché usa due correzioni di psxrecomp incluse nel pacchetto. Se ti sembra che qualcosa non vada, puoi spegnerlo: togli la spunta e premi **Gioca**.

Le opzioni restano salvate e si cambiano dalla pagina **Opzioni** del launcher: durante la partita il gioco non ha un menu delle opzioni, ma solo il menu dei salvataggi rapidi (F7) e il volume (+ e − del tastierino). Sono le mod di psxrecomp, nel file `mods\state.toml` accanto al gioco (il salto delle attese invece è nel `game.toml`).

**Salvataggi rapidi (F7).** Oltre alle memory card del gioco, durante la partita il tasto F7 apre il menu dei salvataggi rapidi, che salvano e ricaricano il punto esatto in cui sei. Widescreen e distanza visiva cambiano la memoria del gioco: un salvataggio rapido fatto con queste due opzioni impostate in un altro modo non si carica (il gioco lo rifiuta e continua da dove sei). Lo stesso vale per un salvataggio rapido fatto con un'altra versione del motore, per esempio con la 0.11. I salvataggi sulla memory card non hanno questo limite.

**Volume.** Nella pagina Opzioni, **Volume all'avvio** sceglie il volume con cui parte il gioco (100% = come il gioco). Nel gioco si cambia ancora con + e − del tastierino. Serve un'installazione fatta con la 0.12.

## PGXP (geometria precisa)

La PlayStation calcola le posizioni dei poligoni sullo schermo con numeri interi: per questo nel gioco originale i poligoni tremano di un pixel quando la telecamera si muove e le texture si deformano sulle superfici grandi (pavimenti, muri), cosa che a risoluzione alta si nota molto. PGXP tiene i valori precisi dei calcoli e li usa per disegnare, come in DuckStation. Cambia solo il disegno, mai il gioco: con gli stessi tasti il gioco fa esattamente le stesse cose.

**Come si accende.** Nella pagina Opzioni spunta **PGXP (geometria precisa)** e premi **Gioca**. PGXP funziona davvero solo se il gioco è compilato con i suoi *punti di aggancio* (piccoli pezzi di codice che passano a PGXP i valori precisi dei calcoli del gioco): se l'installazione non li ha, **Gioca** chiede se ricompilarla, una volta sola (alcuni minuti, come una reinstallazione; salvataggi e opzioni restano). Con il PGO il pacchetto ha il profilo pronto anche per il gioco con i punti di aggancio, nelle tre versioni principali. Dalla riga di comando: `installa --profilo <VERSIONE> --pgxp` (anche insieme a `--pgo`) e poi `opzioni --profilo <VERSIONE> --pgxp si`.

**Le voci** si scelgono con **Opzioni PGXP...**: sono tutte quelle della finestra PGXP di DuckStation, comprese le ultime due (Depth Bias e normalizzazione della profondità), con i valori che DuckStation usa per Spider-Man 2 (il pulsante **Valori di DuckStation** li rimette): le sue impostazioni di partenza, più la modalità CPU accesa e la tolleranza a 3, che il suo database dei giochi mette da solo per tutte e cinque le versioni di Spider-Man 2.

| Voce | Cosa fa | Di partenza |
|---|---|---|
| Texture in prospettiva | pavimenti e muri non si deformano più quando la telecamera si muove | accesa |
| Colori in prospettiva | anche le sfumature di colore seguono la prospettiva (di solito si nota poco); solo con le texture in prospettiva | spenta |
| Correzione del culling | il gioco sceglie quali facce nascondere con le posizioni precise: niente buchi tra i poligoni lontani | accesa |
| Precisione della proiezione | la proiezione esatta invece di quella arrotondata della PS1: toglie l'ultimo tremolio vicino alla telecamera | spenta |
| Modalità CPU | segue la precisione anche nei calcoli del processore: più poligoni corretti, più lavoro per il processore | accesa (DuckStation la accende da solo per Spider-Man 2: «riduce un po' il tremolio») |
| Cache dei vertici | per i vertici senza storia usa l'ultima posizione precisa vista nello stesso punto dello schermo; può spostare per sbaglio scritte e menu | spenta |
| Buffer di profondità | decide cosa sta davanti con la profondità dei vertici invece che con l'ordine di disegno del gioco; in Spider-Man 2 nasconde per sbaglio pezzi di Spider-Man, quindi lascialo spento; solo con le texture in prospettiva (con lui si scelgono anche la soglia di pulizia, le fessure e la voce qui sotto) | spento |
| Profondità anche per i semitrasparenti | con il buffer di profondità anche ombre ed effetti semitrasparenti fanno il test di profondità; spesso le ombre entrano nel pavimento | spenta |
| Niente PGXP sui poligoni 2D | i poligoni senza profondità su tutti i vertici (interfaccia, scritte, poligoni fatti dal processore) restano interi nella posizione della PS1: può sistemare un'interfaccia storta, ma accanto ai poligoni precisi possono aprirsi fessure | spenta |
| Tolleranza | scarta le posizioni precise lontane più di tanti pixel da quelle della PS1; -1 = nessun limite | 3 (DuckStation per Spider-Man 2: «sistema i poligoni sbagliati per un cambio di segno e gli effetti dei fulmini») |
| Depth Bias | con il buffer di profondità ogni poligono va un po' più vicino alla telecamera di quelli disegnati prima, di tanti milionesimi della profondità (come in DuckStation si conta per poligono: un quadrilatero è un passo solo): i poligoni sovrapposti restano nell'ordine di disegno; valori alti possono far vedere poligoni attraverso quelli davanti | 1 |
| Normalizzazione della profondità | toglie dalla profondità la scala della trasformazione di ogni oggetto (Spider-Man 2 scala le trasformazioni in 34 livelli su 44, anche dei modelli: con il buffer di profondità alcuni oggetti si vedono attraverso muri e pavimento, quindi qui resta spenta come in DuckStation); «solo con il buffer di profondità» o «sempre», che la usa anche per le texture in prospettiva | automatica: come in DuckStation, per Spider-Man 2 spenta |

Come in DuckStation, PGXP decide per tutto il poligono se ha la profondità: un poligono ce l'ha solo se ce l'hanno tutti i suoi vertici e solo con le texture in prospettiva accese. Senza, quel poligono si disegna senza prospettiva e senza buffer di profondità e, con «Niente PGXP sui poligoni 2D», nella posizione della PS1. Per questo con le texture in prospettiva spente la finestra spegne anche colori in prospettiva e buffer di profondità.

Come in DuckStation, con PGXP acceso anche le **linee** vanno nelle posizioni precise: Spider-Man 2 ne disegna in 34 livelli su 44, per esempio la pioggia. Nella prova dei 44 livelli il motore ne ha disegnate 46.965, il 99,88% con tutte e due le estremità nelle posizioni precise, e nelle immagini a 4x la pioggia non è più agganciata ai pixel della PS1: con il motore di prima (e con PGXP spento) l'87-89% delle gocce comincia e finisce sul bordo di un pixel della PS1, adesso il 24-27%, cioè dove capita. Lo stesso con Vulkan: con PGXP spento il 64-86% delle gocce comincia e finisce sul bordo di un pixel della PS1, acceso il 26-31%. Con il movimento fluido le linee restano precise anche nei frame generati.

**Quanto fa e quanto costa** (misurato il 6/11/2026 sul PC di prova con la USA Rev 1, nel primo livello, con Spider-Man che si muove sul tetto): con PGXP acceso e i valori di partenza l'83% dei triangoli disegnati ha tutti i vertici nelle posizioni precise (con il gioco senza punti di aggancio solo lo 0,2%; senza la modalità CPU, cioè con le impostazioni generali di DuckStation, il 70%) e il 77% dei triangoli con le texture è corretto in prospettiva. Il processore lavora 5,52 millisecondi per frame invece di 3,23 (+70,8%; un frame ne ha a disposizione 16,7; senza la modalità CPU 4,93); il gioco con i punti di aggancio ma PGXP spento costa +10,2%, per questo il launcher li mette solo quando accendi PGXP. Con il buffer di profondità la Depth Bias si conta per poligono come in DuckStation (nel primo livello 52.422 passi per 85.572 triangoli in 7 secondi di gioco); nelle 273 immagini di prova del primo livello (13 percorsi brevi, frame esatti: due giri uguali danno immagini identiche) il buffer di profondità ne cambia 144, la Depth Bias a 1 (il valore di partenza) invece che a 0 ne cambia 4, in tutto 6 pixel, perché serve solo dove due poligoni sovrapposti hanno quasi la stessa profondità, e a 1000 ne cambia 125; la normalizzazione della profondità cambia la profondità di circa 690.000 vertici in 450 frame (7,5 secondi di gioco). Con PGXP acceso e i valori di partenza il gioco parziale automatico di sempre ha giocato tutti i 44 livelli senza chiusure né blocchi, e le partite rigiocate sono identiche frame per frame.

**Limiti.** PGXP vale con OpenGL; con Vulkan (sperimentale) valgono geometria e texture dei poligoni e le linee nelle posizioni precise (niente buffer di profondità né colori in prospettiva); il disegno «software» non ha PGXP. Spider-Man che si vede attraverso i muretti è come nel gioco originale (vedi `PROSSIMI_OBIETTIVI.md`): PGXP non lo cambia.

## Filmati

La scelta **Filmati** (pagina Opzioni) ha sei voci:

- **Originali**: come sulla PlayStation, ingranditi a blocchi;
- **Filtro in tempo reale**: senza preparazione; attenua i quadretti della compressione, interpola il colore tra i pixel e ingrandisce seguendo i contorni, con un po' di nitidezza e senza aloni (le scritte piccole restano come sono);
- **Migliorati**: fotogrammi ripuliti dai quadretti della compressione e ingranditi 4 volte, preparati una volta sola sul tuo PC e dal tuo disco con l'azione **Filmati** (dalla riga di comando `prepara-filmati`). Per una versione ci vogliono circa 1,1 GB e, su un PC veloce, poco più di un minuto. Il gioco li mostra al posto degli originali; audio, tempi e salto del filmato restano quelli del gioco. Provati sulle tre versioni principali: fino al primo livello più del 99,9% delle immagini dei filmati viene sostituito;
- **IA: Swin2SR**, **IA: Real-ESRGAN general** e **IA: Real-ESRGAN anime** (facoltativi, dalla 0.12): fotogrammi ingranditi 4 volte da un'intelligenza artificiale, vedi sotto.

I filtri e i filmati preparati funzionano solo con OpenGL (il motore grafico normale). Dove i fotogrammi preparati mancano, il gioco usa i Migliorati o il filtro in tempo reale. I filmati preparati restano nella cartella della tua installazione (`giochi\<versione>\filmati_hd\` e `giochi\<versione>\filmati_ia_<modello>\`): vengono dal tuo disco e non vanno distribuiti.

### Filmati IA (facoltativi)

L'azione **Filmati** apre la finestra dei filmati della versione scelta. Per i Migliorati e per ognuno dei tre modelli IA trovi una spiegazione, i **difetti possibili**, il tempo che ci vuole sul tuo PC, due **immagini di prova** fatte dal tuo disco (tenendo premuto il tasto sinistro del mouse sull'immagine si vede l'originale) e i pulsanti per preparare, fermare e riprendere. **Usa questi filmati nel gioco** mette la scelta nelle opzioni; si salva con **Gioca**.

| Modello | Com'è | Difetti possibili | Tempo sul PC di prova (GeForce RTX 4060 Laptop) |
|---|---|---|---|
| **Swin2SR** (fedele) | il più fedele: non inventa dettagli; più nitido dei Migliorati su volti, contorni e scritte grandi | superfici con trame fini (pelle, muri, facciate) un po' lisciate, effetto «dipinto»; scritte minuscole con qualche lettera storta; in qualche scena colori un po' più saturi | circa 5 ore e mezza; con una scheda video integrata, giorni |
| **Real-ESRGAN general-x4v3** (nitido) | molto nitido e veloce | inventa dettagli che non c'erano (piccole trame, pieghe, riflessi); le scritte piccole possono cambiare o diventare illeggibili; aloni chiari o scuri attorno ad alcuni contorni | circa 11 minuti |
| **Real-ESRGAN animevideov3** (cartone animato) | il più veloce e il più netto, pensato per i cartoni animati | appiattisce le sfumature: i volti possono sembrare di plastica; inventa dettagli e può cambiare le scritte piccole; contorni a volte troppo marcati | circa 9 minuti |

Per tutti e tre: le scritte piccole in movimento possono tremolare un poco. Per ridurlo il launcher stabilizza i fotogrammi nel tempo, come l'anti-aliasing temporale dei giochi: nel laboratorio del filmato iniziale il tremolio delle scritte cala di circa il 10-12%. Ogni modello occupa circa 1-2 GB per versione del gioco.

**Cosa si scarica.** I filmati IA hanno bisogno di programmi e modelli che non sono nel pacchetto: si scaricano **una volta sola e solo se lo chiedi** (pulsante **Scarica e fai le immagini di prova**), dopo una domanda che elenca dimensioni, siti e licenze. Sono onnxruntime-directml 1.24.4 e numpy 2.5.4 da pypi.org (circa 38 MB), Swin2SR da huggingface.co (53 MB) e i due Real-ESRGAN da github.com (7 MB): circa 100 MB in tutto, in `tools\ia\`. Ogni file si controlla con la sua impronta SHA-256; i due Real-ESRGAN si convertono sul tuo PC nel formato ONNX, senza altri programmi. Se il PC dove giochi non ha internet, puoi copiare la cartella `tools\ia\` da un altro PC dove hai già scaricato tutto con lo stesso launcher: il launcher controlla i file e non scarica niente. I filmati si preparano con la scheda video tramite DirectML (NVIDIA, AMD o Intel); senza una scheda adatta si usa il processore, molto più lento. Le versioni di onnxruntime per Windows hanno la telemetria di Microsoft accesa: il launcher la spegne.

**Preparazione.** Prima di cominciare il launcher dice quanto ci vorrà sul tuo PC (lo misura con le immagini di prova). Intanto puoi usare il launcher; **Ferma** interrompe alla fine del fotogramma in corso e **Riprendi** continua da dove eri. Anche chiudendo il launcher la preparazione si ferma e riprende la volta dopo. Mentre lavora il PC non va in sospensione; per Swin2SR conviene tenere il portatile collegato alla corrente.

## Comandi, controller e vibrazione

Il gioco usa da solo il primo controller collegato, anche se lo colleghi a gioco aperto; la tastiera funziona sempre. L'azione **Comandi** apre la finestra dei comandi del giocatore 1:

- quale controller usare (uno preciso, il primo collegato o solo la tastiera), analogico o digitale, zona morta delle levette;
- per ogni tasto della PlayStation il tasto del controller e quello della tastiera: clic, poi premi il tasto da usare entro 5 secondi (Esc annulla); un avviso dice se un tasto fa già un altro comando; **Ripristina i predefiniti** rimette tutto com'era;
- la prova dal vivo: i comandi si illuminano quando premi i tasti.

I controller Xbox e PlayStation (DualShock 4 e 5) sono riconosciuti con la stessa libreria del gioco (SDL3). **Vibrazione:** il gioco cerca il DualShock solo quando parte, quindi per avere la vibrazione collega il controller prima di premere **Gioca**. **Se il controller non risponde** (per esempio in Bluetooth), controlla che non ci sia un programma che lo nasconde ai giochi, come HidHide (di solito si installa insieme a DS4Windows): in HidHide togli il blocco del controller, oppure aggiungi l'eseguibile del gioco (`SpiderMan2EnterElectro.exe` nella cartella `build-release` dell'installazione) alle applicazioni permesse.

Con **Impostazioni di psxrecomp prima del gioco** (pagina Opzioni) si apre prima la finestra di psxrecomp, anche se l'avevi nascosta da lì.

## Salvataggi

La pagina **Salvataggi** mostra, per la versione scelta, i salvataggi di ogni memory card (titolo, versione, blocchi e icona) e i salvataggi rapidi (F7) con l'anteprima, lo slot e la data. **Copia di sicurezza delle memory card** le copia in `saves\copie\` della versione; **Ripristina una copia...** rimette una delle copie; **Usa un'altra memory card...** mette un file di un altro emulatore (`.mcd`, `.mcr`, `.gme`). In tutti e due i casi il launcher fa prima una copia della memory card di adesso. Dalla riga di comando: `salvataggi`.

**Copia le partite in un'altra versione...** copia le partite di Spider-Man 2 della versione scelta nella memory card di un'altra versione installata, con il nome che quella versione cerca: per esempio dalla USA all'Europa o al contrario. Le partite restano le stesse; il launcher corregge solo l'altezza dello schermo, che le versioni europee salvano in un altro modo (senza correzione l'immagine resterebbe più bassa), e prima fa una copia di sicurezza della memory card che cambia. Le due USA usano già le stesse partite, e così le due europee in inglese. Provato nel gioco con LOAD GAME dall'Europa alla USA Rev 1 e dalla USA Rev 1 all'Europa, alla Francia, alla Germania e al Giappone. Dalla riga di comando: `salvataggi --profilo <VERSIONE> --copia-in <ALTRA VERSIONE>`.

## Aggiornare da una versione precedente

Estrai la versione nuova in una cartella nuova, accanto a quella vecchia, e nella pagina Opzioni premi **Prendi da una versione precedente...** (dalla riga di comando `importa-cartella`): il launcher sposta dischi, installazioni e salvataggi dalla cartella vecchia, senza cancellare niente. Le installazioni restano giocabili; quelle fatte con un motore diverso hanno la nota «versione precedente: reinstalla per le novità». **Reinstalla** tiene opzioni e salvataggi. Passando dalla 0.11 alla 0.12 si reinstalla una volta; da lì in poi solo quando cambia il motore. I salvataggi rapidi (F7) fatti con il motore di prima non si caricano più: per continuare una partita usa le memory card.

## Per i PC lenti: installa con il PGO

Spunta **Installa con il PGO** prima di premere **Installa** (dalla riga di comando: `installa --pgo`). Il gioco viene compilato ottimizzando le parti del codice che si usano di più (PGO, ottimizzazione guidata dal profilo, di clang): sul PC di prova usa circa il 15% di CPU in meno (misurato il 4/11/2026 con le opzioni di default: avvio, filmati e titolo) e fa le stesse cose.

Dalla 0.12 il pacchetto contiene il profilo già pronto per le tre versioni principali (USA Rev 1, USA originale, Europa originale), anche per il gioco con i punti di aggancio di PGXP: niente partita di allenamento e una sola compilazione, quindi con il PGO l'installazione dura quasi come una normale. Per le altre versioni il launcher compila prima una versione del gioco che conta quante volte passa da ogni punto del codice, la fa giocare da sola per circa 3 minuti (con la finestra nascosta e senza audio) e poi compila il gioco vero; se qualcosa va storto durante la partita di allenamento, compila il gioco normale senza PGO.

**Installazione più veloce.** Dalla 0.12 il pacchetto porta anche il motore già compilato (in `cache\compilatore\`: solo motore, interfaccia e librerie, mai il codice del gioco) e il launcher tiene lì quello che compila, così le reinstallazioni rifanno solo quello che è cambiato. Se disco, motore e impostazioni della traduzione non sono cambiati, la reinstallazione salta anche la traduzione del codice del gioco (dalla riga di comando `installa --rigenera` la rifà comunque). Il motore del pacchetto è pronto per tutte e sette le versioni senza PGO e per le tre principali con il profilo PGO pronto, anche con i punti di aggancio di PGXP. Il pezzo più lungo è il collegamento finale del gioco, che la cache non accorcia: dalla 0.12 usa tanti thread quanti i core di compilazione (da solo ne usava uno per core fisico). Su un PC con 4 processori, come un portatile (misure del 7/11/2026 sul PC di prova limitato a 4 processori): l'Europa senza PGO si installa in circa 220 secondi, la USA Rev 1 con il PGO in circa 355 secondi.

## Prova del PC

Per sapere se il gioco va a piena velocità sul tuo computer (per esempio un portatile), dopo aver aggiunto almeno un disco fai doppio clic su **`PROVA-PC.cmd`** (dalla versione 0.11 del launcher). Se serve, la prova installa quella versione con il PGO e con un eseguibile di prova: sui PC lenti anche più di mezz'ora, una volta sola. Poi apre il gioco per circa 3 minuti: va da solo fino al primo livello premendo i tasti, con l'audio spento (non toccare la sua finestra), e misura la velocità e quanto lavora la CPU. Alla fine scrive il risultato in `work\prova_pc\rapporto.txt` e prepara uno zip da mandare a chi segue il progetto: contiene solo testi e misure, niente del gioco. Le opzioni che hai scelto restano com'erano.

## Senza finestra

Gli stessi comandi funzionano dalla riga di comando (vanno bene anche i nomi inglesi: `identify`, `import`, `install`, `play`, `options`, `status`, `--profile` e così via; `--lingua it|en` sceglie la lingua dei messaggi):

```
SM2-Launcher.cmd riconosci
SM2-Launcher.cmd importa "D:\dump\Spider-Man 2 - Enter - Electro (USA).cue"
SM2-Launcher.cmd installa --profilo SLUS-01378-Rev1
SM2-Launcher.cmd installa --profilo SLUS-01378-Rev1 --pgo
SM2-Launcher.cmd installa --profilo SLUS-01378-Rev1 --pgo --pgxp
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --risoluzione 1080p --pgxp si
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --pgxp-proiezione si --pgxp-cpu no
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --attese no
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --filmati migliorati --volume 80
SM2-Launcher.cmd prepara-filmati --profilo SLUS-01378-Rev1
SM2-Launcher.cmd ia-scarica --si
SM2-Launcher.cmd anteprime-ia --profilo SLUS-01378-Rev1
SM2-Launcher.cmd prepara-filmati-ia --profilo SLUS-01378-Rev1 --modello anime
SM2-Launcher.cmd opzioni --profilo SLUS-01378-Rev1 --filmati ia-anime
SM2-Launcher.cmd salvataggi --profilo SLUS-01378-Rev1 --copia
SM2-Launcher.cmd salvataggi --profilo SLES-03623 --copia-in SLUS-01378-Rev1
SM2-Launcher.cmd importa-cartella "C:\Giochi\SM2-Recomp-0.11"
SM2-Launcher.cmd avvia --profilo SLUS-01378-Rev1
SM2-Launcher.cmd stato
```

Dalla 0.12 `SM2-Launcher.cmd` restituisce il codice di uscita del launcher: 0 se il comando è andato bene, un altro numero se no (per esempio 2 per `ia-scarica` senza `--si`), così si può usare anche negli script.

## Cartelle

| Cartella | Contenuto |
|---|---|
| `input\` | i tuoi dump, una cartella per versione |
| `giochi\` | le versioni installate (codice generato ed eseguibili, salvataggi in `saves\`, filmati migliorati in `filmati_hd\`, filmati IA in `filmati_ia_<modello>\` e le loro immagini di prova in `anteprime_ia\`: restano sul tuo PC) |
| `tools\ia\` | solo se scegli i filmati IA: i programmi e i modelli scaricati (onnxruntime-directml, numpy, Swin2SR, Real-ESRGAN), con le loro licenze. Si può cancellare |
| `cache\` | la cache del compilatore: il motore già compilato del pacchetto e quello che compila il launcher. Serve solo a installare più in fretta; si può cancellare |
| `tools\` | il launcher e i suoi strumenti; in `tools\toolchain\` gli strumenti di compilazione e, in `tools\toolchain\sorgenti\`, i sorgenti dei loro programmi con licenza GPL o LGPL; in `tools\overlay\` il toolchain degli overlay di psxrecomp (Python 3.13.1 incorporabile e TinyCC 0.9.27, con il sorgente di TinyCC), che il launcher copia in ogni installazione |
| `aot\` | solo fatti sul gioco (hash, dimensioni, indirizzi) e, in `aot\pgo\`, i profili PGO pronti (solo contatori sulle funzioni), nessun dato del gioco |
| `psxrecomp\`, `recomp-ui\` | psxrecomp e la sua interfaccia, con le loro licenze |

## Licenze

Il launcher di EnterElectro-Recomp ha la licenza MIT (`LICENSE`). Il pacchetto contiene anche psxrecomp, recomp-ui e gli strumenti di compilazione, ognuno con la sua licenza: per quella di psxrecomp il pacchetto si può usare e distribuire **solo gratis e per scopi non commerciali**; per i programmi degli strumenti con licenza GPL o LGPL i sorgenti sono in `tools\toolchain\sorgenti\`. I programmi e i modelli dei filmati IA non sono nel pacchetto: si scaricano solo se il giocatore lo chiede, ognuno con la sua licenza (MIT, BSD-3-Clause, Apache 2.0). I dettagli sono in `LICENZE.md` (in inglese: `LICENSES.md`); nel pacchetto, `PACCHETTO.txt` elenca tutti i file con le loro impronte SHA-256.

Stato: giocabile, buon gameplay. Quello che il progetto ha documentato finora:

- **Versioni del disco riconosciute:** le 7 della tabella «Versioni riconosciute».
- **Prove automatiche:** in tutte e 7 le versioni il gioco arriva a giocare dal codice ricompilato e partono tutti i 44 livelli, con i moduli dei livelli compilati in anticipo; le novità della 0.12 sono provate automaticamente sul PC di prova.
- **Prova manuale:** con la 0.11, una partita completa dall'inizio alla fine con la versione USA Rev 1, su un portatile di prova (Core i7-6500U, GeForce 920MX). Per le altre versioni non è documentata una partita completa. Con la 0.12, una partita completa dall'inizio alla fine con la USA Rev 1, registrata (circa due ore e mezza di gioco in 10 sessioni), su un PC con Core i9 e GeForce RTX 4060, con un DualShock 4 originale: i comandi funzionano con il cavo USB e in Bluetooth. La vibrazione della 0.12 aspetta ancora una prova specifica.
- **Problemi conosciuti:** sono elencati in `PROSSIMI_OBIETTIVI.md` («Difetti conosciuti della 0.12»).

I prossimi passi dello sviluppo sono in `PROSSIMI_OBIETTIVI.md`.
