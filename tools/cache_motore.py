# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - il "motore precompilato": dalla cache del compilatore di un'installazione prende solo gli oggetti del
motore (psxrecomp, recomp-ui, librerie, mod di EnterElectro-Recomp), mai quelli del codice del gioco, per metterli nel pacchetto.
EnterElectro-Recomp 0.12 - the "precompiled engine": takes from an installation's compiler cache only the engine objects, never
the game code ones, to ship them in the package.

  python cache_motore.py estrai --registro LOG --installazione CARTELLA --cache CACHE --uscita USCITA
        LOG: registro di ccache (CCACHE_LOGFILE) della compilazione di CARTELLA\\build-release con la cache CACHE;
        copia in USCITA (stessa struttura di CACHE) i file della cache scritti o letti per i sorgenti del motore.
        Un oggetto e' del motore solo se il sorgente sta in psxrecomp\\, recomp-ui\\, mods_src\\ o build-release\\_deps\\
        e nessuno dei file che include (ninja -t deps) sta in generated\\ o aot\\ dell'installazione: cosi' nel pacchetto
        non c'e' niente che venga dal disco del giocatore. Dal 5/11/2026 anche gli oggetti degli emettitori di
        psxrecomp (psxrecomp-game e psxrecomp-bios, compilati da "psxrecomp generate" in psxrecomp\\recompiler\\build):
        sono programmi di psxrecomp, uguali per tutte le versioni del gioco, con lo stesso controllo dei file inclusi.
  python cache_motore.py elenca --uscita USCITA
        numero di file e grandezza.

Gli oggetti sono quelli che il compilatore del pacchetto fa da quei sorgenti con quelle opzioni: ccache li riusa solo
se sorgenti, opzioni, compilatore e file inclusi sono uguali, quindi il gioco compilato con la cache e' identico.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NINJA = ROOT / 'tools' / 'toolchain' / 'cmake-clang-v1' / 'bin' / ('ninja.exe' if os.name == 'nt' else 'ninja')
DEL_MOTORE = ('psxrecomp', 'recomp-ui', 'mods_src')


def _norm(p: str) -> str:
    return p.replace('\\', '/').lower()


def leggi_registro(path: Path) -> list:
    """[{pid, sorgente, oggetto, file: [percorsi nella cache], esiti: [...]}] per ogni compilazione nel registro."""
    per = collections.OrderedDict()
    for riga in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = re.match(r'\[[^\]]*\s(\d+)\s*\]\s*(.*)', riga)
        if not m:
            continue
        pid, t = m.group(1), m.group(2)
        if t.startswith('=== CCACHE') and 'STARTED' in t:
            per[pid] = {'pid': pid, 'sorgente': None, 'oggetto': None, 'cartella': None, 'file': [], 'esiti': []}
            continue
        voce = per.get(pid)
        if voce is None:
            continue
        if t.startswith('Working directory: '):
            voce['cartella'] = t[len('Working directory: '):].strip()
        elif t.startswith('Source file: '):
            voce['sorgente'] = t[len('Source file: '):].strip()
        elif t.startswith('Object file: '):
            voce['oggetto'] = t[len('Object file: '):].strip()
        elif (t.startswith('Stored ') and ' in local storage (' in t) or \
                (t.startswith('Retrieved ') and ' from local storage (' in t):
            voce['file'].append(t.rsplit('(', 1)[1].rstrip(')').strip())
        elif t.startswith('Result: '):
            voce['esiti'].append(t[len('Result: '):].strip())
    return [v for v in per.values() if v['sorgente']]


def dipendenze(build: Path) -> dict:
    """{oggetto (percorso relativo alla cartella di compilazione, minuscolo con /): [file inclusi]} da ninja -t deps."""
    p = subprocess.run([str(NINJA), '-C', str(build), '-t', 'deps'], capture_output=True, timeout=600)
    out, cur = {}, None
    for riga in (p.stdout or b'').decode('utf-8', 'replace').splitlines():
        if not riga.strip():
            continue
        if not riga.startswith((' ', '\t')):
            cur = _norm(riga.split(':', 1)[0].strip())
            out[cur] = []
        elif cur is not None:
            out[cur].append(riga.strip())
    return out


def del_motore(sorgente: str) -> bool:
    """Il sorgente (percorso relativo alla cartella di compilazione, come lo scrive ccache) e' del motore: psxrecomp\\,
    recomp-ui\\ o mods_src\\ dell'installazione (giunzioni alla radice), o una libreria in build-release\\_deps\\."""
    parti = [p for p in _norm(sorgente).split('/') if p not in ('', '.')]
    if parti and parti[0] == '_deps':
        return True
    while parti and parti[0] == '..':
        parti.pop(0)
    return bool(parti) and parti[0] in DEL_MOTORE


def cartella_emettitori(cartella: str | None):
    """La cartella di lavoro di una compilazione e' quella degli emettitori di psxrecomp (...\\recompiler\\build con
    recompiler\\CMakeLists.txt accanto)? Restituisce il percorso vero o None."""
    if not cartella:
        return None
    try:
        c = Path(cartella).resolve()
    except OSError:
        return None
    if c.name.lower() == 'build' and c.parent.name.lower() == 'recompiler' and (c.parent / 'CMakeLists.txt').is_file():
        return c
    return None


def cmd_estrai(args) -> int:
    inst = Path(args.installazione).resolve()
    build = inst / 'build-release'
    cache = Path(args.cache).resolve()
    uscita = Path(args.uscita).resolve()
    voci = leggi_registro(Path(args.registro))
    deps = dipendenze(build)
    deps_emettitori = {}
    # file inclusi vietati: codice e dati del gioco (generated\\, aot\\) e i file scritti per questa installazione nella
    # cartella di compilazione (tranne le librerie in _deps\\)
    vietati = [_norm(str(inst / 'generated')) + '/', _norm(str(inst / 'aot')) + '/', _norm(str(build)) + '/']
    permessi = [_norm(str(build / '_deps')) + '/']
    conti = collections.Counter()
    copiati, byte, esclusi = 0, 0, []
    for v in voci:
        emet = cartella_emettitori(v['cartella'])
        if emet is not None:                 # emettitori di psxrecomp: tutti del motore, con il controllo degli inclusi
            if str(emet) not in deps_emettitori:
                deps_emettitori[str(emet)] = dipendenze(emet)
            incl, base, tipo = deps_emettitori[str(emet)].get(_norm(v['oggetto'] or ''), None), emet, 'emettitori'
        elif not del_motore(v['sorgente']):
            conti['gioco o altro'] += 1
            continue
        else:
            incl, base, tipo = deps.get(_norm(v['oggetto'] or ''), None), build, 'motore'
        if incl is None:
            conti['senza dipendenze'] += 1
            esclusi.append((v['sorgente'], 'dipendenze non trovate'))
            continue
        cattivi = []
        for d in incl:
            n = _norm(d if os.path.isabs(d) else os.path.normpath(str(base / d)))
            if any(n.startswith(x) for x in vietati) and not any(n.startswith(x) for x in permessi):
                cattivi.append(d)
        if cattivi:
            conti['include file del gioco'] += 1
            esclusi.append((v['sorgente'], cattivi[0]))
            continue
        if not v['file']:
            conti['niente in cache'] += 1
            continue
        conti[tipo] += 1
        for f in v['file']:
            fp = Path(f)
            try:
                rel = fp.resolve().relative_to(cache)
            except ValueError:
                continue
            dest = uscita / rel
            if dest.exists() or not fp.is_file():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, dest)
            copiati += 1
            byte += fp.stat().st_size
    ris = {'compilazioni': len(voci), 'per_tipo': dict(conti), 'file_copiati': copiati, 'byte': byte,
           'esclusi': esclusi[:40]}
    print(json.dumps(ris, ensure_ascii=False, indent=1))
    return 0


def cmd_elenca(args) -> int:
    u = Path(args.uscita)
    f = [p for p in u.rglob('*') if p.is_file()]
    print(json.dumps({'file': len(f), 'byte': sum(p.stat().st_size for p in f)}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('estrai')
    s.add_argument('--registro', required=True)
    s.add_argument('--installazione', required=True)
    s.add_argument('--cache', required=True)
    s.add_argument('--uscita', required=True)
    s = sp.add_parser('elenca')
    s.add_argument('--uscita', required=True)
    args = ap.parse_args()
    return {'estrai': cmd_estrai, 'elenca': cmd_elenca}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
