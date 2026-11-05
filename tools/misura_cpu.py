#!/usr/bin/env python3
"""SM2-Recomp - quanta CPU consuma l'eseguibile normale (quello senza server di debug) a velocita' normale.

English: SM2-Recomp - how much CPU the game executable (build-release, without the debug server) uses at normal
speed: it runs the game with the window hidden and dummy audio, without input, for --secondi seconds and reads the
CPU time of the process (GetProcessTimes). Less CPU for the same work = a more efficient executable. The comments are
in Italian.

L'eseguibile con cui si gioca (build-release) non ha il server di debug: niente turbo e niente tempi per frame. Qui lo si
avvia con la finestra nascosta e l'audio finto (SDL_AUDIODRIVER=dummy, impostato dal .cmd), senza tasti, per --secondi
secondi a velocita' normale (il gioco e' agganciato a 59,94 frame al secondo, quindi fa lo stesso lavoro in ogni
avvio: avvio, filmati, titolo) e si legge il tempo di CPU usato dal processo (GetProcessTimes di Windows: tutti i suoi
thread, utente piu' sistema). Meno CPU per lo stesso lavoro = eseguibile piu' efficiente.

Con --attese no,si ogni cartella gira anche senza e con il salto delle attese (PSX_IDLE_SKIP=0 e 1, che psxrecomp legge
al posto della chiave idle_skip del game.toml; i punti di v_wait restano quelli del game.toml), alternati in ogni giro.

v3 (28/10/2026): --cpu tutti lascia al gioco tutti i processori (per la prova del PC, tools/prova_pc.py); di default,
come prima, la prima meta' (--cpu meta).

v4 (3/11/2026, QA livello 5): --progetto <cartella> usa un'altra installazione (per esempio work/qa5/SLUS-01378-Rev1,
senza PGO) invece di giochi/<PROFILO>; senza, uguale a prima.

Uso:  python tools/misura_cpu.py --cartelle build-release,build-pgo-rel [--profile SLUS-01378-Rev1] [--secondi 100]
                                [--giri 2] [--attese no,si] [--uscita pgo] [--cpu meta|tutti] [--progetto <cartella>]
Uscita: work/<uscita>/<PROFILO>/cpu.json e cpu.txt
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import m2_smoke as smoke  # noqa: E402  (limite CPU)

EXE = 'SpiderMan2EnterElectro.exe'


def tempi_cpu(proc) -> float | None:
    """Secondi di CPU (utente + sistema) del processo, da GetProcessTimes."""
    if os.name != 'nt':
        return None
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    ft = [wintypes.FILETIME() for _ in range(4)]
    h = wintypes.HANDLE(int(proc._handle))
    if not k32.GetProcessTimes(h, *[ctypes.byref(x) for x in ft]):
        return None
    val = lambda f: ((f.dwHighDateTime << 32) | f.dwLowDateTime) / 1e7  # noqa: E731
    return round(val(ft[2]) + val(ft[3]), 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--profile', default='SLUS-01378-Rev1')
    ap.add_argument('--cartelle', default='build-release,build-pgo-rel')
    ap.add_argument('--secondi', type=int, default=100)
    ap.add_argument('--giri', type=int, default=2)
    ap.add_argument('--attese', default='', help='no,si: senza e con il salto delle attese (variabile PSX_IDLE_SKIP)')
    ap.add_argument('--uscita', default='pgo', help='sottocartella di work per i risultati')
    ap.add_argument('--cpu', choices=('meta', 'tutti'), default='meta', help='processori per il gioco (v3)')
    ap.add_argument('--progetto', default='', help='installazione (dalla radice), di default giochi/<PROFILO> (v4)')
    args = ap.parse_args()
    modi = [m.strip() for m in args.attese.split(',') if m.strip()] or ['']
    if any(m not in ('', 'si', 'no') for m in modi):
        print('ERRORE: --attese: valori validi si e no')
        return 2
    progetto = (ROOT / args.progetto) if args.progetto else ROOT / 'giochi' / args.profile
    cue = Path(json.loads((progetto / 'installazione.json').read_text(encoding='utf-8'))['disco'])
    cartelle = [c.strip() for c in args.cartelle.split(',') if c.strip()]
    out = ROOT / 'work' / args.uscita / args.profile
    out.mkdir(parents=True, exist_ok=True)
    log_f = open(out / 'cpu_log.txt', 'a', encoding='utf-8')

    def log(riga=''):
        print(riga, flush=True)
        log_f.write(riga + '\n')
        log_f.flush()

    cpu = smoke.limit_cpu_half() if args.cpu == 'meta' else {'applicato': False, 'processori_logici': os.cpu_count()}
    log(f'== {datetime.datetime.now():%Y-%m-%d %H:%M:%S} CPU dell\'eseguibile normale {args.profile}: {args.giri} giri '
        f'di {args.secondi} s per {", ".join(cartelle)}' + (f', salto delle attese {"/".join(modi)}' if modi != [''] else '') +
        f'; finestra nascosta, nessun tasto; limite CPU {json.dumps(cpu)}')
    for c in cartelle:
        e = progetto / c / EXE
        if not e.is_file():
            log(f'ERRORE: manca {e}')
            return 1
        log(f'   {c}: {e.stat().st_size / 1e6:.1f} MB, {datetime.datetime.fromtimestamp(e.stat().st_mtime):%d/%m %H:%M}')
    ris = []
    etichette = []
    for giro in range(1, args.giri + 1):
        for c, modo in [(c, m) for c in cartelle for m in modi]:
            etichetta = c + (f' [attese {modo}]' if modo else '')
            if etichetta not in etichette:
                etichette.append(etichetta)
            exe = progetto / c / EXE
            env = dict(os.environ, PSX_OVERLAY_AUTOCOMPILE_OFF='1')
            if modo:
                env['PSX_IDLE_SKIP'] = '1' if modo == 'si' else '0'
            cmd = [str(exe), '--no-launcher', '--game', str(progetto / 'game.toml'), '--disc', str(cue),
                   '--hidden-window']
            uscita = out / f'cpu_{c}{"_attese_" + modo if modo else ""}_{giro}.txt'
            f = open(uscita, 'w', encoding='utf-8', errors='replace')
            proc = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=f, stderr=subprocess.STDOUT)
            t0 = time.time()
            campioni = []
            while time.time() - t0 < args.secondi and proc.poll() is None:
                time.sleep(10)
                campioni.append((round(time.time() - t0, 1), tempi_cpu(proc)))
            vivo = proc.poll() is None
            finale = tempi_cpu(proc)
            durata = round(time.time() - t0, 1)
            if vivo:
                proc.kill()
                proc.wait(timeout=15)
            f.close()
            righe_idle = [r.strip() for r in uscita.read_text(encoding='utf-8', errors='replace').splitlines()
                          if 'idle_skip' in r][:3]
            rec = {'cartella': c, 'attese': modo, 'etichetta': etichetta, 'giro': giro, 'secondi': durata,
                   'cpu_secondi': finale, 'vivo': vivo, 'campioni': campioni, 'idle_skip_log': righe_idle}
            ris.append(rec)
            log(f'   {etichetta} giro {giro}: {finale} s di CPU in {durata} s ' +
                ('' if vivo else f'(ATTENZIONE: il gioco si e\' chiuso da solo, codice {proc.returncode})') +
                (f' | {" | ".join(righe_idle)}' if righe_idle else ''))
            (out / 'cpu.json').write_text(json.dumps(ris, indent=1), encoding='utf-8')
            time.sleep(3)
    righe = [f'SM2-Recomp - CPU dell\'eseguibile normale ({args.profile}), {datetime.datetime.now():%Y-%m-%d %H:%M}',
             f'{args.secondi} s a velocita\' normale, finestra nascosta, senza tasti (avvio, filmati, titolo):', '']
    base = None
    for e in etichette:
        v = [r['cpu_secondi'] for r in ris if r['etichetta'] == e and isinstance(r['cpu_secondi'], (int, float))]
        if not v:
            righe.append(f'  {e}: -')
            continue
        m = sum(v) / len(v)
        if base is None:
            base = m
        righe.append(f'  {e}: {m:.2f} s di CPU in media [{", ".join(f"{x:.2f}" for x in v)}]' +
                     (f' ({100 * (m - base) / base:+.1f}%)' if base and e != etichette[0] else ''))
    (out / 'cpu.txt').write_text('\n'.join(righe) + '\n', encoding='utf-8')
    for r in righe:
        log(r)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
