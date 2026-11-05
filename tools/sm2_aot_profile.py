#!/usr/bin/env python3
"""SM2-Recomp - Milestone 3: scrive aot/overlays.json, il profilo AOT di psxrecomp per i moduli
di codice di CD.WAD (.bin + .rel), dal disco dell'utente.

English: SM2-Recomp Milestone 3 - writes aot/overlays.json, the psxrecomp AOT profile for the code modules in
CD.WAD (.bin + .rel), from the user's own disc. The profile holds only facts (disc hash, offsets, sizes and SHA-256
of the modules, relocation counts, load bases from aot/sm2_placements.json), no game bytes. The comments are in
Italian.

Il profilo contiene solo fatti: hash del disco, offset, dimensioni e SHA-256 dei moduli dentro
CD.WAD, numero di rilocazioni e basi di caricamento. Nessun byte del gioco. Le basi vengono da
aot/sm2_placements.json (osservate nella RAM del gioco, vedi il campo "evidence").

Con il profilo, `psxrecomp_cli.py generate` compila i moduli in anticipo (metodo
relocated_extent_members di psxrecomp) in generated/aot/overlays_static.c, che il CMakeLists
collega con GAME_OVERLAY_STATIC_C.

Uso:  python tools/sm2_aot_profile.py [--profile SLUS-01378-Rev1] [--check-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'psxrecomp' / 'tools'))

PLACEMENTS = ROOT / 'aot' / 'sm2_placements.json'
PROFILE_OUT = ROOT / 'aot' / 'overlays.json'
STATIC_OUTPUT = 'generated/aot/overlays_static.c'
HED, WAD = 'CD.HED', 'CD.WAD'


def parse_hed(hed: bytes):
    """Indice di CD.WAD: {nome\\0, allineamento a 4, offset u32, size u32}..., terminato da 0xFF.
    Ritorna nome (minuscolo) -> lista di (offset, size): alcuni nomi compaiono piu' volte."""
    entries, i = {}, 0
    while i < len(hed) and hed[i] != 0xFF:
        j = hed.index(b'\x00', i)
        name = hed[i:j].decode('ascii')
        i = (j + 1 + 3) & ~3
        off, size = struct.unpack_from('<II', hed, i)
        i += 8
        if not name:
            raise ValueError(f'voce di CD.HED senza nome vicino al byte {i}')
        entries.setdefault(name.lower(), []).append((off, size))
    if i >= len(hed):
        raise ValueError('CD.HED senza terminatore 0xFF')
    return entries


def build_profile(game_id: str, disc_sha1: str, hed: bytes, wad: bytes, modules: dict) -> dict:
    """Profilo AOT per i moduli con basi note. `modules`: nome -> {"placements": [...], ...}."""
    from counted_mips_relocations import parse_stream, relocate
    index = parse_hed(hed)
    members, total = [], 0
    for name in sorted(modules):
        info = modules[name]
        bases = [int(b, 16) for b in info.get('placements', [])]
        if not bases:
            continue
        extents = {}
        for ext in ('bin', 'rel'):
            key = f'{name}.{ext}'
            if len(index.get(key, [])) != 1:
                raise ValueError(f'{key} deve comparire esattamente una volta in CD.HED '
                                 f'(trovato {len(index.get(key, []))})')
            (off, size), = index[key]
            if off + size > len(wad):
                raise ValueError(f'{key} esce da CD.WAD')
            body = wad[off:off + size]
            extents[ext] = (off, size, body)
        image, stream = extents['bin'][2], extents['rel'][2]
        member = parse_stream(image, stream, extents['bin'][0], extents['rel'][0])
        for base in bases:
            relocate(member, base)          # controlla allineamento e RAM
        members.append({
            'name': name.upper(),
            'image': {'file': WAD, 'file_offset': hex(extents['bin'][0]), 'size': hex(extents['bin'][1]),
                      'sha256': hashlib.sha256(image).hexdigest()},
            'relocations': {'file': WAD, 'file_offset': hex(extents['rel'][0]), 'size': hex(extents['rel'][1]),
                            'sha256': hashlib.sha256(stream).hexdigest()},
            'relocation_count': len(member.relocations),
            # il gioco chiama base+0 dopo la rilocazione (func_8001E8E4 -> func_8001EEF0 -> base)
            'placements': [{'load_addr': f'0x{b:08X}', 'entries': [f'0x{b:08X}']} for b in bases],
        })
        total += len(bases)
    if not members:
        raise ValueError('nessun modulo con basi note: niente da compilare in anticipo')
    return {
        'schema': 'psxrecomp AOT methods v1',
        'game_id': game_id,
        'disc_hashes': {'sha1': disc_sha1},
        'static_output': STATIC_OUTPUT,
        'strict_bounds': True,
        'expected_records': total,
        'images': [{'method': 'relocated_extent_members', 'members': members}],
    }


def read_game_id(progetto: Path = ROOT) -> str:
    import tomllib
    return tomllib.loads((progetto / 'game.toml').read_text(encoding='utf-8'))['game']['id']


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default='SLUS-01378-Rev1')
    ap.add_argument('--progetto', default='', help='progetto della versione (versioni/<PROFILO>, tools/versione.py): '
                                                  'game.toml letto da li\' e profilo scritto in <progetto>/aot/overlays.json')
    ap.add_argument('--check-only', action='store_true', help='controlla senza scrivere il profilo')
    args = ap.parse_args()

    facts = json.loads(PLACEMENTS.read_text(encoding='utf-8'))
    version = facts['versions'].get(args.profile)
    if version is None:
        print(f'ERRORE: nessuna base nota per {args.profile} in {PLACEMENTS.relative_to(ROOT)}')
        return 1
    cues = sorted((ROOT / 'input' / args.profile).glob('*.cue'))
    if not cues:
        print(f'ERRORE: nessun .cue in input/{args.profile}')
        return 1
    import aot_overlay_pipeline as pipeline
    disc = pipeline.Disc(cues[0])
    sha1 = pipeline.digest(disc.binary, 'sha1')
    if sha1 != version['disc_sha1']:
        print(f'ERRORE: il disco in input/{args.profile} ha SHA-1 {sha1}, le basi note sono per {version["disc_sha1"]}')
        return 1
    progetto = (ROOT / args.progetto) if args.progetto else ROOT
    out_p = progetto / 'aot' / 'overlays.json'
    profile = build_profile(read_game_id(progetto), sha1, disc.read(HED), disc.read(WAD), version['modules'])
    # stessa verifica che fara' generate: il metodo di psxrecomp deve ricostruire le stesse immagini
    sources = pipeline.positioned_sources(disc, profile['images'])
    for s in sources:
        print(f"{s['name']:<16} base 0x{s['base']:08X}  {len(s['body']):>6} byte  "
              f"rilocazioni {next(m['relocation_count'] for m in profile['images'][0]['members'] if s['name'].startswith(m['name'] + '@'))}")
    print(f'disco: SHA-1 {sha1} (corrisponde)')
    print(f'moduli: {len(profile["images"][0]["members"])}, basi: {profile["expected_records"]}')
    if args.check_only:
        print('controllo riuscito (--check-only: profilo non scritto)')
        return 0
    out_p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(profile, indent=1) + '\n'
    old = out_p.read_text(encoding='utf-8') if out_p.is_file() else None
    if old == text:
        print(f'{out_p.relative_to(ROOT)} gia\' aggiornato')
    else:
        out_p.write_text(text, encoding='utf-8')
        print(f'scritto {out_p.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
