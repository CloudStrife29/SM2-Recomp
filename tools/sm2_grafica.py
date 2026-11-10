# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - la grafica della finestra del launcher: pannelli semitrasparenti, pulsanti, distintivi, bagliori.
EnterElectro-Recomp 0.12 - the launcher window graphics: translucent panels, buttons, badges, glows.

Le forme si disegnano qui in Python puro (solo la libreria standard: zlib per il PNG), della grandezza giusta per lo
schermo e per l'ingrandimento di Windows, e Tk le mostra con la trasparenza sopra l'immagine di fondo. Le immagini fisse
(lo sfondo disegnato con la citta' di notte, le lettere del titolo, le icone e, dal 6/11/2026, l'icona del launcher in
tools/grafica/icona_launcher/) sono in tools/grafica/: le ha disegnate EnterElectro-Recomp per il launcher (vedi
tools/grafica/LEGGIMI.txt). Niente immagini o loghi del gioco.
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

CARTELLA = Path(__file__).resolve().parent / 'grafica'


def png_rgba(w: int, h: int, righe) -> bytes:
    """PNG RGBA (8 bit) dalle righe di pixel (w * 4 byte ciascuna)."""
    grezzo = b''.join(b'\x00' + r for r in righe)

    def pezzo(tipo: bytes, dati: bytes) -> bytes:
        return struct.pack('>I', len(dati)) + tipo + dati + struct.pack('>I', zlib.crc32(tipo + dati) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + pezzo(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            pezzo(b'IDAT', zlib.compress(grezzo, 6)) + pezzo(b'IEND', b''))


def _copertura(px: float, py: float, w: float, h: float, r: float) -> float:
    """Quanto il pixel con il centro in (px, py) sta dentro il rettangolo [0, w] x [0, h] con gli angoli di raggio r
    (distanza con segno dal bordo, mezzo pixel di sfumatura)."""
    qx = abs(px - w / 2.0) - (w / 2.0 - r)
    qy = abs(py - h / 2.0) - (h / 2.0 - r)
    fuori = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
    return min(1.0, max(0.0, 0.5 - fuori))


def _mescola(ci: float, co: float, riemp, bordo) -> bytes:
    """Un pixel: riempimento dove la forma interna copre (ci), bordo nella corona (co - ci)."""
    fa = ci * riemp[3]
    ba = (co - ci) * bordo[3] if bordo else 0.0
    a = fa + ba
    if a <= 0.0:
        return b'\x00\x00\x00\x00'
    c = bordo or riemp
    return bytes((int((riemp[0] * fa + c[0] * ba) / a + 0.5), int((riemp[1] * fa + c[1] * ba) / a + 0.5),
                  int((riemp[2] * fa + c[2] * ba) / a + 0.5), min(255, int(a + 0.5))))


def rett_tondo(w: int, h: int, r: float, riemp, bordo=None, sp: int = 1, riemp2=None) -> bytes:
    """Rettangolo arrotondato w x h (PNG RGBA): riempimento riemp (r, g, b, a), sfumato verso riemp2 in basso se c'e',
    con il bordo largo sp del colore bordo (r, g, b, a) se c'e'. Bordi lisci (mezzo pixel di sfumatura)."""
    w, h = max(1, int(w)), max(1, int(h))
    r = max(0.0, min(float(r), w / 2.0, h / 2.0))
    ri = max(0.0, r - sp) if bordo else r
    zona = int(math.ceil(r)) + sp + 2           # colonne vicino ai lati che vanno calcolate pixel per pixel
    zona = min(zona, (w + 1) // 2)
    righe = []
    for y in range(h):
        t = y / max(1, h - 1)
        rc = tuple(int(riemp[k] + ((riemp2 or riemp)[k] - riemp[k]) * t) for k in range(4)) if riemp2 else riemp
        py = y + 0.5
        sx = []
        for x in range(zona):
            px = x + 0.5
            co = _copertura(px, py, w, h, r)
            ci = _copertura(px - sp, py - sp, w - 2 * sp, h - 2 * sp, ri) if bordo else co
            sx.append(_mescola(ci, co, rc, bordo))
        medio_n = w - 2 * zona
        if medio_n >= 0:
            # in mezzo: dentro la forma interna (o nel bordo, nelle righe in alto e in basso)
            co = _copertura(w / 2.0, py, w, h, r)
            ci = _copertura(w / 2.0 - sp, py - sp, w - 2 * sp, h - 2 * sp, ri) if bordo else co
            righe.append(b''.join(sx) + _mescola(ci, co, rc, bordo) * medio_n + b''.join(reversed(sx)))
        else:                                   # larghezza dispari piu' piccola delle due zone: un pixel in comune
            righe.append(b''.join(sx) + b''.join(reversed(sx[:w - zona])))
    return png_rgba(w, h, righe)


def cerchio(d: int, riemp, bordo=None, sp: int = 2) -> bytes:
    """Cerchio pieno d x d (PNG RGBA), con l'anello del colore bordo se c'e'."""
    return rett_tondo(d, d, d / 2.0, riemp, bordo, sp)


def bagliore(w: int, h: int, r: float, colore, margine: int, forza: float = 1.0) -> bytes:
    """Alone morbido attorno a un rettangolo arrotondato w x h: immagine (w + 2 margine) x (h + 2 margine), colore
    (r, g, b, a) che sfuma verso l'esterno (dentro la forma e' trasparente: sotto c'e' il pulsante)."""
    W, H = int(w + 2 * margine), int(h + 2 * margine)
    sig = max(1.0, margine / 2.2)
    righe = []
    for y in range(H):
        riga = bytearray()
        py = y + 0.5 - margine
        for x in range(W):
            px = x + 0.5 - margine
            qx = abs(px - w / 2.0) - (w / 2.0 - r)
            qy = abs(py - h / 2.0) - (h / 2.0 - r)
            dist = math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
            if dist <= 0:
                a = 0
            else:
                a = int(colore[3] * forza * math.exp(-(dist / sig) ** 2) + 0.5)
            riga += bytes((colore[0], colore[1], colore[2], min(255, a)))
        righe.append(bytes(riga))
    return png_rgba(W, H, righe)


def velo(w: int, h: int, colore, colore2=None, orizzontale: bool = False) -> bytes:
    """Rettangolo semitrasparente w x h, sfumato verso colore2 (in basso, o a destra con orizzontale) se c'e'."""
    w, h = max(1, int(w)), max(1, int(h))
    if colore2 is None:
        riga = bytes(colore) * w
        return png_rgba(w, h, [riga] * h)
    if orizzontale:
        riga = b''.join(bytes(int(colore[k] + (colore2[k] - colore[k]) * x / max(1, w - 1)) for k in range(4))
                        for x in range(w))
        return png_rgba(w, h, [riga] * h)
    righe = [bytes(int(colore[k] + (colore2[k] - colore[k]) * y / max(1, h - 1)) for k in range(4)) * w
             for y in range(h)]
    return png_rgba(w, h, righe)


def _dist_segmento(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx, vy = bx - ax, by - ay
    l2 = vx * vx + vy * vy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / l2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def casella(px: int, riemp, bordo, segno=None, sp: int = 1) -> bytes:
    """Casella di spunta px x px (PNG RGBA): rettangolo arrotondato riemp (r, g, b, a) con il bordo, e il segno di
    spunta del colore segno (r, g, b, a) se c'e'."""
    px = max(6, int(px))
    r = max(2.0, px * 0.24)
    ri = max(0.0, r - sp)
    larg = max(1.6, px * 0.13)                 # spessore del segno
    punti = ((0.25 * px, 0.53 * px), (0.43 * px, 0.71 * px), (0.77 * px, 0.32 * px))
    righe = []
    for y in range(px):
        riga = bytearray()
        py = y + 0.5
        for x in range(px):
            pxx = x + 0.5
            co = _copertura(pxx, py, px, px, r)
            ci = _copertura(pxx - sp, py - sp, px - 2 * sp, px - 2 * sp, ri)
            pix = _mescola(ci, co, riemp, bordo)
            if segno is not None and co > 0:
                d = min(_dist_segmento(pxx, py, *punti[0], *punti[1]), _dist_segmento(pxx, py, *punti[1], *punti[2]))
                k = min(1.0, max(0.0, 0.5 + larg / 2.0 - d)) * co * segno[3] / 255.0
                if k > 0:
                    a0 = pix[3] / 255.0
                    a = k + a0 * (1 - k)
                    pix = bytes(int((segno[i] * k + pix[i] * a0 * (1 - k)) / a + 0.5) for i in range(3)) + \
                        bytes((min(255, int(a * 255 + 0.5)),))
            riga += pix
        righe.append(bytes(riga))
    return png_rgba(px, px, righe)


def scelta(px: int, riemp, bordo, punto=None, sp: int = 1) -> bytes:
    """Pallino di scelta px x px (PNG RGBA): cerchio riemp con il bordo e, se c'e', il punto del colore punto."""
    px = max(6, int(px))
    r = px / 2.0
    rp = px * 0.2                              # raggio del punto
    righe = []
    for y in range(px):
        riga = bytearray()
        py = y + 0.5
        for x in range(px):
            pxx = x + 0.5
            co = _copertura(pxx, py, px, px, r)
            ci = _copertura(pxx - sp, py - sp, px - 2 * sp, px - 2 * sp, r - sp)
            pix = _mescola(ci, co, riemp, bordo)
            if punto is not None:
                k = min(1.0, max(0.0, 0.5 - (math.hypot(pxx - r, py - r) - rp))) * punto[3] / 255.0
                if k > 0:
                    a0 = pix[3] / 255.0
                    a = k + a0 * (1 - k)
                    pix = bytes(int((punto[i] * k + pix[i] * a0 * (1 - k)) / a + 0.5) for i in range(3)) + \
                        bytes((min(255, int(a * 255 + 0.5)),))
            riga += pix
        righe.append(bytes(riga))
    return png_rgba(px, px, righe)


# ------------------------------------------------------------------------------------------- immagini fisse

ICONE_PX = (16, 20, 24, 28, 32, 40, 48, 56)
TITOLO_SCALE = (75, 100, 125, 150, 175, 200)


def file_icona(nome: str, px: int, spenta: bool = False):
    """Il file dell'icona nella grandezza disponibile piu' vicina (None se manca)."""
    migliore = min(ICONE_PX, key=lambda p: (abs(p - px), -p))
    f = CARTELLA / 'icone' / f'{nome}{"_spenta" if spenta else ""}_{migliore}.png'
    return f if f.is_file() else None


def file_titolo(scala: float):
    s = min(TITOLO_SCALE, key=lambda p: abs(p / 100.0 - scala))
    f = CARTELLA / f'titolo_{s}.png'
    return f if f.is_file() else None


def file_sfondo():
    f = CARTELLA / 'sfondo_citta.png'
    return f if f.is_file() else None


# l'icona del launcher (6/11/2026): ragnatela, fulmine, citta' di notte e la scritta SM2, disegnata da EnterElectro-Recomp
ICONA_LAUNCHER_PX = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def file_icona_launcher(px: int):
    """L'icona del launcher in PNG nella grandezza disponibile piu' vicina (None se manca)."""
    migliore = min(ICONA_LAUNCHER_PX, key=lambda p: (abs(p - px), -p))
    f = CARTELLA / 'icona_launcher' / f'sm2_{migliore}.png'
    return f if f.is_file() else None


def file_ico():
    """L'icona del launcher per Windows (sm2.ico, tutte le grandezze): finestra, barra delle applicazioni e il
    collegamento EnterElectro-Recomp nella cartella (None se manca)."""
    f = CARTELLA / 'icona_launcher' / 'sm2.ico'
    return f if f.is_file() else None
