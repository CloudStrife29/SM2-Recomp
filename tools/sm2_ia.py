# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - filmati IA (facoltativi): tre ingranditori a intelligenza artificiale tra cui il giocatore sceglie.
EnterElectro-Recomp 0.12 - AI movies (optional): three artificial-intelligence upscalers the player chooses from.

Come i filmati Migliorati, si preparano una volta sola sul PC del giocatore, dal suo disco (nel pacchetto non c'e'
nessun fotogramma del gioco), nel formato fmv_hd di psxrecomp: giochi/<VERSIONE>/filmati_ia_<modello>/. Il gioco li
usa con PSX_FMV_HD_DIR, come i Migliorati. I programmi (onnxruntime-directml, numpy) e i modelli si scaricano solo se il
giocatore lo chiede, in tools/ia/ (una volta per tutte le versioni):
  - Swin2SR per foto reali (x4, versione PSNR): pesi ufficiali di github.com/mv-lab/swin2sr (Apache 2.0) nella
    conversione ONNX di huggingface.co/Xenova; il piu' fedele e il piu' lento;
  - Real-ESRGAN general-x4v3 e animevideov3: pesi ufficiali di github.com/xinntao/Real-ESRGAN (BSD-3-Clause),
    convertiti in ONNX qui, senza torch, da sm2_ia_calcolo.esrgan_onnx; veloci e nitidi, ma inventano dettagli.
Questo modulo usa solo la libreria standard; la parte di calcolo (numpy, onnxruntime) e' in sm2_ia_calcolo.py.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

VERSIONE_ORT = '1.24.4'
VERSIONE_NUMPY = '2.5.4'
QUALITA = 90                # JPEG come i Migliorati
PESO_STABILE = 30           # % dell'immagine nuova a ogni passo della stabilizzazione (100 = niente)
FORMATO = 1                 # formato delle cartelle filmati_ia_* (cambia se cambia il modo di farle)
SCARICHI_PROGRAMMI = [('onnxruntime-directml ' + VERSIONE_ORT, 25_100_000), ('numpy ' + VERSIONE_NUMPY, 12_600_000)]
LICENZE_PROGRAMMI = ['MIT + Microsoft DirectML', 'BSD-3-Clause']

MODELLI = {
    'swin2sr': {
        'nome': 'Swin2SR', 'tipo': 'swin2sr', 'file': 'swin2sr-realworld-x4-psnr.onnx',
        'url': 'https://huggingface.co/Xenova/swin2SR-realworld-sr-x4-64-bsrgan-psnr/resolve/main/onnx/model.onnx',
        'byte': 52772645, 'sha256': 'f496dc73dcc01d778b1a12eb4c4038d6b27cd1c0b5bcd4258455ed6d7816c835',
        'licenza': 'Apache 2.0 (github.com/mv-lab/swin2sr; ONNX: huggingface.co/Xenova)',
        'titolo': ('Swin2SR (fedele)', 'Swin2SR (faithful)'),
        'descrizione': (
            "Il pi\u00f9 fedele: non inventa dettagli. Pi\u00f9 nitido dei Migliorati su volti, contorni e scritte grandi. "
            "\u00c8 il pi\u00f9 lento: con una scheda video da gioco alcune ore, con una scheda integrata giorni.",
            "The most faithful: it does not invent detail. Sharper than Enhanced on faces, edges and large text. "
            "It is the slowest: a few hours with a gaming graphics card, days with an integrated one."),
        'difetti': [
            ("le superfici con trame fini (pelle, muri, facciate) vengono un po' lisciate, effetto \"dipinto\"",
             'surfaces with fine texture (skin, walls, buildings) get a little smoothed, a "painted" look'),
            ("le scritte minuscole possono uscire con qualche lettera storta",
             'tiny text may come out with a few crooked letters'),
            ("in qualche scena i colori sono un po' pi\u00f9 saturi", 'in a few scenes colours are a little more saturated'),
            ("le scritte piccole in movimento possono tremolare un poco (ridotto dalla stabilizzazione)",
             'small moving text may wobble a little (reduced by the stabilisation)'),
        ],
    },
    'general': {
        'nome': 'Real-ESRGAN general-x4v3', 'tipo': 'srvgg', 'file': 'realesr-general-x4v3.onnx',
        'pth': 'realesr-general-x4v3.pth',
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth',
        'byte': 4885111, 'sha256': '8dc7edb9ac80ccdc30c3a5dca6616509367f05fbc184ad95b731f05bece96292',
        'sha256_onnx': 'a9ada37621f4003037c8fe94b7b7ec0e525236400a287d8012d0234d56d692c7',
        'licenza': 'BSD-3-Clause (github.com/xinntao/Real-ESRGAN)',
        'titolo': ('Real-ESRGAN general-x4v3 (nitido)', 'Real-ESRGAN general-x4v3 (sharp)'),
        'descrizione': (
            "Molto nitido e veloce: pochi minuti con una scheda video da gioco. Per sembrare pi\u00f9 definito inventa "
            "qualche dettaglio.",
            "Very sharp and fast: a few minutes with a gaming graphics card. To look more detailed it invents some "
            "detail."),
        'difetti': [
            ("inventa dettagli che non c'erano (piccole trame, pieghe, riflessi)",
             'it invents detail that was not there (small textures, creases, highlights)'),
            ("le scritte piccole possono cambiare o diventare illeggibili (lettere inventate)",
             'small text may change or become unreadable (invented letters)'),
            ("aloni chiari o scuri attorno ad alcuni contorni", 'light or dark halos around some edges'),
            ("le scritte piccole in movimento possono tremolare (ridotto dalla stabilizzazione)",
             'small moving text may wobble (reduced by the stabilisation)'),
        ],
    },
    'anime': {
        'nome': 'Real-ESRGAN animevideov3', 'tipo': 'srvgg', 'file': 'realesr-animevideov3.onnx',
        'pth': 'realesr-animevideov3.pth',
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth',
        'byte': 2504012, 'sha256': 'b8a8376811077954d82ca3fcf476f1ac3da3e8a68a4f4d71363008000a18b75d',
        'sha256_onnx': 'a5d1b9e670661336bf7c9c7764a8518bb6ebea0bbb46af003d0fd32f97317e42',
        'licenza': 'BSD-3-Clause (github.com/xinntao/Real-ESRGAN)',
        'titolo': ('Real-ESRGAN animevideov3 (cartone animato)', 'Real-ESRGAN animevideov3 (cartoon)'),
        'descrizione': (
            "Il pi\u00f9 veloce e il pi\u00f9 netto, pensato per i cartoni animati: superfici pulite e contorni marcati.",
            "The fastest and crispest, made for cartoons: clean surfaces and strong edges."),
        'difetti': [
            ("appiattisce le sfumature (effetto cartone animato): i volti possono sembrare di plastica",
             'it flattens shading (cartoon look): faces may look like plastic'),
            ("inventa dettagli e pu\u00f2 cambiare le scritte piccole", 'it invents detail and may change small text'),
            ("contorni a volte troppo marcati", 'edges sometimes too strong'),
            ("le scritte piccole in movimento possono tremolare (ridotto dalla stabilizzazione)",
             'small moving text may wobble (reduced by the stabilisation)'),
        ],
    },
}
ORDINE = ['swin2sr', 'general', 'anime']
DIFETTI_COMUNI = [
    ("si preparano una volta sola, con la scheda video: il tempo dipende molto dalla scheda (il launcher lo misura "
     "prima)", 'they are prepared once, with the graphics card: the time depends a lot on the card (the launcher '
     'measures it first)'),
    ("occupano circa 1-1,5 GB per versione del gioco", 'they take about 1-1.5 GB per game version'),
    ("se mancano o qualcosa va storto, il gioco usa i Migliorati o il filtro in tempo reale",
     'if they are missing or something goes wrong, the game uses the Enhanced movies or the real-time filter'),
]


def cartella(root: Path) -> Path:
    return root / 'tools' / 'ia'


def cartella_filmati(modello: str) -> str:
    return f'filmati_ia_{modello}'


# ---------------------------------------------------------------- programmi e modelli scaricati

def programmi_pronti(root: Path) -> bool:
    py = cartella(root) / 'py'
    return ((py / f'onnxruntime_directml-{VERSIONE_ORT}.dist-info').is_dir() and
            (py / f'numpy-{VERSIONE_NUMPY}.dist-info').is_dir())


def modello_pronto(root: Path, nome: str) -> bool:
    try:
        stato = json.loads((cartella(root) / 'componenti.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    m = MODELLI[nome]
    voce = (stato.get('modelli') or {}).get(nome) or {}
    f = cartella(root) / 'modelli' / m['file']
    return bool(voce.get('ok')) and f.is_file() and f.stat().st_size == voce.get('byte')


def _sorgente(root: Path, nome: str) -> Path:
    """Il file del modello come si scarica (.pth per Real-ESRGAN, .onnx per Swin2SR) in tools/ia/modelli."""
    m = MODELLI[nome]
    return cartella(root) / 'modelli' / (m.get('pth') or m['file'])


def da_scaricare(root: Path, modelli) -> list:
    """(cosa, byte) da scaricare ancora per i modelli chiesti. Un modello gia' presente in tools/ia/modelli con la
    dimensione giusta (per esempio copiato da un altro PC) non si scarica: "installa" lo controlla (SHA-256) e lo
    converte."""
    out = [] if programmi_pronti(root) else list(SCARICHI_PROGRAMMI)
    for n in modelli:
        f = _sorgente(root, n)
        if not modello_pronto(root, n) and not (f.is_file() and f.stat().st_size == MODELLI[n]['byte']):
            out.append((MODELLI[n]['nome'], MODELLI[n]['byte']))
    return out


def descrivi_scarichi(root: Path, modelli) -> list:
    """Quello che da_scaricare elenca, con la fonte e la licenza (per chiedere il permesso al giocatore)."""
    out = []
    for cosa, byte in da_scaricare(root, modelli):
        prog = [i for i, (c, _) in enumerate(SCARICHI_PROGRAMMI) if c == cosa]
        if prog:
            out.append({'cosa': cosa, 'byte': byte, 'fonte': 'pypi.org', 'licenza': LICENZE_PROGRAMMI[prog[0]]})
            continue
        m = next(MODELLI[n] for n in modelli if MODELLI[n]['nome'] == cosa)
        out.append({'cosa': cosa, 'byte': byte, 'fonte': m['url'].split('/')[2], 'licenza': m['licenza'].split(' (')[0]})
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def _scarica(url: str, dest: Path, log, T) -> None:
    tmp = dest.with_name(dest.name + '.parziale')
    req = urllib.request.Request(url, headers={'User-Agent': 'EnterElectro-Recomp-launcher/0.12'})
    t0, fatti, ultimo = time.time(), 0, 0.0
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
        totale = int(r.headers.get('Content-Length') or 0)
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            fatti += len(b)
            if time.time() - ultimo > 2:
                ultimo = time.time()
                log(T(f'  scaricati {fatti / 1e6:.1f} MB' + (f' di {totale / 1e6:.1f}' if totale else ''),
                      f'  downloaded {fatti / 1e6:.1f} MB' + (f' of {totale / 1e6:.1f}' if totale else '')))
    tmp.replace(dest)
    log(T(f'  {dest.name}: {fatti / 1e6:.1f} MB in {time.time() - t0:.0f} s',
          f'  {dest.name}: {fatti / 1e6:.1f} MB in {time.time() - t0:.0f} s'))


def calcolo(root: Path):
    """La parte di calcolo, con numpy e onnxruntime di tools/ia/py."""
    for p in (str(cartella(root) / 'py'), str(Path(__file__).resolve().parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    import sm2_ia_calcolo  # noqa: E402
    return sm2_ia_calcolo


def installa(root: Path, modelli, log, T, scarica: bool = True) -> bool:
    """Scarica (una volta) i programmi e i modelli chiesti in tools/ia/, li controlla (SHA-256) e converte i
    Real-ESRGAN in ONNX. scarica=True solo con il si' del giocatore; con False non scarica niente e, se qualcosa
    manca, lo dice e si ferma. True se alla fine e' tutto pronto."""
    base = cartella(root)
    (base / 'modelli').mkdir(parents=True, exist_ok=True)

    def serve_il_si(cosa: str) -> bool:
        log(T(f'ERRORE: per {cosa} bisogna scaricare: serve il permesso (ia-scarica --si)',
              f'ERROR: {cosa} has to be downloaded: permission is needed (ai-download --yes)'))
        return False
    if not programmi_pronti(root):
        if not scarica:
            return serve_il_si('onnxruntime-directml e numpy')
        nuova = base / 'py.nuova'
        if nuova.exists():
            shutil.rmtree(nuova, ignore_errors=True)
        cmd = [sys.executable, '-m', 'pip', 'install', '--target', str(nuova), '--no-deps', '--only-binary=:all:',
               '--no-cache-dir', '--no-input', '--disable-pip-version-check', f'onnxruntime-directml=={VERSIONE_ORT}',
               f'numpy=={VERSIONE_NUMPY}']
        log(T('scarico i programmi per l\'IA da pypi.org (onnxruntime-directml e numpy, circa 38 MB)',
              'downloading the AI programs from pypi.org (onnxruntime-directml and numpy, about 38 MB)'))
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0:
            log(T('ERRORE: pip non riuscito:\n', 'ERROR: pip failed:\n') + (r.stdout + r.stderr)[-1500:])
            return False
        vecchia = base / 'py'
        if vecchia.exists():
            vecchia.rename(base / f'py.prima_{datetime.datetime.now():%Y%m%d_%H%M%S}')
        nuova.rename(vecchia)
    try:
        stato = json.loads((base / 'componenti.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        stato = {}
    stato.setdefault('modelli', {})
    stato['programmi'] = {'onnxruntime-directml': VERSIONE_ORT, 'numpy': VERSIONE_NUMPY}
    for n in modelli:
        if modello_pronto(root, n):
            continue
        m = MODELLI[n]
        sorgente = _sorgente(root, n)
        if sorgente.is_file() and _sha256(sorgente) != m['sha256']:
            sorgente.rename(sorgente.with_name(sorgente.name + f'.sbagliato_{datetime.datetime.now():%Y%m%d_%H%M%S}'))
            log(T(f'{m["nome"]}: il file presente non e\' quello atteso (impronta SHA-256 diversa): messo da parte',
                  f'{m["nome"]}: the file present is not the expected one (different SHA-256): set aside'))
        if not sorgente.is_file():
            if not scarica:
                return serve_il_si(m['nome'])
            log(T(f'scarico {m["nome"]} ({m["byte"] / 1e6:.1f} MB) da {m["url"].split("/")[2]}',
                  f'downloading {m["nome"]} ({m["byte"] / 1e6:.1f} MB) from {m["url"].split("/")[2]}'))
            try:
                _scarica(m['url'], sorgente, log, T)
            except OSError as e:
                log(T(f'ERRORE: {m["nome"]} non scaricato ({e})', f'ERROR: {m["nome"]} not downloaded ({e})'))
                return False
            if _sha256(sorgente) != m['sha256']:
                sorgente.rename(sorgente.with_name(sorgente.name + f'.sbagliato_{datetime.datetime.now():%Y%m%d_%H%M%S}'))
                log(T(f'ERRORE: {m["nome"]}: il file scaricato non e\' quello atteso (impronta SHA-256 diversa)',
                      f'ERROR: {m["nome"]}: the downloaded file is not the expected one (different SHA-256)'))
                return False
        else:
            log(T(f'{m["nome"]}: gia\' presente in tools/ia/modelli, impronta SHA-256 giusta (niente da scaricare)',
                  f'{m["nome"]}: already present in tools/ia/modelli, right SHA-256 (nothing to download)'))
        dest = base / 'modelli' / m['file']
        if m.get('pth'):
            C = calcolo(root)
            dati = C.esrgan_onnx(C.carica_pth(sorgente), nome=Path(m['file']).stem)   # come il file provato
            if hashlib.sha256(dati).hexdigest() != m['sha256_onnx']:
                log(T(f'ERRORE: {m["nome"]}: conversione ONNX diversa da quella provata',
                      f'ERROR: {m["nome"]}: ONNX conversion differs from the tested one'))
                return False
            dest.write_bytes(dati)
        stato['modelli'][n] = {'ok': True, 'file': m['file'], 'byte': dest.stat().st_size, 'fonte': m['url'],
                               'licenza': m['licenza'], 'data': f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'}
        (base / 'componenti.json').write_text(json.dumps(stato, indent=1, ensure_ascii=False), encoding='utf-8')
        log(T(f'{m["nome"]}: pronto', f'{m["nome"]}: ready'))
    return programmi_pronti(root) and all(modello_pronto(root, n) for n in modelli)


# ---------------------------------------------------------------- preparazione dei filmati di una versione

def pronti(cartella_gioco: Path, stato: dict, modello: str) -> bool:
    v = (stato.get('filmati_ia') or {}).get(modello) or {}
    return (bool(v.get('completo')) and v.get('formato') == FORMATO and
            (cartella_gioco / cartella_filmati(modello) / 'liste.txt').is_file())


def _sveglio(si: bool) -> None:
    """Windows: niente sospensione del PC mentre si preparano i filmati (richiesta del solo processo, che finisce con
    lui: le impostazioni del sistema non cambiano)."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if si else 0))
    except Exception:  # noqa: BLE001
        pass


def prepara(root: Path, fmv_str, dati: Path, filmati: list, cartella_gioco: Path, modello: str, ritardo: int, log, T,
            rifai: bool = False, peso: int = PESO_STABILE, processi: int = 0) -> int:
    """Prepara i filmati IA di una versione installata. 0 = fatto, 1 = errore, 2 = fermato (si riprende da dove era).
    Per fermare: creare il file STOP nella cartella <filmati_ia_modello>.tmp."""
    _sveglio(True)
    try:
        return _prepara(root, fmv_str, dati, filmati, cartella_gioco, modello, ritardo, log, T, rifai, peso, processi)
    finally:
        _sveglio(False)


def _prepara(root, fmv_str, dati, filmati, cartella_gioco, modello, ritardo, log, T, rifai, peso, processi) -> int:
    C = calcolo(root)
    m = MODELLI[modello]
    dest = cartella_gioco / cartella_filmati(modello)
    tmp = cartella_gioco / (cartella_filmati(modello) + '.tmp')
    if rifai and tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    stop = tmp / 'STOP'
    if stop.exists():
        stop.unlink()
    scheda = C.scheda_migliore()
    sess = C.Sessione(cartella(root) / 'modelli' / m['file'], m['tipo'], scheda)
    if sess.scheda is None:
        log(T('avviso: nessuna scheda video usabile con DirectML: si usa il processore, MOLTO lento',
              'warning: no graphics card usable with DirectML: using the processor, VERY slow'))
    else:
        log(T(f'scheda video: {sess.scheda["nome"]}', f'graphics card: {sess.scheda["nome"]}'))
    totale = sum(s for _, _, s in filmati) // 10
    fatti = {'n': 0}
    blocco = threading.Lock()
    coda: queue.Queue = queue.Queue()
    for f in filmati:
        if (tmp / f[0] / 'fatto.json').is_file():
            try:
                fatti['n'] += json.loads((tmp / f[0] / 'fatto.json').read_text(encoding='utf-8')).get('fotogrammi', 0)
            except (OSError, ValueError):
                pass
            continue
        coda.put(f)
    risultati, errori = {}, []
    t0 = time.time()
    fatti_prima = fatti['n']

    def avanza(n):
        with blocco:
            fatti['n'] += n

    def lavoratore():
        while not stop.exists():
            try:
                nome, lba, settori = coda.get_nowait()
            except queue.Empty:
                return
            d = tmp / nome
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)      # filmato lasciato a meta': si rifa' (e' solo nostro)
            try:
                r = C.prepara_film(fmv_str, dati, lba, settori, d, ritardo, sess, QUALITA, peso, ferma=stop.exists,
                                   avanza=avanza)
            except Exception as e:  # noqa: BLE001  (errore della scheda video o dei programmi: si scrive e si va avanti)
                try:
                    testo = str(e)
                except Exception:  # noqa: BLE001  (messaggi di Windows non in UTF-8)
                    testo = repr(e)
                r = {'ok': False, 'errori': f'{type(e).__name__}: {testo}'[-600:]}
            risultati[nome] = r
            if r.get('ok'):
                (d / 'fatto.json').write_text(json.dumps(r, ensure_ascii=False), encoding='utf-8')
                log(T(f'  {nome}: {r["fotogrammi"]} fotogrammi, {r["byte"] / 1e6:.1f} MB',
                      f'  {nome}: {r["fotogrammi"]} frames, {r["byte"] / 1e6:.1f} MB'))
            elif not r.get('fermato'):
                errori.append(nome)
                log(T(f'  ERRORE {nome}: {r.get("errori", "")}', f'  ERROR {nome}: {r.get("errori", "")}'))

    n_proc = processi if processi > 0 else (1 if m['tipo'] == 'swin2sr' else 3)
    fili = [threading.Thread(target=lavoratore, daemon=True) for _ in range(n_proc)]
    for f in fili:
        f.start()
    macchina = not sys.stdout.isatty()        # finestra del launcher: righe AVANZAMENTO da leggere, non per il registro
    ultimo = time.time()
    while any(f.is_alive() for f in fili):
        time.sleep(2)
        fatto = fatti['n']
        vel = (fatto - fatti_prima) / max(1e-6, time.time() - t0)
        resto = (totale - fatto) / vel if vel > 0 else 0
        if macchina:
            print(f'AVANZAMENTO {fatto} {totale} {int(resto)}', flush=True)
        if time.time() - ultimo >= 60:
            ultimo = time.time()
            log(T(f'  {100 * fatto // max(1, totale)}% ({fatto} di {totale} fotogrammi), circa {int(resto // 60)} minuti '
                  'alla fine', f'  {100 * fatto // max(1, totale)}% ({fatto} of {totale} frames), about '
                               f'{int(resto // 60)} minutes to the end'))
    if stop.exists():
        log(T('fermato: alla prossima preparazione si riprende da dove era',
              'stopped: the next preparation resumes where it was'))
        return 2
    if errori:
        log(T(f'ERRORE: {len(errori)} filmati non preparati ({", ".join(errori)})',
              f'ERROR: {len(errori)} movies not prepared ({", ".join(errori)})'))
        return 1
    (tmp / 'liste.txt').write_text('\n'.join(n for n, _, _ in filmati) + '\n', encoding='utf-8')
    tot_fot, tot_byte = 0, 0
    for n, _, _ in filmati:
        try:
            j = json.loads((tmp / n / 'fatto.json').read_text(encoding='utf-8'))
            tot_fot += j.get('fotogrammi', 0)
            tot_byte += j.get('byte', 0)
        except (OSError, ValueError):
            log(T(f'ERRORE: {n} non risulta fatto', f'ERROR: {n} is not marked as done'))
            return 1
    if dest.exists():
        vecchia = cartella_gioco / f'{cartella_filmati(modello)}.prima_{datetime.datetime.now():%Y%m%d_%H%M%S}'
        dest.rename(vecchia)
        log(T(f'filmati IA di prima spostati in {vecchia} (si possono cancellare)',
              f'previous AI movies moved to {vecchia} (they can be deleted)'))
    tmp.rename(dest)
    stato = json.loads((cartella_gioco / 'installazione.json').read_text(encoding='utf-8'))
    stato.setdefault('filmati_ia', {})[modello] = {
        'completo': True, 'formato': FORMATO, 'modello': m['nome'], 'filmati': len(filmati), 'fotogrammi': tot_fot,
        'byte': tot_byte, 'qualita': QUALITA, 'stabilizzazione': peso, 'ritardo': ritardo,
        'scheda': (sess.scheda or {}).get('nome', 'processore'), 'secondi': round(time.time() - t0, 1),
        'data': f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'}
    (cartella_gioco / 'installazione.json').write_text(json.dumps(stato, indent=1, ensure_ascii=False), encoding='utf-8')
    log(T(f'Fatto: {len(filmati)} filmati, {tot_fot} fotogrammi, {tot_byte / 1e9:.2f} GB con {m["nome"]}.',
          f'Done: {len(filmati)} movies, {tot_fot} frames, {tot_byte / 1e9:.2f} GB with {m["nome"]}.'))
    return 0


# ---------------------------------------------------------------- immagini di prova e tempi, sul PC del giocatore

def fotogrammi_prova(filmati: list) -> list:
    """Due fotogrammi per le immagini di prova: (filmato, numero nel pacchetto, ritaglio x, y, l, a, etichetta)."""
    nomi = {n: s for n, _, s in filmati}
    if 'HELLO' in nomi and nomi['HELLO'] // 10 > 560:
        return [('HELLO', 540, 100, 20, 160, 96, ('volto', 'face')),
                ('HELLO', 499, 60, 64, 160, 96, ('scritte', 'text'))]
    lungo = max(filmati, key=lambda f: f[2])
    n = lungo[2] // 10
    return [(lungo[0], int(n * 0.35), 80, 48, 160, 96, ('scena 1', 'scene 1')),
            (lungo[0], int(n * 0.65), 80, 48, 160, 96, ('scena 2', 'scene 2'))]


def anteprime(root: Path, fmv_str, dati: Path, filmati: list, cartella_gioco: Path, modelli, migliorati_dir, log, T,
              ritardo: int = 22) -> dict:
    """Immagini di prova (ritagli PPM, 4 volte l'originale) di ogni modello pronto e dei Migliorati, e il tempo per
    fotogramma sulla scheda video di questo PC, in <installazione>/anteprime_ia/ (anteprime.json)."""
    C = calcolo(root)
    out = cartella_gioco / 'anteprime_ia'
    out.mkdir(exist_ok=True)
    scelti = fotogrammi_prova(filmati)
    voci = {n: (lba, s) for n, lba, s in filmati}
    totale = sum(s for _, _, s in filmati) // 10
    ris = {'fotogrammi': [], 'modelli': {}, 'totale_fotogrammi': totale}
    originali = {}
    for nome, idx, *_ in scelti:
        if (nome, idx) in originali:
            continue
        lba, s = voci[nome]
        p, gen = C.fotogrammi_grezzi(fmv_str, dati, lba, s, out / '_indice', ritardo)
        for num, img in gen:
            if num in [i for n2, i, *_ in scelti if n2 == nome]:
                originali[(nome, num)] = img.copy()
            if num >= max(i for n2, i, *_ in scelti if n2 == nome):
                break
        p.kill()
        p.communicate()
    shutil.rmtree(out / '_indice', ignore_errors=True)
    for k, (nome, idx, x, y, w, h, et) in enumerate(scelti):
        img = originali.get((nome, idx))
        if img is None:
            continue
        base = f'{k + 1}_{nome}_{idx:06d}'
        crop = img[y:y + h, x:x + w].repeat(4, axis=0).repeat(4, axis=1)
        C.scrivi_ppm(out / f'{base}_originale.ppm', crop)
        voce = {'base': base, 'etichetta': list(et), 'filmato': nome, 'numero': idx,
                'versioni': {'originale': f'{base}_originale.ppm'}}
        if migliorati_dir is not None:
            jpg = Path(migliorati_dir) / nome / 'frames' / f'{idx:06d}.jpg'
            if jpg.is_file():
                r = subprocess.run([str(fmv_str), 'ritaglio', str(jpg), str(out / f'{base}_migliorati.ppm'),
                                    str(x * 4), str(y * 4), str(w * 4), str(h * 4)], capture_output=True, text=True)
                if r.returncode == 0:
                    voce['versioni']['migliorati'] = f'{base}_migliorati.ppm'
        ris['fotogrammi'].append(voce)
    scheda = C.scheda_migliore()
    for mod in modelli:
        if not modello_pronto(root, mod):
            continue
        m = MODELLI[mod]
        try:
            sess = C.Sessione(cartella(root) / 'modelli' / m['file'], m['tipo'], scheda)
        except Exception as e:  # noqa: BLE001
            log(T(f'{m["nome"]}: non parte ({e})', f'{m["nome"]}: does not start ({e})'))
            continue
        tempi = []
        for k, (nome, idx, x, y, w, h, et) in enumerate(scelti):
            img = originali.get((nome, idx))
            if img is None:
                continue
            base = f'{k + 1}_{nome}_{idx:06d}'
            try:
                grande = sess.ingrandisci(img)                # la prima volta prepara la scheda: non conta
                for _ in range(2):
                    t0 = time.perf_counter()
                    grande = sess.ingrandisci(img)
                    tempi.append(time.perf_counter() - t0)
            except Exception as e:  # noqa: BLE001
                try:
                    testo = str(e)
                except Exception:  # noqa: BLE001
                    testo = repr(e)
                log(T(f'{m["nome"]}: errore sulla scheda video ({testo[-300:]})',
                      f'{m["nome"]}: error on the graphics card ({testo[-300:]})'))
                tempi = []
                break
            C.scrivi_ppm(out / f'{base}_{mod}.ppm', grande[y * 4:(y + h) * 4, x * 4:(x + w) * 4])
            for v in ris['fotogrammi']:
                if v['base'] == base:
                    v['versioni'][mod] = f'{base}_{mod}.ppm'
        if tempi:
            s = sorted(tempi)[len(tempi) // 2]
            stima = totale * (s + 0.06) / max(1, (1 if m['tipo'] == 'swin2sr' else 2))
            ris['modelli'][mod] = {'secondi_per_fotogramma': round(s, 4), 'stima_secondi': int(stima),
                                   'scheda': (sess.scheda or {}).get('nome', 'processore')}
            log(T(f'{m["nome"]}: {s:.3f} s per fotogramma, tutti i filmati in circa {stima / 60:.0f} minuti',
                  f'{m["nome"]}: {s:.3f} s per frame, all the movies in about {stima / 60:.0f} minutes'))
        del sess
    (out / 'anteprime.json').write_text(json.dumps(ris, indent=1, ensure_ascii=False), encoding='utf-8')
    return ris
