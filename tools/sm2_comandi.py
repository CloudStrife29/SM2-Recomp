# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - comandi del giocatore 1: controller, tasti del controller e della tastiera (dal 4/11/2026).
EnterElectro-Recomp 0.12 - player 1 controls: gamepad choice, gamepad buttons and keyboard keys.

Il gioco (psxrecomp) legge all'avvio, accanto all'eseguibile:
 - settings.toml, sezione [controller]: p1_device ("auto" = primo controller collegato, "keyboard" = solo tastiera,
   oppure il GUID di un controller), p1_mode ("analog" o "digital"), p1_deadzone (0-32767);
 - input.ini: [mapping] per tutti i controller, [mapping.<guid>] per un modello (parte da [mapping]); valori con i
   nomi SDL per posizione (a = tasto in basso, cioe' Croce su PlayStation), assi con il segno (leftx-), piu' valori
   separati da virgole;
 - keybinds.ini: [player1] ... [player5], nomi SDL dei tasti per posizione fisica, un secondo tasto dopo la virgola.
Questo modulo legge e scrive quei file (solo [controller], [mapping] / [mapping.<guid>] e [player1]; il resto resta
com'e'; la prima volta salva una copia <file>.prima_del_launcher) e compila tools/pad/sm2_pad, il programmino con la
SDL3 del gioco che elenca i controller e legge i tasti per la finestra del launcher.
Fonti: psxrecomp/runtime/src/main.cpp (parse_controller_source, default_input_ini_text, load_input_config),
psxrecomp/runtime/src/psx_keybinds.c (PSXKB_PLAYER_DEFAULTS, load_ini, write_ini).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

# (chiave nei file, italiano, inglese): l'ordine e' quello dei file del gioco
COMANDI = [
    ('up', 'Su', 'Up'), ('down', 'Giù', 'Down'), ('left', 'Sinistra', 'Left'), ('right', 'Destra', 'Right'),
    ('cross', 'Croce', 'Cross'), ('circle', 'Cerchio', 'Circle'), ('square', 'Quadrato', 'Square'),
    ('triangle', 'Triangolo', 'Triangle'), ('l1', 'L1', 'L1'), ('r1', 'R1', 'R1'), ('l2', 'L2', 'L2'),
    ('r2', 'R2', 'R2'), ('l3', 'L3 (levetta sinistra premuta)', 'L3 (left stick click)'),
    ('r3', 'R3 (levetta destra premuta)', 'R3 (right stick click)'), ('start', 'Start', 'Start'),
    ('select', 'Select', 'Select'),
    ('ls_up', 'Levetta sinistra su', 'Left stick up'), ('ls_down', 'Levetta sinistra giù', 'Left stick down'),
    ('ls_left', 'Levetta sinistra a sinistra', 'Left stick left'),
    ('ls_right', 'Levetta sinistra a destra', 'Left stick right'),
    ('rs_up', 'Levetta destra su', 'Right stick up'), ('rs_down', 'Levetta destra giù', 'Right stick down'),
    ('rs_left', 'Levetta destra a sinistra', 'Right stick left'),
    ('rs_right', 'Levetta destra a destra', 'Right stick right'),
]
CHIAVI = [c for c, _, _ in COMANDI]

# predefiniti di psxrecomp (default_input_ini_text e PSXKB_PLAYER_DEFAULTS)
PAD_PREDEFINITI = {
    'up': 'dpup', 'down': 'dpdown', 'left': 'dpleft', 'right': 'dpright', 'cross': 'a', 'circle': 'b', 'square': 'x',
    'triangle': 'y', 'l1': 'leftshoulder', 'r1': 'rightshoulder', 'l2': 'lefttrigger', 'r2': 'righttrigger',
    'l3': 'leftstick', 'r3': 'rightstick', 'start': 'start', 'select': 'back', 'ls_up': 'lefty-', 'ls_down': 'lefty+',
    'ls_left': 'leftx-', 'ls_right': 'leftx+', 'rs_up': 'righty-', 'rs_down': 'righty+', 'rs_left': 'rightx-',
    'rs_right': 'rightx+'}
TASTIERA_PREDEFINITI = {
    'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right', 'cross': 'X', 'circle': 'S', 'square': 'Z',
    'triangle': 'A', 'l1': 'Q', 'r1': 'W', 'l2': 'E', 'r2': 'R', 'l3': 'T', 'r3': 'Y', 'start': 'Return',
    'select': 'Right Shift', 'ls_up': 'Up', 'ls_down': 'Down', 'ls_left': 'Left', 'ls_right': 'Right', 'rs_up': 'None',
    'rs_down': 'None', 'rs_left': 'None', 'rs_right': 'None'}
# tasti che il gioco usa gia' da soli (rt/host_keymap.c): legarli a un comando li fa valere due volte
TASTI_DEL_GIOCO = {'Tab': 'avanti veloce / fast forward', 'F': 'prestazioni / performance overlay',
                   'F6': 'F6', 'F7': 'salvataggi di stato / save states', 'F8': 'F8', 'F9': 'F9',
                   'F10': 'menu', 'Keypad +': 'volume', 'Keypad -': 'volume'}
# nomi che il gioco accetta per i tasti del controller (parse_controller_source)
PAD_VALIDI = {'a', 'b', 'x', 'y', 'back', 'view', 'select', 'start', 'menu', 'guide', 'leftstick', 'rightstick',
              'leftshoulder', 'lb', 'l1', 'rightshoulder', 'rb', 'r1', 'dpup', 'dpadup', 'dpdown', 'dpaddown', 'dpleft',
              'dpadleft', 'dpright', 'dpadright', 'lefttrigger', 'lt', 'l2', 'righttrigger', 'rt', 'r2', 'lsright',
              'lsleft', 'lsdown', 'lsup', 'rsright', 'rsleft', 'rsdown', 'rsup', 'misc1', 'paddle1', 'paddle2',
              'paddle3', 'paddle4', 'touchpad', 'none'}
ASSI = {'leftx', 'lefty', 'rightx', 'righty', 'lefttrigger', 'righttrigger'}
GUID_RE = re.compile(r'^[0-9a-fA-F]{32}$')
MODI = {'analog', 'digital'}
ZONA_MORTA_PREDEFINITA = 3277          # circa il 10% (kDefaultDeadzoneRaw)
FILE_COMANDI = ('settings.toml', 'input.ini', 'keybinds.ini')


def pad_valido(valore: str) -> bool:
    """Un valore di input.ini che il gioco riconosce: nomi separati da virgole, assi con il segno (leftx-)."""
    pezzi = [p.strip().lower() for p in str(valore).split(',') if p.strip()]
    if not pezzi:
        return False
    for p in pezzi:
        base = p[:-1] if p[-1:] in '+-' and len(p) > 1 else p
        if base in ASSI:
            if base in ('leftx', 'lefty', 'rightx', 'righty') and p == base:
                return False                   # le levette vogliono il segno
            continue
        if p not in PAD_VALIDI and base not in PAD_VALIDI:
            return False
    return True


def tasto_valido(valore: str) -> bool:
    """Un valore di keybinds.ini plausibile: uno o due nomi, senza caratteri strani (i nomi li da' SDL)."""
    pezzi = [p.strip() for p in str(valore).split(',')]
    return 1 <= len(pezzi) <= 2 and all(p and len(p) <= 32 and '=' not in p and '[' not in p for p in pezzi)


# ---------------------------------------------------------------------------- file ini semplici
def _sezioni(testo: str) -> list:
    """[(nome sezione minuscolo o '' per l'inizio, [righe])] mantenendo l'ordine e le righe com'erano."""
    out = [('', [])]
    for riga in testo.splitlines():
        s = riga.strip()
        if s.startswith('[') and s.endswith(']'):
            out.append((s[1:-1].strip().lower(), [riga]))
        else:
            out[-1][1].append(riga)
    return out


def _valori(righe: list, commenti_in_riga: bool = True) -> dict:
    """chiave minuscola -> valore. commenti_in_riga: ';' e '#' tolgono il resto della riga (input.ini, settings.toml);
    in keybinds.ini solo le righe che iniziano con ';' o '#' sono commenti, perche' '#' e ';' sono anche nomi di tasti."""
    v = {}
    for r in righe:
        s = r.strip()
        if not s or s.startswith(('[', ';', '#')):
            continue
        if commenti_in_riga:
            s = s.split(';', 1)[0].split('#', 1)[0]
        if '=' in s:
            k, x = s.split('=', 1)
            v[k.strip().lower()] = x.strip()
    return v


def _copia_prima(path: Path) -> None:
    if path.is_file():
        copia = path.with_name(path.name + '.prima_del_launcher')
        if not copia.exists():
            shutil.copy2(path, copia)


def leggi(cartella: Path) -> dict:
    """Comandi del giocatore 1 come li trova il gioco nella cartella dell'eseguibile (predefiniti dove mancano)."""
    conf = {'controller': 'auto', 'modo': 'analog', 'zona_morta': ZONA_MORTA_PREDEFINITA,
            'pad': dict(PAD_PREDEFINITI), 'tastiera': dict(TASTIERA_PREDEFINITI), 'pad_guid': {}}
    st = cartella / 'settings.toml'
    if st.is_file():
        sez = dict(_sezioni(st.read_text(encoding='utf-8', errors='replace')))
        v = _valori(sez.get('controller', []))
        if v.get('p1_device'):
            conf['controller'] = v['p1_device'].strip('"\'')
        if v.get('p1_mode', '').strip('"\'') in MODI:
            conf['modo'] = v['p1_mode'].strip('"\'')
        try:
            conf['zona_morta'] = max(0, min(32767, int(v.get('p1_deadzone', conf['zona_morta']))))
        except ValueError:
            pass
    ini = cartella / 'input.ini'
    if ini.is_file():
        for nome, righe in _sezioni(ini.read_text(encoding='utf-8', errors='replace')):
            v = _valori(righe)
            if nome == 'mapping':
                conf['pad'].update({k: x for k, x in v.items() if k in CHIAVI})
            elif nome.startswith('mapping.'):
                conf['pad_guid'][nome[8:]] = {k: x for k, x in v.items() if k in CHIAVI}
    kb = cartella / 'keybinds.ini'
    if kb.is_file():
        sez = dict(_sezioni(kb.read_text(encoding='utf-8', errors='replace')))
        conf['tastiera'].update({k: x for k, x in _valori(sez.get('player1', []), False).items() if k in CHIAVI})
    return conf


def pad_effettivo(conf: dict) -> dict:
    """I tasti del controller che il gioco usera': [mapping.<guid>] del controller scelto sopra [mapping]."""
    pad = dict(conf['pad'])
    g = str(conf.get('controller', '')).lower()
    if GUID_RE.match(g):
        pad.update(conf.get('pad_guid', {}).get(g, {}))
    return pad


def scrivi_settings(path: Path, valori: dict) -> list:
    """Chiavi della sezione [controller] di settings.toml; il resto del file resta com'e'."""
    testo = path.read_text(encoding='utf-8') if path.is_file() else ''
    righe = testo.splitlines()

    def fmt(v):
        return str(v) if isinstance(v, int) else '"' + str(v).replace('\\', '\\\\').replace('"', '\\"') + '"'
    cambiate = []
    inizio = next((i for i, r in enumerate(righe) if r.strip() == '[controller]'), None)
    if inizio is None:
        if righe and righe[-1].strip():
            righe.append('')
        righe.append('[controller]')
        righe += [f'{k} = {fmt(v)}' for k, v in valori.items()]
        cambiate = list(valori)
    else:
        fine = next((i for i in range(inizio + 1, len(righe)) if righe[i].strip().startswith('[')), len(righe))
        for k, v in valori.items():
            pat = re.compile(r'^\s*' + re.escape(k) + r'\s*=')
            idx = next((i for i in range(inizio + 1, fine) if pat.match(righe[i])), None)
            nuova = f'{k} = {fmt(v)}'
            if idx is None:
                dove = max((i for i in range(inizio, fine) if righe[i].strip()), default=inizio) + 1
                righe.insert(dove, nuova)
                fine += 1
                cambiate.append(k)
            elif righe[idx].strip() != nuova:
                righe[idx] = nuova
                cambiate.append(k)
    if cambiate:
        _copia_prima(path)
        path.write_text('\n'.join(righe) + '\n', encoding='utf-8')
    return cambiate


def _sostituisci_sezione(testo: str, nome: str, corpo: list, intestazione: str = '') -> str:
    """Rimpiazza la sezione [nome] (o la aggiunge in fondo) con le righe corpo."""
    sez = _sezioni(testo)
    nuove, fatto = [], False
    for n, righe in sez:
        if n == nome.lower():
            if not fatto:
                nuove.append((n, [righe[0]] + corpo + ['']))
                fatto = True
            continue                                     # una sezione ripetuta: resta solo la prima, rifatta
        nuove.append((n, righe))
    if not fatto:
        ultime = nuove[-1][1]
        if ultime and ultime[-1].strip():
            ultime.append('')
        nuove.append((nome, [f'[{intestazione or nome}]'] + corpo + ['']))
    righe = [r for _, rr in nuove for r in rr]
    while righe and not righe[-1].strip():
        righe.pop()
    return '\n'.join(righe) + '\n'


def scrivi_input_ini(path: Path, pad: dict, guid: str = '') -> bool:
    """[mapping] con tutti i 24 comandi (vale per tutti i controller), uguale anche in ogni [mapping.<guid>] che c'e'
    gia' (scritto per esempio dalla finestra di psxrecomp: altrimenti coprirebbe la scelta per quel controller) e, con
    un controller preciso, in [mapping.<guid>] di quello. Il resto del file resta com'e'."""
    if path.is_file():
        testo = path.read_text(encoding='utf-8', errors='replace')
    else:
        testo = ('; PSXRecomp input mapping (scritto dal launcher di EnterElectro-Recomp; nomi SDL per posizione, vedi i\n'
                 '; commenti del file predefinito del gioco).\n\n[controller]\nenabled = true\ndevice = 0\n'
                 'deadzone = 3277\n')
    corpo = [f'{k} = {pad.get(k, PAD_PREDEFINITI[k])}' for k in CHIAVI]
    nuovo = _sostituisci_sezione(testo, 'mapping', corpo)
    g = guid.lower()
    altri = [n for n, _ in _sezioni(nuovo) if n.startswith('mapping.')]
    for n in altri + ([f'mapping.{g}'] if GUID_RE.match(g) and f'mapping.{g}' not in altri else []):
        nuovo = _sostituisci_sezione(nuovo, n, corpo)
    if path.is_file() and nuovo == testo:
        return False
    _copia_prima(path)
    path.write_text(nuovo, encoding='utf-8')
    return True


def scrivi_keybinds(path: Path, tastiera: dict) -> bool:
    """Solo [player1] di keybinds.ini (gli altri giocatori restano com'erano)."""
    if path.is_file():
        testo = path.read_text(encoding='utf-8', errors='replace')
    else:
        testo = ('# PSXRecomp Keyboard Keybinds (keyboard -> DualShock), scritto dal launcher di EnterElectro-Recomp.\n'
                 '# Nomi SDL dei tasti per posizione fisica; "None" = nessuno; un secondo tasto dopo la virgola.\n')
    corpo = [f'{k:<9} = {tastiera.get(k, TASTIERA_PREDEFINITI[k])}' for k in CHIAVI]
    nuovo = _sostituisci_sezione(testo, 'player1', corpo)
    if path.is_file() and nuovo == testo:
        return False
    _copia_prima(path)
    path.write_text(nuovo, encoding='utf-8')
    return True


def scrivi(cartella: Path, conf: dict) -> list:
    """Scrive i comandi nella cartella di un eseguibile. Restituisce i file cambiati."""
    cambiati = []
    zona = max(0, min(32767, int(conf.get('zona_morta', ZONA_MORTA_PREDEFINITA))))
    if scrivi_settings(cartella / 'settings.toml', {'p1_device': conf.get('controller', 'auto'),
                                                    'p1_mode': conf.get('modo', 'analog'), 'p1_deadzone': zona}):
        cambiati.append('settings.toml')
    if 'pad' in conf and scrivi_input_ini(cartella / 'input.ini', conf['pad'], str(conf.get('controller', ''))):
        cambiati.append('input.ini')
    if 'tastiera' in conf and scrivi_keybinds(cartella / 'keybinds.ini', conf['tastiera']):
        cambiati.append('keybinds.ini')
    return cambiati


def doppioni(mappa: dict, tastiera: bool = False) -> dict:
    """{valore: [comandi]} per i valori legati a piu' di un comando. Le direzioni della croce e della levetta sinistra
    sulla tastiera (frecce) sono doppie apposta, come nei predefiniti del gioco."""
    uso = {}
    for k in CHIAVI:
        for p in str(mappa.get(k, '')).split(','):
            p = p.strip()
            if not p or p.lower() == 'none':
                continue
            uso.setdefault(p if tastiera else p.lower(), []).append(k)
    apposta = {('up', 'ls_up'), ('down', 'ls_down'), ('left', 'ls_left'), ('right', 'ls_right')}
    out = {}
    for v, ks in uso.items():
        if len(ks) > 1 and not (len(ks) == 2 and tuple(ks) in apposta):
            out[v] = ks
    return out


# ---------------------------------------------------------------------------- sm2_pad
def strumento_pad(tools: Path, toolchain: Path, log=print, T=lambda it, en: it):
    """tools/pad/sm2_pad.exe compilato con CMake e la SDL3 statica del toolchain (la stessa del gioco). Lo rifa' se
    il sorgente e' piu' nuovo. Restituisce il percorso o None."""
    src = tools / 'pad'
    nome = 'sm2_pad.exe' if os.name == 'nt' else 'sm2_pad'
    exe = src / 'build' / nome
    sorgenti = [src / 'sm2_pad.c', src / 'CMakeLists.txt']
    if not all(s.is_file() for s in sorgenti):
        log(T(f'ERRORE: mancano i sorgenti di sm2_pad in {src}', f'ERROR: the sm2_pad sources are missing in {src}'))
        return None
    if exe.is_file() and all(exe.stat().st_mtime >= s.stat().st_mtime for s in sorgenti if s.is_file()):
        return exe
    sdl3 = os.environ.get('SDL3_DIR') or str(toolchain / 'deps' / 'lib' / 'cmake' / 'SDL3')
    cmake = shutil.which('cmake') or str(toolchain / 'bin' / ('cmake.exe' if os.name == 'nt' else 'cmake'))
    log(T('[comandi] compilo tools/pad/sm2_pad (controller e tastiera per la finestra)',
          '[controls] building tools/pad/sm2_pad (gamepad and keyboard for the window)'))
    uscita = src / 'build_log.txt'
    with open(uscita, 'w', encoding='utf-8', errors='replace') as out:
        r = subprocess.run([cmake, '-S', str(src), '-B', str(src / 'build'), '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
                            f'-DSDL3_DIR={sdl3}'], stdout=out, stderr=subprocess.STDOUT)
        if r.returncode == 0:
            r = subprocess.run([cmake, '--build', str(src / 'build')], stdout=out, stderr=subprocess.STDOUT)
    if r.returncode != 0 or not exe.is_file():
        log(T(f'ERRORE: sm2_pad non compilato (dettagli in {uscita})', f'ERROR: sm2_pad not built (details in {uscita})'))
        return None
    return exe


def elenco_controller(exe: Path, timeout: int = 15) -> dict:
    """{'sdl': versione, 'pad': [{id, nome, tipo, guid, etichette}]} dai controller collegati adesso."""
    flags = 0x08000000 if os.name == 'nt' else 0               # CREATE_NO_WINDOW
    p = subprocess.run([str(exe), 'elenco'], capture_output=True, timeout=timeout, creationflags=flags)
    for riga in p.stdout.decode('utf-8', 'replace').splitlines():
        if riga.strip().startswith('{'):
            try:
                return json.loads(riga)
            except ValueError:
                pass
    return {'errore': p.stderr.decode('utf-8', 'replace')[-300:] or 'nessuna risposta'}
