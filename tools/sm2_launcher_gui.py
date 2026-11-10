#!/usr/bin/env python3
"""EnterElectro-Recomp - finestra del launcher (dal 27/10/2026; spiegazioni al passaggio del mouse e opzioni dello schermo dal 31/10).

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

Dal 5/11/2026 (0.12): il pulsante "Filmati" apre la finestra dei filmati (classe FinestraFilmati): Migliorati e tre
filmati IA a scelta (Swin2SR, Real-ESRGAN general-x4v3 e animevideov3), con le immagini di prova fatte dal disco del
giocatore, i difetti possibili di ciascuno e il tempo su questo PC; le scelte IA sono anche nelle opzioni dei filmati.

Dal 6/11/2026 (0.12): l'icona del launcher (tools/grafica/icona_launcher: ragnatela, fulmine e la scritta SM2, disegnata
per EnterElectro-Recomp, niente del gioco) sulla finestra e sulla barra delle applicazioni (il launcher ha un suo AppUserModelID,
EnterElectroRecomp.Launcher, cosi' Windows non mostra l'icona di Python), e il collegamento EnterElectro-Recomp.lnk con quell'icona nella
cartella di EnterElectro-Recomp (apre SM2-Launcher.cmd; si rifa' da solo se la cartella viene spostata). Il collegamento lo
scrive un processo a parte (questo file con --collegamento), cosi' un problema di Windows non puo' fermare la finestra.
La prova automatica scrive anche le icone della finestra (gui_icona_piccola.png, gui_icona_grande.png) e il collegamento.

English: the EnterElectro-Recomp launcher window (tkinter). It drives tools/sm2_launcher.py in a separate process: list of the 7
game versions with disc and installation state, buttons Add a disc / Install / Play / Open folder / Refresh, the player's
options and a log. Since 4 Nov 2026 the window is in Italian or English ("Lingua / Language" choice, saved in
lingua.txt); the values passed to the commands stay the Italian ones, which sm2_launcher.py always accepts.
--autotest FOLDER opens the window, refreshes the list, saves screenshots, runs "status" and closes; with
--cambia-lingua it also switches the language like the "Lingua / Language" choice (writing lingua.txt) and saves a
screenshot of the window in the other language. Since 6 Nov 2026 the launcher has its own icon (window and taskbar, with
its own AppUserModelID) and creates the EnterElectro-Recomp.lnk shortcut with that icon in its folder.
"""
from __future__ import annotations

import base64
import json
import os
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sm2_launcher as L  # noqa: E402
from sm2_lingua import T, imposta as imposta_lingua, lingua, lingua_gioco, nome_versione  # noqa: E402
from sm2_lingua import salva as salva_lingua  # noqa: E402
import sm2_comandi as C  # noqa: E402
import sm2_salvataggi as S  # noqa: E402
import sm2_grafica as GR  # noqa: E402

TITOLO = f'Spider-Man 2: Enter Electro - EnterElectro-Recomp {L.VERSIONE}'
LINGUE = [('Italiano', 'it'), ('English', 'en')]
# nomi inglesi dei comandi di sm2_launcher.py (solo per i messaggi; la finestra lancia sempre i nomi italiani)
NOMI_COMANDI_EN = {'riconosci': 'identify', 'importa': 'import', 'installa': 'install', 'avvia': 'play',
                   'opzioni': 'options', 'stato': 'status', 'prepara-registrazione': 'prepare-recording',
                   'prepara-filmati': 'prepare-movies', 'prepara-filmati-ia': 'prepare-ai-movies',
                   'ia-scarica': 'ai-download', 'anteprime-ia': 'ai-previews'}
# valori interni (italiani) delle opzioni, come si leggono nei messaggi in inglese
VALORI_EN = {'si': 'yes', 'no': 'no', 'gioco': 'game', 'accesa': 'on', 'spenta': 'off', 'adattiva': 'adaptive',
             'finestra': 'window', 'senza-bordi': 'borderless', 'esclusivo': 'exclusive', 'originali': 'original',
             'filtro': 'real-time filter', 'migliorati': 'enhanced', 'ia-swin2sr': 'AI Swin2SR',
             'ia-general': 'AI Real-ESRGAN general', 'ia-anime': 'AI Real-ESRGAN anime'}

RIS: list = []
FILTRI: list = []
FILMATI: list = []
WIDE: list = []
SINC: list = []
SCHERMI: list = []
LARGHEZZE: list = []
TASTI_NEL_GIOCO = ''
SORGENTI: dict = {}
FACCE: dict = {}
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
    global RIS, FILTRI, FILMATI, WIDE, SINC, SCHERMI, LARGHEZZE, TASTI_NEL_GIOCO, SUGG, VALIDI, SORGENTI, FACCE
    RIS = [(T('Come il gioco', 'As in the game'), 'gioco'), (T('Nativa', 'Native'), 'native'), ('720p', '720p'),
           ('1080p', '1080p'), ('1440p', '1440p'), ('4K', '4k')]
    FILTRI = [(T('Come il gioco', 'As in the game'), 'gioco'), (T('Nearest (originale)', 'Nearest (original)'), 'nearest'),
              ('Bilinear', 'bilinear'), ('xBR', 'xbr')]
    FILMATI = [(T('Originali', 'Original'), 'originali'), (T('Filtro in tempo reale', 'Real-time filter'), 'filtro'),
               (T('Migliorati', 'Enhanced'), 'migliorati'),
               (T('IA: Swin2SR (fedele)', 'AI: Swin2SR (faithful)'), 'ia-swin2sr'),
               (T('IA: Real-ESRGAN general (nitido)', 'AI: Real-ESRGAN general (sharp)'), 'ia-general'),
               (T('IA: Real-ESRGAN anime (cartone)', 'AI: Real-ESRGAN anime (cartoon)'), 'ia-anime')]
    WIDE = [('No (4:3)', 'no'), (T('16:9 (sperimentale)', '16:9 (experimental)'), '16:9'),
            (T('16:10 (sperimentale)', '16:10 (experimental)'), '16:10'),
            (T('21:9 (sperimentale)', '21:9 (experimental)'), '21:9'),
            (T('Adatta alla finestra (sperimentale)', 'Fit to window (experimental)'), 'adatta')]
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
    # nomi dei tasti del controller (valori di input.ini) per la finestra dei comandi
    SORGENTI = {'dpup': T('croce direzionale su', 'd-pad up'), 'dpdown': T('croce direzionale gi\u00f9', 'd-pad down'),
                'dpleft': T('croce direzionale sinistra', 'd-pad left'),
                'dpright': T('croce direzionale destra', 'd-pad right'),
                'leftshoulder': 'L1 / LB', 'rightshoulder': 'R1 / RB', 'lefttrigger': 'L2 / LT', 'righttrigger': 'R2 / RT',
                'leftstick': T('L3 (levetta sinistra premuta)', 'L3 (left stick click)'),
                'rightstick': T('R3 (levetta destra premuta)', 'R3 (right stick click)'), 'start': 'Start',
                'back': 'Select / Back', 'guide': T('tasto PS / Guide', 'PS / Guide button'), 'touchpad': 'Touchpad',
                'leftx-': T('levetta sinistra a sinistra', 'left stick left'),
                'leftx+': T('levetta sinistra a destra', 'left stick right'),
                'lefty-': T('levetta sinistra su', 'left stick up'), 'lefty+': T('levetta sinistra gi\u00f9', 'left stick down'),
                'rightx-': T('levetta destra a sinistra', 'right stick left'),
                'rightx+': T('levetta destra a destra', 'right stick right'),
                'righty-': T('levetta destra su', 'right stick up'),
                'righty+': T('levetta destra gi\u00f9', 'right stick down'), 'none': T('nessuno', 'none')}
    FACCE = {'cross': T('Croce', 'Cross'), 'circle': T('Cerchio', 'Circle'), 'square': T('Quadrato', 'Square'),
             'triangle': T('Triangolo', 'Triangle'), 'A': 'A', 'B': 'B', 'X': 'X', 'Y': 'Y'}
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
                   "successive e si possono cambiare pure dal menu nel gioco (F10). Collega il controller prima di "
                   "premere Gioca: il gioco cerca il DualShock solo all'avvio, e senza non c'\u00e8 la vibrazione.",
                   "Saves the options chosen in this window and starts the game. The options are kept for the next "
                   "times as well and can also be changed from the in-game menu (F10). Connect the gamepad before "
                   "pressing Play: the game looks for a DualShock only at start-up, and without it there is no "
                   "rumble."),
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
        'filmati': T("Come vengono mostrati i filmati del gioco. Originali: ingranditi a blocchi, come sulla PS1. "
                     "Filtro in tempo reale: attenua i quadretti della compressione, pulisce i colori e ingrandisce "
                     "seguendo i contorni, senza preparazione. "
                     "Migliorati: fotogrammi ripuliti e ingranditi 4 volte, preparati una volta dal tuo disco (circa "
                     "1,3 GB). IA: fotogrammi ingranditi da un'intelligenza artificiale (Swin2SR, Real-ESRGAN general o "
                     "anime), pi\u00f9 nitidi ma con qualche difetto possibile; si scaricano e si preparano una volta "
                     "con il pulsante \u00abFilmati\u00bb, dove li confronti con le immagini di prova. Dove mancano i "
                     "fotogrammi preparati valgono i Migliorati o il filtro. Solo con OpenGL. Vale dal prossimo avvio.",
                     "How the game's movies are shown. Original: enlarged in blocks, as on the PS1. Real-time filter: "
                     "softens the compression blocks, cleans up the colours and enlarges following the edges, with no "
                     "preparation. Enhanced: frames cleaned up and "
                     "enlarged 4 times, prepared once from your disc (about 1.3 GB). AI: frames enlarged by an "
                     "artificial intelligence (Swin2SR, Real-ESRGAN general or anime), sharper but with some possible "
                     "defects; they are downloaded and prepared once with the \u201cMovies\u201d button, where you "
                     "compare them with the test pictures. Where the prepared frames are missing, the Enhanced movies "
                     "or the filter are used. OpenGL only. Applies from the next start."),
        'prepara_filmati': T("Apre la finestra dei filmati della versione scelta: prepara i Migliorati (pochi minuti) o i "
                             "filmati IA, con le immagini di prova fatte dal tuo disco per confrontarli, i difetti "
                             "possibili di ciascuno e il tempo che ci vuole su questo PC.",
                             "Opens the movies window of the chosen version: prepares the Enhanced movies (a few "
                             "minutes) or the AI movies, with test pictures made from your disc to compare them, the "
                             "possible defects of each and the time it takes on this PC."),
        'ia_scelte': T("Le versioni dei filmati: scegline una per vedere la sua immagine di prova, la spiegazione e i "
                       "difetti possibili. Il pallino dice se \u00e8 pronta (verde), a met\u00e0 o da preparare.",
                       "The movie versions: choose one to see its test picture, the explanation and the possible "
                       "defects. The dot tells whether it is ready (green), half done or still to prepare."),
        'ia_scarica': T("Scarica una volta sola i programmi e i tre modelli IA (circa 100 MB: prima chiede il permesso, "
                        "con fonti e licenze) e fa le immagini di prova con il tuo disco, misurando il tempo sulla tua "
                        "scheda video.",
                        "Downloads only once the programs and the three AI models (about 100 MB: it asks for permission "
                        "first, with sources and licences) and makes the test pictures from your disc, measuring the "
                        "time on your graphics card."),
        'ia_prepara': T("Prepara i filmati della versione scelta a sinistra, dal tuo disco: i Migliorati in pochi "
                        "minuti, i filmati IA da pochi minuti a qualche ora secondo il modello e la scheda video. Si "
                        "pu\u00f2 fermare e riprendere.",
                        "Prepares the movies of the version chosen on the left, from your disc: the Enhanced ones in a "
                        "few minutes, the AI ones from a few minutes to a few hours depending on the model and the "
                        "graphics card. It can be stopped and resumed."),
        'ia_ferma': T("Ferma la preparazione dei filmati IA alla fine del fotogramma in corso. Con \u00abRiprendi\u00bb "
                      "si continua da dove era, senza rifare i filmati gi\u00e0 finiti.",
                      "Stops the preparation of the AI movies at the end of the current frame. \u201cResume\u201d "
                      "continues where it was, without redoing the movies already finished."),
        'ia_usa': T("Mette questi filmati nella scelta \u00abFilmati\u00bb delle opzioni; si salva con "
                    "\u00abGioca\u00bb, come le altre opzioni.",
                    "Puts these movies in the \u201cMovies\u201d choice of the options; it is saved with "
                    "\u201cPlay\u201d, like the other options."),
        'precedente': T("Porta qui i dischi, le installazioni e i salvataggi (memory card e salvataggi rapidi) di una "
                        "cartella di EnterElectro-Recomp precedente (o di SM2-Recomp, il nome fino alla 0.11): scegli quella "
                        "cartella. I file vengono spostati, non "
                        "copiati, e la cartella vecchia resta: la cancelli tu quando hai controllato che tutto "
                        "funziona. Le installazioni fatte con un motore diverso vanno reinstallate, ma i salvataggi "
                        "restano.",
                        "Brings here the discs, installations and saves (memory cards and save states) of an earlier "
                        "EnterElectro-Recomp folder (or SM2-Recomp, the name up to 0.11): choose that folder. The files are "
                        "moved, not copied, and the old folder "
                        "stays: you delete it once you have checked that everything works. Installations made with a "
                        "different engine must be installed again, but the saves stay."),
        'comandi': T("Controller e tasti del giocatore 1 per la versione scelta: quale controller usare, analogico o "
                     "digitale, zona morta delle levette e quale tasto del controller o della tastiera fa ogni comando "
                     "della PS1. Si prova tutto dal vivo, prima di giocare.",
                     "Player 1 gamepad and keys for the chosen version: which gamepad to use, analog or digital, stick "
                     "dead zone and which gamepad button or keyboard key does each PS1 control. Everything can be "
                     "tried live, before playing."),
        'cmd_controller': T("Primo collegato: il gioco usa il primo controller che trova, anche se lo colleghi a gioco "
                            "aperto (la vibrazione per\u00f2 c'\u00e8 solo se \u00e8 collegato prima di avviare il "
                            "gioco). Solo tastiera: il controller viene ignorato. Oppure un controller preciso tra "
                            "quelli collegati adesso. La tastiera funziona sempre.",
                            "First connected: the game uses the first gamepad it finds, even if you plug it in while "
                            "playing (but rumble works only if it is connected before starting the game). Keyboard only: gamepads are ignored. Or one particular gamepad among those connected "
                            "now. The keyboard always works."),
        'cmd_modo': T("Analogico: le levette funzionano come levette (come un DualShock). Digitale: la levetta sinistra fa "
                      "da croce direzionale, come un controller PS1 senza levette.",
                      "Analog: the sticks work as sticks (like a DualShock). Digital: the left stick acts as the d-pad, "
                      "like a PS1 controller without sticks."),
        'cmd_zona': T("Quanto devi spostare una levetta o premere un grilletto prima che il gioco se ne accorga. Alzala se "
                      "il personaggio si muove da solo (levette consumate); il gioco usa il 10%.",
                      "How far you must move a stick or press a trigger before the game notices. Raise it if the "
                      "character moves by itself (worn sticks); the game uses 10%."),
        'wide': T("Allarga l'immagine a 16:9, 16:10 o 21:9 mostrando pi\u00f9 scena ai lati invece di stirarla; con "
                  "\u00abAdatta alla finestra\u00bb segue la forma della finestra o dello schermo. Filmati, "
                  "menu e giornale restano in 4:3. Sperimentale: in pochi punti un oggetto ai lati pu\u00f2 comparire in "
                  "ritardo.",
                  "Widens the picture to 16:9, 16:10 or 21:9, showing more of the scene at the sides instead of "
                  "stretching it; with \"Fit to window\" it follows the shape of the window or screen. Movies, menus and "
                  "the journal stay in 4:3. Experimental: in a few places an object at the sides can appear late."),
        'pgxp': T("Correzione della geometria (PGXP, come in DuckStation): i poligoni non tremano pi\u00f9 tra un "
                  "pixel e l'altro e, con le texture in prospettiva, pavimenti e muri non si deformano. Si nota da 720p "
                  "in su. Funziona davvero solo se l'installazione ha i punti di aggancio di PGXP: se non li ha, Gioca "
                  "la ricompila una volta (salvataggi e opzioni restano). Costa processore: sui PC deboli lascialo "
                  "spento. Le singole voci sono in \u00abOpzioni PGXP...\u00bb.",
                  "Geometry correction (PGXP, as in DuckStation): polygons stop wobbling between pixels and, with "
                  "perspective-correct textures, floors and walls stop warping. It shows from 720p up. It really works "
                  "only if the installation has the PGXP hooks: if it does not, Play builds it again once (saves and "
                  "options stay). It costs processor: on weak PCs leave it off. The single items are in \u00abPGXP "
                  "options...\u00bb."),
        'pgxp_finestra': T("Le voci di PGXP una per una, con i nomi e i valori di partenza di DuckStation.",
                           "The PGXP items one by one, with DuckStation's names and defaults."),
        'pgxp_texture': T("Texture in prospettiva (Texture Correction): pavimenti e muri non si deformano pi\u00f9 "
                          "quando la telecamera si muove. Acceso di partenza, come in DuckStation.",
                          "Perspective-correct textures (Texture Correction): floors and walls stop warping when the "
                          "camera moves. On by default, as in DuckStation."),
        'pgxp_colori': T("Colori in prospettiva (Color Correction): anche le sfumature di colore seguono la "
                         "prospettiva. Di solito si nota poco. Vale solo con le texture in prospettiva. Spento di "
                         "partenza, come in DuckStation.",
                         "Perspective-correct colours (Color Correction): colour shading follows the perspective too. "
                         "Usually subtle. Only with perspective-correct textures. Off by default, as in DuckStation."),
        'pgxp_culling': T("Correzione del culling (Culling Correction): il gioco sceglie quali facce nascondere usando "
                          "le posizioni precise, cos\u00ec non si aprono buchi tra i poligoni lontani. Cambia un calcolo "
                          "del gioco, ma solo su cosa disegnare. Acceso di partenza, come in DuckStation.",
                          "Culling Correction: the game chooses which faces to hide from the precise positions, so no "
                          "gaps open between far polygons. It changes one of the game's calculations, but only about "
                          "what to draw. On by default, as in DuckStation."),
        'pgxp_proiezione': T("Precisione della proiezione (Preserve Projection Precision): usa la proiezione esatta "
                             "invece di quella arrotondata della PS1 e toglie l'ultimo tremolio della geometria vicina "
                             "alla telecamera. Spento di partenza, come in DuckStation.",
                             "Preserve Projection Precision: uses the exact projection instead of the PS1's rounded one "
                             "and removes the last wobble of geometry near the camera. Off by default, as in "
                             "DuckStation."),
        'pgxp_cpu': T("Modalit\u00e0 CPU (CPU Mode): segue la precisione anche nei calcoli del processore, per i "
                      "giochi che rielaborano i vertici. Pi\u00f9 poligoni corretti ma pi\u00f9 lavoro per il "
                      "processore. Accesa di partenza: per Spider-Man 2 DuckStation la accende da solo (il suo "
                      "database dei giochi: riduce un po' il tremolio).",
                      "CPU Mode: follows the precision through the processor's calculations too, for games that rework "
                      "the vertices. More polygons corrected but more processor work. On by default: for Spider-Man 2 "
                      "DuckStation turns it on by itself (its game database: it reduces jitter slightly)."),
        'pgxp_cache': T("Cache dei vertici (Vertex Cache): per i vertici di cui PGXP non conosce la storia usa la "
                        "posizione precisa vista per ultima nello stesso punto dello schermo. Pu\u00f2 aiutare, ma "
                        "pu\u00f2 anche spostare per sbaglio scritte e menu. Spento di partenza, come in DuckStation.",
                        "Vertex Cache: for vertices whose history PGXP does not know, it uses the precise position last "
                        "seen at the same point of the screen. It can help, but it can also wrongly move text and "
                        "menus. Off by default, as in DuckStation."),
        'pgxp_profondita': T("Buffer di profondit\u00e0 (Depth Buffer, bassa compatibilit\u00e0 come in DuckStation): "
                             "decide cosa sta davanti con la profondit\u00e0 dei vertici invece che con l'ordine di "
                             "disegno del gioco. In Spider-Man 2 sbaglia: nasconde pezzi di Spider-Man dietro "
                             "pavimento e casse (prova del 5/11/2026). Lascialo spento. Come in DuckStation vale solo "
                             "con le texture in prospettiva.",
                             "Depth Buffer (low compatibility, as in DuckStation): decides what is in front from the "
                             "vertices' depth instead of the game's drawing order. In Spider-Man 2 it gets it wrong: it "
                             "hides parts of Spider-Man behind floors and crates (test of 5 Nov 2026). Leave it off. "
                             "As in DuckStation, only with perspective-correct textures."),
        'pgxp_no2d': T("Niente PGXP sui poligoni 2D (Disable on 2D Polygons): i poligoni che non hanno la profondit\u00e0 su "
                       "tutti i vertici (interfaccia, scritte, poligoni fatti dal processore) restano interi nella "
                       "posizione della PS1. Pu\u00f2 sistemare un'interfaccia storta, altrimenti va lasciato spento: "
                       "dove un poligono torna alla PS1 accanto a uno preciso si possono vedere fessure. Come in "
                       "DuckStation la profondit\u00e0 c'\u00e8 solo con le texture in prospettiva: senza, tornano "
                       "tutti alla PS1. Spento di partenza, come in DuckStation.",
                       "Disable on 2D Polygons: polygons without depth on every vertex (interface, text, polygons built "
                       "by the processor) stay whole at the PS1 position. It can fix a misaligned interface, otherwise "
                       "leave it off: where a polygon goes back to the PS1 next to a precise one, cracks can show. As in "
                       "DuckStation, depth exists only with perspective-correct textures: without them, all polygons go "
                       "back to the PS1. Off by default, as in DuckStation."),
        'pgxp_trasparenti': T("Profondit\u00e0 anche per i semitrasparenti (Depth Test Transparent Polygons): con il "
                              "buffer di profondit\u00e0 anche ombre ed effetti semitrasparenti fanno il test di "
                              "profondit\u00e0; spesso le ombre entrano nel pavimento. Vale solo con il buffer di "
                              "profondit\u00e0. Spento di partenza, come in DuckStation.",
                              "Depth Test Transparent Polygons: with the depth buffer, semi-transparent shadows and "
                              "effects are depth tested too; shadows often clip into the floor. Only with the depth "
                              "buffer. Off by default, as in DuckStation."),
        'pgxp_soglia': T("Soglia di pulizia della profondit\u00e0 (Depth Clear Threshold): quando la profondit\u00e0 "
                         "media dei poligoni torna indietro di pi\u00f9 di cos\u00ec, il buffer di profondit\u00e0 si "
                         "svuota (il gioco ha cominciato un altro disegno). In unit\u00e0 SZ della PS1; 0 = mai. Vale "
                         "solo con il buffer di profondit\u00e0.",
                         "Depth Clear Threshold: when the polygons' average depth jumps back by more than this, the "
                         "depth buffer is cleared (the game started another drawing pass). In PS1 SZ units; 0 = never. "
                         "Only with the depth buffer."),
        'pgxp_tolleranza': T("Tolleranza della geometria (Geometry Tolerance): scarta le posizioni precise che si "
                             "allontanano pi\u00f9 di questi pixel da quelle della PS1. Di partenza 3, come DuckStation "
                             "per Spider-Man 2 (il suo database dei giochi: sistema i poligoni sbagliati per un cambio "
                             "di segno e gli effetti dei fulmini); -1 = nessun limite.",
                             "Geometry Tolerance: discards precise positions further than this many pixels from the "
                             "PS1 ones. 3 by default, as DuckStation for Spider-Man 2 (its game database: it fixes "
                             "glitch polygons from a sign flip and the lightning effects); -1 = no limit."),
        'pgxp_bias': T("Depth Bias: con il buffer di profondit\u00e0 ogni poligono va un po' pi\u00f9 vicino alla "
                       "telecamera di quelli disegnati prima, di tanti milionesimi della profondit\u00e0: i poligoni "
                       "sovrapposti (scritte, ombre) restano nell'ordine di disegno. Valori alti tolgono il tremolio "
                       "delle scritte ma possono far vedere poligoni attraverso quelli davanti. Di partenza 1, come in "
                       "DuckStation. Vale solo con il buffer di profondit\u00e0.",
                       "Depth Bias: with the depth buffer, each polygon moves a little closer to the camera than the "
                       "ones drawn before it, in millionths of depth: overlapping polygons (decals, shadows) stay in "
                       "drawing order. High values remove decal flicker but can make polygons show through the ones in "
                       "front. 1 by default, as in DuckStation. Only with the depth buffer."),
        'pgxp_normalizza': T("Normalizzazione della profondit\u00e0 (Normalize Depth Scale): toglie dalla profondit\u00e0 "
                             "la scala della trasformazione di ogni oggetto. Spider-Man 2 scala le trasformazioni degli "
                             "oggetti, quindi con il buffer di profondit\u00e0 conviene \u00abCon il buffer di "
                             "profondit\u00e0\u00bb; \u00abSempre\u00bb la usa anche per le texture in prospettiva. "
                             "Automatica di partenza, come in DuckStation (per Spider-Man 2 vuol dire spenta).",
                             "Normalize Depth Scale: removes the scale of each object's transform from the depth. "
                             "Spider-Man 2 scales its object transforms, so with the depth buffer \u201cDepth buffer "
                             "only\u201d is the one to use; \u201cAlways\u201d applies it to texture correction too. "
                             "Automatic by default, as in DuckStation (for Spider-Man 2 it means off)."),
        'pgxp_fessure': T("Fessure (in pi\u00f9 di DuckStation, dal motore psxrecomp): allarga di pochissimo i bordi "
                          "dei poligoni per chiudere le fessure sottili che ad alta risoluzione lasciano vedere lo "
                          "sfondo. Vale solo con il buffer di profondit\u00e0, che decide chi sta sopra.",
                          "Seams (extra to DuckStation, from the psxrecomp engine): widens polygon edges a tiny bit to "
                          "close the thin cracks that show the background at high resolution. Only with the depth "
                          "buffer, which decides which one is on top."),
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
        'pgo': T("Vale per Installa. Il gioco viene ottimizzato sulle parti del codice che si usano di pi\u00f9: "
                 "circa 15% di processore in meno. Se il pacchetto ha il profilo gi\u00e0 pronto per la tua versione, "
                 "basta una compilazione e l'installazione dura quasi come senza PGO; altrimenti prima c'\u00e8 una "
                 "partita di prova automatica di circa 3 minuti, senza finestra e senza audio, e l'installazione dura "
                 "qualche minuto in pi\u00f9.",
                 "Applies to Install. The game is optimised for the parts of the code that are used most: about 15% "
                 "less processor. If the package has the ready-made profile for your version, one build is enough and "
                 "the installation takes almost as long as without PGO; otherwise an automatic test game of about 3 "
                 "minutes, with no window and no audio, comes first and the installation takes a few minutes longer."),
        'sinc': T("Sincronia verticale. Accesa (consigliata): immagine senza strappi; un frame in ritardo aspetta "
                  "il refresh successivo (un piccolo scatto). Adattiva: come accesa, ma un frame in ritardo viene "
                  "mostrato subito, con un possibile strappo; sugli schermi pi\u00f9 veloci del gioco (120, 144, 240 "
                  "Hz) diventa accesa, perch\u00e9 l\u00ec strapperebbe sempre. Spenta: nessuna attesa, strappi. VRR: "
                  "per schermi G-Sync o FreeSync attivi.",
                  "Vertical sync. On (recommended): a picture without tearing; a late frame waits for the next refresh "
                  "(a small hitch). Adaptive: like On, but a late frame is shown at once, with possible tearing; on "
                  "screens faster than the game (120, 144, 240 Hz) it becomes On, because there it would always tear. "
                  "Off: no waiting, tearing. VRR: for active G-Sync or FreeSync screens."),
        'thread': T("Comanda la scheda video da un secondo thread del processore, in parallelo all'emulazione: un "
                    "frame costa il pi\u00f9 lento dei due lavori invece della loro somma. Pu\u00f2 aiutare sui PC con "
                    "almeno 2 core; aggiunge al massimo un frame di ritardo all'immagine. Attenzione: sulle schede "
                    "NVIDIA, tranne che a schermo intero esclusivo, psxrecomp spegne la sincronia verticale quando il "
                    "thread \u00e8 acceso, e a schermo intero senza bordi l'immagine pu\u00f2 strappare: se vedi "
                    "strappi, spegnilo. Si applica al prossimo avvio.",
                    "Drives the graphics card from a second processor thread, in parallel with the emulation: a frame "
                    "costs the slower of the two jobs instead of their sum. It can help on PCs with at least 2 cores; "
                    "it adds at most one frame of delay to the picture. Note: on NVIDIA graphics cards, except in "
                    "exclusive fullscreen, psxrecomp turns vertical sync off while the thread is on, and in borderless "
                    "fullscreen the picture can tear: if you see tearing, turn it off. Applied at the next start."),
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
        'volume': T("Volume del gioco quando parte (100% = come il gioco). Nel gioco lo cambiano + e \u2212 del "
                    "tastierino. Serve un'installazione della 0.12: con una precedente reinstalla (i salvataggi "
                    "restano).",
                    "Game volume when it starts (100% = as in the game). In the game the keypad + and \u2212 change "
                    "it. It needs a 0.12 installation: with an earlier one, install again (the saves stay)."),
        'consigliate':T("Imposta qui sotto le scelte pi\u00f9 leggere per un PC lento: risoluzione e filtro come il "
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
              id(FILTRI): ('gioco', 'nearest', 'bilinear', 'xbr'), id(WIDE): ('no', '16:9', '16:10', '21:9', 'adatta'),
              id(FILMATI): ('originali', 'filtro', 'migliorati', 'ia-swin2sr', 'ia-general', 'ia-anime'),
              id(SINC): ('accesa', 'adattiva', 'spenta', 'vrr'), id(SCHERMI): ('finestra', 'senza-bordi', 'esclusivo')}


def etichetta_di(tabella: list, valore, altrimenti=None):
    """Il testo mostrato per un valore di una tabella di scelte (None se il valore non c'e')."""
    return next((e for e, v in tabella if v == valore), altrimenti)


testi()


# -------------------------------------------------------------------------------- aspetto (0.12)
# 0.12, finestra "meno spartana, come OpenGOAL" (richiesta del 5/11/2026): tema scuro; in cima un'immagine grande con il
# titolo, la versione scelta e un pulsante principale grande (Gioca, Installa o Aggiungi un disco); a sinistra l'elenco
# delle versioni con un pallino colorato; a destra le schede (Gioco, Opzioni, Salvataggi, Registro). Tutto con Tk e ttk
# (tema "clam" con i nostri colori): niente librerie in piu'. L'immagine in cima e' un fotogramma dei filmati migliorati
# fatti dal disco del giocatore; senza filmati migliorati c'e' una sfumatura scura fatta qui.
CARATTERE = 'Segoe UI'
COL = {'fondo': '#11151f', 'lista': '#161b27', 'campo': '#1e2432', 'pulsante': '#262d3d', 'pulsante2': '#313a4e',
       'bordo': '#2b3243', 'notte': '#070a14', 'testo': '#e8e9ec', 'testo2': '#a3aab5', 'testo3': '#6c7380', 'accento': '#cf2338',
       'accento2': '#e43b4f', 'accento3': '#a81c2e', 'accento_spento': '#3b2b30', 'scelta': '#2f4f8f',
       'verde': '#43c06f', 'giallo': '#e2b02a', 'grigio': '#646b77', 'registro': '#0f1115', 'stato': '#101216',
       'premuto': '#2f6b45', 'avviso': '#ff6b6b'}


def applica_tema(root) -> None:
    """Tema scuro della finestra: ttk "clam" con i nostri colori. Se "clam" non c'e' resta il tema di sistema."""
    st = ttk.Style(root)
    try:
        st.theme_use('clam')
    except tk.TclError:
        return
    c = COL
    try:
        root.configure(bg=c['fondo'])
        for k, v in (('background', c['campo']), ('foreground', c['testo']), ('selectBackground', c['scelta']),
                     ('selectForeground', '#ffffff')):
            root.option_add(f'*TCombobox*Listbox.{k}', v)
    except tk.TclError:
        pass
    st.configure('.', background=c['fondo'], foreground=c['testo'], fieldbackground=c['campo'], bordercolor=c['bordo'],
                 lightcolor=c['fondo'], darkcolor=c['fondo'], troughcolor=c['campo'], selectbackground=c['scelta'],
                 selectforeground='#ffffff', insertcolor=c['testo'], focuscolor=c['bordo'], arrowcolor=c['testo2'],
                 font=(CARATTERE, 10))
    st.map('.', foreground=[('disabled', c['testo3'])])
    try:    # caselle di testo e menu a tendina con lo stesso carattere delle scritte
        import tkinter.font as tkfont
        tkfont.nametofont('TkTextFont').configure(family=CARATTERE, size=10)
        for nome in ('TkDefaultFont', 'TkHeadingFont'):      # elenchi e intestazioni delle colonne
            tkfont.nametofont(nome).configure(family=CARATTERE)
        root.option_add('*TCombobox*Listbox.font', (CARATTERE, 10))
    except Exception:  # noqa: BLE001
        pass
    st.configure('TLabel', background=c['fondo'], foreground=c['testo'])
    st.configure('Nota.TLabel', foreground=c['testo2'])
    st.configure('Sezione.TLabel', foreground=c['testo3'], font=(CARATTERE, 9, 'bold'))
    st.configure('Dato.TLabel', foreground=c['testo'], font=(CARATTERE, 10, 'bold'))
    st.configure('Legenda.TLabel', foreground=c['testo2'], font=(CARATTERE, 9))
    st.configure('Stato.TLabel', background=c['stato'], foreground=c['testo2'], padding=(12, 4))
    st.configure('TButton', background=c['pulsante'], foreground=c['testo'], bordercolor=c['bordo'],
                 lightcolor=c['pulsante'], darkcolor=c['pulsante'], padding=(12, 5), focuscolor=c['pulsante'])
    st.map('TButton', background=[('disabled', c['fondo']), ('pressed', c['bordo']), ('active', c['pulsante2'])],
           lightcolor=[('disabled', c['fondo']), ('active', c['pulsante2'])],
           darkcolor=[('disabled', c['fondo']), ('active', c['pulsante2'])],
           foreground=[('disabled', c['testo3'])])
    st.configure('Accento.TButton', background=c['accento'], foreground='#ffffff', bordercolor=c['accento'],
                 lightcolor=c['accento'], darkcolor=c['accento'], focuscolor=c['accento'], font=(CARATTERE, 10, 'bold'))
    st.map('Accento.TButton', background=[('disabled', c['accento_spento']), ('pressed', c['accento3']),
                                          ('active', c['accento2'])],
           lightcolor=[('disabled', c['accento_spento']), ('active', c['accento2'])],
           darkcolor=[('disabled', c['accento_spento']), ('active', c['accento2'])],
           bordercolor=[('disabled', c['accento_spento'])], foreground=[('disabled', '#8c7479')])
    for w in ('TCheckbutton', 'TRadiobutton'):
        st.configure(w, background=c['fondo'], foreground=c['testo'], indicatorbackground=c['campo'],
                     indicatorforeground='#ffffff', upperbordercolor=c['bordo'], lowerbordercolor=c['bordo'],
                     focuscolor=c['fondo'], padding=(2, 3))
        st.map(w, background=[('active', c['fondo'])], foreground=[('disabled', c['testo3'])],
               indicatorbackground=[('selected', c['accento']), ('active', c['pulsante2'])])
    try:    # frecce dei menu a tendina e delle barre grandi quanto il carattere (Windows al 125-150%)
        freccia = int(round(14 * max(1.0, root.winfo_fpixels('1i') / 96.0)))
    except (tk.TclError, ValueError, TypeError):
        freccia = 14
    st.configure('TCombobox', fieldbackground=c['campo'], background=c['pulsante'], foreground=c['testo'],
                 arrowcolor=c['testo2'], bordercolor=c['bordo'], lightcolor=c['campo'], darkcolor=c['campo'],
                 padding=(6, 3), arrowsize=freccia)
    st.map('TCombobox', fieldbackground=[('readonly', c['campo']), ('disabled', c['fondo'])],
           foreground=[('readonly', c['testo']), ('disabled', c['testo3'])],
           selectbackground=[('readonly', c['campo'])], selectforeground=[('readonly', c['testo'])],
           background=[('active', c['pulsante2'])], arrowcolor=[('active', '#ffffff')])
    for w in ('TSpinbox', 'TEntry'):
        st.configure(w, fieldbackground=c['campo'], background=c['pulsante'], foreground=c['testo'],
                     arrowcolor=c['testo2'], bordercolor=c['bordo'], lightcolor=c['campo'], darkcolor=c['campo'])
    st.configure('TNotebook', background=c['fondo'], bordercolor=c['bordo'], lightcolor=c['fondo'],
                 darkcolor=c['fondo'], tabmargins=(0, 0, 0, 0))
    st.configure('TNotebook.Tab', background=c['fondo'], foreground=c['testo2'], bordercolor=c['fondo'],
                 lightcolor=c['fondo'], darkcolor=c['fondo'], padding=(18, 7), font=(CARATTERE, 10, 'bold'))
    st.map('TNotebook.Tab', background=[('selected', c['pulsante']), ('active', c['lista'])],
           foreground=[('selected', '#ffffff'), ('active', c['testo'])],
           lightcolor=[('selected', c['accento'])], bordercolor=[('selected', c['pulsante'])])
    st.configure('TLabelframe', background=c['fondo'], bordercolor=c['bordo'], lightcolor=c['fondo'],
                 darkcolor=c['fondo'], relief='solid', borderwidth=1)
    st.configure('TLabelframe.Label', background=c['fondo'], foreground=c['testo2'], font=(CARATTERE, 10, 'bold'))
    st.configure('Treeview', background=c['lista'], fieldbackground=c['lista'], foreground=c['testo'],
                 bordercolor=c['bordo'], lightcolor=c['lista'], darkcolor=c['lista'])
    st.map('Treeview', background=[('selected', c['scelta'])], foreground=[('selected', '#ffffff')])
    st.configure('Treeview.Heading', background=c['pulsante'], foreground=c['testo2'], bordercolor=c['bordo'],
                 lightcolor=c['pulsante'], darkcolor=c['pulsante'], relief='flat')
    st.map('Treeview.Heading', background=[('active', c['pulsante2'])])
    st.configure('Versioni.Treeview', font=(CARATTERE, 11), borderwidth=0)
    st.configure('Horizontal.TScale', background=c['pulsante2'], troughcolor=c['campo'], bordercolor=c['bordo'],
                 lightcolor=c['pulsante2'], darkcolor=c['pulsante2'])
    st.map('Horizontal.TScale', background=[('active', '#3d4860')])
    tema_disegnato(root, st)
    for w in ('Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        st.configure(w, background=c['pulsante'], troughcolor=c['registro'], bordercolor=c['registro'],
                     lightcolor=c['pulsante'], darkcolor=c['pulsante'], arrowcolor=c['testo2'], gripcount=0,
                     arrowsize=freccia)
        st.map(w, background=[('active', c['pulsante2'])])
    st.configure('TSeparator', background=c['bordo'])
    st.configure('Pagine.TNotebook', background=c['fondo'], borderwidth=0, bordercolor=c['fondo'],
                 lightcolor=c['fondo'], darkcolor=c['fondo'], tabmargins=(0, 0, 0, 0))
    try:
        st.layout('Pagine.TNotebook.Tab', [])       # niente linguette: le pagine si scelgono dalla barra in alto
    except tk.TclError:
        pass


def tema_disegnato(root, st) -> None:
    """Caselle di spunta, pallini di scelta e cursore del volume disegnati da sm2_grafica (come i pulsanti della
    finestra) al posto di quelli di "clam". Le immagini si fanno una volta sola per ogni finestra principale; se
    qualcosa non va restano quelli di "clam"."""
    if getattr(root, '_sm2_tema_disegnato', None) is not None:
        im = root._sm2_tema_disegnato
    else:
        try:
            s = max(1.0, root.winfo_fpixels('1i') / 96.0)
            px = int(round(16 * s))
            sp = max(1, int(round(2 * s)))

            def foto(b):
                return tk.PhotoImage(master=root, data=base64.b64encode(b).decode('ascii'))
            rosso, rosso2, rosso3, bianco = (214, 33, 61, 255), (236, 64, 86, 255), (232, 52, 78, 255), (255, 255, 255, 255)
            vuoto, bordo, vuoto2, bordo2 = (30, 36, 50, 255), (82, 92, 114, 255), (38, 45, 61, 255), (120, 132, 158, 255)
            spento, bordo3, spento2, bordo4 = (22, 26, 36, 255), (43, 50, 67, 255), (70, 40, 48, 255), (90, 52, 60, 255)
            im = {'px': px}
            for nome, fz in (('casella', GR.casella), ('scelta', GR.scelta)):
                im[nome] = foto(fz(px, vuoto, bordo))
                im[nome + '_sopra'] = foto(fz(px, vuoto2, bordo2))
                im[nome + '_si'] = foto(fz(px, rosso, rosso2, bianco))
                im[nome + '_si_sopra'] = foto(fz(px, rosso3, (250, 96, 112, 255), bianco))
                im[nome + '_spenta'] = foto(fz(px, spento, bordo3))
                im[nome + '_si_spenta'] = foto(fz(px, spento2, bordo4, (150, 140, 144, 255)))
            im['cursore'] = foto(GR.cerchio(px, (240, 242, 246, 255), rosso, sp))
            im['cursore_sopra'] = foto(GR.cerchio(px, bianco, (240, 64, 84, 255), sp))
            for nome, el in (('casella', 'Spunta.indicator'), ('scelta', 'Scelta.indicator')):
                st.element_create(el, 'image', im[nome], ('disabled', 'selected', im[nome + '_si_spenta']),
                                  ('disabled', im[nome + '_spenta']), ('active', 'selected', im[nome + '_si_sopra']),
                                  ('selected', im[nome + '_si']), ('active', im[nome + '_sopra']),
                                  width=px + int(round(8 * s)), sticky='w')
            st.element_create('Volume.Horizontal.Scale.slider', 'image', im['cursore'],
                              ('pressed', im['cursore_sopra']), ('active', im['cursore_sopra']))
            root._sm2_tema_disegnato = im           # restano vive finche' c'e' la finestra
        except (tk.TclError, ValueError, TypeError, AttributeError):
            return
    try:
        for w, el in (('Checkbutton', 'Spunta.indicator'), ('Radiobutton', 'Scelta.indicator')):
            st.layout('T' + w, [(w + '.padding', {'sticky': 'nswe', 'children': [
                (el, {'side': 'left', 'sticky': ''}),
                (w + '.focus', {'side': 'left', 'sticky': 'w', 'children': [(w + '.label', {'sticky': 'nswe'})]})]})])
        st.layout('Horizontal.TScale', [('Horizontal.Scale.trough', {'sticky': 'nswe', 'children': [
            ('Volume.Horizontal.Scale.slider', {'side': 'left', 'sticky': ''})]})])
        st.configure('Horizontal.TScale', background=COL['fondo'], troughcolor=COL['campo'], bordercolor=COL['bordo'],
                     lightcolor=COL['campo'], darkcolor=COL['campo'])
    except tk.TclError:
        pass


def area_di_lavoro(root):
    """Lo spazio dello schermo principale senza la barra delle applicazioni: (larghezza, altezza, x, y) in pixel."""
    if os.name == 'nt':
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):   # SPI_GETWORKAREA
                if r.right - r.left > 320 and r.bottom - r.top > 240:
                    return r.right - r.left, r.bottom - r.top, r.left, r.top
        except Exception:  # noqa: BLE001
            pass
    try:
        s = max(1.0, root.winfo_fpixels('1i') / 96.0)
        return int(root.winfo_screenwidth()), int(root.winfo_screenheight()) - int(48 * s), 0, 0
    except (tk.TclError, ValueError, TypeError):
        return 1280, 800, 0, 0


def barra_scura(finestra) -> None:
    """Barra del titolo scura su Windows 10 e 11 (se Windows lo permette; altrimenti resta com'e')."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        finestra.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(finestra.winfo_id())
        v = ctypes.c_int(1)
        for attributo in (20, 19):          # DWMWA_USE_IMMERSIVE_DARK_MODE (20, e 19 nelle versioni piu' vecchie)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attributo, ctypes.byref(v), ctypes.sizeof(v)) == 0:
                break
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------------------- icona e collegamento (6/11/2026)

AUMID = 'EnterElectroRecomp.Launcher'        # il nome del launcher per la barra delle applicazioni di Windows
COLLEGAMENTO = 'EnterElectro-Recomp.lnk'
DESCRIZIONE_COLLEGAMENTO = 'Spider-Man 2: Enter Electro - EnterElectro-Recomp (launcher)'


def _api(dll: str, nome: str, ris, *arg):
    """Una funzione di Windows con i suoi tipi, senza cambiare quelli di ctypes.windll (li usano anche altre parti)."""
    import ctypes
    return ctypes.WINFUNCTYPE(ris, *arg)((nome, ctypes.WinDLL(dll)))


def identita_windows() -> None:
    """Windows: il launcher ha un suo nome per la barra delle applicazioni (AppUserModelID), cosi' la barra mostra
    l'icona del launcher e non quella di Python. Va fatto prima di aprire la finestra; vale solo per questo processo
    (niente registro, niente impostazioni di Windows)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        _api('shell32', 'SetCurrentProcessExplicitAppUserModelID', ctypes.HRESULT, ctypes.c_wchar_p)(AUMID)
    except Exception:  # noqa: BLE001
        pass


def aumid_attuale() -> str:
    """L'AppUserModelID di questo processo (per la prova automatica)."""
    if os.name != 'nt':
        return 'non Windows'
    import ctypes
    try:
        p = ctypes.c_void_p()
        _api('shell32', 'GetCurrentProcessExplicitAppUserModelID', ctypes.HRESULT,
             ctypes.POINTER(ctypes.c_void_p))(ctypes.byref(p))
        v = ctypes.wstring_at(p.value) if p.value else ''
        _api('ole32', 'CoTaskMemFree', None, ctypes.c_void_p)(p)
        return v or '(vuoto)'
    except OSError as e:
        return f'(nessuno: {e})'


def _icona_windows(root, ico: Path) -> str:
    """Le icone di sm2.ico nelle grandezze di Windows per questo schermo (anche con l'ingrandimento): la piccola per la
    barra del titolo, la grande per la barra delle applicazioni e Alt+Tab; sulla finestra e sulla classe delle finestre
    di Tk, cosi' le hanno anche le finestre che si aprono dopo (Filmati, Comandi, PGXP)."""
    import ctypes
    H = ctypes.c_void_p
    metrica = _api('user32', 'GetSystemMetrics', ctypes.c_int, ctypes.c_int)
    carica = _api('user32', 'LoadImageW', H, H, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_int, ctypes.c_int,
                  ctypes.c_uint)
    antenato = _api('user32', 'GetAncestor', H, H, ctypes.c_uint)
    messaggio = _api('user32', 'SendMessageW', H, H, ctypes.c_uint, ctypes.c_size_t, H)
    try:
        classe = _api('user32', 'SetClassLongPtrW', H, H, ctypes.c_int, H)
    except AttributeError:                                  # Python a 32 bit
        classe = _api('user32', 'SetClassLongW', H, H, ctypes.c_int, H)
    piccola, grande = metrica(49), metrica(11)              # SM_CXSMICON, SM_CXICON
    hp = carica(None, str(ico), 1, piccola, piccola, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
    hg = carica(None, str(ico), 1, grande, grande, 0x10)
    if not hp or not hg:
        raise OSError('LoadImageW non riuscito')
    root.update_idletasks()                                 # la cornice della finestra deve esistere
    hwnd = antenato(root.winfo_id(), 2)                     # GA_ROOT
    if not hwnd:
        raise OSError('finestra non trovata')
    messaggio(hwnd, 0x0080, 0, hp)                          # WM_SETICON, ICON_SMALL
    messaggio(hwnd, 0x0080, 1, hg)                          # WM_SETICON, ICON_BIG
    classe(hwnd, -34, hp)                                   # GCLP_HICONSM
    classe(hwnd, -14, hg)                                   # GCLP_HICON
    root._sm2_icone_windows = (hp, hg)                      # restano finche' c'e' il launcher
    return f'sm2.ico {piccola} e {grande} px'


def icona_finestra(root) -> str:
    """L'icona del launcher (tools/grafica/icona_launcher: ragnatela, fulmine e la scritta SM2, disegnata per
    EnterElectro-Recomp) sulla finestra e sulla barra delle applicazioni. Su Windows da sm2.ico; altrove, o se non riesce, con le
    immagini PNG (iconphoto di Tk). Una volta sola per finestra principale; restituisce cosa ha fatto (per il registro
    della prova automatica)."""
    fatta = getattr(root, '_sm2_icona', None)
    if fatta:
        return fatta                        # finestra rifatta in un'altra lingua: l'icona c'e' gia'
    esito, fatto = '', False
    try:
        ico = GR.file_ico() if os.name == 'nt' else None
        if os.name == 'nt' and ico is None:
            esito = 'manca sm2.ico; '
        elif ico is not None:
            try:
                esito, fatto = _icona_windows(root, ico), True
            except Exception as e:  # noqa: BLE001
                esito = f'sm2.ico non usata ({e}); '
        if not fatto:
            imm = [tk.PhotoImage(master=root, file=str(f)) for f in
                   (GR.file_icona_launcher(px) for px in (32, 16, 48, 256)) if f is not None]
            if imm:
                root.iconphoto(True, *imm)
                root._sm2_icone_png = imm
                esito += f'immagini PNG: {len(imm)}'
            else:
                esito += 'nessuna immagine'
    except Exception as e:  # noqa: BLE001    l'icona non deve mai fermare la finestra
        esito += f'icona non messa ({type(e).__name__}: {e})'
    root._sm2_icona = esito
    return esito


def collegamento(radice: Path) -> dict:
    """Scrive (o rifa') EnterElectro-Recomp.lnk nella cartella di EnterElectro-Recomp, con l'icona del launcher: apre SM2-Launcher.cmd con
    cmd.exe (cosi' Windows lascia aggiungerlo alla barra delle applicazioni e a Start), nella cartella di EnterElectro-Recomp, e
    ha lo stesso AppUserModelID della finestra (la finestra aperta va sotto il collegamento aggiunto alla barra). Non lo
    riscrive se e' gia' giusto: lo rifa' solo se manca o se la cartella e' stata spostata. Gira in un processo a parte
    (questo file con --collegamento), perche' usa le interfacce COM di Windows (IShellLinkW, IPersistFile,
    IPropertyStore) con ctypes: un problema li' non puo' fermare la finestra."""
    if os.name != 'nt':
        return {'esito': 'non Windows'}
    ico = GR.file_ico()
    if ico is None:
        return {'esito': 'errore', 'errore': 'manca tools\\grafica\\icona_launcher\\sm2.ico'}
    import ctypes
    lnk = radice / COLLEGAMENTO
    cmd = os.environ.get('ComSpec') or str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32' / 'cmd.exe')
    voluto = {'destinazione': cmd, 'argomenti': '/c SM2-Launcher.cmd', 'cartella': str(radice), 'icona': f'{ico},0',
              'aumid': AUMID}
    HR, P = ctypes.HRESULT, ctypes.c_void_p
    ole32 = ctypes.OleDLL('ole32')

    class GUID(ctypes.Structure):
        _fields_ = [('a', ctypes.c_uint32), ('b', ctypes.c_uint16), ('c', ctypes.c_uint16), ('d', ctypes.c_ubyte * 8)]

    class PKEY(ctypes.Structure):
        _fields_ = [('fmtid', GUID), ('pid', ctypes.c_uint32)]

    class PROPVARIANT(ctypes.Structure):
        _fields_ = [('vt', ctypes.c_ushort), ('r1', ctypes.c_ushort), ('r2', ctypes.c_ushort), ('r3', ctypes.c_ushort),
                    ('p', ctypes.c_void_p), ('p2', ctypes.c_void_p)]

    def guid(s: str) -> GUID:
        g = GUID()
        ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g))
        return g

    def metodo(obj, n: int, *tipi):
        tabella = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        f = ctypes.WINFUNCTYPE(HR, P, *tipi)(tabella[n])
        return lambda *a: f(obj, *a)

    def rilascia(obj) -> None:
        if obj and obj.value:
            tabella = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
            ctypes.WINFUNCTYPE(ctypes.c_ulong, P)(tabella[2])(obj)

    def chiedi(obj, iid: str):
        q = P()
        metodo(obj, 0, ctypes.POINTER(GUID), ctypes.POINTER(P))(ctypes.byref(guid(iid)), ctypes.byref(q))
        return q

    def nuovo():
        q = P()
        ole32.CoCreateInstance(ctypes.byref(guid('{00021401-0000-0000-C000-000000000046}')), None, 1,    # ShellLink
                               ctypes.byref(guid('{000214F9-0000-0000-C000-000000000046}')), ctypes.byref(q))  # IShellLinkW
        return q
    IID_FILE = '{0000010B-0000-0000-C000-000000000046}'          # IPersistFile
    IID_PROP = '{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}'          # IPropertyStore
    chiave = PKEY(guid('{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}'), 5)  # PKEY_AppUserModel_ID

    def leggi() -> dict:
        sl = nuovo()
        pf = ps = None
        try:
            pf = chiedi(sl, IID_FILE)
            metodo(pf, 5, ctypes.c_wchar_p, ctypes.c_uint32)(str(lnk), 0)                  # Load, STGM_READ
            buf = ctypes.create_unicode_buffer(2048)
            n = ctypes.c_int()
            metodo(sl, 3, P, ctypes.c_int, P, ctypes.c_uint32)(buf, 2048, None, 4)          # GetPath, SLGP_RAWPATH
            d = {'destinazione': buf.value}
            metodo(sl, 10, P, ctypes.c_int)(buf, 2048)                                     # GetArguments
            d['argomenti'] = buf.value
            metodo(sl, 8, P, ctypes.c_int)(buf, 2048)                                      # GetWorkingDirectory
            d['cartella'] = buf.value
            metodo(sl, 16, P, ctypes.c_int, ctypes.POINTER(ctypes.c_int))(buf, 2048, ctypes.byref(n))  # GetIconLocation
            d['icona'] = f'{buf.value},{n.value}'
            ps = chiedi(sl, IID_PROP)
            pv = PROPVARIANT()
            metodo(ps, 5, ctypes.POINTER(PKEY), ctypes.POINTER(PROPVARIANT))(ctypes.byref(chiave), ctypes.byref(pv))
            d['aumid'] = ctypes.wstring_at(pv.p) if pv.vt == 31 and pv.p else ''          # VT_LPWSTR
            ole32.PropVariantClear(ctypes.byref(pv))
            return d
        finally:
            rilascia(ps)
            rilascia(pf)
            rilascia(sl)

    def scrivi() -> None:
        sl = nuovo()
        pf = ps = None
        try:
            metodo(sl, 20, ctypes.c_wchar_p)(voluto['destinazione'])                       # SetPath
            metodo(sl, 11, ctypes.c_wchar_p)(voluto['argomenti'])                          # SetArguments
            metodo(sl, 9, ctypes.c_wchar_p)(voluto['cartella'])                            # SetWorkingDirectory
            metodo(sl, 17, ctypes.c_wchar_p, ctypes.c_int)(str(ico), 0)                    # SetIconLocation
            metodo(sl, 7, ctypes.c_wchar_p)(DESCRIZIONE_COLLEGAMENTO)                      # SetDescription
            ps = chiedi(sl, IID_PROP)
            testo = ctypes.create_unicode_buffer(AUMID)
            pv = PROPVARIANT()
            pv.vt, pv.p = 31, ctypes.cast(testo, ctypes.c_void_p).value
            metodo(ps, 6, ctypes.POINTER(PKEY), ctypes.POINTER(PROPVARIANT))(ctypes.byref(chiave), ctypes.byref(pv))
            metodo(ps, 7)()                                                                # Commit
            pf = chiedi(sl, IID_FILE)
            metodo(pf, 6, ctypes.c_wchar_p, ctypes.c_int)(str(lnk), 1)                     # Save
        finally:
            rilascia(ps)
            rilascia(pf)
            rilascia(sl)

    def giusto(d: dict) -> list:
        """Le voci del collegamento diverse da quelle volute (percorsi senza maiuscole e con le variabili espanse)."""
        diverse = []
        for k, v in voluto.items():
            x = str(d.get(k) or '')
            if k in ('destinazione', 'cartella', 'icona'):
                uguale = os.path.normcase(os.path.expandvars(x)) == os.path.normcase(v)
            else:
                uguale = x == v
            if not uguale:
                diverse.append(k)
        return diverse
    try:
        ole32.CoInitialize(None)
        esisteva = lnk.exists()
        prima = None
        if esisteva:
            try:
                prima = leggi()
            except OSError as e:
                prima = {'errore': str(e)}
            if not giusto(prima):
                return {'esito': 'uguale', 'percorso': str(lnk), 'letto': prima}
        scrivi()
        dopo = leggi()
        diverse = giusto(dopo)
        if diverse:
            return {'esito': 'errore', 'errore': f'riletto diverso: {diverse}', 'percorso': str(lnk), 'letto': dopo}
        return {'esito': 'aggiornato' if esisteva else 'creato', 'percorso': str(lnk), 'letto': dopo, 'prima': prima}
    except Exception as e:  # noqa: BLE001
        return {'esito': 'errore', 'errore': f'{type(e).__name__}: {e}', 'percorso': str(lnk)}


def chiedi_collegamento() -> dict:
    """Il collegamento con l'icona (collegamento()) in un processo a parte, senza finestra; il suo risultato."""
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--collegamento'], capture_output=True,
                           timeout=60, cwd=str(L.ROOT),
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except (OSError, subprocess.SubprocessError) as e:
        return {'esito': 'errore', 'errore': str(e)}
    righe = (p.stdout or b'').decode('utf-8', 'replace').strip().splitlines()
    try:
        return json.loads(righe[-1])
    except (ValueError, IndexError):
        return {'esito': 'errore', 'errore': f'codice {p.returncode}: ' +
                (p.stderr or b'').decode('utf-8', 'replace')[-300:].strip()}


def collegamento_in_fondo(f) -> None:
    """All'apertura della finestra: il collegamento con l'icona senza fermare la finestra; una riga nel registro solo
    se l'ha creato o rifatto (o se non ci e' riuscito)."""
    if os.name != 'nt':
        return

    def lavoro():
        d = chiedi_collegamento()
        e = d.get('esito')
        if e == 'creato':
            testo = T(f'Nella cartella {L.ROOT} c\'e\' adesso il collegamento "EnterElectro-Recomp" con l\'icona del launcher: lo '
                      'apre come SM2-Launcher.cmd e si puo\' copiare sul desktop o aggiungere alla barra delle '
                      'applicazioni.',
                      f'The folder {L.ROOT} now has the "EnterElectro-Recomp" shortcut with the launcher icon: it opens the '
                      'launcher like SM2-Launcher.cmd and can be copied to the desktop or pinned to the taskbar.')
        elif e == 'aggiornato':
            testo = T('Collegamento "EnterElectro-Recomp" rifatto per questa cartella.',
                      'The "EnterElectro-Recomp" shortcut was updated for this folder.')
        elif e in ('uguale', 'non Windows'):
            return
        else:
            testo = T(f'Collegamento "EnterElectro-Recomp" non creato: {d.get("errore") or e}',
                      f'"EnterElectro-Recomp" shortcut not created: {d.get("errore") or e}')
        f.coda.put(('riga', testo))
    threading.Thread(target=lavoro, daemon=True).start()


COL_ROSSO = (214, 33, 61)          # pulsante principale, versione scelta
COL_GIALLO = (222, 255, 74)        # pagina scelta nella barra in alto (giallo "elettrico")


def sigla_regione(prof: str) -> str:
    """La sigla nel distintivo della versione: US, EU, FR, DE, JP."""
    if prof.startswith('SLUS'):
        return 'US'
    if prof.startswith('SLPM'):
        return 'JP'
    return {'SLES-03624': 'FR', 'SLES-03625': 'DE'}.get(prof[:10], 'EU')


def nome_breve(nome: str) -> str:
    """Il nome della versione per l'elenco: senza la spiegazione tra parentesi ("originale, prima dell'11 settembre"
    diventa "originale")."""
    if ' (' not in nome:
        return nome
    base, resto = nome.split(' (', 1)
    for parola in ('originale', 'original'):
        if parola in resto.lower():
            return f'{base} {parola}'
    return base


def accorcia(testo: str, larghezza: int, carattere) -> str:
    """Il testo, con i puntini in fondo se non ci sta nella larghezza (in pixel) con quel carattere."""
    try:
        import tkinter.font as tkfont
        f = tkfont.Font(family=carattere[0], size=carattere[1], weight='bold' if 'bold' in carattere else 'normal')
        if f.measure(testo) <= larghezza:
            return testo
        while testo and f.measure(testo + '...') > larghezza:
            testo = testo[:-1]
        return testo.rstrip() + '...'
    except Exception:  # noqa: BLE001
        return testo


class SuggerimentoTela:
    """La spiegazione degli elementi disegnati sulla tela (come Suggerimento per i widget): una sola per tutta la
    tela, mostrata dopo un attimo con il mouse fermo su un elemento che ne ha una."""

    def __init__(self, canvas, ritardo: int = 600):
        self.c, self.ritardo = canvas, ritardo
        self.testo = ''
        self._xy = (0, 0)
        self._id, self._tip = None, None

    def entra(self, testo: str, evento=None) -> None:
        self.nascondi()
        self.testo = testo
        self._xy = (getattr(evento, 'x_root', 0), getattr(evento, 'y_root', 0))
        self._id = self.c.after(self.ritardo, self._mostra)

    def nascondi(self, _evento=None) -> None:
        if self._id is not None:
            try:
                self.c.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None

    def mostra_ora(self, testo: str, x_root: int, y_root: int) -> None:
        """Per la prova automatica: la spiegazione subito, come se il mouse fosse in (x_root, y_root)."""
        self.nascondi()
        self.testo, self._xy = testo, (x_root, y_root)
        self._mostra()

    def _mostra(self):
        self._id = None
        try:
            scala = max(1.0, self.c.winfo_fpixels('1i') / 96.0)
            tip = tk.Toplevel(self.c)
            tip.wm_overrideredirect(True)
            try:
                tip.attributes('-topmost', True)
            except tk.TclError:
                pass
            tk.Label(tip, text=self.testo, justify='left', background='#262b33', foreground=COL['testo'],
                     relief='flat', borderwidth=0, highlightthickness=1, highlightbackground=COL['bordo'],
                     wraplength=int(430 * scala), padx=10, pady=7, font=(CARATTERE, 9)).pack()
            tip.update_idletasks()
            x, y = self._xy[0] + 14, self._xy[1] + 20
            larg, alt = tip.winfo_width(), tip.winfo_height()
            x = max(0, min(x, tip.winfo_screenwidth() - larg - 8))
            if y + alt > tip.winfo_screenheight() - 40:
                y = max(0, self._xy[1] - alt - 10)
            tip.wm_geometry(f'+{x}+{y}')
            self._tip = tip
        except tk.TclError:
            self._tip = None


def ppm_sfumato(w: int, h: int) -> bytes:
    """Immagine PPM per l'immagine in cima senza filmati migliorati: dal quasi nero a sinistra (dove c'e' il titolo) a
    un rosso scuro a destra, un po' piu' scura in basso."""
    a, b = (16, 18, 23), (78, 20, 33)
    riga = bytearray()
    for i in range(w):
        t = i / max(1, w - 1)
        t = t * t * (3 - 2 * t)
        riga += bytes(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
    riga = bytes(riga)
    righe = []
    for y in range(h):
        f = 1.0 - 0.35 * (y / max(1, h - 1)) ** 1.5
        righe.append(riga.translate(bytes(min(255, int(v * f)) for v in range(256))))
    return b'P6 %d %d 255\n' % (w, h) + b''.join(righe)


def pallino(colore: str, d: int):
    """Pallino colorato d x d (fuori dal cerchio l'immagine e' trasparente) per l'elenco delle versioni."""
    img = tk.PhotoImage(width=d, height=d)
    r = d / 2.0
    for y in range(d):
        dy = y + 0.5 - r
        if abs(dy) >= r:
            continue
        mezza = (r * r - dy * dy) ** 0.5
        x0, x1 = int(round(r - mezza)), int(round(r + mezza))
        if x1 > x0:
            img.put(colore, to=(x0, y, x1, y + 1))
    return img


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
        tk.Label(tip, text=self.testo, justify='left', background='#262b33', foreground=COL['testo'], relief='flat',
                 borderwidth=0, highlightthickness=1, highlightbackground=COL['bordo'],
                 wraplength=int(430 * scala), padx=10, pady=7, font=(CARATTERE, 9)).pack()
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
    try:
        motore = L.impronta_motore()
    except OSError:
        motore = None
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
        chip = []
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
                # pastiglie sotto il nome nella finestra (0.12)
                chip = [x for x in ('PGO' if st.get('pgo') else '', 'PGXP' if st.get('pgxp') else '',
                                    T('Filmati migliorati', 'Enhanced movies') if L.filmati_hd_pronti(cartella, st)
                                    else '',
                                    T('Filmati IA', 'AI movies') if filmati_ia_pronti(cartella, st) else '',
                                    T('Salto delle attese', 'Idle skip') if L.attese_accese(cartella / 'game.toml')
                                    else '') if x]
                if st.get('distanza') and not (st.get('bordi_widescreen') and st.get('area_pacchetti')
                                               and st.get('gioco_widescreen') and st.get('piani_widescreen')):
                    # fatta prima della v0.8 / v0.9 / v0.9.1 / v0.11
                    istato += T(' (aggiornabile: premi Installa)', ' (can be updated: press Install)')
                elif not m3.get('attiva'):
                    istato += T(' (senza moduli in anticipo)', ' (without precompiled modules)')
                if motore is not None and not L.motore_uguale(st, motore):
                    istato += T(' (versione precedente: reinstalla per le novit\u00e0, i salvataggi restano)',
                                ' (earlier version: install again for the new features, the saves stay)')
            else:
                istato = T('incompleta', 'incomplete')
        out.append({'profilo': prof, 'nome': nome_versione(prof, v['nome']), 'lingua': lingua_gioco(v.get('lingua', '')),
                    'video': v.get('video', ''), 'disco': dstato, 'installazione': istato, 'ha_disco': bool(disco),
                    'pronta': pronta, 'extra': chip})
    cache.salva()
    return out


def filmati_ia_pronti(cartella: Path, st: dict) -> bool:
    """Almeno un modello di filmati IA (0.12) pronto per questa installazione."""
    try:
        ia = L._ia()
        return any(ia.pronti(cartella, st, m) for m in L.MODELLI_IA)
    except Exception:  # noqa: BLE001
        return False


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
        filmati = valore(L.MOD_FILTRI, 'fmv_filtering', 'default')
        try:
            inst = json.loads((L.GIOCHI / prof / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            inst = {}
        video = L.leggi_video(path.parent.parent / 'settings.toml')
        sinc = {v: k for k, v in L.SINCRONIA.items()}.get(str(video.get('vsync', 'on')), 'accesa')
        fs = video.get('fullscreen', 0)
        schermo = {v: k for k, v in L.SCHERMO.items()}.get(int(fs) if isinstance(fs, (bool, int)) else 0, 'finestra')
        larg = video.get('window_width', 0)
        vol = inst.get('volume', 100)
        return {'risoluzione': valore(L.MOD_RISOLUZIONE, 'resolution', 'gioco'),
                'filtro': 'gioco' if filtro == 'default' else filtro,
                'filmati': inst.get('filmati') if inst.get('filmati') in ('migliorati',) + L.FILMATI_IA else (
                    'originali' if filmati in ('default', 'nearest') else 'filtro'),
                'widescreen': {v: k for k, v in L.ASPETTO_WIDESCREEN.items()}.get(
                    valore(L.MOD_WIDESCREEN, 'aspect', 'no'), valore(L.MOD_WIDESCREEN, 'aspect', 'no')),
                'pgxp': bool(voce(L.MOD_PGXP).get('enabled')),
                'pgxp_opz': L.leggi_pgxp(L.GIOCHI / prof),
                'distanza': bool(voce(L.MOD_DISTANZA).get('enabled')),
                'attese': L.attese_accese(L.GIOCHI / prof / 'game.toml'),
                'sincronia': sinc, 'thread': bool(video.get('render_thread')), 'schermo': schermo,
                'larghezza': larg if isinstance(larg, int) else 0,
                'latenza': video.get('low_latency_input') is not False,
                'fluido': bool(video.get('frame_generation')),
                'volume': vol if isinstance(vol, int) and 0 <= vol <= 100 else 100}
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
        self.scala = s = scala
        aw, ah, ax, ay = area_di_lavoro(root)
        larg = min(int(1280 * s), aw - int(24 * s))         # mai piu' grande dello schermo (portatili al 150%)
        alt = min(int(820 * s), ah - int(40 * s))           # 40: la barra del titolo della finestra
        root.geometry(f'{larg}x{alt}+{ax + max(0, (aw - larg) // 2)}+{ay + max(0, (ah - alt - int(32 * s)) // 2)}')
        root.minsize(min(int(1000 * s), larg), min(int(600 * s), alt))
        applica_tema(root)
        try:    # righe degli elenchi alte quanto il carattere (con l'ingrandimento di Windows erano tagliate)
            import tkinter.font as tkfont
            alto = tkfont.nametofont('TkDefaultFont').metrics('linespace')
            ttk.Style(root).configure('Treeview', rowheight=int(alto * 1.3) + 2)
        except Exception:  # noqa: BLE001
            pass
        self._img = {}             # immagini disegnate (chiave -> PhotoImage), tenute vive finche' c'e' la finestra
        self._pallini = {}
        self.dati = {}
        self.passi = []
        self._sopra = None         # elemento della tela sotto il mouse
        self.pagina = 0            # 0 Gioco, 1 Opzioni, 2 Salvataggi, 3 Registro
        self._dim_disegno = None
        self._id_disegno = None
        self._ultima_riga = ''
        self._varianti = {}
        self._attivi = {}          # gruppi di elementi cliccabili della tela: tag -> (comando, spiegazione)
        self._legati = set()       # gruppi gia' legati al mouse
        self._principale = (T('GIOCA', 'PLAY'), None, False, 'gioca')
        self._azioni = {}
        self.lavoro_filmati = None   # (profilo, 'migliorati' o modello IA) mentre si preparano i filmati
        self.avanzamento = None      # (fatti, totale, secondi rimasti) dalle righe AVANZAMENTO
        self.finestra_filmati = None

        # una sola tela per tutta la finestra: immagine di fondo, barra in alto, versioni, titolo e pulsanti disegnati
        c = self.tela = self.c_sfondo = tk.Canvas(root, highlightthickness=0, bd=0, bg=COL['notte'])
        c.pack(fill='both', expand=True)
        self.cima = c
        self._sugg_tela = SuggerimentoTela(c)
        self.img_sfondo = None     # il fotogramma dei filmati migliorati, se c'e'
        self._img_fondo = None     # l'immagine di fondo mostrata
        self._sfondo_di = None
        self._con_sfondo = False
        self._id_rifai = None

        # cose che la finestra non mostra: l'elenco delle versioni e i pulsanti restano come "modello" (stato, scelta,
        # spiegazioni) per la logica di sempre e per le prove automatiche; quello che si vede e' disegnato sulla tela
        nascosti = ttk.Frame(root)
        self.albero = ttk.Treeview(nascosti, show='tree', selectmode='browse', height=7)
        self.albero.bind('<<TreeviewSelect>>', lambda e: self.versione_scelta())
        self.b_disco = ttk.Button(nascosti, text=T('Aggiungi un disco...', 'Add a disc...'), command=self.aggiungi_disco)
        self.b_aggiorna = ttk.Button(nascosti, text=T('Aggiorna', 'Refresh'), command=self.aggiorna)
        self.b_installa = ttk.Button(nascosti, text=T('Installa', 'Install'), command=self.installa)
        self.b_gioca = ttk.Button(nascosti, text=T('Gioca', 'Play'), command=self.gioca)
        self.b_filmati = ttk.Button(nascosti, text=T('Filmati...', 'Movies...'), command=self.apri_filmati)
        self.b_comandi = ttk.Button(nascosti, text=T('Comandi...', 'Controls...'), command=self.comandi)
        self.b_cartella = ttk.Button(nascosti, text=T('Apri la cartella', 'Open folder'), command=self.apri_cartella)
        self.b_precedente = ttk.Button(nascosti, text=T('Prendi da una versione precedente...',
                                                        'Import from an earlier version...'),
                                       command=self.prendi_precedente)
        self.b_consigliate = ttk.Button(nascosti, text=T('Impostazioni per PC lenti',
                                                         'Recommended settings for slow PCs'),
                                        command=self.consigliate_pc_lenti)
        for b, chiave in ((self.b_disco, 'disco'), (self.b_installa, 'installa'), (self.b_gioca, 'gioca'),
                          (self.b_cartella, 'cartella'), (self.b_aggiorna, 'aggiorna'),
                          (self.b_filmati, 'prepara_filmati'), (self.b_comandi, 'comandi'),
                          (self.b_consigliate, 'consigliate'), (self.b_precedente, 'precedente')):
            Suggerimento(b, SUGG[chiave])
        self._opzioni_di = None

        # lingua in alto a destra
        self.lingua = tk.StringVar(value=etichetta_di(LINGUE, lingua(), 'Italiano'))
        self.cb_lingua = ttk.Combobox(c, textvariable=self.lingua, values=[e for e, _ in LINGUE], state='readonly',
                                      width=10)
        self.cb_lingua.bind('<<ComboboxSelected>>', self.cambia_lingua)
        Suggerimento(self.cb_lingua, SUGG['lingua'])
        self._id_lingua = c.create_window(0, 0, window=self.cb_lingua, anchor='e')

        # pagine Opzioni, Salvataggi e Registro: dentro un pannello scuro sulla tela, scelte dalla barra in alto (il
        # Notebook resta, senza linguette, come prima per la logica e le prove automatiche)
        self.pannello_pagine = ttk.Frame(c)
        self.schede = ttk.Notebook(self.pannello_pagine, style='Pagine.TNotebook')
        self.schede.pack(fill='both', expand=True)
        t_gioco = ttk.Frame(self.schede)
        t_opzioni = ttk.Frame(self.schede, padding=(int(6 * s), int(6 * s)))
        t_salv = ttk.Frame(self.schede, padding=(int(6 * s), int(6 * s)))
        t_reg = ttk.Frame(self.schede)
        self.schede.add(t_gioco, text=T('Gioco', 'Game'))
        self.schede.add(t_opzioni, text=T('Opzioni', 'Options'))
        self.schede.add(t_salv, text=T('Salvataggi', 'Saves'))
        self.schede.add(t_reg, text=T('Registro', 'Log'))
        self.t_salv, self.t_registro = t_salv, t_reg
        self.salvataggi = None
        self.schede.bind('<<NotebookTabChanged>>', lambda e: self.scheda_cambiata())
        self._id_pagine = c.create_window(0, 0, window=self.pannello_pagine, anchor='nw', state='hidden')

        # pagina Opzioni: per argomento, in due colonne
        def etichetta(dove, testo, chiave, riga, col, **kw):
            e = ttk.Label(dove, text=testo)
            e.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(e, SUGG[chiave])
            return e

        def spunta(dove, testo, var, chiave, riga, col, **kw):
            cc = ttk.Checkbutton(dove, text=testo, variable=var)
            cc.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(cc, SUGG[chiave])
            return cc

        def scelta(dove, var, tabella, chiave, larg, riga, col, **kw):
            cb = ttk.Combobox(dove, textvariable=var, values=[r[0] for r in tabella], state='readonly', width=larg)
            cb.grid(row=riga, column=col, sticky='w', **kw)
            Suggerimento(cb, SUGG[chiave])
            return cb

        t_opzioni.columnconfigure(0, weight=1, uniform='opz')
        t_opzioni.columnconfigure(1, weight=1, uniform='opz')
        sx = ttk.Frame(t_opzioni)
        sx.grid(row=0, column=0, sticky='nsew', padx=(0, int(10 * s)))
        dx = ttk.Frame(t_opzioni)
        dx.grid(row=0, column=1, sticky='nsew')
        pad = (int(12 * s), int(8 * s))
        sp = (int(10 * s), 0)
        gr = ttk.LabelFrame(sx, text=T('Grafica', 'Graphics'), padding=pad)
        gr.pack(fill='x')
        etichetta(gr, T('Risoluzione interna', 'Internal resolution'), 'ris', 0, 0)
        self.ris = tk.StringVar(value=etichetta_di(RIS, 'gioco'))
        self.cb_ris = scelta(gr, self.ris, RIS, 'ris', 18, 0, 1, padx=sp, pady=2)
        etichetta(gr, T('Filtro delle texture', 'Texture filter'), 'filtro', 1, 0)
        self.filtro = tk.StringVar(value=etichetta_di(FILTRI, 'gioco'))
        self.cb_filtro = scelta(gr, self.filtro, FILTRI, 'filtro', 18, 1, 1, padx=sp, pady=2)
        etichetta(gr, 'Widescreen', 'wide', 2, 0)
        self.wide = tk.StringVar(value=etichetta_di(WIDE, 'no'))
        self.cb_wide = scelta(gr, self.wide, WIDE, 'wide', 18, 2, 1, padx=sp, pady=2)
        self.pgxp = tk.BooleanVar(value=False)
        self.pgxp_opz = L.pgxp_predefiniti()       # le voci di "Opzioni PGXP..." (0.12, come in DuckStation)
        spunta(gr, T('PGXP (geometria precisa)', 'PGXP (precise geometry)'), self.pgxp, 'pgxp', 3, 0, pady=(6, 0))
        self.b_pgxp = ttk.Button(gr, text=T('Opzioni PGXP...', 'PGXP options...'), command=self.apri_pgxp)
        self.b_pgxp.grid(row=3, column=1, sticky='w', padx=sp, pady=(6, 0))
        Suggerimento(self.b_pgxp, SUGG['pgxp_finestra'])
        self.distanza = tk.BooleanVar(value=False)
        spunta(gr, T('Distanza visiva estesa (sperimentale)', 'Extended draw distance (experimental)'), self.distanza,
               'distanza', 4, 0, columnspan=2)
        fm = ttk.LabelFrame(sx, text=T('Filmati', 'Movies'), padding=pad)
        fm.pack(fill='x', pady=(int(10 * s), 0))
        etichetta(fm, T('Filmati', 'Movies'), 'filmati', 0, 0)
        self.filmati = tk.StringVar(value=etichetta_di(FILMATI, 'originali'))
        self.cb_filmati = scelta(fm, self.filmati, FILMATI, 'filmati', 20, 0, 1, padx=sp, pady=2)
        au = ttk.LabelFrame(sx, text='Audio', padding=pad)     # 0.12: volume all'avvio
        au.pack(fill='x', pady=(int(10 * s), 0))
        etichetta(au, T("Volume all'avvio", 'Volume at start'), 'volume', 0, 0)
        self.volume = tk.IntVar(value=100)
        self.l_volume = ttk.Label(au, text='100%', width=5)

        def mostra_volume(*_a):
            try:
                self.l_volume.configure(text=f'{self.volume_scelto()}%')
            except (tk.TclError, ValueError):
                pass
        self.sc_volume = ttk.Scale(au, from_=0, to=100, orient='horizontal', variable=self.volume,
                                   length=int(170 * s), command=mostra_volume)
        self.sc_volume.grid(row=0, column=1, sticky='w', padx=sp)
        Suggerimento(self.sc_volume, SUGG['volume'])
        self.l_volume.grid(row=0, column=2, sticky='w', padx=(8, 0))
        self.volume.trace_add('write', mostra_volume)

        sc = ttk.LabelFrame(dx, text=T('Schermo e prestazioni', 'Display and performance'), padding=pad)
        sc.pack(fill='x')
        etichetta(sc, T('Sincronia verticale', 'Vertical sync'), 'sinc', 0, 0)
        self.sinc = tk.StringVar(value=etichetta_di(SINC, 'accesa'))
        self.cb_sinc = scelta(sc, self.sinc, SINC, 'sinc', 26, 0, 1, padx=sp, pady=2)
        etichetta(sc, T('Schermo', 'Screen'), 'schermo', 1, 0)
        self.schermo = tk.StringVar(value=etichetta_di(SCHERMI, 'finestra'))
        self.cb_schermo = scelta(sc, self.schermo, SCHERMI, 'schermo', 26, 1, 1, padx=sp, pady=2)
        etichetta(sc, T('Larghezza della finestra', 'Window width'), 'larghezza', 2, 0)
        self.larghezza = tk.StringVar(value=etichetta_di(LARGHEZZE, 0))
        self.cb_larghezza = scelta(sc, self.larghezza, LARGHEZZE, 'larghezza', 12, 2, 1, padx=sp, pady=2)
        self.attese = tk.BooleanVar(value=True)
        spunta(sc, T('Salto delle attese (meno lavoro per la CPU)', 'Idle skip (less work for the CPU)'), self.attese,
               'attese', 3, 0, columnspan=2, pady=(6, 0))
        self.thread = tk.BooleanVar(value=False)
        spunta(sc, T('Disegno in un thread separato', 'Render thread'), self.thread, 'thread', 4, 0, columnspan=2)
        self.latenza = tk.BooleanVar(value=True)
        spunta(sc, T('Input a bassa latenza', 'Low-latency input'), self.latenza, 'latenza', 5, 0, columnspan=2)
        self.fluido = tk.BooleanVar(value=False)
        spunta(sc, T('Movimento fluido per schermi a 120 Hz o piu\' (sperimentale)',
                     'Smooth motion for 120 Hz or faster screens (experimental)'), self.fluido, 'fluido', 6, 0,
               columnspan=2)
        ins = ttk.LabelFrame(dx, text=T('Installazione e avvio', 'Installation and start'), padding=pad)
        ins.pack(fill='x', pady=(int(10 * s), 0))
        self.pgo = tk.BooleanVar(value=False)
        spunta(ins, T('Installa con il PGO (circa 15% di CPU in meno)', 'Install with PGO (about 15% less CPU)'),
               self.pgo, 'pgo', 0, 0)
        self.con_launcher = tk.BooleanVar(value=False)
        spunta(ins, T('Impostazioni di psxrecomp prima del gioco', 'psxrecomp settings before the game'),
               self.con_launcher, 'con_launcher', 1, 0)
        altro = ttk.Frame(t_opzioni)
        altro.grid(row=1, column=0, columnspan=2, sticky='w', pady=(int(12 * s), 0))
        b1 = ttk.Button(altro, text=T('Impostazioni per PC lenti', 'Recommended settings for slow PCs'),
                        command=self.consigliate_pc_lenti)
        b1.pack(side='left')
        Suggerimento(b1, SUGG['consigliate'])
        b2 = ttk.Button(altro, text=T('Prendi da una versione precedente...', 'Import from an earlier version...'),
                        command=self.prendi_precedente)
        b2.pack(side='left', padx=(8, 0))
        Suggerimento(b2, SUGG['precedente'])
        tasti = ttk.Label(t_opzioni, text=TASTI_NEL_GIOCO, style='Nota.TLabel', wraplength=int(760 * s),
                          justify='left')
        tasti.grid(row=2, column=0, columnspan=2, sticky='w', pady=(int(12 * s), 0))
        Suggerimento(tasti, SUGG['tasti'])

        # pagina Registro
        self.registro = tk.Text(t_reg, height=10, font=('Consolas', 9), wrap='word', state='disabled',
                                bg=COL['registro'], fg='#cfd3da', insertbackground=COL['testo'],
                                selectbackground=COL['scelta'], relief='flat', borderwidth=0, highlightthickness=0,
                                padx=10, pady=8)
        barra = ttk.Scrollbar(t_reg, orient='vertical', command=self.registro.yview)
        self.registro.configure(yscrollcommand=barra.set)
        barra.pack(side='right', fill='y')
        self.registro.pack(side='left', fill='both', expand=True)
        Suggerimento(self.registro, SUGG['registro'], ritardo=1200)

        self.stato = tk.StringVar(value=self._pronto)
        self.stato.trace_add('write', lambda *_a: self._scrivi_stato())
        if prima:
            self.ripristina_scelte(prima)
        if registro:
            self.scrivi(registro)
        c.bind('<Configure>', lambda e: self._ridimensionata())
        self.aggiorna_pulsanti()
        self.mostra_sfondo()
        self._ridisegna()
        root.after(100, self._svuota_coda)
        root.protocol('WM_DELETE_WINDOW', self.chiudi)
        barra_scura(root)
        self.icona = icona_finestra(root)          # 6/11/2026: ragnatela, fulmine e SM2 (finestra e barra delle applicazioni)
        if self._fmv_str() is None:
            threading.Thread(target=self._prepara_strumento, daemon=True).start()

    # ---------------------------------------------------------------------------- lingua
    def scelte(self) -> dict:
        """Le scelte di adesso con i valori dei comandi (non i testi), per rifare la finestra in un'altra lingua."""
        return {'profilo': self.profilo_scelto() or self._da_scegliere, 'opzioni_di': self._opzioni_di,
                'ris': dict(RIS).get(self.ris.get(), 'gioco'), 'filtro': dict(FILTRI).get(self.filtro.get(), 'gioco'),
                'filmati': dict(FILMATI).get(self.filmati.get(), 'originali'),
                'wide': dict(WIDE).get(self.wide.get(), 'no'), 'sinc': dict(SINC).get(self.sinc.get(), 'accesa'),
                'schermo': dict(SCHERMI).get(self.schermo.get(), 'finestra'),
                'larghezza': dict(LARGHEZZE).get(self.larghezza.get(), 0),
                **{k: getattr(self, k).get() for k in ('pgxp', 'distanza', 'con_launcher', 'attese', 'pgo', 'thread',
                                                       'latenza', 'fluido')}, 'volume': self.volume_scelto(),
                'pgxp_opz': dict(self.pgxp_opz)}

    def volume_scelto(self) -> int:
        """Il volume all'avvio scelto con il cursore (0-100)."""
        try:
            v = float(self.volume.get())
        except (tk.TclError, ValueError, TypeError):
            v = 100.0
        return max(0, min(100, int(round(v))))

    def ripristina_scelte(self, s: dict) -> None:
        self._opzioni_di = s.get('opzioni_di')
        for var, cb, tabella, chiave in ((self.ris, self.cb_ris, RIS, 'ris'), (self.filtro, self.cb_filtro, FILTRI, 'filtro'),
                                         (self.filmati, self.cb_filmati, FILMATI, 'filmati'),
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
        if isinstance(s.get('volume'), int):
            self.volume.set(max(0, min(100, s['volume'])))
        if isinstance(s.get('pgxp_opz'), dict):
            self.pgxp_opz = dict(L.pgxp_predefiniti(), **s['pgxp_opz'])

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
        if self.proc is not None:                      # l'ultima riga del comando, sotto il pulsante principale
            riga = next((x.strip() for x in reversed(testo.splitlines()) if x.strip()), '')
            if riga:
                self._ultima_riga = riga if len(riga) <= 90 else riga[:87] + '...'
                try:
                    self.tela.itemconfigure('didascalia', text=self._ultima_riga)
                except tk.TclError:
                    pass

    def _svuota_coda(self) -> None:
        if not self.vivo:
            return              # finestra rifatta in un'altra lingua: ci pensa quella nuova
        try:
            while True:
                tipo, dato = self.coda.get_nowait()
                if tipo == 'riga':
                    if dato.startswith('AVANZAMENTO '):
                        self._avanzamento(dato)
                        continue
                    self.scrivi(dato)
                elif tipo == 'fine':
                    cmd, codice = dato
                    self.proc = None
                    self.avanzamento = None
                    self.lavoro_filmati = None
                    nome = nome_comando(cmd)
                    if cmd == 'prepara-filmati-ia' and codice == 2:
                        self.stato.set(T('Preparazione dei filmati IA fermata: con "Riprendi" continua da dove era.',
                                         'Preparation of the AI movies stopped: "Resume" continues where it was.'))
                    else:
                        self.stato.set(T(f'"{nome}" finito ' + ('bene.' if codice == 0 else f'con errore (codice {codice}).'),
                                         f'"{nome}" finished ' + ('successfully.' if codice == 0
                                                                  else f'with an error (code {codice}).')))
                    poi, self._poi = getattr(self, '_poi', None), None
                    if poi and codice == 0:
                        poi()
                    else:
                        self.aggiorna()
                    if cmd == 'salvataggi' and self.salvataggi is not None:
                        self.salvataggi.aggiorna(self.profilo_scelto())
                elif tipo == 'righe':
                    self._mostra_righe(dato)
                elif tipo == 'sfondo':                     # fmv_str pronto: immagine di fondo su misura
                    self._sfondo_di = None
                    self.mostra_sfondo()
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
            self.albero.insert('', 'end', iid=r['profilo'], text=r['nome'])
        if scelto and self.albero.exists(scelto):
            self.albero.selection_set(scelto)
        elif righe:
            primo = next((r['profilo'] for r in righe if r['ha_disco']), righe[0]['profilo'])
            self.albero.selection_set(primo)
        if self.proc is None:
            self.stato.set(self._msg_dopo)
        self.versione_scelta()

    def scheda_cambiata(self) -> None:
        try:
            i = self.schede.index('current')
        except tk.TclError:
            i = 0
        if isinstance(i, int) and i != self.pagina:
            self.pagina = i
            self._ridisegna()
        if self.schede.index('current') == 2:
            if self.salvataggi is None:
                self.salvataggi = PannelloSalvataggi(self, self.t_salv)
            self.salvataggi.aggiorna(self.profilo_scelto())

    # ---------------------------------------------------------------------------- la tela (0.12)
    def _dim(self):
        c = self.tela
        try:
            W, H = int(c.winfo_width()), int(c.winfo_height())
        except (tk.TclError, ValueError, TypeError):
            W = H = 0
        if W <= 1 or H <= 1:
            W, H = int(1280 * self.scala), int(820 * self.scala)
        return W, H

    def _ridimensionata(self) -> None:
        """La finestra ha cambiato grandezza: si ridisegna dopo un attimo (non a ogni pixel mentre si trascina)."""
        if self._dim() == self._dim_disegno:
            return
        if self._id_disegno is not None:
            try:
                self.root.after_cancel(self._id_disegno)
            except tk.TclError:
                pass
        self._id_disegno = self.root.after(60, self._ridisegna)
        if self._id_rifai is not None:
            try:
                self.root.after_cancel(self._id_rifai)
            except tk.TclError:
                pass
        self._id_rifai = self.root.after(400, self._rifai_fondo)

    def _rifai_fondo(self) -> None:
        self._id_rifai = None
        self.mostra_sfondo()

    def _foto(self, chiave, fabbrica):
        """Immagine disegnata da sm2_grafica (PNG), fatta una volta sola per ogni forma e grandezza."""
        img = self._img.get(chiave)
        if img is None:
            img = tk.PhotoImage(data=base64.b64encode(fabbrica()).decode('ascii'))
            self._img[chiave] = img
        return img

    def _icona(self, nome: str, px: int, spenta: bool = False):
        f = GR.file_icona(nome, px, spenta)
        if f is None:
            return None
        chiave = ('icona', f.name)
        if chiave not in self._img:
            try:
                self._img[chiave] = tk.PhotoImage(file=str(f))
            except tk.TclError:
                return None
        return self._img[chiave]

    def _vetro(self, w: int, h: int, r: int, alfa: int = 150, bordo: int = 26):
        return self._foto(('vetro', w, h, r, alfa, bordo),
                          lambda: GR.rett_tondo(w, h, r, (12, 16, 30, alfa), (255, 255, 255, bordo), 1))

    def _tasto(self, tag: str, comando, testo_sugg: str | None = None) -> None:
        """Rende cliccabile un gruppo di elementi della tela (con la manina e, se c'e', la spiegazione). Il mouse si
        lega una volta sola per ogni gruppo: a ogni disegno cambiano solo il comando e la spiegazione (in _attivi)."""
        self._attivi[tag] = (comando, testo_sugg)
        if tag in self._legati:
            return
        self._legati.add(tag)
        c = self.tela
        c.tag_bind(tag, '<Enter>', lambda e, t=tag: self._entra_tela(t, e))
        c.tag_bind(tag, '<Leave>', lambda e, t=tag: self._esci_tela(t))
        c.tag_bind(tag, '<ButtonPress-1>', self._sugg_tela.nascondi)
        c.tag_bind(tag, '<ButtonRelease-1>', lambda e, t=tag: self._clic_tela(t))

    def _entra_tela(self, tag: str, evento=None) -> None:
        if tag not in self._attivi:          # elemento spento in questo disegno
            return
        self._sopra = tag
        try:
            self.tela.configure(cursor='hand2')
        except tk.TclError:
            pass
        self._evidenzia(tag, True)
        testo = self._attivi[tag][1]
        if testo:
            self._sugg_tela.entra(testo, evento)

    def _esci_tela(self, tag: str) -> None:
        if self._sopra == tag:
            self._sopra = None
        try:
            self.tela.configure(cursor='')
        except tk.TclError:
            pass
        self._evidenzia(tag, False)
        self._sugg_tela.nascondi()

    def _clic_tela(self, tag: str) -> None:
        azione = self._attivi.get(tag)
        if azione is not None and azione[0] is not None:
            self._sugg_tela.nascondi()
            azione[0]()

    def _evidenzia(self, tag: str, sopra: bool) -> None:
        """Sotto il mouse: lo sfondo dell'elemento diventa piu' chiaro (immagini preparate in _ridisegna)."""
        varianti = self._varianti.get(tag)
        if varianti:
            item, normale, chiara = varianti
            try:
                self.tela.itemconfigure(item, image=chiara if sopra else normale)
            except tk.TclError:
                pass

    def vai_pagina(self, i: int) -> None:
        try:
            self.schede.select(i)
        except tk.TclError:
            pass
        self.scheda_cambiata()

    def _scrivi_stato(self) -> None:
        try:
            self.tela.itemconfigure('testo_stato', text=self.stato.get())
        except tk.TclError:
            pass

    def _prepara_strumento(self) -> None:
        """Senza fmv_str (prima volta): si compila in sottofondo, poi l'immagine di fondo si adatta alla finestra."""
        try:
            if L.strumento_filmati() is not None:
                self.coda.put(('sfondo', None))
        except Exception:  # noqa: BLE001
            pass

    def _ridisegna(self) -> None:
        """Ridisegna tutto quello che sta sulla tela (tranne l'immagine di fondo e le finestre dentro la tela)."""
        self._id_disegno = None
        c, s = self.tela, self.scala
        W, H = self._dim()
        self._dim_disegno = (W, H)
        self._varianti = {}
        self._attivi = {}
        if self._sopra is not None:          # l'elemento sotto il mouse si rifa': di nuovo con <Enter>
            self._sopra = None
            try:
                c.configure(cursor='')
            except tk.TclError:
                pass
        c.delete('disegno')
        D = ('disegno',)

        def z(v):
            return int(round(v * s))
        tb = z(56)
        # ---- barra in alto: marchio, pagine, lingua
        c.create_image(0, 0, image=self._foto(('velo', W, tb), lambda: GR.velo(W, tb, (6, 8, 16, 160))), anchor='nw',
                       tags=D)
        c.create_line(0, tb, W, tb, fill='#252b39', tags=D)
        d = z(10)
        c.create_image(z(24), tb // 2, image=self._foto(('cerchio', d, 'rosso'), lambda: GR.cerchio(d, COL_ROSSO + (255,))),
                       anchor='w', tags=D)
        marca = c.create_text(z(42), tb // 2, text='ENTERELECTRO-RECOMP', fill='#ffffff', font=(CARATTERE, 11, 'bold'),
                              anchor='w', tags=D)
        bb = c.bbox(marca) or (0, 0, z(140), 0)
        c.create_text(bb[2] + z(8), tb // 2 + 1, text=str(L.VERSIONE), fill='#8f97a8', font=(CARATTERE, 9), anchor='w',
                      tags=D)
        x = max(z(250), bb[2] + z(70))
        for i, nome in enumerate((T('GIOCO', 'GAME'), T('OPZIONI', 'OPTIONS'), T('SALVATAGGI', 'SAVES'),
                                  T('REGISTRO', 'LOG'))):
            tag = f'nav{i}'
            it = c.create_text(x, tb // 2, text=nome, fill='#ffffff' if i == self.pagina else '#8c94a5',
                               font=(CARATTERE, 10, 'bold'), anchor='w', tags=D + (tag,))
            b = c.bbox(it) or (x, 0, x + z(60), 0)
            if i == self.pagina:
                lw = max(4, b[2] - b[0])
                c.create_image(b[0], tb - z(7), image=self._foto(('linea', lw, z(4)), lambda lw=lw: GR.rett_tondo(
                    lw, z(4), z(2), COL_GIALLO + (255,))), anchor='nw', tags=D)
            # zona cliccabile un po' piu' grande della scritta
            c.create_rectangle(b[0] - z(10), 0, b[2] + z(10), tb, outline='', fill='', tags=D + (tag,))
            self._tasto(tag, lambda i=i: self.vai_pagina(i))
            x = b[2] + z(38)
        c.coords(self._id_lingua, W - z(24), tb // 2)
        c.create_text(W - z(24) - max(z(100), int(self.cb_lingua.winfo_reqwidth() or 0)) - z(10), tb // 2,
                      text='Lingua / Language', fill='#8f97a8', font=(CARATTERE, 9), anchor='e', tags=D)
        # ---- riga di stato in basso
        hs = z(24)
        c.create_image(0, H - hs, image=self._foto(('velo', W, hs, 'stato'), lambda: GR.velo(W, hs, (4, 6, 12, 185))),
                       anchor='nw', tags=D)
        c.create_text(z(24), H - hs // 2, text=self.stato.get(), fill='#9aa2b3', font=(CARATTERE, 9), anchor='w',
                      tags=D + ('testo_stato',))
        nota = T('Immagine dai filmati migliorati del tuo disco', 'Picture from the enhanced movies of your disc') \
            if self._con_sfondo else T('Sfondo disegnato per EnterElectro-Recomp', 'Background drawn for EnterElectro-Recomp')
        c.create_text(W - z(24), H - hs // 2, text=nota, fill='#6f7789', font=(CARATTERE, 8), anchor='e', tags=D)
        # ---- versioni a sinistra (elenco stretto, solo i distintivi, se la pagina scelta non ci starebbe accanto)
        px0, py0, pw = z(24), tb + z(20), z(320)
        if self.pagina != 0:
            try:
                serve = int(self.pannello_pagine.winfo_reqwidth()) + z(28)
            except (tk.TclError, ValueError, TypeError):
                serve = 0
            if W - z(24 + 28 + 24) - pw < serve:
                pw = z(84)
        stretto = pw < z(200)
        ph = H - py0 - hs - z(20)
        c.create_image(px0, py0, image=self._vetro(pw, ph, z(18), 140), anchor='nw', tags=D)
        if not stretto:
            c.create_text(px0 + z(20), py0 + z(26), text=T('VERSIONI DEL GIOCO', 'GAME VERSIONS'), fill='#8f97a8',
                          font=(CARATTERE, 9, 'bold'), anchor='w', tags=D)
        by = py0 + ph - z(16) - z(40)
        if stretto:                  # uno sopra l'altro, solo le icone
            tasti = (('t_disco', px0 + z(12), by, pw - z(24), 'piu', '', self.aggiungi_disco, 'disco'),
                     ('t_aggiorna', px0 + z(12), by - z(48), pw - z(24), 'aggiorna', '', self.aggiorna, 'aggiorna'))
            fine_elenco = by - z(48) - z(10)
        else:
            tasti = (('t_disco', px0 + z(12), by, pw - z(24) - z(76), 'piu', T('Aggiungi un disco', 'Add a disc'),
                      self.aggiungi_disco, 'disco'),
                     ('t_aggiorna', px0 + pw - z(12) - z(64), by, z(64), 'aggiorna', '', self.aggiorna, 'aggiorna'))
            fine_elenco = by - z(10)
        for tag, x0, y0, w, icona, testo, comando, chiave in tasti:
            attivo = self.proc is None
            n_img = self._foto(('tasto', w, z(40), 'n'), lambda w=w: GR.rett_tondo(w, z(40), z(10), (255, 255, 255, 16),
                                                                                    (255, 255, 255, 60), 1))
            s_img = self._foto(('tasto', w, z(40), 's'), lambda w=w: GR.rett_tondo(w, z(40), z(10), (255, 255, 255, 34),
                                                                                    (255, 255, 255, 110), 1))
            it = c.create_image(x0, y0, image=n_img, anchor='nw', tags=D + (tag,))
            ic = self._icona(icona, z(18), not attivo)
            if testo:
                if ic:
                    c.create_image(x0 + z(16), y0 + z(20), image=ic, anchor='w', tags=D + (tag,))
                c.create_text(x0 + z(42), y0 + z(20), text=testo, fill='#e6e8ee' if attivo else '#6f7789',
                              font=(CARATTERE, 10, 'bold'), anchor='w', tags=D + (tag,))
            elif ic:
                c.create_image(x0 + w // 2, y0 + z(20), image=ic, anchor='center', tags=D + (tag,))
            if attivo:
                self._varianti[tag] = (it, n_img, s_img)
                self._tasto(tag, comando, SUGG[chiave])
        righe = self.righe
        if righe:
            ya, yb = py0 + (z(14) if stretto else z(44)), fine_elenco
            ch = max(z(30), min(z(84 if not stretto else 64), (yb - ya) // len(righe)))   # basse se la finestra e' bassa
            hc, wc = ch - z(8), pw - z(24)
            scelto = self.profilo_scelto()
            for i, r in enumerate(righe):
                self._carta(r, px0 + z(12), ya + i * ch, wc, hc, r['profilo'] == scelto)
        # ---- pagina principale (titolo, versione scelta, pulsanti) oppure le altre pagine
        x0 = px0 + pw + z(28)
        cw = max(z(400), W - x0 - z(24))
        if self.pagina == 0:
            c.itemconfigure(self._id_pagine, state='hidden')
            self._disegna_principale(x0, tb, cw, H - hs)
        else:
            alto = H - hs - z(20) - (tb + z(20))
            c.create_image(x0, tb + z(20), image=self._foto(('pagina', cw, alto), lambda: GR.rett_tondo(
                cw, alto, z(18), (17, 21, 31, 250), (255, 255, 255, 30), 1)), anchor='nw', tags=D)
            c.coords(self._id_pagine, x0 + z(14), tb + z(34))
            c.itemconfigure(self._id_pagine, width=cw - z(28), height=alto - z(28), state='normal')
        c.tag_raise('disegno')
        try:
            c.tag_raise(self._id_lingua)
            c.tag_raise(self._id_pagine)
        except tk.TclError:
            pass

    def _carta(self, r, x: int, y: int, w: int, h: int, scelta: bool) -> None:
        """Una versione del gioco nell'elenco a sinistra: distintivo con la regione, nome, lingua e video, pallino."""
        c, s = self.tela, self.scala
        D = ('disegno',)

        def z(v):
            return int(round(v * s))
        tag = f'carta_{r["profilo"]}'
        if scelta:
            img = self._foto(('carta', w, h, 'scelta'), lambda: GR.rett_tondo(w, h, z(12), (255, 255, 255, 30),
                                                                               (255, 255, 255, 64), 1))
            chiara = img
        else:
            img = self._foto(('carta', w, h, 'vuota'), lambda: GR.rett_tondo(w, h, z(12), (255, 255, 255, 1)))
            chiara = self._foto(('carta', w, h, 'sopra'), lambda: GR.rett_tondo(w, h, z(12), (255, 255, 255, 16),
                                                                                (255, 255, 255, 36), 1))
        it = c.create_image(x, y, image=img, anchor='nw', tags=D + (tag,))
        self._varianti[tag] = (it, img, chiara)
        if scelta:
            bh = max(z(20), h - z(28))
            c.create_image(x + 1, y + (h - bh) // 2, image=self._foto(('barra', z(4), bh), lambda: GR.rett_tondo(
                z(4), bh, z(2), COL_ROSSO + (255,))), anchor='nw', tags=D + (tag,))
        colore = self.colore_stato(r)
        rgb = tuple(int(colore[i:i + 2], 16) for i in (1, 3, 5))
        if w < z(120):                     # elenco stretto: distintivo al centro, pallino dello stato sul bordo
            d = max(z(16), min(z(40), h - z(12)))
            xc, yc = x + w // 2 + z(2), y + h // 2
            c.create_image(xc, yc, image=self._foto(('distintivo', d, colore), lambda: GR.cerchio(
                d, rgb + (44,), rgb + (235,), max(1, z(2)))), anchor='center', tags=D + (tag,))
            c.create_text(xc, yc, text=sigla_regione(r['profilo']), fill='#eef0f5', font=(CARATTERE, 8, 'bold'),
                          anchor='center', tags=D + (tag,))
            dd = z(10)
            c.create_image(xc + d // 2 - z(3), yc - d // 2 + z(3), image=self._foto(('cerchio_bordo', dd, colore),
                           lambda: GR.cerchio(dd, rgb + (255,), (17, 21, 31, 255), max(1, z(2)))), anchor='center',
                           tags=D + (tag,))
            self._tasto(tag, lambda p=r['profilo']: self.scegli_versione(p), f'{r.get("nome", "")} ({r["profilo"]})')
            return
        bassa = h < z(46)                  # finestra molto bassa: una riga sola (nome), distintivo piu' piccolo
        d = max(z(16), h - z(10)) if bassa else min(z(40), h - z(16))
        c.create_image(x + z(18), y + h // 2, image=self._foto(('distintivo', d, colore), lambda: GR.cerchio(
            d, rgb + (44,), rgb + (235,), max(1, z(2)))), anchor='w', tags=D + (tag,))
        c.create_text(x + z(18) + d // 2, y + h // 2, text=sigla_regione(r['profilo']), fill='#eef0f5',
                      font=(CARATTERE, 8, 'bold'), anchor='center', tags=D + (tag,))
        tx = x + z(18) + d + z(14)
        larg_testo = w - (tx - x) - z(30)
        c.create_text(tx, y + h // 2 - (0 if bassa else z(10)),
                      text=accorcia(nome_breve(r.get('nome') or r['profilo']), larg_testo, (CARATTERE, 11, 'bold')),
                      fill='#ffffff' if scelta else '#dce0e8', font=(CARATTERE, 11, 'bold'), anchor='w',
                      tags=D + (tag,))
        if not bassa:
            c.create_text(tx, y + h // 2 + z(11), text=f'{r.get("lingua", "")} \u00b7 {r.get("video", "")}', fill='#8f97a8',
                          font=(CARATTERE, 9), anchor='w', tags=D + (tag,))
        dd = z(10)
        c.create_image(x + w - z(16), y + h // 2, image=self._foto(('cerchio', dd, colore), lambda: GR.cerchio(
            dd, rgb + (255,))), anchor='e', tags=D + (tag,))
        self._tasto(tag, lambda p=r['profilo']: self.scegli_versione(p), f'{r.get("nome", "")} ({r["profilo"]})')

    def scegli_versione(self, prof: str) -> None:
        try:
            if self.albero.exists(prof):
                self.albero.selection_set(prof)
                self.albero.see(prof)
        except tk.TclError:
            pass
        self.versione_scelta()

    def _disegna_principale(self, x0: int, tb: int, cw: int, fondo_y: int) -> None:
        c, s = self.tela, self.scala
        D = ('disegno', 'principale')

        def z(v):
            return int(round(v * s))
        r = self.riga(self.profilo_scelto())
        bp_h = z(156)
        bp_y = fondo_y - z(20) - bp_h
        # titolo disegnato: il piu' grande che sta tra la barra in alto e il pannello in basso (le finestre basse o
        # strette, come sui portatili con l'ingrandimento di Windows al 150%, hanno quello piccolo)
        yt = tb + z(10)
        img, sc = None, s
        for k in (1.0, 0.75, 0.6):
            sc = s * k
            img = self._titolo(sc)
            if img is None or (int(img.height() * 0.86) <= bp_y - yt - z(122) and img.width() - int(50 * sc) <= cw):
                break
        if img is not None:
            c.create_image(x0 - int(50 * sc) + z(6), yt, image=img, anchor='nw', tags=D)
            alto_titolo = int(img.height() * 0.86)        # sotto c'e' solo il bagliore delle lettere
        else:
            c.create_text(x0, yt + z(60), text='Spider-Man 2: Enter Electro', fill='#ffffff',
                          font=(CARATTERE, 26, 'bold'), anchor='w', tags=D)
            alto_titolo = z(110)
        # spazio sotto il titolo: meno se la finestra e' bassa (fino a sovrapporsi al bagliore delle lettere)
        yv = yt + alto_titolo + max(-z(12), min(z(22), bp_y - yt - alto_titolo - z(94)))
        I = D + ('info',)
        if r is not None:
            nome = c.create_text(x0 + z(20), yv, text=nome_breve(r.get('nome') or r['profilo']), fill='#ffffff',
                                 font=(CARATTERE, 16, 'bold'), anchor='w', tags=I)
            b = c.bbox(nome) or (0, 0, x0 + z(200), 0)
            c.create_text(b[2] + z(14), yv + 1,
                          text=f'{r.get("lingua", "")}  \u00b7  {r.get("video", "")}  \u00b7  {r["profilo"]}',
                          fill='#c3c9d6', font=(CARATTERE, 10), anchor='w', tags=I)
            # pastiglie: stato e caratteristiche dell'installazione (larghe quanto la scritta; quelle che non ci
            # stanno non si mostrano). Scure, come il vetro dei pannelli: si leggono anche sopra un fotogramma chiaro
            x = x0 + z(20)
            yc = yv + z(30)
            colore = self.colore_stato(r)
            rgb = tuple(int(colore[i:i + 2], 16) for i in (1, 3, 5))
            stato = (T('Installata', 'Installed') if r['pronta'] else
                     (T('Da installare', 'To install') if r['ha_disco'] else T('Manca il disco', 'Disc missing')))
            for i, testo in enumerate([stato] + list(r.get('extra') or [])):
                pieno = i == 0
                scritta = c.create_text(x + z(13), yc + z(14), text=testo, fill='#ffffff' if pieno else '#dde1ea',
                                        font=(CARATTERE, 9, 'bold'), anchor='w', tags=I)
                bb = c.bbox(scritta)
                lw = ((bb[2] - bb[0]) if bb else int(len(testo) * 7.2 * s)) + z(26)
                if i > 0 and x + lw > x0 + cw - z(20):
                    c.delete(scritta)
                    break
                img = self._foto(('pastiglia', lw, z(28), colore if pieno else 'vuota'), lambda lw=lw, pieno=pieno: (
                    GR.rett_tondo(lw, z(28), z(14), tuple(int(v * 0.32) + 8 for v in rgb) + (225,), rgb + (220,), 1)
                    if pieno else GR.rett_tondo(lw, z(28), z(14), (12, 16, 28, 205), (255, 255, 255, 72), 1)))
                fondo = c.create_image(x, yc, image=img, anchor='nw', tags=I)
                c.tag_lower(fondo, scritta)
                x += lw + z(10)
            c.create_text(x0 + z(20), yc + z(46), text=self.descrivi_stato(r), fill='#d2d7e0',
                          font=(CARATTERE, 10), anchor='w', width=cw - z(40), tags=I)
        else:
            c.create_text(x0 + z(20), yv, text=self.descrivi_stato(None), fill='#d2d7e0', font=(CARATTERE, 11),
                          anchor='w', tags=I)
        # vetro scuro dietro le informazioni della versione, grande quanto le scritte: si leggono sopra qualunque
        # immagine di fondo (i fotogrammi dei filmati possono essere chiari proprio li')
        bb = c.bbox('info')
        if bb:
            vx, vy = bb[0] - z(18), bb[1] - z(12)
            vw, vh = min(cw + z(4), bb[2] - bb[0] + z(40)), bb[3] - bb[1] + z(24)
            vetro = c.create_image(vx, vy, image=self._vetro(vw, vh, z(16), 145, 18), anchor='nw', tags=D)
            c.tag_lower(vetro, 'info')
        # ---- pannello in basso: azioni e pulsante principale (piu' stretto se la finestra e' stretta)
        azioni = [('filmati', T('Filmati', 'Movies'), self.apri_filmati, 'prepara_filmati', 'filmati'),
                  ('comandi', T('Comandi', 'Controls'), self.comandi, 'comandi', 'comandi'),
                  ('cartella', T('Cartella', 'Folder'), self.apri_cartella, 'cartella', 'cartella'),
                  ('installa', T('Reinstalla', 'Reinstall'), self.installa, 'installa', 'installa'),
                  ('impostazioni', T('Opzioni', 'Options'), lambda: self.vai_pagina(1), None, 'opzioni')]
        c.create_image(x0, bp_y, image=self._vetro(cw, bp_h, z(20), 150), anchor='nw', tags=D)
        bw, bh = max(z(220), min(z(300), cw - z(76) - len(azioni) * z(70))), z(84)
        bx, by = x0 + cw - z(28) - bw, bp_y + z(30)
        testo, comando, attivo, icona = self._principale
        if attivo:
            c.create_image(bx - z(22), by - z(22), image=self._foto(('alone', bw, bh), lambda: GR.bagliore(
                bw, bh, z(18), COL_ROSSO + (140,), z(22))), anchor='nw', tags=D + ('principale_tasto',))
        varianti = {}
        for chiave, c1, c2 in (('n', (240, 64, 84, 255), (214, 33, 61, 255)), ('s', (255, 96, 112, 255),
                                                                              (230, 52, 78, 255)),
                               ('x', (74, 58, 64, 255), (56, 44, 50, 255))):
            varianti[chiave] = self._foto(('grande', bw, bh, chiave), lambda c1=c1, c2=c2: GR.rett_tondo(
                bw, bh, z(18), c1, None, 1, c2))
        it = c.create_image(bx, by, image=varianti['n' if attivo else 'x'], anchor='nw',
                            tags=D + ('principale_tasto',))
        c.create_image(bx + z(3), by + z(3), image=self._foto(('velo_tasto', bw - z(6), bh // 2), lambda: GR.rett_tondo(
            bw - z(6), bh // 2, z(16), (255, 255, 255, 30 if attivo else 8))), anchor='nw',
            tags=D + ('principale_tasto',))
        ic = self._icona(icona, z(30), not attivo)
        larg_ic = z(30) + z(14) if ic else 0
        scritta, larg = None, 0
        for pt in (17, 15, 13, 11):          # la scritta piu' grande che ci sta
            if scritta is not None:
                c.delete(scritta)
            scritta = c.create_text(bx, by + bh // 2, text=testo, fill='#ffffff' if attivo else '#9b8a8d',
                                    font=(CARATTERE, pt, 'bold'), anchor='w', tags=D + ('principale_tasto',))
            bb = c.bbox(scritta)
            larg = (bb[2] - bb[0]) if bb else int(len(testo) * 0.68 * pt * s)
            if larg_ic + larg <= bw - z(32):
                break
        xs = bx + (bw - larg_ic - larg) // 2
        if ic:
            c.create_image(xs, by + bh // 2, image=ic, anchor='w', tags=D + ('principale_tasto',))
        c.coords(scritta, xs + larg_ic, by + bh // 2)
        c.create_text(bx + bw // 2, by + bh + z(20), text=self._didascalia(), fill='#8f97a8', font=(CARATTERE, 8),
                      anchor='center', width=bw + z(40), tags=D + ('didascalia',))
        if attivo and comando is not None:
            self._varianti['principale_tasto'] = (it, varianti['n'], varianti['s'])
            self._tasto('principale_tasto', comando)
        # azioni secondarie
        spazio = bx - (x0 + z(28)) - z(20)
        passo = max(z(56), min(z(92), spazio // len(azioni)))
        lato = max(z(48), min(z(76), passo - z(14)))
        ya = bp_y + (bp_h - lato) // 2
        for i, (icona, nome, cmd, chiave, stato_k) in enumerate(azioni):
            xa = x0 + z(28) + i * passo
            attiva = self._azioni.get(stato_k, True)
            tag = f'azione_{stato_k}'
            n_img = self._foto(('azione', lato, 'n'), lambda: GR.rett_tondo(lato, lato, z(16), (255, 255, 255, 16),
                                                                             (255, 255, 255, 52), 1))
            s_img = self._foto(('azione', lato, 's'), lambda: GR.rett_tondo(lato, lato, z(16), (255, 255, 255, 34),
                                                                             (255, 255, 255, 110), 1))
            x_img = self._foto(('azione', lato, 'x'), lambda: GR.rett_tondo(lato, lato, z(16), (255, 255, 255, 6),
                                                                             (255, 255, 255, 24), 1))
            it = c.create_image(xa, ya, image=n_img if attiva else x_img, anchor='nw', tags=D + (tag,))
            ic = self._icona(icona, int(lato * 0.40), not attiva)
            if ic:
                c.create_image(xa + lato // 2, ya + int(lato * 0.40), image=ic, anchor='center', tags=D + (tag,))
            c.create_text(xa + lato // 2, ya + lato - z(13), text=nome, fill='#c4cad6' if attiva else '#5f6676',
                          font=(CARATTERE, 8, 'bold'), anchor='center', tags=D + (tag,))
            if attiva:
                self._varianti[tag] = (it, n_img, s_img)
                self._tasto(tag, cmd, SUGG[chiave] if chiave else None)

    def _titolo(self, sc: float):
        """Le lettere del titolo (tools/grafica/titolo_NNN.png) per l'ingrandimento sc, None se mancano."""
        f = GR.file_titolo(sc)
        if f is None:
            return None
        img = self._img.get(('titolo', f.name))
        if img is None:
            try:
                img = self._img[('titolo', f.name)] = tk.PhotoImage(file=str(f))
            except tk.TclError:
                return None
        return img

    def _didascalia(self) -> str:
        if self.proc is not None:
            return self._ultima_riga or T('Comando in corso: i dettagli sono nel Registro.',
                                          'Command running: the details are in the Log.')
        testo, _comando, attivo, _icona = self._principale
        if not attivo:
            return T('Scegli una versione a sinistra.', 'Choose a version on the left.')
        if testo == T('GIOCA', 'PLAY'):
            return T('Nel gioco: F10 menu, F7 salvataggi rapidi', 'In the game: F10 menu, F7 save states')
        if testo == T('INSTALLA', 'INSTALL'):
            return T('Prepara il gioco dal tuo disco: alcuni minuti', 'Builds the game from your disc: a few minutes')
        return T('Scegli il dump del tuo disco (.cue o .ccd)', 'Choose the dump of your disc (.cue or .ccd)')

    def pallino_di(self, colore: str, d: int | None = None):
        d = d or int(12 * self.scala)
        if (colore, d) not in self._pallini:
            self._pallini[(colore, d)] = pallino(colore, d)
        return self._pallini[(colore, d)]

    def colore_stato(self, r) -> str:
        if r and r['pronta']:
            return COL['verde']
        return COL['giallo'] if (r and r['ha_disco']) else COL['grigio']

    def descrivi_stato(self, r) -> str:
        """La riga sotto il nome della versione scelta."""
        if r is None:
            return T('Scegli una versione nell\'elenco a sinistra.', 'Choose a version in the list on the left.')
        if r['pronta']:
            # le caratteristiche sono gia' nelle pastiglie: qui solo le note tra parentesi (versione precedente...)
            testo = r.get('installazione', '')
            note = [x.split(')')[0] for x in testo.split('(')[1:]]
            if note:
                return '; '.join(note)[:1].upper() + '; '.join(note)[1:] + '.'
            return T('Pronta: premi Gioca.', 'Ready: press Play.')
        if r['ha_disco']:
            if r.get('installazione', 'no') not in (T('no', 'no'), 'no'):
                return T('Installazione incompleta: premi Installa.', 'Incomplete installation: press Install.')
            return T('Il disco c\'e\': premi Installa per preparare il gioco (alcuni minuti).',
                     'The disc is there: press Install to build the game (a few minutes).')
        return T('Manca il disco: aggiungi il dump del tuo disco.', 'The disc is missing: add the dump of your disc.')

    def aggiorna_cima(self) -> None:
        """La versione scelta e' cambiata: si ridisegna la tela (le immagini sono gia' pronte, e' veloce)."""
        self._ridisegna()

    def sfondo_disponibile(self):
        """Il fotogramma per l'immagine di fondo: della versione scelta o, se non ce l'ha, di un'altra installata con i
        filmati migliorati; None se nessuna li ha."""
        scelto = self.profilo_scelto()
        profili = ([scelto] if scelto else []) + [r['profilo'] for r in self.righe if r['profilo'] != scelto]
        for p in profili:
            cart = L.GIOCHI / p
            jpg = cart / L.SFONDO
            if not jpg.is_file() and (cart / L.FILMATI_HD).is_dir():
                try:
                    L.prepara_sfondo(cart)
                except OSError:
                    pass
            if jpg.is_file():
                return jpg
        return None

    def _larghezza_sfondo(self) -> int:
        return self._dim()[0]

    def _fmv_str(self):
        """tools/fmv/fmv_str se c'e' ed e' aggiornato (non piu' vecchio di fmv_str.c), altrimenti None (lo rifa'
        _prepara_strumento in sottofondo)."""
        exe = L.FMV_DIR / ('fmv_str.exe' if os.name == 'nt' else 'fmv_str')
        try:
            sorgente = L.FMV_DIR / 'fmv_str.c'
            if exe.is_file() and (not sorgente.is_file() or exe.stat().st_mtime >= sorgente.stat().st_mtime):
                return exe
        except OSError:
            pass
        return None

    def _fai_ppm(self, sorgente: Path, dest: Path, W: int, H: int, centro: int, scuro: int) -> bool:
        exe = self._fmv_str()
        if exe is None:
            return False
        if dest.is_file() and dest.stat().st_mtime >= sorgente.stat().st_mtime:
            return True
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        r = subprocess.run([str(exe), 'sfondo', str(sorgente), str(dest), str(W), str(H), str(centro), str(scuro)],
                           capture_output=True, timeout=30, creationflags=flags)
        return r.returncode == 0 and dest.is_file()

    def mostra_sfondo(self) -> None:
        """Immagine di fondo di tutta la finestra: un fotogramma dei filmati migliorati (ritagliato e scurito da
        tools/fmv/fmv_str per la grandezza della finestra; il risultato resta accanto al fotogramma), altrimenti lo
        sfondo disegnato per il launcher (togli_sfondo)."""
        try:
            jpg = self.sfondo_disponibile()
            if jpg is None or self._fmv_str() is None:
                self.togli_sfondo()
                return
            W, H = self._dim()
            ppm = jpg.with_name(f'sfondo_{W}x{H}.ppm')
            chiave = (str(jpg), jpg.stat().st_mtime, W, H)
            if chiave == self._sfondo_di:
                return
            if not self._fai_ppm(jpg, ppm, W, H, 450, 100):
                self.togli_sfondo()
                return
            for vecchio in jpg.parent.glob('sfondo_*.ppm'):      # quelli per altre grandezze della finestra
                if vecchio.name != ppm.name:
                    try:
                        vecchio.unlink()
                    except OSError:
                        pass
            self._metti_fondo(tk.PhotoImage(file=str(ppm)), chiave, True)
        except (tk.TclError, OSError, subprocess.SubprocessError, ValueError):
            self.togli_sfondo()

    def togli_sfondo(self) -> None:
        """Senza fotogramma: lo sfondo disegnato per il launcher (citta' di notte con i fulmini), adattato alla finestra
        da fmv_str se c'e', altrimenti centrato com'e'; senza nemmeno quello, una sfumatura scura fatta qui."""
        W, H = self._dim()
        arte = GR.file_sfondo()
        img = None
        chiave = ('disegnato', W, H)
        if chiave == self._sfondo_di:
            return
        try:
            if arte is not None:
                # nella cartella temporanea, con la grandezza del disegno nel nome (un pacchetto nuovo con un altro
                # disegno non riusa quello vecchio); quelli per altre grandezze della finestra si tolgono
                tmp = Path(tempfile.gettempdir()) / f'sm2_sfondo2_{W}x{H}_{arte.stat().st_size}.ppm'
                if self._fai_ppm(arte, tmp, W, H, 500, 0):
                    for vecchio in tmp.parent.glob('sm2_sfondo*.ppm'):
                        if vecchio.name != tmp.name:
                            try:
                                vecchio.unlink()
                            except OSError:
                                pass
                    img = tk.PhotoImage(file=str(tmp))
                else:
                    img = tk.PhotoImage(file=str(arte))
                    chiave = ('disegnato_centrato', W, H)
            else:
                img = tk.PhotoImage(data=ppm_sfumato(W, H))
                chiave = ('sfumatura', W, H)
        except (tk.TclError, OSError, subprocess.SubprocessError):
            img = None
            chiave = ('nessuno', W, H)
        self._metti_fondo(img, chiave, False)

    def _metti_fondo(self, img, chiave, foto: bool) -> None:
        c = self.tela
        c.delete('fondo_cima')
        if img is not None:
            W, H = self._dim()
            centrato = chiave[0] == 'disegnato_centrato'
            c.create_image(W // 2 if centrato else 0, H // 2 if centrato else 0, image=img,
                           anchor='center' if centrato else 'nw', tags=('fondo_cima',))
            c.tag_lower('fondo_cima')
        self._img_fondo = img
        self.img_sfondo = img if foto else None
        cambio = foto != self._con_sfondo
        self._sfondo_di = chiave
        self._con_sfondo = foto
        if cambio and self._dim_disegno is not None:
            self._ridisegna()

    def versione_scelta(self) -> None:
        """Pulsanti, immagine in cima e scheda Gioco per la versione scelta e, se e' cambiata, le sue opzioni gia'
        salvate."""
        self.aggiorna_pulsanti()
        self.aggiorna_cima()
        self.mostra_sfondo()
        if self.salvataggi is not None and self.schede.index('current') == 2:
            self.salvataggi.aggiorna(self.profilo_scelto())
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
                                         (self.filmati, self.cb_filmati, FILMATI, o.get('filmati', 'originali')),
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
        if isinstance(o.get('pgxp_opz'), dict):
            self.pgxp_opz = dict(o['pgxp_opz'])
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
        self.volume.set(o.get('volume', 100))
        sn = lambda x: valore_letto('si' if x else 'no')  # noqa: E731
        self.scrivi(T(f'Opzioni salvate di {prof}: risoluzione {o["risoluzione"]}, filtro {o["filtro"]}, '
                      f'filmati {o.get("filmati", "originali")}, '
                      f'widescreen {o["widescreen"]}, PGXP {sn(o["pgxp"])}, distanza visiva {sn(o["distanza"])}, '
                      f'salto delle attese {sn(o.get("attese"))}; sincronia {o.get("sincronia")}, '
                      f'thread video {sn(o.get("thread"))}, schermo {o.get("schermo")}; volume all\'avvio '
                      f'{o.get("volume", 100)}%',
                      f'Saved options of {prof}: resolution {valore_letto(o["risoluzione"])}, filter '
                      f'{valore_letto(o["filtro"])}, movies {valore_letto(o.get("filmati", "originali"))}, '
                      f'widescreen {o["widescreen"]}, PGXP {sn(o["pgxp"])}, draw distance '
                      f'{sn(o["distanza"])}, idle skip {sn(o.get("attese"))}; vertical sync '
                      f'{valore_letto(o.get("sincronia"))}, render thread {sn(o.get("thread"))}, screen '
                      f'{valore_letto(o.get("schermo"))}; volume at start {o.get("volume", 100)}%'))

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
        self.b_filmati.state(['!disabled' if pronta else 'disabled'])
        self.b_comandi.state(['!disabled' if (pronta and not occupato) else 'disabled'])
        self.b_precedente.state(['disabled' if occupato else '!disabled'])
        if occupato:
            self._principale = (T('IN CORSO...', 'WORKING...'), None, False, 'aggiorna')
        elif r is None:
            self._principale = (T('GIOCA', 'PLAY'), None, False, 'gioca')
        elif pronta:
            self._principale = (T('GIOCA', 'PLAY'), self.gioca, True, 'gioca')
        elif r['ha_disco']:
            self._principale = (T('INSTALLA', 'INSTALL'), self.installa, True, 'installa')
        else:
            self._principale = (T('AGGIUNGI UN DISCO', 'ADD A DISC'), self.aggiungi_disco, True, 'disco')
        self._azioni = {'filmati': pronta, 'comandi': pronta and not occupato,
                        'cartella': bool(r and (L.GIOCHI / r['profilo']).is_dir()),
                        'installa': bool(r and r['ha_disco'] and pronta and not occupato), 'opzioni': True}
        if getattr(self, '_dim_disegno', None) is not None:
            self._ridisegna()

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
        self._ultima_riga = ''
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

    def apri_filmati(self):
        """La finestra dei filmati (0.12) della versione scelta: Migliorati e filmati IA. Si apre anche mentre si
        preparano (per seguire e fermare); una sola alla volta."""
        prof = self.profilo_scelto()
        r = self.riga(prof)
        if not prof or not (r and r['pronta']):
            return None
        ff = self.finestra_filmati
        if ff is not None and ff.vivo:
            if ff.prof == prof:
                try:
                    ff.top.deiconify()
                    ff.top.lift()
                    ff.top.focus_force()
                    return ff
                except tk.TclError:
                    pass
            ff.chiudi()
        self.finestra_filmati = FinestraFilmati(self, prof)
        return self.finestra_filmati

    def _avanzamento(self, riga: str) -> None:
        """Una riga "AVANZAMENTO fatti totale secondi" di prepara-filmati-ia: sotto il pulsante principale."""
        try:
            fatti, totale, resto = (int(x) for x in riga.split()[1:4])
        except ValueError:
            return
        self.avanzamento = (fatti, totale, resto)
        testo = T(f'Filmati IA: {100 * fatti // max(1, totale)}% ({fatti} di {totale}), circa {durata(resto)} alla fine',
                  f'AI movies: {100 * fatti // max(1, totale)}% ({fatti} of {totale}), about {durata(resto)} to the end')
        self._ultima_riga = testo
        try:
            self.tela.itemconfigure('didascalia', text=testo)
        except tk.TclError:
            pass

    def prepara_filmati(self) -> None:
        prof = self.profilo_scelto()
        if not prof:
            return
        self.esegui(['prepara-filmati', '--profilo', prof],
                    T(f'Preparo i filmati migliorati di {prof} (alcuni minuti)',
                      f'Preparing the enhanced movies of {prof} (a few minutes)'))

    def argomenti_pgxp(self) -> list:
        """Le voci PGXP per il comando "opzioni" (tutte, cosi' quello che si vede e' quello che si salva)."""
        o = dict(L.pgxp_predefiniti(), **self.pgxp_opz)
        arg = ['--pgxp', 'si' if self.pgxp.get() else 'no']
        for k, _v, _c in L.PGXP_VOCI:
            arg += [f'--pgxp-{k}', 'si' if o[k] else 'no']
        return arg + ['--pgxp-tolleranza', f'{float(o["tolleranza"]):g}', '--pgxp-soglia', f'{float(o["soglia"]):g}',
                      '--pgxp-fessure', o['fessure'] if o['fessure'] in L.PGXP_FESSURE else 'no',
                      '--pgxp-bias', f'{float(o.get("bias", L.PGXP_BIAS)):g}',
                      '--pgxp-normalizza', o['normalizza'] if o.get('normalizza') in L.PGXP_NORMALIZZA else 'automatico']

    def ricompila_con_pgxp(self, prof: str):
        """PGXP acceso su un'installazione senza i punti di aggancio: in Spider-Man 2 PGXP non correggerebbe quasi
        niente. Chiede se ricompilare (una volta, salvataggi e opzioni restano). Restituisce gli argomenti di
        "installa", [] per giocare senza ricompilare (PGXP spento) o None per non fare niente."""
        cartella = L.GIOCHI / prof
        try:
            st = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            st = {}
        if st.get('pgxp'):
            return []
        tempi = st.get('tempi') or {}
        quanto = T('alcuni minuti', 'a few minutes')
        try:
            secondi = sum(float(v) for v in tempi.values()) if isinstance(tempi, dict) else 0.0
        except (TypeError, ValueError):
            secondi = 0.0
        if secondi >= 30:
            minuti = max(1, round(secondi / 60))
            quanto = T(f'circa {minuti} minuti, come l\'ultima installazione',
                       f'about {minuti} minutes, like the last installation')
        r = messagebox.askyesnocancel(
            'PGXP',
            T(f'Questa installazione di {prof} non ha i punti di aggancio di PGXP: senza di loro, in Spider-Man 2 '
              'PGXP non corregge quasi niente.\n\nPer farlo funzionare davvero il gioco va ricompilato con PGXP, una '
              f'volta sola ({quanto}; con il PGO, se serve, anche una partita di allenamento di circa 3 minuti a '
              'finestra nascosta). Salvataggi e opzioni restano.\n\nS\u00ec: ricompila e poi gioca\nNo: gioca adesso '
              'con PGXP spento\nAnnulla: non fare niente',
              f'This installation of {prof} does not have the PGXP hooks: without them, in Spider-Man 2 PGXP corrects '
              'almost nothing.\n\nTo make it really work the game must be built again with PGXP, only once '
              f'({quanto}; with PGO, if needed, also a training game of about 3 minutes in a hidden window). Saves '
              'and options stay.\n\nYes: build it and then play\nNo: play now with PGXP off\nCancel: do nothing'),
            parent=self.root)
        if r is None:
            return None
        if r is False:
            self.pgxp.set(False)
            return []
        arg = ['installa', '--profilo', prof, '--pgxp', '--attese', 'si' if self.attese.get() else 'no']
        if st.get('pgo'):
            arg.append('--pgo')
        if L.trova_exe(cartella / 'build-dev'):
            arg.append('--debug')
        return arg

    def apri_pgxp(self):
        """La finestra delle voci PGXP (0.12): si salvano con Gioca, come le altre opzioni."""
        return FinestraPGXP(self)

    def gioca(self) -> None:
        prof = self.profilo_scelto()
        if not prof:
            return
        ricompila = self.ricompila_con_pgxp(prof) if self.pgxp.get() else []
        if ricompila is None:
            return
        opz = ['opzioni', '--profilo', prof, '--risoluzione', dict(RIS).get(self.ris.get(), 'gioco'),
               *self.argomenti_pgxp(),
               '--filtro-texture', dict(FILTRI).get(self.filtro.get(), 'gioco'),
               '--filmati', dict(FILMATI).get(self.filmati.get(), 'originali'),
               '--widescreen', dict(WIDE).get(self.wide.get(), 'no'),
               '--distanza', 'si' if self.distanza.get() else 'no',
               '--attese', 'si' if self.attese.get() else 'no',
               '--sincronia', dict(SINC).get(self.sinc.get(), 'accesa'),
               '--thread-video', 'si' if (self.thread.get() or self.fluido.get()) else 'no',
               '--schermo', dict(SCHERMI).get(self.schermo.get(), 'finestra'),
               '--latenza-bassa', 'si' if self.latenza.get() else 'no',
               '--movimento-fluido', 'si' if self.fluido.get() else 'no',
               '--volume', str(self.volume_scelto())]
        larg = dict(LARGHEZZE).get(self.larghezza.get(), 0)
        if larg:
            opz += ['--larghezza-finestra', str(larg)]
        avvio = ['avvia', '--profilo', prof] + (['--con-launcher'] if self.con_launcher.get() else [])
        if ricompila:            # prima la ricompilazione con PGXP, poi le opzioni (anche quelle PGXP) e il gioco
            def dopo_installa():
                self.esegui(opz, T(f'Opzioni di {prof}', f'Saving the options of {prof}'),
                            poi=lambda: self.esegui(avvio, T(f'Avvio {prof}', f'Starting {prof}')))
            self.esegui(ricompila, T(f'Ricompilo {prof} con PGXP (una volta sola)',
                                     f'Building {prof} again with PGXP (only once)'), poi=dopo_installa)
            return
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
        self.sinc.set(etichetta_di(SINC, 'accesa'))      # 0.12: niente strappi (vedi la spiegazione)
        self.thread.set(False)                            # 0.12: su NVIDIA il thread spegne la sincronia
        self.fluido.set(False)
        self.scrivi(T('Impostazioni per PC lenti scelte: risoluzione e filtro come il gioco, PGXP e distanza visiva '
                      'spenti, salto delle attese acceso, sincronia accesa, disegno in un thread separato spento; PGO '
                      'spuntato '
                      'per la prossima installazione (se l\'installazione ha PGXP, reinstallare senza PGXP alleggerisce '
                      'ancora). Premi Gioca per salvarle.',
                      'Recommended settings for slow PCs chosen: resolution and filter as in the game, PGXP and draw '
                      'distance off, idle skip on, vertical sync on, render thread off; PGO ticked for the next '
                      'installation (if the installation has PGXP, installing again without PGXP makes it lighter '
                      'still). Press Play to save them.'))

    def comandi(self):
        """La finestra dei comandi del giocatore 1 per la versione scelta (si salva con il comando "opzioni")."""
        prof = self.profilo_scelto()
        r = self.riga(prof)
        if not prof or not (r and r['pronta']) or self.proc is not None:
            return None
        return FinestraComandi(self, prof)

    def prendi_precedente(self) -> None:
        """Dischi, installazioni e salvataggi dalla cartella di una versione precedente (comando "importa-cartella")."""
        d = filedialog.askdirectory(title=T('Scegli la cartella della versione precedente (EnterElectro-Recomp o SM2-Recomp)',
                                            'Choose the folder of the earlier version (EnterElectro-Recomp or SM2-Recomp)'),
                                    initialdir=str(L.ROOT.parent))
        if not d:
            return
        if not messagebox.askyesno(T('Prendi da una versione precedente', 'Import from an earlier version'),
                                   T(f'Dischi, installazioni e salvataggi di\n{d}\nverranno spostati in questa cartella. '
                                     'La cartella vecchia resta. Continuare?',
                                     f'The discs, installations and saves of\n{d}\nwill be moved into this folder. The '
                                     'old folder stays. Continue?')):
            return
        self.esegui(['importa-cartella', d], T('Prendo dischi e salvataggi dalla versione precedente',
                                               'Importing discs and saves from the earlier version'))

    def apri_cartella(self) -> None:
        prof = self.profilo_scelto()
        if prof and (L.GIOCHI / prof).is_dir() and os.name == 'nt':
            os.startfile(str(L.GIOCHI / prof))  # noqa: S606

    def chiudi(self) -> None:
        lav = self.lavoro_filmati if self.proc is not None else None
        if lav and lav[1] in L.MODELLI_IA:
            if not messagebox.askyesno(
                    T('Uscire', 'Exit'), T('Si stanno preparando i filmati IA: chiudendo la finestra la preparazione si '
                                           'ferma, e la prossima volta riprende da dove era. Uscire?',
                                           'The AI movies are being prepared: closing the window stops the preparation, '
                                           'and the next time it resumes where it was. Exit?')):
                return
            ferma_filmati_ia(L.GIOCHI / lav[0], lav[1])
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        elif self.proc is not None and not messagebox.askyesno(
                T('Uscire', 'Exit'), T('Un comando e\' ancora in corso: chiudendo la finestra lo interrompi. Uscire lo '
                                       'stesso?', 'A command is still running: closing the window stops it. Exit '
                                                  'anyway?')):
            return
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
        self.root.destroy()


# -------------------------------------------------------------------------------- scheda dei salvataggi (0.12)

class PannelloSalvataggi:
    """Memory card e salvataggi rapidi della versione scelta: cosa c'e' dentro (titoli, icone, anteprime), copie di
    sicurezza, ripristino di una copia, una memory card presa da un altro file. Le azioni passano dal comando
    "salvataggi" (come la riga di comando); niente si cancella."""

    def __init__(self, finestra, dove):
        import tempfile
        self.f = finestra
        self.prof = None
        self.immagini = []
        self.tmp = Path(tempfile.mkdtemp(prefix='sm2_salvataggi_'))
        su = ttk.Frame(dove)
        su.pack(fill='x')
        self.cartella = tk.StringVar(value='')
        ttk.Button(su, text=T('Apri la cartella dei salvataggi', 'Open the saves folder'),
                   command=self.apri).pack(side='right')
        ttk.Button(su, text=T('Copia di sicurezza delle memory card', 'Back up the memory cards'),
                   command=self.copia).pack(side='right', padx=(0, 8))
        ttk.Button(su, text=T('Copia le partite in un\'altra versione...', 'Copy the saved games to another version...'),
                   command=self.copia_in).pack(side='right', padx=(0, 8))
        ttk.Label(su, textvariable=self.cartella, foreground=COL['testo2'], wraplength=int(430 * finestra.scala),
                  justify='left').pack(side='left', fill='x', expand=True)
        righe = ttk.Frame(dove)
        righe.pack(fill='x', pady=(6, 0))
        self.card = []
        for i in (1, 2):
            fr = ttk.LabelFrame(righe, text=f'Memory card {i}', padding=(6, 4))
            fr.grid(row=0, column=i - 1, sticky='nsew', padx=(0, 8) if i == 1 else 0)
            righe.columnconfigure(i - 1, weight=1)
            tv = ttk.Treeview(fr, columns=('codice', 'blocchi'), show='tree headings', height=5, selectmode='none')
            tv.heading('#0', text=T('Salvataggio', 'Save'))
            tv.heading('codice', text=T('Versione', 'Version'))
            tv.heading('blocchi', text=T('Blocchi', 'Blocks'))
            tv.column('#0', width=260)
            tv.column('codice', width=150)
            tv.column('blocchi', width=60, anchor='e')
            tv.pack(fill='x')
            info = tk.StringVar(value='')
            ttk.Label(fr, textvariable=info).pack(anchor='w', pady=(2, 0))
            bt = ttk.Frame(fr)
            bt.pack(fill='x', pady=(4, 0))
            ttk.Button(bt, text=T('Ripristina una copia...', 'Restore a backup...'),
                       command=lambda i=i: self.ripristina(i, True)).pack(side='left')
            ttk.Button(bt, text=T('Usa un\'altra memory card...', 'Use another memory card...'),
                       command=lambda i=i: self.ripristina(i, False)).pack(side='left', padx=(8, 0))
            self.card.append({'tv': tv, 'info': info})
        fr = ttk.LabelFrame(dove, text=T('Salvataggi rapidi (F7 nel gioco)', 'Save states (F7 in the game)'), padding=(6, 4))
        fr.pack(fill='x', pady=(8, 0))
        self.rapidi = ttk.Frame(fr)
        self.rapidi.pack(fill='x')
        self.nessuno = tk.StringVar(value='')
        ttk.Label(fr, textvariable=self.nessuno, foreground=COL['testo2']).pack(anchor='w')

    def _immagine(self, nome: str, dati: bytes):
        f = self.tmp / nome
        f.write_bytes(dati)
        img = tk.PhotoImage(file=str(f))
        self.immagini.append(img)
        return img

    def aggiorna(self, prof) -> None:
        self.prof = prof
        self.immagini = []
        cart = L.GIOCHI / prof if prof else None
        for c in self.card:
            c['tv'].delete(*c['tv'].get_children())
            c['info'].set('')
        for w in self.rapidi.winfo_children():
            w.destroy()
        if not cart or not cart.is_dir():
            self.cartella.set(T('Questa versione non e\' installata.', 'This version is not installed.'))
            self.nessuno.set('')
            return
        base = S.cartella_memory_card(cart)
        self.cartella.set(T(f'{prof}: salvataggi in {base}', f'{prof}: saves in {base}'))
        for i, (c, path) in enumerate(zip(self.card, S.percorsi_memory_card(cart)), 1):
            r = S.leggi_memory_card(path)
            if not r['ok']:
                c['info'].set({'manca': T('Non ancora creata: la crea il gioco.', 'Not created yet: the game creates it.'),
                               'non formattata': T('Non formattata.', 'Not formatted.')}.get(
                                   r['motivo'], T('Formato sconosciuto.', 'Unknown format.')))
                continue
            for k, x in enumerate(r['salvataggi']):
                img = self._immagine(f'icona_{i}_{k}.ppm', S.ppm(16, 16, x['icona'], 1)) if x.get('icona') else ''
                c['tv'].insert('', 'end', text=' ' + (x['titolo'] or x['file']), image=img,
                               values=(x['codice'] + (f' ({x["regione"]})' if x['regione'] else ''), x['blocchi']))
            copie = S.copie_di_sicurezza(path)
            c['info'].set(T(f'{len(r["salvataggi"])} salvataggi, {r["liberi"]} blocchi liberi su 15',
                            f'{len(r["salvataggi"])} saves, {r["liberi"]} free blocks of 15') +
                          (T(f'; copie di sicurezza: {len(copie)}', f'; backups: {len(copie)}') if copie else ''))
        rap = S.salvataggi_rapidi(cart)
        self.nessuno.set('' if rap else T('Nessun salvataggio rapido: nel gioco F7 apre il menu dei salvataggi rapidi.',
                                          'No save states: in the game F7 opens the save state menu.'))
        for n, x in enumerate(rap[:12]):
            img = ''
            if x['anteprima']:
                a = S.leggi_anteprima(x['anteprima'])
                if a:
                    img = self._immagine(f'anteprima_{n}.ppm', S.ppm(*a))
            e = ttk.Label(self.rapidi, image=img, compound='top',
                          text=f'slot {x["slot"]}  {x["data"]:%d/%m %H:%M}')
            e.grid(row=n // 6, column=n % 6, padx=4, pady=4)

    def copia(self) -> None:
        if self.prof:
            self.f.esegui(['salvataggi', '--profilo', self.prof, '--copia'],
                          T(f'Copia di sicurezza delle memory card di {self.prof}', f'Backing up the memory cards of {self.prof}'))

    def scelte_copia_in(self) -> tuple:
        """(memory card con le partite di questa versione o None, righe delle altre versioni installate con partite
        diverse, motivo se non si puo')."""
        if not self.prof:
            return None, [], ''
        cart = L.GIOCHI / self.prof
        card = next((i for i, c in enumerate(S.percorsi_memory_card(cart), 1) if S.ha_partite(c, self.prof)), None)
        if card is None:
            return None, [], T(f'Nelle memory card di {self.prof} non ci sono partite di Spider-Man 2 da copiare.',
                               f'The memory cards of {self.prof} have no Spider-Man 2 saved games to copy.')
        mio = S.NOME_SALVATAGGIO.get(self.prof)
        altre = [r for r in self.f.righe if r['profilo'] != self.prof and (L.GIOCHI / r['profilo']).is_dir() and
                 S.NOME_SALVATAGGIO.get(r['profilo']) not in (None, mio)]
        if not altre:
            return card, [], T('Non c\'e\' un\'altra versione installata con partite diverse da questa (le due USA e le '
                               'due europee in inglese usano gia\' le stesse).', 'There is no other installed version '
                               'with saved games different from this one (the two US and the two English European '
                               'versions already share them).')
        return card, altre, ''

    def finestra_copia_in(self, card: int, altre: list) -> tuple:
        """La finestrella della scelta della versione: (finestra, esito); esito['dest'] dopo "Copia"."""
        top = tk.Toplevel(self.f.root)
        top.title(T('Copia le partite in un\'altra versione', 'Copy the saved games to another version'))
        top.transient(self.f.root)
        try:
            top.configure(bg=COL['fondo'])
        except tk.TclError:
            pass
        fr = ttk.Frame(top, padding=14)
        fr.pack(fill='both', expand=True)
        largo = int(460 * self.f.scala)
        ttk.Label(fr, text=T(f'Le partite di {self.prof} (memory card {card}) in quale versione?',
                             f'Copy the saved games of {self.prof} (memory card {card}) to which version?'),
                  wraplength=largo).pack(anchor='w')
        voci = [f'{r["profilo"]} - {r["nome"]}' for r in altre]
        scelta = tk.StringVar(value=voci[0])
        ttk.Combobox(fr, textvariable=scelta, state='readonly', width=46, values=voci).pack(anchor='w', pady=(8, 8))
        ttk.Label(fr, text=T('Vanno nella memory card 1 di quella versione, o nella 2 se la 1 ha gia\' le sue partite; la '
                             'memory card che cambia va prima nelle copie di sicurezza. Nel gioco: MEMORY CARD, poi '
                             '"load game data". Chiudi il gioco prima di continuare.',
                             'They go to memory card 1 of that version, or to card 2 if card 1 already has its own saved '
                             'games; the memory card that changes is backed up first. In the game: MEMORY CARD, then '
                             '"load game data". Close the game before continuing.'),
                  wraplength=largo, foreground=COL['testo2']).pack(anchor='w')
        esito = {}

        def ok():
            esito['dest'] = scelta.get().split(' - ', 1)[0]
            top.destroy()
        bt = ttk.Frame(fr)
        bt.pack(fill='x', pady=(12, 0))
        ttk.Button(bt, text=T('Copia', 'Copy'), command=ok).pack(side='right')
        ttk.Button(bt, text=T('Annulla', 'Cancel'), command=top.destroy).pack(side='right', padx=(0, 8))
        return top, esito

    def copia_in(self) -> None:
        """0.12: le partite di Spider-Man 2 di questa versione nella memory card di un'altra versione installata, con il
        nome che quella versione cerca (comando "salvataggi --copia-in")."""
        if not self.prof or self.f.proc is not None:
            return
        card, altre, motivo = self.scelte_copia_in()
        if motivo:
            messagebox.showinfo(T('Copia le partite in un\'altra versione', 'Copy the saved games to another version'),
                                motivo)
            return
        top, esito = self.finestra_copia_in(card, altre)
        top.grab_set()
        top.wait_window()
        dest = esito.get('dest')
        if dest:
            self.f.esegui(['salvataggi', '--profilo', self.prof, '--card', str(card), '--copia-in', dest],
                          T(f'Partite di {self.prof} copiate in {dest}', f'Saved games of {self.prof} copied to {dest}'))

    def ripristina(self, i: int, da_copie: bool) -> None:
        if not self.prof or self.f.proc is not None:
            return
        cart = L.GIOCHI / self.prof
        card = S.percorsi_memory_card(cart)[i - 1]
        iniziale = card.parent / 'copie' if da_copie and (card.parent / 'copie').is_dir() else Path.home()
        p = filedialog.askopenfilename(title=T(f'Memory card {i}: scegli il file', f'Memory card {i}: choose the file'),
                                       initialdir=str(iniziale), filetypes=[
            (T('Memory card PS1', 'PS1 memory cards'), ' '.join('*' + e for e in S.ESTENSIONI_CARD)),
            (T('Tutti i file', 'All files'), '*.*')])
        if not p:
            return
        if not messagebox.askyesno(T('Memory card', 'Memory card'),
                                   T(f'La memory card {i} di {self.prof} diventa\n{p}\nQuella di adesso va prima nelle copie '
                                     'di sicurezza. Chiudi il gioco prima di continuare. Continuare?',
                                     f'Memory card {i} of {self.prof} becomes\n{p}\nThe current one goes to the backups '
                                     'first. Close the game before continuing. Continue?')):
            return
        self.f.esegui(['salvataggi', '--profilo', self.prof, '--ripristina', p, '--card', str(i)],
                      T(f'Memory card {i} di {self.prof}', f'Memory card {i} of {self.prof}'))

    def apri(self) -> None:
        if self.prof and os.name == 'nt':
            base = S.cartella_memory_card(L.GIOCHI / self.prof)
            if base.is_dir():
                os.startfile(str(base))  # noqa: S606


# -------------------------------------------------------------------------------- finestra dei comandi (0.12)

def nome_sorgente(v: str, etichette: dict) -> str:
    """Un valore di input.ini in parole: a -> Croce (sui controller PlayStation) o A, leftx- -> levetta sinistra a
    sinistra; piu' valori separati da virgole."""
    out = []
    for p in str(v).split(','):
        p = p.strip().lower()
        if not p:
            continue
        base = p[:-1] if p[-1:] in '+-' and p[:-1] in ('lefttrigger', 'righttrigger') else p
        if base in ('a', 'b', 'x', 'y'):
            et = (etichette or {}).get(base)
            pos = {'a': 'cross', 'b': 'circle', 'x': 'square', 'y': 'triangle'}[base]
            out.append(FACCE.get(et) or f'{FACCE[pos]} / {base.upper()}')
        else:
            out.append(SORGENTI.get(base, base))
    return ', '.join(out) or SORGENTI['none']


def testo_ascii(t: str) -> str:
    """Le scritte della finestrella di sm2_pad hanno solo i caratteri ASCII (carattere di SDL)."""
    import unicodedata
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode('ascii')


class FinestraComandi:
    """Comandi del giocatore 1 (0.12): quale controller, analogico o digitale, zona morta, tasti del controller e della
    tastiera per ogni comando della PS1, con la prova dal vivo. Legge i file accanto all'eseguibile (sm2_comandi) e
    salva con il comando "opzioni", come la riga di comando. Il controller si legge con tools/pad/sm2_pad, che usa la
    stessa SDL3 del gioco: "ascolta" mentre la finestra e' aperta, "tasto" per la tastiera."""

    def __init__(self, padre, prof: str):
        self.padre, self.prof = padre, prof
        self.cartella = L.GIOCHI / prof
        dirs = [d for d in (self.cartella / 'build-release', self.cartella / 'build-dev') if L.trova_exe(d)]
        conf = C.leggi(dirs[0]) if dirs else C.leggi(self.cartella)
        self.pad = C.pad_effettivo(conf)
        self.tastiera = dict(conf['tastiera'])
        self.controller_salvato = conf['controller']
        self.coda: queue.Queue = queue.Queue()
        self.exe = None
        self.proc = None
        self.pads = {}            # id -> nome, tipo, guid, etichette
        self.giu = set()          # (id, tasto) premuti
        self.assi = {}            # (id, asse) -> valore
        self.cattura = None       # (chiave, scadenza) mentre si aspetta un tasto del controller
        self.occupato = False     # finestrella della tastiera aperta
        self.vivo = True
        top = self.top = tk.Toplevel(padre.root)
        top.title(T(f'Comandi - {prof}', f'Controls - {prof}'))
        top.transient(padre.root)
        scala = max(1.0, top.winfo_fpixels('1i') / 96.0)
        self.scala = scala
        s = ttk.Style(top)
        s.configure('Premuto.TLabel', background=COL['premuto'], foreground='#ffffff')
        s.configure('Valore.TLabel', relief='solid', padding=(4, 1), background=COL['campo'],
                    bordercolor=COL['bordo'])
        s.configure('ValorePremuto.TLabel', relief='solid', padding=(4, 1), background=COL['premuto'],
                    foreground='#ffffff', bordercolor=COL['bordo'])
        try:
            top.configure(bg=COL['fondo'])
        except tk.TclError:
            pass
        barra_scura(top)

        su = ttk.Frame(top, padding=(12, 10, 12, 4))
        su.pack(fill='x')
        e = ttk.Label(su, text=T('Controller del giocatore 1:', 'Player 1 gamepad:'))
        e.grid(row=0, column=0, sticky='w')
        self.scelta = tk.StringVar()
        self.cb = ttk.Combobox(su, textvariable=self.scelta, state='readonly', width=44)
        self.cb.grid(row=0, column=1, sticky='w', padx=(6, 18))
        for w in (e, self.cb):
            Suggerimento(w, SUGG['cmd_controller'])
        self.modo = tk.StringVar(value=conf['modo'])
        r1 = ttk.Radiobutton(su, text=T('Analogico', 'Analog'), value='analog', variable=self.modo)
        r2 = ttk.Radiobutton(su, text=T('Digitale', 'Digital'), value='digital', variable=self.modo)
        r1.grid(row=0, column=2, sticky='w')
        r2.grid(row=0, column=3, sticky='w', padx=(6, 18))
        for w in (r1, r2):
            Suggerimento(w, SUGG['cmd_modo'])
        e2 = ttk.Label(su, text=T('Zona morta (%):', 'Dead zone (%):'))
        e2.grid(row=0, column=4, sticky='w')
        self.zona = tk.IntVar(value=round(100 * conf['zona_morta'] / 32767))
        sp = ttk.Spinbox(su, from_=0, to=50, textvariable=self.zona, width=4)
        sp.grid(row=0, column=5, sticky='w', padx=(6, 0))
        for w in (e2, sp):
            Suggerimento(w, SUGG['cmd_zona'])
        self.info = tk.StringVar(value=T('Cerco i controller...', 'Looking for gamepads...'))
        ttk.Label(top, textvariable=self.info, padding=(12, 0)).pack(anchor='w')

        mezzo = ttk.Frame(top, padding=(12, 6))
        mezzo.pack(fill='both', expand=True)
        self.righe = {}
        gruppi = ((T('Tasti', 'Buttons'), C.CHIAVI[:12]), (T('Levette e altri tasti', 'Sticks and other buttons'),
                                                            C.CHIAVI[12:]))
        for col, (titolo, chiavi) in enumerate(gruppi):
            f = ttk.LabelFrame(mezzo, text=titolo, padding=(8, 4))
            f.grid(row=0, column=col, sticky='nsew', padx=(0, 10) if col == 0 else 0)
            for c, testo in enumerate((T('Comando PS1', 'PS1 control'), T('Controller', 'Gamepad'), '',
                                       T('Tastiera', 'Keyboard'), '')):
                ttk.Label(f, text=testo, foreground=COL['testo2']).grid(row=0, column=c, sticky='w', padx=(0, 6))
            for i, k in enumerate(chiavi, 1):
                nome = next(T(it, en) for kk, it, en in C.COMANDI if kk == k)
                e = ttk.Label(f, text=nome)
                e.grid(row=i, column=0, sticky='w', padx=(0, 6), pady=1)
                vp = ttk.Label(f, style='Valore.TLabel', width=24)
                vp.grid(row=i, column=1, sticky='w', padx=(0, 2), pady=1)
                bp = ttk.Button(f, text=T('Controller...', 'Gamepad...'), width=12,
                                command=lambda k=k: self.cattura_pad(k))
                bp.grid(row=i, column=2, sticky='w', padx=(0, 8), pady=1)
                vt = ttk.Label(f, style='Valore.TLabel', width=12)
                vt.grid(row=i, column=3, sticky='w', padx=(0, 2), pady=1)
                bt = ttk.Button(f, text=T('Tastiera...', 'Keyboard...'), width=11,
                                command=lambda k=k: self.cattura_tastiera(k))
                bt.grid(row=i, column=4, sticky='w', pady=1)
                self.righe[k] = {'nome': e, 'pad': vp, 'bp': bp, 'tastiera': vt, 'bt': bt}
        mezzo.columnconfigure(0, weight=1)
        mezzo.columnconfigure(1, weight=1)
        self.avviso = tk.StringVar(value='')
        ttk.Label(top, textvariable=self.avviso, foreground=COL['avviso'], padding=(12, 0),
                  wraplength=int(1000 * scala)).pack(anchor='w')
        ttk.Label(top, text=T('Controller...: premi il tasto o muovi la levetta sul controller entro 5 secondi (Esc '
                              'annulla). Tastiera...: si apre una finestrella, premi il tasto. Tenendo premuto un tasto '
                              'del controller, la riga del comando si colora: cos\u00ec provi tutto prima di giocare.',
                              'Gamepad...: press the button or move the stick on the gamepad within 5 seconds (Esc '
                              'cancels). Keyboard...: a small window opens, press the key. While you hold a gamepad '
                              'button, the row of the control lights up: so you can try everything before playing.'),
                  foreground=COL['testo2'], padding=(12, 2), wraplength=int(1000 * scala)).pack(anchor='w')
        giu = ttk.Frame(top, padding=(12, 8))
        giu.pack(fill='x')
        ttk.Button(giu, text=T('Ripristina i predefiniti', 'Restore defaults'), command=self.predefiniti).pack(side='left')
        ttk.Button(giu, text=T('Salva', 'Save'), command=self.salva).pack(side='right')
        ttk.Button(giu, text=T('Annulla', 'Cancel'), command=self.chiudi).pack(side='right', padx=(0, 8))
        top.protocol('WM_DELETE_WINDOW', self.chiudi)
        top.bind('<Escape>', self._esc)
        self.aggiorna_scelte()
        self.mostra()
        top.grab_set()
        threading.Thread(target=self._avvia_lettore, daemon=True).start()
        top.after(40, self._ciclo)

    # ---------------------------------------------------------------- controller collegati
    def _avvia_lettore(self) -> None:
        """Compila sm2_pad se serve (pochi secondi la prima volta) e lancia "ascolta"; le righe vanno nella coda."""
        righe = []
        try:
            L.attiva_toolchain()
            self.exe = C.strumento_pad(L.TOOLS, L.TOOLCHAIN, righe.append, T)
        except Exception as e:  # noqa: BLE001
            righe.append(str(e))
            self.exe = None
        if self.exe is None or not self.vivo:
            self.coda.put(('errore', ' '.join(righe)[-300:] or T('sm2_pad non disponibile', 'sm2_pad not available')))
            return
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            self.proc = subprocess.Popen([str(self.exe), 'ascolta', '3600'], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=flags)
        except OSError as e:
            self.coda.put(('errore', str(e)))
            return
        for riga in self.proc.stdout:
            try:
                self.coda.put(('ev', json.loads(riga.decode('utf-8', 'replace'))))
            except ValueError:
                pass
        self.coda.put(('ev', {'ev': 'fine'}))

    def _ciclo(self) -> None:
        if not self.vivo:
            return
        cambiato = False
        try:
            while True:
                tipo, dato = self.coda.get_nowait()
                cambiato = True
                if tipo == 'errore':
                    self.info.set(T('Lettore dei controller non disponibile: ', 'Gamepad reader not available: ') + dato)
                    for r in self.righe.values():
                        r['bp'].state(['disabled'])
                        r['bt'].state(['disabled'])
                elif tipo == 'tastiera':
                    self._fine_tastiera(*dato)
                elif tipo == 'ev':
                    self._evento(dato)
        except queue.Empty:
            pass
        if self.cattura and time.time() > self.cattura[1]:
            self.cattura = None
            self.avviso.set(T('Nessun tasto premuto: comando lasciato com\'era.', 'No button pressed: control left as it was.'))
            cambiato = True
        if cambiato:
            self.mostra()
        self.top.after(40, self._ciclo)

    def _evento(self, ev: dict) -> None:
        tipo = ev.get('ev')
        if tipo == 'pronto':
            self.info.set(T(f'SDL {ev.get("sdl")}: nessun controller collegato (collegane uno quando vuoi).',
                            f'SDL {ev.get("sdl")}: no gamepad connected (plug one in whenever you like).'))
        elif tipo == 'pad':
            self.pads[ev['id']] = ev
            self.aggiorna_scelte()
        elif tipo == 'via':
            self.pads.pop(ev.get('id'), None)
            self.giu = {x for x in self.giu if x[0] != ev.get('id')}
            self.aggiorna_scelte()
        elif tipo == 'tasto':
            chiave = (ev['id'], ev['tasto'])
            if ev.get('giu'):
                self.giu.add(chiave)
                if self.cattura and self._pad_giusto(ev['id']):
                    self._catturato(ev['tasto'])
            else:
                self.giu.discard(chiave)
        elif tipo == 'asse':
            self.assi[(ev['id'], ev['asse'])] = ev['v']
            if self.cattura and self._pad_giusto(ev['id']) and abs(ev['v']) >= 20000:
                if ev['asse'] in ('lefttrigger', 'righttrigger'):
                    self._catturato(ev['asse'])
                else:
                    self._catturato(ev['asse'] + ('-' if ev['v'] < 0 else '+'))
        elif tipo == 'fine' and self.vivo and self.proc is not None and self.proc.poll() is not None:
            self.info.set(T('Il lettore dei controller si e\' chiuso.', 'The gamepad reader closed.'))

    def aggiorna_scelte(self) -> None:
        """L'elenco della scelta del controller: primo collegato, solo tastiera, i controller collegati adesso e quello
        salvato se non e' collegato."""
        voci = [(T('Primo collegato (consigliato)', 'First connected (recommended)'), 'auto'),
                (T('Solo tastiera', 'Keyboard only'), 'keyboard')]
        visti = set()
        for p in sorted(self.pads.values(), key=lambda x: x['id']):
            g = str(p.get('guid', '')).lower()
            if g and g not in visti:
                visti.add(g)
                voci.append((f'{p.get("nome")} ({p.get("tipo")})', g))
        att = self.valore_scelto() or self.controller_salvato
        if C.GUID_RE.match(str(att)) and att.lower() not in visti:
            voci.append((T(f'Controller salvato, non collegato ({att[:8]}...)', f'Saved gamepad, not connected ({att[:8]}...)'),
                         att.lower()))
        self.voci = voci
        self.cb.configure(values=[e for e, _ in voci])
        self.scelta.set(next((e for e, v in voci if v == str(att).lower()), voci[0][0]))
        n = len(self.pads)
        if n:
            self.info.set(T(f'Controller collegati: {n} (' + ', '.join(p['nome'] for p in self.pads.values()) + ')',
                            f'Gamepads connected: {n} (' + ', '.join(p['nome'] for p in self.pads.values()) + ')'))

    def valore_scelto(self) -> str:
        return dict(getattr(self, 'voci', [])).get(self.scelta.get(), '')

    def _pad_giusto(self, pid) -> bool:
        v = self.valore_scelto()
        if C.GUID_RE.match(v):
            return str(self.pads.get(pid, {}).get('guid', '')).lower() == v
        return True

    def etichette(self) -> dict:
        v = self.valore_scelto()
        for p in self.pads.values():
            if not C.GUID_RE.match(v) or str(p.get('guid', '')).lower() == v:
                return p.get('etichette') or {}
        return {}

    # ---------------------------------------------------------------- cattura
    def cattura_pad(self, k: str) -> None:
        if self.occupato:
            return
        self.cattura = (k, time.time() + 5)
        self.avviso.set(T('Premi il tasto o muovi la levetta sul controller per: ', 'Press the button or move the stick on '
                          'the gamepad for: ') + self.righe[k]['nome'].cget('text') + T(' (Esc annulla)', ' (Esc cancels)'))
        self.mostra()

    def _catturato(self, valore: str) -> None:
        k = self.cattura[0]
        self.cattura = None
        self.pad[k] = valore
        self.avviso.set(self.doppi())
        self.mostra()

    def _esc(self, _evento=None) -> None:
        if self.cattura:
            self.cattura = None
            self.avviso.set(T('Annullato.', 'Cancelled.'))
            self.mostra()

    def cattura_tastiera(self, k: str) -> None:
        if self.occupato or self.exe is None:
            return
        self.occupato = True
        self.cattura = None
        nome = self.righe[k]['nome'].cget('text')
        self.avviso.set(T('Premi il tasto nella finestrella per: ', 'Press the key in the small window for: ') + nome)
        for r in self.righe.values():
            r['bt'].state(['disabled'])
        testo = testo_ascii(T(f'Premi il tasto per: {nome}', f'Press the key for: {nome}'))
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        def lavoro():
            try:
                p = subprocess.run([str(self.exe), 'tasto', testo, '6'], capture_output=True, timeout=30,
                                   creationflags=flags)
                righe = [x for x in p.stdout.decode('utf-8', 'replace').splitlines() if x.strip().startswith('{')]
                ris = json.loads(righe[-1]) if righe else {}
            except Exception as e:  # noqa: BLE001
                ris = {'errore': str(e)}
            self.coda.put(('tastiera', (k, ris)))
        threading.Thread(target=lavoro, daemon=True).start()

    def _fine_tastiera(self, k: str, ris: dict) -> None:
        self.occupato = False
        for r in self.righe.values():
            r['bt'].state(['!disabled'])
        if 'tasto' in ris:
            self.tastiera[k] = ris['tasto']
            msg = self.doppi()
            if ris['tasto'] in C.TASTI_DEL_GIOCO:
                msg = (msg + ' ' if msg else '') + T(f'Il tasto {ris["tasto"]} lo usa gia\' il gioco '
                                                     f'({C.TASTI_DEL_GIOCO[ris["tasto"]]}).',
                                                     f'The key {ris["tasto"]} is already used by the game '
                                                     f'({C.TASTI_DEL_GIOCO[ris["tasto"]]}).')
            self.avviso.set(msg)
        elif ris.get('scaduto'):
            self.avviso.set(T('Nessun tasto premuto: comando lasciato com\'era.', 'No key pressed: control left as it was.'))
        elif ris.get('annullato'):
            self.avviso.set(T('Annullato.', 'Cancelled.'))
        else:
            self.avviso.set(T('Finestrella della tastiera non riuscita: ', 'Keyboard window failed: ') + str(ris)[:200])
        try:
            self.top.focus_force()
        except tk.TclError:
            pass
        self.mostra()

    def doppi(self) -> str:
        parti = []
        for v, ks in C.doppioni(self.pad).items():
            parti.append(T(f'Sul controller "{nome_sorgente(v, self.etichette())}" fa piu\' comandi: ',
                           f'On the gamepad "{nome_sorgente(v, self.etichette())}" does more than one control: ') +
                         ', '.join(self.righe[k]['nome'].cget('text') for k in ks) + '.')
        for v, ks in C.doppioni(self.tastiera, True).items():
            parti.append(T(f'Il tasto {v} fa piu\' comandi: ', f'The key {v} does more than one control: ') +
                         ', '.join(self.righe[k]['nome'].cget('text') for k in ks) + '.')
        return ' '.join(parti)

    # ---------------------------------------------------------------- disegno
    def attivo(self, sorgenti: str) -> bool:
        """Il comando e' premuto adesso sul controller? Con le regole del gioco: tasti, assi oltre la zona morta."""
        zona = max(0, min(50, self._zona())) * 32767 / 100
        for p in str(sorgenti).split(','):
            p = p.strip().lower()
            if not p or p == 'none':
                continue
            segno = p[-1] if p[-1:] in '+-' else ''
            base = p[:-1] if segno else p
            if base in ('leftx', 'lefty', 'rightx', 'righty', 'lefttrigger', 'righttrigger'):
                for (pid, asse), v in self.assi.items():
                    if asse == base and self._pad_giusto(pid):
                        if (segno == '-' and v < -zona) or (segno != '-' and v > zona):
                            return True
            elif any(t == base and self._pad_giusto(pid) for pid, t in self.giu):
                return True
        return False

    def _zona(self) -> int:
        try:
            return int(self.zona.get())
        except (tk.TclError, ValueError):
            return 10

    def mostra(self) -> None:
        et = self.etichette()
        for k, r in self.righe.items():
            if self.cattura and self.cattura[0] == k:
                r['pad'].configure(text=T(f'premi... ({max(0, int(self.cattura[1] - time.time()) + 1)} s)',
                                          f'press... ({max(0, int(self.cattura[1] - time.time()) + 1)} s)'))
            else:
                r['pad'].configure(text=nome_sorgente(self.pad.get(k, ''), et))
            tk_v = self.tastiera.get(k, '')
            r['tastiera'].configure(text=T('nessuno', 'none') if tk_v.strip().lower() == 'none' else tk_v)
            premuto = self.attivo(self.pad.get(k, ''))
            r['nome'].configure(style='Premuto.TLabel' if premuto else 'TLabel')
            r['pad'].configure(style='ValorePremuto.TLabel' if premuto else 'Valore.TLabel')

    # ---------------------------------------------------------------- pulsanti
    def predefiniti(self) -> None:
        self.pad = dict(C.PAD_PREDEFINITI)
        self.tastiera = dict(C.TASTIERA_PREDEFINITI)
        self.modo.set('analog')
        self.zona.set(10)
        self.avviso.set(T('Comandi come li ha il gioco (non ancora salvati: premi Salva).',
                          'Controls as the game has them (not saved yet: press Save).'))
        self.mostra()

    def salva(self) -> None:
        if self.padre.proc is not None:
            self.avviso.set(T('Un comando del launcher e\' ancora in corso: riprova tra poco.',
                              'A launcher command is still running: try again in a moment.'))
            return
        f = self.cartella / 'comandi_dalla_finestra.json'
        try:
            f.write_text(json.dumps({'pad': self.pad, 'tastiera': self.tastiera}, indent=1, ensure_ascii=False),
                         encoding='utf-8')
        except OSError as e:
            self.avviso.set(str(e))
            return
        ctrl = self.valore_scelto() or 'auto'
        arg = ['opzioni', '--profilo', self.prof, '--controller', 'tastiera' if ctrl == 'keyboard' else ctrl,
               '--modo-pad', 'analogico' if self.modo.get() == 'analog' else 'digitale',
               '--zona-morta', str(max(0, min(50, self._zona()))), '--comandi', str(f)]
        self.chiudi()
        self.padre.esegui(arg, T(f'Salvo i comandi di {self.prof}', f'Saving the controls of {self.prof}'))

    def chiudi(self) -> None:
        self.vivo = False
        p, self.proc = self.proc, None
        if p is not None and p.poll() is None:
            try:
                p.stdin.write(b'esci\n')
                p.stdin.close()
            except OSError:
                pass
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
        try:
            self.top.grab_release()
            self.top.destroy()
        except tk.TclError:
            pass


# -------------------------------------------------------------------------------- finestra PGXP (0.12)

class FinestraPGXP:
    """Le voci di PGXP come in DuckStation (Impostazioni > Grafica > PGXP), con gli stessi valori di partenza. Le
    scelte vanno nella finestra principale e si salvano con Gioca, come le altre opzioni (comando "opzioni")."""

    def __init__(self, padre):
        self.padre = padre
        o = dict(L.pgxp_predefiniti(), **padre.pgxp_opz)
        prof = padre.profilo_scelto()
        try:
            st = json.loads((L.GIOCHI / prof / 'installazione.json').read_text(encoding='utf-8')) if prof else {}
        except (OSError, ValueError):
            st = {}
        top = self.top = tk.Toplevel(padre.root)
        top.title(T('Opzioni PGXP', 'PGXP options') + (f' - {prof}' if prof else ''))
        top.transient(padre.root)
        scala = max(1.0, top.winfo_fpixels('1i') / 96.0)
        try:
            top.configure(bg=COL['fondo'])
        except tk.TclError:
            pass
        barra_scura(top)
        su = ttk.Frame(top, padding=(14, 12, 14, 4))
        su.pack(fill='x')
        self.acceso = tk.BooleanVar(value=bool(padre.pgxp.get()))
        c = ttk.Checkbutton(su, text=T('PGXP acceso: correzione della geometria (Geometry Correction)',
                                       'PGXP on: Geometry Correction'), variable=self.acceso,
                            command=self.mostra_stato)
        c.pack(anchor='w')
        Suggerimento(c, SUGG['pgxp'])
        if prof:
            ha = bool(st.get('pgxp'))
            testo = (T(f'{prof}: l\'installazione ha i punti di aggancio di PGXP, tutte le voci funzionano.',
                       f'{prof}: the installation has the PGXP hooks, every item works.') if ha else
                     T(f'{prof}: l\'installazione non ha i punti di aggancio di PGXP. Con PGXP acceso, Gioca la '
                       'ricompila una volta (salvataggi e opzioni restano); senza, PGXP non corregge quasi niente.',
                       f'{prof}: the installation does not have the PGXP hooks. With PGXP on, Play builds it again '
                       'once (saves and options stay); without them PGXP corrects almost nothing.'))
            ttk.Label(su, text=testo, foreground=COL['testo2'] if ha else COL['avviso'],
                      wraplength=int(560 * scala), justify='left').pack(anchor='w', pady=(4, 0))
        mezzo = ttk.LabelFrame(top, text=T('Voci di DuckStation', 'DuckStation items'), padding=(12, 6))
        mezzo.pack(fill='both', expand=True, padx=14, pady=(6, 0))
        nomi = {'texture': T('Texture in prospettiva (Texture Correction)', 'Texture Correction'),
                'colori': T('Colori in prospettiva (Color Correction)', 'Color Correction'),
                'culling': T('Correzione del culling (Culling Correction)', 'Culling Correction'),
                'proiezione': T('Precisione della proiezione (Preserve Projection Precision)',
                                'Preserve Projection Precision'),
                'cpu': T('Modalit\u00e0 CPU (CPU Mode)', 'CPU Mode'),
                'cache': T('Cache dei vertici (Vertex Cache)', 'Vertex Cache'),
                'profondita': T('Buffer di profondit\u00e0 (Depth Buffer, bassa compatibilit\u00e0)',
                                'Depth Buffer (low compatibility)'),
                'no2d': T('Niente PGXP sui poligoni 2D (Disable on 2D Polygons)', 'Disable on 2D Polygons'),
                'trasparenti': T('Profondit\u00e0 anche per i semitrasparenti (Depth Test Transparent Polygons)',
                                 'Depth Test Transparent Polygons')}
        self.v = {}
        self.caselle = []
        for i, (k, _v, _c) in enumerate(L.PGXP_VOCI):
            self.v[k] = tk.BooleanVar(value=bool(o[k]))
            cb = ttk.Checkbutton(mezzo, text=nomi[k], variable=self.v[k], command=self.mostra_stato)
            cb.grid(row=i, column=0, columnspan=2, sticky='w', pady=1)
            Suggerimento(cb, SUGG[f'pgxp_{k}'])
            self.caselle.append(cb)
        r = len(L.PGXP_VOCI)
        e = ttk.Label(mezzo, text=T('Tolleranza della geometria (pixel, -1 = nessuna)',
                                    'Geometry Tolerance (pixels, -1 = none)'))
        e.grid(row=r, column=0, sticky='w', pady=(8, 1))
        self.tolleranza = tk.StringVar(value=f'{float(o["tolleranza"]):g}')
        self.s_tol = ttk.Spinbox(mezzo, from_=-1, to=8, increment=0.5, textvariable=self.tolleranza, width=7)
        self.s_tol.grid(row=r, column=1, sticky='w', padx=(8, 0), pady=(8, 1))
        for w in (e, self.s_tol):
            Suggerimento(w, SUGG['pgxp_tolleranza'])
        e = ttk.Label(mezzo, text=T('Soglia di pulizia della profondit\u00e0 (SZ, 0 = mai)',
                                    'Depth Clear Threshold (SZ, 0 = never)'))
        e.grid(row=r + 1, column=0, sticky='w', pady=1)
        self.soglia = tk.StringVar(value=f'{float(o["soglia"]):g}')
        self.s_soglia = ttk.Spinbox(mezzo, from_=0, to=65535, increment=256, textvariable=self.soglia, width=7)
        self.s_soglia.grid(row=r + 1, column=1, sticky='w', padx=(8, 0), pady=1)
        for w in (e, self.s_soglia):
            Suggerimento(w, SUGG['pgxp_soglia'])
        e = ttk.Label(mezzo, text=T('Fessure (in pi\u00f9 di DuckStation)', 'Seams (extra to DuckStation)'))
        e.grid(row=r + 2, column=0, sticky='w', pady=1)
        self.tab_fessure = [(T('Spento', 'Off'), 'no'), (T('Fine', 'Fine'), 'fine'), (T('Largo', 'Wide'), 'largo')]
        self.fessure = tk.StringVar(value=etichetta_di(self.tab_fessure, o['fessure'], self.tab_fessure[0][0]))
        self.cb_fessure = ttk.Combobox(mezzo, textvariable=self.fessure, values=[x for x, _ in self.tab_fessure],
                                       state='readonly', width=9)
        self.cb_fessure.grid(row=r + 2, column=1, sticky='w', padx=(8, 0), pady=1)
        for w in (e, self.cb_fessure):
            Suggerimento(w, SUGG['pgxp_fessure'])
        # EnterElectro-Recomp 0.12, 6/11/2026 pomeriggio: le ultime due voci di DuckStation
        e = ttk.Label(mezzo, text=T('Depth Bias (milionesimi della profondit\u00e0)', 'Depth Bias (millionths of depth)'))
        e.grid(row=r + 3, column=0, sticky='w', pady=1)
        self.bias = tk.StringVar(value=f'{float(o.get("bias", L.PGXP_BIAS)):g}')
        self.s_bias = ttk.Spinbox(mezzo, from_=0, to=1000, increment=1, textvariable=self.bias, width=7)
        self.s_bias.grid(row=r + 3, column=1, sticky='w', padx=(8, 0), pady=1)
        for w in (e, self.s_bias):
            Suggerimento(w, SUGG['pgxp_bias'])
        e = ttk.Label(mezzo, text=T('Normalizzazione della profondit\u00e0 (Normalize Depth Scale)',
                                    'Normalize Depth Scale'))
        e.grid(row=r + 4, column=0, sticky='w', pady=1)
        self.tab_normalizza = [(T('Automatica', 'Automatic'), 'automatico'), (T('Spenta', 'Disabled'), 'no'),
                               (T('Con il buffer di profondit\u00e0', 'Depth buffer only'), 'profondita'),
                               (T('Sempre (anche le texture)', 'Always (textures too)'), 'sempre')]
        self.normalizza = tk.StringVar(value=etichetta_di(self.tab_normalizza, o.get('normalizza', 'automatico'),
                                                          self.tab_normalizza[0][0]))
        self.cb_normalizza = ttk.Combobox(mezzo, textvariable=self.normalizza,
                                          values=[x for x, _ in self.tab_normalizza], state='readonly', width=30)
        self.cb_normalizza.grid(row=r + 4, column=1, sticky='w', padx=(8, 0), pady=1)
        for w in (e, self.cb_normalizza):
            Suggerimento(w, SUGG['pgxp_normalizza'])
        self.nota = tk.StringVar(value='')
        ttk.Label(top, textvariable=self.nota, foreground=COL['testo2'], padding=(14, 4),
                  wraplength=int(560 * scala), justify='left').pack(anchor='w')
        giu = ttk.Frame(top, padding=(14, 8, 14, 12))
        giu.pack(fill='x')
        ttk.Button(giu, text=T('Valori di DuckStation', 'DuckStation defaults'), command=self.predefiniti).pack(
            side='left')
        ttk.Button(giu, text='OK', command=self.ok).pack(side='right')
        ttk.Button(giu, text=T('Annulla', 'Cancel'), command=self.chiudi).pack(side='right', padx=(0, 8))
        top.protocol('WM_DELETE_WINDOW', self.chiudi)
        top.bind('<Escape>', lambda _e: self.chiudi())
        self.mostra_stato()
        top.grab_set()

    def mostra_stato(self) -> None:
        """Voci attive solo con PGXP acceso e con le voci da cui dipendono (L.PGXP_DIPENDE, come in DuckStation: colori
        in prospettiva e buffer di profondita' solo con le texture in prospettiva); soglia, fessure e profondita' dei
        semitrasparenti solo con il buffer di profondita'."""
        on = self.acceso.get()
        s = {k: bool(v.get()) for k, v in self.v.items()}
        for (k, _v, _c), cb in zip(L.PGXP_VOCI, self.caselle):
            d = L.PGXP_DIPENDE.get(k)
            cb.state(['!disabled' if on and (d is None or L.pgxp_vale(s, d)) else 'disabled'])
        self.s_tol.state(['!disabled' if on else 'disabled'])
        prof_on = on and L.pgxp_vale(s, 'profondita')
        self.s_soglia.state(['!disabled' if prof_on else 'disabled'])
        self.cb_fessure.state(['!disabled', 'readonly'] if prof_on else ['disabled'])
        self.s_bias.state(['!disabled' if prof_on else 'disabled'])
        # come la finestra di DuckStation: la normalizzazione serve al buffer di profondita' o alle texture
        norm_on = on and (prof_on or s.get('texture', False))
        self.cb_normalizza.state(['!disabled', 'readonly'] if norm_on else ['disabled'])
        self.nota.set(T('Le scelte si salvano con Gioca, come le altre opzioni. PGXP vale con OpenGL (con Vulkan '
                        'geometria e texture, con il disegno software niente) e si vede da 720p in su.',
                        'The choices are saved with Play, like the other options. PGXP works with OpenGL (with Vulkan '
                        'geometry and textures, with the software renderer nothing) and shows from 720p up.'))

    def predefiniti(self) -> None:
        d = L.pgxp_predefiniti()
        for k, var in self.v.items():
            var.set(bool(d[k]))
        self.tolleranza.set(f'{d["tolleranza"]:g}')
        self.soglia.set(f'{d["soglia"]:g}')
        self.fessure.set(self.tab_fessure[0][0])
        self.bias.set(f'{d["bias"]:g}')
        self.normalizza.set(etichetta_di(self.tab_normalizza, d['normalizza'], self.tab_normalizza[0][0]))
        self.mostra_stato()

    def numero(self, var, minimo, massimo, predefinito) -> float:
        try:
            x = float(str(var.get()).replace(',', '.'))
        except (TypeError, ValueError):
            return predefinito
        return max(minimo, min(massimo, x))

    def ok(self) -> None:
        o = {k: bool(v.get()) for k, v in self.v.items()}
        o['tolleranza'] = self.numero(self.tolleranza, -1.0, 64.0, L.PGXP_TOLLERANZA)
        if o['tolleranza'] < 0:
            o['tolleranza'] = -1.0
        o['soglia'] = self.numero(self.soglia, 0.0, 1e6, L.PGXP_SOGLIA)
        o['fessure'] = dict(self.tab_fessure).get(self.fessure.get(), 'no')
        o['bias'] = self.numero(self.bias, 0.0, 1000.0, L.PGXP_BIAS)
        o['normalizza'] = dict(self.tab_normalizza).get(self.normalizza.get(), 'automatico')
        self.padre.pgxp_opz = o
        self.padre.pgxp.set(bool(self.acceso.get()))
        self.padre.scrivi(T('Opzioni PGXP scelte (si salvano con Gioca): ', 'PGXP options chosen (saved with Play): ')
                          + L.descrivi_pgxp(dict(o, acceso=bool(self.acceso.get()))))
        self.chiudi()

    def chiudi(self) -> None:
        try:
            self.top.grab_release()
            self.top.destroy()
        except tk.TclError:
            pass


# -------------------------------------------------------------------------------- finestra dei filmati (0.12)

def durata(secondi) -> str:
    """Una durata a parole, arrotondata: "8 minuti", "1 h 20 min", "2 giorni 3 h"."""
    s = max(0, int(secondi or 0))
    if s < 90:
        return T('un minuto', 'a minute') if s >= 30 else T('meno di un minuto', 'less than a minute')
    m = (s + 30) // 60
    if m < 60:
        return T(f'{m} minuti', f'{m} minutes')
    h, m = divmod(m, 60)
    if h < 24:
        return f'{h} h' + (f' {m} min' if m and h < 10 else '')
    g, h = divmod(h, 24)
    return T(f'{g} giorn' + ('o' if g == 1 else 'i'), f'{g} day' + ('' if g == 1 else 's')) + (f' {h} h' if h else '')


def gb(byte) -> str:
    """Byte come "1,2 GB" (virgola in italiano)."""
    t = f'{(byte or 0) / 1e9:.1f}'
    return (t.replace('.', ',') if lingua() == 'it' else t) + ' GB'


class FinestraFilmati:
    """Filmati della versione scelta (0.12): i Migliorati e i tre filmati IA (Swin2SR, Real-ESRGAN general-x4v3 e
    Real-ESRGAN animevideov3, vedi sm2_ia.py). Per ogni scelta: spiegazione, difetti possibili, stato, tempo su questo PC
    e le immagini di prova fatte qui dal disco del giocatore (comando anteprime-ia), da guardare prima di scegliere:
    tenendo premuto il mouse sull'immagine si vede l'originale. Scarica, prepara e ferma con i comandi di sm2_launcher.py
    lanciati dalla finestra principale (ia-scarica, anteprime-ia, prepara-filmati, prepara-filmati-ia), come la riga di
    comando; "Usa questi filmati" mette la scelta nelle opzioni (si salva con Gioca, come le altre). Non blocca la
    finestra principale: la preparazione continua anche chiudendo questa, con l'avanzamento sotto il pulsante principale.
    English: the Movies window: Enhanced and the three AI upscalers, with description, possible defects, state, time on
    this PC and test pictures made here from the player's disc."""

    LATO_W, LATO_H = 640, 384           # le immagini di prova: ritagli 160x96 ingranditi 4 volte (sm2_ia.anteprime)

    def __init__(self, padre, prof: str):
        self.padre, self.prof = padre, prof
        self.cartella = L.GIOCHI / prof
        self.ia = L._ia()
        self.vivo = True
        self.foto = {}                  # (versione, ritaglio) -> PhotoImage
        self.anteprime = {}
        self.premuto = False
        self._occupato_prima = None
        self.scelte = ['migliorati'] + list(L.MODELLI_IA)
        top = self.top = tk.Toplevel(padre.root)
        self.nome = (padre.riga(prof) or {}).get('nome', prof)
        top.title(T(f'Filmati - {self.nome}', f'Movies - {self.nome}'))
        top.transient(padre.root)
        s = self.scala = max(1.0, top.winfo_fpixels('1i') / 96.0)
        try:
            top.configure(bg=COL['fondo'])
        except tk.TclError:
            pass
        barra_scura(top)
        largo = int(1060 * s)
        st = ttk.Style(top)
        st.configure('Titolo.TLabel', font=(CARATTERE, 13, 'bold'))
        st.configure('Piccolo.TLabel', font=(CARATTERE, 8), foreground=COL['testo3'])
        st.configure('Grassetto.TLabel', font=(CARATTERE, 9, 'bold'))

        su = ttk.Frame(top, padding=(14, 10, 14, 4))
        su.pack(fill='x')
        ttk.Label(su, text=T(f'Filmati di {self.nome}', f'Movies of {self.nome}'), style='Titolo.TLabel').pack(anchor='w')
        ttk.Label(su, wraplength=largo, foreground=COL['testo2'], text=T(
            "Scegli come vedere i filmati del gioco. Ogni versione si prepara una volta sola dal tuo disco. Le versioni "
            "IA ingrandiscono ogni fotogramma con un'intelligenza artificiale: sono pi\u00f9 nitide, ma possono avere "
            "dei difetti (scritti sotto per ciascuna). Le immagini di prova sono fatte sul tuo PC con il tuo disco: "
            "guardale e scegli quella che ti piace di pi\u00f9.",
            "Choose how to see the game's movies. Each version is prepared only once from your disc. The AI versions "
            "enlarge every frame with an artificial intelligence: they are sharper, but they may have defects (listed "
            "below for each one). The test pictures are made on your PC from your disc: look at them and choose the "
            "one you like best.")).pack(anchor='w', pady=(2, 0))

        mezzo = ttk.Frame(top, padding=(14, 6))
        mezzo.pack(fill='x')
        # a sinistra le scelte, con lo stato
        sx = ttk.LabelFrame(mezzo, text=T('Versioni dei filmati', 'Movie versions'), padding=(10, 6))
        sx.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
        self.scelta = tk.StringVar(value=self._scelta_iniziale())
        self.stati = {}
        for i, v in enumerate(self.scelte):
            rb = ttk.Radiobutton(sx, text=self.titolo(v), value=v, variable=self.scelta, command=self.mostra)
            rb.grid(row=2 * i, column=0, sticky='w', pady=(6 if i else 0, 0))
            Suggerimento(rb, SUGG['ia_scelte'])
            et = ttk.Label(sx, text='', style='Piccolo.TLabel')
            et.grid(row=2 * i + 1, column=0, sticky='w', padx=(int(22 * s), 0))
            self.stati[v] = et
        self.nel_gioco = tk.StringVar(value='')
        ttk.Label(sx, textvariable=self.nel_gioco, foreground=COL['testo2'], wraplength=int(300 * s)).grid(
            row=2 * len(self.scelte), column=0, sticky='w', pady=(12, 0))
        # a destra le immagini di prova
        dx = ttk.LabelFrame(mezzo, text=T('Immagini di prova (dal tuo disco)', 'Test pictures (from your disc)'),
                            padding=(10, 6))
        dx.grid(row=0, column=1, sticky='nsew')
        riga_r = ttk.Frame(dx)
        riga_r.pack(fill='x')
        self.ritaglio = tk.IntVar(value=0)
        self.b_ritagli = []
        for k in range(2):
            b = ttk.Radiobutton(riga_r, text='', value=k, variable=self.ritaglio, command=self.mostra)
            b.pack(side='left', padx=(0, 14))
            self.b_ritagli.append(b)
        self.dove = tk.StringVar(value='')
        ttk.Label(riga_r, textvariable=self.dove, style='Piccolo.TLabel').pack(side='right')
        self.ridotta = 1                # 2 = immagini a meta', per gli schermi piccoli
        self.cw, self.ch = self.LATO_W, self.LATO_H
        self.tela = tk.Canvas(dx, width=self.cw, height=self.ch, highlightthickness=1,
                              highlightbackground=COL['bordo'], bg=COL['notte'], bd=0, cursor='hand2')
        self.tela.pack(pady=(6, 4))
        self.tela.bind('<ButtonPress-1>', lambda e: self._premi(True))
        self.tela.bind('<ButtonRelease-1>', lambda e: self._premi(False))
        self.tela.bind('<Leave>', lambda e: self._premi(False))
        self.guardi = tk.StringVar(value='')
        ttk.Label(dx, textvariable=self.guardi, foreground=COL['testo2']).pack(anchor='w')
        mezzo.columnconfigure(0, weight=1)

        # sotto: la scelta in dettaglio (spiegazione, difetti possibili, tempo, licenza)
        det = self.dettagli = ttk.LabelFrame(top, text='', padding=(12, 6))
        det.pack(fill='x', padx=14, pady=(4, 0))
        self.t_desc = ttk.Label(det, wraplength=largo, justify='left')
        self.t_desc.pack(anchor='w')
        ttk.Label(det, text=T('Difetti possibili', 'Possible defects'), style='Grassetto.TLabel').pack(anchor='w',
                                                                                                    pady=(6, 0))
        self.t_difetti = ttk.Label(det, wraplength=largo, justify='left')
        self.t_difetti.pack(anchor='w')
        self.t_comuni = ttk.Label(det, wraplength=largo, justify='left', foreground=COL['testo2'])
        self.t_comuni.pack(anchor='w', pady=(4, 0))
        self.t_tempo = ttk.Label(det, wraplength=largo, justify='left')
        self.t_tempo.pack(anchor='w', pady=(6, 0))
        self.t_licenza = ttk.Label(det, wraplength=largo, justify='left', style='Piccolo.TLabel')
        self.t_licenza.pack(anchor='w', pady=(2, 0))

        # avanzamento della preparazione
        av = ttk.Frame(top, padding=(14, 8, 14, 0))
        av.pack(fill='x')
        self.barra = ttk.Progressbar(av, orient='horizontal', mode='determinate', maximum=1000)
        self.barra.pack(fill='x')
        self.t_avanzamento = tk.StringVar(value='')
        ttk.Label(av, textvariable=self.t_avanzamento, foreground=COL['testo2']).pack(anchor='w')

        giu = ttk.Frame(top, padding=(14, 8, 14, 12))
        giu.pack(fill='x')
        self.b_scarica = ttk.Button(giu, text='', command=self.scarica_e_prova)
        self.b_scarica.pack(side='left')
        self.b_prepara = ttk.Button(giu, text=T('Prepara', 'Prepare'), command=self.prepara)
        self.b_prepara.pack(side='left', padx=(8, 0))
        self.b_ferma = ttk.Button(giu, text=T('Ferma', 'Stop'), command=self.ferma)
        self.b_ferma.pack(side='left', padx=(8, 0))
        ttk.Button(giu, text=T('Chiudi', 'Close'), command=self.chiudi).pack(side='right')
        self.b_usa = ttk.Button(giu, text=T('Usa questi filmati nel gioco', 'Use these movies in the game'),
                                command=self.usa)
        self.b_usa.pack(side='right', padx=(0, 8))
        for b, k in ((self.b_scarica, 'ia_scarica'), (self.b_prepara, 'ia_prepara'), (self.b_ferma, 'ia_ferma'),
                     (self.b_usa, 'ia_usa')):
            Suggerimento(b, SUGG[k])
        top.protocol('WM_DELETE_WINDOW', self.chiudi)
        top.bind('<Escape>', lambda e: self.chiudi())
        top.bind('<Up>', lambda e: self._sposta(-1))
        top.bind('<Down>', lambda e: self._sposta(1))
        self.ricarica()
        top.update_idletasks()
        # al centro della finestra principale, mai piu' grande dello schermo (se non ci sta: immagini a meta')
        aw, ah, ax, ay = area_di_lavoro(top)
        if top.winfo_reqheight() > ah - 50 or top.winfo_reqwidth() > aw - 20:
            self.ridotta = 2
            self.cw, self.ch = self.LATO_W // 2, self.LATO_H // 2
            self.tela.configure(width=self.cw, height=self.ch)
            self.foto = {}
            self.mostra()
            top.update_idletasks()
        w, h = min(top.winfo_reqwidth(), aw - 20), min(top.winfo_reqheight(), ah - 40)
        px = padre.root.winfo_rootx() + (padre.root.winfo_width() - w) // 2
        py = padre.root.winfo_rooty() + (padre.root.winfo_height() - h) // 2
        top.geometry(f'+{max(ax, min(px, ax + aw - w))}+{max(ay, min(py, ay + ah - h - 30))}')
        top.after(500, self._ciclo)

    # ---------------------------------------------------------------- testi
    def titolo(self, v: str) -> str:
        if v == 'migliorati':
            return T('Migliorati (senza IA)', 'Enhanced (no AI)')
        return T('IA: ', 'AI: ') + T(*self.ia.MODELLI[v]['titolo'])

    def valore(self, v: str) -> str:
        """Il valore di --filmati per una scelta."""
        return 'migliorati' if v == 'migliorati' else 'ia-' + v

    def _scelta_iniziale(self) -> str:
        attuale = dict(FILMATI).get(self.padre.filmati.get(), 'originali')
        if attuale.startswith('ia-') and attuale[3:] in L.MODELLI_IA:
            return attuale[3:]
        return 'migliorati'

    def _stato_inst(self) -> dict:
        try:
            return json.loads((self.cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def _a_meta(self, v: str) -> int:
        """Filmati gia' fatti di una preparazione IA fermata (0 se non ce n'e' una)."""
        tmp = self.cartella / (self.ia.cartella_filmati(v) + '.tmp')
        try:
            return sum(1 for d in tmp.iterdir() if (d / 'fatto.json').is_file()) if tmp.is_dir() else 0
        except OSError:
            return 0

    def _in_corso(self):
        """Il modello che si sta preparando per questa versione (o 'migliorati'), None se niente."""
        lav = getattr(self.padre, 'lavoro_filmati', None)
        return lav[1] if (lav and lav[0] == self.prof and self.padre.proc is not None) else None

    def _info(self, v: str) -> dict:
        """Stato di una scelta: pronti, byte, data, scaricato (modelli e programmi), a_meta, in_corso."""
        st = self.stato_inst
        corso = self._in_corso()
        if v == 'migliorati':
            hd = st.get('filmati_hd') or {}
            return {'pronti': L.filmati_hd_pronti(self.cartella, st), 'byte': hd.get('byte'), 'data': hd.get('data'),
                    'scaricato': True, 'a_meta': 0, 'in_corso': corso == v}
        f = (st.get('filmati_ia') or {}).get(v) or {}
        return {'pronti': self.ia.pronti(self.cartella, st, v), 'byte': f.get('byte'), 'data': f.get('data'),
                'scaricato': self.programmi and self.ia.modello_pronto(L.ROOT, v), 'a_meta': self._a_meta(v),
                'in_corso': corso == v, 'secondi': f.get('secondi'), 'scheda': f.get('scheda')}

    def _testo_stato(self, i: dict) -> tuple:
        if i['in_corso']:
            return '\u25cf ' + T('in preparazione', 'being prepared'), COL['giallo']
        if i['pronti']:
            return ('\u25cf ' + T('pronti', 'ready') + (f' ({gb(i["byte"])})' if i.get('byte') else ''),
                    COL['verde'])
        if i['a_meta']:
            return '\u25cf ' + T('a met\u00e0: si riprende da dove era', 'half done: resumes where it was'), COL['giallo']
        if not i['scaricato']:
            return '\u25cf ' + T('da scaricare e preparare', 'to download and prepare'), COL['grigio']
        return '\u25cf ' + T('da preparare', 'to prepare'), COL['grigio']

    # ---------------------------------------------------------------- dati e immagini
    def ricarica(self) -> None:
        """Rilegge stato, programmi e immagini di prova (dopo ogni comando)."""
        self.stato_inst = self._stato_inst()
        self.programmi = self.ia.programmi_pronti(L.ROOT)
        try:
            self.anteprime = json.loads((self.cartella / 'anteprime_ia' / 'anteprime.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.anteprime = {}
        self.foto = {}
        fot = self.anteprime.get('fotogrammi') or []
        for k, b in enumerate(self.b_ritagli):
            if k < len(fot):
                et = fot[k].get('etichetta') or ['', '']
                b.configure(text=T(et[0], et[1]) if len(et) == 2 else str(et), state='normal')
            else:
                b.configure(text=T('Immagine', 'Picture') + f' {k + 1}', state='disabled')
        self.serve = self.ia.da_scaricare(L.ROOT, L.MODELLI_IA)
        self.mostra()

    def _foto(self, versione: str, k: int):
        chiave = (versione, k)
        if chiave not in self.foto:
            img = None
            fot = self.anteprime.get('fotogrammi') or []
            nome = (fot[k].get('versioni') or {}).get(versione) if k < len(fot) else None
            if nome:
                try:
                    img = tk.PhotoImage(master=self.top, file=str(self.cartella / 'anteprime_ia' / nome))
                    if self.ridotta > 1:
                        img = img.subsample(self.ridotta)
                except (tk.TclError, OSError):
                    img = None
            self.foto[chiave] = img
        return self.foto[chiave]

    def _premi(self, giu: bool) -> None:
        if giu != self.premuto:
            self.premuto = giu
            self.mostra_immagine()

    def _sposta(self, d: int) -> None:
        i = self.scelte.index(self.scelta.get()) if self.scelta.get() in self.scelte else 0
        self.scelta.set(self.scelte[(i + d) % len(self.scelte)])
        self.mostra()

    def mostra_immagine(self) -> None:
        c = self.tela
        c.delete('all')
        v = self.scelta.get()
        k = self.ritaglio.get()
        fot = self.anteprime.get('fotogrammi') or []
        if k < len(fot):
            self.dove.set(T(f'{fot[k].get("filmato", "")}, fotogramma {fot[k].get("numero", "")}',
                            f'{fot[k].get("filmato", "")}, frame {fot[k].get("numero", "")}'))
        else:
            self.dove.set('')
        versione = 'originale' if self.premuto else v
        img = self._foto(versione, k)
        if img is not None:
            c.create_image(self.cw // 2, self.ch // 2, image=img, anchor='center')
            if self.premuto:
                self.guardi.set(T('Stai guardando: l\'originale (come sulla PS1, ingrandito a blocchi)',
                                  'You are looking at: the original (as on the PS1, enlarged in blocks)'))
            else:
                self.guardi.set(T(f'Stai guardando: {self.titolo(v)}. Tieni premuto il tasto sinistro del mouse '
                                  'sull\'immagine per vedere l\'originale.',
                                  f'You are looking at: {self.titolo(v)}. Hold the left mouse button on the picture '
                                  'to see the original.'))
            return
        if not self.anteprime and not getattr(self, 'serve', None):
            testo = T('Ancora nessuna immagine di prova per questa versione.\n\nPremi \u00abFai le immagini di prova\u00bb: '
                      'circa un minuto, con il tuo disco e la tua scheda video.',
                      'No test pictures for this version yet.\n\nPress \u201cMake the test pictures\u201d: about a minute, '
                      'with your disc and your graphics card.')
        elif not self.anteprime:
            testo = T('Ancora nessuna immagine di prova.\n\nPremi \u00abScarica e fai le immagini di prova\u00bb: il '
                      'launcher scarica i programmi e i modelli IA (una volta sola) e prepara qui le immagini di prova '
                      'con il tuo disco.',
                      'No test pictures yet.\n\nPress \u201cDownload and make the test pictures\u201d: the launcher '
                      'downloads the AI programs and models (only once) and makes the test pictures here from your '
                      'disc.')
        elif versione == 'migliorati':
            testo = T('Nessuna immagine dei Migliorati: preparali, poi premi \u00abRifai le immagini di prova\u00bb.',
                      'No picture of the Enhanced movies: prepare them, then press \u201cRedo the test pictures\u201d.')
        else:
            testo = T('Nessuna immagine per questa versione: premi \u00abRifai le immagini di prova\u00bb.',
                      'No picture for this version: press \u201cRedo the test pictures\u201d.')
        c.create_text(self.cw // 2, self.ch // 2, text=testo, fill=COL['testo2'], width=self.cw - 40,
                      font=(CARATTERE, 10), justify='center')
        self.guardi.set('')

    def mostra(self) -> None:
        """Aggiorna tutto per la scelta di adesso: stati, immagine, dettagli, pulsanti."""
        if not self.vivo:
            return
        info = {v: self._info(v) for v in self.scelte}
        for v, et in self.stati.items():
            testo, colore = self._testo_stato(info[v])
            et.configure(text=testo, foreground=colore)
        self.nel_gioco.set(T('Scelti nelle opzioni: ', 'Chosen in the options: ') + self.padre.filmati.get())
        v = self.scelta.get()
        i = info[v]
        self.mostra_immagine()
        self.dettagli.configure(text=self.titolo(v))
        if v == 'migliorati':
            self.t_desc.configure(text=T(
                "Fotogrammi ripuliti dai blocchi della compressione, con colori pi\u00f9 puliti, e ingranditi 4 volte, "
                "senza intelligenza artificiale: fedeli all'originale, ma un po' morbidi. Si preparano in pochi minuti "
                "e non serve scaricare niente.",
                "Frames cleaned of the compression blocks, with cleaner colours, and enlarged 4 times, without "
                "artificial intelligence: faithful to the original, but a little soft. They are prepared in a few "
                "minutes and nothing has to be downloaded."))
            difetti = [T("meno nitidi delle versioni IA: contorni e scritte restano un po' morbidi",
                         'less sharp than the AI versions: edges and text stay a little soft')]
            comuni = ''
            tempo = T('Tempo: pochi minuti; spazio: circa 1-1,5 GB nella cartella dell\'installazione.',
                      'Time: a few minutes; space: about 1-1.5 GB in the installation folder.')
            licenza = T('Fatti dal tuo disco con gli strumenti di EnterElectro-Recomp (MIT) e di psxrecomp (PolyForm '
                        'Noncommercial 1.0.0).',
                        'Made from your disc with the EnterElectro-Recomp tools (MIT) and psxrecomp (PolyForm '
                        'Noncommercial 1.0.0).')
        else:
            m = self.ia.MODELLI[v]
            self.t_desc.configure(text=T(*m['descrizione']))
            difetti = [T(*d) for d in m['difetti']]
            comuni = T('Per tutti i filmati IA: ', 'For all AI movies: ') + '; '.join(T(*d) for d in
                                                                                     self.ia.DIFETTI_COMUNI) + '.'
            mis = (self.anteprime.get('modelli') or {}).get(v)
            if i['pronti'] and i.get('secondi'):
                tempo = T(f'Preparati in {durata(i["secondi"])} con {i.get("scheda") or "?"}',
                          f'Prepared in {durata(i["secondi"])} with {i.get("scheda") or "?"}') + \
                    (f', {gb(i["byte"])}' if i.get('byte') else '') + (f' ({i["data"]})' if i.get('data') else '') + '.'
            elif mis:
                spf = f'{mis.get("secondi_per_fotogramma", 0):.3f}'
                tempo = T(f'Su questo PC: circa {durata(mis.get("stima_secondi"))} per preparare tutti i filmati, con '
                          f'{mis.get("scheda", "?")} ({spf.replace(".", ",")} secondi per fotogramma); spazio: circa '
                          '1-2 GB.',
                          f'On this PC: about {durata(mis.get("stima_secondi"))} to prepare all the movies, with '
                          f'{mis.get("scheda", "?")} ({spf} seconds per frame); space: about 1-2 GB.')
                if v == 'swin2sr':
                    tempo += T(' Meglio con il PC collegato alla corrente.', ' Better with the PC plugged in.')
            else:
                tempo = T('Il tempo su questo PC si misura con le immagini di prova; spazio: circa 1-2 GB.',
                          'The time on this PC is measured with the test pictures; space: about 1-2 GB.')
            licenza = T(f'Modello: {m["nome"]}, licenza {m["licenza"]}. Scaricato una volta in tools\\ia insieme a '
                        'onnxruntime-directml (MIT) e numpy (BSD-3-Clause).',
                        f'Model: {m["nome"]}, licence {m["licenza"]}. Downloaded once into tools\\ia together with '
                        'onnxruntime-directml (MIT) and numpy (BSD-3-Clause).')
        self.t_difetti.configure(text='\n'.join('\u2022 ' + d for d in difetti))
        self.t_comuni.configure(text=comuni)
        self.t_tempo.configure(text=tempo)
        self.t_licenza.configure(text=licenza)
        self.aggiorna_pulsanti(info)

    def aggiorna_pulsanti(self, info=None) -> None:
        info = info or {v: self._info(v) for v in self.scelte}
        occupato = self.padre.proc is not None
        v = self.scelta.get()
        i = info[v]
        if self.serve:
            testo_s = T('Scarica e fai le immagini di prova...', 'Download and make the test pictures...')
        elif not self.anteprime:
            testo_s = T('Fai le immagini di prova', 'Make the test pictures')
        else:
            testo_s = T('Rifai le immagini di prova', 'Redo the test pictures')
        self.b_scarica.configure(text=testo_s)
        self.b_scarica.state(['disabled' if occupato else '!disabled'])
        if v != 'migliorati' and not i['scaricato']:
            testo, ok = T('Prepara', 'Prepare'), False
        elif i['pronti']:
            testo, ok = T('Rifai...', 'Redo...'), True
        elif i['a_meta']:
            testo, ok = T('Riprendi', 'Resume'), True
        else:
            testo, ok = T('Prepara...', 'Prepare...'), True
        self.b_prepara.configure(text=testo)
        self.b_prepara.state(['!disabled' if (ok and not occupato) else 'disabled'])
        self.b_ferma.state(['!disabled' if (self._in_corso() not in (None, 'migliorati')) else 'disabled'])
        self.b_usa.state(['!disabled' if (i['pronti'] or i['in_corso'] or i['a_meta']) else 'disabled'])

    # ---------------------------------------------------------------- comandi
    def scarica_e_prova(self) -> None:
        if self.padre.proc is not None:
            return
        serve = self.ia.da_scaricare(L.ROOT, L.MODELLI_IA)
        if serve:
            voci = self.ia.descrivi_scarichi(L.ROOT, L.MODELLI_IA)
            def mb(b):
                t = f'{b / 1e6:.1f}'
                return (t.replace('.', ',') if lingua() == 'it' else t) + ' MB'
            righe = '\n'.join(f'\u2022 {x["cosa"]} - {mb(x["byte"])} ' +
                              T(f'da {x["fonte"]} (licenza {x["licenza"]})', f'from {x["fonte"]} (licence '
                                                                             f'{x["licenza"]})') for x in voci)
            tot = sum(x['byte'] for x in voci) / 1e6
            if not messagebox.askyesno(
                    T('Filmati IA: scaricare?', 'AI movies: download?'),
                    T(f'Per i filmati IA il launcher scarica una volta sola, nella cartella tools\\ia, circa {tot:.0f} MB:'
                      f'\n\n{righe}\n\nOgni file si controlla con la sua impronta SHA-256. Poi il launcher fa le immagini '
                      'di prova con il tuo disco e misura il tempo sulla tua scheda video (circa un minuto).\n\n'
                      'Scaricare?',
                      f'For the AI movies the launcher downloads only once, into the tools\\ia folder, about {tot:.0f} MB:'
                      f'\n\n{righe}\n\nEvery file is checked with its SHA-256 fingerprint. Then the launcher makes the '
                      'test pictures from your disc and measures the time on your graphics card (about a minute).\n\n'
                      'Download?'), parent=self.top):
                return
            self.padre.esegui(['ia-scarica', '--si'], T('Scarico i programmi e i modelli per i filmati IA',
                                                         'Downloading the programs and models for the AI movies'),
                              poi=self._anteprime)
        else:
            self._anteprime()
        self.aggiorna_pulsanti()

    def _anteprime(self) -> None:
        self.padre.esegui(['anteprime-ia', '--profilo', self.prof],
                          T(f'Immagini di prova dei filmati IA di {self.prof} (circa un minuto)',
                            f'Test pictures of the AI movies of {self.prof} (about a minute)'))

    def prepara(self) -> None:
        if self.padre.proc is not None:
            return
        v = self.scelta.get()
        i = self._info(v)
        if v == 'migliorati':
            if i['pronti'] and not messagebox.askyesno(
                    T('Rifare i Migliorati?', 'Redo the Enhanced movies?'),
                    T('I filmati Migliorati sono gi\u00e0 pronti. Rifarli (pochi minuti)? Quelli di adesso vengono '
                      'spostati da parte, non cancellati.',
                      'The Enhanced movies are already prepared. Redo them (a few minutes)? The current ones are moved '
                      'aside, not deleted.'), parent=self.top):
                return
            self.padre.lavoro_filmati = (self.prof, v)
            self.padre.esegui(['prepara-filmati', '--profilo', self.prof] + (['--rifai'] if i['pronti'] else []),
                              T(f'Preparo i filmati migliorati di {self.prof} (alcuni minuti)',
                                f'Preparing the enhanced movies of {self.prof} (a few minutes)'))
            self.aggiorna_pulsanti()
            return
        mis = (self.anteprime.get('modelli') or {}).get(v) or {}
        quanto = (T(f'Su questo PC ci vorranno circa {durata(mis["stima_secondi"])} ({mis.get("scheda", "?")}).',
                    f'On this PC it will take about {durata(mis["stima_secondi"])} ({mis.get("scheda", "?")}).')
                  if mis.get('stima_secondi') else T('Il tempo dipende dalla scheda video.',
                                                     'The time depends on the graphics card.'))
        if i['pronti']:
            domanda = T(f'I filmati {self.titolo(v)} sono gi\u00e0 pronti. Rifarli da capo? {quanto} Quelli di adesso '
                        'vengono spostati da parte, non cancellati.',
                        f'The {self.titolo(v)} movies are already prepared. Redo them from the start? {quanto} The '
                        'current ones are moved aside, not deleted.')
        elif i['a_meta']:
            domanda = T(f'Riprendere la preparazione dei filmati di {self.nome} con {self.titolo(v)}? Si continua da '
                        f'dove era ({i["a_meta"]} filmati gi\u00e0 fatti).\n\n{quanto}',
                        f'Resume the preparation of the movies of {self.nome} with {self.titolo(v)}? It continues '
                        f'where it was ({i["a_meta"]} movies already done).\n\n{quanto}')
        else:
            domanda = T(f'Preparare i filmati di {self.nome} con {self.titolo(v)}?\n\n{quanto} Spazio: circa 1-2 GB.\n\n'
                        'Intanto puoi usare il launcher; \u00abFerma\u00bb interrompe e la volta dopo si riprende da dove '
                        'eri. Chiudendo il launcher la preparazione si ferma (e riprende la volta dopo).' +
                        (' Meglio con il PC collegato alla corrente.' if v == 'swin2sr' else ''),
                        f'Prepare the movies of {self.nome} with {self.titolo(v)}?\n\n{quanto} Space: about 1-2 GB.\n\n'
                        'Meanwhile you can use the launcher; \u201cStop\u201d interrupts and the next time it resumes '
                        'where it was. Closing the launcher stops the preparation (it resumes the next time).' +
                        (' Better with the PC plugged in.' if v == 'swin2sr' else ''))
        if not messagebox.askyesno(T('Filmati IA', 'AI movies'), domanda, parent=self.top):
            return
        self.padre.lavoro_filmati = (self.prof, v)
        self.padre.esegui(['prepara-filmati-ia', '--profilo', self.prof, '--modello', v] +
                          (['--rifai'] if i['pronti'] else []),
                          T(f'Preparo i filmati IA di {self.prof} con {self.ia.MODELLI[v]["nome"]}',
                            f'Preparing the AI movies of {self.prof} with {self.ia.MODELLI[v]["nome"]}'))
        self.aggiorna_pulsanti()

    def ferma(self) -> None:
        v = self._in_corso()
        if v in (None, 'migliorati'):
            return
        if ferma_filmati_ia(self.cartella, v):
            self.padre.scrivi(T('Fermo la preparazione dei filmati IA (alla fine del fotogramma in corso); con '
                                '\u00abRiprendi\u00bb si continua da dove era.',
                                'Stopping the preparation of the AI movies (at the end of the current frame); '
                                '\u201cResume\u201d continues where it was.'))
        self.b_ferma.state(['disabled'])

    def usa(self) -> None:
        v = self.scelta.get()
        val = self.valore(v)
        et = etichetta_di(FILMATI, val)
        if et is None:
            return
        self.padre.filmati.set(et)
        self.padre.scrivi(T(f'Filmati scelti: {et}. Si salvano con \u00abGioca\u00bb, come le altre opzioni.',
                            f'Movies chosen: {et}. They are saved with \u201cPlay\u201d, like the other options.'))
        self.mostra()

    def chiudi(self) -> None:
        self.vivo = False
        if getattr(self.padre, 'finestra_filmati', None) is self:
            self.padre.finestra_filmati = None
        try:
            self.top.destroy()
        except tk.TclError:
            pass

    def _ciclo(self) -> None:
        if not self.vivo:
            return
        if not getattr(self.padre, 'vivo', True):       # finestra principale rifatta in un'altra lingua
            self.chiudi()
            return
        try:
            self._passo()
        except tk.TclError:                              # finestra distrutta (cambio di lingua): basta cosi'
            self.vivo = False
            return
        self.top.after(500, self._ciclo)

    def _passo(self) -> None:
        occupato = self.padre.proc is not None
        if occupato != self._occupato_prima:
            if self._occupato_prima and not occupato:    # un comando e' appena finito: stato e immagini nuovi
                self.ricarica()
            else:
                self.aggiorna_pulsanti()
            self._occupato_prima = occupato
        av = getattr(self.padre, 'avanzamento', None)
        if av and occupato and self._in_corso():
            fatti, totale, resto = av
            self.barra.configure(value=int(1000 * fatti / max(1, totale)))
            self.t_avanzamento.set(T(f'{self.titolo(self._in_corso())}: {fatti} di {totale} fotogrammi '
                                     f'({100 * fatti // max(1, totale)}%), circa {durata(resto)} alla fine',
                                     f'{self.titolo(self._in_corso())}: {fatti} of {totale} frames '
                                     f'({100 * fatti // max(1, totale)}%), about {durata(resto)} to the end'))
        elif occupato and self._in_corso() == 'migliorati':
            self.barra.configure(mode='indeterminate')
            self.barra.step(15)
            self.t_avanzamento.set(T('Preparo i Migliorati (pochi minuti)...', 'Preparing the Enhanced movies (a few '
                                                                                'minutes)...'))
        elif occupato:
            self.t_avanzamento.set(T('Comando in corso: ', 'Command running: ') + (self.padre.stato.get() or ''))
        else:
            if str(self.barra.cget('mode')) != 'determinate':
                self.barra.configure(mode='determinate')
            self.barra.configure(value=0)
            self.t_avanzamento.set('')


def ferma_filmati_ia(cartella_gioco: Path, modello: str) -> bool:
    """Chiede a prepara-filmati-ia di fermarsi: il file STOP nella cartella di lavoro (sm2_ia.prepara)."""
    try:
        tmp = cartella_gioco / (L._ia().cartella_filmati(modello) + '.tmp')
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / 'STOP').write_text('stop\n', encoding='utf-8')
        return True
    except OSError:
        return False


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


def icone_della_finestra(root, cartella: Path) -> str:
    """Windows: le icone che la finestra mostra (WM_GETICON; se non ci sono, quelle della classe delle finestre di Tk):
    la piccola (barra del titolo) e la grande (barra delle applicazioni, Alt+Tab), con la grandezza; ciascuna salvata in
    PNG sopra un fondo grigio (gui_icona_piccola.png, gui_icona_grande.png), per vedere che e' quella del launcher."""
    if os.name != 'nt':
        return 'non Windows'
    import ctypes
    from ctypes import wintypes
    H = ctypes.c_void_p

    class ICONINFO(ctypes.Structure):
        _fields_ = [('fIcon', wintypes.BOOL), ('xHotspot', wintypes.DWORD), ('yHotspot', wintypes.DWORD),
                    ('hbmMask', H), ('hbmColor', H)]

    class BITMAP(ctypes.Structure):
        _fields_ = [('bmType', wintypes.LONG), ('bmWidth', wintypes.LONG), ('bmHeight', wintypes.LONG),
                    ('bmWidthBytes', wintypes.LONG), ('bmPlanes', wintypes.WORD), ('bmBitsPixel', wintypes.WORD),
                    ('bmBits', ctypes.c_void_p)]

    class BMI(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG), ('biHeight', wintypes.LONG),
                    ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD), ('pad', wintypes.DWORD * 3)]
    antenato = _api('user32', 'GetAncestor', H, H, ctypes.c_uint)
    messaggio = _api('user32', 'SendMessageW', H, H, ctypes.c_uint, ctypes.c_size_t, H)
    try:
        classe = _api('user32', 'GetClassLongPtrW', H, H, ctypes.c_int)
    except AttributeError:                                  # Python a 32 bit
        classe = _api('user32', 'GetClassLongW', H, H, ctypes.c_int)
    info = _api('user32', 'GetIconInfo', wintypes.BOOL, H, ctypes.POINTER(ICONINFO))
    oggetto = _api('gdi32', 'GetObjectW', ctypes.c_int, H, ctypes.c_int, ctypes.c_void_p)
    cancella = _api('gdi32', 'DeleteObject', wintypes.BOOL, H)
    dc_schermo = _api('user32', 'GetDC', H, H)
    lascia_dc = _api('user32', 'ReleaseDC', ctypes.c_int, H, H)
    dc_nuovo = _api('gdi32', 'CreateCompatibleDC', H, H)
    via_dc = _api('gdi32', 'DeleteDC', wintypes.BOOL, H)
    bitmap = _api('gdi32', 'CreateCompatibleBitmap', H, H, ctypes.c_int, ctypes.c_int)
    scegli = _api('gdi32', 'SelectObject', H, H, H)
    pennello = _api('gdi32', 'CreateSolidBrush', H, wintypes.DWORD)
    riempi = _api('user32', 'FillRect', ctypes.c_int, H, ctypes.POINTER(wintypes.RECT), H)
    disegna = _api('user32', 'DrawIconEx', wintypes.BOOL, H, ctypes.c_int, ctypes.c_int, H, ctypes.c_int, ctypes.c_int,
                   ctypes.c_uint, H, ctypes.c_uint)
    bit = _api('gdi32', 'GetDIBits', ctypes.c_int, H, H, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p,
               ctypes.c_void_p, ctypes.c_uint)
    root.update()
    hwnd = antenato(root.winfo_id(), 2)                     # GA_ROOT
    out = []
    for nome, tipo, n_classe in (('piccola', 0, -34), ('grande', 1, -14)):
        hi, da = messaggio(hwnd, 0x007F, tipo, None), 'finestra'        # WM_GETICON
        if not hi:
            hi, da = classe(hwnd, n_classe), 'classe'                   # GCLP_HICONSM, GCLP_HICON
        if not hi:
            out.append(f'{nome}: nessuna')
            continue
        ii = ICONINFO()
        if not info(hi, ctypes.byref(ii)):
            out.append(f'{nome}: GetIconInfo non riuscito ({da})')
            continue
        bm = BITMAP()
        oggetto(ii.hbmColor or ii.hbmMask, ctypes.sizeof(bm), ctypes.byref(bm))
        w, h = bm.bmWidth, (bm.bmHeight if ii.hbmColor else bm.bmHeight // 2)
        for b in (ii.hbmColor, ii.hbmMask):
            if b:
                cancella(b)
        if w <= 0 or h <= 0 or w > 1024 or h > 1024:
            out.append(f'{nome}: grandezza strana {w}x{h} ({da})')
            continue
        sch = dc_schermo(None)
        dc = dc_nuovo(sch)
        bmp = bitmap(sch, w, h)
        vecchio = scegli(dc, bmp)
        pn = pennello(0x00404040)
        riempi(dc, ctypes.byref(wintypes.RECT(0, 0, w, h)), pn)
        cancella(pn)
        ok = disegna(dc, 0, 0, hi, w, h, 0, None, 3)                    # DI_NORMAL
        scegli(dc, vecchio)
        bmi = BMI()
        bmi.biSize, bmi.biWidth, bmi.biHeight, bmi.biPlanes, bmi.biBitCount = 40, w, -h, 1, 32
        buf = ctypes.create_string_buffer(w * h * 4)
        bit(dc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
        cancella(bmp)
        via_dc(dc)
        lascia_dc(None, sch)
        dati = buf.raw
        righe = []
        for y in range(h):
            riga = dati[y * w * 4:(y + 1) * w * 4]
            rgb = bytearray(w * 3)
            rgb[0::3], rgb[1::3], rgb[2::3] = riga[2::4], riga[1::4], riga[0::4]
            righe.append(bytes(rgb))
        _png(cartella / f'gui_icona_{nome}.png', w, h, righe)
        out.append(f'{nome}: {w}x{h} ({da}), gui_icona_{nome}.png DrawIconEx={ok}')
    return ' ; '.join(out)


def autotest(cartella: Path, cambia: bool = False) -> int:
    """Prova senza mouse: elenco, immagine, (con cambia: cambio di lingua e immagine), comando "stato", seconda
    immagine, finestra dei comandi, finestra dei filmati (ogni scelta, l'originale, il secondo ritaglio), chiusura."""
    cartella.mkdir(parents=True, exist_ok=True)
    reg = open(cartella / 'gui_log.txt', 'w', encoding='utf-8')

    def r(*a):
        reg.write(' '.join(str(x) for x in a) + '\n')
        reg.flush()

    def prova_filmati(f) -> None:
        """La finestra dei filmati della versione scelta: un'immagine per ogni scelta, poi l'originale (come tenendo
        premuto il mouse) e il secondo ritaglio."""
        def attendi(n=8):
            for _ in range(n):
                root.update()
                time.sleep(0.05)
        try:
            ff = f.apri_filmati()
        except Exception as e:  # noqa: BLE001
            r('finestra dei filmati: ERRORE', repr(e))
            return
        r('finestra dei filmati:', ff is not None)
        if ff is None:
            return
        attendi(12)
        r('filmati - immagini di prova:', bool(ff.anteprime), '; da scaricare:', ff.serve, '; programmi:', ff.programmi,
          '; finestra:', ff.top.winfo_width(), 'x', ff.top.winfo_height())
        for v in ff.scelte:
            ff.scelta.set(v)
            ff.mostra()
            attendi()
            r(f'filmati - {v}:', ff.stati[v].cget('text'), '|', ff.dettagli.cget('text'), '|',
              ff.t_tempo.cget('text'), '|', str(ff.t_difetti.cget('text')).replace('\n', ' / '), '| prepara:',
              ff.b_prepara.cget('text'), ff.b_prepara.state(), '| usa:', ff.b_usa.state(), '| scarica:',
              ff.b_scarica.cget('text'), '| immagine:', ff.guardi.get() or '(nessuna)')
            r(cattura_finestra(ff.top, cartella / f'gui_filmati_{v}.png'))
        ff.premuto = True
        ff.mostra_immagine()
        attendi()
        r('filmati - premuto:', ff.guardi.get() or '(nessuna)')
        r(cattura_finestra(ff.top, cartella / 'gui_filmati_originale.png'))
        ff.premuto = False
        if len(ff.anteprime.get('fotogrammi') or []) > 1:
            ff.ritaglio.set(1)
            ff.mostra()
            attendi()
            r('filmati - secondo ritaglio:', ff.dove.get())
            r(cattura_finestra(ff.top, cartella / 'gui_filmati_ritaglio2.png'))
        ff.chiudi()
        r('finestra dei filmati chiusa:', f.finestra_filmati is None)

    def prova_pgxp(f) -> None:
        """La finestra delle voci PGXP (0.12): immagine con PGXP spento e acceso, valori di DuckStation, Annulla
        (le scelte della finestra principale non cambiano)."""
        prima = (f.pgxp.get(), dict(f.pgxp_opz))
        try:
            fp = f.apri_pgxp()
        except Exception as e:  # noqa: BLE001
            r('finestra PGXP: ERRORE', repr(e))
            return
        for _ in range(8):
            root.update()
            time.sleep(0.05)
        r('finestra PGXP:', fp is not None, '; voci:', {k: v.get() for k, v in fp.v.items()}, '; tolleranza:',
          fp.tolleranza.get(), '; soglia:', fp.soglia.get(), '; fessure:', fp.fessure.get())
        r(cattura_finestra(fp.top, cartella / 'gui_pgxp.png'))
        fp.acceso.set(True)
        fp.predefiniti()
        for _ in range(4):
            root.update()
            time.sleep(0.05)
        r('PGXP - valori di DuckStation:', {k: v.get() for k, v in fp.v.items()}, '; attive:',
          [k for k, cb in zip(fp.v, fp.caselle) if 'disabled' not in cb.state()])
        r(cattura_finestra(fp.top, cartella / 'gui_pgxp_acceso.png'))
        fp.chiudi()
        r('finestra PGXP chiusa, scelte invariate:', (f.pgxp.get(), dict(f.pgxp_opz)) == prima)
    dpi_nitido()
    identita_windows()
    root = tk.Tk()
    finestra = {'f': Finestra(root)}
    root.attributes('-topmost', True)
    passi = {'n': 0}
    t0 = time.time()
    r('lingua:', lingua())
    r('aumid:', aumid_attuale())

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
            r('sfondo:', f._con_sfondo, f._sfondo_di)
            r('finestra:', root.winfo_geometry(), '; scala:', round(f.scala, 3), '; tela:', f._dim(),
              '; schermo senza la barra:', area_di_lavoro(root))
            r('tema disegnato:', sorted(k for k in (getattr(root, '_sm2_tema_disegnato', None) or {}) if k != 'px'),
              '; carattere delle caselle:', tkfont_attuale('TkTextFont'))
            r('principale:', f._principale[0], f._principale[2], '; azioni:', f._azioni)
            r(cattura_finestra(root, cartella / 'gui_1.png'))
            r('icona:', f.icona, '|', icone_della_finestra(root, cartella))
            r('collegamento:', json.dumps(chiedi_collegamento(), ensure_ascii=False))
            r('spiegazioni:', len(Suggerimento.tutti))
            f.vai_pagina(1)                  # le caselle delle opzioni si vedono solo nella loro pagina
            for _ in range(6):
                root.update()
                time.sleep(0.05)
            for nome, widget in (('sincronia', f.cb_sinc), ('thread', None), ('filmati', None), ('pgo', None)):
                s = next((x for x in Suggerimento.tutti if (x.w is widget if widget is not None
                                                            else x.testo == SUGG[nome])), None)
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
            f.vai_pagina(0)
            for _ in range(6):
                root.update()
                time.sleep(0.05)
            # spiegazione di un elemento disegnato sulla tela (Reinstalla), come con il mouse sopra
            bb = f.tela.bbox('azione_installa')
            if bb:
                f._sugg_tela.mostra_ora(SUGG['installa'], f.tela.winfo_rootx() + bb[0], f.tela.winfo_rooty() + bb[3])
                for _ in range(8):
                    root.update()
                    time.sleep(0.05)
                r('spiegazione installa (tela): ' + (cattura_finestra(f._sugg_tela._tip, cartella /
                                                                      'gui_spiegazione_installa.png')
                                                     if f._sugg_tela._tip is not None else 'non mostrata'))
                f._sugg_tela.nascondi()
            else:
                r('spiegazione installa (tela): elemento non trovato')
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
            for n_s, nome_s in ((1, 'gui_opzioni.png'), (2, 'gui_salvataggi.png'), (3, 'gui_registro.png')):
                f.vai_pagina(n_s)
                for _ in range(10):
                    root.update()
                    time.sleep(0.05)
                r(f'scheda {n_s}:', cattura_finestra(root, cartella / nome_s))
                if n_s == 2 and f.salvataggi is not None:
                    r('salvataggi:', f.salvataggi.cartella.get(), '|', [c['info'].get() for c in f.salvataggi.card], '|',
                      f.salvataggi.nessuno.get())
                    card_c, altre_c, motivo_c = f.salvataggi.scelte_copia_in()
                    r('copia in un\'altra versione:', card_c, [x['profilo'] for x in altre_c], motivo_c)
                    if altre_c:
                        top_c, _ = f.salvataggi.finestra_copia_in(card_c, altre_c)
                        for _ in range(10):
                            root.update()
                            time.sleep(0.05)
                        r('finestra della copia:', cattura_finestra(top_c, cartella / 'gui_copia_partite.png'))
                        top_c.destroy()
            f.vai_pagina(0)
            root.update()
            fc = f.comandi()
            r('finestra dei comandi:', fc is not None)
            if fc is not None:
                finestra['c'] = fc
                passi['n'] = 3
                passi['t3'] = time.time()
                root.after(1500, passo)
                return
            prova_pgxp(f)
            prova_filmati(f)
            r('fine')
            reg.close()
            root.destroy()
            return
        elif n == 3:                         # finestra dei comandi: lettore dei controller, immagine, chiusura
            fc = finestra['c']
            if fc.proc is None and fc.exe is None and time.time() - passi['t3'] < 60 and \
                    'non disponibile' not in fc.info.get() and 'not available' not in fc.info.get():
                root.after(500, passo)
                return
            root.after(1500)
            root.update()
            r('comandi - info:', fc.info.get())
            r('comandi - scelte:', [e for e, _ in fc.voci], '; scelto:', fc.scelta.get(), '; modo:', fc.modo.get(),
              '; zona:', fc.zona.get())
            r('comandi - righe:', {k: (x['pad'].cget('text'), x['tastiera'].cget('text')) for k, x in fc.righe.items()})
            r(cattura_finestra(fc.top, cartella / 'gui_comandi.png'))
            fc.chiudi()
            r('lettore chiuso:', fc.proc is None)
            prova_pgxp(f)
            prova_filmati(f)
            r('fine')
            reg.close()
            root.destroy()
            return
        passi['n'] += 1
        root.after(700, passo)
    root.after(300, passo)
    root.mainloop()
    return 0


def tkfont_attuale(nome: str) -> dict:
    try:
        import tkinter.font as tkfont
        return tkfont.nametofont(nome).actual()
    except Exception:  # noqa: BLE001
        return {}


def cartelle_precedenti() -> list:
    """Cartelle di versioni precedenti (EnterElectro-Recomp o SM2-Recomp) accanto a questa con dischi o installazioni, se
    qui non ci sono ancora dischi."""
    try:
        if L.INPUT.is_dir() and any(p.is_dir() and any(p.iterdir()) for p in L.INPUT.iterdir()):
            return []
        out = []
        for d in sorted(L.ROOT.parent.iterdir()):
            if d == L.ROOT or not d.is_dir() or not (d / 'tools' / 'sm2_launcher.py').is_file():
                continue
            pieni = [x for x in ((d / 'input'), (d / 'giochi')) if x.is_dir() and any(y.is_dir() for y in x.iterdir())]
            if pieni:
                out.append(d)
        return out[:3]
    except OSError:
        return []


def dpi_nitido() -> None:
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--collegamento' in argv:            # processo a parte lanciato dalla finestra: il collegamento con l'icona
        print(json.dumps(collegamento(L.ROOT), ensure_ascii=True))
        return 0
    if '--autotest' in argv:
        return autotest(Path(argv[argv.index('--autotest') + 1]), cambia='--cambia-lingua' in argv)
    dpi_nitido()
    identita_windows()
    root = tk.Tk()
    f = Finestra(root)
    f.scrivi(f'EnterElectro-Recomp launcher {L.VERSIONE} - {L.ROOT}')
    f.scrivi(T('Per iniziare: "Aggiungi un disco..." (oppure metti il dump in input\\), poi "Installa" e "Gioca".',
               'To start: "Add a disc..." (or put the dump in input\\), then "Install" and "Play".'))
    for vecchia in cartelle_precedenti():
        f.stato.set(T('Trovata la cartella di una versione precedente: vedi la scheda Registro.',
                      'Found the folder of an earlier version: see the Log tab.'))
        f.scrivi(T(f'Trovata la cartella di una versione precedente con dischi o salvataggi: {vecchia}. Per portarli qui: '
                   '"Prendi da una versione precedente...".',
                   f'Found the folder of an earlier version with discs or saves: {vecchia}. To bring them here: "Import '
                   'from an earlier version...".'))
    f.aggiorna()
    collegamento_in_fondo(f)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
