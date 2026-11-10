# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - memory card e salvataggi rapidi di un'installazione (dal 4/11/2026).
EnterElectro-Recomp 0.12 - memory cards and save states of an installation.

Dove sono: il game.toml dell'installazione dice [runtime] memcard_dir = "saves", relativo alla cartella del gioco
(giochi/<PROFILO>), quindi le memory card sono giochi/<PROFILO>/saves/card1.mcd e card2.mcd, a meno che settings.toml
accanto all'eseguibile non dica altro ([memcard] dir, card1, card2). I salvataggi rapidi (F7) di psxrecomp sono in
<cartella delle memory card>/<openbios|scph1001>/state_<...>_slotNN.pst, con l'anteprima 128x96 in .thumb ("PSTH",
larghezza, altezza, poi i pixel ARGB a 32 bit; psxrecomp/runtime/src/savestate.c).

Memory card della PS1: 128 KB, 16 blocchi da 8 KB. Il blocco 0 ha "MC" e 15 voci di elenco da 128 byte (stato del
blocco, dimensione, blocco seguente, nome del file come BASLUS-01378...); il primo blocco di ogni salvataggio comincia
con "SC", il numero di immagini dell'icona e il titolo in Shift-JIS, poi la tavolozza dell'icona (16 colori a 15 bit) e
l'icona 16x16 a 4 bit.

Le copie di sicurezza vanno in <cartella delle memory card>/copie/; un ripristino fa prima una copia della memory card
di adesso. Niente si cancella.
"""
from __future__ import annotations

import datetime
import re
import shutil
import struct
import unicodedata
from pathlib import Path

try:
    from sm2_lingua import T
except ImportError:                     # usato da solo, fuori da tools\\
    def T(it: str, en: str) -> str:
        return it

DIMENSIONE_CARD = 131072
BLOCCO = 8192
ESTENSIONI_CARD = ('.mcd', '.mcr', '.mc', '.srm', '.ps', '.ddf', '.mem', '.gme')


def _toml_semplice(path: Path) -> dict:
    """{sezione: {chiave: valore}} con valori stringa o numero; abbastanza per settings.toml e game.toml."""
    out, sez = {}, ''
    try:
        righe = path.read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return out
    for r in righe:
        s = r.strip()
        if s.startswith('[') and s.endswith(']'):
            sez = s[1:-1].strip()
            continue
        if '=' in s and not s.startswith('#'):
            k, v = s.split('=', 1)
            v = v.split('#', 1)[0].strip() if not v.strip().startswith('"') else v.strip()
            if v.startswith('"'):
                m = re.match(r'"((?:[^"\\]|\\.)*)"', v)
                v = m.group(1).replace('\\\\', '\\') if m else v.strip('"')
            out.setdefault(sez, {})[k.strip()] = v
    return out


def cartella_memory_card(cartella: Path) -> Path:
    """La cartella delle memory card di un'installazione (giochi/<PROFILO>)."""
    for b in ('build-release', 'build-dev'):
        st = _toml_semplice(cartella / b / 'settings.toml').get('memcard', {})
        if st.get('dir'):
            p = Path(st['dir'])
            return p if p.is_absolute() else (cartella / b / p)
    g = _toml_semplice(cartella / 'game.toml').get('runtime', {})
    return cartella / g.get('memcard_dir', 'saves')


def percorsi_memory_card(cartella: Path) -> list:
    """[card1, card2] (anche se non ci sono ancora)."""
    base = cartella_memory_card(cartella)
    out = [base / 'card1.mcd', base / 'card2.mcd']
    for b in ('build-release', 'build-dev'):
        st = _toml_semplice(cartella / b / 'settings.toml').get('memcard', {})
        for i, k in enumerate(('card1', 'card2')):
            if st.get(k):
                p = Path(st[k])
                out[i] = p if p.is_absolute() else (cartella / b / p)
        if st:
            break
    return out


def _dati_card(path: Path) -> bytes | None:
    """I 128 KB della memory card: file .mcd/.mcr grezzi oppure .gme di DexDrive (3904 byte di intestazione)."""
    try:
        b = path.read_bytes()
    except OSError:
        return None
    if len(b) == DIMENSIONE_CARD:
        return b
    if len(b) == DIMENSIONE_CARD + 3904 and b[:11] == b'123-456-STD':
        return b[3904:]
    return None


def titolo(b: bytes) -> str:
    """Il titolo Shift-JIS di un salvataggio in caratteri normali (le lettere larghe giapponesi diventano normali)."""
    b = b.split(b'\x00', 1)[0]
    try:
        t = b.decode('cp932', errors='replace')          # Shift-JIS come lo scrivono i giochi (con le estensioni)
    except LookupError:
        t = b.decode('latin-1', errors='replace')
    t = unicodedata.normalize('NFKC', t)
    t = re.sub(r'(?<=[A-Za-z0-9])\u30fc(?=[A-Za-z0-9])', '-', t)   # "SPIDER\u30fcMAN": il trattino largo dei titoli
    return re.sub(r'\s+', ' ', t).strip()


def _icona(blocco: bytes) -> list:
    """L'icona 16x16 della prima immagine come righe di byte RGB (tavolozza a 15 bit, colore 0 trasparente = nero)."""
    tav = []
    for i in range(16):
        c = struct.unpack_from('<H', blocco, 96 + 2 * i)[0]
        r, g, bl = (c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31
        tav.append(bytes((r, g, bl)))
    righe = []
    for y in range(16):
        riga = bytearray()
        for x in range(16):
            v = blocco[128 + y * 8 + x // 2]
            riga += tav[(v >> 4) if x & 1 else (v & 15)]
        righe.append(bytes(riga))
    return righe


def leggi_memory_card(path: Path) -> dict:
    """{'ok', 'motivo', 'salvataggi': [{blocco, blocchi, file, codice, titolo, icona}], 'liberi'}."""
    b = _dati_card(path)
    if b is None:
        return {'ok': False, 'motivo': 'manca' if not path.is_file() else 'formato', 'salvataggi': [], 'liberi': 0}
    if b[:2] != b'MC':
        return {'ok': False, 'motivo': 'non formattata', 'salvataggi': [], 'liberi': 0}
    voci = [b[128 * i:128 * (i + 1)] for i in range(1, 16)]
    salvataggi, liberi = [], 0
    for i, v in enumerate(voci, 1):
        stato = struct.unpack_from('<I', v, 0)[0]
        if stato & 0xF0 == 0xA0 or stato == 0:
            liberi += 1
            continue
        if stato != 0x51:
            continue                                     # blocco di mezzo o finale: conta con il primo
        dim = struct.unpack_from('<I', v, 4)[0]
        nome = v[10:30].split(b'\x00', 1)[0].decode('ascii', errors='replace')
        blocchi = 1
        succ = struct.unpack_from('<H', v, 8)[0]
        visti = {i}
        while succ != 0xFFFF and 0 <= succ < 15 and succ + 1 not in visti:
            visti.add(succ + 1)
            blocchi += 1
            succ = struct.unpack_from('<H', voci[succ], 8)[0]
        primo = b[BLOCCO * i:BLOCCO * (i + 1)]
        t = titolo(primo[4:68]) if primo[:2] == b'SC' else ''
        m = re.match(r'^B[AIE]([A-Z]{4})-?(\d{5})', nome)
        salvataggi.append({'blocco': i, 'blocchi': max(blocchi, (dim + BLOCCO - 1) // BLOCCO if dim else 1),
                           'file': nome, 'codice': f'{m.group(1)}-{m.group(2)}' if m else '',
                           'regione': {'A': 'USA', 'E': 'Europa', 'I': 'Giappone'}.get(nome[1:2], '') if nome[:1] == 'B'
                           else '', 'titolo': t, 'icona': _icona(primo) if primo[:2] == b'SC' else None})
    return {'ok': True, 'motivo': '', 'salvataggi': salvataggi, 'liberi': liberi}


def copia_di_sicurezza(card: Path) -> Path | None:
    """Copia la memory card in <cartella>/copie/<nome>_<data>.mcd; None se non c'e'."""
    if not card.is_file():
        return None
    dest = card.parent / 'copie' / f'{card.stem}_{datetime.datetime.now():%Y%m%d_%H%M%S}{card.suffix}'
    dest.parent.mkdir(parents=True, exist_ok=True)
    n = 1
    while dest.exists():
        dest = dest.with_name(f'{card.stem}_{datetime.datetime.now():%Y%m%d_%H%M%S}_{n}{card.suffix}')
        n += 1
    shutil.copy2(card, dest)
    return dest


def copie_di_sicurezza(card: Path) -> list:
    """Le copie di quella memory card, dalla piu' recente."""
    d = card.parent / 'copie'
    if not d.is_dir():
        return []
    return sorted(d.glob(f'{card.stem}_*{card.suffix}'), key=lambda p: p.stat().st_mtime, reverse=True)


def ripristina(card: Path, da: Path) -> Path | None:
    """Mette nella memory card il contenuto di un'altra (copia di sicurezza o file importato, anche .gme), dopo una
    copia di quella di adesso. Restituisce la copia fatta (None se la card non c'era). Errore se da non e' valida."""
    dati = _dati_card(da)
    if dati is None or dati[:2] != b'MC':
        raise ValueError(f'{da.name}: non e\' una memory card della PS1 (128 KB, "MC")')
    copia = copia_di_sicurezza(card)
    card.parent.mkdir(parents=True, exist_ok=True)
    tmp = card.with_name(card.name + '.nuova')
    tmp.write_bytes(dati)
    tmp.replace(card)
    return copia


# Salvataggi di Spider-Man 2 tra versioni diverse (5/11/2026). Ogni versione tiene le sue partite in un solo file della
# memory card (un blocco), con fino a 8 partite salvate da 180 byte ciascuna a partire da 0x200 del blocco; il nome del
# file e' il codice della versione (visto nelle memory card delle prove automatiche di tutte e sette le versioni). Le due
# USA hanno lo stesso nome, e anche le due europee in inglese: tra loro le partite valgono gia'.
# Nelle partite il byte 0xA0 e' l'altezza dello schermo tolta in basso: 18 (0x12) nelle versioni europee (PAL), 0 nelle
# altre. Lasciato com'e', la USA con una partita europea mostra 222 righe invece di 240 (prova del 5/11/2026), quindi la
# copia lo sposta di quanto cambiano i valori di partenza delle due versioni e corregge l'impronta della partita (i primi
# 4 byte), che per quel byte cresce di 16 per unita': la USA Rev 1 carica la partita cosi' corretta (lavoro 33).
SCHERMO_SALVATAGGIO = {'SLES-03623': 18, 'SLES-03623-Rev1': 18, 'SLES-03624': 18, 'SLES-03625': 18}
NOME_SALVATAGGIO = {'SLUS-01378-Rev1': 'BASLUS-01378', 'SLUS-01378': 'BASLUS-01378',
                    'SLES-03623': 'BESLES-03623', 'SLES-03623-Rev1': 'BESLES-03623',
                    'SLES-03624': 'BESLES-03624', 'SLES-03625': 'BESLES-03625', 'SLPM-87073': 'BISLPM-87073SPD'}


class ErroreDestinazione(ValueError):
    """La memory card di arrivo non va bene (non e' una memory card, ha gia' quel salvataggio, e' piena): si puo'
    provare con l'altra."""


def _xor(b: bytes) -> int:
    x = 0
    for c in b[:127]:
        x ^= c
    return x


def card_vuota() -> bytes:
    """Una memory card formattata e vuota, come la fa psxrecomp (memcard_format in runtime/src/memcard.c)."""
    d = bytearray(b'\xff' * DIMENSIONE_CARD)
    d[0:128] = bytes(128)
    d[0:2] = b'MC'
    d[127] = _xor(d[0:128])
    for s in range(1, 16):
        f = bytearray(128)
        f[0], f[8], f[9] = 0xA0, 0xFF, 0xFF
        f[127] = _xor(f)
        d[128 * s:128 * (s + 1)] = f
    for s in range(16, 36):
        f = bytearray(128)
        f[0:4] = b'\xff\xff\xff\xff'
        f[8], f[9] = 0xFF, 0xFF
        f[127] = _xor(f)
        d[128 * s:128 * (s + 1)] = f
    for s in range(36, 63):
        d[128 * s:128 * (s + 1)] = bytes(128)
    d[63 * 128:64 * 128] = d[0:128]
    return bytes(d)


def _voce_salvataggio(dati: bytes, nome: str) -> int | None:
    """Il numero del blocco (1-15) del salvataggio con quel nome di file, o None."""
    for i in range(1, 16):
        v = dati[128 * i:128 * (i + 1)]
        if struct.unpack_from('<I', v, 0)[0] == 0x51 and v[10:30].split(b'\x00', 1)[0] == nome.encode('ascii'):
            return i
    return None


def ha_partite(card: Path, prof: str) -> bool:
    """Nella memory card c'e' il file delle partite di Spider-Man 2 di quella versione?"""
    d = _dati_card(card)
    return bool(d and d[:2] == b'MC' and prof in NOME_SALVATAGGIO and
                _voce_salvataggio(d, NOME_SALVATAGGIO[prof]) is not None)


def _sposta_schermo(blocco: bytearray, delta: int) -> list:
    """Byte 0xA0 di ogni partita del blocco spostato di delta (tra 0 e 255), con l'impronta corretta (+16 per unita').
    [(posto, prima, dopo)]."""
    fatti = []
    for k in range(8):
        a = 0x200 + 180 * k
        s = blocco[a:a + 180]
        if not any(s) or not delta:
            continue
        prima = s[0xA0]
        dopo = max(0, min(255, prima + delta))
        if dopo == prima:
            continue
        imp = (struct.unpack_from('<I', s, 0)[0] + 16 * (dopo - prima)) & 0xFFFFFFFF
        struct.pack_into('<I', blocco, a, imp)
        blocco[a + 0xA0] = dopo
        fatti.append((k, prima, dopo))
    return fatti


def partite_salvate(dati: bytes, blocco: int) -> list:
    """Le partite nel blocco di Spider-Man 2: [{posto, livello, nome}] (posto da 0 a 7)."""
    b = dati[BLOCCO * blocco:BLOCCO * (blocco + 1)]
    out = []
    for k in range(8):
        s = b[0x200 + 180 * k:0x200 + 180 * (k + 1)]
        if any(s):
            out.append({'posto': k, 'livello': s[4:20].split(b'\x00', 1)[0].decode('ascii', 'replace'),
                        'nome': s[0x3F:0x48].split(b'\x00', 1)[0].decode('ascii', 'replace')})
    return out


def copia_in_versione(da: Path, prof_da: str, a: Path, prof_a: str, prova: bool = False) -> dict:
    """Copia il file delle partite di Spider-Man 2 della versione prof_da (memory card da) nella memory card a, con il
    nome della versione prof_a. Le partite restano uguali, tranne l'altezza dello schermo tra versioni europee e no
    (byte 0xA0, vedi SCHERMO_SALVATAGGIO) e la loro impronta. Se a non c'e' la crea vuota; se c'e', prima ne fa una copia di sicurezza. ValueError se nella card da
    non c'e' il salvataggio di prof_da, se le due versioni usano lo stesso nome o se nella card a c'e' gia' un salvataggio
    di prof_a (le partite non si mescolano: va usata l'altra memory card) o non c'e' un blocco libero.
    Restituisce {blocco, nome, partite, copia}."""
    if prof_da not in NOME_SALVATAGGIO or prof_a not in NOME_SALVATAGGIO:
        x = prof_da if prof_da not in NOME_SALVATAGGIO else prof_a
        raise ValueError(T(f'versione sconosciuta: {x}', f'unknown version: {x}'))
    nome_da, nome_a = NOME_SALVATAGGIO[prof_da], NOME_SALVATAGGIO[prof_a]
    if nome_da == nome_a:
        raise ValueError(T(f'{prof_da} e {prof_a} usano gia\' lo stesso salvataggio ({nome_a})',
                           f'{prof_da} and {prof_a} already use the same save ({nome_a})'))
    if not da.is_file():
        raise ValueError(T(f'{da.name} non c\'e\' ancora: nessuna partita da copiare',
                           f'{da.name} does not exist yet: no saved games to copy'))
    src = _dati_card(da)
    if src is None or src[:2] != b'MC':
        raise ValueError(T(f'{da.name}: non e\' una memory card della PS1', f'{da.name}: not a PS1 memory card'))
    i = _voce_salvataggio(src, nome_da)
    if i is None:
        raise ValueError(T(f'in {da.name} non c\'e\' un salvataggio di {prof_da} ({nome_da})',
                           f'{da.name} has no save of {prof_da} ({nome_da})'))
    voce = src[128 * i:128 * (i + 1)]
    if struct.unpack_from('<H', voce, 8)[0] != 0xFFFF or struct.unpack_from('<I', voce, 4)[0] != BLOCCO:
        raise ValueError(T(f'{da.name}: il salvataggio di {prof_da} non e\' di un solo blocco',
                           f'{da.name}: the save of {prof_da} is not a single block'))
    if a.is_file():
        dst = _dati_card(a)
        if dst is None or dst[:2] != b'MC':
            raise ErroreDestinazione(T(f'{a.name}: non e\' una memory card della PS1',
                                       f'{a.name}: not a PS1 memory card'))
    else:
        dst = card_vuota()
    if _voce_salvataggio(dst, nome_a) is not None:
        raise ErroreDestinazione(T(f'in {a.name} c\'e\' gia\' un salvataggio di {prof_a}: usa l\'altra memory card',
                                   f'{a.name} already has a save of {prof_a}: use the other memory card'))
    libero = next((j for j in range(1, 16) if dst[128 * j] & 0xF0 == 0xA0 or dst[128 * j] == 0), None)
    if libero is None:
        raise ErroreDestinazione(T(f'in {a.name} non c\'e\' un blocco libero', f'{a.name} has no free block'))
    nuova = bytearray(dst)
    blocco = bytearray(src[BLOCCO * i:BLOCCO * (i + 1)])
    schermo = _sposta_schermo(blocco, SCHERMO_SALVATAGGIO.get(prof_a, 0) - SCHERMO_SALVATAGGIO.get(prof_da, 0))
    nuova[BLOCCO * libero:BLOCCO * (libero + 1)] = blocco
    v = bytearray(voce)
    v[10:30] = nome_a.encode('ascii').ljust(20, b'\x00')
    v[127] = _xor(v)
    nuova[128 * libero:128 * (libero + 1)] = v
    ris = {'blocco': libero, 'nome': nome_a, 'partite': partite_salvate(bytes(nuova), libero), 'schermo': schermo,
           'copia': None}
    if not prova:
        if a.is_file():
            ris['copia'] = copia_di_sicurezza(a)
        a.parent.mkdir(parents=True, exist_ok=True)
        tmp = a.with_name(a.name + '.nuova')
        tmp.write_bytes(bytes(nuova))
        tmp.replace(a)
    return ris


def salvataggi_rapidi(cartella: Path) -> list:
    """I salvataggi rapidi (F7): [{slot, file, data, byte, anteprima (Path o None), cartella_bios}] dal piu' recente."""
    base = cartella_memory_card(cartella)
    out = []
    for f in base.glob('*/state_*_slot*.pst'):
        m = re.search(r'_slot(\d+)\.pst$', f.name)
        if not m:
            continue
        th = f.with_suffix('.thumb')
        st = f.stat()
        out.append({'slot': int(m.group(1)), 'file': f, 'data': datetime.datetime.fromtimestamp(st.st_mtime),
                    'byte': st.st_size, 'anteprima': th if th.is_file() else None, 'cartella_bios': f.parent.name})
    return sorted(out, key=lambda x: x['data'], reverse=True)


def leggi_anteprima(path: Path):
    """(larghezza, altezza, righe RGB) dell'anteprima .thumb di psxrecomp, o None."""
    try:
        b = path.read_bytes()
    except OSError:
        return None
    if len(b) < 12 or b[:4] != b'PSTH':
        return None
    w, h = struct.unpack_from('<II', b, 4)
    if not (0 < w <= 1024 and 0 < h <= 1024) or len(b) < 12 + w * h * 4:
        return None
    righe = []
    for y in range(h):
        riga = bytearray()
        for x in range(w):
            p = struct.unpack_from('<I', b, 12 + 4 * (y * w + x))[0]
            riga += bytes(((p >> 16) & 255, (p >> 8) & 255, p & 255))
        righe.append(bytes(riga))
    return w, h, righe


def ppm(w: int, h: int, righe: list, scala: int = 1) -> bytes:
    """Un'immagine PPM (Tk la mostra senza librerie in piu'), ingrandita di scala volte."""
    out = bytearray(f'P6 {w * scala} {h * scala} 255\n'.encode('ascii'))
    for r in righe:
        if scala > 1:
            r = b''.join(r[3 * x:3 * x + 3] * scala for x in range(w))
        out += r * scala
    return bytes(out)
