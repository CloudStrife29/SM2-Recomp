#!/usr/bin/env python3
"""SM2-Recomp - launcher (prototipo, 27/10/2026): dal disco dell'utente al gioco per PC, tutto in locale.

English: SM2-Recomp launcher - from the user's own disc to the PC game, everything done locally. Commands (the Italian
names keep working): identify, import, install, play, options, status, gui, text, prepare-recording. Messages are in
Italian or English (tools/sm2_lingua.py: --lingua/--language it|en, SM2_LINGUA, lingua.txt, Windows display language).

Come OpenGOAL: l'utente fornisce il suo disco di Spider-Man 2: Enter Electro (PS1), il launcher lo
riconosce, genera il codice C del gioco e lo compila sul suo PC. Nel progetto non c'e' nessun dato
del gioco: solo fatti (hash, offset, indirizzi) in aot/.

Non tocca il sistema: niente PATH o registro di Windows. Il toolchain portatile del progetto
(tools/toolchain/cmake-clang-v1, scaricato da SM2-Launcher.cmd) vale solo per questo processo e per
quelli che lancia, come env.bat. Non usa mai `ensure-toolchain` di psxrecomp (scrive nel registro) e
l'eseguibile del launcher non contiene la procedura guidata di psxrecomp, che lo lancerebbe.

Comandi:
  riconosci [PERCORSO ...]   riconosce i dump (cartelle, o file .cue/.ccd/.bin/.img/.iso);
                             senza percorsi guarda in input/
  importa PERCORSO [...]     riconosce i dump e li sposta in input/<PROFILO>/, creando la cartella
                             (--copia per copiarli invece di spostarli). Non sovrascrive mai niente.
  installa --profilo P       prepara giochi/<P>/ dal disco dell'utente: progetto psxrecomp, codice C
                             del gioco, moduli di CD.WAD compilati in anticipo (Milestone 3) ed
                             eseguibile. --debug compila anche build-dev (server di debug, per i test).
                             --pgo (v0.10): eseguibile ottimizzato con il PGO di clang dopo una partita di
                             allenamento di circa 3 minuti (finestra nascosta, audio spento): circa il 15% di
                             CPU in meno (misura del 4/11/2026), qualche minuto di installazione in piu'. --attese si|no (v0.10, di
                             default si): salto delle attese di psxrecomp nel game.toml.
  avvia --profilo P          avvia il gioco installato (--risoluzione 1080p ecc., --con-launcher per
                             la finestra delle impostazioni di psxrecomp prima del gioco)
  opzioni --profilo P        opzioni che restano (mod di psxrecomp: --risoluzione, --pgxp si|no,
                             --filtro-texture, --scaling, --crt si|no, --audio-hq si|no, --widescreen
                             no|16:9|16:10|21:9, --distanza si|no), scritte in
                             mods/state.toml accanto all'eseguibile, e --attese si|no (salto delle
                             attese, nel game.toml); dal 31/10/2026 anche lo schermo e la presentazione,
                             in settings.toml accanto all'eseguibile: --sincronia accesa|spenta|adattiva|vrr,
                             --thread-video si|no, --schermo finestra|senza-bordi|esclusivo,
                             --larghezza-finestra N, --latenza-bassa si|no, --movimento-fluido si|no;
                             senza opzioni le mostra
  stato                      versioni conosciute, dischi trovati, versioni installate
  gui                        la finestra (tools/sm2_launcher_gui.py); e' anche quello che succede senza
                             comandi. Senza tkinter: il menu di testo, che si apre anche con "testo".

Il catalogo delle versioni e' aot/sm2_versioni.json; le basi dei moduli aot/sm2_placements.json; gli
indirizzi del renderer per la mod "Distanza visiva" aot/sm2_renderer.json.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sm2_lingua import NOMI_EN, T, imposta as imposta_lingua, lingua as lingua_scelta, lingua_gioco, nome_versione  # noqa: E402,F401

VERSIONE = '0.11'
ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / 'tools'
CATALOGO = ROOT / 'aot' / 'sm2_versioni.json'
PLACEMENTS = ROOT / 'aot' / 'sm2_placements.json'
RENDERER = ROOT / 'aot' / 'sm2_renderer.json'
INPUT = ROOT / 'input'
GIOCHI = ROOT / 'giochi'
TOOLCHAIN = TOOLS / 'toolchain' / 'cmake-clang-v1'
EXE_BASE = 'SpiderMan2EnterElectro'
GIUNZIONI = ('psxrecomp', 'recomp-ui')
# Ottimizzazione su tutto il programma (ThinLTO) anche nelle cartelle di compilazione gia' esistenti (2/11/2026, sera):
# il set(... CACHE ...) del CMakeLists.txt vale solo per una cartella nuova; in una cartella configurata prima dal
# psxrecomp della 0.11 resta PSX_RUNTIME_IPO=OFF (option di psxrecomp), quindi il valore va passato a CMake.
IPO_ON = ['--cmake-extra=-DPSX_RUNTIME_IPO=ON']
# Motore grafico Vulkan di psxrecomp (sperimentale, 31/10/2026): per compilarlo servono le intestazioni ufficiali di Vulkan e
# un compilatore degli shader. tools\\scarica_vulkan.cmd li mette in tools\\vulkan (niente installazione nel sistema); se ci
# sono, "installa" compila anche Vulkan e lo rende sceglibile (game.toml [video] offer_vulkan, opzioni --motore vulkan).
VULKAN = ROOT / 'tools' / 'vulkan'
SALTA_IN_INPUT = {'bios', '_duplicati'}
SOGLIA_SCIOLTI_MB = 100          # immagini senza foglio trovate cercando in una cartella: solo file grandi
SPAZIO_MINIMO_GB = 4             # per installare una versione (codice C, oggetti, eseguibili)
RISOLUZIONI = ('native', '720p', '1080p', '1440p', '4k')

_log_f = None


def log(*a) -> None:
    riga = ' '.join(str(x) for x in a)
    print(riga, flush=True)
    if _log_f:
        _log_f.write(riga + '\n')
        _log_f.flush()


def apri_log(path: Path) -> None:
    global _log_f
    path.parent.mkdir(parents=True, exist_ok=True)
    _log_f = open(path, 'a', encoding='utf-8', errors='replace')
    _log_f.write(f'\n== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} sm2_launcher {VERSIONE}: '
                 f'{" ".join(sys.argv[1:])}\n')


def catalogo() -> dict:
    return json.loads(CATALOGO.read_text(encoding='utf-8'))['versioni']


# --------------------------------------------------------------------------------------------- dischi

class ErroreDisco(Exception):
    pass


class Immagine:
    """Il file della traccia dati: settori da 2352 byte (dump completo), 2048 (immagine "cotta") o
    2336, con il file system ISO9660 del disco."""

    LAYOUT = ((2352, 24), (2048, 0), (2336, 8))

    def __init__(self, path: Path):
        self.path = path
        self.f = open(path, 'rb')
        try:
            self.settore, self.testa = self._layout()
        except Exception:
            self.f.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.f.close()

    def _layout(self):
        for size, testa in self.LAYOUT:
            self.f.seek(16 * size + testa)
            b = self.f.read(6)
            if len(b) == 6 and b[1:6] == b'CD001':
                return size, testa
        raise ErroreDisco(T('nessun file system ISO9660: non e\' l\'immagine di un disco',
                            'no ISO9660 file system: this is not a disc image'))

    def modo(self) -> int:
        """Modo del settore 16 (1 o 2; i dischi PS1 sono in modo 2), solo per i dump da 2352 byte."""
        if self.settore != 2352:
            return 0
        self.f.seek(16 * 2352 + 15)
        return self.f.read(1)[0]

    def leggi(self, lba: int, size: int) -> bytes:
        out = bytearray()
        for i in range((size + 2047) // 2048):
            self.f.seek((lba + i) * self.settore + self.testa)
            d = self.f.read(2048)
            if len(d) != 2048:
                raise ErroreDisco(T(f'settore {lba + i} non leggibile: file troncato?',
                                    f'sector {lba + i} cannot be read: truncated file?'))
            out += d
        return bytes(out[:size])

    def cartella(self, lba: int, size: int):
        data = self.leggi(lba, size)
        i, voci = 0, []
        while i < len(data):
            n = data[i]
            if n == 0:
                i = (i // 2048 + 1) * 2048
                continue
            nome = data[i + 33:i + 33 + data[i + 32]]
            if nome not in (b'\x00', b'\x01'):
                voci.append((nome.decode('ascii', 'replace').split(';')[0].upper(),
                             int.from_bytes(data[i + 2:i + 6], 'little'),
                             int.from_bytes(data[i + 10:i + 14], 'little'), bool(data[i + 25] & 2)))
            i += n
        return voci

    def trova(self, percorso: str):
        """(lba, size) di un file, per esempio 'SYSTEM.CNF' o '\\DIR\\FILE.EXE', o None."""
        pvd = self.leggi(16, 2048)
        lba, size = int.from_bytes(pvd[158:162], 'little'), int.from_bytes(pvd[166:170], 'little')
        parti = [p for p in re.split(r'[\\/]', percorso.upper()) if p]
        for k, parte in enumerate(parti):
            for nome, l, s, d in self.cartella(lba, size):
                if nome == parte and d == (k < len(parti) - 1):
                    lba, size = l, s
                    break
            else:
                return None
        return lba, size


def _frame(m, s, f) -> int:
    return (int(m) * 60 + int(s)) * 75 + int(f)


def _msf(frame: int) -> str:
    return f'{frame // 4500:02d}:{frame // 75 % 60:02d}:{frame % 75:02d}'


def leggi_cue(cue: Path) -> dict:
    """File e tracce di un foglio .cue; la traccia dati e' il primo TRACK MODEx."""
    files = []
    for riga in cue.read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'\s*FILE\s+"([^"]+)"', riga, re.I) or re.match(r'\s*FILE\s+(\S+)', riga, re.I)
        if m:
            files.append({'nome': m.group(1), 'tracce': []})
            continue
        m = re.match(r'\s*TRACK\s+(\d+)\s+(\S+)', riga, re.I)
        if m and files:
            files[-1]['tracce'].append({'n': int(m.group(1)), 'tipo': m.group(2).upper(), 'indici': {}})
            continue
        m = re.match(r'\s*INDEX\s+(\d+)\s+(\d+):(\d+):(\d+)', riga, re.I)
        if m and files and files[-1]['tracce']:
            files[-1]['tracce'][-1]['indici'][int(m.group(1))] = _frame(*m.group(2, 3, 4))
    tracce = sum(len(f['tracce']) for f in files)
    for f in files:
        for k, t in enumerate(f['tracce']):
            if not t['tipo'].startswith('MODE'):
                continue
            m = re.match(r'MODE(\d)/(\d+)', t['tipo'])
            settore = int(m.group(2)) if m else 2352
            limite = None
            if k + 1 < len(f['tracce']):      # altre tracce nello stesso file: la traccia dati finisce prima
                dopo = f['tracce'][k + 1]['indici']
                inizio = dopo.get(0, dopo.get(1))
                if inizio is not None:
                    limite = inizio * settore
            return {'dati': cue.parent / f['nome'], 'settore_cue': settore, 'limite': limite,
                    'file': [cue] + [cue.parent / x['nome'] for x in files], 'tracce': tracce}
    raise ErroreDisco(T('il foglio .cue non ha una traccia dati (TRACK ... MODE1/MODE2)',
                        'the .cue sheet has no data track (TRACK ... MODE1/MODE2)'))


def leggi_ccd(ccd: Path) -> dict:
    """Dump CloneCD: .ccd + .img (+ .sub). Tracce dalle voci [Entry] con Point 1..99."""
    vicini = {p.name.lower(): p for p in ccd.parent.iterdir()}
    img = vicini.get(ccd.stem.lower() + '.img')
    if img is None:
        raise ErroreDisco(T(f'manca {ccd.stem}.img accanto a {ccd.name}', f'{ccd.stem}.img is missing next to {ccd.name}'))
    voci, cur = [], None
    for riga in ccd.read_text(encoding='utf-8', errors='replace').splitlines():
        riga = riga.strip()
        if riga.startswith('['):
            cur = {} if riga.lower().startswith('[entry') else None
            if cur is not None:
                voci.append(cur)
            continue
        if cur is not None and '=' in riga:
            k, v = riga.split('=', 1)
            cur[k.strip().lower()] = v.strip()
    tracce = []
    for v in voci:
        try:
            point, control, plba = int(v['point'], 0), int(v.get('control', '0'), 0), int(v['plba'])
        except (KeyError, ValueError):
            continue
        if 1 <= point <= 99:
            tracce.append({'n': point, 'dati': bool(control & 4), 'plba': plba})
    tracce.sort(key=lambda t: t['n'])
    file = [ccd, img] + [p for k, p in vicini.items() if k in (ccd.stem.lower() + '.sub', ccd.stem.lower() + '.cue')]
    limite = None
    if len(tracce) > 1 and tracce[0]['dati']:
        limite = (tracce[1]['plba'] - 150) * 2352        # la pausa prima della traccia 2 non e' dati
    return {'dati': img, 'settore_cue': 2352, 'limite': limite, 'file': file, 'tracce': max(1, len(tracce)),
            'tracce_ccd': tracce}


def cue_per_immagine(img: Path, modo: int, tracce_ccd=None) -> str:
    """Foglio .cue per un'immagine a 2352 byte senza foglio (o con il .ccd di CloneCD)."""
    righe = [f'FILE "{img.name}" BINARY', f'  TRACK 01 MODE{modo or 2}/2352', '    INDEX 01 00:00:00']
    for t in (tracce_ccd or [])[1:]:
        righe.append(f'  TRACK {t["n"]:02d} {"MODE2/2352" if t["dati"] else "AUDIO"}')
        if t['plba'] >= 150:
            righe.append(f'    INDEX 00 {_msf(t["plba"] - 150)}')
        righe.append(f'    INDEX 01 {_msf(t["plba"])}')
    return '\n'.join(righe) + '\n'


class CacheHash:
    """SHA-1 dei file grandi, ricordati per percorso, dimensione e data di modifica."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.d = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.d = {}
        self.cambiata = False

    def sha1(self, f: Path, limite=None) -> str:
        st = f.stat()
        chiave = f'{f.resolve()}|{st.st_size}|{st.st_mtime_ns}|{limite or 0}'
        if chiave in self.d:
            return self.d[chiave]
        h, resto = hashlib.sha1(), (limite if limite else st.st_size)
        with open(f, 'rb') as fh:
            while resto > 0:
                b = fh.read(min(8 << 20, resto))
                if not b:
                    break
                h.update(b)
                resto -= len(b)
        self.d[chiave] = h.hexdigest()
        self.cambiata = True
        return self.d[chiave]

    def salva(self) -> None:
        if self.cambiata:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.d, indent=0), encoding='utf-8')


def riconosci_dump(foglio: Path, cache: CacheHash, cat: dict) -> dict:
    """Riconosce un dump: foglio .cue/.ccd o immagine senza foglio."""
    r = {'foglio': str(foglio), 'formato': None, 'dati': None, 'file': [], 'tracce': 1, 'settore': None,
         'seriale': None, 'exe': None, 'exe_sha1': None, 'profilo': None, 'nome': None,
         'dati_sha1': None, 'traccia1_sha1': None, 'redump': None, 'problemi': [], 'avvisi': []}
    try:
        est = foglio.suffix.lower()
        if est == '.cue':
            info = leggi_cue(foglio)
            r['formato'] = 'cue'
        elif est == '.ccd':
            info = leggi_ccd(foglio)
            r['formato'] = 'ccd'
        else:
            info = {'dati': foglio, 'settore_cue': None, 'limite': None, 'file': [foglio], 'tracce': 1}
            r['formato'] = 'immagine senza foglio'
        dati = info['dati']
        r.update(dati=str(dati), file=[str(p) for p in info['file']], tracce=info['tracce'])
        mancanti = [p.name for p in info['file'] if not p.is_file()]
        if mancanti:
            raise ErroreDisco(T('file mancanti: ', 'missing files: ') + ', '.join(mancanti))
        with Immagine(dati) as im:
            r['settore'] = im.settore
            r['modo'] = im.modo()
            cnf_pos = im.trova('SYSTEM.CNF')
            if cnf_pos is None:
                raise ErroreDisco(T('SYSTEM.CNF non c\'e\': non e\' un disco PlayStation',
                                    'no SYSTEM.CNF: this is not a PlayStation disc'))
            cnf = im.leggi(*cnf_pos).decode('ascii', 'replace')
            m = re.search(r'BOOT\s*=\s*cdrom:\\?([^;\s]+)', cnf, re.I)
            if not m:
                raise ErroreDisco(T('SYSTEM.CNF senza la riga BOOT', 'SYSTEM.CNF has no BOOT line'))
            percorso_exe = m.group(1)
            r['exe'] = re.split(r'[\\/]', percorso_exe)[-1].upper()
            m2 = re.match(r'([A-Z]{4})[_-]?(\d{3})\.?(\d{2})', r['exe'])
            r['seriale'] = f'{m2.group(1)}-{m2.group(2)}{m2.group(3)}' if m2 else None
            exe_pos = im.trova(percorso_exe)
            if exe_pos is None:
                raise ErroreDisco(T(f'{r["exe"]} (indicato da SYSTEM.CNF) non c\'e\' sul disco',
                                    f'{r["exe"]} (named in SYSTEM.CNF) is not on the disc'))
            r['exe_sha1'] = hashlib.sha1(im.leggi(*exe_pos)).hexdigest()
        for p, v in cat.items():
            if v['exe_sha1'] == r['exe_sha1']:
                r['profilo'], r['nome'] = p, nome_versione(p, v['nome'])
        if r['profilo'] is None:
            r['problemi'].append(T(f'versione sconosciuta (eseguibile {r["exe"] or "?"} con SHA-1 '
                                   f'{(r["exe_sha1"] or "?")[:12]}...): non e\' una delle 7 versioni di '
                                   'Spider-Man 2: Enter Electro che il progetto conosce',
                                   f'unknown version (executable {r["exe"] or "?"} with SHA-1 '
                                   f'{(r["exe_sha1"] or "?")[:12]}...): it is not one of the 7 versions of '
                                   'Spider-Man 2: Enter Electro that the project knows'))
        if r['settore'] == 2048:
            r['problemi'].append(T('immagine "cotta" a 2048 byte per settore: mancano i dati dei filmati e '
                                   'dell\'audio (settori XA). Serve un dump completo a 2352 byte (.bin/.cue)',
                                   '"cooked" image with 2048 bytes per sector: the movie and audio data (XA sectors) '
                                   'are missing. A complete dump with 2352 bytes per sector (.bin/.cue) is needed'))
        elif r['settore'] == 2336:
            r['problemi'].append(T('immagine a 2336 byte per settore: formato non supportato, serve un dump a '
                                   '2352 byte (.bin/.cue)',
                                   'image with 2336 bytes per sector: format not supported, a dump with 2352 bytes '
                                   'per sector (.bin/.cue) is needed'))
        if info.get('settore_cue') and r['settore'] and info['settore_cue'] != r['settore']:
            r['problemi'].append(T(f'il foglio dice {info["settore_cue"]} byte per settore, il file ne ha {r["settore"]}',
                                   f'the sheet says {info["settore_cue"]} bytes per sector, the file has {r["settore"]}'))
        if r['settore'] == 2352:
            r['dati_sha1'] = cache.sha1(dati)
            if info.get('limite') and info['limite'] < dati.stat().st_size:
                r['traccia1_sha1'] = cache.sha1(dati, info['limite'])
            if r['profilo']:
                for rd in cat[r['profilo']].get('redump', []):
                    if rd['sha1'] in (r['dati_sha1'], r['traccia1_sha1']):
                        r['redump'] = rd['nome']
                if not r['redump']:
                    r['avvisi'].append(T('dump non uguale a quello di Redump: probabilmente va bene lo stesso '
                                         '(i moduli vengono controllati uno per uno all\'installazione)',
                                         'dump not identical to the Redump one: it is probably fine anyway '
                                         '(the modules are checked one by one during installation)'))
        if r['formato'] != 'cue' and not r['problemi']:
            r['avvisi'].append(T('senza foglio .cue: "importa" ne scrive uno accanto all\'immagine',
                                 'no .cue sheet: "import" writes one next to the image'))
    except (ErroreDisco, OSError, UnicodeDecodeError) as e:
        r['problemi'].append(str(e))
    return r


def foglio_di(f: Path) -> Path:
    """Per un'immagine indicata direttamente (.bin/.img/.iso), il .cue o .ccd accanto che la cita, se c'e'."""
    if f.suffix.lower() not in ('.bin', '.img', '.iso'):
        return f
    for vicino in sorted(f.parent.iterdir()):
        try:
            if vicino.suffix.lower() == '.cue':
                citati = leggi_cue(vicino)['file']
            elif vicino.suffix.lower() == '.ccd':
                citati = leggi_ccd(vicino)['file']
            else:
                continue
        except (ErroreDisco, OSError):
            continue
        if any(p.name.lower() == f.name.lower() for p in citati):
            return vicino
    return f


def trova_dump(percorsi, soglia_mb=SOGLIA_SCIOLTI_MB):
    """Fogli .cue/.ccd e immagini senza foglio, dai percorsi (file o cartelle, cercando dentro)."""
    trovati, citati, sciolti = [], set(), []
    for base in percorsi:
        base = Path(base)
        if base.is_file():
            trovati.append(foglio_di(base))
            continue
        if not base.is_dir():
            log(T(f'  {base}: non esiste', f'  {base}: does not exist'))
            continue
        for d, sotto, nomi in os.walk(base):
            if Path(d).resolve() == INPUT.resolve():
                sotto[:] = [s for s in sotto if s.lower() not in SALTA_IN_INPUT]
            sotto.sort()
            nomi_l = {n.lower() for n in nomi}
            for n in sorted(nomi):
                p = Path(d) / n
                est = p.suffix.lower()
                if est == '.cue':
                    if Path(n).stem.lower() + '.ccd' in nomi_l:
                        continue                              # lo gestisce il .ccd
                    trovati.append(p)
                    try:
                        citati.update(str(x).lower() for x in leggi_cue(p)['file'])
                    except (ErroreDisco, OSError):
                        pass
                elif est == '.ccd':
                    trovati.append(p)
                    citati.add(str(p.with_suffix('.img')).lower())
                    citati.update(str(Path(d) / x).lower() for x in nomi if x.lower() == Path(n).stem.lower() + '.img')
                elif est in ('.bin', '.img', '.iso'):
                    sciolti.append(p)
    for p in sciolti:
        if str(p).lower() not in citati and p.stat().st_size >= soglia_mb * 1024 * 1024:
            trovati.append(p)
    return trovati


def stampa_dump(r: dict) -> None:
    stato = 'OK' if r['profilo'] and not r['problemi'] else T('NON USABILE', 'NOT USABLE')
    formato = T(r['formato'], 'image without sheet') if r['formato'] == 'immagine senza foglio' else r['formato']
    log(f'== {r["foglio"]}')
    log(T(f'   formato: {formato}, tracce: {r["tracce"]}, settori da {r["settore"] or "?"} byte',
          f'   format: {formato}, tracks: {r["tracce"]}, sectors of {r["settore"] or "?"} bytes'))
    if r['exe']:
        log(T(f'   seriale {r["seriale"]}, eseguibile {r["exe"]} (SHA-1 {r["exe_sha1"]})',
              f'   serial {r["seriale"]}, executable {r["exe"]} (SHA-1 {r["exe_sha1"]})'))
    if r['profilo']:
        log(T(f'   VERSIONE: {r["profilo"]} - {r["nome"]}', f'   VERSION: {r["profilo"]} - {r["nome"]}'))
    if r['dati_sha1']:
        log(T(f'   traccia dati: SHA-1 {r["dati_sha1"]}', f'   data track: SHA-1 {r["dati_sha1"]}') +
            (T(f' (solo la traccia 1: {r["traccia1_sha1"]})', f' (track 1 only: {r["traccia1_sha1"]})')
             if r['traccia1_sha1'] else ''))
    if r['redump']:
        log(T(f'   dump verificato con Redump: {r["redump"]}', f'   dump verified with Redump: {r["redump"]}'))
    for a in r['avvisi']:
        log(T(f'   avviso: {a}', f'   warning: {a}'))
    for p in r['problemi']:
        log(T(f'   PROBLEMA: {p}', f'   PROBLEM: {p}'))
    log(f'   -> {stato}')


def cmd_riconosci(args) -> int:
    cat = catalogo()
    cache = CacheHash(GIOCHI / 'cache_hash.json')
    percorsi = args.percorsi or [INPUT]
    risultati = []
    for f in trova_dump(percorsi, args.soglia_mb):
        r = riconosci_dump(f, cache, cat)
        stampa_dump(r)
        risultati.append(r)
    cache.salva()
    ok = [r for r in risultati if r['profilo'] and not r['problemi']]
    log(T(f'\n{len(risultati)} dump trovati, {len(ok)} usabili: ', f'\n{len(risultati)} dumps found, {len(ok)} usable: ') +
        (', '.join(sorted({r["profilo"] for r in ok})) or T('nessuno', 'none')))
    if args.json:
        Path(args.json).write_text(json.dumps(risultati, indent=1, ensure_ascii=False), encoding='utf-8')
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------- importa

def importa_dump(r: dict, copia: bool = False) -> str:
    """Sposta (o copia) i file di un dump riconosciuto in input/<PROFILO>/; scrive un .cue se manca."""
    prof = r['profilo']
    file = [Path(x) for x in r['file']]
    dest = INPUT / prof
    posti = {(INPUT / prof).resolve(), (INPUT / '_duplicati' / prof).resolve()}
    if len({p.parent.resolve() for p in file}) == 1 and file[0].parent.resolve() in posti:
        dest = file[0].parent
        esito = T('gia\' al suo posto', 'already in place') + (T(' (tra i duplicati)', ' (among the duplicates)')
                                                               if dest.resolve() != (INPUT / prof).resolve() else '')
    else:
        if any(p.parent.resolve() != file[0].parent.resolve() for p in file):
            return T('NON importato: i file del dump sono in cartelle diverse, spostali a mano in ',
                     'NOT imported: the dump files are in different folders, move them by hand to ') + str(dest)
        if dest.is_dir() and any(x.suffix.lower() in ('.cue', '.ccd') for x in dest.iterdir()):
            dest = INPUT / '_duplicati' / prof        # la versione ha gia' un dump: questo va a parte
        dest.mkdir(parents=True, exist_ok=True)
        gia = [p.name for p in file if (dest / p.name).exists()]
        if gia:
            return T(f'NON importato: in {dest} ci sono gia\' file con lo stesso nome ({", ".join(gia)})',
                     f'NOT imported: {dest} already has files with the same name ({", ".join(gia)})')
        for p in file:
            if copia:
                shutil.copy2(p, dest / p.name)
            else:
                shutil.move(str(p), str(dest / p.name))
        esito = (T('copiato', 'copied') if copia else T('spostato', 'moved')) + T(f' in {dest}', f' to {dest}')
    if r['formato'] != 'cue':
        dati = dest / Path(r['dati']).name
        cue = dati.with_suffix('.cue')
        if not cue.exists():
            tracce = leggi_ccd(dest / Path(r['foglio']).name).get('tracce_ccd') if r['formato'] == 'ccd' else None
            cue.write_text(cue_per_immagine(dati, r.get('modo') or 2, tracce), encoding='utf-8', newline='\r\n')
            esito += T(f'; scritto {cue.name}', f'; {cue.name} written')
    return esito


def cmd_importa(args) -> int:
    cat = catalogo()
    cache = CacheHash(GIOCHI / 'cache_hash.json')
    n_ok = 0
    for f in trova_dump(args.percorsi, args.soglia_mb):
        r = riconosci_dump(f, cache, cat)
        stampa_dump(r)
        if r['profilo'] and not r['problemi']:
            esito = importa_dump(r, args.copia)
            log(T(f'   IMPORTA: {esito}', f'   IMPORT: {esito}'))
            n_ok += not esito.startswith(('NON', 'NOT'))
    cache.salva()
    log(T(f'\n{n_ok} dump importati', f'\n{n_ok} dumps imported'))
    return 0 if n_ok else 1


def disco_della_versione(prof: str, cache: CacheHash, cat: dict):
    """Il dump di quella versione in input/<PROFILO>/ (riconosciuto e usabile), o None."""
    cartella = INPUT / prof
    if not cartella.is_dir():
        return None
    for f in sorted(cartella.glob('*.cue')):
        r = riconosci_dump(f, cache, cat)
        if r['profilo'] == prof and not r['problemi']:
            return r
    return None


# ------------------------------------------------------------------------------------------ toolchain

def attiva_toolchain() -> str:
    """Come env.bat: il toolchain portatile nel PATH di questo processo (e dei figli), mai nel sistema."""
    tc = TOOLCHAIN
    if not (tc / 'bin').is_dir():
        return T('toolchain portatile non trovato in ', 'portable toolchain not found in ') + str(tc) + (
            T(' (lancia SM2-Launcher.cmd, che lo scarica)', ' (run SM2-Launcher.cmd, which downloads it)')
            if os.name == 'nt' else '')
    parti = os.environ.get('PATH', '').split(os.pathsep)
    for d in (tc / 'python', tc / 'bin'):
        if str(d).lower() not in (x.lower() for x in parti):
            parti.insert(0, str(d))
    os.environ['PATH'] = os.pathsep.join(parti)
    ext = '.exe' if os.name == 'nt' else ''
    os.environ.update(CC=str(tc / 'bin' / f'clang{ext}'), CXX=str(tc / 'bin' / f'clang++{ext}'),
                      AR=str(tc / 'bin' / f'llvm-ar{ext}'), RANLIB=str(tc / 'bin' / f'llvm-ranlib{ext}'),
                      RETCOMM_TOOLCHAIN_DIR=str(tc), RETCOMM_PYTHON=str(tc / 'python' / f'python{ext}'),
                      PYTHONNOUSERSITE='1')
    os.environ.pop('PYTHONHOME', None)
    os.environ.pop('PYTHONPATH', None)
    if (tc / 'deps' / 'include' / 'zlib.h').is_file():
        os.environ['ZLIB_ROOT'] = str(tc / 'deps')
    sdl3 = tc / 'deps' / 'lib' / 'cmake' / 'SDL3'
    if (sdl3 / 'SDL3Config.cmake').is_file() or (sdl3 / 'SDL3-config.cmake').is_file():
        os.environ['SDL3_DIR'] = str(sdl3)
    return T('toolchain portatile attivo (solo per questo processo): ',
             'portable toolchain active (only for this process): ') + str(tc)


def dipendenze_offline() -> str:
    """Pacchetto completo (3/11/2026): se in psxrecomp/third_party/ ci sono gli archivi delle librerie che la prima
    compilazione prenderebbe da internet (libchdr e libwebp, con i nomi di deps.manifest; SDL3 e zlib vengono dagli
    strumenti), dice a psxrecomp di non scaricare niente (PSX_DEPS_OFFLINE=1): una libreria che mancasse diventa un
    errore chiaro invece di un download. Se ne manca uno (per esempio con git clone) la prima compilazione lo scarica,
    come prima. CMake controlla comunque ogni archivio con l'impronta SHA-256 di deps.manifest."""
    terzi = ROOT / 'psxrecomp' / 'third_party'
    try:
        righe = [r.split() for r in (terzi / 'deps.manifest').read_text(encoding='utf-8').splitlines()
                 if r.strip() and not r.lstrip().startswith('#')]
    except OSError:
        return T('psxrecomp/third_party/deps.manifest non trovato: le librerie che mancano si scaricano da internet',
                 'psxrecomp/third_party/deps.manifest not found: the missing libraries are downloaded from the internet')
    voci = {r[0]: r[1] for r in righe if len(r) == 4}
    mancano = [voci[n] for n in ('psx_libchdr', 'psx_libwebp') if n in voci and not (terzi / voci[n]).is_file()]
    if mancano:
        return (T('librerie di psxrecomp da scaricare da internet alla prima compilazione (circa 4 MB; il pacchetto '
                  'completo le contiene gia\'): ',
                  'psxrecomp libraries to download from the internet at the first build (about 4 MB; the complete '
                  'package already contains them): ') + ', '.join(mancano))
    os.environ['PSX_DEPS_OFFLINE'] = '1'
    return T('librerie di psxrecomp tutte nel pacchetto (libchdr, libwebp): la compilazione non scarica niente da internet',
             'psxrecomp libraries all in the package (libchdr, libwebp): the build downloads nothing from the internet')


def imposta_core(n: int) -> int:
    """Core per compilare: di default tre quarti dei processori logici (24 su 32), come chiesto il 27/10/2026:
    quasi tutta la velocita' e un po' di margine per il resto del PC."""
    tot = os.cpu_count() or 2
    n = n if n > 0 else max(1, tot * 3 // 4)
    os.environ['CMAKE_BUILD_PARALLEL_LEVEL'] = str(n)
    os.environ['PSXRECOMP_AOT_WORKERS'] = str(n)
    return n


# ------------------------------------------------------------------------------------------- progetto

CMAKELISTS = r'''cmake_minimum_required(VERSION 3.20)
# SM2-Recomp - @NOME@ (@PROFILO@). Progetto scritto da tools/sm2_launcher.py a partire dal disco
# dell'utente: il codice C del gioco viene generato qui, in locale (generated/, mai nel repository).
# psxrecomp e recomp-ui sono giunzioni alle cartelle della radice del progetto.
set(PSXRECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/psxrecomp" CACHE PATH "Path to psxrecomp")
if(NOT EXISTS "${PSXRECOMP_ROOT}/runtime/runtime.cmake")
    message(FATAL_ERROR "PSXRecomp runtime is missing: ${PSXRECOMP_ROOT}/runtime/runtime.cmake")
endif()

project(SM2_Recomp LANGUAGES C CXX)

# Niente procedura guidata di psxrecomp (setup wizard, "Generate & rebuild"): generazione e
# compilazione le fa il launcher, e la procedura guidata lancerebbe ensure-toolchain, che scrive nel
# registro di Windows. La finestra del launcher di recomp-ui (impostazioni) resta disponibile.
# Ottimizzazione su tutto il programma (ThinLTO, opzione PSX_RUNTIME_IPO di psxrecomp; 2/11/2026): circa il 10%
# di lavoro in meno per frame, comportamento del gioco identico. Valore di partenza: si puo' cambiare con
# -DPSX_RUNTIME_IPO=OFF; con un psxrecomp che non ha l'opzione non fa niente.
set(PSX_RUNTIME_IPO ON CACHE BOOL "SM2-Recomp: ottimizzazione su tutto il programma (ThinLTO)")
include("${PSXRECOMP_ROOT}/runtime/runtime.cmake")

set(PSX_PRELOADED_MODS "${CMAKE_CURRENT_SOURCE_DIR}/mods/preloaded")
if(NOT IS_DIRECTORY "${PSX_PRELOADED_MODS}")
    set(PSX_PRELOADED_MODS "NONE")
endif()

psxrecomp_add_game_runtime(psx-runtime
    PRELOADED_MODS_DIR "${PSX_PRELOADED_MODS}"
    WINDOW_TITLE "@TITOLO@"
    EXE_NAME "@EXE_BASE@"
    DEFAULT_GAME_CONFIG_PATH "game.toml"
    MAX_PLAYERS 1
@PGXP@    # Milestone 3: i moduli di CD.WAD compilati in anticipo (aot/overlays.json, generato dal disco
    # dell'utente). Se il file manca la build funziona lo stesso: i moduli li compila il gioco.
    GAME_OVERLAY_STATIC_C "${CMAKE_CURRENT_SOURCE_DIR}/generated/aot/overlays_static.c"
    GEN_MARKER "generated/@EXE@_dispatch.c"
    GEN_FULL_GLOB "generated/@EXE@_full_*.c"
)

# Mod "Widescreen" di SM2-Recomp (spenta di default, si accende tra le mod o con sm2_launcher.py opzioni
# --widescreen 16:9): il plugin sceglie le proporzioni prima che la finestra si apra. Il pacchetto della
# mod e' in mods/preloaded/, le impostazioni dell'HUD nella sezione [widescreen] del game.toml.
target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_widescreen.c")

# Portatili con due schede video (Intel o AMD integrata piu' NVIDIA o AMD dedicata): l'eseguibile chiede ai driver la
# scheda dedicata (launcher dal 31/10/2026). Non cambia niente nel sistema: sono due variabili esportate dall'eseguibile.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_gpu_preferita.c")
    target_sources(psx-runtime PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_gpu_preferita.c")
endif()

# Mod "Distanza visiva" (spenta di default; c'e' solo nelle versioni con gli indirizzi del renderer in
# aot/sm2_renderer.json): plugin sull'estensione del renderer Neversoft di psxrecomp. I punti di aggancio
# sono nella sezione [recompiler] del game.toml.
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_draw_distance.cpp")
    target_sources(psx-runtime PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_draw_distance.cpp"
        "${CMAKE_CURRENT_SOURCE_DIR}/mods_src/sm2_draw_distance_init.c")
endif()

foreach(_PSX_RUNTIME_CONFIG game.toml game_options.toml)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}")
        add_custom_command(TARGET psx-runtime POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different
                "${CMAKE_CURRENT_SOURCE_DIR}/${_PSX_RUNTIME_CONFIG}"
                "$<TARGET_FILE_DIR:psx-runtime>/${_PSX_RUNTIME_CONFIG}"
            COMMENT "Staging ${_PSX_RUNTIME_CONFIG}"
            VERBATIM)
    endif()
endforeach()
'''

# QA, livello 4 (3/11/2026): registratore delle partite di psxrecomp (Playtest Diagnostics), solo nelle installazioni di
# prova fatte con "installa --registratore" (mai in quelle normali): registra a ogni frame i tasti del giocatore e un
# controllo della RAM in saves/diagnostics/ accanto all'eseguibile, per rigiocare la stessa partita con
# replay-diagnostics.py (psxrecomp/docs/PLAYTEST_DIAGNOSTICS.md). Non cambia il gioco.
CMAKE_REGISTRATORE = '''
# QA di SM2-Recomp (installa --registratore): registratore delle partite di psxrecomp (Playtest Diagnostics).
# Registra i tasti e un controllo della RAM a ogni frame in saves/diagnostics/ accanto all'eseguibile, per rigiocare la
# stessa partita (replay-diagnostics.py). Il pacchetto sm2.diagnostics e' in mods/preloaded/. Non cambia il gioco.
include("${PSXRECOMP_ROOT}/runtime/playtest_diagnostics.cmake")
psxrecomp_add_playtest_diagnostics(psx-runtime GAME_ID "@PROFILO@" MOD_ID "sm2.diagnostics")
'''

MANIFESTO_DIAGNOSTICA = '''format_version = 5
id = "sm2.diagnostics"
version = "1.0.0"
name = "Playtest diagnostics"
author = "SM2-Recomp"
description = "Test builds only: records the controller and a RAM check every frame in saves/diagnostics, so the same game can be replayed exactly (replay-diagnostics.py). It does not change the game."
resolver = "declarative"
save_compatibility = "shared"

[[target]]
game_id = "*"

[[feature]]
id = "recording"
name = "Recording"
description = "Records the session in saves/diagnostics beside the game. L3 + R3 together mark an incident and take a screenshot."
group = "Diagnostics"
default_enabled = false

[[feature]]
id = "osd"
name = "Input display"
description = "Shows the buttons being pressed."
group = "Diagnostics"
default_enabled = false

[[plugin]]
feature = "recording"
id = "sm2.diagnostics"

[[plugin]]
feature = "osd"
id = "sm2.diagnostics.osd"
'''

SYMBOLS = '''# Spider-Man 2: Enter Electro - @NOME@ (@PROFILO@): mappa dei simboli, scritta da tools/sm2_launcher.py.
# Vedi psxrecomp/docs/SYMBOLS.md.

[[func]]
pc = 0x@ENTRY@
name = "BootEntry"
emit = false
status = "guessed"
note = "SYSTEM.CNF / EXE entry PC (probe seed)"
'''

GPU_PREFERITA = r'''/* SM2-Recomp - scheda video dedicata sui portatili con due schede video, scritto da tools/sm2_launcher.py.
 *
 * I driver NVIDIA (Optimus) e AMD (PowerXpress / Switchable Graphics) leggono queste due variabili esportate
 * dall'eseguibile del gioco: se valgono 1 usano la scheda dedicata invece di quella integrata nel processore.
 * Sui PC con una sola scheda video non fanno niente. Non cambiano impostazioni del sistema.
 */
#ifdef _WIN32
__declspec(dllexport) unsigned long NvOptimusEnablement = 0x00000001;
__declspec(dllexport) int AmdPowerXpressRequestHighPerformance = 1;
#endif
'''


PLUGIN_WIDESCREEN = r'''/* SM2-Recomp - mod "Widescreen" di Spider-Man 2: Enter Electro, scritta da tools/sm2_launcher.py.
 *
 * Quando il giocatore accende la mod (pacchetto sm2.enhancement.widescreen in mods/preloaded/), questo
 * plugin sceglie le proporzioni della finestra prima che si apra. Il resto lo fa psxrecomp: proiezione
 * della scena piu' larga e HUD con le proporzioni giuste (chiavi [widescreen] del game.toml). Con la mod
 * spenta non succede niente: il gioco resta in 4:3 com'e'.
 */
#include "mod_plugins.h"

#include <string.h>

static void sm2_widescreen_attiva(void) {
    char scelta[16] = "";
    uint32_t num = 16, den = 9;
    if (psx_mod_current_option_value("aspect", scelta, (uint32_t)sizeof scelta)) {
        if (strcmp(scelta, "21:9") == 0) {
            num = 21;
            den = 9;
        } else if (strcmp(scelta, "16:10") == 0) {
            num = 16;
            den = 10;
        }
    }
    (void)psx_mod_set_fixed_display_aspect(num, den);
}

PSX_MOD_CONSTRUCTOR(sm2_widescreen_registra) {
    (void)psx_mod_register_activation_plugin("sm2.widescreen", sm2_widescreen_attiva);
}
'''

MANIFESTO_WIDESCREEN = '''format_version = 5
id = "sm2.enhancement.widescreen"
version = "1.0.0"
name = "Widescreen"
author = "SM2-Recomp"
description = "Wider view for Spider-Man 2: Enter Electro: the 3D scene is projected wider, the floor and the objects at the sides are drawn, and the HUD keeps its proportions. Menus and 2D screens stay 4:3."
resolver = "declarative"
save_compatibility = "shared"

[[target]]
game_id = "*"

[[feature]]
id = "widescreen"
name = "Widescreen"
description = "Disabled by default (the original 4:3 picture). Experimental."
group = "Visual"
default_enabled = false

[[option]]
feature = "widescreen"
id = "aspect"
label = "Aspect ratio"
description = "Shape of the game window."
group = "Visual"
type = "choice"
default = "16:9"

[[option.choice]]
value = "16:9"
label = "16:9"

[[option.choice]]
value = "16:10"
label = "16:10"

[[option.choice]]
value = "21:9"
label = "21:9"

[[plugin]]
feature = "widescreen"
id = "sm2.widescreen"
'''

# gte_game_mode: psxrecomp allarga l'immagine solo nei momenti che riconosce come "di gioco"; per Spider-Man 2
# li riconosce dai vertici 3D proiettati dalla GTE. Senza, il widescreen non si attiva (provato il 27/10).
RIGA_GTE = '''# SM2-Recomp (launcher v0.7): i momenti di gioco si riconoscono dai vertici 3D della GTE; senza questa
# chiave il widescreen non si attiva e il gioco resta in 4:3 al centro della finestra.
gte_game_mode = true
'''

BLOCCO_WIDESCREEN = '''
# SM2-Recomp (tools/sm2_launcher.py): impostazioni per la mod "Widescreen". Con la mod spenta (4:3) queste
# chiavi non cambiano niente. La bussola di Spider-Man unisce due quadrati e una freccia 3D, quindi i
# pezzi dell'HUD si correggono sul posto (auto_ui_anchor = "in_place", docs/WIDESCREEN.md).
[widescreen]
hud_sprt_squash = true
auto_ui_squash = true
auto_ui_anchor = "in_place"
''' + RIGA_GTE


def aggiorna_toml_widescreen(toml: Path) -> str:
    """Sezione [widescreen] del game.toml per la mod "Widescreen": la aggiunge se manca e, nelle installazioni
    fatte dal launcher v0.5-v0.6, aggiunge gte_game_mode. Il gioco legge il game.toml all'avvio, quindi basta
    questo, senza ricompilare. Restituisce cosa ha cambiato ('' se niente)."""
    testo = toml.read_text(encoding='utf-8')
    if '[widescreen]' not in testo:
        toml.write_text(testo.rstrip('\n') + '\n' + BLOCCO_WIDESCREEN, encoding='utf-8')
        return T('game.toml: aggiunta la sezione [widescreen] (HUD e riconoscimento del gioco per la mod Widescreen)',
                 'game.toml: [widescreen] section added (HUD and gameplay detection for the Widescreen mod)')
    if 'gte_game_mode' not in testo and 'auto_ui_anchor = "in_place"\n' in testo:
        nuovo = testo.replace('auto_ui_anchor = "in_place"\n', 'auto_ui_anchor = "in_place"\n' + RIGA_GTE, 1)
        toml.write_text(nuovo, encoding='utf-8')
        return T('game.toml: aggiunto gte_game_mode = true nella sezione [widescreen] (senza, il widescreen non si attiva)',
                 'game.toml: gte_game_mode = true added in the [widescreen] section (without it the widescreen does not turn on)')
    return ''



PLUGIN_DISTANZA = r'''/* SM2-Recomp - mod "Distanza visiva" di Spider-Man 2: Enter Electro, @NOME@ (@PROFILO@).
 * Scritta da tools/sm2_launcher.py con gli indirizzi di aot/sm2_renderer.json, controllati
 * sull'eseguibile di questa versione prima di scrivere questo file.
 *
 * Usa l'estensione del renderer Neversoft di psxrecomp (runtime/include/mod_neversoft_renderer.hpp):
 *  - funzione "draw-distance": la nebbia comincia piu' lontano (aggancio alla funzione che la imposta) e un
 *    aggancio all'invio dei pacchetti alla GPU conta quanto si riempie l'area dei pacchetti (contatori
 *    sm2.draw-distance.peak e .full, comando mod_counters del server di debug);
 *  - funzione "subdivision-precision": con PGXP acceso, precisione anche per i poligoni che il gioco
 *    suddivide vicino alla telecamera.
@AREA_NOTA@ * Ogni aggancio controlla in RAM l'istruzione originale o le variabili prima di fare qualcosa. Con le
 * funzioni spente (cosi' sono di default) il gioco resta com'e'.
 */
#include "mod_neversoft_renderer.hpp"

#include <cstdlib>
#include <cstring>

namespace {
struct SM2Renderer {
    static constexpr const char *Plugin = "sm2.draw-distance", *PrecisionPlugin = "sm2.subdivision-precision";
    static constexpr const char *AreaPlugin = "sm2.packet-area";
    static constexpr const char *FogCounter = "sm2.draw-distance.fog", *PeakCounter = "sm2.draw-distance.peak";
    static constexpr const char *FullCounter = "sm2.draw-distance.full", *PacketCounter = "sm2.draw-distance.packet";
    static constexpr const char *ArenaCounter = "sm2.draw-distance.arena";
    static constexpr const char *PrecisionCounter = "sm2.subdivision-precision.store";
    static constexpr uint32_t BufferA = @BufferA@u, BufferB = BufferA + 0x78u;
    static constexpr uint32_t Current = @Current@u, Cursor = @Cursor@u, Limit = @Limit@u;
    static constexpr uint32_t AllocA = @AllocA@u, AllocB = @AllocB@u, AllocWord = @AllocWord@u;
    static constexpr uint32_t FogPc = @FogPc@u, SwapPc = @SwapPc@u, LimitPc = @LimitPc@u;
    static constexpr uint32_t SubmitPc = @SubmitPc@u, PrecisionPc = @PrecisionPc@u;
@AREA_PUNTI@};
using Renderer = PSXNeversoftRenderer<SM2Renderer>;
@AREA_ATTIVA@}  // namespace

@BORDI_CODICE@@PIANI_CODICE@@GIOCO_CODICE@
extern "C" void sm2_distanza_registra(void) {
    psx_mod_register_activation_plugin(SM2Renderer::Plugin, sm2_distanza_attiva);
    psx_mod_register_function_entry_plugin(SM2Renderer::Plugin, SM2Renderer::FogPc, Renderer::fog);
    psx_mod_register_function_entry_plugin(SM2Renderer::Plugin, SM2Renderer::SubmitPc, Renderer::submit);
    psx_mod_register_instruction_plugin(SM2Renderer::PrecisionPlugin, SM2Renderer::PrecisionPc, 0x4819B000u,
                                        Renderer::subdivision_precision);
@AREA_REGISTRA@@BORDI_REGISTRA@@PIANI_REGISTRA@@GIOCO_REGISTRA@}
'''

# Area dei pacchetti piu' grande (launcher v0.9). La prova del 27/10/2026 alle 17:35 (launcher v0.6) si era
# fermata all'inizio del primo livello con un comando non valido per la GPU (0xF1): l'estensione corregge il
# calcolo della lunghezza dei pacchetti nei punti PacketT2 e PacketS2, dove pero' in Spider-Man 2 il registro
# contiene solo il numero di parole; il punto in cui il gioco la calcola dalla parola che contiene anche il
# collegamento al pacchetto precedente e' un altro (PacketLink, uno solo in ogni versione).
AREA_NOTA = ''' * Area dei pacchetti piu' grande (launcher v0.9): con la nebbia piu' lontana il gioco disegna molti piu'
 * poligoni, e l'area dove prepara i pacchetti per la GPU passa da 0x17000 byte (94.208) a 0x60000 (393.216)
 * per ciascuno dei due buffer, nella memoria che psxrecomp riserva alle mod (indirizzi della GPU da
 * 0x00800000): agganci allo scambio dei buffer (@SwapPc@), al calcolo del limite (@LimitPc@) e al
 * calcolo della lunghezza dei pacchetti. Oltre ai 2 punti dell'estensione (@PacketT2@ e @PacketS2@,
 * dove il registro ha solo il numero di parole) c'e' @PacketLink@: li' Spider-Man 2 calcola la lunghezza
 * dalla parola che contiene anche il collegamento al pacchetto precedente, e senza la correzione i bit 22-23
 * dell'indirizzo della nuova area la sbaglierebbero di 2 byte (prova del 27/10/2026 alle 17:35: la GPU ha
 * ricevuto un comando non valido, 0xF1). L'area si prende una volta sola (contatore sm2.draw-distance.arena:
 * scambi con la nuova area; sm2.draw-distance.packet: lunghezze corrette).
 * Per i test: SM2_AREA_PACCHETTI=originale lascia l'area del gioco; SM2_DISTANZA_MISURA=1 lascia nebbia e
 * area del gioco, e restano solo i contatori.
'''
AREA_NOTA_NO = ''' * Non usa l'area dei pacchetti piu' grande dell'estensione: per questa versione manca il punto in cui il
 * gioco calcola la lunghezza di un pacchetto dalla parola con il collegamento al pacchetto precedente
 * (PacketLink in aot/sm2_renderer.json). Se l'area dei pacchetti si riempie, il gioco smette di aggiungere
 * poligoni in quel frame (come nel gioco originale).
 * Per i test: con la variabile d'ambiente SM2_DISTANZA_MISURA=1 la nebbia resta quella originale e
 * restano solo i contatori.
'''
AREA_PUNTI = '''    static constexpr PSXNeversoftPacketLengthSite PacketLengthSites[] = {
        {@PacketT2@u, 0x000A5582u}, {@PacketS2@u, 0x00129582u}, {@PacketLink@u, 0x000A5582u},
    };
'''
AREA_ATTIVA = '''
uint32_t sm2_area = 0;      /* 2 x 0x60000 byte, presi alla prima attivazione e poi riusati */

void sm2_distanza_attiva(void) {
    const char* misura = std::getenv("SM2_DISTANZA_MISURA");
    const char* area = std::getenv("SM2_AREA_PACCHETTI");
    const bool solo_misura = misura && misura[0] == '1';
    Renderer::extended = !solo_misura;                    /* nebbia piu' lontana, tranne nei test di misura */
    const bool grande = !solo_misura && !(area && std::strcmp(area, "originale") == 0);
    if (grande && !sm2_area)
        sm2_area = psx_mod_alloc_gpu_dma_memory(2 * Renderer::ArenaSize, 8);
    Renderer::arena = grande ? sm2_area : 0;              /* 0: area dei pacchetti originale */
    Renderer::peak = 0;
    Renderer::packet_corrections = 0;
}

/* Launcher v0.11: la stessa area anche con il solo widescreen, che a 21:9 disegna molti piu' poligoni (prova del
 * 28/10/2026: con i piani laterali allargati, in e4m1 l'area del gioco si riempiva in 14 frame). Funzione nascosta
 * "packet-area" del pacchetto della distanza visiva, plugin sm2.packet-area: la accendono da soli, per la sessione,
 * il widescreen ([[requirement]] nel suo pacchetto) e la distanza visiva (stessi agganci registrati anche per lei).
 * Con tutte e due accese gli agganci girano due volte: lo scambio dei buffer e la lunghezza dei pacchetti danno lo
 * stesso risultato, e del calcolo del limite conta solo il primo. */
void sm2_area_attiva(void) {
    const char* misura = std::getenv("SM2_DISTANZA_MISURA");
    const char* area = std::getenv("SM2_AREA_PACCHETTI");
    const bool grande = !(misura && misura[0] == '1') && !(area && std::strcmp(area, "originale") == 0);
    if (grande && !sm2_area)
        sm2_area = psx_mod_alloc_gpu_dma_memory(2 * Renderer::ArenaSize, 8);
    Renderer::arena = grande ? sm2_area : 0;
    Renderer::peak = 0;
    Renderer::packet_corrections = 0;
}
'''
ATTIVA_SENZA_AREA = '''
void sm2_distanza_attiva(void) {
    const char* misura = std::getenv("SM2_DISTANZA_MISURA");
    Renderer::extended = !(misura && misura[0] == '1');   /* nebbia piu' lontana, tranne nei test di misura */
    Renderer::arena = 0;          /* area dei pacchetti originale */
    Renderer::peak = 0;
    Renderer::packet_corrections = 0;
}
'''
AREA_REGISTRA = '''    /* area dei pacchetti piu' grande: scambio dei buffer, limite e lunghezza dei pacchetti (3 punti) */
    psx_mod_register_function_entry_plugin(SM2Renderer::Plugin, SM2Renderer::SwapPc, Renderer::swap);
    psx_mod_register_function_filter_plugin(SM2Renderer::Plugin, SM2Renderer::LimitPc, Renderer::limit);
    for (const auto& punto : SM2Renderer::PacketLengthSites)
        psx_mod_register_instruction_plugin(SM2Renderer::Plugin, punto.address, punto.word,
            punto.word == 0x000A5582u ? Renderer::packet_length_t2 : Renderer::packet_length_s2);
    /* launcher v0.11: la stessa area per la funzione nascosta "packet-area" (accesa anche dal widescreen) */
    psx_mod_register_activation_plugin(SM2Renderer::AreaPlugin, sm2_area_attiva);
    psx_mod_register_function_entry_plugin(SM2Renderer::AreaPlugin, SM2Renderer::SwapPc, Renderer::swap);
    psx_mod_register_function_filter_plugin(SM2Renderer::AreaPlugin, SM2Renderer::LimitPc, Renderer::limit);
    psx_mod_register_function_entry_plugin(SM2Renderer::AreaPlugin, SM2Renderer::SubmitPc, Renderer::submit);
    for (const auto& punto : SM2Renderer::PacketLengthSites)
        psx_mod_register_instruction_plugin(SM2Renderer::AreaPlugin, punto.address, punto.word,
            punto.word == 0x000A5582u ? Renderer::packet_length_t2 : Renderer::packet_length_s2);
'''
# sll t5,t5,24; or t2,t2,t5; sw t2,0(t3); srl t2,t2,22: il punto PacketLink e' l'ultima istruzione
COLLEGAMENTO = (0x000D6E00, 0x014D5025, 0xAD6A0000, 0x000A5582)

# Mod "Widescreen" (launcher v0.8): bordi dello schermo largo nei bit "fuori schermo" dei vertici. Va nello
# stesso file del renderer (sm2_draw_distance.cpp) perche' usa gli indirizzi di aot/sm2_renderer.json; gli
# agganci appartengono al plugin sm2.widescreen, quindi funzionano solo con la mod Widescreen accesa.
BORDI_CODICE = r'''
/* Mod "Widescreen" (plugin sm2.widescreen, launcher v0.8). Il renderer segna ogni vertice proiettato con bit
 * "fuori schermo" (bit 13: a sinistra, bit 14: a destra; 29 e 30: sopra e sotto) e scarta oggetti, poligoni e
 * pezzi dei poligoni suddivisi che hanno tutti i vertici dalla stessa parte. Con lo schermo largo psxrecomp
 * disegna anche ai lati (psx_mod_widescreen_x_margin() pixel in piu' per parte): questi agganci ricalcolano i
 * due bit orizzontali con il margine, subito dopo il calcolo del gioco. La coordinata X che legge la GPU
 * (bit 0-10) non cambia, e a 4:3 (margine 0) non cambia niente. Punti, controllati dal launcher su questo
 * eseguibile: @BordiA@ e @BordiB@ (andi t9,t8,1: vertice in t2, larghezza dello schermo in t4),
 * @BordiC@ (sw t2,0(v1): vertice in t2, larghezza in t4) e PrecisionPc - 4 (sw s0,0(a1): vertice in s0,
 * larghezza in s4). Il contatore sm2.widescreen.edges conta i vertici corretti.
 * Altre 5 funzioni (@Limiti1@, @Limiti2@, @Limiti3@, @Limiti4@, @Limiti5@) segnano i vertici
 * con confronti "slt" contro i limiti dello schermo che caricano all'inizio (s0 = destra, s1 = sinistra): li
 * l'aggancio, su "ori s7,zero,0xFFFF" subito dopo il caricamento, allarga i due limiti del margine (contatore
 * sm2.widescreen.bounds, una volta per chiamata). */
namespace {
struct SM2Bordi {
    static constexpr const char *Plugin = "sm2.widescreen", *Counter = "sm2.widescreen.edges";
    static constexpr const char *LimitiCounter = "sm2.widescreen.bounds";
    static constexpr uint32_t A = @BordiA@u, B = @BordiB@u, C = @BordiC@u, Griglia = @PrecisionPc@u - 4u;
    static constexpr uint32_t Limiti[5] = {@Limiti1@u, @Limiti2@u, @Limiti3@u, @Limiti4@u, @Limiti5@u};
};

void sm2_limiti(CPUState* cpu, uint32_t) {
    const int32_t m = psx_mod_widescreen_x_margin();
    if (m <= 0) return;
    const int32_t destra = int32_t(cpu->gpr[16]), sinistra = int32_t(cpu->gpr[17]);
    if (destra < 256 || destra > 1024 || sinistra < -64 || sinistra > 64) return;
    cpu->gpr[16] = uint32_t(destra + m);
    cpu->gpr[17] = uint32_t(sinistra - m);
    psx_mod_counter_add(SM2Bordi::LimitiCounter, 1);
}

template <unsigned Vertice, unsigned Larghezza>
void sm2_bordi(CPUState* cpu, uint32_t) {
    const int32_t m = psx_mod_widescreen_x_margin();
    if (m <= 0) return;
    const int32_t w = int32_t(int16_t(uint16_t(cpu->gpr[Larghezza] & 0xFFFFu)));
    if (w < 256 || w > 1024) return;
    const uint32_t v = cpu->gpr[Vertice];
    const int32_t x = int32_t((v & 0x7FFu) ^ 0x400u) - 0x400;     /* X a 11 bit, come la legge la GPU */
    const uint32_t bit = (x < -m ? 0x2000u : 0u) | (x >= w + m ? 0x4000u : 0u);
    if ((v & 0x6000u) == bit) return;
    cpu->gpr[Vertice] = (v & ~0x6000u) | bit;
    psx_mod_counter_add(SM2Bordi::Counter, 1);
}
}  // namespace
'''

BORDI_REGISTRA = '''    /* mod "Widescreen": bordi dello schermo largo nei bit "fuori schermo" dei vertici */
    psx_mod_register_instruction_plugin(SM2Bordi::Plugin, SM2Bordi::A, 0x33190001u, sm2_bordi<10, 12>);
    psx_mod_register_instruction_plugin(SM2Bordi::Plugin, SM2Bordi::B, 0x33190001u, sm2_bordi<10, 12>);
    psx_mod_register_instruction_plugin(SM2Bordi::Plugin, SM2Bordi::C, 0xAC6A0000u, sm2_bordi<10, 12>);
    psx_mod_register_instruction_plugin(SM2Bordi::Plugin, SM2Bordi::Griglia, 0xACB00000u, sm2_bordi<16, 20>);
    for (uint32_t punto : SM2Bordi::Limiti)
        psx_mod_register_instruction_plugin(SM2Bordi::Plugin, punto, 0x3417FFFFu, sm2_limiti);
'''

# Mod "Widescreen" (launcher v0.11): oggetti interi ai lati. Prima di disegnare un oggetto il gioco lo confronta con
# 6 piani (vicino, lontano, sopra, sotto, sinistra, destra) calcolati a ogni frame dalla larghezza dello schermo 4:3, e
# scarta interi quelli fuori da un piano: con lo schermo largo, un oggetto che stava solo nelle parti in piu' ai lati
# non veniva disegnato e compariva in ritardo. L'aggancio allarga i due piani laterali del margine dello schermo largo.
PIANI_CODICE = r'''
/* Mod "Widescreen" (plugin sm2.widescreen, launcher v0.11): oggetti interi ai lati. Prima di disegnare gli oggetti il
 * gioco li confronta con 6 piani (vicino, lontano, sopra, sotto, sinistra, destra) che calcola a ogni frame dalla
 * larghezza dello schermo 4:3, e scarta interi quelli che stanno tutti fuori da un piano: con lo schermo largo, un
 * oggetto che stava solo nelle parti in piu' ai lati non veniva disegnato e compariva in ritardo, quando entrava
 * nella parte 4:3. L'aggancio, su "sll s3,v0,11" (@PianiX@) nel calcolo dei due piani laterali, aggiunge alla
 * larghezza dello schermo (v0) i due margini dello schermo largo (psx_mod_widescreen_x_margin() per parte): i due
 * piani passano per i bordi della finestra larga. La proiezione e gli altri piani non cambiano, e a 4:3 (margine 0)
 * non cambia niente. Il contatore sm2.widescreen.planes conta i calcoli corretti (uno per frame).
 * Per i test: SM2_PIANI=originale lascia i piani del gioco. */
namespace {
int sm2_piani_spenti = -1;

void sm2_piani(CPUState* cpu, uint32_t) {
    if (sm2_piani_spenti < 0) {
        const char* p = std::getenv("SM2_PIANI");
        sm2_piani_spenti = (p && std::strcmp(p, "originale") == 0) ? 1 : 0;
    }
    const int32_t m = psx_mod_widescreen_x_margin();
    if (m <= 0 || sm2_piani_spenti) return;
    const int32_t w = int32_t(cpu->gpr[2]);
    if (w < 256 || w > 1024) return;
    cpu->gpr[2] = uint32_t(w + 2 * m);
    psx_mod_counter_add("sm2.widescreen.planes", 1);
}
}  // namespace
'''

PIANI_REGISTRA = '''    /* mod "Widescreen": piani laterali con cui il gioco scarta gli oggetti interi (launcher v0.11) */
    psx_mod_register_instruction_plugin(SM2Bordi::Plugin, @PianiX@u, 0x00029AC0u, sm2_piani);
'''

# Widescreen (launcher v0.9.1): quando si sta davvero giocando. Con gte_game_mode psxrecomp riconosceva il gioco
# dai vertici proiettati con la GTE, e allargava anche il giornale che gira dopo una missione fallita (disegnato in
# 3D, a 320): la pagina del giornale si rovinava (prove del 27/10 sera, tools\prova_giornale*.cmd). Lo decide
# invece questo codice, con lo stato del livello del gioco; nel game.toml gte_game_mode = false.
GIOCO_CODICE = r'''
/* Mod "Widescreen" (launcher v0.9.1): quando si sta davvero giocando. psxrecomp allarga l'immagine solo nei frame
 * «di gioco» (native-wide). Con gte_game_mode = true li riconosceva dai vertici proiettati con la GTE, ma cosi'
 * allargava anche il giornale che gira dopo una missione fallita (disegnato in 3D), e la pagina del giornale si
 * rovinava. Ora il game.toml ha gte_game_mode = false e lo dice questo plugin a psxrecomp
 * (psx_mod_set_world_scene_predicate): si gioca quando il ciclo del livello e' in corso (stato di uscita
 * @ExitState@ = 0; 3 = livello finito, 9 = missione fallita o ripartenza, 1 = menu), lo schermo e' largo 512
 * (giornale, caricamenti e filmati sono a 320) e la shell dei menu non e' caricata (lista dei moduli @ModHead@,
 * CRC del nome 0xBA6D4D02). Fino alla prima volta che compare la shell (loghi e filmati dell'avvio) non si gioca.
 * Calcolato una volta per frame (vblank del plugin sm2.widescreen, attivo solo con la mod accesa); il predicato si
 * ricollega a ogni vblank perche' psxrecomp lo azzera all'inizio di ogni sessione (main.cpp) e l'attivazione di
 * sm2.widescreen e' gia' di sm2_widescreen.c. Contatori: sm2.widescreen.play (inizi del gioco) e
 * sm2.widescreen.not_play (fine). */
namespace {
struct SM2Gioco {
    static constexpr uint32_t ExitState = @ExitState@u, ModHead = @ModHead@u, Shell = 0xBA6D4D02u;
};
bool sm2_gioco = false, sm2_shell_vista = false;

int sm2_gioco_scena(void);

void sm2_gioco_vblank(void) {
    psx_mod_set_world_scene_predicate(sm2_gioco_scena);
    bool shell = false;
    uint32_t nodo = psx_mod_read_word(SM2Gioco::ModHead);
    for (int i = 0; nodo && i < 40; ++i) {
        if (nodo < 0x80000000u || nodo >= 0x80200000u || (nodo & 3u)) break;
        if (psx_mod_read_word(nodo + 8) == SM2Gioco::Shell) {
            shell = true;
            break;
        }
        nodo = psx_mod_read_word(nodo + 60);
    }
    sm2_shell_vista = sm2_shell_vista || shell;
    const bool gioco = sm2_shell_vista && !shell && psx_mod_read_word(SM2Gioco::ExitState) == 0 &&
                       psx_mod_display_width() >= 512;
    if (gioco != sm2_gioco) {
        sm2_gioco = gioco;
        psx_mod_counter_add(gioco ? "sm2.widescreen.play" : "sm2.widescreen.not_play", 1);
    }
}

int sm2_gioco_scena(void) { return sm2_gioco ? 1 : 0; }
}  // namespace
'''

GIOCO_REGISTRA = '''    /* mod "Widescreen": si gioca solo nel ciclo del livello, a 512, senza la shell (gte_game_mode = false) */
    psx_mod_register_vblank_plugin(SM2Bordi::Plugin, sm2_gioco_vblank);
'''
INDIRIZZI = ROOT / 'aot' / 'sm2_indirizzi.json'


def stato_gioco(prof: str):
    """Widescreen (launcher v0.9.1): stato di uscita del livello e testa della lista dei moduli di questa versione
    (aot/sm2_indirizzi.json, EXIT_STATE e MOD_HEAD). Restituisce (indirizzi, '') o (None, motivo)."""
    try:
        voce = json.loads(INDIRIZZI.read_text(encoding='utf-8'))[prof]['indirizzi']
        r = {'ExitState': int(voce['EXIT_STATE']['valore'], 16), 'ModHead': int(voce['MOD_HEAD']['valore'], 16)}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return None, T(f'{INDIRIZZI.name} senza EXIT_STATE o MOD_HEAD per questa versione ({e})',
                       f'{INDIRIZZI.name} has no EXIT_STATE or MOD_HEAD for this version ({e})')
    if not all(0x800A0000 <= v < 0x80100000 and v % 4 == 0 for v in r.values()):
        return None, T('indirizzi fuori dalla zona dei dati del gioco', 'addresses outside the game data area')
    return r, ''


def imposta_gte(toml: Path, valore: bool) -> str:
    """Riga gte_game_mode della sezione [widescreen]: false se il plugin riconosce il gioco (v0.9.1), true
    altrimenti. Restituisce cosa ha cambiato ('' se niente)."""
    testo = toml.read_text(encoding='utf-8')
    voluto = f'gte_game_mode = {"true" if valore else "false"}'
    righe = testo.split('\n')
    idx = [i for i, r in enumerate(righe) if r.strip().startswith('gte_game_mode')]
    if not idx or righe[idx[0]].strip() == voluto:
        return ''
    i = idx[0]
    while i > 0 and righe[i - 1].startswith('#'):        # commento della riga (v0.7 o scritto a mano)
        i -= 1
    commento = (RIGA_GTE.rstrip('\n').split('\n')[:-1] if valore else
                ['# SM2-Recomp (launcher v0.9.1): quando si gioca lo dice il plugin del renderer (stato del livello),',
                 '# non i vertici della GTE: cosi\' il giornale che gira dopo una missione fallita resta in 4:3 e non',
                 '# si rovina.'])
    righe[i:idx[0] + 1] = commento + [voluto]
    toml.write_text('\n'.join(righe), encoding='utf-8')
    return T(f'game.toml: {voluto} nella sezione [widescreen]', f'game.toml: {voluto} in the [widescreen] section')


PLUGIN_DISTANZA_INIT = r'''/* SM2-Recomp - registrazione della mod "Distanza visiva" (sm2_draw_distance.cpp) prima di main(),
 * con lo stesso meccanismo delle mod incluse in psxrecomp. Scritto da tools/sm2_launcher.py. */
#include "mod_plugins.h"

void sm2_distanza_registra(void);

PSX_MOD_CONSTRUCTOR(sm2_distanza_costruttore) {
    sm2_distanza_registra();
}
'''

MANIFESTO_DISTANZA = '''format_version = 5
id = "sm2.enhancement.draw-distance"
version = "1.0.0"
name = "Draw distance"
author = "SM2-Recomp"
description = "Spider-Man 2: Enter Electro (@NOME@): the fog starts farther away@PIU_POLIGONI@, through psxrecomp's Neversoft renderer extension. Written for the game version of this installation."
resolver = "declarative"
save_compatibility = "shared"

[[target]]
game_id = "@GAME_ID@"

[[feature]]
id = "draw-distance"
name = "Extended draw distance"
description = "Disabled by default. The fog starts farther away, so more of the city is visible@PIU_POLIGONI_2@. Experimental."
group = "Visual"
default_enabled = false

[[feature]]
id = "subdivision-precision"
name = "PGXP: subdivided polygons"
description = "Disabled by default. With PGXP enabled, also corrects the polygons the game subdivides near the camera. No effect without PGXP."
group = "Visual"
default_enabled = false
@AREA_FEATURE@
[[plugin]]
feature = "draw-distance"
id = "sm2.draw-distance"

[[plugin]]
feature = "subdivision-precision"
id = "sm2.subdivision-precision"
@AREA_PLUGIN@'''

# Launcher v0.11: area dei pacchetti piu' grande anche con il solo widescreen (funzione nascosta del pacchetto della
# distanza visiva, accesa per la sessione dal [[requirement]] del widescreen; formato 7 dei pacchetti di psxrecomp).
AREA_FEATURE = '''
[[feature]]
id = "packet-area"
name = "Larger GPU packet area"
description = "Room for about four times as many polygons per frame. Turned on automatically by Extended draw distance and by Widescreen."
group = "Visual"
default_enabled = false
hidden = true
'''
AREA_PLUGIN = '''
[[plugin]]
feature = "packet-area"
id = "sm2.packet-area"
'''
REQUISITO_AREA = '''
# SM2-Recomp (launcher v0.11): con lo schermo largo il gioco disegna piu' poligoni; il widescreen accende per la
# sessione l'area dei pacchetti piu' grande del pacchetto della distanza visiva (funzione nascosta).
[[requirement]]
feature = "widescreen"
package = "sm2.enhancement.draw-distance"
requires_feature = "packet-area"
'''

# Punti di aggancio per la mod "Distanza visiva" nella sezione [recompiler] del game.toml, tra i segni.
INIZIO_DISTANZA = '# >>> SM2-Recomp: mod "Distanza visiva"'
FINE_DISTANZA = '# <<< SM2-Recomp: mod "Distanza visiva"'
BLOCCO_DISTANZA = INIZIO_DISTANZA + ''' (tools/sm2_launcher.py; senza la mod accesa il gioco non cambia)
# Funzioni: quella che imposta la nebbia e l'invio dei pacchetti alla GPU (per contare quanto si riempie
# l'area dei pacchetti)@NOTA_FUNZIONI_AREA@.
mod_function_entry_funcs = [@FUNZIONI@]
# Istruzioni: dopo la coordinata di schermo dei poligoni suddivisi (precisione PGXP)@NOTA_AREA@@NOTA_BORDI@@NOTA_PIANI@.
mod_instruction_sites = [@ISTRUZIONI@]
''' + FINE_DISTANZA + '\n'
NOTA_FUNZIONI_AREA = (';\n# per l\'area dei pacchetti piu\' grande (launcher v0.9) lo scambio dei due buffer e il calcolo del '
                      'limite')
NOTA_AREA = ('; per l\'area dei pacchetti piu\' grande\n# (launcher v0.9) i 3 punti che calcolano la lunghezza '
             'di un pacchetto')
NOTA_BORDI = ('; per la mod Widescreen\n# (launcher v0.8) i 4 punti in cui il renderer finisce di calcolare i bit "fuori schermo" '
              'dei vertici\n# e le 5 funzioni che confrontano X con i limiti dello schermo')
NOTA_PIANI = ('; dalla v0.11 anche il calcolo dei\n# due piani laterali con cui il gioco scarta gli oggetti interi '
              'prima di disegnarli')

# Istruzioni che l'estensione del renderer di psxrecomp controlla prima di agire: uguali in ogni versione.
CONTROLLI_RENDERER = (('LimitPc', 4, 0x34846F00), ('FogPc', 0, 0x00803821), ('PrecisionPc', 0, 0x4819B000),
                      ('PrecisionPc', -4, 0xACB00000), ('PacketT2', 0, 0x000A5582), ('PacketS2', 0, 0x00129582))
FUNZIONI_RENDERER = ('FogPc', 'SwapPc', 'LimitPc', 'SubmitPc')
CHIAVI_RENDERER = ('BufferA', 'Current', 'Cursor', 'Limit', 'AllocA', 'AllocB', 'Allocatore', 'FogPc', 'SwapPc',
                   'LimitPc', 'SubmitPc', 'PrecisionPc', 'PacketT2', 'PacketS2')
# Widescreen (facoltativi): i punti in cui il renderer finisce di calcolare i bit "fuori schermo" dei vertici,
# con le istruzioni del calcolo che li precedono (le stesse che cerca tools/mappa_renderer.py).
CHIAVI_BORDI = ('BordiA', 'BordiB', 'BordiC')
# e le 5 funzioni che confrontano X con i limiti dello schermo caricati all'inizio (s0 = destra, s1 =
# sinistra): punto su "ori s7,zero,0xFFFF" subito dopo il caricamento.
CHIAVI_LIMITI = ('Limiti1', 'Limiti2', 'Limiti3', 'Limiti4', 'Limiti5')
_X_FLAG = (0x014CC823, 0x032DC827, 0x014D5024, 0x01595025)   # subu t9,t2,t4; nor t9,t9,t5; and t2,t2,t5; or t2,t2,t9
CONTROLLI_BORDI = {
    'BordiA': ((0, 0x33190001), (-4, 0x01595025), (-8, 0x014F5024), (-12, 0x032FC827)),
    'BordiB': ((0, 0x33190001), (-4, 0x01595025), (-8, 0x014F5024), (-12, 0x032FC827)),
    'BordiC': ((0, 0xAC6A0000), (-4, 0x01595025), (-8, 0x01475024), (-12, 0x0327C827)),
    'PrecisionPc': ((-4, 0xACB00000), (-0x24, 0x02198025), (-0x28, 0x02158024), (-0x2C, 0x0335C827),
                    (-0x30, 0x0214C823)),
}
SCARTI_X_FLAG = {'BordiA': (-0x20,), 'BordiB': (-0x24,), 'BordiC': (-0x20,)}


def layout_renderer(prof: str, exe: bytes):
    """Indirizzi del renderer per la mod "Distanza visiva" (aot/sm2_renderer.json), controllati sulle
    istruzioni dell'eseguibile della versione. Restituisce (indirizzi, '') o (None, motivo)."""
    try:
        voce = json.loads(RENDERER.read_text(encoding='utf-8'))['versioni'].get(prof)
    except (OSError, ValueError, KeyError) as e:
        return None, T(f'{RENDERER.name} non leggibile ({e})', f'{RENDERER.name} cannot be read ({e})')
    if not voce:
        return None, T('indirizzi del renderer non ancora trovati per questa versione',
                       'renderer addresses not found yet for this version')
    try:
        lay = {k: int(voce[k], 16) for k in CHIAVI_RENDERER}
    except (KeyError, TypeError, ValueError) as e:
        return None, T(f'{RENDERER.name}: voce incompleta ({e})', f'{RENDERER.name}: incomplete entry ({e})')
    carica = struct.unpack_from('<I', exe, 0x18)[0]

    def parola(indirizzo: int):
        o = 0x800 + indirizzo - carica
        return struct.unpack_from('<I', exe, o)[0] if 0x800 <= o <= len(exe) - 4 else None
    jal = 0x0C000000 | ((lay['Allocatore'] >> 2) & 0x03FFFFFF)     # jal all'allocatore della memoria
    controlli = [('AllocA', 0, jal), ('AllocB', 0, jal)] + list(CONTROLLI_RENDERER) + \
                [(f, -8, 0x03E00008) for f in FUNZIONI_RENDERER]   # jr ra prima di ogni funzione agganciata
    for nome, scarto, atteso in controlli:
        if parola(lay[nome] + scarto) != atteso:
            return None, T(f'{nome}{scarto:+d} (0x{lay[nome] + scarto:08X}): istruzione diversa da quella attesa',
                           f'{nome}{scarto:+d} (0x{lay[nome] + scarto:08X}): instruction different from the expected one')
    lay['AllocWord'] = jal
    return lay, ''


def bordi_renderer(prof: str, exe: bytes, lay: dict):
    """Widescreen (facoltativo): i punti in cui il renderer finisce di calcolare i bit "fuori schermo" dei
    vertici (aot/sm2_renderer.json, BordiA/B/C), controllati sulle istruzioni dell'eseguibile. Restituisce
    (indirizzi, '') o (None, motivo)."""
    try:
        voce = json.loads(RENDERER.read_text(encoding='utf-8'))['versioni'].get(prof) or {}
        bordi = {k: int(voce[k], 16) for k in CHIAVI_BORDI}
    except (OSError, ValueError, KeyError, TypeError):
        return None, T(f'{RENDERER.name} senza i punti dei bordi per questa versione',
                       f'{RENDERER.name} has no edge sites for this version')
    carica = struct.unpack_from('<I', exe, 0x18)[0]

    def parola(indirizzo: int):
        o = 0x800 + indirizzo - carica
        return struct.unpack_from('<I', exe, o)[0] if 0x800 <= o <= len(exe) - 4 else None
    tutti = dict(bordi, PrecisionPc=lay['PrecisionPc'])
    sbagliati = [f'{k}{s:+#x}' for k, cc in CONTROLLI_BORDI.items() for s, w in cc if parola(tutti[k] + s) != w]
    sbagliati += [f'{k} (calcolo del bit a destra)' for k, ss in SCARTI_X_FLAG.items()
                  if not any(all(parola(tutti[k] + s + 4 * i) == _X_FLAG[i] for i in range(4)) for s in ss)]
    if sbagliati:
        return None, T('istruzioni diverse da quelle attese in ', 'instructions different from the expected ones at ') + ', '.join(sbagliati)
    try:
        limiti = {k: int(voce[k], 16) for k in CHIAVI_LIMITI}
    except (KeyError, TypeError, ValueError):
        return None, T(f'{RENDERER.name} senza le funzioni dei limiti dello schermo per questa versione',
                       f'{RENDERER.name} has no screen limit functions for this version')
    sbagliati = [k for k, a in limiti.items() if not limiti_ok(parola, a)]
    if sbagliati or len(set(limiti.values())) != len(limiti):
        return None, T('istruzioni diverse da quelle attese in ', 'instructions different from the expected ones at ') + (
            ', '.join(sbagliati) or T('limiti ripetuti', 'repeated limits'))
    return dict(bordi, **limiti), ''


def limiti_ok(w, a: int) -> bool:
    """Punto della seconda famiglia (lo stesso controllo di tools/mappa_renderer.py): "ori s7,zero,0xFFFF" subito
    dopo "lw s0,0(base); lw s1,4(base)" e "andi s0/s1,0xFFFF", e piu' avanti "slt t0,s0,t7; slt t7,t7,s1"."""
    if w(a) != 0x3417FFFF:
        return False
    prima = [w(a - 4 * i) for i in range(1, 11)]
    if 0x3210FFFF not in prima[:6] or 0x3231FFFF not in prima[:4]:
        return False
    if not ((0x8EB00000 in prima and 0x8EB10004 in prima) or (0x8E900000 in prima and 0x8E910004 in prima)):
        return False
    dopo = [w(a + 4 * i) for i in range(1, 129)]
    return any(dopo[i] == 0x020F402A and dopo[i + 1] == 0x01F1782A for i in range(len(dopo) - 1))


def collegamento_renderer(prof: str, exe: bytes):
    """Area dei pacchetti piu' grande (facoltativa, launcher v0.9): il punto PacketLink di aot/sm2_renderer.json,
    dove il gioco calcola la lunghezza di un pacchetto dalla parola con il collegamento al pacchetto precedente,
    controllato sulle istruzioni dell'eseguibile. Restituisce (indirizzo, '') o (None, motivo)."""
    try:
        voce = json.loads(RENDERER.read_text(encoding='utf-8'))['versioni'].get(prof) or {}
        a = int(voce['PacketLink'], 16)
    except (OSError, ValueError, KeyError, TypeError):
        return None, T(f'{RENDERER.name} senza il punto PacketLink per questa versione',
                       f'{RENDERER.name} has no PacketLink site for this version')
    carica = struct.unpack_from('<I', exe, 0x18)[0]

    def parola(indirizzo: int):
        o = 0x800 + indirizzo - carica
        return struct.unpack_from('<I', exe, o)[0] if 0x800 <= o <= len(exe) - 4 else None
    k = len(COLLEGAMENTO)
    if [parola(a - 4 * (k - 1 - i)) for i in range(k)] != list(COLLEGAMENTO):
        return None, T(f'PacketLink (0x{a:08X}): istruzioni diverse da quelle attese',
                       f'PacketLink (0x{a:08X}): instructions different from the expected ones')
    return a, ''


# Widescreen (launcher v0.11): il punto in cui il gioco calcola i due piani laterali con cui scarta gli oggetti interi
# (PianiX in aot/sm2_renderer.json): "sll s3,v0,11", con v0 = larghezza dello schermo (destra - sinistra) appena
# calcolata da "lhu v0,0(s4)", "lhu a0|v1,4(s4)" e "subu v0,v0,a0|v1"; poco dopo i due piani vengono salvati a +0x20 e
# +0x28 della tabella dei piani (s0). Lo stesso controllo di tools/mappa_renderer.py.
PIANI_PUNTO = 0x00029AC0         # sll s3,v0,11


def piani_ok(w, a: int) -> bool:
    """Punto PianiX; w(indirizzo) legge una parola dell'eseguibile (None fuori dal file)."""
    def p(x):
        v = w(x)
        return v if v is not None else 0
    if p(a) != PIANI_PUNTO:
        return False
    prima = [p(a - 4 * i) for i in range(1, 9)]
    if 0x96820000 not in prima or not ({0x96840004, 0x96830004} & set(prima)):   # lhu v0,0(s4); lhu a0|v1,4(s4)
        return False
    if not ({0x00441023, 0x00431023} & set(prima[:3])):                           # subu v0,v0,a0|v1
        return False
    salvati = {p(a + 4 * i) & 0xFFFF for i in range(1, 41) if (p(a + 4 * i) & 0xFFE00000) == 0xA6000000}
    return {0x20, 0x28} <= salvati and not (salvati & {0x10, 0x12, 0x14, 0x18, 0x1A, 0x1C})   # sh ...,(s0)


def piani_renderer(prof: str, exe: bytes):
    """Widescreen (facoltativo, launcher v0.11): il punto PianiX di aot/sm2_renderer.json, dove il gioco calcola i
    due piani laterali con cui scarta gli oggetti interi, controllato sulle istruzioni dell'eseguibile. Restituisce
    (indirizzo, '') o (None, motivo)."""
    try:
        voce = json.loads(RENDERER.read_text(encoding='utf-8'))['versioni'].get(prof) or {}
        a = int(voce['PianiX'], 16)
    except (OSError, ValueError, KeyError, TypeError):
        return None, T(f'{RENDERER.name} senza il punto PianiX per questa versione',
                       f'{RENDERER.name} has no PianiX site for this version')
    carica = struct.unpack_from('<I', exe, 0x18)[0]

    def parola(indirizzo: int):
        o = 0x800 + indirizzo - carica
        return struct.unpack_from('<I', exe, o)[0] if 0x800 <= o <= len(exe) - 4 else None
    if not piani_ok(parola, a):
        return None, T(f'PianiX (0x{a:08X}): istruzioni diverse da quelle attese',
                       f'PianiX (0x{a:08X}): instructions different from the expected ones')
    return a, ''


GAME_OPTIONS = '''# Native in-game OPTION persistence (optional).
# Declared next to game.toml; read by the recompiler (init-store hooks) and
# runtime (restore / save). Omit [[option]] rows until the title needs them.
# See psxrecomp GameOptions / runtime game_options.c.
'''


def giunzione(link: Path, target: Path) -> bool:
    if link.exists() or link.is_symlink():
        ok = link.resolve() == target.resolve()
        log(T(f'  {link.name}: gia\' presente', f'  {link.name}: already there') +
            ('' if ok else T(f' MA punta a {link.resolve()}', f' BUT it points to {link.resolve()}')))
        return ok
    if os.name == 'nt':
        r = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)], capture_output=True, text=True)
        log(T(f'  giunzione {link.name} -> {target}: codice {r.returncode} {r.stdout.strip()} {r.stderr.strip()}',
              f'  junction {link.name} -> {target}: code {r.returncode} {r.stdout.strip()} {r.stderr.strip()}'))
        return r.returncode == 0
    link.symlink_to(target, target_is_directory=True)
    log(T(f'  collegamento {link.name} -> {target}', f'  link {link.name} -> {target}'))
    return True


def scrivi_se_diverso(path: Path, testo: str) -> bool:
    if path.is_file() and path.read_text(encoding='utf-8') == testo:
        return False
    path.write_text(testo, encoding='utf-8', newline='\n')
    return True


def leggi_toml(path: Path) -> dict:
    import tomllib
    return tomllib.loads(path.read_text(encoding='utf-8'))


# ------------------------------------------------------------------------------ salto delle attese (launcher v0.10)

# v_wait di PsyQ libetc, l'attesa della sincronia verticale (VSync(0)/VSync(n)): parola per parola da v_wait a
# v_wait+0x90, con mascherate le parti che cambiano da una versione all'altra (indirizzi e chiamate). Il codice e' lo
# stesso in tutte e 7 le versioni e nel gioco di riferimento di psxrecomp (R4, docs/config_schema.md, "Developer
# contract for idle_skip_store_counters"): a v_wait+0x28 toglie 1 al contatore del timeout in 16(sp) e, se arriva
# a -1, scrive "VSync: timeout" e salta all'uscita; a v_wait+0x70 rilegge il numero di vblank e torna su; a
# v_wait+0x88 esce. L'unica uscita che dipende dal contatore e' quella del timeout, e psxrecomp non porta mai il
# contatore sotto 2: quel controllo gira sempre davvero.
V_WAIT_SCHEMA = (
    (0x27BDFFE0, 0xFFFFFFFF), (0x00052BC0, 0xFFFFFFFF), (0xAFA50010, 0xFFFFFFFF), (0x3C020000, 0xFFFF0000),
    (0x8C420000, 0xFFFF0000), (0x00000000, 0xFFFFFFFF), (0x0044102A, 0xFFFFFFFF), (0x1040001A, 0xFFFFFFFF),
    (0xAFBF0018, 0xFFFFFFFF), (0x2403FFFF, 0xFFFFFFFF), (0x8FA20010, 0xFFFFFFFF), (0x00000000, 0xFFFFFFFF),
    (0x2442FFFF, 0xFFFFFFFF), (0xAFA20010, 0xFFFFFFFF), (0x8FA20010, 0xFFFFFFFF), (0x00000000, 0xFFFFFFFF),
    (0x1443000B, 0xFFFFFFFF), (0x00000000, 0xFFFFFFFF), (0x3C040000, 0xFFFF0000), (0x0C000000, 0xFC000000),
    (0x24840000, 0xFFFF0000), (0x0C000000, 0xFC000000), (0x00002021, 0xFFFFFFFF), (0x24040003, 0xFFFFFFFF),
    (0x0C000000, 0xFC000000), (0x00002821, 0xFFFFFFFF), (0x08000000, 0xFC000000), (0x00000000, 0xFFFFFFFF),
    (0x3C020000, 0xFFFF0000), (0x8C420000, 0xFFFF0000), (0x00000000, 0xFFFFFFFF), (0x0044102A, 0xFFFFFFFF),
    (0x1440FFE9, 0xFFFFFFFF), (0x00000000, 0xFFFFFFFF), (0x8FBF0018, 0xFFFFFFFF), (0x27BD0020, 0xFFFFFFFF),
    (0x03E00008, 0xFFFFFFFF))
INIZIO_ATTESE = '# >>> SM2-Recomp: salto delle attese'
FINE_ATTESE = '# <<< SM2-Recomp: salto delle attese'
# Le due correzioni di psxrecomp del 28/10/2026 (runtime/src/psx_cycles.c), riconosciute dai loro commenti:
#  1) la distanza dal prossimo evento dei dispositivi si misura da adesso per ogni ciclo di attesa (senza, il VBlank
#     del frame 589 di USA Rev 1 arrivava 456 cicli in ritardo);
#  2) il limite del registro che conta alla rovescia si legge con il segno (senza, un'attesa breve del Giappone che
#     esce sotto lo zero, al frame 285, durava fino al VBlank).
# Senza tutte e due il gioco non fa piu' esattamente le stesse cose con il salto delle attese.
SEGNI_CORREZIONE = ('Measure from now, for every loop shape', 'Signed, like the counter word below')


def trova_v_wait(exe: bytes):
    """(indirizzo, '') di v_wait nell'eseguibile PS-X EXE, controllato istruzione per istruzione, oppure (None, motivo)."""
    if len(exe) < 0x800 or exe[:8] != b'PS-X EXE':
        return None, T('non e\' un eseguibile PS-X', 'not a PS-X executable')
    base = struct.unpack_from('<I', exe, 0x18)[0]
    testo = exe[0x800:]
    testa = struct.pack('<3I', *(v for v, _ in V_WAIT_SCHEMA[:3]))
    lung = 4 * len(V_WAIT_SCHEMA)
    trovati = []
    i = testo.find(testa)
    while i != -1:
        if i % 4 == 0 and i + lung <= len(testo):
            parole = struct.unpack_from(f'<{len(V_WAIT_SCHEMA)}I', testo, i)
            if all((w & m) == v for w, (v, m) in zip(parole, V_WAIT_SCHEMA)):
                trovati.append((i, parole))
        i = testo.find(testa, i + 4)
    if len(trovati) != 1:
        return None, T(f'{len(trovati)} copie di v_wait invece di 1', f'{len(trovati)} copies of v_wait instead of 1')
    i, w = trovati[0]
    a = base + i

    def s16(x):
        return x - 0x10000 if x & 0x8000 else x
    conta1 = ((w[3] & 0xFFFF) << 16) + s16(w[4] & 0xFFFF)
    conta2 = ((w[28] & 0xFFFF) << 16) + s16(w[29] & 0xFFFF)
    salto = ((a + 0x6C) & 0xF0000000) | ((w[26] & 0x03FFFFFF) << 2)
    scritta = ((w[18] & 0xFFFF) << 16) + s16(w[20] & 0xFFFF) - base
    if conta1 != conta2:
        return None, T('v_wait legge due contatori di vblank diversi', 'v_wait reads two different vblank counters')
    if salto != a + 0x88:
        return None, T('il timeout di v_wait non salta all\'uscita', 'the v_wait timeout does not jump to the exit')
    if not 0 <= scritta < len(testo) - 14 or testo[scritta:scritta + 14] != b'VSync: timeout':
        return None, T('la scritta del timeout di v_wait non e\' quella attesa', 'the v_wait timeout text is not the expected one')
    return a, ''


def attese_corrette() -> bool:
    """La copia di psxrecomp ha le due correzioni di runtime/src/psx_cycles.c del 28/10/2026?"""
    try:
        testo = (ROOT / 'psxrecomp' / 'runtime' / 'src' / 'psx_cycles.c').read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    return all(s in testo for s in SEGNI_CORREZIONE)


def blocco_attese(v_wait: int) -> str:
    return (INIZIO_ATTESE + ' (tools/sm2_launcher.py, launcher v0.10; opzioni --attese si|no)\n'
            '# psxrecomp salta i giri a vuoto dei cicli di attesa (idle_skip) e, nei due punti qui sotto, quelli di\n'
            f'# v_wait di PsyQ (l\'attesa della sincronia verticale, a 0x{v_wait:08X}, controllata dal launcher nell\'eseguibile).\n'
            '# Con le correzioni di psxrecomp/runtime/src/psx_cycles.c del 28/10/2026 il gioco fa esattamente le stesse\n'
            '# cose che senza: cambia solo il lavoro della CPU.\n'
            'idle_skip = true\n'
            'idle_skip_store_counters = true\n'
            f'idle_skip_store_counter_sites = ["0x{v_wait + 0x28:08X}", "0x{v_wait + 0x70:08X}"]\n'
            + FINE_ATTESE + '\n')


def strumenti_vulkan():
    """(intestazioni, compilatore degli shader) in tools\\vulkan, oppure None se non ci sono."""
    sdk, glslc = VULKAN / 'Vulkan-Headers', VULKAN / 'glslc.cmd'
    if (sdk / 'include' / 'vulkan' / 'vulkan.h').is_file() and glslc.is_file():
        return sdk, glslc
    return None


def imposta_chiave_toml(path: Path, sezione: str, chiave: str, valore) -> str:
    """Scrive chiave = valore nella sezione [sezione] di un file TOML (la crea se manca), lasciando il resto com'e'.
    Restituisce cosa ha cambiato ('' se niente)."""
    testo = path.read_text(encoding='utf-8') if path.is_file() else ''
    righe = testo.splitlines()
    v = ('true' if valore else 'false') if isinstance(valore, bool) else (str(valore) if isinstance(valore, int)
                                                                          else _q(valore))
    riga_nuova = f'{chiave} = {v}'
    inizio = next((i for i, r in enumerate(righe) if r.strip() == f'[{sezione}]'), None)
    if inizio is None:
        if righe and righe[-1].strip():
            righe.append('')
        righe += [f'[{sezione}]', riga_nuova]
    else:
        fine = next((i for i in range(inizio + 1, len(righe)) if righe[i].strip().startswith('[')), len(righe))
        pat = re.compile(r'^\s*' + re.escape(chiave) + r'\s*=')
        idx = next((i for i in range(inizio + 1, fine) if pat.match(righe[i])), None)
        if idx is not None and righe[idx].strip() == riga_nuova:
            return ''
        if idx is None:
            dove = max((i for i in range(inizio, fine) if righe[i].strip()), default=inizio) + 1
            righe.insert(dove, riga_nuova)
        else:
            righe[idx] = riga_nuova
    path.write_text('\n'.join(righe) + '\n', encoding='utf-8')
    return f'{path.name}: [{sezione}] {riga_nuova}'


def imposta_attese(toml: Path, v_wait) -> str:
    """Salto delle attese nella sezione [runtime] del game.toml: lo scrive (v_wait = indirizzo) o lo toglie (None).
    Il gioco legge il game.toml all'avvio, quindi non serve ricompilare. Restituisce cosa ha cambiato ('' se niente)."""
    testo = toml.read_text(encoding='utf-8')
    senza = re.sub(re.escape(INIZIO_ATTESE) + r'.*?' + re.escape(FINE_ATTESE) + r'\n?', '', testo, flags=re.S)
    if v_wait is None:
        if senza == testo:
            return ''
        toml.write_text(senza, encoding='utf-8')
        return T('game.toml: salto delle attese tolto', 'game.toml: idle skip removed')
    if re.search(r'(?m)^\s*idle_skip', senza):
        return T('avviso: nel game.toml ci sono gia\' chiavi idle_skip scritte a mano: salto delle attese non scritto',
                 'warning: game.toml already has idle_skip keys written by hand: idle skip not written')
    nuovo, n = re.subn(r'(?m)^\[runtime\][ \t]*\n', lambda m: m.group(0) + blocco_attese(v_wait), senza, count=1)
    if n != 1:
        return T('avviso: sezione [runtime] non trovata nel game.toml: salto delle attese non scritto',
                 'warning: no [runtime] section in game.toml: idle skip not written')
    if nuovo == testo:
        return ''
    toml.write_text(nuovo, encoding='utf-8')
    return T(f'game.toml: salto delle attese acceso (idle_skip con i contatori di v_wait a 0x{v_wait:08X})',
             f'game.toml: idle skip on (idle_skip with the v_wait counters at 0x{v_wait:08X})')


def attese_accese(toml: Path) -> bool:
    try:
        return INIZIO_ATTESE in toml.read_text(encoding='utf-8')
    except OSError:
        return False


# ------------------------------------------------------------------------------------------------- PGO (v0.10)

PGO_PORTA = 4390
PGO_TASTI = {'NONE': 0xFFFF, 'START': 0xFFF7, 'CROSS': 0xBFFF, 'CIRCLE': 0xDFFF, 'TRIANGLE': 0xEFFF,
             'SQUARE': 0x7FFF, 'UP': 0xFFEF, 'DOWN': 0xFFBF, 'LEFT': 0xFF7F, 'RIGHT': 0xFFDF}
PGO_MOSSE = ('UP', 'UP', 'RIGHT', 'SQUARE', 'UP', 'LEFT', 'CROSS', 'DOWN', 'SQUARE', 'RIGHT', 'UP', 'CIRCLE')


def tasti_allenamento(prof: str):
    """Tasti (frame, tasto) della partita di allenamento del PGO e il frame a cui finisce: fino al primo livello con
    gli stessi tasti dei test (la versione giapponese conferma con il cerchio), poi Spider-Man che si muove, salta e
    colpisce. Circa 3 minuti di gioco (PAL: 50 frame al secondo)."""
    if prof.startswith('SLUS'):
        tasti = [(3700, 'START'), (3800, 'START')] + [(f, 'CROSS') for f in range(4100, 5601, 150)]
        da, a, fine = 6100, 10400, 10800
    else:
        conferma = 'CIRCLE' if prof.startswith('SLPM') else 'CROSS'
        tasti = [(f, 'START') for f in range(2400, 3901, 150)] + [(f, conferma) for f in range(2475, 7101, 150)]
        da, a, fine = 7200, 8800, (10800 if prof.startswith('SLPM') else 9000)
    tasti += [(f, PGO_MOSSE[(f // 120) % len(PGO_MOSSE)]) for f in range(da, a, 10)]
    return sorted(tasti), fine


def percorso_tasti(tasti: list, inizio: int, tieni: int = 8) -> list:
    """Passi (frame, tasti premuti) per input_route_append del server di debug, dal frame inizio."""
    passi, cur = [], inizio
    for f, b in tasti:
        if f < cur:
            raise ValueError(T(f'tasto al frame {f} troppo vicino al precedente o all\'inizio ({cur})',
                               f'button at frame {f} too close to the previous one or to the start ({cur})'))
        if f > cur:
            passi.append((f - cur, PGO_TASTI['NONE']))
        passi.append((tieni, PGO_TASTI[b]))
        cur = f + tieni
    passi.append((30, PGO_TASTI['NONE']))
    return passi


def allena_pgo(prof: str, exe: Path, toml: Path, cue: Path, pgo_dir: Path, max_secs: int = 1800) -> dict:
    """Partita di allenamento del PGO con l'eseguibile strumentato: finestra nascosta, audio finto, tasti a frame
    esatti dal server di debug fino all'ultimo frame, poi chiusura dal server di debug (cosi' l'eseguibile scrive i
    conteggi in pgo_dir). Restituisce {'ok': bool, 'errore', 'conteggi', 'secondi', ...}."""
    sys.path.insert(0, str(ROOT / 'psxrecomp' / 'tools'))
    import debug_client  # noqa: E402  (client del server di debug di psxrecomp)
    exe, toml, cue, pgo_dir = Path(exe).resolve(), Path(toml).resolve(), Path(cue).resolve(), Path(pgo_dir).resolve()
    pgo_dir.mkdir(parents=True, exist_ok=True)
    for f in pgo_dir.glob('*.profraw'):
        f.unlink()
    tasti, fine = tasti_allenamento(prof)
    env = dict(os.environ, LLVM_PROFILE_FILE=str(pgo_dir / 'sm2-%p.profraw'), SDL_AUDIODRIVER='dummy',
               SDL_AUDIO_DRIVER='dummy', PSX_OVERLAY_AUTOCOMPILE_OFF='1', PSX_DISPLAY_RING='0', PSX_DEBUG_TOGGLES='0')
    cmd = [str(exe), '--no-launcher', '--game', str(toml), '--disc', str(cue), '--debug-port', str(PGO_PORTA),
           '--hidden-window']
    conta = [0]

    def chiama(comando, timeout=10.0, **kw):
        conta[0] += 1
        try:
            return debug_client.query('127.0.0.1', PGO_PORTA, {'id': conta[0], 'cmd': comando, **kw}, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return {'error': f'{type(e).__name__}: {e}'}

    def frame():
        r = chiama('frame')
        f = r.get('frame') if isinstance(r, dict) else None
        return f if isinstance(f, int) else None

    ris = {'ok': False, 'frame_fine': fine}
    uscita = open(pgo_dir / 'allenamento_output.txt', 'w', encoding='utf-8', errors='replace')
    proc = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=uscita, stderr=subprocess.STDOUT)
    t0 = time.time()
    try:
        while time.time() - t0 < 120:
            r = chiama('ping', timeout=3)
            if isinstance(r, dict) and r.get('ok'):
                break
            if proc.poll() is not None:
                ris['errore'] = T(f'il gioco si e\' chiuso subito (codice {proc.returncode})',
                                  f'the game closed at once (code {proc.returncode})')
                return ris
            time.sleep(1)
        else:
            ris['errore'] = T('server di debug non raggiungibile', 'debug server not reachable')
            return ris
        f_ora = frame() or 0
        if f_ora + 60 >= tasti[0][0]:
            ris['errore'] = T(f'il gioco era gia\' al frame {f_ora}', f'the game was already at frame {f_ora}')
            return ris
        inizio = max(f_ora + 60 + 3 * len(percorso_tasti(tasti, max(f_ora, 120))), 120)
        if inizio >= tasti[0][0]:
            ris['errore'] = T(f'il gioco era gia\' al frame {f_ora}', f'the game was already at frame {f_ora}')
            return ris
        passi = percorso_tasti(tasti, inizio)
        chiama('input_route_clear')
        errori = [r for r in (chiama('input_route_append', frames=k, buttons=b) for k, b in passi)
                  if not (isinstance(r, dict) and r.get('ok'))]
        r = chiama('input_route_start', at_frame=inizio)
        if errori or not (isinstance(r, dict) and r.get('ok')):
            ris['errore'] = T('tasti non programmati', 'buttons not scheduled')
            return ris
        avviso = time.time()
        while True:
            if proc.poll() is not None:
                ris['errore'] = T(f'il gioco si e\' chiuso da solo (codice {proc.returncode})',
                                  f'the game closed by itself (code {proc.returncode})')
                return ris
            f = frame()
            if f is not None and f >= fine:
                break
            if time.time() - t0 > max_secs:
                ris['errore'] = T(f'troppo lento: frame {f} dopo {max_secs} s', f'too slow: frame {f} after {max_secs} s')
                return ris
            if time.time() - avviso >= 60:
                log(T(f'  allenamento: frame {f} di {fine}', f'  training: frame {f} of {fine}'))
                avviso = time.time()
            time.sleep(0.5)
        ris['ok'] = True
        return ris
    finally:
        chiama('quit', timeout=5)
        for _ in range(300):                 # l'eseguibile strumentato scrive i conteggi mentre si chiude
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        if proc.poll() is None:
            proc.kill()
            ris['ok'] = False
            ris['errore'] = ris.get('errore') or T('il gioco non si e\' chiuso', 'the game did not close')
        uscita.close()
        raws = sorted(pgo_dir.glob('*.profraw'))
        ris['conteggi'] = [f'{x.name} {x.stat().st_size // 1024} KB' for x in raws]
        ris['secondi'] = round(time.time() - t0)
        if not raws:
            ris['ok'] = False
            ris['errore'] = ris.get('errore') or T('nessun file di conteggi scritto', 'no profile count file written')


def unisci_pgo(pgo_dir: Path, dest: Path):
    """llvm-profdata merge dei conteggi dell'allenamento in dest; restituisce dest o None."""
    raws = sorted(pgo_dir.glob('*.profraw'))
    cand = TOOLCHAIN / 'bin' / 'llvm-profdata.exe'
    prog = shutil.which('llvm-profdata') or (str(cand) if cand.is_file() else None)
    if not raws or not prog:
        log(T(f'  ERRORE: conteggi {len(raws)}, llvm-profdata {"trovato" if prog else "non trovato"}',
              f'  ERROR: count files {len(raws)}, llvm-profdata {"found" if prog else "not found"}'))
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([prog, 'merge', '-sparse', *[str(x) for x in raws], '-o', str(dest)],
                       capture_output=True, text=True, errors='replace')
    if r.returncode != 0 or not dest.is_file():
        log(T(f'  ERRORE: llvm-profdata (codice {r.returncode}): {r.stderr.strip()[-600:]}',
              f'  ERROR: llvm-profdata (code {r.returncode}): {r.stderr.strip()[-600:]}'))
        return None
    dove = dest.relative_to(dest.parents[1]) if len(dest.parents) > 1 else dest
    log(T(f'  conteggi uniti in {dove} ({dest.stat().st_size // 1024} KB)',
          f'  counts merged into {dove} ({dest.stat().st_size // 1024} KB)'))
    return dest


class Installazione:
    def __init__(self, prof: str, cartella: Path, disco: dict, cat: dict, pgxp: bool = False,
                 registratore: bool = False):
        self.prof, self.cartella, self.disco, self.v = prof, cartella, disco, cat[prof]
        self.pgxp = pgxp
        self.registratore = registratore
        self.cue = Path(disco['foglio'])
        self.exe = self.v['exe']
        self.stato_path = cartella / 'installazione.json'
        try:
            self.stato = json.loads(self.stato_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            self.stato = {}

    def salva(self, **kw) -> None:
        self.stato.update(kw)
        self.stato_path.write_text(json.dumps(self.stato, indent=1, ensure_ascii=False), encoding='utf-8')

    def cli(self, argomenti: list, uscita: Path) -> bool:
        env = None
        vk = strumenti_vulkan() if argomenti and argomenti[0] == 'rebuild' else None
        if vk:       # motore grafico Vulkan (sperimentale): intestazioni e compilatore degli shader di tools\vulkan
            env = dict(os.environ, VULKAN_SDK=str(vk[0]))
            # PSX_PYTHON: lo stesso Python del launcher per tools\\embed_spirv.py (CMake altrimenti cerca py/python nel PATH)
            argomenti = list(argomenti) + [f'--cmake-extra=-DGLSLC_EXE={vk[1]}',
                                           f'--cmake-extra=-DPSX_PYTHON={sys.executable}']
        cmd = [sys.executable, str(self.cartella / 'psxrecomp' / 'psxrecomp_cli.py')] + argomenti
        log('  ' + ' '.join(cmd))
        with open(uscita, 'a', encoding='utf-8', errors='replace') as out:
            out.write(f'\n== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} {argomenti[0]}\n')
            out.flush()
            r = subprocess.run(cmd, cwd=str(self.cartella), stdout=out, stderr=subprocess.STDOUT, env=env)
        log(T(f'  -> codice di uscita {r.returncode} (dettagli in {uscita.name})',
              f'  -> exit code {r.returncode} (details in {uscita.name})'))
        return r.returncode == 0

    # -- passi

    def prepara(self) -> bool:
        base = self.cartella
        base.mkdir(parents=True, exist_ok=True)
        log(T(f'[prepara] {base}', f'[prepare] {base}'))
        for g in GIUNZIONI:
            if not giunzione(base / g, ROOT / g):
                log(T(f'ERRORE: collegamento a {g} non riuscito', f'ERROR: link to {g} failed'))
                return False
        titolo = f'Spider-Man 2: Enter Electro ({nome_versione(self.prof, self.v["nome"]).split(" (")[0]})'
        pgxp = ('    # PGXP: eseguibile con i punti di aggancio per la precisione della geometria (mod PGXP\n'
                '    # Precision di psxrecomp, da accendere quando si gioca); scelto con installa --pgxp.\n'
                '    PGXP\n') if self.pgxp else ''
        testo = (CMAKELISTS.replace('@NOME@', self.v['nome']).replace('@PROFILO@', self.prof)
                 .replace('@TITOLO@', titolo).replace('@EXE_BASE@', EXE_BASE).replace('@EXE@', self.exe)
                 .replace('@PGXP@', pgxp))
        if self.registratore:
            testo += CMAKE_REGISTRATORE.replace('@PROFILO@', self.prof)
        scrivi_se_diverso(base / 'CMakeLists.txt', testo)
        diag = base / 'mods' / 'preloaded' / 'packages' / 'sm2.diagnostics'
        if self.registratore:
            (diag / '1.0.0').mkdir(parents=True, exist_ok=True)
            scrivi_se_diverso(diag / '1.0.0' / 'manifest.toml', MANIFESTO_DIAGNOSTICA)
            log(T('  registratore delle partite (QA): acceso in questa installazione di prova, sessioni in '
                  'saves\\diagnostics\\ accanto all\'eseguibile',
                  '  game recorder (QA): on in this test installation, sessions in saves\\diagnostics\\ next to '
                  'the executable'))
        elif (diag / '1.0.0' / 'manifest.toml').is_file():
            shutil.rmtree(diag)                 # scritto da un'installazione con --registratore: qui non serve
            log(T('  registratore delle partite (QA): tolto da questa installazione',
                  '  game recorder (QA): removed from this installation'))
        if not (base / 'game_options.toml').is_file():
            sorgente = ROOT / 'game_options.toml'
            (base / 'game_options.toml').write_text(
                sorgente.read_text(encoding='utf-8') if sorgente.is_file() else GAME_OPTIONS, encoding='utf-8')
        # game.toml, catalog_identity.json, seeds/ e disc/<exe> da probe_disc, sul disco dell'utente
        toml = base / 'game.toml'
        rifai = True
        if toml.is_file():
            try:
                g = leggi_toml(toml)
                disco = Path(g['game']['disc'])
                disco = disco if disco.is_absolute() else (base / disco)
                noti = set(g.get('prepare_disc', {}).get('known_sha1', []))
                rifai = not (disco.resolve() == self.cue.resolve() and
                             noti & {self.disco['dati_sha1'], self.disco.get('traccia1_sha1')} and
                             (base / 'disc' / self.exe).is_file())
            except (OSError, ValueError, KeyError):
                rifai = True
        if rifai:
            disc_rel = os.path.relpath(self.cue, base).replace('\\', '/')
            cmd = [sys.executable, str(base / 'psxrecomp' / 'tools' / 'new_project_layout' / 'probe_disc.py'),
                   str(self.cue), '--write-game-toml', 'game.toml', '--write-catalog', 'catalog_identity.json',
                   '--write-seeds', 'seeds/ghidra_funcs.txt', '--disc-rel', disc_rel, '--out-dir', 'disc',
                   '--players', '1', '--display-name', 'Spider-Man 2: Enter Electro', '--write-boot-exe', 'disc']
            log(T('  probe_disc sul disco dell\'utente:', '  probe_disc on the user\'s disc:'), self.cue.name)
            r = subprocess.run(cmd, cwd=str(base), capture_output=True, text=True, errors='replace')
            (base / 'probe_disc_output.txt').write_text(r.stdout + '\n' + r.stderr, encoding='utf-8')
            if r.returncode != 0 or not toml.is_file():
                log(r.stderr.strip()[-2000:])
                log(T(f'ERRORE: probe_disc ha restituito {r.returncode}', f'ERROR: probe_disc returned {r.returncode}'))
                return False
        else:
            log(T('  game.toml gia\' scritto per questo disco: probe_disc saltato',
                  '  game.toml already written for this disc: probe_disc skipped'))
        # mod "Widescreen" (spenta di default): plugin, pacchetto e chiavi dell'HUD nel game.toml
        (base / 'mods_src').mkdir(exist_ok=True)
        scrivi_se_diverso(base / 'mods_src' / 'sm2_widescreen.c', PLUGIN_WIDESCREEN)
        scrivi_se_diverso(base / 'mods_src' / 'sm2_gpu_preferita.c', GPU_PREFERITA)
        pacchetto = base / 'mods' / 'preloaded' / 'packages' / 'sm2.enhancement.widescreen' / '1.0.0'
        pacchetto.mkdir(parents=True, exist_ok=True)
        scrivi_se_diverso(pacchetto / 'manifest.toml', MANIFESTO_WIDESCREEN)
        cambiato = aggiorna_toml_widescreen(toml)
        if cambiato:
            log('  ' + cambiato)
        boot = base / 'disc' / self.exe
        if not boot.is_file():
            log(T(f'ERRORE: manca disc/{self.exe} (probe_disc)', f'ERROR: disc/{self.exe} is missing (probe_disc)'))
            return False
        dati = boot.read_bytes()
        if hashlib.sha1(dati).hexdigest() != self.v['exe_sha1']:
            log(T('ERRORE: l\'eseguibile estratto non e\' quello della versione riconosciuta',
                  'ERROR: the extracted executable is not the one of the recognized version'))
            return False
        entry = struct.unpack_from('<I', dati, 0x10)[0]
        scrivi_se_diverso(base / 'symbols.toml', SYMBOLS.replace('@NOME@', self.v['nome'])
                          .replace('@PROFILO@', self.prof).replace('@ENTRY@', f'{entry:08X}'))
        self.distanza(dati)
        self.attese_trovate(dati)
        log(T(f'  progetto pronto: eseguibile {self.exe}, entry 0x{entry:08X}',
              f'  project ready: executable {self.exe}, entry 0x{entry:08X}'))
        return True

    def attese_trovate(self, exe: bytes) -> None:
        """Salto delle attese (v0.10): v_wait di questa versione, controllato nell'eseguibile, e la correzione di
        psxrecomp. Il game.toml lo scrive cmd_installa prima di compilare (installa --attese si, di default)."""
        v, motivo = trova_v_wait(exe)
        if v is not None and not attese_corrette():
            v, motivo = None, T('psxrecomp senza le correzioni di runtime/src/psx_cycles.c (28/10/2026)',
                                'psxrecomp without the runtime/src/psx_cycles.c fixes (28 Oct 2026)')
        if v is None:
            self.salva(attese=None)
            log(T(f'  salto delle attese non disponibile: {motivo}', f'  idle skip not available: {motivo}'))
        else:
            self.salva(attese={'v_wait': f'0x{v:08X}', 'siti': [f'0x{v + 0x28:08X}', f'0x{v + 0x70:08X}']})
            log(T(f'  salto delle attese disponibile: v_wait a 0x{v:08X} (punti 0x{v + 0x28:08X} e 0x{v + 0x70:08X})',
                  f'  idle skip available: v_wait at 0x{v:08X} (sites 0x{v + 0x28:08X} and 0x{v + 0x70:08X})'))

    def distanza(self, exe: bytes) -> bool:
        """Mod "Distanza visiva" (spenta di default): plugin, pacchetto e punti di aggancio nel game.toml,
        solo se aot/sm2_renderer.json ha gli indirizzi di questa versione e le istruzioni corrispondono.
        Altrimenti toglie quello che una installazione precedente avesse scritto."""
        base = self.cartella
        toml = base / 'game.toml'
        lay, motivo = layout_renderer(self.prof, exe)
        sorgenti = (base / 'mods_src' / 'sm2_draw_distance.cpp', base / 'mods_src' / 'sm2_draw_distance_init.c')
        pacchetto = base / 'mods' / 'preloaded' / 'packages' / 'sm2.enhancement.draw-distance'
        testo = toml.read_text(encoding='utf-8')
        senza = re.sub(re.escape(INIZIO_DISTANZA) + r'.*?' + re.escape(FINE_DISTANZA) + r'\n?', '', testo, flags=re.S)
        if lay is None:
            for f in sorgenti:
                if f.is_file():
                    f.unlink()
            if pacchetto.is_dir():
                shutil.rmtree(pacchetto)
            if senza != testo:
                toml.write_text(senza, encoding='utf-8')
            log(T(f'  mod "Distanza visiva": non disponibile per questa versione ({motivo})',
                  f'  "Draw distance" mod: not available for this version ({motivo})'))
            self.salva(distanza=False, bordi_widescreen=False, area_pacchetti=False, gioco_widescreen=False,
                       piani_widescreen=False, area_widescreen=False)
            return False
        bordi, motivo_bordi = bordi_renderer(self.prof, exe, lay)
        if bordi:
            lay = dict(lay, **bordi)
        piani, motivo_piani = piani_renderer(self.prof, exe) if bordi else (None, T('senza la correzione dei bordi',
                                                                                      'without the edge fix'))
        if piani:
            lay['PianiX'] = piani
        link, motivo_area = collegamento_renderer(self.prof, exe)
        if link:
            lay['PacketLink'] = link
        gioco, motivo_gioco = stato_gioco(self.prof) if bordi else (None, T('senza la correzione dei bordi',
                                                                              'without the edge fix'))
        if gioco:
            lay = dict(lay, **gioco)
        h = {k: f'0x{v:08X}' for k, v in lay.items()}
        cpp = PLUGIN_DISTANZA.replace('@NOME@', self.v['nome']).replace('@PROFILO@', self.prof)
        cpp = cpp.replace('@AREA_NOTA@', AREA_NOTA if link else AREA_NOTA_NO)
        cpp = cpp.replace('@AREA_PUNTI@', AREA_PUNTI if link else '')
        cpp = cpp.replace('@AREA_ATTIVA@', AREA_ATTIVA if link else ATTIVA_SENZA_AREA)
        cpp = cpp.replace('@AREA_REGISTRA@', AREA_REGISTRA if link else '')
        cpp = cpp.replace('@BORDI_CODICE@', BORDI_CODICE if bordi else '')
        cpp = cpp.replace('@BORDI_REGISTRA@', BORDI_REGISTRA if bordi else '')
        cpp = cpp.replace('@PIANI_CODICE@', PIANI_CODICE if piani else '')
        cpp = cpp.replace('@PIANI_REGISTRA@', PIANI_REGISTRA if piani else '')
        cpp = cpp.replace('@GIOCO_CODICE@', GIOCO_CODICE if gioco else '')
        cpp = cpp.replace('@GIOCO_REGISTRA@', GIOCO_REGISTRA if gioco else '')
        for k, v in h.items():
            cpp = cpp.replace(f'@{k}@', v)
        if re.search(r'@[A-Za-z0-9_]+@', cpp):
            raise RuntimeError(T('modello del plugin "Distanza visiva" con segnaposti non sostituiti',
                                 '"Draw distance" plugin template with placeholders not replaced'))
        scrivi_se_diverso(sorgenti[0], cpp)
        scrivi_se_diverso(sorgenti[1], PLUGIN_DISTANZA_INIT)
        cartella_pacchetto = pacchetto / '1.0.0'
        cartella_pacchetto.mkdir(parents=True, exist_ok=True)
        game_id = leggi_toml(toml)['game']['id']
        scrivi_se_diverso(cartella_pacchetto / 'manifest.toml',
                          MANIFESTO_DISTANZA.replace('@NOME@', NOMI_EN.get(self.prof, self.v['nome']))
                          .replace('@GAME_ID@', game_id)
                          .replace('@PIU_POLIGONI@', ' and the game has room for about four times as many polygons '
                                                     'per frame' if link else '')
                          .replace('@PIU_POLIGONI_2@', ', with room for about four times as many polygons per frame'
                                   if link else '')
                          .replace('@AREA_FEATURE@', AREA_FEATURE if link else '')
                          .replace('@AREA_PLUGIN@', AREA_PLUGIN if link else ''))
        # launcher v0.11: con l'area piu' grande, il widescreen la accende per la sessione ([[requirement]], formato 7)
        man_ws = base / 'mods' / 'preloaded' / 'packages' / 'sm2.enhancement.widescreen' / '1.0.0' / 'manifest.toml'
        if man_ws.parent.is_dir():
            scrivi_se_diverso(man_ws, MANIFESTO_WIDESCREEN.replace('format_version = 5', 'format_version = 7', 1)
                              + REQUISITO_AREA if link else MANIFESTO_WIDESCREEN)
        funzioni = ['FogPc', 'SubmitPc'] + (['SwapPc', 'LimitPc'] if link else [])
        istruzioni = [h['PrecisionPc']]
        if link:                         # area dei pacchetti piu' grande: i 3 punti della lunghezza dei pacchetti
            istruzioni += [h['PacketT2'], h['PacketS2'], h['PacketLink']]
        if bordi:                        # mod Widescreen: i 4 punti dei bit "fuori schermo"
            istruzioni += [f'0x{lay["PrecisionPc"] - 4:08X}'] + [h[k] for k in CHIAVI_BORDI + CHIAVI_LIMITI]
        if piani:                        # mod Widescreen (v0.11): i due piani laterali
            istruzioni.append(h['PianiX'])
        blocco = (BLOCCO_DISTANZA
                  .replace('@FUNZIONI@', ', '.join(f'"{h[f]}"' for f in funzioni))
                  .replace('@NOTA_FUNZIONI_AREA@', NOTA_FUNZIONI_AREA if link else '')
                  .replace('@NOTA_AREA@', NOTA_AREA if link else '')
                  .replace('@NOTA_BORDI@', NOTA_BORDI if bordi else '')
                  .replace('@NOTA_PIANI@', NOTA_PIANI if piani else '')
                  .replace('@ISTRUZIONI@', ', '.join(f'"{x}"' for x in istruzioni)))
        righe = senza.splitlines(keepends=True)
        pos = next((i for i, r in enumerate(righe) if r.strip() == '[recompiler]'), None)
        if pos is None:
            nuovo = senza.rstrip('\n') + '\n\n[recompiler]\n' + blocco
        else:
            nuovo = ''.join(righe[:pos + 1]) + blocco + ''.join(righe[pos + 1:])
        if nuovo != testo:
            toml.write_text(nuovo, encoding='utf-8')
            log(T('  game.toml: punti di aggancio per la mod "Distanza visiva" nella sezione [recompiler]',
                  '  game.toml: hook sites for the "Draw distance" mod in the [recompiler] section'))
        log(T('  mod "Distanza visiva": plugin e pacchetto scritti (spenta di default; opzioni --distanza si)',
              '  "Draw distance" mod: plugin and package written (off by default; options --draw-distance yes)'))
        if link:
            log(T(f'  mod "Distanza visiva": area dei pacchetti piu\' grande (0x60000 byte per buffer invece di 0x17000), '
                  f'con la lunghezza dei pacchetti corretta anche in {h["PacketLink"]}',
                  f'  "Draw distance" mod: larger packet area (0x60000 bytes per buffer instead of 0x17000), '
                  f'with the packet length also corrected at {h["PacketLink"]}'))
        else:
            log(T(f'  mod "Distanza visiva": area dei pacchetti originale ({motivo_area})',
                  f'  "Draw distance" mod: original packet area ({motivo_area})'))
        if bordi:
            log(T('  mod "Widescreen": bordi dello schermo largo nei bit "fuori schermo" dei vertici (9 punti agganciati)',
                  '  "Widescreen" mod: wide screen edges in the vertex "off screen" bits (9 sites hooked)'))
        else:
            log(T(f'  mod "Widescreen": senza la correzione dei bordi ({motivo_bordi})',
                  f'  "Widescreen" mod: without the edge fix ({motivo_bordi})'))
        if piani:
            log(T(f'  mod "Widescreen": gli oggetti ai lati non vengono piu\' scartati interi (piani laterali allargati, '
                  f'punto {h["PianiX"]})',
                  f'  "Widescreen" mod: objects at the sides are no longer culled whole (side planes widened, '
                  f'site {h["PianiX"]})'))
        if link:
            log(T('  mod "Widescreen": accende anche l\'area dei pacchetti piu\' grande (funzione nascosta packet-area)',
                  '  "Widescreen" mod: also turns on the larger packet area (hidden packet-area feature)'))
        elif bordi:
            log(T(f'  mod "Widescreen": oggetti ai lati scartati come nel gioco originale ({motivo_piani})',
                  f'  "Widescreen" mod: objects at the sides culled as in the original game ({motivo_piani})'))
        if gioco:
            log(T(f'  mod "Widescreen": si allarga solo mentre si gioca (stato del livello {h["ExitState"]}, lista dei '
                  f'moduli {h["ModHead"]}); il giornale resta in 4:3',
                  f'  "Widescreen" mod: widens only during gameplay (level state {h["ExitState"]}, module list '
                  f'{h["ModHead"]}); the journal stays 4:3'))
        else:
            log(T(f'  mod "Widescreen": gioco riconosciuto dalla GTE ({motivo_gioco})',
                  f'  "Widescreen" mod: gameplay recognized from the GTE ({motivo_gioco})'))
        try:
            cambiato = imposta_gte(toml, not gioco)
        except OSError as e:
            cambiato = T(f'avviso: game.toml non aggiornato ({e})', f'warning: game.toml not updated ({e})')
        if cambiato:
            log('  ' + cambiato)
        self.salva(distanza=True, bordi_widescreen=bool(bordi), area_pacchetti=bool(link), gioco_widescreen=bool(gioco),
                   piani_widescreen=bool(piani), area_widescreen=bool(link))
        return True

    def m3(self, senza: bool = False) -> bool:
        """Profilo AOT dei moduli di CD.WAD (Milestone 3) dal disco dell'utente, con le basi note."""
        base = self.cartella
        profilo_p = base / 'aot' / 'overlays.json'
        statico = base / 'generated' / 'aot'
        if senza:
            log(T('[m3] saltata (--senza-m3): i moduli li compilera\' il gioco mentre gira',
                  '[m3] skipped (--no-m3): the game will compile the modules while it runs'))
            if profilo_p.is_file():
                profilo_p.unlink()
            if statico.is_dir():
                shutil.rmtree(statico)                # codice generato da questa installazione
            self.salva(m3={'attiva': False})
            return True
        log(T('[m3] profilo dei moduli compilati in anticipo', '[m3] profile of the precompiled modules'))
        sys.path.insert(0, str(TOOLS))
        import sm2_aot_profile as sap                 # aggiunge psxrecomp/tools al percorso
        import aot_overlay_pipeline as pipeline
        basi = json.loads(PLACEMENTS.read_text(encoding='utf-8'))['versions'].get(self.prof)
        if not basi:
            log(T(f'  nessuna base nota per {self.prof}: niente moduli in anticipo',
                  f'  no known bases for {self.prof}: no precompiled modules'))
            return self.m3(senza=True)
        disc = pipeline.Disc(self.cue)
        sha1 = pipeline.digest(disc.binary, 'sha1')
        hed, wad = disc.read('CD.HED'), disc.read('CD.WAD')
        indice = sap.parse_hed(hed)
        attesi = self.v['moduli']
        usati, scartati = {}, []
        for nome, info in sorted(basi['modules'].items()):
            if not info.get('placements'):
                continue
            a = attesi.get(nome)
            ok = a is not None
            for est in ('bin', 'rel'):
                voci = indice.get(f'{nome}.{est}', [])
                if not ok or len(voci) != 1:
                    ok = False
                    break
                off, size = voci[0]
                corpo = wad[off:off + size]
                ok = (size == a[f'{est}_size'] and hashlib.sha256(corpo).hexdigest() == a[f'{est}_sha256'])
            if ok:
                usati[nome] = info
            else:
                scartati.append(nome)
        if scartati:
            log(T(f'  moduli diversi da quelli conosciuti, lasciati al gioco: {", ".join(scartati)}',
                  f'  modules different from the known ones, left to the game: {", ".join(scartati)}'))
        if not usati:
            log(T('  nessun modulo uguale a quelli conosciuti: niente moduli in anticipo',
                  '  no module identical to the known ones: no precompiled modules'))
            return self.m3(senza=True)
        game_id = leggi_toml(base / 'game.toml')['game']['id']
        profilo = sap.build_profile(game_id, sha1, hed, wad, usati)
        pipeline.positioned_sources(disc, profilo['images'])   # stessa verifica che fara' generate
        profilo_p.parent.mkdir(parents=True, exist_ok=True)
        testo = json.dumps(profilo, indent=1) + '\n'
        if profilo_p.is_file() and profilo_p.read_text(encoding='utf-8') == testo:
            log(T('  aot/overlays.json gia\' aggiornato', '  aot/overlays.json already up to date'))
        else:
            profilo_p.write_text(testo, encoding='utf-8')
            log(T('  scritto aot/overlays.json', '  aot/overlays.json written'))
        n_basi = profilo['expected_records']
        log(T(f'  moduli: {len(usati)} su {len(basi["modules"])}, basi: {n_basi}',
              f'  modules: {len(usati)} of {len(basi["modules"])}, bases: {n_basi}'))
        self.salva(m3={'attiva': True, 'moduli': len(usati), 'basi': n_basi, 'scartati': scartati,
                       'disco_sha1': sha1})
        return True

    def genera(self) -> bool:
        log(T('[genera] codice C del gioco (psxrecomp generate) e dei moduli compilati in anticipo',
              '[generate] C code of the game (psxrecomp generate) and of the precompiled modules'))
        ok = self.cli(['generate', '--config', 'game.toml', '--project-root', '.', '--disc', str(self.cue),
                       '--no-toolchain-download'], self.cartella / 'psxrecomp_cli_output.txt')
        marker = self.cartella / 'generated' / f'{self.exe}_dispatch.c'
        if ok and not marker.is_file():
            log(T(f'ERRORE: manca {marker.relative_to(self.cartella)}', f'ERROR: {marker.relative_to(self.cartella)} is missing'))
            ok = False
        statico = self.cartella / 'generated' / 'aot' / 'overlays_static.c'
        if ok and (self.cartella / 'aot' / 'overlays.json').is_file():
            if not statico.is_file():
                log(T('ERRORE: c\'e\' il profilo dei moduli ma generate non ha scritto generated/aot/overlays_static.c',
                      'ERROR: the module profile is there but generate did not write generated/aot/overlays_static.c'))
                ok = False
            else:
                parti = sorted(statico.parent.glob('overlays_static_*.c'))
                mb = sum(p.stat().st_size for p in parti) / 1e6
                log(T(f'  moduli compilati in anticipo: {len(parti)} file di codice C, {mb:.1f} MB',
                      f'  precompiled modules: {len(parti)} C code files, {mb:.1f} MB'))
        return ok

    def compila(self, debug: bool, pgo: bool = False) -> bool:
        ok = True
        fatto_pgo = self.compila_pgo() if pgo else False
        if pgo and not fatto_pgo:
            log(T('  PGO non riuscito: compilo l\'eseguibile normale, senza PGO',
                  '  PGO failed: building the normal executable, without PGO'))
        self.salva(pgo=fatto_pgo)
        for build_dir, extra, desc in (('build-release', list(IPO_ON), T('eseguibile del gioco', 'game executable')),
                                       ('build-dev', ['--cmake-extra=-DPSX_DEBUG_TOOLS=ON'] + IPO_ON,
                                        T('eseguibile di sviluppo con server di debug (per i test)',
                                          'development executable with the debug server (for tests)'))):
            if build_dir == 'build-dev' and not debug:
                continue
            if build_dir == 'build-release' and fatto_pgo:
                continue                     # gia' compilato con il PGO
            log(T(f'[compila] {desc} in {build_dir}', f'[compile] {desc} in {build_dir}'))
            ok = self.cli(['rebuild', '--config', 'game.toml', '--project-root', '.', '--build-dir', build_dir,
                           '--target', 'psx-runtime', '--exe-basename', EXE_BASE, '--no-toolchain-download',
                           '--no-pgo'] + extra, self.cartella / 'psxrecomp_cli_output.txt')
            exe = trova_exe(self.cartella / build_dir)
            if exe:
                log(f'  {exe} ({exe.stat().st_size / 1e6:.1f} MB)')
            ok = ok and exe is not None
            if not ok:
                break
        if ok:
            vk = self.vulkan_compilato()
            self.salva(vulkan=vk)
            if vk or 'offer_vulkan' in (self.cartella / 'game.toml').read_text(encoding='utf-8'):
                cambio = imposta_chiave_toml(self.cartella / 'game.toml', 'video', 'offer_vulkan', vk)
                if cambio:
                    log('  ' + cambio)
            log(T('  motore grafico Vulkan (sperimentale): ', '  Vulkan renderer (experimental): ') +
                (T('compilato, si sceglie con opzioni --motore vulkan', 'built, choose it with options --renderer vulkan')
                 if vk else T('non compilato (strumenti non presenti in tools\\vulkan)',
                              'not built (tools not present in tools\\vulkan)')))
            for d in ('build-release', 'build-dev'):
                if trova_exe(self.cartella / d):
                    cambio = risoluzione_iniziale(self.cartella / d / 'mods' / 'state.toml')
                    if cambio:
                        log('  ' + cambio)
        return ok

    def vulkan_compilato(self) -> bool:
        """Dall'ultima configurazione di CMake in psxrecomp_cli_output.txt: il motore Vulkan e' stato compilato davvero?"""
        try:
            testo = (self.cartella / 'psxrecomp_cli_output.txt').read_text(encoding='utf-8', errors='replace')
        except OSError:
            return False
        righe = [r for r in testo.splitlines() if 'Vulkan backend:' in r]
        return bool(righe) and 'Vulkan backend: headers' in righe[-1]

    def compila_pgo(self) -> bool:
        """PGO (v0.10): eseguibile strumentato, partita di allenamento, unione dei conteggi, eseguibile del gioco
        compilato con i conteggi (clang mette in ordine e ottimizza di piu' il codice che si usa di piu')."""
        uscita = self.cartella / 'psxrecomp_cli_output.txt'
        comune = ['rebuild', '--config', 'game.toml', '--project-root', '.', '--target', 'psx-runtime',
                  '--exe-basename', EXE_BASE, '--no-toolchain-download', '--no-pgo']
        log(T('[compila] PGO 1/4: eseguibile strumentato (conta i passaggi nel codice) in build-pgo-gen',
              '[compile] PGO 1/4: instrumented executable (counts the passes through the code) in build-pgo-gen'))
        if not self.cli(comune + ['--build-dir', 'build-pgo-gen', '--cmake-extra=-DPSX_DEBUG_TOOLS=ON', '--cmake-extra=-DPSX_RUNTIME_IPO=OFF',
                                  '--cmake-extra=-DPSX_PGO=generate'], uscita):
            return False
        exe = trova_exe(self.cartella / 'build-pgo-gen')
        if exe is None:
            log(T('  ERRORE: manca l\'eseguibile strumentato', '  ERROR: the instrumented executable is missing'))
            return False
        log(T('[compila] PGO 2/4: partita di allenamento (finestra nascosta e audio spento, circa 3-4 minuti)',
              '[compile] PGO 2/4: training game (hidden window, audio off, about 3-4 minutes)'))
        r = allena_pgo(self.prof, exe, self.cartella / 'game.toml', self.cue, self.cartella / 'build-pgo-gen' / 'pgo')
        log(T(f'  allenamento {"riuscito" if r["ok"] else "NON riuscito"} in {r.get("secondi")} s',
              f'  training {"succeeded" if r["ok"] else "FAILED"} in {r.get("secondi")} s') +
            (f': {r["errore"]}' if r.get('errore') else '') +
            (T(f'; conteggi: {", ".join(r["conteggi"])}', f'; counts: {", ".join(r["conteggi"])}')
             if r.get('conteggi') else ''))
        if not r['ok']:
            return False
        log(T('[compila] PGO 3/4: unione dei conteggi', '[compile] PGO 3/4: merging the counts'))
        prof = unisci_pgo(self.cartella / 'build-pgo-gen' / 'pgo', self.cartella / 'pgo' / 'default.profdata')
        if prof is None:
            return False
        dest = self.cartella / 'build-release' / 'pgo'
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prof, dest / 'default.profdata')
        log(T('[compila] PGO 4/4: eseguibile del gioco con il PGO in build-release',
              '[compile] PGO 4/4: game executable with PGO in build-release'))
        ok = self.cli(comune + ['--build-dir', 'build-release', '--cmake-extra=-DPSX_PGO=use'] + IPO_ON, uscita)
        exe = trova_exe(self.cartella / 'build-release')
        if not (ok and exe):
            return False
        log(T(f'  {exe} ({exe.stat().st_size / 1e6:.1f} MB), con il PGO', f'  {exe} ({exe.stat().st_size / 1e6:.1f} MB), with PGO'))
        shutil.rmtree(self.cartella / 'build-pgo-gen', ignore_errors=True)     # non serve piu' (piu' di 1 GB)
        return True


def trova_exe(cartella: Path):
    for nome in (EXE_BASE + '.exe', EXE_BASE):
        p = cartella / nome
        if p.is_file():
            return p
    return None


def cmd_installa(args) -> int:
    cat = catalogo()
    prof = args.profilo
    if prof not in cat:
        log(T(f'ERRORE: versione sconosciuta {prof}; quelle conosciute: {", ".join(cat)}',
              f'ERROR: unknown version {prof}; the known ones are: {", ".join(cat)}'))
        return 2
    cartella = Path(args.cartella) if args.cartella else GIOCHI / prof
    cartella = cartella if cartella.is_absolute() else (ROOT / cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    apri_log(cartella / 'launcher_log.txt')
    nome = nome_versione(prof, cat[prof]['nome'])
    log(T(f'SM2-Recomp launcher {VERSIONE} - installazione di {prof} ({nome}) in {cartella}',
          f'SM2-Recomp launcher {VERSIONE} - installing {prof} ({nome}) in {cartella}'))
    cache = CacheHash(GIOCHI / 'cache_hash.json')
    if args.disco:
        disco = riconosci_dump(Path(args.disco).resolve(), cache, cat)
        stampa_dump(disco)
        if disco['profilo'] != prof or disco['problemi']:
            log(T(f'ERRORE: il disco indicato non e\' un dump usabile di {prof}',
                  f'ERROR: the given disc is not a usable dump of {prof}'))
            return 1
        if disco['formato'] != 'cue':
            log(T('ERRORE: serve il foglio .cue: usa prima il comando "importa", che lo scrive',
                  'ERROR: the .cue sheet is needed: first use the "import" command, which writes it'))
            return 1
    else:
        disco = disco_della_versione(prof, cache, cat)
        if disco is None:
            log(T(f'ERRORE: nessun dump usabile di {prof} in input/{prof}/: usa prima "importa"',
                  f'ERROR: no usable dump of {prof} in input/{prof}/: first use "import"'))
            return 1
        log(T('disco: ', 'disc: ') + f'{disco["foglio"]}' + (f' (Redump: {disco["redump"]})' if disco['redump'] else ''))
    cache.salva()
    libero = shutil.disk_usage(cartella).free / 1024 ** 3
    log(T(f'spazio libero sul disco: {libero:.1f} GB', f'free disk space: {libero:.1f} GB'))
    if libero < SPAZIO_MINIMO_GB:
        log(T(f'ERRORE: servono almeno {SPAZIO_MINIMO_GB} GB liberi', f'ERROR: at least {SPAZIO_MINIMO_GB} GB of free space are needed'))
        return 1
    log(attiva_toolchain())
    log(dipendenze_offline())
    log(T(f'core per compilare: {imposta_core(args.core)} su {os.cpu_count()}',
          f'cores for compiling: {imposta_core(args.core)} of {os.cpu_count()}'))
    inst = Installazione(prof, cartella, disco, cat, pgxp=args.pgxp, registratore=args.registratore)
    inst.salva(profilo=prof, nome=cat[prof]['nome'], disco=disco['foglio'], disco_sha1=disco['dati_sha1'],
               redump=disco['redump'], launcher=VERSIONE, completata=False, pgxp=args.pgxp,
               registratore=args.registratore)
    if args.registratore:
        log(T('installazione di prova con il registratore delle partite (QA): ogni partita viene registrata in '
              'saves\\diagnostics\\ accanto all\'eseguibile',
              'test installation with the game recorder (QA): every game is recorded in saves\\diagnostics\\ next '
              'to the executable'))
    if args.pgo:
        log(T('eseguibile con il PGO: dopo il codice C, una partita di allenamento di circa 3 minuti (finestra nascosta, '
              'audio spento) e una compilazione in piu\'',
              'executable with PGO: after the C code, a training game of about 3 minutes (hidden window, audio off) '
              'and one more build'))
    if args.pgxp:
        log(T('eseguibile con i punti di aggancio di PGXP (geometria piu\' precisa): la si accende con avvia --pgxp',
              'executable with the PGXP hooks (more precise geometry): turn it on with play --pgxp'))
    t_tot = time.time()
    tempi = {}
    for passo in args.passi:
        t0 = time.time()
        if passo == 'prepara':
            ok = inst.prepara()
        elif passo == 'm3':
            ok = inst.m3(args.senza_m3)
        elif passo == 'genera':
            ok = inst.genera()
        else:
            v = (inst.stato.get('attese') or {}).get('v_wait')
            acceso = bool(v) and args.attese == 'si'
            try:
                cambiato = imposta_attese(cartella / 'game.toml', int(v, 16) if acceso else None)
            except OSError as e:
                cambiato = T(f'avviso: game.toml non aggiornato ({e})', f'warning: game.toml not updated ({e})')
            if cambiato:
                log('  ' + cambiato)
            inst.salva(salto_attese=acceso and attese_accese(cartella / 'game.toml'))
            ok = inst.compila(args.debug, pgo=args.pgo)
            if not ok and acceso:
                # l'eseguibile rimasto potrebbe essere uno compilato prima delle correzioni di psxrecomp
                try:
                    imposta_attese(cartella / 'game.toml', None)
                except OSError:
                    pass
                inst.salva(salto_attese=attese_accese(cartella / 'game.toml'))
                log(T('  salto delle attese tolto dal game.toml: la compilazione non e\' riuscita',
                      '  idle skip removed from game.toml: the build failed'))
        tempi[passo] = round(time.time() - t0, 1)
        log(T(f'[{passo}] {"OK" if ok else "ERRORE"} in {tempi[passo]:.0f} s',
              f'[{PASSI_EN.get(passo, passo)}] {"OK" if ok else "ERROR"} in {tempi[passo]:.0f} s'))
        if not ok:
            inst.salva(tempi=tempi, errore=passo)
            log(T('\nInstallazione NON completata: dettagli in launcher_log.txt e psxrecomp_cli_output.txt',
                  '\nInstallation NOT completed: details in launcher_log.txt and psxrecomp_cli_output.txt'))
            return 1
    completa = set(args.passi) >= {'prepara', 'm3', 'genera', 'compila'}
    exe = trova_exe(cartella / 'build-release')
    if args.registratore and completa:
        for e in [exe] + ([trova_exe(cartella / 'build-dev')] if args.debug else []):
            if e is not None:
                log(prepara_cache_overlay(e, cartella / 'game.toml', Path(disco['foglio'])))
    inst.salva(tempi=tempi, errore=None, completata=completa and exe is not None,
               eseguibile=str(exe) if exe else None, data=f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}')
    log(T(f'\nFatto in {time.time() - t_tot:.0f} s: ', f'\nDone in {time.time() - t_tot:.0f} s: ') +
        (T(f'{prof} installato, per giocare: sm2_launcher.py avvia --profilo {prof}',
           f'{prof} installed, to play: sm2_launcher.py play --profile {prof}') if completa
         else T('passi richiesti completati', 'requested steps completed')))
    return 0


# QA, livello 4 (3/11/2026): la prima volta che un eseguibile nuovo parte, psxrecomp trova all'avvio alcuni pezzi di
# codice non compilati in anticipo (3 nella USA Rev 1), li esegue con l'interprete e intanto li compila in sottofondo
# (cache/ accanto all'eseguibile, qualche secondo). In quella prima partita il gioco va in modo leggermente diverso
# (indagine del 3/11, work/qa/indagine_registratore_*: la RAM cambia dal frame 471), quindi la sua registrazione non si
# rigioca in modo esatto; dalla seconda partita in poi, con la cache pronta, le partite sono identiche frame per frame
# (anche con il turbo). Per questo le installazioni con il registratore fanno partire il gioco una volta da sole prima
# che si registri qualcosa.

def pezzi_cache_overlay(exe: Path) -> int:
    """Pezzi di codice compilati al volo da psxrecomp (cache degli overlay) accanto all'eseguibile."""
    cache = exe.parent / 'cache'
    return sum(1 for _ in cache.rglob('*.dll')) if cache.is_dir() else 0


def firma_cache_overlay(exe: Path) -> tuple:
    cache = exe.parent / 'cache'
    if not cache.is_dir():
        return ()
    voci = []
    for f in cache.rglob('*'):
        try:
            voci.append((str(f), f.stat().st_size if f.is_file() else -1))
        except OSError:
            pass
    return tuple(sorted(voci))


def prepara_cache_overlay(exe: Path, toml: Path, cue: Path, secondi_max: int = 150, minimo: int = 40,
                          quiete: int = 15) -> str:
    """Fa partire il gioco da solo (finestra nascosta, audio spento, memory card in una cartella temporanea) finche' la
    cache degli overlay e' pronta, poi lo chiude e toglie la registrazione di questo avvio e la cartella temporanea.
    Non fa niente se la cache ha gia' dei pezzi."""
    n = pezzi_cache_overlay(exe)
    if n:
        return T(f'cache del codice compilato al volo gia\' pronta ({n} pezzi) per {exe}',
                 f'cache of the code compiled on the fly already ready ({n} pieces) for {exe}')
    if not cue.is_file():
        return T(f'avviso: cache del codice compilato al volo non preparata (manca il disco {cue})',
                 f'warning: cache of the code compiled on the fly not prepared (the disc {cue} is missing)')
    diag = exe.parent / 'saves' / 'diagnostics'
    prima = {p.name for p in diag.glob('session-*')} if diag.is_dir() else set()
    tmp = Path(tempfile.mkdtemp(prefix='prepara_registrazione_', dir=str(exe.parent)))
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', SDL_AUDIO_DRIVER='dummy')
    cmd = [str(exe), '--hidden-window', '--no-launcher', '--game', str(toml), '--disc', str(cue),
           '--memcard-dir', str(tmp)]
    log(T(f'preparo la cache del codice compilato al volo per {exe.parent.name}: il gioco parte da solo, nascosto e '
          f'senza audio, per circa un minuto...',
          f'preparing the cache of the code compiled on the fly for {exe.parent.name}: the game starts by itself, '
          f'hidden and without audio, for about a minute...'))
    uscita = open(exe.parent / 'prepara_registrazione_output.txt', 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=uscita, stderr=subprocess.STDOUT)
    t0 = time.time()
    firma, cambiata = firma_cache_overlay(exe), time.time()
    try:
        while time.time() - t0 < secondi_max and p.poll() is None:
            time.sleep(1)
            f = firma_cache_overlay(exe)
            if f != firma:
                firma, cambiata = f, time.time()
            # pronta: ci sono pezzi compilati e la cartella non cambia da 15 s (la compilazione in sottofondo e' finita)
            if pezzi_cache_overlay(exe) and time.time() - t0 >= minimo and time.time() - cambiata >= quiete:
                break
    finally:
        chiuso_da_solo = p.poll() is not None
        if not chiuso_da_solo:
            p.terminate()
            try:
                p.wait(15)
            except subprocess.TimeoutExpired:
                p.kill()
        uscita.close()
    for s in (diag.glob('session-*') if diag.is_dir() else []):
        if s.name not in prima:
            shutil.rmtree(s, ignore_errors=True)    # registrazione di questo avvio di preparazione: non serve
    shutil.rmtree(tmp, ignore_errors=True)
    n = pezzi_cache_overlay(exe)
    if n:
        return T(f'cache del codice compilato al volo pronta: {n} pezzi in {time.time() - t0:.0f} s',
                 f'cache of the code compiled on the fly ready: {n} pieces in {time.time() - t0:.0f} s')
    return (T('avviso: la cache del codice compilato al volo non si e\' riempita',
              'warning: the cache of the code compiled on the fly did not fill up') +
            (T(f' (il gioco si e\' chiuso da solo con codice {p.returncode})',
               f' (the game closed by itself with code {p.returncode})') if chiuso_da_solo else '') +
            T(': la prima partita registrata potrebbe non rigiocarsi in modo esatto',
              ': the first recorded game might not replay exactly'))


def cmd_prepara_registrazione(args) -> int:
    cartella = Path(args.cartella) if args.cartella else ROOT / 'work' / 'registra' / args.profilo
    cartella = cartella if cartella.is_absolute() else (ROOT / cartella)
    apri_log(cartella / 'launcher_log.txt')
    try:
        stato = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        log(T(f'ERRORE: {args.profilo} non e\' installato in {cartella}', f'ERROR: {args.profilo} is not installed in {cartella}'))
        return 1
    if not stato.get('registratore'):
        log(T(f'ERRORE: {cartella} non e\' un\'installazione con il registratore (installa --registratore)',
              f'ERROR: {cartella} is not an installation with the recorder (install --recorder)'))
        return 1
    exe = trova_exe(cartella / ('build-dev' if args.debug else 'build-release'))
    if exe is None:
        log(T('ERRORE: eseguibile non trovato: rifai "installa --registratore"',
              'ERROR: executable not found: run "install --recorder" again'))
        return 1
    log(prepara_cache_overlay(exe, cartella / 'game.toml', Path(stato.get('disco') or '')))
    return 0


# ---------------------------------------------------------------------------------------------- avvia

def limita_cpu_meta() -> str:
    """Windows: questo processo (e quindi il gioco che lancia) sulla prima meta' dei processori logici."""
    if os.name != 'nt':
        return T('non Windows: nessun limite', 'not Windows: no limit')
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t),
                                           ctypes.POINTER(ctypes.c_size_t)]
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    me = k32.GetCurrentProcess()
    pm, sm = ctypes.c_size_t(0), ctypes.c_size_t(0)
    if not k32.GetProcessAffinityMask(me, ctypes.byref(pm), ctypes.byref(sm)):
        return T('limite non applicato', 'limit not applied')
    bits = [i for i in range(64) if (pm.value >> i) & 1]
    keep = bits[:max(1, len(bits) // 2)]
    if not k32.SetProcessAffinityMask(me, sum(1 << i for i in keep)):
        return T('limite non applicato', 'limit not applied')
    return T(f'limite CPU: {len(keep)} processori logici su {len(bits)}', f'CPU limit: {len(keep)} logical processors of {len(bits)}')


def cmd_avvia(args) -> int:
    cat = catalogo()
    prof = args.profilo
    cartella = Path(args.cartella) if args.cartella else GIOCHI / prof
    cartella = cartella if cartella.is_absolute() else (ROOT / cartella)
    apri_log(cartella / 'launcher_log.txt')
    try:
        stato = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        log(T(f'ERRORE: {prof} non e\' installato in {cartella}: usa prima "installa"',
              f'ERROR: {prof} is not installed in {cartella}: first use "install"'))
        return 1
    exe = trova_exe(cartella / ('build-dev' if args.debug else 'build-release'))
    cue = Path(stato.get('disco') or '')
    if exe is None or not cue.is_file():
        manca = (T('l\'eseguibile', 'the executable') if exe is None else T('il disco ', 'the disc ') + str(cue))
        log(T(f'ERRORE: manca {manca}: rifai "installa"', f'ERROR: {manca} is missing: run "install" again'))
        return 1
    if (cartella / 'mods' / 'preloaded' / 'packages' / MOD_WIDESCREEN[0]).is_dir():
        try:                         # installazioni v0.5-v0.6: il widescreen si attiva senza reinstallare
            cambiato = aggiorna_toml_widescreen(cartella / 'game.toml')
        except OSError as e:
            cambiato = T(f'avviso: game.toml non aggiornato ({e})', f'warning: game.toml not updated ({e})')
        if cambiato:
            log(cambiato)
    cmd = [str(exe), '--game', str(cartella / 'game.toml'), '--disc', str(cue)]
    if not args.con_launcher:
        cmd.append('--no-launcher')
        try:                         # QA-015: senza la finestra di psxrecomp il controller va scelto da qui
            nota = controller_predefinito(exe.parent / 'settings.toml')
        except OSError as e:
            nota = T(f'avviso: settings.toml non aggiornato per il controller ({e})',
                     f'warning: settings.toml not updated for the controller ({e})')
        if nota:
            log(nota)
    env = dict(os.environ)
    if args.risoluzione:
        env['PSX_INTERNAL_RESOLUTION'] = args.risoluzione
    if args.pgxp:
        env['PSX_GEOMETRY_CORRECTION'] = '1'
        env['PSX_PERSPECTIVE_TEXTURING'] = '1'
        if not stato.get('pgxp'):
            log(T('avviso: questa installazione non e\' compilata con --pgxp: PGXP funziona solo in parte',
                  'warning: this installation is not built with --pgxp: PGXP only works in part'))
    if args.cpu == 'meta':
        log(limita_cpu_meta())
    nome = nome_versione(prof, cat.get(prof, {}).get('nome', ''))
    log(T(f'avvio di {prof} ({nome}):', f'starting {prof} ({nome}):'), ' '.join(cmd))
    if args.risoluzione:
        log(T(f'risoluzione interna: {args.risoluzione}', f'internal resolution: {args.risoluzione}'))
    if args.pgxp:
        log(T('PGXP acceso (geometria e texture piu\' precise)', 'PGXP on (more precise geometry and textures)'))
    uscita = open(cartella / 'gioco_output.txt', 'w', encoding='utf-8', errors='replace')
    if not args.prova:
        flags = 0
        if os.name == 'nt':
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        p = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=uscita, stderr=subprocess.STDOUT,
                             creationflags=flags)
        log(T(f'gioco avviato (processo {p.pid})', f'game started (process {p.pid})'))
        return 0
    p = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=uscita, stderr=subprocess.STDOUT)
    t0 = time.time()
    while time.time() - t0 < args.prova and p.poll() is None:
        time.sleep(0.5)
    vivo = p.poll() is None
    durata = time.time() - t0
    if vivo:
        p.terminate()
        try:
            p.wait(15)
        except subprocess.TimeoutExpired:
            p.kill()
    uscita.close()
    coda = (cartella / 'gioco_output.txt').read_text(encoding='utf-8', errors='replace').splitlines()[-15:]
    log(T('ultime righe del gioco:\n    ', 'last lines of the game:\n    ') + '\n    '.join(coda))
    if vivo:
        log(T(f'PROVA RIUSCITA: il gioco e\' rimasto aperto {durata:.0f} s, poi e\' stato chiuso dal launcher',
              f'TEST PASSED: the game stayed open for {durata:.0f} s, then the launcher closed it'))
        return 0
    log(T(f'PROVA FALLITA: il gioco si e\' chiuso da solo dopo {durata:.0f} s (codice {p.returncode})',
          f'TEST FAILED: the game closed by itself after {durata:.0f} s (code {p.returncode})'))
    return 1


# -------------------------------------------------------------------------------------------- opzioni

# Mod incluse in psxrecomp (psxrecomp/mods/builtin/packages): pacchetto, funzione.
MOD_RISOLUZIONE = ('psx.enhancement.internal-resolution', 'internal-resolution')
MOD_PGXP = ('psx.enhancement.pgxp', 'pgxp')
MOD_FILTRI = ('psx.enhancement.image-filtering', 'image-filtering')
MOD_CRT = ('psx.enhancement.crt-filter', 'crt-filter')
MOD_AUDIO = ('psx.enhancement.enhanced-audio', 'enhanced-audio')
MOD_WIDESCREEN = ('sm2.enhancement.widescreen', 'widescreen')       # nostra, in mods/preloaded/
MOD_DISTANZA = ('sm2.enhancement.draw-distance', 'draw-distance')    # nostra, solo dove ci sono gli indirizzi
MOD_SUDDIVISI = ('sm2.enhancement.draw-distance', 'subdivision-precision')   # con PGXP

# Schermo e presentazione (31/10/2026): non sono mod ma impostazioni di psxrecomp, nella sezione [video] di settings.toml
# accanto all'eseguibile, lo stesso file che legge e scrive la finestra delle impostazioni di psxrecomp
# (recompiler/src/config_loader.cpp, load_user_settings). Nessuna cambia quello che fa il gioco.
SINCRONIA = {'accesa': 'on', 'spenta': 'off', 'adattiva': 'adaptive', 'vrr': 'vrr'}
SCHERMO = {'finestra': 0, 'senza-bordi': 1, 'esclusivo': 2}


def leggi_video(path: Path) -> dict:
    """La sezione [video] di settings.toml ({} se il file o la sezione mancano)."""
    if not path.is_file():
        return {}
    testo = path.read_text(encoding='utf-8', errors='replace')
    try:
        import tomllib
        return dict(tomllib.loads(testo).get('video') or {})
    except Exception:  # noqa: BLE001  (Python senza tomllib o file non valido: lettura riga per riga)
        out, dentro = {}, False
        for riga in testo.splitlines():
            r = riga.strip()
            if r.startswith('['):
                dentro = r == '[video]'
                continue
            m = re.match(r'^([A-Za-z_]+)\s*=\s*(.+?)\s*(#.*)?$', r) if dentro else None
            if m:
                v = m.group(2)
                if v in ('true', 'false'):
                    out[m.group(1)] = v == 'true'
                elif re.fullmatch(r'-?\d+', v):
                    out[m.group(1)] = int(v)
                else:
                    out[m.group(1)] = v.strip('"')
        return out


def scrivi_video(path: Path, valori: dict) -> None:
    """Scrive alcune chiavi della sezione [video] di settings.toml lasciando il resto com'e'. La prima volta salva una
    copia del file com'era in settings.toml.prima_del_launcher."""
    testo = path.read_text(encoding='utf-8') if path.is_file() else ''
    if path.is_file():
        copia = path.with_name('settings.toml.prima_del_launcher')
        if not copia.exists():
            copia.write_text(testo, encoding='utf-8')
    righe = testo.splitlines()

    def fmt(v):
        return ('true' if v else 'false') if isinstance(v, bool) else (str(v) if isinstance(v, int) else _q(v))
    inizio = next((i for i, r in enumerate(righe) if r.strip() == '[video]'), None)
    if inizio is None:
        if righe and righe[-1].strip():
            righe.append('')
        righe.append('[video]')
        righe += [f'{k} = {fmt(v)}' for k, v in valori.items()]
    else:
        fine = next((i for i in range(inizio + 1, len(righe)) if righe[i].strip().startswith('[')), len(righe))
        for k, v in valori.items():
            pat = re.compile(r'^\s*' + re.escape(k) + r'\s*=')
            idx = next((i for i in range(inizio + 1, fine) if pat.match(righe[i])), None)
            if idx is None:
                dove = max((i for i in range(inizio, fine) if righe[i].strip()), default=inizio) + 1
                righe.insert(dove, f'{k} = {fmt(v)}')
                fine += 1
            else:
                righe[idx] = f'{k} = {fmt(v)}'
    path.write_text('\n'.join(righe) + '\n', encoding='utf-8')


def controller_predefinito(path: Path) -> str:
    """QA-015 (4/11/2026): il giocatore 1 usa il primo controller collegato se settings.toml non dice niente.
    Nell'eseguibile con cui si gioca psxrecomp parte con il giocatore 1 sulla sola tastiera finche' non si sceglie un
    controller nella sua finestra, che il launcher salta con --no-launcher (runtime/src/main.cpp: "Release keeps
    keyboard as its pre-launch default"). Con [controller] p1_device = "auto" (come gia' nell'eseguibile di prova) usa
    il primo controller collegato, anche se lo si collega a gioco aperto, e la tastiera resta attiva: i tasti di
    keybinds.ini valgono sempre. Una scelta gia' salvata (un controller preciso, "keyboard", "none") non si tocca.
    Restituisce la riga per il registro, o '' se non c'era niente da fare."""
    testo = path.read_text(encoding='utf-8') if path.is_file() else ''
    righe = testo.splitlines()
    inizio = next((i for i, r in enumerate(righe) if r.strip() == '[controller]'), None)
    if inizio is not None:
        fine = next((i for i in range(inizio + 1, len(righe)) if righe[i].strip().startswith('[')), len(righe))
        if any(re.match(r'^\s*p1_device\s*=', righe[i]) for i in range(inizio + 1, fine)):
            return ''
        righe.insert(inizio + 1, 'p1_device = "auto"')
    else:
        if righe and righe[-1].strip():
            righe.append('')
        righe += ['[controller]', 'p1_device = "auto"']
    if path.is_file():
        copia = path.with_name('settings.toml.prima_del_launcher')
        if not copia.exists():
            copia.write_text(testo, encoding='utf-8')
    path.write_text('\n'.join(righe) + '\n', encoding='utf-8')
    return T('controller: il giocatore 1 usa il primo controller collegato (settings.toml [controller] p1_device = '
             '"auto"); la tastiera resta attiva',
             'controller: player 1 uses the first connected controller (settings.toml [controller] p1_device = '
             '"auto"); the keyboard stays active')


def descrivi_video(video: dict) -> str:
    """Le impostazioni dello schermo in parole (quelle assenti valgono come psxrecomp le sceglie da solo)."""
    sinc = {v: k for k, v in SINCRONIA.items()}
    sch = {v: k for k, v in SCHERMO.items()}
    fs = video.get('fullscreen')
    fs = int(fs) if isinstance(fs, (bool, int)) else None
    if lingua_scelta() == 'en':
        sch_en = {0: 'window', 1: 'borderless fullscreen', 2: 'exclusive fullscreen'}
        return ', '.join([
            f"renderer {'Vulkan' if video.get('renderer') == 'vulkan' else 'OpenGL'}",
            f"vertical sync {video.get('vsync', 'on')}",
            f"render thread {'yes' if video.get('render_thread') else 'no'}",
            f"screen {sch_en.get(fs, 'window') if fs is not None else 'window'}",
            f"window width {video.get('window_width', 'automatic')}",
            f"low-latency input {'no' if video.get('low_latency_input') is False else 'yes'}",
            f"smooth motion {'yes' if video.get('frame_generation') else 'no'}"])
    return ', '.join([
        f"motore grafico {'Vulkan' if video.get('renderer') == 'vulkan' else 'OpenGL'}",
        f"sincronia verticale {sinc.get(str(video.get('vsync', 'on')), video.get('vsync', 'accesa'))}",
        f"thread video {'si' if video.get('render_thread') else 'no'}",
        f"schermo {sch.get(fs, 'finestra') if fs is not None else 'finestra'}",
        f"larghezza della finestra {video.get('window_width', 'automatica')}",
        f"input a bassa latenza {'no' if video.get('low_latency_input') is False else 'si'}",
        f"movimento fluido {'si' if video.get('frame_generation') else 'no'}"])


def _q(v: str) -> str:
    return '"' + str(v).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


def leggi_stato_mod(path: Path) -> dict:
    """mods/state.toml accanto all'eseguibile (formato 2 di psxrecomp), o uno stato vuoto."""
    stato = {'quick_mods': {}, 'sources': {}, 'package': [], 'feature': []}
    if path.is_file():
        import tomllib
        d = tomllib.loads(path.read_text(encoding='utf-8'))
        if d.get('format_version') not in (1, 2):
            raise ValueError(T(f'{path}: formato {d.get("format_version")} non previsto',
                               f'{path}: unexpected format {d.get("format_version")}'))
        for k in ('quick_mods', 'sources'):
            stato[k] = dict(d.get(k, {}))
        stato['package'] = [dict(x) for x in d.get('package', [])]
        stato['feature'] = [dict(x) for x in d.get('feature', [])]
    return stato


def scrivi_stato_mod(path: Path, stato: dict) -> None:
    """Scrive mods/state.toml come lo scrive il runtime (ModPackageManager::save_state)."""
    r = ['format_version = 2']
    if stato['quick_mods']:
        r += ['', '[quick_mods]'] + [f'{_q(k)} = {"true" if v else "false"}' for k, v in stato['quick_mods'].items()]
    if stato['sources']:
        r += ['', '[sources]'] + [f'{_q(k)} = {_q(v)}' for k, v in stato['sources'].items()]
    for p in stato['package']:
        r += ['', '[[package]]', f'id = {_q(p["id"])}']
        if p.get('version'):
            r.append(f'version = {_q(p["version"])}')
        if 'enabled' in p:
            r.append(f'enabled = {"true" if p["enabled"] else "false"}')
        if p.get('values'):
            r += ['[package.values]'] + [f'{k} = {_q(v)}' for k, v in p['values'].items()]
    for f in stato['feature']:
        r += ['', '[[feature]]', f'package_id = {_q(f["package_id"])}', f'id = {_q(f["id"])}',
              f'enabled = {"true" if f.get("enabled") else "false"}']
        if f.get('values'):
            r += ['[feature.values]'] + [f'{k} = {_q(v if not isinstance(v, bool) else str(v).lower())}'
                                         for k, v in f['values'].items()]
        if f.get('resources'):
            r += ['[feature.resources]'] + [f'{k} = {_q(v)}' for k, v in f['resources'].items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('state.toml.tmp')
    tmp.write_text('\n'.join(r) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, path)


def risoluzione_iniziale(path: Path) -> str:
    """Installazione nuova: risoluzione interna "come il gioco" scritta in mods/state.toml, se non ce n'e' gia' una scelta.
    Il psxrecomp aggiornato (31/10/2026) sui profili nuovi parte da 4x, che sui PC deboli pesa: cosi' il punto di partenza
    resta quello della 0.11 (la risoluzione della PS1) e la si alza dalla finestra del launcher o dal menu del gioco."""
    try:
        stato = leggi_stato_mod(path)
    except (OSError, ValueError) as e:
        return T(f'avviso: {path} non letto ({e})', f'warning: {path} not read ({e})')
    if any((f.get('package_id'), f.get('id')) == MOD_RISOLUZIONE for f in stato['feature']):
        return ''
    imposta_mod(stato, MOD_RISOLUZIONE, False)
    scrivi_stato_mod(path, stato)
    return T(f'{path.parent.parent.name}\\mods\\state.toml: risoluzione interna come il gioco (si cambia con Gioca o opzioni)',
             f'{path.parent.parent.name}\\mods\\state.toml: internal resolution as in the game (change it with Play or options)')


def imposta_mod(stato: dict, mod: tuple, attiva: bool, valori: dict = None) -> None:
    pacchetto, funzione = mod
    voce = next((f for f in stato['feature'] if f.get('package_id') == pacchetto and f.get('id') == funzione), None)
    if voce is None:
        voce = {'package_id': pacchetto, 'id': funzione}
        stato['feature'].append(voce)
    voce['enabled'] = bool(attiva)
    if valori:
        voce.setdefault('values', {}).update(valori)


def descrivi_stato_mod(stato: dict) -> list:
    righe = []
    for f in stato['feature']:
        valori = ', '.join(f'{k}={v}' for k, v in (f.get('values') or {}).items())
        acceso = T('ACCESA', 'ON') if f.get('enabled') else T('spenta', 'off')
        righe.append(f'{f["package_id"]} / {f["id"]}: {acceso}' + (f' ({valori})' if valori else ''))
    return righe or [T('nessuna mod scelta (tutte come le ha il gioco)', 'no mod chosen (all as the game has them)')]


def cmd_opzioni(args) -> int:
    """Opzioni del giocatore che restano: le mod di psxrecomp in mods/state.toml accanto all'eseguibile.
    Le stesse si cambiano anche dal menu nel gioco o dalla finestra di recomp-ui."""
    prof = args.profilo
    cartella = Path(args.cartella) if args.cartella else GIOCHI / prof
    cartella = cartella if cartella.is_absolute() else (ROOT / cartella)
    apri_log(cartella / 'launcher_log.txt')
    dirs = [d for d in (cartella / 'build-release', cartella / 'build-dev') if trova_exe(d)]
    if not dirs:
        log(T(f'ERRORE: {prof} non e\' installato in {cartella}: usa prima "installa"',
              f'ERROR: {prof} is not installed in {cartella}: first use "install"'))
        return 1
    ha_distanza = (cartella / 'mods' / 'preloaded' / 'packages' / MOD_DISTANZA[0]).is_dir()
    ha_widescreen = (cartella / 'mods' / 'preloaded' / 'packages' / MOD_WIDESCREEN[0]).is_dir()
    if args.widescreen and args.widescreen != 'no' and not ha_widescreen:
        log(T('avviso: la mod "Widescreen" non c\'e\' in questa installazione (serve un\'installazione fatta '
              'con il launcher dalla v0.5): opzione ignorata',
              'warning: the "Widescreen" mod is not in this installation (an installation made with launcher 0.5 or '
              'later is needed): option ignored'))
    elif args.widescreen and args.widescreen != 'no':
        try:
            cambiato = aggiorna_toml_widescreen(cartella / 'game.toml')
        except OSError as e:
            cambiato = T(f'avviso: game.toml non aggiornato ({e})', f'warning: game.toml not updated ({e})')
        if cambiato:
            log(cambiato)
        try:
            inst = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            inst = {}
        if not inst.get('bordi_widescreen'):
            log(T('nota: questa installazione non ha ancora la correzione dei bordi del widescreen (launcher v0.8): '
                  'ai lati possono restare zone nere. Per averla, rifai "installa" (premi di nuovo Installa).',
                  'note: this installation does not have the widescreen edge fix yet (launcher 0.8): black areas may '
                  'remain at the sides. To get it, run "install" again (press Install again).'))
        elif not inst.get('gioco_widescreen'):
            log(T('nota: in questa installazione il widescreen allarga anche il giornale che compare quando una '
                  'missione fallisce, e la pagina si rovina (corretto dal launcher v0.9.1). Per la correzione, rifai '
                  '"installa" (premi di nuovo Installa).',
                  'note: in this installation the widescreen also widens the journal shown when a mission fails, and '
                  'the page gets garbled (fixed in launcher 0.9.1). For the fix, run "install" again (press Install '
                  'again).'))
        elif not inst.get('piani_widescreen'):
            log(T('nota: in questa installazione gli oggetti che stanno solo nelle parti in piu\' ai lati compaiono in '
                  'ritardo (corretto dal launcher v0.11). Per la correzione, rifai "installa" (premi di nuovo Installa).',
                  'note: in this installation objects that are only in the extra parts at the sides appear late '
                  '(fixed in launcher 0.11). For the fix, run "install" again (press Install again).'))
    if args.distanza == 'si' and not ha_distanza:
        log(T('avviso: la mod "Distanza visiva" non c\'e\' in questa installazione (serve un\'installazione fatta '
              'con il launcher dalla v0.6): opzione ignorata',
              'warning: the "Draw distance" mod is not in this installation (an installation made with launcher 0.6 '
              'or later is needed): option ignored'))
    elif args.distanza == 'si':
        try:
            inst = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            inst = {}
        if not inst.get('area_pacchetti'):
            log(T('nota: questa installazione usa ancora l\'area dei pacchetti originale (l\'area piu\' grande e\' '
                  'dalla v0.9): nei punti con piu\' poligoni il gioco puo\' lasciarne fuori qualcuno lontano. Per '
                  'averla, rifai "installa" (premi di nuovo Installa).',
                  'note: this installation still uses the original packet area (the larger area is from 0.9): where '
                  'there are more polygons the game may leave out some far ones. To get it, run "install" again '
                  '(press Install again).'))
    if args.attese:
        try:
            inst = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            inst = {}
        v = (inst.get('attese') or {}).get('v_wait')
        if args.attese == 'si' and not v:
            log(T('avviso: il salto delle attese non c\'e\' in questa installazione (serve un\'installazione fatta con il '
                  'launcher dalla v0.10, con psxrecomp corretto): opzione ignorata. Per averlo, rifai "installa" '
                  '(premi di nuovo Installa).',
                  'warning: idle skip is not in this installation (an installation made with launcher 0.10 or later, '
                  'with the fixed psxrecomp, is needed): option ignored. To get it, run "install" again (press Install '
                  'again).'))
        else:
            try:
                cambiato = imposta_attese(cartella / 'game.toml', int(v, 16) if args.attese == 'si' else None)
                if (cartella / 'installazione.json').is_file():
                    inst['salto_attese'] = attese_accese(cartella / 'game.toml')
                    (cartella / 'installazione.json').write_text(json.dumps(inst, indent=1, ensure_ascii=False),
                                                                 encoding='utf-8')
            except OSError as e:
                cambiato = T(f'avviso: game.toml non aggiornato ({e})', f'warning: game.toml not updated ({e})')
            if cambiato:
                log(cambiato)
    acceso = attese_accese(cartella / 'game.toml')
    log(T(f'salto delle attese: {"acceso" if acceso else "spento"} (game.toml)',
          f'idle skip: {"on" if acceso else "off"} (game.toml)'))
    for d in dirs:
        path = d / 'mods' / 'state.toml'
        try:
            stato = leggi_stato_mod(path)
        except (OSError, ValueError) as e:
            log(T(f'ERRORE: {e}', f'ERROR: {e}'))
            return 1
        if args.risoluzione:
            imposta_mod(stato, MOD_RISOLUZIONE, args.risoluzione != 'gioco',
                        None if args.risoluzione == 'gioco' else {'resolution': args.risoluzione})
        if args.pgxp:
            imposta_mod(stato, MOD_PGXP, args.pgxp == 'si')
            if ha_distanza:                  # PGXP anche per i poligoni suddivisi dal gioco
                imposta_mod(stato, MOD_SUDDIVISI, args.pgxp == 'si')
        if args.distanza and ha_distanza:
            imposta_mod(stato, MOD_DISTANZA, args.distanza == 'si')
        if args.filtro_texture or args.scaling:
            vals = {}
            if args.filtro_texture:
                vals['texture_filtering'] = 'default' if args.filtro_texture == 'gioco' else args.filtro_texture
            if args.scaling:
                vals['smoothing'] = 'default' if args.scaling == 'gioco' else args.scaling
            voce = next((f for f in stato['feature'] if (f.get('package_id'), f.get('id')) == MOD_FILTRI), {})
            tutti = dict(voce.get('values') or {}, **vals)
            imposta_mod(stato, MOD_FILTRI, any(v != 'default' for v in tutti.values()), vals)
        if args.crt:
            imposta_mod(stato, MOD_CRT, args.crt == 'si')
        if args.audio_hq:
            imposta_mod(stato, MOD_AUDIO, args.audio_hq == 'si')
        usa_widescreen = args.widescreen and (ha_widescreen or args.widescreen == 'no')
        if usa_widescreen:
            imposta_mod(stato, MOD_WIDESCREEN, args.widescreen != 'no',
                        None if args.widescreen == 'no' else {'aspect': args.widescreen})
        cambia = any((args.risoluzione, args.pgxp, args.filtro_texture, args.scaling, args.crt, args.audio_hq,
                      usa_widescreen, args.distanza and ha_distanza))
        if cambia:
            scrivi_stato_mod(path, stato)
        log(f'{d.name}\\mods\\state.toml' + (T(' aggiornato:', ' updated:') if cambia else ':'))
        for r in descrivi_stato_mod(stato):
            log('  ' + r)
        video = {}
        if args.sincronia:
            video['vsync'] = SINCRONIA[args.sincronia]
        if args.thread_video:
            video['render_thread'] = args.thread_video == 'si'
        if args.schermo:
            video['fullscreen'] = SCHERMO[args.schermo]
        if args.larghezza_finestra:
            video['window_width'] = max(640, min(7680, args.larghezza_finestra))
        if args.latenza_bassa:
            video['low_latency_input'] = args.latenza_bassa == 'si'
        if args.movimento_fluido:
            video['frame_generation'] = args.movimento_fluido == 'si'
            if args.movimento_fluido == 'si':
                video['render_thread'] = True      # il movimento fluido lavora nel thread video
        if args.motore:
            try:
                ha_vulkan = bool(json.loads((cartella / 'installazione.json').read_text(encoding='utf-8')).get('vulkan'))
            except (OSError, ValueError):
                ha_vulkan = False
            if args.motore == 'vulkan' and not ha_vulkan:
                if d == dirs[0]:
                    log(T('avviso: questa installazione non ha il motore grafico Vulkan (servono gli strumenti di '
                          'tools\\scarica_vulkan.cmd e una nuova installazione): resta OpenGL',
                          'warning: this installation does not have the Vulkan renderer (the tools of '
                          'tools\\scarica_vulkan.cmd and a new installation are needed): OpenGL stays'))
                video['renderer'] = 'opengl'
            else:
                video['renderer'] = args.motore
        if video:
            try:
                scrivi_video(d / 'settings.toml', video)
            except OSError as e:
                log(T(f'ERRORE: {d.name}\\settings.toml non scritto ({e})', f'ERROR: {d.name}\\settings.toml not written ({e})'))
                return 1
        log(f'{d.name}\\settings.toml' + (T(' aggiornato: ', ' updated: ') if video else ': ') +
            descrivi_video(leggi_video(d / 'settings.toml')))
    return 0


# ---------------------------------------------------------------------------------------------- stato

def cmd_stato(args) -> int:
    cat = catalogo()
    cache = CacheHash(GIOCHI / 'cache_hash.json')
    log(f'SM2-Recomp launcher {VERSIONE} - {ROOT}')
    log(attiva_toolchain())
    log(dipendenze_offline())
    for prof, v in cat.items():
        disco = disco_della_versione(prof, cache, cat)
        cartella = GIOCHI / prof
        try:
            st = json.loads((cartella / 'installazione.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            st = None
        inst = T('non installata', 'not installed')
        if st:
            exe = trova_exe(cartella / 'build-release')
            m3 = st.get('m3') or {}
            inst = ((T('installata', 'installed') if st.get('completata') and exe
                     else T('installazione incompleta', 'incomplete installation')) +
                    (T(f', {m3.get("basi")} basi di {m3.get("moduli")} moduli in anticipo',
                       f', {m3.get("basi")} bases of {m3.get("moduli")} precompiled modules') if m3.get('attiva') else '') +
                    (', PGXP' if st.get('pgxp') else '') +
                    (T(', mod Distanza visiva', ', Draw distance mod') if st.get('distanza') else '') +
                    ((T(', mod Widescreen', ', Widescreen mod') +
                      (T(' (allarga solo mentre si gioca)', ' (widens only during gameplay)')
                       if st.get('gioco_widescreen') else '')) if st.get('bordi_widescreen') else '') +
                    (', PGO' if st.get('pgo') else '') +
                    (T(', salto delle attese', ', idle skip') if attese_accese(cartella / 'game.toml') else ''))
        nome = nome_versione(prof, v['nome'])
        log(f'{prof:<16} {nome:<45} ' + T(f'disco: {"si" if disco else "no":<3} ', f'disc: {"yes" if disco else "no":<3} ') + inst)
    cache.salva()
    return 0


# ----------------------------------------------------------------------------------------------- menu

def menu() -> int:
    while True:
        print(T('\nSM2-Recomp - launcher (prototipo)\n'
                '  1) riconosci i dischi in input\\\n'
                '  2) importa un dump (scrivi o trascina qui il percorso del .cue/.ccd/.bin)\n'
                '  3) installa una versione\n'
                '  4) gioca\n'
                '  5) stato\n'
                '  0) esci',
                '\nSM2-Recomp - launcher (prototype)\n'
                '  1) identify the discs in input\\\n'
                '  2) import a dump (type or drag here the path of the .cue/.ccd/.bin)\n'
                '  3) install a version\n'
                '  4) play\n'
                '  5) status\n'
                '  0) exit'))
        try:
            scelta = input(T('scelta: ', 'choice: ')).strip()
        except EOFError:
            return 0
        if scelta == '0':
            return 0
        if scelta == '1':
            main(['riconosci'])
        elif scelta == '2':
            p = input(T('percorso: ', 'path: ')).strip().strip('"')
            if p:
                main(['importa', p])
        elif scelta in ('3', '4'):
            cat = catalogo()
            nomi = list(cat)
            for i, p in enumerate(nomi, 1):
                print(f'  {i}) {p} - {nome_versione(p, cat[p]["nome"])}')
            try:
                prof = nomi[int(input(T('versione: ', 'version: ')).strip()) - 1]
            except (ValueError, IndexError):
                continue
            if scelta == '3':
                main(['installa', '--profilo', prof])
            else:
                r = input(T('risoluzione interna (Invio = nativa, oppure 720p, 1080p, 1440p, 4k): ',
                            'internal resolution (Enter = native, or 720p, 1080p, 1440p, 4k): ')).strip()
                main(['avvia', '--profilo', prof] + (['--risoluzione', r] if r in RISOLUZIONI else []))
        elif scelta == '5':
            main(['stato'])


# Nomi inglesi di comandi, opzioni e valori (4/11/2026): quelli italiani restano validi; dopo la lettura degli argomenti
# i valori inglesi diventano quelli italiani, che usa il resto del programma.
# English names of commands, options and values (4 Nov 2026); the Italian ones keep working.
ALIAS_COMANDI = {'identify': 'riconosci', 'import': 'importa', 'install': 'installa', 'play': 'avvia',
                 'options': 'opzioni', 'status': 'stato', 'text': 'testo', 'prepare-recording': 'prepara-registrazione'}
VALORI_EN = {'yes': 'si', 'game': 'gioco', 'on': 'accesa', 'off': 'spenta', 'adaptive': 'adattiva',
             'window': 'finestra', 'borderless': 'senza-bordi', 'exclusive': 'esclusivo', 'half': 'meta', 'all': 'tutti',
             'prepare': 'prepara', 'generate': 'genera', 'compile': 'compila'}
PASSI_EN = {'prepara': 'prepare', 'm3': 'm3', 'genera': 'generate', 'compila': 'compile'}
CON_VALORI = ('risoluzione', 'pgxp', 'filtro_texture', 'scaling', 'crt', 'audio_hq', 'distanza', 'attese', 'sincronia',
              'thread_video', 'schermo', 'latenza_bassa', 'movimento_fluido', 'cpu', 'motore', 'widescreen')


def con_inglese(*valori) -> tuple:
    """Le scelte di un'opzione con in piu' i loro nomi inglesi (yes, game, on, off...)."""
    inglesi = {v: k for k, v in VALORI_EN.items()}
    return tuple(valori) + tuple(inglesi[v] for v in valori if v in inglesi)


def lingua_da_argomenti(argv: list) -> list:
    """--lingua / --language it|en in qualsiasi punto della riga di comando: sceglie la lingua (prima di preparare i
    testi dell'aiuto) e la toglie dagli argomenti."""
    resto, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a in ('--lingua', '--language') and i + 1 < len(argv):
            imposta_lingua(argv[i + 1])
            i += 2
            continue
        if a.startswith(('--lingua=', '--language=')):
            imposta_lingua(a.split('=', 1)[1])
            i += 1
            continue
        resto.append(a)
        i += 1
    return resto


def main(argv=None) -> int:
    argv = lingua_da_argomenti(list(sys.argv[1:] if argv is None else argv))
    SI_NO = con_inglese('si', 'no')
    ap = argparse.ArgumentParser(description=T('SM2-Recomp launcher (prototipo)', 'SM2-Recomp launcher (prototype)'),
                                 epilog=T('Lingua: --lingua it|en (anche --language). I comandi hanno anche i nomi '
                                          'inglesi: identify, import, install, play, options, status, gui, text.',
                                          'Language: --language it|en (also --lingua). The commands also have Italian '
                                          'names: riconosci, importa, installa, avvia, opzioni, stato, gui, testo.'))
    sub = ap.add_subparsers(dest='comando')
    p = sub.add_parser('riconosci', aliases=['identify'], help=T('riconosce i dump', 'identifies the dumps'))
    p.add_argument('percorsi', nargs='*', metavar=T('PERCORSO', 'PATH'))
    p.add_argument('--soglia-mb', type=int, default=SOGLIA_SCIOLTI_MB, help=argparse.SUPPRESS)
    p.add_argument('--json', default='', metavar='FILE', help=T('scrive anche i risultati in questo file JSON',
                                                'also writes the results to this JSON file'))
    p.set_defaults(fn=cmd_riconosci)
    p = sub.add_parser('importa', aliases=['import'],
                       help=T('riconosce i dump e li sposta in input/<PROFILO>/',
                              'identifies the dumps and moves them to input/<PROFILE>/'))
    p.add_argument('percorsi', nargs='+', metavar=T('PERCORSO', 'PATH'))
    p.add_argument('--copia', '--copy', action='store_true', help=T('copia invece di spostare', 'copy instead of moving'))
    p.add_argument('--soglia-mb', type=int, default=SOGLIA_SCIOLTI_MB, help=argparse.SUPPRESS)
    p.set_defaults(fn=cmd_importa)
    p = sub.add_parser('installa', aliases=['install'],
                       help=T('prepara e compila una versione dal disco dell\'utente',
                              'prepares and builds a version from the user\'s disc'))
    p.add_argument('--profilo', '--profile', required=True, metavar=T('PROFILO', 'PROFILE'))
    p.add_argument('--disco', '--disc', default='', metavar=T('FOGLIO_CUE', 'CUE_SHEET'),
                   help=T('foglio .cue da usare (di default quello in input/<PROFILO>/)',
                          '.cue sheet to use (by default the one in input/<PROFILE>/)'))
    p.add_argument('--cartella', '--folder', default='', metavar=T('CARTELLA', 'FOLDER'),
                   help=T('cartella dell\'installazione (di default giochi/<PROFILO>)',
                          'installation folder (by default giochi/<PROFILE>)'))
    p.add_argument('--debug', action='store_true',
                   help=T('compila anche build-dev, con il server di debug', 'also builds build-dev, with the debug server'))
    p.add_argument('--core', type=int, default=0, metavar='N',
                   help=T('core per compilare (di default tre quarti dei processori logici)',
                          'cores for compiling (by default three quarters of the logical processors)'))
    p.add_argument('--senza-m3', '--no-m3', action='store_true',
                   help=T('niente moduli compilati in anticipo', 'no precompiled modules'))
    p.add_argument('--pgxp', action='store_true',
                   help=T('eseguibile con i punti di aggancio di PGXP (geometria piu\' precisa, da accendere con avvia --pgxp)',
                          'executable with the PGXP hooks (more precise geometry, turn it on with play --pgxp)'))
    p.add_argument('--pgo', action='store_true',
                   help=T('eseguibile ottimizzato con il PGO (partita di allenamento di circa 3 minuti, poi una '
                          'compilazione in piu\'): circa il 15%% di CPU in meno',
                          'executable optimized with PGO (a training game of about 3 minutes, then one more build): '
                          'about 15%% less CPU'))
    p.add_argument('--attese', '--idle-skip', choices=SI_NO, default='si',
                   help=T('salto delle attese di psxrecomp nel game.toml (di default si; il gioco resta identico)',
                          'psxrecomp idle skip in game.toml (yes by default; the game stays identical)'))
    p.add_argument('--passi', '--steps', nargs='+', default=['prepara', 'm3', 'genera', 'compila'],
                   choices=con_inglese('prepara', 'm3', 'genera', 'compila'))
    p.add_argument('--registratore', '--recorder', action='store_true',
                   help=T('QA: installazione di prova con il registratore delle partite di psxrecomp (usare una --cartella '
                          'diversa da quella normale)',
                          'QA: test installation with the psxrecomp game recorder (use a --folder different from the '
                          'normal one)'))
    p.set_defaults(fn=cmd_installa)
    p = sub.add_parser('avvia', aliases=['play'], help=T('avvia il gioco installato', 'starts the installed game'))
    p.add_argument('--profilo', '--profile', required=True, metavar=T('PROFILO', 'PROFILE'))
    p.add_argument('--cartella', '--folder', default='', metavar=T('CARTELLA', 'FOLDER'))
    p.add_argument('--risoluzione', '--resolution', choices=RISOLUZIONI, default='')
    p.add_argument('--con-launcher', '--with-launcher', action='store_true',
                   help=T('prima la finestra delle impostazioni di psxrecomp', 'first the psxrecomp settings window'))
    p.add_argument('--pgxp', action='store_true',
                   help=T('accende PGXP (geometria e texture piu\' precise)', 'turns on PGXP (more precise geometry and textures)'))
    p.add_argument('--debug', action='store_true',
                   help=T('usa build-dev invece di build-release', 'uses build-dev instead of build-release'))
    p.add_argument('--cpu', choices=con_inglese('meta', 'tutti'), default='tutti')
    p.add_argument('--prova', '--test', type=int, default=0, metavar=T('SECONDI', 'SECONDS'),
                   help=T('prova: tiene il gioco aperto N secondi, poi lo chiude',
                          'test: keeps the game open N seconds, then closes it'))
    p.set_defaults(fn=cmd_avvia)
    p = sub.add_parser('prepara-registrazione', aliases=['prepare-recording'],
                       help=T('QA: prepara un\'installazione con il registratore (cache del codice compilato al volo), '
                              'cosi\' anche la prima partita registrata si rigioca in modo esatto',
                              'QA: prepares an installation with the recorder (cache of the code compiled on the fly), '
                              'so that the first recorded game also replays exactly'))
    p.add_argument('--profilo', '--profile', required=True, metavar=T('PROFILO', 'PROFILE'))
    p.add_argument('--cartella', '--folder', default='', metavar=T('CARTELLA', 'FOLDER'),
                   help=T('di default work/registra/<PROFILO>', 'by default work/registra/<PROFILE>'))
    p.add_argument('--debug', action='store_true',
                   help=T('build-dev invece di build-release', 'build-dev instead of build-release'))
    p.set_defaults(fn=cmd_prepara_registrazione)
    p = sub.add_parser('opzioni', aliases=['options'],
                       help=T('opzioni del giocatore che restano (mod di psxrecomp in mods/state.toml)',
                              'player options that are kept (psxrecomp mods in mods/state.toml)'))
    p.add_argument('--profilo', '--profile', required=True, metavar=T('PROFILO', 'PROFILE'))
    p.add_argument('--cartella', '--folder', default='', metavar=T('CARTELLA', 'FOLDER'))
    p.add_argument('--risoluzione', '--resolution',
                   choices=con_inglese('gioco', 'native', '720p', '1080p', '1440p', '4k', '5k', '8k', 'display', 'auto'))
    p.add_argument('--pgxp', choices=SI_NO)
    p.add_argument('--filtro-texture', '--texture-filter', choices=con_inglese('gioco', 'nearest', 'bilinear', 'xbr'))
    p.add_argument('--scaling', choices=con_inglese('gioco', 'smooth', 'sharp'))
    p.add_argument('--crt', choices=SI_NO)
    p.add_argument('--audio-hq', choices=SI_NO)
    p.add_argument('--widescreen', choices=('no', '16:9', '16:10', '21:9'),
                   help=T('mod Widescreen di SM2-Recomp (sperimentale; serve un\'installazione dalla v0.5)',
                          'SM2-Recomp Widescreen mod (experimental; needs an installation from 0.5 on)'))
    p.add_argument('--distanza', '--draw-distance', choices=SI_NO,
                   help=T('mod "Distanza visiva" di SM2-Recomp (sperimentale; serve un\'installazione dalla v0.6)',
                          'SM2-Recomp "Draw distance" mod (experimental; needs an installation from 0.6 on)'))
    p.add_argument('--attese', '--idle-skip', choices=SI_NO,
                   help=T('salto delle attese di psxrecomp (meno lavoro per la CPU; serve un\'installazione dalla v0.10)',
                          'psxrecomp idle skip (less CPU work; needs an installation from 0.10 on)'))
    p.add_argument('--sincronia', '--vsync', choices=con_inglese(*SINCRONIA),
                   help=T('sincronia verticale (settings.toml [video] vsync): adattiva o spenta aiutano i PC lenti',
                          'vertical sync (settings.toml [video] vsync): adaptive or off help slow PCs'))
    p.add_argument('--thread-video', '--render-thread', choices=SI_NO,
                   help=T('disegno in un thread separato (settings.toml [video] render_thread)',
                          'drawing in a separate thread (settings.toml [video] render_thread)'))
    p.add_argument('--schermo', '--screen', choices=con_inglese(*SCHERMO),
                   help=T('finestra o schermo intero (settings.toml [video] fullscreen)',
                          'window or fullscreen (settings.toml [video] fullscreen)'))
    p.add_argument('--larghezza-finestra', '--window-width', type=int, default=0, metavar='PIXEL',
                   help=T('larghezza della finestra in pixel (640-7680)', 'window width in pixels (640-7680)'))
    p.add_argument('--latenza-bassa', '--low-latency', choices=SI_NO,
                   help=T('input a bassa latenza (settings.toml [video] low_latency_input)',
                          'low-latency input (settings.toml [video] low_latency_input)'))
    p.add_argument('--motore', '--renderer', choices=('opengl', 'vulkan'),
                   help=T('motore grafico (settings.toml [video] renderer): vulkan e\' sperimentale e serve un\'installazione con Vulkan',
                          'renderer (settings.toml [video] renderer): vulkan is experimental and needs an installation with Vulkan'))
    p.add_argument('--movimento-fluido', '--smooth-motion', choices=SI_NO,
                   help=T('immagini intermedie per schermi a 120 Hz o piu\' (sperimentale; settings.toml [video] frame_generation)',
                          'in-between frames for 120 Hz or faster screens (experimental; settings.toml [video] frame_generation)'))
    p.set_defaults(fn=cmd_opzioni)
    p = sub.add_parser('stato', aliases=['status'],
                       help=T('versioni conosciute, dischi e installazioni', 'known versions, discs and installations'))
    p.set_defaults(fn=cmd_stato)
    p = sub.add_parser('gui', help=T('la finestra del launcher (anche senza comandi)', 'the launcher window (also with no command)'))
    p.add_argument('--autotest', default='', metavar=T('CARTELLA', 'FOLDER'),
                   help=T('prova automatica della finestra: registro e immagini in questa cartella',
                          'automatic test of the window: log and pictures in this folder'))
    p = sub.add_parser('testo', aliases=['text'], help=T('il menu di testo, senza finestra', 'the text menu, without a window'))
    args = ap.parse_args(argv)
    args.comando = ALIAS_COMANDI.get(args.comando, args.comando)
    for nome in CON_VALORI:
        v = getattr(args, nome, None)
        if isinstance(v, str) and v in VALORI_EN:
            setattr(args, nome, VALORI_EN[v])
    if isinstance(getattr(args, 'passi', None), list):
        args.passi = [VALORI_EN.get(x, x) for x in args.passi]
    for flusso in (sys.stdout, sys.stderr):
        try:
            flusso.reconfigure(errors='replace')     # percorsi con lettere accentate in una console Windows
        except (AttributeError, ValueError):
            pass
    if not args.comando or args.comando == 'gui':
        try:
            import sm2_launcher_gui
        except Exception as e:  # noqa: BLE001  (tkinter assente: menu di testo)
            print(T(f'finestra non disponibile ({e}): menu di testo', f'window not available ({e}): text menu'))
            return menu()
        return sm2_launcher_gui.main(['--autotest', args.autotest] if getattr(args, 'autotest', '') else [])
    if args.comando == 'testo':
        return menu()
    if args.comando in ('riconosci', 'importa', 'stato') and _log_f is None:
        apri_log(GIOCHI / 'launcher_log.txt')
    return args.fn(args)


if __name__ == '__main__':
    raise SystemExit(main())
