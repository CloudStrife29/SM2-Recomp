#!/usr/bin/env python3
"""SM2-Recomp - finestra del launcher (dal 27/10/2026; spiegazioni al passaggio del mouse e opzioni dello schermo dal 31/10).

Una finestra sopra i comandi di tools/sm2_launcher.py: elenco delle 7 versioni con disco e installazione,
pulsanti Aggiungi un disco / Installa / Gioca / Apri la cartella, opzioni (risoluzione interna, PGXP,
finestra delle impostazioni di psxrecomp) e il registro di quello che succede. I comandi girano in un
processo a parte (lo stesso sm2_launcher.py), quindi la finestra resta libera e fa esattamente quello che
farebbe la riga di comando.

Usa tkinter, che e' gia' nel Python del toolchain portatile. Si apre da SM2-Launcher.cmd senza argomenti.

Dalla v0.8: quando si sceglie una versione, le opzioni della finestra mostrano quelle gia' salvate per
quell'installazione (mods\\state.toml), cosi' "Gioca" non le cambia se non le tocchi.

Dal 31/10/2026: ogni voce, pulsante e colonna ha una spiegazione che compare tenendoci sopra il mouse (classe
Suggerimento, testi in SUGG); nuovo riquadro "Schermo e prestazioni" (sincronia verticale, disegno in un thread separato,
finestra o schermo intero, larghezza della finestra, input a bassa latenza, movimento fluido), scritto in settings.toml
accanto all'eseguibile dal comando "opzioni"; pulsante con le impostazioni consigliate per i PC lenti; tasti nel gioco.

Prova automatica (per i test senza mouse): --autotest CARTELLA apre la finestra, aggiorna l'elenco,
salva un'immagine della finestra, lancia "stato", salva una seconda immagine e si chiude; registro e
immagini in CARTELLA. Con --cambia-lingua, prima di "stato" cambia anche la lingua come la scelta "Lingua / Language"
(rifa' la finestra e scrive lingua.txt) e salva un'immagine della finestra nell'altra lingua (gui_1_lingua.png).

Dal 4/11/2026: finestra in italiano o in inglese (tools/sm2_lingua.py), con la scelta "Lingua / Language" in alto a
destra; la scelta si ricorda in lingua.txt e passa ai comandi lanciati dalla finestra (variabile SM2_LINGUA). I valori
passati ai comandi restano quelli italiani, che sm2_launcher.py accetta sempre.

English: the SM2-Recomp launcher window (tkinter). It drives tools/sm2_launcher.py in a separate process: list of the 7
game versions with disc and installation state, buttons Add a disc / Install / Play / Open folder / Refresh, the player's
options and a log. Since 4 Nov 2026 the window is in Italian or English ("Lingua / Language" choice, saved in
lingua.txt); the values passed to the commands stay the Italian ones, which sm2_launcher.py always accepts.
--autotest FOLDER opens the window, refreshes the list, saves screenshots, runs "status" and closes; with
--cambia-lingua it also switches the language like the "Lingua / Language" choice (writing lingua.txt) and saves a
screenshot of the window in the other language.
"""
from __future__ import annotations

import json
import os
import queue
import struct
import subprocess
import sys
import threading
import time
import zlib
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sm2_launcher as L  # noqa: E402
from sm2_lingua import T, imposta as imposta_lingua, lingua, lingua_gioco, nome_versione  # noqa: E402
from sm2_lingua import salva as salva_lingua  # noqa: E402

TITOLO = f'Spider-Man 2: Enter Electro - SM2-Recomp {L.VERSIONE}'
LINGUE = [('Italiano', 'it'), ('English', 'en')]
# nomi inglesi dei comandi di sm2_launcher.py (solo per i messaggi; la finestra lancia sempre i nomi italiani)
NOMI_COMANDI_EN = {'riconosci': 'identify', 'importa': 'import', 'installa': 'install', 'avvia': 'play',
                   'opzioni': 'options', 'stato': 'status', 'prepara-registrazione': 'prepare-recording'}
# valori interni (italiani) delle opzioni, come si leggono nei messaggi in inglese
VALORI_EN = {'si': 'yes', 'no': 'no', 'gioco': 'game', 'accesa': 'on', 'spenta': 'off', 'adattiva': 'adaptive',
             'finestra': 'window', 'senza-bordi': 'borderless', 'esclusivo': 'exclusive'}

RIS: list = []
FILTRI: list = []
WIDE: list = []
SINC: list = []
SCHERMI: list = []
LARGHEZZE: list = []
TASTI_NEL_GIOCO = ''
SUGG: dict = {}
VALIDI: dict = {}


def valore_letto(v) -> str:
    """Un valore interno delle opzioni (si, gioco, accesa...) come si scrive nella lingua scelta."""
    return VALORI_EN.get(str(v), str(v)) if lingua() == 'en' else str(v)


def nome_comando(cmd: str) -> str:
    """Il nome di un comando di sm2_launcher.py nella lingua scelta (quelli italiani restano validi)."""
    return NOMI_COMANDI_EN.get(cmd, cmd) if lingua() == 'en' else cmd


def testi() -> None:
    """Elenchi delle scelte e spiegazioni nella lingua scelta. Si rifanno quando la lingua cambia: le tabelle sono
    (testo mostrato, valore per il comando "opzioni"), e il valore resta sempre lo stesso."""
    global RIS, FILTRI, WIDE, SINC, SCHERMI, LARGHEZZE, TASTI_NEL_GIOCO, SUGG, VALIDI
    RIS = [(T('Come il gioco', 'As in the game'), 'gioco'), (T('Nativa', 'Native'), 'native'), ('720p', '720p'),
           ('1080p', '1080p'), ('1440p', '1440p'), ('4K', '4k')]
    FILTRI = [(T('Come il gioco', 'As in the game'), 'gioco'), (T('Nearest (originale)', 'Nearest (original)'), 'nearest'),
              ('Bilinear', 'bilinear'), ('xBR', 'xbr')]
    WIDE = [('No (4:3)', 'no'), (T('16:9 (sperimentale)', '16:9 (experimental)'), '16:9'),
            (T('16:10 (sperimentale)', '16:10 (experimental)'), '16:10'),
            (T('21:9 (sperimentale)', '21:9 (experimental)'), '21:9')]
    SINC = [(T('Accesa', 'On'), 'accesa'), (T('Adattiva', 'Adaptive'), 'adattiva'), (T('Spenta', 'Off'), 'spenta'),
            ('VRR (G-Sync, FreeSync)', 'vrr')]
    SCHERMI = [(T('Finestra', 'Window'), 'finestra'),
               (T('Schermo intero senza bordi', 'Borderless fullscreen'), 'senza-bordi'),
               (T('Schermo intero esclusivo', 'Exclusive fullscreen'), 'esclusivo')]
    LARGHEZZE = [(T('Automatica', 'Automatic'), 0), ('960', 960), ('1280', 1280), ('1600', 1600), ('1920', 1920),
                 ('2560', 2560)]
    TASTI_NEL_GIOCO = T('Tasti nel gioco: F10 menu e impostazioni \u00b7 F7 salvataggi di stato \u00b7 Tab (tenuto) avanti '
                        'veloce \u00b7 F mostra le prestazioni \u00b7 Alt+Invio schermo intero \u00b7 + e \u2212 del '
                        'tastierino: volume',
                        'Keys in the game: F10 menu and settings \u00b7 F7 save states \u00b7 Tab (held) fast forward '
                        '\u00b7 F shows performance \u00b7 Alt+Enter fullscreen \u00b7 keypad + and \u2212: volume')
    # Spiegazioni che compaiono tenendo il mouse su una voce (classe Suggerimento). Scritte per chi gioca: cosa fa,
    # quando conviene, quanto costa.
    SUGG = {
        'elenco': T("Le 7 versioni del gioco che il launcher sa preparare. Clicca su una riga per sceglierla: i pulsanti "
                    "e le opzioni qui sotto valgono per quella.\n\nDisco: \u00absi\u00bb se il dump di quella versione \u00e8 "
                    "nella cartella input del progetto (\u00abRedump\u00bb se coincide con un dump verificato).\n"
                    "Installazione: se \u00e8 pronta da giocare e con quali opzioni \u00e8 stata compilata.",
                    "The 7 versions of the game that the launcher can prepare. Click a row to choose it: the buttons "
                    "and the options below apply to that version.\n\nDisc: \u201cyes\u201d if the dump of that version is "
                    "in the project's input folder (\u201cRedump\u201d if it matches a verified dump).\nInstallation: "
                    "whether it is ready to play and with which options it was built."),
        'disco': T("Scegli il dump del tuo disco (.cue, .ccd, .bin, .img o .iso). Il launcher riconosce la versione dal "
                   "contenuto, non dal nome del file, e sposta i file nella cartella input del progetto. Il disco resta "
                   "sul tuo PC: niente viene caricato su internet.",
                   "Choose the dump of your disc (.cue, .ccd, .bin, .img or .iso). The launcher recognises the version "
                   "from its content, not from the file name, and moves the files into the project's input folder. The "
                   "disc stays on your PC: nothing is uploaded to the internet."),
        'installa': T("Prepara la versione scelta dal tuo disco: genera il codice del gioco, lo compila per questo PC e "
                      "prepara le mod. Ci vogliono alcuni minuti (qualcuno in pi\u00f9 con il PGO). Rifallo dopo un "
                      "aggiornamento del launcher per avere le correzioni nuove: le opzioni scelte restano.",
                      "Prepares the chosen version from your disc: it generates the game code, compiles it for this PC "
                      "and prepares the mods. It takes a few minutes (a few more with PGO). Do it again after a launcher "
                      "update to get the new fixes: the options you chose are kept."),
        'gioca': T("Salva le opzioni scelte in questa finestra e avvia il gioco. Le opzioni restano anche per le volte "
                   "successive e si possono cambiare pure dal menu nel gioco (F10).",
                   "Saves the options chosen in this window and starts the game. The options are kept for the next "
                   "times as well and can also be changed from the in-game menu (F10)."),
        'cartella': T("Apre la cartella dell'installazione (giochi\\<versione>): eseguibile, impostazioni, registri.",
                      "Opens the installation folder (giochi\\<version>): executable, settings, logs."),
        'aggiorna': T("Ricontrolla dischi e installazioni, per esempio dopo aver copiato a mano un dump nella cartella "
                      "input.",
                      "Checks the discs and installations again, for example after copying a dump into the input folder "
                      "by hand."),
        'ris': T("Risoluzione a cui la scheda video disegna il gioco. \u00abCome il gioco\u00bb \u00e8 quella originale "
                 "(320\u00d7240), la pi\u00f9 leggera. 720p, 1080p, 1440p e 4K danno un'immagine pi\u00f9 nitida: "
                 "costano lavoro alla scheda video, non al processore. Sui PC deboli lascia \u00abCome il gioco\u00bb o "
                 "720p.",
                 "Resolution at which the graphics card draws the game. \u201cAs in the game\u201d is the original one "
                 "(320\u00d7240), the lightest. 720p, 1080p, 1440p and 4K give a sharper picture: they cost work for "
                 "the graphics card, not for the processor. On weak PCs keep \u201cAs in the game\u201d or 720p."),
        'filtro': T("Come vengono ingrandite le texture. Nearest: pixel netti come sulla PS1. Bilinear: pi\u00f9 morbide. "
                    "xBR: ammorbidisce mantenendo i contorni, un po' pi\u00f9 pesante per la scheda video. \u00abCome il "
                    "gioco\u00bb usa la scelta predefinita.",
                    "How the textures are enlarged. Nearest: sharp pixels as on the PS1. Bilinear: smoother. xBR: "
                    "smooths while keeping the edges, a bit heavier for the graphics card. \u201cAs in the game\u201d "
                    "uses the default choice."),
        'wide': T("Allarga l'immagine a 16:9, 16:10 o 21:9 mostrando pi\u00f9 scena ai lati invece di stirarla. Filmati, "
                  "menu e giornale restano in 4:3. Sperimentale: in pochi punti un oggetto ai lati pu\u00f2 comparire in "
                  "ritardo.",
                  "Widens the picture to 16:9, 16:10 or 21:9, showing more of the scene at the sides instead of "
                  "stretching it. Movies, menus and the journal stay in 4:3. Experimental: in a few places an object at "
                  "the sides can appear late."),
        'pgxp': T("Corregge il tremolio dei poligoni e la deformazione delle texture tipici della PS1. Ha effetto "
                  "completo solo se l'installazione \u00e8 stata fatta con PGXP; si nota soprattutto da 720p in su. "
                  "Costa circa il 6% di processore: sui PC deboli lascialo spento.",
                  "Fixes the polygon wobble and the texture warping typical of the PS1. It has its full effect only if "
                  "the installation was made with PGXP; it shows mostly from 720p up. It costs about 6% of processor: "
                  "on weak PCs leave it off."),
        'distanza': T("Allontana la nebbia e mostra la citt\u00e0 pi\u00f9 lontano, con un'area pi\u00f9 grande per i "
                      "comandi alla scheda video cos\u00ec che niente venga scartato. Costa un po' di processore e di "
                      "scheda video. Sperimentale.",
                      "Pushes the fog further away and shows the city further out, with a larger area for the commands "
                      "to the graphics card so that nothing is dropped. It costs some processor and graphics card work. "
                      "Experimental."),
        'con_launcher': T("Prima del gioco apre la finestra delle impostazioni di psxrecomp: controller, tasti, audio "
                          "e altre opzioni. Utile la prima volta, per configurare un controller.",
                          "Before the game, opens the psxrecomp settings window: controller, keys, audio and other "
                          "options. Useful the first time, to set up a controller."),
        'attese': T("Quando il gioco aspetta il frame successivo, il processore si ferma invece di girare a vuoto. Il "
                    "gioco resta identico (verificato frame per frame nelle 7 versioni). Consigliato acceso, "
                    "soprattutto sui portatili: meno calore e meno batteria.",
                    "When the game waits for the next frame, the processor stops instead of spinning idle. The game "
                    "stays identical (checked frame by frame in the 7 versions). Recommended on, especially on laptops: "
                    "less heat and less battery use."),
        'pgo': T("Vale per Installa. Compila il gioco in due passaggi: una partita di prova automatica di circa 3 "
                 "minuti, senza finestra e senza audio, misura quali parti del codice si usano di pi\u00f9; poi la "
                 "versione finale viene ottimizzata su quelle. Circa 15% di processore in meno; l'installazione dura "
                 "qualche minuto in pi\u00f9.",
                 "Applies to Install. The game is compiled in two passes: an automatic test game of about 3 minutes, "
                 "with no window and no audio, measures which parts of the code are used most; then the final version "
                 "is optimised for those. About 15% less processor; the installation takes a few minutes longer."),
        'sinc': T("Sincronia verticale. Accesa: immagine senza strappi, ma su uno schermo a 60 Hz un frame in ritardo "
                  "aspetta il refresh successivo e il gioco pu\u00f2 scendere fino a met\u00e0 velocit\u00e0. Adattiva: "
                  "sincronizza solo quando il gioco \u00e8 in tempo, altrimenti mostra subito (consigliata sui PC lenti). "
                  "Spenta: nessuna attesa, possibili strappi. VRR: per schermi G-Sync o FreeSync.",
                  "Vertical sync. On: a picture without tearing, but on a 60 Hz screen a late frame waits for the next "
                  "refresh and the game can drop to half speed. Adaptive: syncs only when the game is on time, "
                  "otherwise shows the frame at once (recommended on slow PCs). Off: no waiting, possible tearing. "
                  "VRR: for G-Sync or FreeSync screens."),
        'thread': T("Comanda la scheda video da un secondo thread del processore, in parallelo all'emulazione: un "
                    "frame costa il pi\u00f9 lento dei due lavori invece della loro somma. Pu\u00f2 aiutare sui PC con "
                    "almeno 2 core; aggiunge al massimo un frame di ritardo all'immagine. Si applica al prossimo avvio.",
                    "Drives the graphics card from a second processor thread, in parallel with the emulation: a frame "
                    "costs the slower of the two jobs instead of their sum. It can help on PCs with at least 2 cores; "
                    "it adds at most one frame of delay to the picture. Applied at the next start."),
        'schermo': T("Finestra; schermo intero senza bordi (consigliato: si passa subito ad altre finestre); schermo "
                     "intero esclusivo (a volte pi\u00f9 fluido sui PC deboli). Nel gioco Alt+Invio passa da finestra a "
                     "schermo intero.",
                     "Window; borderless fullscreen (recommended: you can switch to other windows at once); exclusive "
                     "fullscreen (sometimes smoother on weak PCs). In the game Alt+Enter switches between window and "
                     "fullscreen."),
        'larghezza': T("Larghezza della finestra in pixel quando il gioco non \u00e8 a schermo intero; l'altezza segue "
                       "le proporzioni. Automatica lascia decidere a psxrecomp.",
                       "Width of the window in pixels when the game is not fullscreen; the height follows the "
                       "proportions. Automatic lets psxrecomp decide."),
        'latenza': T("Legge controller e tastiera il pi\u00f9 tardi possibile prima di ogni frame, cos\u00ec i comandi "
                     "rispondono prima. Lascialo acceso.",
                     "Reads the controller and the keyboard as late as possible before each frame, so the controls "
                     "respond sooner. Leave it on."),
        'fluido': T("Per schermi a 120 Hz o pi\u00f9: crea immagini intermedie tra un frame e l'altro (la logica del "
                    "gioco resta a 60 Hz). Accende anche il disegno in un thread separato e richiede processore in "
                    "pi\u00f9: non usarlo sui PC deboli. Sperimentale: in alcune scene pu\u00f2 tremolare.",
                    "For screens at 120 Hz or more: creates in-between pictures from one frame to the next (the game "
                    "logic stays at 60 Hz). It also turns on the render thread and needs more processor: do not use it "
                    "on weak PCs. Experimental: it can flicker in some scenes."),
        'consigliate': T("Imposta qui sotto le scelte pi\u00f9 leggere per un PC lento: risoluzione e filtro come il "
                         "gioco, PGXP e distanza visiva spenti, salto delle attese acceso, sincronia adattiva, disegno "
                         "in un thread separato, PGO per la prossima installazione. Non salva niente finch\u00e9 non "
                         "premi Gioca o Installa.",
                         "Sets the lightest choices for a slow PC below: resolution and filter as in the game, PGXP and "
                         "draw distance off, idle skip on, adaptive vertical sync, render thread on, PGO for the next "
                         "installation. Nothing is saved until you press Play or Install."),
        'tasti': T("Tasti del gioco per PC (si cambiano dal menu F10). F7 apre i 12 spazi dei salvataggi di stato: si "
                   "salva e si riprende in qualsiasi punto. Tab tenuto premuto fa andare il gioco pi\u00f9 veloce, per "
                   "esempio nei caricamenti. F mostra frame al secondo e tempi.",
                   "Keys of the PC game (they can be changed from the F10 menu). F7 opens the 12 save state slots: you "
                   "can save and resume at any point. Holding Tab makes the game run faster, for example while loading. "
                   "F shows frames per second and timings."),
        'registro': T("Quello che il launcher sta facendo, con i messaggi dei comandi. Le stesse righe restano nei file "
                      "launcher_log.txt.",
                      "What the launcher is doing, with the messages of the commands. The same lines are kept in the "
                      "launcher_log.txt files."),
        # la scelta della lingua si spiega in tutte e due le lingue: chi non capisce quella di adesso la trova lo stesso
        'lingua': "Lingua della finestra e dei messaggi del launcher; la scelta resta per le prossime volte (file "
                  "lingua.txt).\nLanguage of the window and of the launcher messages; the choice is kept for the next "
                  "times (lingua.txt file).",
    }
    # valori che il comando "opzioni" accetta (sm2_launcher.py), anche quelli che non sono negli elenchi
    VALIDI = {id(RIS): ('gioco', 'native', '720p', '1080p', '1440p', '4k', '5k', '8k', 'display', 'auto'),
              id(FILTRI): ('gioco', 'nearest', 'bilinear', 'xbr'), id(WIDE): ('no', '16:9', '16:10', '21:9'),
              id(SINC): ('accesa', 'adattiva', 'spenta', 'vrr'), id(SCHERMI): ('finestra', 'senza-bordi', 'esclusivo')}


def etichetta_di(tabella: list, valore, altrimenti=None):
    """Il testo mostrato per un valore di una tabella di scelte (None se il valore non c'e')."""
    return next((e for e, v in tabella if v == valore), altrimenti)


testi()


class Suggerimento:
    """Spiegazione che compare dopo mezzo secondo con il mouse fermo su un elemento della finestra."""

    tutti: list = []          # per la prova automatica della finestra

    def __init__(self, widget, testo: str, ritardo: int = 500):
        self.w, self.testo, self.ritardo = widget, testo, ritardo
        self._id, self._tip = None, None
        Suggerimento.tutti.append(self)
        widget.bind('<Enter>', self._entra, add='+')
        widget.bind('<Leave>', self._nascondi, add='+')
        widget.bind('<ButtonPress>', self._nascondi, add='+')

    def _entra(self, _evento=None):
        self._annulla()
        self._id = self.w.after(self.ritardo, self._mostra)

    def _annulla(self):
        if self._id is not None:
            try:
                self.w.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None

    def _nascondi(self, _evento=None):
        self._annulla()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

    def _mostra(self):
        self._id = None
        try:
            if self._tip is not None or not self.w.winfo_viewable():
                return
        except tk.TclError:       # elemento gia' distrutto (finestra rifatta per cambiare lingua)
            return
        scala = max(1.0, self.w.winfo_fpixels('1i') / 96.0)
        tip = tk.Toplevel(self.w)
        tip.wm_overrideredirect(True)
        try:
            tip.attributes('-topmost', True)
        except tk.TclError:
            pass
        tk.Label(tip, text=self.testo, justify='left', background='#fffbe6', foreground='#222222', relief='solid',
                 borderwidth=1, wraplength=int(430 * scala), padx=9, pady=6, font=('Segoe UI', 9)).pack()
        tip.update_idletasks()
        x = self.w.winfo_rootx() + 12
        y = self.w.winfo_rooty() + self.w.winfo_height() + 4
        larg, alt = tip.winfo_width(), tip.winfo_height()
        x = max(0, min(x, tip.winfo_screenwidth() - larg - 8))
        if y + alt > tip.winfo_screenheight() - 40:
            y = max(0, self.w.winfo_rooty() - alt - 4)
        tip.wm_geometry(f'+{x}+{y}')
        self._tip = tip


def righe_versioni() -> list:
    """Per ogni versione del catalogo: nome, lingua, stato del disco e dell'installazione (testi nella lingua scelta;
    la logica della finestra usa i campi ha_disco e pronta, non i testi)."""
    cat = L.catalogo()
    cache = L.CacheHash(L.GIOCHI / 'cache_hash.json')
    out = []
    for prof, v in cat.items():
        disco = L.disco_della_versione(prof, cache, cat)
        dstato = T('no', 'no')
        if disco:
            dstato = T('si (Redump)', 'yes (Redump)') if disco.get('redump') else T('si', 'yes')
        cartella = L.GIOCHI / prof
        try:
            st = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            st = None
        istato = T('no', 'no')
        pronta = False
        if st:
            exe = L.trova_exe(cartella / 'build-release')
            m3 = st.get('m3') or {}
            if st.get('completata') and exe:
                # (i moduli compilati in anticipo li mostra "Stato"; qui solo cio' che serve al giocatore)
                extra = [x for x in ('PGXP' if st.get('pgxp') else '',
                                     T('distanza visiva', 'draw distance') if st.get('distanza') else '',
                                     'widescreen' if st.get('bordi_widescreen') else '',
                                     'PGO' if st.get('pgo') else '',
                                     T('salto delle attese', 'idle skip')
                                     if L.attese_accese(cartella / 'game.toml') else '') if x]
                istato = T('installata', 'installed') + (': ' + ', '.join(extra) if extra else '')
                pronta = True
                if st.get('distanza') and not (st.get('bordi_widescreen') and st.get('area_pacchetti')
                                               and st.get('gioco_widescreen') and st.get('piani_widescreen')):
                    # fatta prima della v0.8 / v0.9 / v0.9.1 / v0.11
                    istato += T(' (aggiornabile: premi Installa)', ' (can be updated: press Install)')
                elif not m3.get('attiva'):
                    istato += T(' (senza moduli in anticipo)', ' (without precompiled modules)')
            else:
                istato = T('incompleta', 'incomplete')
        out.append({'profilo': prof, 'nome': nome_versione(prof, v['nome']), 'lingua': lingua_gioco(v.get('lingua', '')),
                    'video': v.get('video', ''), 'disco': dstato, 'installazione': istato, 'ha_disco': bool(disco),
                    'pronta': pronta})
    cache.salva()
    return out


def opzioni_salvate(prof: str) -> dict:
    """Le opzioni gia' scelte per un'installazione (mods\\state.toml accanto all'eseguibile), con i valori
    che usa il comando "opzioni"; {} se non ci sono."""
    for d in ('build-release', 'build-dev'):
        path = L.GIOCHI / prof / d / 'mods' / 'state.toml'
        if not path.is_file():
            continue
        try:
            stato = L.leggi_stato_mod(path)
        except (OSError, ValueError):
            return {}
        voci = {(f.get('package_id'), f.get('id')): f for f in stato['feature']}

        def voce(mod):
            return voci.get(tuple(mod)) or {}

        def valore(mod, chiave, spento):
            v = voce(mod)
            return str((v.get('values') or {}).get(chiave, spento)) if v.get('enabled') else spento
        filtro = str((voce(L.MOD_FILTRI).get('values') or {}).get('texture_filtering', 'default'))
        video = L.leggi_video(path.parent.parent / 'settings.toml')
        sinc = {v: k for k, v in L.SINCRONIA.items()}.get(str(video.get('vsync', 'on')), 'accesa')
        fs = video.get('fullscreen', 0)
        schermo = {v: k for k, v in L.SCHERMO.items()}.get(int(fs) if isinstance(fs, (bool, int)) else 0, 'finestra')
        larg = video.get('window_width', 0)
        return {'risoluzione': valore(L.MOD_RISOLUZIONE, 'resolution', 'gioco'),
                'filtro': 'gioco' if filtro == 'default' else filtro,
                'widescreen': valore(L.MOD_WIDESCREEN, 'aspect', 'no'),
                'pgxp': bool(voce(L.MOD_PGXP).get('enabled')),
                'distanza': bool(voce(L.MOD_DISTANZA).get('enabled')),
                'attese': L.attese_accese(L.GIOCHI / prof / 'game.toml'),
                'sincronia': sinc, 'thread': bool(video.get('render_thread')), 'schermo': schermo,
                'larghezza': larg if isinstance(larg, int) else 0,
                'latenza': video.get('low_latency_input') is not False,
                'fluido': bool(video.get('frame_generation'))}
    return {}


class Finestra:
    def __init__(self, root: tk.Tk, prima: dict | None = None, registro: str = ''):
        """prima e registro: scelte e registro della finestra di prima, quando la si rifa' per cambiare lingua."""
        self.root = root
        self.vivo = True
        self.coda: queue.Queue = queue.Queue()
        self.proc = None
        self.righe = []
        self._pronto = T('Pronto.', 'Ready.')
        self._controllo = T('Controllo dei dischi e delle installazioni...', 'Checking the discs and installations...')
        self._msg_dopo = self._pronto
        self._da_scegliere = (prima or {}).get('profilo')
        Suggerimento.tutti.clear()
        root.title(TITOLO)
        scala = max(1.0, root.winfo_fpixels('1i') / 96.0)     # schermi con ingrandimento (150% ecc.)
        root.geometry(f'{int(1120 * scala)}x{int(800 * scala)}')
        root.minsize(int(820 * scala), int(600 * scala))
        try:    # righe dell'elenco alte quanto il carattere (con l'ingrandimento di Windows erano tagliate)
            import tkinter.font as tkfont
            alto = tkfont.nametofont('TkDefaultFont').metrics('linespace')
            ttk.Style(root).configure('Treeview', rowheight=int(alto * 1.3) + 2)
        except Exception:  # noqa: BLE001
            pass

        cima = ttk.Frame(root, padding=(12, 10, 12, 4))
        cima.pack(fill='x')
        lingue = ttk.Frame(cima)
        lingue.pack(side='right', anchor='ne')
        e_lingua = ttk.Label(lingue, text='Lingua / Language:')
        e_lingua.pack(side='left', padx=(0, 6))
        self.lingua = tk.StringVar(value=etichetta_di(LINGUE, lingua(), 'Italiano'))
        self.cb_lingua = ttk.Combobox(lingue, textvariable=self.lingua, values=[e for e, _ in LINGUE], state='readonly',
                                      width=10)
        self.cb_lingua.pack(side='left')
        self.cb_lingua.bind('<<ComboboxSelected>>', self.cambia_lingua)
        Suggerimento(e_lingua, SUGG['lingua'])
        Suggerimento(self.cb_lingua, SUGG['lingua'])
        ttk.Label(cima, text='Spider-Man 2: Enter Electro', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        ttk.Label(cima, text=T('Il gioco per PC si prepara dal tuo disco: scegli il dump, installa la versione e '
                               'gioca. Nessun dato del gioco e\' incluso nel progetto. Tieni il mouse su una voce per '
                               'sapere cosa fa.',
                               'The PC game is built from your own disc: choose the dump, install the version and '
                               'play. No game data is included in the project. Hold the mouse over an item to see '
                               'what it does.'),
                  wraplength=int(800 * scala)).pack(anchor='w')

        mezzo = ttk.Frame(root, padding=(12, 4))
        mezzo.pack(fill='both', expand=True)
        colonne = ('nome', 'lingua', 'video', 'disco', 'installazione')
        self.albero = ttk.Treeview(mezzo, columns=colonne, show='headings', height=7, selectmode='browse')
        for c, testo, larg in (('nome', T('Versione', 'Version'), 350), ('lingua', T('Lingua', 'Language'), 75),
                               ('video', 'Video', 55), ('disco', T('Disco in input\\', 'Disc in input\\'), 100),
                               ('installazione', T('Installazione', 'Installation'), 480)):
            self.albero.heading(c, text=testo)
            self.albero.column(c, width=int(larg * scala), anchor='w')
        self.albero.pack(fill='x')
        self.albero.bind('<<TreeviewSelect>>', lambda e: self.versione_scelta())
        Suggerimento(self.albero, SUGG['elenco'], ritardo=900)
        self._opzioni_di = None

        bott = ttk.Frame(mezzo, padding=(0, 8))
        bott.pack(fill='x')
        self.b_disco = ttk.Button(bott, text=T('Aggiungi un disco...', 'Add a disc...'), command=self.aggiungi_disco)
        self.b_installa = ttk.Button(bott, text=T('Installa', 'Install'), command=self.installa)
        self.b_gioca = ttk.Button(bott, text=T('Gioca', 'Play'), command=self.gioca)
        self.b_cartella = ttk.Button(bott, text=T('Apri la cartella', 'Open folder'), command=self.apri_cartella)
        self.b_aggiorna = ttk.Button(bott, text=T('Aggiorna', 'Refresh'), command=self.aggiorna)
        for b in (self.b_disco, self.b_installa, self.b_gioca, self.b_cartella, self.b_aggiorna):
            b.pack(side='left', padx=(0, 8))
        self.b_consigliate = ttk.Button(bott, text=T('Impostazioni per PC lenti', 'Recommended settings for slow PCs'),
                                        command=self.consigliate_pc_lenti)
        self.b_consigliate.pack(side='right')
        for b, chiave in ((self.b_disco, 'disco'), (self.b_installa, 'installa'), (self.b_gioca, 'gioca'),
                          (self.b_cartella, 'cartella'), (self.b_aggiorna, 'aggiorna'),
                          (self.b_consigliate, 'consigliate')):
            Suggerimento(b, SUGG[chiave])

        opz = ttk.LabelFrame(mezzo, text=T('Immagine e gioco', 'Options'), padding=(10, 6))
        opz.pack(fill='x')

        def etichetta(dove, testo, chiave, riga, col, **kw):
            e = ttk.Label(dove, text=testo)
            e.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(e, SUGG[chiave])
            return e

        def spunta(dove, testo, var, chiave, riga, col, **kw):
            c = ttk.Checkbutton(dove, text=testo, variable=var)
            c.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(c, SUGG[chiave])
            return c

        def scelta(dove, var, tabella, chiave, larg, riga, col, **kw):
            cb = ttk.Combobox(dove, textvariable=var, values=[r[0] for r in tabella], state='readonly', width=larg)
            cb.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(cb, SUGG[chiave])
            return cb

        etichetta(opz, T('Risoluzione interna:', 'Internal resolution:'), 'ris', 0, 0)
        self.ris = tk.StringVar(value=etichetta_di(RIS, 'gioco'))
        self.cb_ris = scelta(opz, self.ris, RIS, 'ris', 14, 0, 1, padx=(6, 18))
        etichetta(opz, T('Filtro delle texture:', 'Texture filter:'), 'filtro', 0, 2)
        self.filtro = tk.StringVar(value=etichetta_di(FILTRI, 'gioco'))
        self.cb_filtro = scelta(opz, self.filtro, FILTRI, 'filtro', 18, 0, 3, padx=(6, 0))
        etichetta(opz, 'Widescreen:', 'wide', 1, 0, pady=(6, 0))
        self.wide = tk.StringVar(value=etichetta_di(WIDE, 'no'))
        self.cb_wide = scelta(opz, self.wide, WIDE, 'wide', 20, 1, 1, padx=(6, 18), pady=(6, 0))
        self.pgxp = tk.BooleanVar(value=False)
        spunta(opz, T('PGXP (geometria e texture piu\' precise)', 'PGXP (more precise geometry and textures)'),
               self.pgxp, 'pgxp', 1, 2, columnspan=2, pady=(6, 0))
        self.distanza = tk.BooleanVar(value=False)
        spunta(opz, T('Distanza visiva estesa (sperimentale)', 'Extended draw distance (experimental)'), self.distanza,
               'distanza', 2, 0, columnspan=2, pady=(4, 0))
        self.con_launcher = tk.BooleanVar(value=False)
        spunta(opz, T('Impostazioni di psxrecomp prima del gioco', 'psxrecomp settings before the game'),
               self.con_launcher, 'con_launcher', 2, 2, columnspan=2, pady=(4, 0))
        self.attese = tk.BooleanVar(value=True)
        spunta(opz, T('Salto delle attese (meno lavoro per la CPU)', 'Idle skip (less work for the CPU)'), self.attese,
               'attese', 3, 0, columnspan=2, pady=(4, 0))
        self.pgo = tk.BooleanVar(value=False)
        spunta(opz, T('Installa con il PGO (circa 15% di CPU in meno)', 'Install with PGO (about 15% less CPU)'),
               self.pgo, 'pgo', 3, 2, columnspan=2, pady=(4, 0))

        sch = ttk.LabelFrame(mezzo, text=T('Schermo e prestazioni', 'Display and performance'), padding=(10, 6))
        sch.pack(fill='x', pady=(6, 0))
        etichetta(sch, T('Sincronia verticale:', 'Vertical sync:'), 'sinc', 0, 0)
        self.sinc = tk.StringVar(value=etichetta_di(SINC, 'accesa'))
        self.cb_sinc = scelta(sch, self.sinc, SINC, 'sinc', 22, 0, 1, padx=(6, 18))
        etichetta(sch, T('Schermo:', 'Screen:'), 'schermo', 0, 2)
        self.schermo = tk.StringVar(value=etichetta_di(SCHERMI, 'finestra'))
        self.cb_schermo = scelta(sch, self.schermo, SCHERMI, 'schermo', 26, 0, 3, padx=(6, 0))
        etichetta(sch, T('Larghezza della finestra:', 'Window width:'), 'larghezza', 1, 0, pady=(6, 0))
        self.larghezza = tk.StringVar(value=etichetta_di(LARGHEZZE, 0))
        self.cb_larghezza = scelta(sch, self.larghezza, LARGHEZZE, 'larghezza', 12, 1, 1, padx=(6, 18), pady=(6, 0))
        self.thread = tk.BooleanVar(value=False)
        spunta(sch, T('Disegno in un thread separato', 'Render thread'), self.thread, 'thread', 1, 2, columnspan=2,
               pady=(6, 0))
        self.latenza = tk.BooleanVar(value=True)
        spunta(sch, T('Input a bassa latenza', 'Low-latency input'), self.latenza, 'latenza', 2, 0, columnspan=2,
               pady=(4, 0))
        self.fluido = tk.BooleanVar(value=False)
        spunta(sch, T('Movimento fluido per schermi a 120 Hz o piu\' (sperimentale)',
                      'Smooth motion for 120 Hz or faster screens (experimental)'), self.fluido, 'fluido', 2, 2,
               columnspan=2, pady=(4, 0))
        tasti = ttk.Label(sch, text=TASTI_NEL_GIOCO, foreground='#555', wraplength=int(1040 * scala))
        tasti.grid(row=3, column=0, columnspan=4, sticky='w', pady=(6, 0))
        Suggerimento(tasti, SUGG['tasti'])

        ttk.Label(mezzo, text=T('Registro:', 'Log:')).pack(anchor='w', pady=(8, 0))
        self.registro = ScrolledText(mezzo, height=10, font=('Consolas', 9), wrap='word', state='disabled')
        self.registro.pack(fill='both', expand=True)
        Suggerimento(self.registro, SUGG['registro'], ritardo=1200)

        self.stato = tk.StringVar(value=self._pronto)
        ttk.Label(root, textvariable=self.stato, relief='sunken', anchor='w', padding=(8, 2)).pack(fill='x')
        if prima:
            self.ripristina_scelte(prima)
        if registro:
            self.scrivi(registro)
        root.after(100, self._svuota_coda)
        root.protocol('WM_DELETE_WINDOW', self.chiudi)

    # ---------------------------------------------------------------------------- lingua
    def scelte(self) -> dict:
        """Le scelte di adesso con i valori dei comandi (non i testi), per rifare la finestra in un'altra lingua."""
        return {'profilo': self.profilo_scelto() or self._da_scegliere, 'opzioni_di': self._opzioni_di,
                'ris': dict(RIS).get(self.ris.get(), 'gioco'), 'filtro': dict(FILTRI).get(self.filtro.get(), 'gioco'),
                'wide': dict(WIDE).get(self.wide.get(), 'no'), 'sinc': dict(SINC).get(self.sinc.get(), 'accesa'),
                'schermo': dict(SCHERMI).get(self.schermo.get(), 'finestra'),
                'larghezza': dict(LARGHEZZE).get(self.larghezza.get(), 0),
                **{k: getattr(self, k).get() for k in ('pgxp', 'distanza', 'con_launcher', 'attese', 'pgo', 'thread',
                                                       'latenza', 'fluido')}}

    def ripristina_scelte(self, s: dict) -> None:
        self._opzioni_di = s.get('opzioni_di')
        for var, cb, tabella, chiave in ((self.ris, self.cb_ris, RIS, 'ris'), (self.filtro, self.cb_filtro, FILTRI, 'filtro'),
                                         (self.wide, self.cb_wide, WIDE, 'wide'), (self.sinc, self.cb_sinc, SINC, 'sinc'),
                                         (self.schermo, self.cb_schermo, SCHERMI, 'schermo'),
                                         (self.larghezza, self.cb_larghezza, LARGHEZZE, 'larghezza')):
            valore = s.get(chiave)
            testo = etichetta_di(tabella, valore)
            if testo is None and valore not in (None, ''):
                testo = str(valore)             # valore scelto altrove (menu nel gioco): resta nell'elenco
                tabella.append((testo, valore))
                cb.configure(values=[e for e, _ in tabella])
            if testo is not None:
                var.set(testo)
        for k in ('pgxp', 'distanza', 'con_launcher', 'attese', 'pgo', 'thread', 'latenza', 'fluido'):
            if k in s:
                getattr(self, k).set(bool(s[k]))

    def cambia_lingua(self, _evento=None):
        """Rifa' la finestra nella lingua scelta, con le stesse scelte e lo stesso registro; la ricorda in lingua.txt."""
        v = dict(LINGUE).get(self.lingua.get(), 'it')
        if v == lingua():
            return
        if self.proc is not None:
            messagebox.showinfo('Lingua / Language', T('Aspetta la fine del comando in corso, poi cambia la lingua.',
                                                       'Wait for the running command to finish, then change the '
                                                       'language.'))
            self.lingua.set(etichetta_di(LINGUE, lingua(), 'Italiano'))
            return
        prima, registro = self.scelte(), self.registro.get('1.0', 'end-1c')
        salvata = salva_lingua(v)
        imposta_lingua(v)
        testi()
        self.vivo = False
        for w in self.root.winfo_children():
            w.destroy()
        nuova = Finestra(self.root, prima=prima, registro=registro)
        nuova.scrivi(T('Lingua: italiano', 'Language: English') + ('' if salvata else T(
            ' (lingua.txt non scritto: la scelta vale fino alla chiusura)',
            ' (lingua.txt not written: the choice lasts until the window is closed)')))
        nuova.aggiorna()
        return nuova            # la finestra nuova (la usa la prova automatica)

    # ---------------------------------------------------------------------------- registro e stato
    def scrivi(self, testo: str) -> None:
        self.registro.configure(state='normal')
        self.registro.insert('end', testo.rstrip('\n') + '\n')
        self.registro.see('end')
        self.registro.configure(state='disabled')

    def _svuota_coda(self) -> None:
        if not self.vivo:
            return              # finestra rifatta in un'altra lingua: ci pensa quella nuova
        try:
            while True:
                tipo, dato = self.coda.get_nowait()
                if tipo == 'riga':
                    self.scrivi(dato)
                elif tipo == 'fine':
                    cmd, codice = dato
                    self.proc = None
                    nome = nome_comando(cmd)
                    self.stato.set(T(f'"{nome}" finito ' + ('bene.' if codice == 0 else f'con errore (codice {codice}).'),
                                     f'"{nome}" finished ' + ('successfully.' if codice == 0
                                                              else f'with an error (code {codice}).')))
                    poi, self._poi = getattr(self, '_poi', None), None
                    if poi and codice == 0:
                        poi()
                    else:
                        self.aggiorna()
                elif tipo == 'righe':
                    self._mostra_righe(dato)
        except queue.Empty:
            pass
        self.root.after(100, self._svuota_coda)

    # ---------------------------------------------------------------------------- elenco
    def aggiorna(self) -> None:
        attuale = self.stato.get()
        self._msg_dopo = attuale if attuale != self._controllo else self._msg_dopo
        self.stato.set(self._controllo)

        def lavoro():
            try:
                self.coda.put(('righe', righe_versioni()))
            except Exception as e:  # noqa: BLE001
                self.coda.put(('riga', T(f'ERRORE nel leggere lo stato: {e}', f'ERROR while reading the status: {e}')))
        threading.Thread(target=lavoro, daemon=True).start()

    def _mostra_righe(self, righe: list) -> None:
        scelto = self.profilo_scelto() or self._da_scegliere
        self._da_scegliere = None
        self.righe = righe
        self.albero.delete(*self.albero.get_children())
        for r in righe:
            self.albero.insert('', 'end', iid=r['profilo'], values=(
                f'{r["nome"]} ({r["profilo"]})', r['lingua'], r['video'], r['disco'], r['installazione']))
        if scelto and self.albero.exists(scelto):
            self.albero.selection_set(scelto)
        elif righe:
            primo = next((r['profilo'] for r in righe if r['ha_disco']), righe[0]['profilo'])
            self.albero.selection_set(primo)
        if self.proc is None:
            self.stato.set(self._msg_dopo)
        self.versione_scelta()

    def versione_scelta(self) -> None:
        """Pulsanti per la versione scelta e, se e' cambiata, le sue opzioni gia' salvate."""
        self.aggiorna_pulsanti()
        prof = self.profilo_scelto()
        if prof and prof != self._opzioni_di:
            self._opzioni_di = prof
            self.carica_opzioni(prof)

    def carica_opzioni(self, prof: str) -> None:
        o = opzioni_salvate(prof)
        if not o:
            return
        for var, cb, tabella, valore in ((self.ris, self.cb_ris, RIS, o['risoluzione']),
                                         (self.filtro, self.cb_filtro, FILTRI, o['filtro']),
                                         (self.wide, self.cb_wide, WIDE, o['widescreen']),
                                         (self.sinc, self.cb_sinc, SINC, o.get('sincronia', 'accesa')),
                                         (self.schermo, self.cb_schermo, SCHERMI, o.get('schermo', 'finestra'))):
            etichetta = next((e for e, v in tabella if v == valore), None)
            if etichetta is None:
                if valore not in VALIDI.get(id(tabella), ()):
                    continue                      # valore che il comando "opzioni" non accetta: resta com'e'
                tabella.append((valore, valore))  # valore scelto altrove (menu nel gioco): lo aggiunge all'elenco
                etichetta = valore
                cb.configure(values=[e for e, _ in tabella])
            var.set(etichetta)
        self.pgxp.set(o['pgxp'])
        self.distanza.set(o['distanza'])
        self.attese.set(o.get('attese', True))
        self.thread.set(o.get('thread', False))
        self.latenza.set(o.get('latenza', True))
        self.fluido.set(o.get('fluido', False))
        larg = o.get('larghezza', 0)
        etich = next((e for e, v in LARGHEZZE if v == larg), None)
        if etich is None and isinstance(larg, int) and 640 <= larg <= 7680:
            LARGHEZZE.append((str(larg), larg))
            self.cb_larghezza.configure(values=[e for e, _ in LARGHEZZE])
            etich = str(larg)
        self.larghezza.set(etich or etichetta_di(LARGHEZZE, 0))
        sn = lambda x: valore_letto('si' if x else 'no')  # noqa: E731
        self.scrivi(T(f'Opzioni salvate di {prof}: risoluzione {o["risoluzione"]}, filtro {o["filtro"]}, '
                      f'widescreen {o["widescreen"]}, PGXP {sn(o["pgxp"])}, distanza visiva {sn(o["distanza"])}, '
                      f'salto delle attese {sn(o.get("attese"))}; sincronia {o.get("sincronia")}, '
                      f'thread video {sn(o.get("thread"))}, schermo {o.get("schermo")}',
                      f'Saved options of {prof}: resolution {valore_letto(o["risoluzione"])}, filter '
                      f'{valore_letto(o["filtro"])}, widescreen {o["widescreen"]}, PGXP {sn(o["pgxp"])}, draw distance '
                      f'{sn(o["distanza"])}, idle skip {sn(o.get("attese"))}; vertical sync '
                      f'{valore_letto(o.get("sincronia"))}, render thread {sn(o.get("thread"))}, screen '
                      f'{valore_letto(o.get("schermo"))}'))

    def profilo_scelto(self):
        sel = self.albero.selection()
        return sel[0] if sel else None

    def riga(self, prof):
        return next((r for r in self.righe if r['profilo'] == prof), None)

    def aggiorna_pulsanti(self) -> None:
        r = self.riga(self.profilo_scelto())
        occupato = self.proc is not None
        self.b_disco.state(['disabled' if occupato else '!disabled'])
        self.b_aggiorna.state(['disabled' if occupato else '!disabled'])
        self.b_installa.state(['!disabled' if (r and r['ha_disco'] and not occupato) else 'disabled'])
        pronta = bool(r and r['pronta'])
        self.b_gioca.state(['!disabled' if (pronta and not occupato) else 'disabled'])
        self.b_cartella.state(['!disabled' if (r and (L.GIOCHI / r['profilo']).is_dir()) else 'disabled'])

    # ---------------------------------------------------------------------------- comandi
    def esegui(self, argomenti: list, descrizione: str, poi=None) -> None:
        if self.proc is not None:
            return
        self._poi = poi
        cmd = [sys.executable, '-u', str(Path(L.__file__).resolve())] + argomenti
        self.scrivi(f'\n> {descrizione}')
        self.stato.set(descrizione + '...')
        env = dict(os.environ, PYTHONIOENCODING='utf-8', SM2_LINGUA=lingua())
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.proc = subprocess.Popen(cmd, cwd=str(L.ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding='utf-8', errors='replace', env=env, creationflags=flags)
        self.aggiorna_pulsanti()
        proc = self.proc

        def leggi():
            for riga in proc.stdout:
                self.coda.put(('riga', riga))
            self.coda.put(('fine', (argomenti[0], proc.wait())))
        threading.Thread(target=leggi, daemon=True).start()

    def aggiungi_disco(self) -> None:
        p = filedialog.askopenfilename(title=T('Scegli il dump di Spider-Man 2: Enter Electro',
                                               'Choose the Spider-Man 2: Enter Electro dump'), filetypes=[
            (T('Dump PlayStation', 'PlayStation dumps'), '*.cue *.ccd *.bin *.img *.iso'),
            (T('Tutti i file', 'All files'), '*.*')])
        if p:
            if not messagebox.askyesno(T('Aggiungi un disco', 'Add a disc'),
                                       T('Il dump verra\' riconosciuto e spostato nella cartella input del progetto '
                                         '(con tutti i suoi file). Continuare?',
                                         'The dump will be recognised and moved into the project\'s input folder '
                                         '(with all its files). Continue?')):
                return
            self.esegui(['importa', p], T(f'Aggiungo il disco {Path(p).name}', f'Adding the disc {Path(p).name}'))

    def installa(self) -> None:
        prof = self.profilo_scelto()
        if not prof:
            return
        arg = ['installa', '--profilo', prof] + (['--pgxp'] if self.pgxp.get() else []) + \
              (['--pgo'] if self.pgo.get() else []) + ['--attese', 'si' if self.attese.get() else 'no']
        self.esegui(arg, T(f'Installo {prof} (alcuni minuti' + (', con il PGO qualcuno in piu\'' if self.pgo.get()
                                                                  else '') + ')',
                           f'Installing {prof} (a few minutes' + (', a few more with PGO' if self.pgo.get() else '')
                           + ')'))

    def gioca(self) -> None:
        prof = self.profilo_scelto()
        if not prof:
            return
        opz = ['opzioni', '--profilo', prof, '--risoluzione', dict(RIS).get(self.ris.get(), 'gioco'),
               '--pgxp', 'si' if self.pgxp.get() else 'no',
               '--filtro-texture', dict(FILTRI).get(self.filtro.get(), 'gioco'),
               '--widescreen', dict(WIDE).get(self.wide.get(), 'no'),
               '--distanza', 'si' if self.distanza.get() else 'no',
               '--attese', 'si' if self.attese.get() else 'no',
               '--sincronia', dict(SINC).get(self.sinc.get(), 'accesa'),
               '--thread-video', 'si' if (self.thread.get() or self.fluido.get()) else 'no',
               '--schermo', dict(SCHERMI).get(self.schermo.get(), 'finestra'),
               '--latenza-bassa', 'si' if self.latenza.get() else 'no',
               '--movimento-fluido', 'si' if self.fluido.get() else 'no']
        larg = dict(LARGHEZZE).get(self.larghezza.get(), 0)
        if larg:
            opz += ['--larghezza-finestra', str(larg)]
        avvio =['avvia', '--profilo', prof] + (['--con-launcher'] if self.con_launcher.get() else [])
        self.esegui(opz, T(f'Opzioni di {prof}', f'Saving the options of {prof}'),
                    poi=lambda: self.esegui(avvio, T(f'Avvio {prof}', f'Starting {prof}')))

    def consigliate_pc_lenti(self) -> None:
        """Le scelte piu' leggere per un PC lento (salvate solo con Gioca o Installa)."""
        self.ris.set(etichetta_di(RIS, 'gioco'))
        self.filtro.set(etichetta_di(FILTRI, 'gioco'))
        self.pgxp.set(False)
        self.distanza.set(False)
        self.attese.set(True)
        self.pgo.set(True)
        self.sinc.set(etichetta_di(SINC, 'adattiva'))
        self.thread.set(True)
        self.fluido.set(False)
        self.scrivi(T('Impostazioni per PC lenti scelte: risoluzione e filtro come il gioco, PGXP e distanza visiva '
                      'spenti, salto delle attese acceso, sincronia adattiva, disegno in un thread separato; PGO spuntato '
                      'per la prossima installazione (se l\'installazione ha PGXP, reinstallare senza PGXP alleggerisce '
                      'ancora). Premi Gioca per salvarle.',
                      'Recommended settings for slow PCs chosen: resolution and filter as in the game, PGXP and draw '
                      'distance off, idle skip on, adaptive vertical sync, render thread on; PGO ticked for the next '
                      'installation (if the installation has PGXP, installing again without PGXP makes it lighter '
                      'still). Press Play to save them.'))

    def apri_cartella(self) -> None:
        prof = self.profilo_scelto()
        if prof and (L.GIOCHI / prof).is_dir() and os.name == 'nt':
            os.startfile(str(L.GIOCHI / prof))  # noqa: S606

    def chiudi(self) -> None:
        if self.proc is not None and not messagebox.askyesno(
                T('Uscire', 'Exit'), T('Un comando e\' ancora in corso: chiudendo la finestra lo interrompi. Uscire lo '
                                       'stesso?', 'A command is still running: closing the window stops it. Exit '
                                                  'anyway?')):
            return
        if self.proc is not None:
            self.proc.terminate()
        self.root.destroy()


# -------------------------------------------------------------------------------- immagine della finestra

def _png(path: Path, w: int, h: int, rgb_rows: list) -> None:
    raw = b''.join(b'\x00' + r for r in rgb_rows)
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def cattura_finestra(root: tk.Tk, path: Path) -> str:
    """Windows: salva in PNG il contenuto della finestra (PrintWindow), anche se e' coperta."""
    if os.name != 'nt':
        return 'non Windows'
    import ctypes
    from ctypes import wintypes
    u32, g32 = ctypes.windll.user32, ctypes.windll.gdi32
    H = ctypes.c_void_p
    u32.GetAncestor.argtypes, u32.GetAncestor.restype = [H, ctypes.c_uint], H
    u32.GetWindowRect.argtypes = [H, ctypes.POINTER(wintypes.RECT)]
    u32.GetWindowDC.argtypes, u32.GetWindowDC.restype = [H], H
    u32.ReleaseDC.argtypes = [H, H]
    u32.PrintWindow.argtypes, u32.PrintWindow.restype = [H, H, ctypes.c_uint], ctypes.c_int
    g32.CreateCompatibleDC.argtypes, g32.CreateCompatibleDC.restype = [H], H
    g32.CreateCompatibleBitmap.argtypes, g32.CreateCompatibleBitmap.restype = [H, ctypes.c_int, ctypes.c_int], H
    g32.SelectObject.argtypes, g32.SelectObject.restype = [H, H], H
    g32.GetDIBits.argtypes = [H, H, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    g32.DeleteObject.argtypes = [H]
    g32.DeleteDC.argtypes = [H]
    root.update()
    hwnd = u32.GetAncestor(root.winfo_id(), 2)
    r = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc_win = u32.GetWindowDC(hwnd)
    hdc = g32.CreateCompatibleDC(hdc_win)
    bmp = g32.CreateCompatibleBitmap(hdc_win, w, h)
    g32.SelectObject(hdc, bmp)
    ok = u32.PrintWindow(hwnd, hdc, 2)

    class BMI(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD), ('pad', wintypes.DWORD * 3)]
    bmi = BMI()
    bmi.biSize, bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = 40, w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    g32.DeleteObject(bmp)
    g32.DeleteDC(hdc)
    u32.ReleaseDC(hwnd, hdc_win)
    data = buf.raw
    rows = []
    for y in range(h):
        riga = data[y * w * 4:(y + 1) * w * 4]
        rgb = bytearray(w * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = riga[2::4], riga[1::4], riga[0::4]
        rows.append(bytes(rgb))
    _png(path, w, h, rows)
    return f'{path.name}: {w}x{h}, PrintWindow={ok}'


def autotest(cartella: Path, cambia: bool = False) -> int:
    """Prova senza mouse: elenco, immagine, (con cambia: cambio di lingua e immagine), comando "stato", seconda
    immagine, chiusura."""
    cartella.mkdir(parents=True, exist_ok=True)
    reg = open(cartella / 'gui_log.txt', 'w', encoding='utf-8')

    def r(*a):
        reg.write(' '.join(str(x) for x in a) + '\n')
        reg.flush()
    dpi_nitido()
    root = tk.Tk()
    finestra = {'f': Finestra(root)}
    root.attributes('-topmost', True)
    passi = {'n': 0}
    t0 = time.time()
    r('lingua:', lingua())

    def passo():
        f = finestra['f']
        n = passi['n']
        if n == 10:                          # dopo il cambio di lingua: elenco nella finestra nuova, immagine, "stato"
            if not f.righe and time.time() - t0 < 150:
                root.after(500, passo)
                return
            r('righe dopo il cambio:', json.dumps(f.righe, ensure_ascii=False))
            r(cattura_finestra(root, cartella / 'gui_1_lingua.png'))
            f.esegui(['stato'], T('Stato', 'Status'))
            passi['n'] = 2
            root.after(700, passo)
            return
        if n == 0:
            f.aggiorna()
            r('aggiorna lanciato')
        elif n == 1:
            if not f.righe and time.time() - t0 < 120:
                root.after(500, passo)
                return
            r('righe:', json.dumps(f.righe, ensure_ascii=False))
            r('scelto:', f.profilo_scelto(), 'pulsanti:', {n_: str(b.state()) for n_, b in (
                ('installa', f.b_installa), ('gioca', f.b_gioca), ('cartella', f.b_cartella))})
            r(cattura_finestra(root, cartella / 'gui_1.png'))
            r('spiegazioni:', len(Suggerimento.tutti))
            for nome, widget in (('installa', f.b_installa), ('sincronia', f.cb_sinc), ('thread', None)):
                s = next((x for x in Suggerimento.tutti if (x.w is widget if widget is not None
                                                            else x.testo == SUGG['thread'])), None)
                if s is None:
                    r(f'spiegazione {nome}: NON trovata')
                    continue
                s._mostra()
                for _ in range(8):           # il riquadro va disegnato prima di catturarlo (altrimenti esce nero)
                    root.update()
                    time.sleep(0.05)
                if s._tip is not None:
                    r(f'spiegazione {nome}: ' + cattura_finestra(s._tip, cartella / f'gui_spiegazione_{nome}.png'))
                else:
                    r(f'spiegazione {nome}: non mostrata')
                s._nascondi()
            if cambia:
                altra = 'en' if lingua() == 'it' else 'it'
                f.lingua.set(etichetta_di(LINGUE, altra, 'English'))
                nuova = f.cambia_lingua()
                r('cambio di lingua: adesso', lingua(), '; finestra nuova:', nuova is not None,
                  '; lingua.txt:', (L.ROOT / 'lingua.txt').read_text(encoding='utf-8').strip()
                  if (L.ROOT / 'lingua.txt').is_file() else '(non c\'e\')')
                if nuova is not None:
                    finestra['f'] = nuova
                    passi['n'] = 10
                    root.after(700, passo)
                    return
            f.esegui(['stato'], T('Stato', 'Status'))
        elif n == 2:
            if f.proc is not None and time.time() - t0 < 180:
                root.after(500, passo)
                return
            root.after(800)
            root.update()
            r('registro:', f.registro.get('1.0', 'end').strip())
            r('stato:', f.stato.get())
            r(cattura_finestra(root, cartella / 'gui_2.png'))
            r('fine')
            reg.close()
            root.destroy()
            return
        passi['n'] += 1
        root.after(700, passo)
    root.after(300, passo)
    root.mainloop()
    return 0


def dpi_nitido() -> None:
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--autotest' in argv:
        return autotest(Path(argv[argv.index('--autotest') + 1]), cambia='--cambia-lingua' in argv)
    dpi_nitido()
    root = tk.Tk()
    f = Finestra(root)
    f.scrivi(f'SM2-Recomp launcher {L.VERSIONE} - {L.ROOT}')
    f.scrivi(T('Per iniziare: "Aggiungi un disco..." (oppure metti il dump in input\\), poi "Installa" e "Gioca".',
               'To start: "Add a disc..." (or put the dump in input\\), then "Install" and "Play".'))
    f.aggiorna()
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
