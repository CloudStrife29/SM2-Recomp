# SM2-Recomp — prossimi obiettivi

English: see ROADMAP.md.

Questo file accompagna ogni versione pubblicata del launcher e dice cosa viene dopo. È un piano, non una promessa: l'ordine può cambiare con quello che emerge dalle prove. Ogni versione esce solo dopo lo stesso giro completo di prove: tutte e 7 le versioni del gioco, tutti i 44 livelli, prove lunghe e prova del pacchetto senza internet.

Versione attuale: 0.11 (novembre 2026).

## Dopo la 0.11: versione 0.12

1. **Filmati più definiti.** I filmati del gioco sono a 320×240 e molto compressi. Nel launcher ci sarà la scelta «Filmati» con tre voci:
   - **Originali**, come adesso;
   - **Filtro in tempo reale**: mentre il filmato va, toglie i quadretti della compressione e lo ingrandisce meglio, senza preparazione;
   - **Migliorati**: un pulsante prepara una volta sola, sul tuo PC e dal tuo disco, una versione ingrandita di tutti i filmati, che il gioco usa al posto degli originali. Come il resto del gioco per PC, i filmati migliorati restano sul tuo computer e non vengono mai distribuiti.
2. **Launcher più curato.** Un'immagine di sfondo per ogni versione del gioco, come in OpenGOAL, presa dal tuo disco al momento dell'installazione (un fotogramma dei filmati migliorati o una scena del gioco a 4K), e una finestra più pulita, divisa in schede.
3. **Controller nella prima finestra.** Scegliere il controller, provarne i tasti e assegnare i comandi del gioco premendo il tasto da usare; lo stesso per la tastiera.
4. **Difetti conosciuti da correggere:**
   - widescreen: in qualche punto un oggetto molto vicino alla telecamera appare tagliato al bordo dell'immagine 4:3 originale;
   - l'opzione «disegno in un thread separato» non parte nell'eseguibile con cui si gioca;
   - il registratore delle partite (usato per le prove) si ferma dove il gioco compila codice nuovo durante la partita;
   - due comportamenti visti nelle prove automatiche, da capire meglio: una differenza alla prima partenza di un eseguibile nuovo e una chiusura lenta dell'eseguibile di prova giapponese.

## Versione 0.13: funzioni da gioco PC moderno

- **Controller:** vibrazione, controller Xbox e PlayStation riconosciuti da soli.
- **Salvataggi:** gestione delle memory card dal launcher (copia di sicurezza, passaggio da una versione all'altra) e salvataggi rapidi con anteprima.
- **Grafica e audio:** Vulkan come scelta in più (sul portatile di prova va come OpenGL), volume regolabile.

## Sempre, in parallelo

- Proporre agli autori di psxrecomp le correzioni e le ottimizzazioni fatte per SM2-Recomp, così possono entrare in psxrecomp e il pacchetto ha meno modifiche proprie.
- Prove automatiche a ogni versione, comprese partite vere registrate e poi rigiocate dal programma.

## Più avanti

- Sostituire a poco a poco con codice scritto a mano le parti più importanti del gioco (telecamera, disegno, comandi). È quello che permette miglioramenti veri, per esempio un widescreen senza tagli e le mod. È il lavoro più lungo.
