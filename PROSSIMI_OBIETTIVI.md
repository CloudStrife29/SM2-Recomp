# SM2-Recomp — prossimi obiettivi

English: see ROADMAP.md.

Questo file accompagna ogni versione pubblicata del launcher e dice cosa viene dopo. È un piano, non una promessa: l'ordine può cambiare con quello che emerge dalle prove. Ogni versione esce solo dopo un giro completo di prove: sulle versioni principali del gioco tutti i 44 livelli, prove lunghe e prova del pacchetto senza internet; sulle altre installazione, partenza dei livelli e un pezzo della storia. La 0.11 è stata provata per intero in tutte e 7 le versioni.

Versione attuale: 0.11 (novembre 2026). Piano aggiornato al 5 novembre 2026: la 0.12 sarà l'ultima versione prima della riscrittura del gioco (decompilazione) e raccoglie anche tutto quello che prima era previsto per dopo.

## Dopo la 0.11: versione 0.12

1. **Filmati più definiti.** I filmati del gioco sono a 320×240 e molto compressi. Nel launcher ci sarà la scelta «Filmati» con queste voci:
   - **Originali**, come adesso;
   - **Filtro in tempo reale**: mentre il filmato va, toglie i quadretti della compressione e lo ingrandisce meglio, senza preparazione;
   - **Migliorati**: un pulsante prepara una volta sola, sul tuo PC e dal tuo disco, una versione ingrandita di tutti i filmati, che il gioco usa al posto degli originali. Come il resto del gioco per PC, i filmati migliorati restano sul tuo computer e non vengono mai distribuiti.
   - **Filmati IA, a scelta:** tre ingranditori con l'intelligenza artificiale, Swin2SR (fedele: non inventa dettagli), Real-ESRGAN general-x4v3 e Real-ESRGAN animevideov3 (più nitidi, ma inventano qualche dettaglio). Il launcher mostra immagini di prova fatte con ogni modello dal tuo disco e scrive i difetti possibili di ciascuno; i programmi e i modelli si scaricano solo se scegli questa opzione.
2. **Launcher più curato.** Un'immagine di sfondo per ogni versione del gioco, come in OpenGOAL, presa dal tuo disco al momento dell'installazione (un fotogramma dei filmati migliorati o una scena del gioco a 4K), e una finestra più pulita, divisa in schede.
3. **Controller nella prima finestra.** Scegliere il controller, provarne i tasti e assegnare i comandi del gioco premendo il tasto da usare; lo stesso per la tastiera. Controller Xbox e PlayStation riconosciuti da soli, vibrazione.
4. **Salvataggi.** Memory card gestite dal launcher (copia di sicurezza, ripristino, copia su un altro PC) e salvataggi rapidi con anteprima.
5. **Volume** regolabile dal launcher.
6. **Installazione più veloce**, soprattutto sui PC con pochi processori: un profilo PGO già pronto nel pacchetto (niente partita di prova e una sola compilazione), ottimizzazione piena solo per il codice che il gioco usa spesso e, se possibile, il motore già compilato. Il gioco deve restare veloce come adesso.
7. **Aggiornamenti senza reinstallare.** Il launcher nuovo tiene i giochi già installati e chiede di reinstallarli solo quando cambia il motore. Passando dalla 0.11 alla 0.12 si reinstalla una volta.
8. **Meno scatti e niente tearing:** immagine più regolare sugli schermi a 60, 120, 144 e 240 Hz, anche quando il ritmo del gioco (50 Hz in Europa, 60 Hz in USA e Giappone) non coincide con quello dello schermo.
9. **Difetti conosciuti da correggere:**
   - sui PC poco potenti, piccoli cali di velocità in pochi punti pesanti (menu Create-a-Spidey a 1080p, torrette di «Rooftops By Night», battaglia finale con Sandman);
   - due difetti grafici segnalati, da verificare sulla PlayStation originale: il cielo in un punto del primo livello e una luce che si vede attraverso una parete in «In Darkest Night»;
   - widescreen: in qualche punto un oggetto molto vicino alla telecamera appare tagliato al bordo dell'immagine 4:3 originale;
   - l'opzione «disegno in un thread separato» non parte nell'eseguibile con cui si gioca;
   - il registratore delle partite (usato per le prove) si ferma dove il gioco compila codice nuovo durante la partita;
   - due comportamenti visti nelle prove automatiche, da capire meglio: una differenza alla prima partenza di un eseguibile nuovo e una chiusura lenta dell'eseguibile di prova giapponese.

Le novità arrivano prima sulle versioni principali: USA Rev 1, USA originale e una europea. Le altre (l'altra europea, Francia, Germania, Giappone) restano installabili e giocabili e ricevono le novità quando il lavoro in più è piccolo; quelle che non dipendono dalla versione, come launcher, controller e memory card, valgono subito per tutte.

## Sempre, in parallelo

- Proporre agli autori di psxrecomp le correzioni e le ottimizzazioni fatte per SM2-Recomp, così possono entrare in psxrecomp e il pacchetto ha meno modifiche proprie.
- Prove automatiche a ogni versione, comprese partite vere registrate e poi rigiocate dal programma.

## Più avanti: il gioco riscritto a mano

- Sostituire a poco a poco con codice scritto a mano le parti più importanti del gioco, partendo dalla versione USA Rev 1: prima il disegno (widescreen senza tagli, distanza visiva vera), poi telecamera e comandi, poi i menù, con le opzioni per PC dentro il gioco. Il gioco riscritto leggerà dati, testi e voci dal disco di chi gioca, di qualunque versione. Ogni parte riscritta dovrà comportarsi come l'originale, e lo dimostreranno le partite registrate. È il lavoro più lungo.
- Vulkan come scelta in più si valuterà quando il disegno sarà riscritto: oggi sul portatile di prova va come OpenGL.
