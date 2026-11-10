#!/usr/bin/env python3
"""EnterElectro-Recomp - prova del PC: il gioco va a piena velocita' su questo computer?

Pensata per i PC meno potenti (per esempio un portatile). Si lancia con un doppio clic su PROVA-PC.cmd, nella
cartella del pacchetto, dopo aver aggiunto almeno un disco con SM2-Launcher. In ordine:
  1. legge processore, numero di processori logici, memoria e sistema;
  2. sceglie la versione del gioco: --profilo, altrimenti la prima gia' installata o con il disco aggiunto
     (in quest'ordine: USA Rev 1, USA, Europa Rev 1, Europa, Francia, Germania);
  3. se serve la (re)installa con il PGO e con l'eseguibile di prova (installa --pgo --debug, con il PGXP se
     l'installazione di prima lo aveva): sui PC lenti puo' volerci piu' di mezz'ora, una volta sola;
  4. test di avvio con l'eseguibile di prova (tools/m2_smoke.py, tutti i processori): il gioco si apre, arriva al
     primo livello premendo da solo i tasti (quelli di m2_smoke per le versioni americane; START e X ogni 150 frame
     per le europee, START e CERCHIO per la giapponese, che conferma i menu con il cerchio) e misura la velocita'
     rispetto al tempo reale, in tutto e nel livello, e quanto va veloce senza il limite dei 60 frame al secondo
     (turbo); circa 3 minuti;
  5. CPU dell'eseguibile con cui si gioca (tools/misura_cpu.py: 60 secondi a finestra nascosta, senza tasti);
  6. scrive work/prova_pc/rapporto.txt e lo zip work/prova_pc/EnterElectro-Recomp-prova-pc-<data>.zip, da mandare a chi
     segue il progetto (contiene solo testi e misure, niente del gioco).
L'audio resta spento durante le misure. Non cambia niente nel sistema; le opzioni del giocatore restano com'erano.

L'eseguibile di prova ha il server di debug e non ha il PGO, quindi e' un po' piu' lento di quello con cui si gioca:
se questo va a piena velocita', quello va di sicuro.

Uso:  PROVA-PC.cmd [--profilo SLUS-01378-Rev1] [--senza-installare] [--secondi-cpu 60] [--cpu tutti|meta]
                   [--lingua it|en]
(--cpu meta lascia al gioco solo la prima meta' dei processori logici, per provare il kit su un PC su cui gira
anche altro; di default il gioco li usa tutti, come quando ci si gioca.)

v2 (4/11/2026, QA-009): nel test di avvio il controllo di blocco dell'eseguibile di prova (PSX_STARVATION_TIMEOUT_US,
solo con il server di debug) aspetta 60 secondi invece di 4: sui PC lenti chiudeva il gioco all'avvio, una volta su
due. L'eseguibile con cui si gioca non ha questo controllo.

v3 (4/11/2026): messaggi e rapporto in italiano o in inglese, come il launcher (tools/sm2_lingua.py: --lingua it|en,
poi la variabile SM2_LINGUA, poi lingua.txt scritto dalla finestra del launcher, poi la lingua di Windows); nomi
inglesi delle opzioni: --profile, --no-install, --cpu-seconds, --cpu all|half, --language. I nomi dei file e le
chiavi di rapporto.json restano uguali.

English: EnterElectro-Recomp PC test - does the game run at full speed on this computer? Double-click PROVA-PC.cmd in the
package folder after adding at least one disc with SM2-Launcher. It installs the game version with PGO and the test
executable if needed (on slow PCs this can take more than half an hour, only once), runs a start-up test (the game
goes by itself to the first level and measures its speed, about 3 minutes), measures the CPU used by the game
executable for 60 seconds, then writes work/prova_pc/rapporto.txt and the zip work/prova_pc/EnterElectro-Recomp-prova-pc-<date>.zip
to send to the project (it contains only texts and measurements, nothing from the game). Audio stays off during the
measurements; nothing in the system and none of the player's options are changed.
Usage: PROVA-PC.cmd [--profile SLUS-01378-Rev1] [--no-install] [--cpu-seconds 60] [--cpu all|half] [--language it|en]
"""
from __future__ import annotations

import argparse
import ctypes
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sm2_lingua import T, imposta as imposta_lingua  # noqa: E402
ROOT = HERE.parent
GIOCHI = ROOT / 'giochi'
INPUT = ROOT / 'input'
USCITA = ROOT / 'work' / 'prova_pc'
ORDINE = ['SLUS-01378-Rev1', 'SLUS-01378', 'SLES-03623-Rev1', 'SLES-03623', 'SLES-03624', 'SLES-03625',
          'SLPM-87073']
EXE = 'SpiderMan2EnterElectro.exe'
SENZA_AUDIO = {'SDL_AUDIO_DRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'}
# tasti per le versioni non americane (come tools/m3_prova/basi_livelli.py, TASTI_ALTRE): START ogni 150 frame sul
# titolo, poi X ogni 150 frame per menu, NEW GAME, difficolta' e filmati; vanno bene anche a 50 frame al secondo.
# La versione giapponese conferma i menu con il cerchio (con la X resta sul menu e parte la demo del titolo).
TASTI_ALTRE = ','.join([f'{f}:START' for f in range(2400, 3901, 150)] + [f'{f}:CROSS' for f in range(2475, 7101, 150)])


def scrivi(riga: str = '') -> None:
    print(riga, flush=True)
    with open(USCITA / 'prova_pc_log.txt', 'a', encoding='utf-8') as f:
        f.write(riga + '\n')


def info_pc() -> dict:
    info = {'computer': platform.node(), 'sistema': platform.platform(), 'processori_logici': os.cpu_count(),
            'processore': platform.processor()}
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                info['processore'] = str(winreg.QueryValueEx(k, 'ProcessorNameString')[0]).strip()
        except OSError:
            pass
        try:
            class Memoria(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            m = Memoria()
            m.dwLength = ctypes.sizeof(Memoria)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                info['memoria_gb'] = round(m.ullTotalPhys / 2 ** 30, 1)
        except (OSError, AttributeError):
            pass
    return info


def stato_installazione(prof: str) -> dict:
    try:
        return json.loads((GIOCHI / prof / 'installazione.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def disco_presente(prof: str) -> bool:
    cartella = INPUT / prof
    return cartella.is_dir() and any(p.suffix.lower() in ('.cue', '.iso', '.bin', '.chd') for p in cartella.iterdir())


def scegli_versione(voluta: str) -> str | None:
    if voluta:
        return voluta
    for prof in ORDINE:
        if stato_installazione(prof).get('completata'):
            return prof
    for prof in ORDINE:
        if disco_presente(prof):
            return prof
    return None


def lancia(cmd: list, nome: str, env_extra: dict | None = None) -> int:
    """Lancia un comando, scrive l'uscita in work/prova_pc/<nome>.txt e restituisce il codice di uscita."""
    env = dict(os.environ, **(env_extra or {}))
    with open(USCITA / f'{nome}.txt', 'w', encoding='utf-8', errors='replace') as out:
        r = subprocess.run(cmd, cwd=str(ROOT), env=env, stdout=out, stderr=subprocess.STDOUT)
    return r.returncode


def lingua_da_argomenti(argv: list) -> str:
    """--lingua / --language letta prima di argparse, cosi' anche l'aiuto (-h) e' nella lingua scelta."""
    for i, a in enumerate(argv):
        for nome in ('--lingua', '--language'):
            if a == nome and i + 1 < len(argv):
                return argv[i + 1]
            if a.startswith(nome + '='):
                return a.split('=', 1)[1]
    return ''


def main() -> int:
    imposta_lingua(lingua_da_argomenti(sys.argv[1:]))
    ap = argparse.ArgumentParser(description=T('EnterElectro-Recomp - prova del PC: il gioco va a piena velocita\' su questo '
                                               'computer?', 'EnterElectro-Recomp - PC test: does the game run at full speed '
                                               'on this computer?'))
    ap.add_argument('--profilo', '--profile', dest='profilo', default='', metavar=T('VERSIONE', 'VERSION'),
                    help=T('versione da provare (di default la prima installata o con il disco)',
                           'game version to test (by default the first one installed or with a disc)'))
    ap.add_argument('--senza-installare', '--no-install', dest='senza_installare', action='store_true',
                    help=T('non reinstalla anche se manca qualcosa', 'do not reinstall even if something is missing'))
    ap.add_argument('--secondi-cpu', '--cpu-seconds', dest='secondi_cpu', type=int, default=60,
                    metavar=T('SECONDI', 'SECONDS'),
                    help=T('secondi della misura della CPU', 'seconds of the CPU measurement'))
    ap.add_argument('--cpu', choices=('tutti', 'meta', 'all', 'half'), default='tutti',
                    help=T('processori per il gioco durante le misure: tutti (all) o la prima meta\' (half)',
                           'processors for the game during the measurements: all (tutti) or the first half (meta)'))
    ap.add_argument('--lingua', '--language', dest='lingua', choices=('it', 'en'), default=None,
                    help=T('lingua dei messaggi e del rapporto (di default quella scelta nel launcher o quella di '
                           'Windows)', 'language of the messages and of the report (by default the one chosen in the '
                           'launcher, or the Windows one)'))
    args = ap.parse_args()
    if args.lingua:
        imposta_lingua(args.lingua)
    args.cpu = {'all': 'tutti', 'half': 'meta'}.get(args.cpu, args.cpu)
    USCITA.mkdir(parents=True, exist_ok=True)
    inizio = time.time()
    ora = datetime.datetime.now()
    scrivi(T(f'== EnterElectro-Recomp, prova del PC - {ora:%Y-%m-%d %H:%M}', f'== EnterElectro-Recomp, PC test - {ora:%Y-%m-%d %H:%M}'))
    pc = info_pc()
    scrivi(T(f'   processore: {pc.get("processore")}; processori logici: {pc.get("processori_logici")}; '
             f'memoria: {pc.get("memoria_gb", "?")} GB; sistema: {pc.get("sistema")}',
             f'   processor: {pc.get("processore")}; logical processors: {pc.get("processori_logici")}; '
             f'memory: {pc.get("memoria_gb", "?")} GB; system: {pc.get("sistema")}'))
    prof = scegli_versione(args.profilo)
    if not prof:
        scrivi(T('ERRORE: nessun disco aggiunto. Apri SM2-Launcher, premi "Aggiungi un disco..." e scegli il dump del '
                 'gioco, poi rilancia PROVA-PC.',
                 'ERROR: no disc added. Open SM2-Launcher, press "Add a disc..." and choose the game dump, then run '
                 'PROVA-PC again.'))
        return 1
    st = stato_installazione(prof)
    ha_prova = (GIOCHI / prof / 'build-dev' / EXE).is_file()
    scrivi(T(f'   versione: {prof}; installazione: launcher {st.get("launcher", "-")}, completata '
             f'{bool(st.get("completata"))}, PGO {bool(st.get("pgo"))}, eseguibile di prova {ha_prova}',
             f'   version: {prof}; installation: launcher {st.get("launcher", "-")}, complete '
             f'{bool(st.get("completata"))}, PGO {bool(st.get("pgo"))}, test executable {ha_prova}'))
    risultati = {'pc': pc, 'versione': prof, 'data': f'{ora:%Y-%m-%d %H:%M}', 'processori_per_il_gioco': args.cpu}

    # 1) installazione con il PGO e l'eseguibile di prova, se serve
    serve = not (st.get('completata') and st.get('pgo') and (GIOCHI / prof / 'build-dev' / EXE).is_file()
                 and (GIOCHI / prof / 'build-release' / EXE).is_file())
    if serve and args.senza_installare:
        scrivi(T('ERRORE: la versione non e\' installata con il PGO e l\'eseguibile di prova, e hai chiesto di non '
                 'reinstallare',
                 'ERROR: this version is not installed with PGO and the test executable, and you asked not to '
                 'reinstall it'))
        return 1
    if serve:
        if not disco_presente(prof):
            scrivi(T(f'ERRORE: manca il disco di {prof} in input\\{prof}: aggiungilo con SM2-Launcher',
                     f'ERROR: the {prof} disc is missing in input\\{prof}: add it with SM2-Launcher'))
            return 1
        cmd = [sys.executable, str(HERE / 'sm2_launcher.py'), 'installa', '--profilo', prof, '--pgo', '--debug']
        if st.get('pgxp'):
            cmd.append('--pgxp')
        scrivi(T(f'[1/3] installo {prof} con il PGO e l\'eseguibile di prova (sui PC lenti anche piu\' di mezz\'ora, '
                 f'una volta sola)...',
                 f'[1/3] installing {prof} with PGO and the test executable (on slow PCs even more than half an hour, '
                 f'only once)...'))
        t0 = time.time()
        codice = lancia(cmd, 'installazione', SENZA_AUDIO)
        risultati['installazione'] = {'secondi': round(time.time() - t0), 'codice': codice}
        scrivi(T(f'      fatta in {round(time.time() - t0)} s, codice {codice}',
                 f'      done in {round(time.time() - t0)} s, exit code {codice}'))
        if codice != 0:
            scrivi(T('ERRORE: installazione non riuscita (dettagli in work\\prova_pc\\installazione.txt)',
                     'ERROR: installation failed (details in work\\prova_pc\\installazione.txt)'))
            return 1
    else:
        scrivi(T('[1/3] installazione gia\' pronta (PGO ed eseguibile di prova)',
                 '[1/3] installation already done (PGO and test executable)'))

    # 2) test di avvio con l'eseguibile di prova
    scrivi(T('[2/3] test di avvio: il gioco si apre, va da solo fino al primo livello e misura la velocita\' (circa 3 '
             'minuti; non toccare tastiera e mouse sulla sua finestra)...',
             '[2/3] start-up test: the game opens, goes by itself to the first level and measures its speed (about 3 '
             'minutes; do not touch the keyboard or the mouse on its window)...'))
    etichetta = 'prova_pc'
    cmd = [sys.executable, str(HERE / 'm2_smoke.py'), '--profile', prof, '--progetto', f'giochi/{prof}',
           '--label', etichetta, '--cpu', args.cpu, '--env', 'PSX_OVERLAY_AUTOCOMPILE_OFF=1',
           '--env', 'PSX_STARVATION_TIMEOUT_US=60000000']
    if not prof.startswith('SLUS'):     # m2_smoke da solo usa i tasti delle versioni americane
        cmd += ['--presses', TASTI_ALTRE.replace(':CROSS', ':CIRCLE') if prof.startswith('SLPM') else TASTI_ALTRE]
    codice = lancia(cmd, 'test_avvio', SENZA_AUDIO)
    cartella_smoke = ROOT / 'work' / 'm2' / etichetta
    try:
        smoke = json.loads((cartella_smoke / 'smoke.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        smoke = {}
    r = smoke.get('result') or {}
    livello = ((smoke.get('ring_stats') or {}).get('livello') or {})
    risultati['test_avvio'] = {
        'codice': codice, 'livello_raggiunto': r.get('arrivato_al_frame_finale'),
        'velocita_percento': r.get('velocita_percento_tempo_reale'), 'velocita_nel_livello': r.get('velocita_nel_livello'),
        'turbo_percento': (r.get('turbo') or {}).get('percento_tempo_reale'),
        'ms_per_frame_turbo': (r.get('turbo') or {}).get('ms_per_frame'),
        'ms_per_frame_livello_p95': livello.get('wall_ms_p95'),
        'funzioni_non_ricompilate': (smoke.get('unknown_dispatch_log') or {}).get('total')}
    scrivi(f'      {json.dumps(risultati["test_avvio"], ensure_ascii=False)}')

    # 3) CPU dell'eseguibile con cui si gioca
    scrivi(T(f'[3/3] CPU dell\'eseguibile con cui si gioca ({args.secondi_cpu} secondi, finestra nascosta)...',
             f'[3/3] CPU used by the game executable ({args.secondi_cpu} seconds, hidden window)...'))
    codice = lancia([sys.executable, str(HERE / 'misura_cpu.py'), '--profile', prof, '--cartelle', 'build-release',
                     '--secondi', str(args.secondi_cpu), '--giri', '1', '--uscita', 'prova_pc', '--cpu', args.cpu],
                    'misura_cpu', SENZA_AUDIO)
    try:
        cpu = json.loads((USCITA / prof / 'cpu.json').read_text(encoding='utf-8'))
        c = cpu[-1]
        risultati['cpu'] = {'secondi_cpu': c.get('cpu_secondi'), 'secondi': c.get('secondi'), 'codice': codice,
                            'per_100_secondi': round(100 * c['cpu_secondi'] / c['secondi'], 1)
                            if c.get('cpu_secondi') and c.get('secondi') else None}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        risultati['cpu'] = {'codice': codice}
    scrivi(f'      {json.dumps(risultati["cpu"], ensure_ascii=False)}')

    # rapporto
    t = risultati['test_avvio']
    v = t.get('velocita_nel_livello')
    if not t.get('livello_raggiunto'):
        giudizio = T('NON VALUTABILE: il test di avvio non e\' arrivato al livello (guarda work\\prova_pc\\test_avvio.txt '
                     'e work\\m2\\prova_pc\\)',
                     'CANNOT TELL: the start-up test did not reach the level (see work\\prova_pc\\test_avvio.txt and '
                     'work\\m2\\prova_pc\\)')
    elif isinstance(v, (int, float)) and v >= 98:
        giudizio = T('OK: il gioco va a piena velocita\' anche con l\'eseguibile di prova, che e\' il piu\' lento',
                     'OK: the game runs at full speed even with the test executable, which is the slowest one')
    elif isinstance(v, (int, float)) and v >= 90:
        giudizio = T('QUASI: l\'eseguibile di prova resta poco sotto la piena velocita\'; quello con cui si gioca (con il '
                     'PGO e senza il server di debug) e\' piu\' veloce e probabilmente basta',
                     'ALMOST: the test executable stays a little below full speed; the game executable (with PGO and '
                     'without the debug server) is faster and is probably enough')
    else:
        giudizio = T('LENTO: il gioco non tiene la piena velocita\'. Prova con la risoluzione del gioco, PGXP spento, '
                     'widescreen e distanza visiva spenti',
                     'SLOW: the game does not keep full speed. Try the game resolution, with PGXP, widescreen and '
                     'draw distance off')
    risultati['giudizio'] = giudizio
    risultati['durata_secondi'] = round(time.time() - inizio)
    rc = risultati['cpu']
    righe = [T(f'EnterElectro-Recomp - prova del PC, {risultati["data"]}', f'EnterElectro-Recomp - PC test, {risultati["data"]}'), '',
             f'Computer: {pc.get("computer")}',
             T(f'Processore: {pc.get("processore")} ({pc.get("processori_logici")} processori logici)',
               f'Processor: {pc.get("processore")} ({pc.get("processori_logici")} logical processors)'),
             T(f'Memoria: {pc.get("memoria_gb", "?")} GB', f'Memory: {pc.get("memoria_gb", "?")} GB'),
             T(f'Sistema: {pc.get("sistema")}', f'System: {pc.get("sistema")}'),
             T(f'Versione del gioco: {prof}', f'Game version: {prof}'),
             T('Processori per il gioco durante le misure: ', 'Processors for the game during the measurements: ')
             + (T('tutti', 'all') if args.cpu == 'tutti' else T('la prima meta\'', 'the first half')), '']
    if 'installazione' in risultati:
        s = risultati['installazione']['secondi']
        righe.append(T(f'Installazione con il PGO e l\'eseguibile di prova: {s} s',
                       f'Installation with PGO and the test executable: {s} s'))
    raggiunto = t.get('livello_raggiunto')
    righe += [T(f'Test di avvio (eseguibile di prova): livello raggiunto {"si" if raggiunto else "no"}; '
                f'velocita\' {t.get("velocita_percento")}% del tempo reale, nel livello {v}%; senza limite (turbo) '
                f'{t.get("turbo_percento")}% ({t.get("ms_per_frame_turbo")} ms di CPU per frame); frame nel livello: '
                f'p95 {t.get("ms_per_frame_livello_p95")} ms; funzioni non ricompilate raggiunte: '
                f'{t.get("funzioni_non_ricompilate")}',
                f'Start-up test (test executable): level reached {"yes" if raggiunto else "no"}; '
                f'speed {t.get("velocita_percento")}% of real time, in the level {v}%; without the limit (turbo) '
                f'{t.get("turbo_percento")}% ({t.get("ms_per_frame_turbo")} ms of CPU per frame); frames in the level: '
                f'p95 {t.get("ms_per_frame_livello_p95")} ms; non-recompiled functions reached: '
                f'{t.get("funzioni_non_ricompilate")}'),
              T(f'CPU dell\'eseguibile con cui si gioca: {rc.get("secondi_cpu")} s in {rc.get("secondi")} s '
                f'({rc.get("per_100_secondi")} s ogni 100 s; sul PC con l\'i9 del progetto circa 13 s con il PGO e il '
                f'salto delle attese)',
                f'CPU used by the game executable: {rc.get("secondi_cpu")} s in {rc.get("secondi")} s '
                f'({rc.get("per_100_secondi")} s every 100 s; on the project PC with the i9 about 13 s with PGO and '
                f'idle skip)'), '',
              T(f'Giudizio: {giudizio}', f'Verdict: {giudizio}'), '',
              T(f'Durata della prova: {risultati["durata_secondi"]} s', f'Test duration: {risultati["durata_secondi"]} s')]
    (USCITA / 'rapporto.txt').write_text('\n'.join(righe) + '\n', encoding='utf-8')
    (USCITA / 'rapporto.json').write_text(json.dumps(risultati, indent=1, ensure_ascii=False), encoding='utf-8')
    nome_zip = USCITA / f'EnterElectro-Recomp-prova-pc-{ora:%Y%m%d-%H%M}.zip'
    with zipfile.ZipFile(nome_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in [USCITA / 'rapporto.txt', USCITA / 'rapporto.json', USCITA / 'prova_pc_log.txt',
                  USCITA / 'installazione.txt', USCITA / 'test_avvio.txt', USCITA / 'misura_cpu.txt',
                  USCITA / prof / 'cpu.txt', USCITA / prof / 'cpu.json']:
            if f.is_file():
                z.write(f, f.relative_to(USCITA).as_posix())
        for nome in ('m2_summary.txt', 'smoke_log.txt', 'runtime_output.txt', 'shot_f06600.png', 'shot_f07200.png'):
            f = cartella_smoke / nome
            if f.is_file():
                z.write(f, f'test_avvio/{nome}')
    for riga in righe:
        scrivi(riga)
    scrivi('')
    scrivi(T(f'Rapporto: {USCITA / "rapporto.txt"}', f'Report: {USCITA / "rapporto.txt"}'))
    scrivi(T(f'Da mandare: {nome_zip}', f'To send: {nome_zip}'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
