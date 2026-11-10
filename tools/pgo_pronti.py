# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - profili PGO gia' pronti per il pacchetto. / Ready-made PGO profiles for the package.

Comandi (lavorano nella cartella del progetto o del pacchetto in cui sta questo file):
  esporta --cartella C [--profilo P] [--variante V]
        prende C\\pgo\\default.profdata di un'installazione fatta con --pgo e con la partita di allenamento, e
        l'impronta del suo codice tradotto; scrive aot\\pgo\\<P>[-<V>].profdata.xz e la sua voce in
        aot\\pgo\\indice.json. Una voce per versione e variante: quella nuova prende il posto della vecchia, il cui
        file viene spostato in aot\\pgo\\vecchi\\ (non si cancella niente).
  controlla
        controlla ogni voce dell'indice: file presente e profilo integro (SHA-256 dopo la scompattazione).
La variante di default viene da installazione.json: "pgxp" se l'installazione ha i punti di aggancio di PGXP,
altrimenti nessuna. Il launcher usa un profilo solo se l'impronta del codice tradotto corrisponde esattamente.

English: "esporta" (export) packs C\\pgo\\default.profdata of a PGO installation, with the fingerprint of its translated
code, into aot\\pgo\\ and aot\\pgo\\indice.json; "controlla" (check) verifies the index. The launcher uses a profile
only when the translated code fingerprint matches exactly.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import lzma
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sm2_launcher as L  # noqa: E402


def scrivi_indice(indice: dict) -> None:
    L.PGO_PRONTI.mkdir(parents=True, exist_ok=True)
    tmp = L.PGO_PRONTI / 'indice.json.tmp'
    tmp.write_text(json.dumps(indice, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(L.PGO_PRONTI / 'indice.json')


def cmd_esporta(args) -> int:
    cart = Path(args.cartella).resolve()
    prof_file = cart / 'pgo' / 'default.profdata'
    try:
        inst = json.loads((cart / 'installazione.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        inst = {}
    prof = args.profilo or inst.get('profilo')
    if not prof or not prof_file.is_file():
        print(f'ERRORE: servono {prof_file} e la versione (--profilo o installazione.json)')
        return 1
    if inst.get('pgo_pronto'):
        print(f'ERRORE: questa installazione ha usato il profilo pronto {inst["pgo_pronto"]}, non una partita di '
              'allenamento: non lo riesporto')
        return 1
    if inst.get('pgo') is not True or not inst.get('completata'):
        print('ERRORE: l\'installazione non risulta completata con il PGO (installazione.json: pgo '
              f'{inst.get("pgo")}, completata {inst.get("completata")})')
        return 1
    variante = args.variante if args.variante is not None else ('pgxp' if inst.get('pgxp') else '')
    imp = L.impronta_codice(cart)
    if inst.get('impronta_codice') and inst['impronta_codice'] != imp['sha256']:
        print('ERRORE: il codice tradotto e\' cambiato dopo l\'installazione (impronta diversa da installazione.json)')
        return 1
    dati = prof_file.read_bytes()
    nome = f'{prof}{"-" + variante if variante else ""}.profdata.xz'
    L.PGO_PRONTI.mkdir(parents=True, exist_ok=True)
    indice = L.indice_pgo_pronti()
    vecchie = [v for v in indice['profili'] if v.get('profilo') == prof and v.get('variante', '') == variante]
    for v in vecchie:
        f = L.PGO_PRONTI / str(v.get('file'))
        if f.is_file():
            dest = L.PGO_PRONTI / 'vecchi' / f'{f.name}.{datetime.datetime.now():%Y%m%d_%H%M%S}'
            n = 1
            while dest.exists():
                n += 1
                dest = dest.with_name(f'{f.name}.{datetime.datetime.now():%Y%m%d_%H%M%S}_{n}')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            print(f'profilo di prima spostato in {dest}')
    (L.PGO_PRONTI / nome).write_bytes(lzma.compress(dati, preset=9 | lzma.PRESET_EXTREME))
    voce = {'profilo': prof, 'variante': variante, 'file': nome,
            'sha256_profdata': hashlib.sha256(dati).hexdigest(), 'byte_profdata': len(dati),
            'impronta_codice': imp['sha256'], 'file_codice': imp['file'], 'byte_codice': imp['byte'],
            'launcher': inst.get('launcher'), 'da': str(cart), 'data': f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'}
    indice['formato'] = 1
    indice['profili'] = [v for v in indice['profili'] if v not in vecchie] + [voce]
    indice['profili'].sort(key=lambda v: (v.get('profilo', ''), v.get('variante', '')))
    scrivi_indice(indice)
    xz = (L.PGO_PRONTI / nome).stat().st_size
    print(f'scritto {L.PGO_PRONTI / nome}: {len(dati)} byte, {xz} compresso; impronta del codice {imp["sha256"][:16]} '
          f'({imp["file"]} file, {imp["byte"] / 1e6:.1f} MB)')
    return 0


def cmd_controlla(args) -> int:
    indice = L.indice_pgo_pronti()
    errori = 0
    for v in indice['profili']:
        f = L.PGO_PRONTI / str(v.get('file'))
        try:
            dati = lzma.decompress(f.read_bytes())
            ok = hashlib.sha256(dati).hexdigest() == v.get('sha256_profdata')
        except (OSError, lzma.LZMAError):
            ok = False
        errori += not ok
        print(f'{"OK" if ok else "NO"}  {v.get("profilo")} {v.get("variante") or "-"}  {v.get("file")}  '
              f'codice {str(v.get("impronta_codice"))[:16]}')
    print(f'{len(indice["profili"])} profili, {errori} con problemi')
    return 1 if errori else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('esporta')
    s.add_argument('--cartella', required=True)
    s.add_argument('--profilo')
    s.add_argument('--variante')
    sp.add_parser('controlla')
    args = ap.parse_args()
    return {'esporta': cmd_esporta, 'controlla': cmd_controlla}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
