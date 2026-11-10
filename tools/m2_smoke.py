#!/usr/bin/env python3
"""EnterElectro-Recomp - test di avvio e misura delle prestazioni del gioco ricompilato (v9).

English: EnterElectro-Recomp start-up test and performance measurement of the recompiled game. It starts the development
executable (build-dev, with the TCP debug server), presses the buttons at exact game frames, saves PNG screenshots,
measures the speed against real time and, inside the level, the CPU profile and the instructions still run by the
interpreter; at the end a few seconds in turbo mode measure what a frame really costs. The comments are in Italian.

Avvia l'eseguibile di sviluppo (build-dev, server di debug TCP sulla porta 4370) e:
  - preme i tasti a frame ESATTI del gioco (input_route del runtime), non dopo un
    certo numero di secondi: la sequenza e' la stessa su qualsiasi PC, veloce o lento
  - salva screenshot PNG dello schermo PS1 a frame prefissati
  - misura la velocita' rispetto al tempo reale (59.94 frame/s NTSC; 50 per le versioni PAL SLES, v9)
  - dentro il livello raccoglie il profilo della CPU del thread di emulazione
    (host_profile) e il numero di istruzioni eseguite dall'interprete per frame
    (frame_wall_ring): sono il codice non ancora ricompilato in nativo
  - alla fine attiva per qualche secondo la modalita' turbo (niente limite dei 60
    frame/s e niente presentazione) per misurare quanto costa davvero un frame alla
    CPU, cioe' il margine che resta
Di default disattiva le funzioni diagnostiche che falsano le misure della build di
sviluppo: PSX_DISPLAY_RING=0 e PSX_DEBUG_TOGGLES=0 (--forensic le lascia attive).

Limite CPU (--cpu meta, default; dalla v6 della seconda sessione): su Windows il gioco
gira sulla prima meta' dei processori logici (sull'i9 sono i core P). Il limite si
eredita, quindi vale anche per la compilazione degli overlay che il gioco avvia da solo
in background (compile_overlays.py usa tutti i core meno 2 e non ha un'opzione per
cambiarlo). Non cambia nulla nel sistema e finisce quando il gioco si chiude.
--cpu tutti lo toglie. L'altro progetto sull'i9 resta cosi' con l'altra meta'.

Audio: psxrecomp @1a3fc0db non legge PSX_HOST_MUTE, quindi il gioco ha l'audio attivo.

Altre versioni (v9): --progetto versioni/<PROFILO> usa l'eseguibile e il game.toml del progetto di
quella versione (tools/versione.py) e --profile il suo dump in input/<PROFILO>.

v11: alla fine legge anche i contatori dei plugin delle mod (comando mod_counters del server di debug),
per esempio quelli della mod "Distanza visiva" del launcher, e li scrive in m2_summary.txt.
v12: --wide salva anche l'immagine larga del widescreen "native-wide" alla risoluzione interna
(screenshot_wide_hires, wr_fNNNNN.png): screenshot_hires mostra solo la parte 4:3 della VRAM.
v13 (31/10/2026): se il gioco corre piu' del previsto mentre la sequenza di tasti viene programmata (con il psxrecomp
aggiornato una volta e' partita al frame 224 invece del 141 chiesto e il test si fermava), la riprogramma con piu'
margine, fino a 4 tentativi, invece di fermarsi.

Uso:
  python tools/m2_smoke.py [--profile SLUS-01378-Rev1] [--progetto versioni/<PROFILO>] [--label smoke]
                           [--end-frame 7200] [--level-from 6000] [--turbo-secs 15]
                           [--max-secs 480] [--presses FRAME:TASTO,...]
                           [--env CHIAVE=VALORE ...] [--forensic] [--no-turbo]
                           [--cpu meta|tutti]
Esempio (confronto con idle_skip):
  python tools/m2_smoke.py --label idle_skip --env PSX_IDLE_SKIP=1
Uscita: work/m2/<label>/ (m2_summary.txt, smoke.json, smoke_log.txt, shot_f*.png,
        host_profile_livello.txt, host_profile_turbo.txt, runtime_output.txt)
"""
from __future__ import annotations

import argparse, bisect, datetime, json, os, platform, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 4370
NTSC = 59.94
RITMO = NTSC        # frame al secondo della versione provata: 50 per le versioni PAL (main)
BUTTONS = {'NONE': 0xFFFF, 'START': 0xFFF7, 'SELECT': 0xFFFE, 'CROSS': 0xBFFF, 'CIRCLE': 0xDFFF,
           'TRIANGLE': 0xEFFF, 'SQUARE': 0x7FFF, 'UP': 0xFFEF, 'DOWN': 0xFFBF, 'LEFT': 0xFF7F,
           'RIGHT': 0xFFDF}
# Il gioco non e' identico frame per frame da un avvio all'altro (26/10/2026: lo stesso START al
# frame 3660 una volta e' arrivato sul titolo, un'altra no). Sequenza robusta: alcuni START sul
# titolo, poi CROSS ogni 150 frame. CROSS conferma menu e difficolta', salta il filmato
# iniziale e nel livello fa solo saltare Spider-Man. START nel livello metterebbe in pausa.
DEFAULT_PRESSES = ('3700:START,3800:START,' +
                   ','.join(f'{f}:CROSS' for f in range(4100, 5601, 150)))
LEVEL_FROM_DEFAULT = 6000  # da qui in poi si e' dentro il livello (per i profili)
SHOT_FRAMES = [300, 600, 900, 1200, 1800, 2400, 3000, 3600, 3750, 3900, 4050, 4200, 4350, 4500,
               4650, 4800, 4950, 5100, 5250, 5400, 5700, 6000, 6600, 7200, 7800, 8400]
END_CMDS = ('unknown_dispatch_log', 'segment_misses', 'overlay_loader_status',
            'overlay_candidates', 'autocompile_status', 'gpu_state', 'video_info', 'perf',
            'mod_counters')   # v11: contatori dei plugin delle mod (per esempio Distanza visiva)

COMPILERS = {'clang.exe', 'clang++.exe', 'clang-cl.exe', 'cl.exe', 'gcc.exe', 'g++.exe', 'cc1.exe',
             'cc1plus.exe', 'ld.exe', 'lld.exe', 'ld.lld.exe', 'lld-link.exe', 'ninja.exe', 'cmake.exe',
             'msbuild.exe', 'link.exe', 'make.exe', 'mingw32-make.exe', 'rustc.exe', 'cargo.exe',
             'javac.exe', 'gradle.exe'}
_log_f = None


def limit_cpu_half() -> dict:
    """Windows: limita questo processo alla prima meta' dei processori logici; il gioco e la
    compilazione degli overlay che il gioco lancia ereditano il limite."""
    if os.name != 'nt':
        return {'applicato': False, 'motivo': 'non Windows'}
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_size_t),
                                           ctypes.POINTER(ctypes.c_size_t)]
    k32.GetProcessAffinityMask.restype = wintypes.BOOL
    k32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    k32.SetProcessAffinityMask.restype = wintypes.BOOL
    me = k32.GetCurrentProcess()
    pmask, smask = ctypes.c_size_t(0), ctypes.c_size_t(0)
    if not k32.GetProcessAffinityMask(me, ctypes.byref(pmask), ctypes.byref(smask)):
        return {'applicato': False, 'motivo': f'GetProcessAffinityMask errore {ctypes.get_last_error()}'}
    bits = [i for i in range(64) if (pmask.value >> i) & 1]
    keep = bits[:max(1, len(bits) // 2)]
    mask = sum(1 << i for i in keep)
    if not k32.SetProcessAffinityMask(me, mask):
        return {'applicato': False, 'motivo': f'SetProcessAffinityMask errore {ctypes.get_last_error()}'}
    return {'applicato': True, 'processori_logici': len(bits), 'usati': len(keep),
            'primo': keep[0], 'ultimo': keep[-1], 'maschera': hex(mask)}


def busy_compilers():
    """Compilatori in esecuzione adesso (per esempio quelli dell'altro progetto), o None se non si sa."""
    if os.name != 'nt':
        return None
    exe = Path(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'tasklist.exe')
    try:
        out = subprocess.run([str(exe) if exe.is_file() else 'tasklist', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, errors='replace', timeout=60).stdout
    except Exception:  # noqa: BLE001
        return None
    names = {line.split('","')[0].strip('"').lower() for line in out.splitlines() if line.strip()}
    return sorted(names & COMPILERS)


def log(*parts) -> None:
    line = ' '.join(str(p) for p in parts)
    print(line, flush=True)
    if _log_f:
        _log_f.write(line + '\n')
        _log_f.flush()


class Dbg:
    """Client del server di debug di psxrecomp: una connessione per comando
    (psxrecomp/tools/debug_client.py: le risposte sono oggetti JSON, non righe)."""
    def __init__(self, port: int):
        sys.path.insert(0, str(ROOT / 'psxrecomp' / 'tools'))
        import debug_client  # noqa: E402
        self.dc, self.port, self.next_id = debug_client, port, 1

    def call(self, cmd: str, timeout: float = 20.0, **kw):
        req = {'id': self.next_id, 'cmd': cmd, **kw}
        self.next_id += 1
        try:
            return self.dc.query('127.0.0.1', self.port, req, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return {'error': f'{type(e).__name__}: {e}'}

    def connect(self, timeout: float) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            r = self.call('ping', timeout=3)   # risposto dal thread I/O: {'pong': true}, senza frame
            if isinstance(r, dict) and r.get('ok'):
                return True
            time.sleep(1)
        return False

    def frame(self):
        r = self.call('frame', timeout=10)    # 'ping' non riporta il frame
        f = r.get('frame') if isinstance(r, dict) else None
        return f if isinstance(f, int) else None


def find_exe(base: Path = ROOT) -> Path | None:
    # build-dev = build con server di debug TCP (PSX_DEBUG_TOOLS=ON), necessario per il test.
    # base: la radice (USA Rev 1) o il progetto di un'altra versione (versioni/<PROFILO>, v9)
    for d in ('build-dev', 'build-release'):
        for p in sorted(base.glob(f'{d}/SpiderMan2EnterElectro*.exe')) + sorted(base.glob(f'{d}/SpiderMan2EnterElectro')):
            if p.is_file():
                return p
    return None


def parse_presses(text: str) -> list[tuple[int, str]]:
    out = []
    for item in [x.strip() for x in text.split(',') if x.strip()]:
        f, _, b = item.partition(':')
        b = b.strip().upper()
        if not f.strip().isdigit() or b not in BUTTONS:
            raise ValueError(f'pressione non valida: {item!r} (formato FRAME:TASTO, tasti {", ".join(BUTTONS)})')
        out.append((int(f), b))
    out.sort()
    return out


def build_route(presses, start_frame: int, hold: int):
    """Passi run-length (frame, tasti) a partire da start_frame."""
    steps, cursor = [], start_frame
    for f, b in presses:
        if f < cursor:
            raise ValueError(f'pressione al frame {f} troppo vicina alla precedente o all\'inizio ({cursor})')
        if f > cursor:
            steps.append((f - cursor, BUTTONS['NONE']))
        steps.append((hold, BUTTONS[b]))
        cursor = f + hold
    steps.append((30, BUTTONS['NONE']))
    return steps


def perf_block(p):
    """frame_perf: i valori medi stanno in p['all'] (formato attuale) o al primo livello."""
    if not isinstance(p, dict):
        return None
    blk = p.get('all') if isinstance(p.get('all'), dict) else p
    return blk if 'total_ms_avg' in blk else None


def nm_symbols(exe: Path):
    """(rva, nome) ordinati dalla tabella dei simboli dell'eseguibile (llvm-nm del toolchain)."""
    nm = shutil.which('llvm-nm') or shutil.which('nm')
    if not nm:
        return None, 'llvm-nm non trovato'
    try:
        out = subprocess.run([nm, '--defined-only', str(exe)], capture_output=True, text=True,
                             errors='replace', timeout=180).stdout
    except Exception as e:  # noqa: BLE001
        return None, f'llvm-nm fallito: {e}'
    with open(exe, 'rb') as f:
        head = f.read(4096)
    base, size = 0, None
    if head[:2] == b'MZ':
        pe = int.from_bytes(head[0x3C:0x40], 'little')
        magic = int.from_bytes(head[pe + 24:pe + 26], 'little')
        base = int.from_bytes(head[pe + 48:pe + 56], 'little') if magic == 0x20B else \
            int.from_bytes(head[pe + 52:pe + 56], 'little')
        size = int.from_bytes(head[pe + 80:pe + 84], 'little')
    table = []
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] in ('T', 't'):
            try:
                table.append((int(parts[0], 16) - base, parts[2]))
            except ValueError:
                pass
    table.sort()
    if not table:
        return None, f'nessun simbolo da {Path(nm).name}'
    return {'table': table, 'keys': [t[0] for t in table], 'size': size}, \
        f'{len(table)} simboli da {Path(nm).name}'


def name_profile(prof, table):
    """Raggruppa i campioni di host_profile per funzione (o per modulo se fuori dall'exe)."""
    if not isinstance(prof, dict) or not prof.get('ok'):
        return None
    per = {}
    for rva_s, n in prof.get('top', []):
        rva = int(rva_s, 16)
        name = f'rva {rva_s}'
        if table:
            if table['size'] is not None and rva >= table['size']:
                name = "(fuori dall'eseguibile: driver, sistema, attese)"
            else:
                i = bisect.bisect_right(table['keys'], rva) - 1
                if i >= 0:
                    name = table['table'][i][1]
        per[name] = per.get(name, 0) + n
    total = prof.get('samples') or 1
    return {'samples': prof.get('samples'), 'modules': prof.get('modules'),
            'functions': sorted(([k, v, round(100.0 * v / total, 1)] for k, v in per.items()),
                                key=lambda x: -x[1])}


def write_profile(path: Path, title: str, named) -> None:
    lines = [title]
    if not named:
        lines.append('profilo non disponibile')
    else:
        total = named['samples'] or 1
        lines.append(f"campioni: {named['samples']} (1 al millisecondo, thread di emulazione)")
        lines.append('per modulo:')
        for m, n in sorted(named.get('modules') or [], key=lambda x: -x[1]):
            lines.append(f'  {n:7d} {100.0 * n / total:5.1f}%  {m}')
        lines.append('funzioni piu\' calde:')
        for name, n, pct in named['functions'][:60]:
            lines.append(f'  {n:7d} {pct:5.1f}%  {name}')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def ring_stats(ring, lo: int, hi: int):
    """Statistiche per frame da frame_wall_ring nella finestra [lo, hi] di frame guest."""
    if not isinstance(ring, dict) or not ring.get('ok'):
        return None
    f, st = ring.get('f') or [], ring.get('stride', 6)
    rows = [f[i:i + st] for i in range(0, len(f) - st + 1, st)]
    rows = [r for r in rows if lo <= r[0] <= hi]
    if len(rows) < 2:
        return None
    wall, interp = [], []
    for a, b in zip(rows, rows[1:]):
        df = b[0] - a[0]
        if df != 1:            # stamp mancante: l'intervallo copre piu' frame, non va contato come uno
            continue
        wall.append((b[1] - a[1]) / 1000.0)
        interp.append((b[2] - a[2]) & 0xFFFFFFFF)
    if not wall:
        return None
    ws = sorted(wall)
    return {'frame': [rows[0][0], rows[-1][0]], 'n': len(wall),
            'wall_ms_media': round(sum(wall) / len(wall), 3),
            'wall_ms_p95': round(ws[int(0.95 * (len(ws) - 1))], 3),
            'wall_ms_max': round(ws[-1], 3),
            'istr_interprete_per_frame': round(sum(interp) / len(interp)),
            'istr_interprete_max': max(interp)}


def contatori_line(r) -> str:
    """Contatori dei plugin delle mod (v11): nome=conteggio (ultimo frame)."""
    if not isinstance(r, dict) or not r.get('ok'):
        return 'contatori delle mod: non disponibili'
    c = r.get('counters') or []
    if not c:
        return 'contatori delle mod: nessuno'
    return 'contatori delle mod: ' + ', '.join(f"{x.get('name')}={x.get('count')} (frame {x.get('last_frame')})" for x in c)


def main() -> int:
    global _log_f, RITMO
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default='SLUS-01378-Rev1')
    ap.add_argument('--progetto', default='', help='cartella del progetto, dalla radice: vuoto = la radice (USA Rev 1), '
                                                  'per le altre versioni versioni/<PROFILO> (tools/versione.py)')
    ap.add_argument('--label', default='smoke')
    ap.add_argument('--end-frame', type=int, default=7200, help='frame di gioco a cui fermare la parte a velocita\' normale')
    ap.add_argument('--level-from', type=int, default=LEVEL_FROM_DEFAULT, help='primo frame considerato dentro il livello')
    ap.add_argument('--turbo-secs', type=float, default=15.0, help='secondi di misura in turbo (0 = niente turbo)')
    ap.add_argument('--no-turbo', action='store_true')
    ap.add_argument('--max-secs', type=int, default=480, help='limite di sicurezza in secondi reali')
    ap.add_argument('--presses', default=DEFAULT_PRESSES, help='FRAME:TASTO separati da virgole ("" = nessuno)')
    ap.add_argument('--shot-every', type=int, default=0, help='screenshot anche ogni N frame fino a --end-frame (v9)')
    ap.add_argument('--hires', action='store_true',
                    help='insieme a ogni screenshot anche screenshot_hires (hr_fNNNNN.png): l\'immagine alla '
                         'risoluzione interna, quella che vede il giocatore (v10)')
    ap.add_argument('--wide', action='store_true',
                    help='anche l\'immagine larga del widescreen native-wide (screenshot_wide_hires, v12)')
    ap.add_argument('--hold', type=int, default=8, help='frame per cui tenere premuto ogni tasto')
    ap.add_argument('--env', action='append', default=[], help='CHIAVE=VALORE per il processo del gioco')
    ap.add_argument('--forensic', action='store_true', help='lascia attivi display ring e debug toggles')
    ap.add_argument('--cpu', choices=('meta', 'tutti'), default='meta',
                    help="meta = prima meta' dei processori logici (default), tutti = nessun limite")
    args = ap.parse_args()
    if args.no_turbo:
        args.turbo_secs = 0
    RITMO = 50.0 if args.profile.upper().startswith('SLES') else NTSC

    out = ROOT / 'work' / 'm2' / args.label
    out.mkdir(parents=True, exist_ok=True)
    _log_f = open(out / 'smoke_log.txt', 'w', encoding='utf-8', errors='replace')
    log(f'EnterElectro-Recomp - test m2_smoke v13 - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}')
    try:
        presses = parse_presses(args.presses)
    except ValueError as e:
        log('ERRORE:', e)
        return 1
    proj = ROOT
    if args.progetto:
        proj = Path(args.progetto) if Path(args.progetto).is_absolute() else (ROOT / args.progetto)
    if not (proj / 'game.toml').is_file():
        log(f'ERRORE: game.toml non trovato nel progetto {proj}')
        return 1
    exe = find_exe(proj)
    if exe is None:
        log(f'ERRORE: eseguibile non trovato in build-dev/ o build-release/ di {proj}')
        return 1
    cues = sorted((ROOT / 'input' / args.profile).glob('*.cue'))
    if not cues:
        log(f'ERRORE: nessun .cue in input/{args.profile}')
        return 1
    cue = cues[0]
    for old in list(out.glob('shot_*.png')) + list(out.glob('host_profile_*.txt')):
        old.unlink()

    extra = {}
    if not args.forensic:
        extra.update({'PSX_DISPLAY_RING': '0', 'PSX_DEBUG_TOGGLES': '0'})
    for kv in args.env:
        if '=' not in kv:
            log(f'ERRORE: --env {kv!r} non e\' nel formato CHIAVE=VALORE')
            return 1
        k, v = kv.split('=', 1)
        extra[k.strip()] = v
    env = dict(os.environ, **extra)
    cmd = [str(exe), '--no-launcher', '--game', str(proj / 'game.toml'), '--disc', str(cue),
           '--debug-port', str(PORT)]
    pc = {'computer': os.environ.get('COMPUTERNAME') or platform.node(),
          'processore': os.environ.get('PROCESSOR_IDENTIFIER') or platform.processor(),
          'processori_logici': os.cpu_count()}
    busy = busy_compilers()
    cpu = limit_cpu_half() if args.cpu == 'meta' else {'applicato': False, 'motivo': '--cpu tutti'}
    log_d = {'versione': 12, 'progetto': str(proj), 'pc': pc, 'exe': str(exe), 'cmd': cmd, 'env_extra': extra,
             'presses': presses, 'events': [], 'timeline': [], 'compilatori_attivi_alla_partenza': busy,
             'limite_cpu': cpu}
    if busy:
        log('ATTENZIONE: altri compilatori in esecuzione (' + ', '.join(busy) + '): le misure di velocita\' '
            'potrebbero essere falsate, meglio ripetere il test a PC libero')
    log('avvio:', ' '.join(cmd))
    log('variabili:', ' '.join(f'{k}={v}' for k, v in extra.items()) or '(nessuna)')
    log('limite CPU:', json.dumps(cpu, ensure_ascii=True))
    log('tasti (frame:tasto):', ', '.join(f'{f}:{b}' for f, b in presses) or 'nessuno')
    out_f = open(out / 'runtime_output.txt', 'w', encoding='utf-8', errors='replace')
    proc = subprocess.Popen(cmd, cwd=str(exe.parent), env=env, stdout=out_f, stderr=subprocess.STDOUT)
    t0 = time.time()

    def alive() -> bool:
        return proc.poll() is None

    def finish(code: int) -> int:
        out_f.close()
        (out / 'smoke.json').write_text(json.dumps(log_d, indent=1), encoding='utf-8')
        if _log_f:
            _log_f.close()
        return code

    dbg = Dbg(PORT)
    if not dbg.connect(90):
        rc = proc.poll()
        log(f'ERRORE: server di debug non raggiungibile entro 90 s (processo: {"terminato rc=" + str(rc) if rc is not None else "ancora vivo"})')
        log_d['result'] = 'no_debug_server'
        if rc is None:
            proc.kill()
        return finish(1)
    log(f'collegato al server di debug dopo {time.time() - t0:.1f} s')

    # ---- sequenza di tasti a frame esatti
    route_info = None
    if presses:
        # margine: ogni passo della sequenza e' una chiamata al server mentre il gioco va avanti
        # (v9: con 71 passi 60 frame non bastavano e la sequenza partiva in ritardo). v13: se la sequenza parte
        # lo stesso in ritardo (il runtime risponde con un start_frame diverso), si ferma e si riprova con un
        # margine tre volte piu' grande, fino a 4 tentativi.
        margine, tentativi, ok, r, steps, bad, start = 60, [], False, None, [], [], None
        for _tentativo in range(4):
            f_now = dbg.frame() or 0
            n_steps = len(build_route(presses, max(f_now, 120), args.hold))
            start = max(f_now + margine + 3 * n_steps, 120)
            if start >= presses[0][0]:
                log(f'ERRORE: il gioco e\' gia\' al frame {f_now}, troppo vicino alla prima pressione ({presses[0][0]})')
                proc.kill()
                return finish(1)
            steps = build_route(presses, start, args.hold)
            dbg.call('input_route_clear')
            bad = [r for r in (dbg.call('input_route_append', frames=n, buttons=b) for n, b in steps)
                   if not (isinstance(r, dict) and r.get('ok'))]
            r = dbg.call('input_route_start', at_frame=start)
            ok = not bad and isinstance(r, dict) and r.get('ok') and r.get('start_frame') == start
            if ok:
                break
            tentativi.append({'start_frame': start, 'risposta': r, 'errori': bad})
            log(f'sequenza di tasti partita in ritardo (chiesto il frame {start}, risposta {json.dumps(r)}): '
                f'la riprogrammo con piu\' margine')
            dbg.call('input_route_stop')
            dbg.call('input_route_clear')
            margine *= 3
        route_info = {'start_frame': start, 'steps': len(steps), 'append_errors': bad, 'start_reply': r,
                      'tentativi_falliti': tentativi}
        log(f"sequenza di tasti programmata: {len(steps)} passi dal frame {start} -> {'OK' if ok else 'ERRORE ' + json.dumps(r)}")
        if not ok:
            proc.kill()
            return finish(1)
    log_d['route'] = route_info

    # ---- parte a velocita' normale fino a end_frame
    shots = [f for f in SHOT_FRAMES if f <= args.end_frame]
    if args.shot_every > 0:
        shots = sorted(set(shots) | set(range(args.shot_every, args.end_frame + 1, args.shot_every)))
    if args.end_frame not in shots:
        shots.append(args.end_frame)
    next_tl, n_perf, frame, lvl_mark = 0.0, 0, 0, False
    shot_idx = 0
    while alive() and time.time() - t0 < args.max_secs:
        frame = dbg.frame()
        now = round(time.time() - t0, 2)
        if frame is None:
            time.sleep(0.3)
            continue
        if now >= next_tl or (frame >= args.level_from and not lvl_mark):
            log_d['timeline'].append([now, frame])
            next_tl = now + 5.0
            lvl_mark = lvl_mark or frame >= args.level_from
        if shot_idx < len(shots) and frame >= shots[shot_idx]:
            target = shots[shot_idx]
            shot_idx += 1
            path = out / f'shot_f{target:05d}.png'
            r = dbg.call('screenshot', path=str(path))
            ev = {'t': now, 'frame': frame, 'evento': 'screenshot', 'file': path.name, 'risposta': r}
            if args.hires:
                path_hr = out / f'hr_f{target:05d}.png'
                ev['hires'] = {'file': path_hr.name, 'risposta': dbg.call('screenshot_hires', path=str(path_hr), timeout=30)}
            if args.wide:
                path_wr = out / f'wr_f{target:05d}.png'
                ev['wide'] = {'file': path_wr.name, 'risposta': dbg.call('screenshot_wide_hires', path=str(path_wr), timeout=30)}
            n_perf += 1
            if n_perf % 3 == 1:
                ev['frame_perf'] = dbg.call('frame_perf')
            log_d['events'].append(ev)
            log(json.dumps({k: v for k, v in ev.items() if k != 'frame_perf'}, ensure_ascii=True)[:260])
        if frame >= args.end_frame:
            break
        time.sleep(0.1)
    if not isinstance(frame, int):     # ultima lettura fallita: vale l'ultimo frame noto
        frame = max([p[1] for p in log_d['timeline'] if isinstance(p[1], int)], default=0)
    t_end_paced, f_end_paced = time.time() - t0, frame
    log_d['timeline'].append([round(t_end_paced, 2), f_end_paced])
    reached = alive() and isinstance(f_end_paced, int) and f_end_paced >= args.end_frame
    if not alive():
        log(f'ATTENZIONE: il gioco si e\' chiuso da solo (rc={proc.returncode}) a {time.time() - t0:.0f} s')
    elif not reached:
        log(f'ATTENZIONE: limite di {args.max_secs} s raggiunto al frame {f_end_paced}')

    table, nm_note = (None, 'non richiesto')
    named_level = named_turbo = None
    turbo = None
    if alive():
        log_d['frame_perf'] = dbg.call('frame_perf')   # ultimi 256 frame a ritmo normale, prima del turbo
        table, nm_note = nm_symbols(exe)
        log('simboli per il profilo:', nm_note)
        lo = args.level_from if f_end_paced > args.level_from + 300 else max(0, f_end_paced - 900)
        prof = dbg.call('host_profile', frame_lo=lo, frame_hi=f_end_paced, top=300, timeout=60)
        log_d['host_profile_livello'] = prof
        named_level = name_profile(prof, table)
        write_profile(out / 'host_profile_livello.txt',
                      f'profilo CPU a velocita\' normale, frame {lo}-{f_end_paced}', named_level)

        # ---- turbo: niente limite dei 60 frame/s e niente presentazione
        if args.turbo_secs > 0:
            f_a, ta = dbg.frame(), time.time()
            r_on = dbg.call('turbo', enabled=1)
            time.sleep(args.turbo_secs)
            f_b, tb = dbg.frame(), time.time()
            r_off = dbg.call('turbo', enabled=0)
            turbo = {'on': r_on, 'off': r_off, 'frame_da': f_a, 'frame_a': f_b, 'secondi': round(tb - ta, 2)}
            if isinstance(f_a, int) and isinstance(f_b, int) and tb > ta and f_b > f_a:
                fps = (f_b - f_a) / (tb - ta)
                turbo.update({'frame_al_secondo': round(fps, 1), 'percento_tempo_reale': round(100 * fps / RITMO, 1),
                              'ms_per_frame': round(1000.0 / fps, 3)})
                prof_t = dbg.call('host_profile', frame_lo=f_a, frame_hi=f_b, top=300, timeout=60)
                log_d['host_profile_turbo'] = prof_t
                named_turbo = name_profile(prof_t, table)
                write_profile(out / 'host_profile_turbo.txt',
                              f'profilo CPU in turbo, frame {f_a}-{f_b}', named_turbo)
            log_d['turbo'] = turbo
            log('turbo:', json.dumps({k: v for k, v in turbo.items() if k not in ('on', 'off')}))
            time.sleep(1.0)
            path = out / 'shot_dopo_turbo.png'
            r = dbg.call('screenshot', path=str(path))
            ev_t = {'t': round(time.time() - t0, 2), 'frame': dbg.frame(),
                    'evento': 'screenshot', 'file': path.name, 'risposta': r}
            if args.hires:
                path_hr = out / 'hr_dopo_turbo.png'
                ev_t['hires'] = {'file': path_hr.name, 'risposta': dbg.call('screenshot_hires', path=str(path_hr), timeout=30)}
            log_d['events'].append(ev_t)

        ring = dbg.call('frame_wall_ring', n=60000, timeout=60)
        fe = f_b if (turbo and isinstance(turbo.get('frame_a'), int)) else f_end_paced
        log_d['ring_stats'] = {
            'avvio_e_filmati': ring_stats(ring, 1, 3600),
            'menu_e_caricamento': ring_stats(ring, 3600, args.level_from),
            'livello': ring_stats(ring, args.level_from, f_end_paced),
            'turbo': ring_stats(ring, turbo['frame_da'], fe) if turbo and isinstance(turbo.get('frame_da'), int) else None,
        }
        for c in END_CMDS:
            log_d[c] = dbg.call(c)
        if args.wide:
            log_d['ws_nw'] = dbg.call('ws_nw')
        # codice statico (Milestone 3): quante volte il gioco e' entrato nel codice compilato in
        # anticipo, in tutto e nella zona dei moduli caricati nell'heap
        log_d['overlay_static_entries'] = dbg.call('overlay_static_entries', limit=32)
        log_d['overlay_static_moduli'] = dbg.call('overlay_static_entries', addr_lo='0x80100000',
                                                  addr_hi='0x80200000', limit=32)
        dbg.call('quit')
        for _ in range(50):
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        if proc.poll() is None:
            proc.kill()
    out_f.close()
    out_f = open(os.devnull, 'w')

    # perche' si e' chiuso (rapporto scritto dal runtime all'uscita)
    rep = exe.parent / 'psx_last_run_report.json'
    exit_origin = None
    try:
        if rep.is_file() and rep.stat().st_mtime >= t0 - 1:
            j = json.loads(rep.read_text(encoding='utf-8', errors='replace'))
            exit_origin = {'reason': j.get('reason'), 'exit_origin': j.get('exit_origin'), 'frame': j.get('frame')}
    except Exception as e:  # noqa: BLE001
        exit_origin = {'errore': str(e)}
    log_d['uscita'] = exit_origin

    tl = log_d['timeline']
    speed = None
    if len(tl) >= 2 and tl[-1][0] > tl[0][0]:
        speed = round(100.0 * (tl[-1][1] - tl[0][1]) / (tl[-1][0] - tl[0][0]) / RITMO, 1)
    lvl = [p for p in tl if p[1] >= args.level_from]
    speed_lvl = None
    if len(lvl) >= 2 and lvl[-1][0] > lvl[0][0]:
        speed_lvl = round(100.0 * (lvl[-1][1] - lvl[0][1]) / (lvl[-1][0] - lvl[0][0]) / RITMO, 1)
    perfs = [perf_block(e.get('frame_perf')) for e in log_d['events']]
    perfs = [p for p in perfs if p]
    last_perf = perf_block(log_d.get('frame_perf')) or (perfs[-1] if perfs else None)
    shots_ok = [e for e in log_d['events'] if e.get('evento') == 'screenshot'
                and isinstance(e.get('risposta'), dict) and e['risposta'].get('ok')]
    ols = log_d.get('overlay_loader_status') if isinstance(log_d.get('overlay_loader_status'), dict) else {}
    log_d['result'] = {
        'arrivato_al_frame_finale': reached, 'frame_finale': f_end_paced,
        'secondi_parte_normale': round(t_end_paced, 1), 'screenshot_ok': len(shots_ok),
        'velocita_percento_tempo_reale': speed, 'velocita_nel_livello': speed_lvl,
        'turbo': {k: v for k, v in (turbo or {}).items() if k not in ('on', 'off')} or None,
        'frame_perf_ultimo': last_perf, 'uscita': exit_origin,
    }

    def short(x, n=220):
        return json.dumps(x)[:n]
    rs = log_d.get('ring_stats') or {}

    def static_line(r, name):
        if not isinstance(r, dict) or not r.get('ok'):
            return f"{name}: non disponibile ({short(r, 120)})"
        return (f"{name}: {r.get('range_entries')} punti d'ingresso, {r.get('range_hit_entries')} usati, "
                f"{r.get('range_hits')} ingressi")

    def ring_line(name, key):
        s = rs.get(key)
        if not s:
            return f'  {name}: non disponibile'
        return (f"  {name} (frame {s['frame'][0]}-{s['frame'][1]}): {s['wall_ms_media']} ms/frame in media, "
                f"p95 {s['wall_ms_p95']}, max {s['wall_ms_max']}; interprete {s['istr_interprete_per_frame']} istruzioni/frame")
    top_fn = (named_turbo or named_level or {}).get('functions') or []
    summary = [
        'EnterElectro-Recomp - test di avvio / prestazioni (m2_smoke v13)',
        f'etichetta: {args.label}   data: {datetime.datetime.now():%Y-%m-%d %H:%M}',
        f"PC: {pc['computer']} - {pc['processore']} - {pc['processori_logici']} processori logici",
        ('altri compilatori attivi alla partenza: ' + (', '.join(busy) + ' -> MISURE DA RIPETERE A PC LIBERO'
                                                      if busy else 'nessuno')) if busy is not None
        else 'altri compilatori attivi alla partenza: non verificato',
        f'eseguibile: {exe}',
        f'disco: {cue.name}',
        'variabili: ' + (' '.join(f'{k}={v}' for k, v in extra.items()) or '(nessuna)'),
        'limite CPU: ' + (f"prima meta' dei processori logici ({cpu['usati']} su {cpu['processori_logici']}, "
                          f"maschera {cpu['maschera']})" if cpu.get('applicato') else f"nessuno ({cpu.get('motivo')})"),
        'tasti (frame:tasto): ' + (', '.join(f'{f}:{b}' for f, b in presses) or 'nessuno'),
        f"arrivato al frame {args.end_frame}: {'SI' if reached else 'NO'} (ultimo frame letto: {f_end_paced}, dopo {t_end_paced:.0f} s)",
        f"chiusura del gioco: {short(exit_origin, 160)}",
        f"screenshot salvati: {len(shots_ok)} (work\\m2\\{args.label}\\shot_f*.png)"
        + (f", ad alta risoluzione: {sum(1 for e in log_d['events'] if isinstance((e.get('hires') or {}).get('risposta'), dict) and e['hires']['risposta'].get('ok'))} (hr_f*.png)"
           if args.hires else ''),
        f"velocita' media a ritmo normale: {speed if speed is not None else '?'}% del tempo reale ({RITMO} frame/s)",
        f"velocita' nel livello: {speed_lvl if speed_lvl is not None else '?'}%",
        ('turbo: ' + (f"{turbo.get('frame_al_secondo')} frame/s = {turbo.get('percento_tempo_reale')}% del tempo reale, "
                      f"{turbo.get('ms_per_frame')} ms di CPU per frame" if turbo and turbo.get('frame_al_secondo')
                      else 'non misurato')),
        'tempi per frame (dal runtime):',
        ring_line('avvio e filmati', 'avvio_e_filmati'),
        ring_line('menu e caricamento', 'menu_e_caricamento'),
        ring_line('livello, ritmo normale', 'livello'),
        ring_line('livello, turbo', 'turbo'),
        (f"overlay: chiamate native {ols.get('dispatch_native')}, all'interprete {ols.get('dispatch_interp_fallback')}, "
         f"DLL caricate {ols.get('loads')}" if ols else 'overlay_loader_status: non disponibile'),
        static_line(log_d.get('overlay_static_entries'), 'codice statico (tutto)'),
        static_line(log_d.get('overlay_static_moduli'), "codice statico dei moduli (0x80100000-0x80200000)"),
        f"dispatch miss (funzioni non ricompilate raggiunte): {short(log_d.get('unknown_dispatch_log'), 160)}",
        f"segment miss: {short(log_d.get('segment_misses'), 160)}",
        ('ultimo frame_perf (ms): ' + ', '.join(f'{k}={last_perf.get(k)}' for k in
            ('total_ms_avg', 'emu_cpu_ms_avg', 'present_wall_ms_avg', 'scene_gpu_ms_avg', 'present_gpu_ms_avg'))
         if last_perf else 'frame_perf: non disponibile'),
        f"risoluzione interna: {short(log_d.get('video_info'), 200)}",
        contatori_line(log_d.get('mod_counters')),
        *( [f"widescreen native-wide: {short(log_d.get('ws_nw'), 200)}; immagini larghe salvate: "
            f"{sum(1 for e in log_d['events'] if isinstance((e.get('wide') or {}).get('risposta'), dict) and e['wide']['risposta'].get('ok'))} (wr_f*.png)"] if args.wide else []),
        f'simboli per il profilo: {nm_note}',
        'funzioni piu\' calde (' + ('turbo' if named_turbo else 'livello') + '):',
    ] + [f'  {pct:5.1f}%  {name}' for name, n, pct in top_fn[:12]]
    (out / 'm2_summary.txt').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    log('\n'.join(summary))
    return finish(0 if reached else 2)


if __name__ == '__main__':
    raise SystemExit(main())
