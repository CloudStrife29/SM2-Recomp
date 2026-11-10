#!/usr/bin/env python3
"""EnterElectro-Recomp - lingua dei messaggi del launcher: italiano o inglese (4/11/2026).
EnterElectro-Recomp - language of the launcher messages: Italian or English (4 Nov 2026).

La lingua si sceglie in quest'ordine / The language is chosen in this order:
  1. imposta('it' | 'en'): opzione --lingua / --language della riga di comando, o la scelta fatta nella finestra
     (command-line option --lingua / --language, or the choice made in the launcher window);
  2. variabile d'ambiente SM2_LINGUA = it | en (environment variable);
  3. il file lingua.txt nella cartella principale, scritto dalla finestra del launcher
     (the lingua.txt file in the main folder, written by the launcher window);
  4. la lingua di Windows: italiano se Windows e' in italiano, altrimenti inglese
     (the Windows display language: Italian if Windows is in Italian, otherwise English).

T('testo italiano', 'English text') restituisce il testo nella lingua scelta / returns the text in the chosen language.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE_LINGUA = ROOT / 'lingua.txt'
LINGUE = ('it', 'en')
_lingua: str | None = None

# Nomi delle versioni e delle lingue del gioco in inglese (il catalogo aot/sm2_versioni.json resta com'e').
# English names of the game versions and languages (the catalogue aot/sm2_versioni.json stays as it is).
NOMI_EN = {
    'SLUS-01378-Rev1': 'USA Rev 1',
    'SLUS-01378': 'USA (original, before 11 September)',
    'SLES-03623': 'Europe (original, before 11 September)',
    'SLES-03623-Rev1': 'Europe/Australia Rev 1',
    'SLES-03624': 'France',
    'SLES-03625': 'Germany',
    'SLPM-87073': 'Japan',
}
LINGUE_GIOCO_EN = {'inglese': 'English', 'francese': 'French', 'tedesco': 'German', 'giapponese': 'Japanese'}


def _da_windows() -> str:
    """Lingua dell'interfaccia di Windows (GetUserDefaultUILanguage): 'it' se italiano, altrimenti 'en'."""
    if os.name == 'nt':
        try:
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return 'it' if (lid & 0x3FF) == 0x10 else 'en'      # 0x10 = LANG_ITALIAN
        except Exception:  # noqa: BLE001
            pass
    v = (os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG') or '').lower()
    return 'it' if v.startswith('it') else 'en'


def lingua() -> str:
    """La lingua scelta: 'it' o 'en' (vedi sopra)."""
    global _lingua
    if _lingua:
        return _lingua
    v = (os.environ.get('SM2_LINGUA') or '').strip().lower()
    if v not in LINGUE:
        try:
            v = FILE_LINGUA.read_text(encoding='utf-8').strip().lower()
        except OSError:
            v = ''
    if v not in LINGUE:
        v = _da_windows()
    _lingua = v
    return v


def imposta(v: str) -> None:
    """Sceglie la lingua per questo processo e per quelli che lancia (variabile SM2_LINGUA)."""
    global _lingua
    v = (v or '').strip().lower()
    if v in LINGUE:
        _lingua = v
        os.environ['SM2_LINGUA'] = v


def salva(v: str) -> bool:
    """Ricorda la scelta della finestra in lingua.txt; False se il file non si puo' scrivere."""
    v = (v or '').strip().lower()
    if v not in LINGUE:
        return False
    try:
        FILE_LINGUA.write_text(v + '\n', encoding='utf-8')
        return True
    except OSError:
        return False


def T(it: str, en: str) -> str:
    """Il testo nella lingua scelta / the text in the chosen language."""
    return en if lingua() == 'en' else it


def nome_versione(profilo: str, nome_it: str) -> str:
    """Nome della versione del gioco nella lingua scelta (in italiano quello del catalogo)."""
    return NOMI_EN.get(profilo, nome_it) if lingua() == 'en' else nome_it


def lingua_gioco(nome_it: str) -> str:
    """Lingua del gioco (inglese, francese...) nella lingua scelta."""
    return LINGUE_GIOCO_EN.get(nome_it, nome_it) if lingua() == 'en' else nome_it
