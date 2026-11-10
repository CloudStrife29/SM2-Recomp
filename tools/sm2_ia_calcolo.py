# -*- coding: utf-8 -*-
"""EnterElectro-Recomp 0.12 - filmati IA, la parte di calcolo (numpy e onnxruntime-directml, scaricati solo se il giocatore
sceglie i filmati IA, in tools/ia/py). La usa sm2_ia.py; non serve al resto del launcher.
EnterElectro-Recomp 0.12 - AI movies, the computing part (numpy and onnxruntime-directml, downloaded only if the player chooses
the AI movies, into tools/ia/py). Used by sm2_ia.py; the rest of the launcher does not need it.

- pesi ufficiali .pth letti senza torch (solo tensori e dizionari, nessun codice) e i due Real-ESRGAN compatti
  (SRVGGNetCompact) scritti come modello ONNX da noi;
- le schede video viste da Windows (DXGI) e la sessione onnxruntime con DirectML;
- un filmato: fmv_str grezzi -> ingranditore -> fmv_str jpeg (con la stabilizzazione nel tempo, in C).
"""
from __future__ import annotations

import collections
import io
import json
import os
import pickle
import struct
import threading
import time
import zipfile

import numpy as np

# ---------------------------------------------------------------- pesi .pth (formato zip di torch) senza torch

_TIPI = {'FloatStorage': np.float32, 'HalfStorage': np.float16, 'DoubleStorage': np.float64,
         'LongStorage': np.int64, 'IntStorage': np.int32}


class _Storage:
    def __init__(self, dtype):
        self.dtype = dtype


def _rebuild_tensor_v2(storage, offset, size, stride, requires_grad=False, hooks=None, metadata=None):
    if not size:
        return storage[offset:offset + 1].reshape(())
    item = storage.itemsize
    return np.lib.stride_tricks.as_strided(storage[offset:], shape=tuple(size),
                                           strides=tuple(s * item for s in stride)).copy()


class _Lettore(pickle.Unpickler):
    def __init__(self, f, z, prefisso):
        super().__init__(f)
        self.z, self.prefisso = z, prefisso

    def find_class(self, module, name):
        if module == 'torch._utils' and name == '_rebuild_tensor_v2':
            return _rebuild_tensor_v2
        if module == 'collections' and name == 'OrderedDict':
            return collections.OrderedDict
        if module == 'torch' and name in _TIPI:
            return _Storage(_TIPI[name])
        raise pickle.UnpicklingError(f'classe non ammessa nel file dei pesi: {module}.{name}')

    def persistent_load(self, pid):
        tipo, storage_type, key, _location, _numel = pid
        if tipo != 'storage':
            raise pickle.UnpicklingError('voce persistente non ammessa')
        dtype = storage_type.dtype if isinstance(storage_type, _Storage) else np.float32
        return np.frombuffer(self.z.read(f'{self.prefisso}/data/{key}'), dtype=dtype)


def carica_pth(path) -> dict:
    """Pesi di un .pth di torch (formato zip): dizionario nome -> array numpy. Niente codice eseguito."""
    with zipfile.ZipFile(path) as z:
        pkl = [n for n in z.namelist() if n.endswith('data.pkl')][0]
        d = _Lettore(io.BytesIO(z.read(pkl)), z, pkl[:-len('/data.pkl')]).load()
    for k in ('params_ema', 'params'):
        if isinstance(d, dict) and k in d:
            return dict(d[k])
    return dict(d)


# ---------------------------------------------------------------- ONNX scritto a mano (protobuf)

def _varint(n: int) -> bytes:
    if n < 0:
        n += 1 << 64
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _k(campo: int, tipo: int) -> bytes:
    return _varint((campo << 3) | tipo)


def _v(campo: int, n: int) -> bytes:
    return _k(campo, 0) + _varint(n)


def _b(campo: int, dati: bytes) -> bytes:
    return _k(campo, 2) + _varint(len(dati)) + dati


def _s(campo: int, testo: str) -> bytes:
    return _b(campo, testo.encode('utf-8'))


FLOAT, INT64 = 1, 7


def _tensore(nome: str, a: np.ndarray) -> bytes:
    a = np.ascontiguousarray(a)
    tipo = {np.dtype(np.float32): FLOAT, np.dtype(np.int64): INT64}[a.dtype]
    return b''.join(_v(1, int(d)) for d in a.shape) + _v(2, tipo) + _s(8, nome) + _b(9, a.tobytes())


def _attr_int(nome, i):
    return _s(1, nome) + _v(20, 2) + _v(3, int(i))


def _attr_ints(nome, valori):
    return _s(1, nome) + _v(20, 7) + b''.join(_v(8, int(x)) for x in valori)


def _attr_str(nome, testo):
    return _s(1, nome) + _v(20, 3) + _b(4, testo.encode('utf-8'))


def _nodo(op, ingressi, uscite, nome, attributi=()):
    return (b''.join(_s(1, x) for x in ingressi) + b''.join(_s(2, x) for x in uscite) + _s(3, nome) + _s(4, op) +
            b''.join(_b(5, a) for a in attributi))


def _valore(nome, dims):
    """ValueInfoProto float con dimensioni intere o nominate (stringhe)."""
    dim = b''.join(_b(1, _v(1, d) if isinstance(d, int) else _s(2, d)) for d in dims)
    tensore = _v(1, FLOAT) + _b(2, dim)
    return _s(1, nome) + _b(2, _b(1, tensore))


def _modello(nodi, iniziali, ingressi, uscite, nome, opset=13) -> bytes:
    grafo = (b''.join(_b(1, n) for n in nodi) + _s(2, nome) + b''.join(_b(5, t) for t in iniziali) +
             b''.join(_b(11, x) for x in ingressi) + b''.join(_b(12, x) for x in uscite))
    return (_v(1, 7) + _s(2, 'SM2-Recomp') + _s(3, '0.12') + _b(7, grafo) + _b(8, _s(1, '') + _v(2, opset)))


def esrgan_onnx(sd: dict, scala: int = 4, nome: str = 'srvgg') -> bytes:
    """SRVGGNetCompact (realesr-general-x4v3, realesr-animevideov3) come ONNX opset 13:
    body = conv 3x3, PReLU, (conv 3x3, PReLU) x n, conv 3x3 -> PixelShuffle(scala) + ingresso ingrandito 'nearest'.
    Ingresso 'input' (1, 3, H, W) RGB in [0, 1], uscita 'output' (1, 3, scala*H, scala*W)."""
    idx = sorted({int(k.split('.')[1]) for k in sd if k.startswith('body.')})
    nodi, iniziali = [], []
    x = 'input'
    for i in idx:
        w = sd[f'body.{i}.weight'].astype(np.float32)
        if f'body.{i}.bias' in sd:                                    # convoluzione 3x3, passo 1, bordo 1
            iniziali += [_tensore(f'w{i}', w), _tensore(f'b{i}', sd[f'body.{i}.bias'].astype(np.float32))]
            nodi.append(_nodo('Conv', [x, f'w{i}', f'b{i}'], [f'c{i}'], f'conv{i}',
                              [_attr_ints('kernel_shape', w.shape[2:]), _attr_ints('pads', [1, 1, 1, 1]),
                               _attr_ints('strides', [1, 1]), _attr_ints('dilations', [1, 1]), _attr_int('group', 1)]))
            x = f'c{i}'
        else:                                                         # PReLU con un parametro per canale
            iniziali.append(_tensore(f'a{i}', w.reshape(-1, 1, 1)))
            nodi.append(_nodo('PRelu', [x, f'a{i}'], [f'p{i}'], f'prelu{i}'))
            x = f'p{i}'
    nodi.append(_nodo('DepthToSpace', [x], ['ps'], 'pixelshuffle',
                      [_attr_int('blocksize', scala), _attr_str('mode', 'CRD')]))
    iniziali.append(_tensore('scale', np.array([1, 1, scala, scala], np.float32)))
    nodi.append(_nodo('Resize', ['input', '', 'scale'], ['base'], 'nearest',
                      [_attr_str('mode', 'nearest'), _attr_str('coordinate_transformation_mode', 'asymmetric'),
                       _attr_str('nearest_mode', 'floor')]))
    nodi.append(_nodo('Add', ['ps', 'base'], ['output'], 'somma'))
    return _modello(nodi, iniziali, [_valore('input', [1, 3, 'altezza', 'larghezza'])],
                    [_valore('output', [1, 3, 'altezza_x4', 'larghezza_x4'])], nome)


# ---------------------------------------------------------------- riferimento numpy (per le prove)

def esrgan_numpy(img: np.ndarray, sd: dict, scala: int = 4) -> np.ndarray:
    """Stesso calcolo in numpy: img (H, W, 3) uint8 -> (scala*H, scala*W, 3) uint8."""
    x = img.astype(np.float32).transpose(2, 0, 1) / np.float32(255.0)
    out = x
    for i in sorted({int(k.split('.')[1]) for k in sd if k.startswith('body.')}):
        w = sd[f'body.{i}.weight'].astype(np.float32)
        if f'body.{i}.bias' in sd:
            c, h, wd = out.shape
            p = np.pad(out, ((0, 0), (1, 1), (1, 1)))
            acc = np.zeros((w.shape[0], h * wd), np.float32)
            for dy in range(3):
                for dx in range(3):
                    acc += np.ascontiguousarray(w[:, :, dy, dx]) @ np.ascontiguousarray(
                        p[:, dy:dy + h, dx:dx + wd]).reshape(c, h * wd)
            out = (acc + sd[f'body.{i}.bias'].astype(np.float32)[:, None]).reshape(w.shape[0], h, wd)
        else:
            out = np.where(out >= 0, out, w.reshape(-1, 1, 1) * out).astype(np.float32)
    c, h, wd = out.shape
    oc = c // (scala * scala)
    out = out.reshape(oc, scala, scala, h, wd).transpose(0, 3, 1, 4, 2).reshape(oc, h * scala, wd * scala)
    out = out + x.repeat(scala, axis=1).repeat(scala, axis=2)
    return np.round(np.clip(out, 0, 1).transpose(1, 2, 0) * 255.0).astype(np.uint8)


# ---------------------------------------------------------------- stabilita' nel tempo (come il TAA dei giochi)

def _luminanza(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def flusso_blocchi(prec: np.ndarray, cur: np.ndarray, blocco: int = 8, raggio: int = 4):
    """Movimento a blocchi tra due immagini piccole (luminanza): per ogni blocco di 'cur' lo spostamento (dy, dx), con
    mezzo pixel di precisione (parabola), tale che cur(y, x) ~ prec(y + dy, x + dx); e la differenza media rimasta."""
    h, w = cur.shape
    hb, wb = h // blocco, w // blocco
    n = 2 * raggio + 1
    p = np.pad(prec, raggio, mode='edge')
    c = cur[:hb * blocco, :wb * blocco].reshape(hb, blocco, wb, blocco)
    costi = np.empty((n, n, hb, wb), np.float32)
    for dy in range(-raggio, raggio + 1):
        for dx in range(-raggio, raggio + 1):
            s = p[raggio + dy:raggio + dy + hb * blocco, raggio + dx:raggio + dx + wb * blocco].reshape(hb, blocco, wb, blocco)
            costi[dy + raggio, dx + raggio] = np.abs(c - s).mean(axis=(1, 3))
    costi[raggio, raggio] -= 0.25                       # a parita', meglio fermo (niente movimenti inventati nel buio)
    piatto = costi.reshape(n * n, hb, wb)
    k = piatto.argmin(0)
    iy, ix = k // n, k % n
    minimo = np.take_along_axis(piatto, k[None], 0)[0] + np.where(k == raggio * n + raggio, 0.25, 0)
    jj, ii = np.meshgrid(np.arange(wb), np.arange(hb))

    def sub(i0, ia, ib):                                # vertice della parabola tra i tre costi
        den = ia - 2 * i0 + ib
        return np.where(np.abs(den) > 1e-6, np.clip(0.5 * (ia - ib) / np.where(np.abs(den) > 1e-6, den, 1), -0.5, 0.5), 0)

    c0 = costi[iy, ix, ii, jj]
    fy = iy - raggio + np.where((iy > 0) & (iy < n - 1),
                                sub(c0, costi[np.clip(iy - 1, 0, n - 1), ix, ii, jj], costi[np.clip(iy + 1, 0, n - 1), ix, ii, jj]), 0)
    fx = ix - raggio + np.where((ix > 0) & (ix < n - 1),
                                sub(c0, costi[iy, np.clip(ix - 1, 0, n - 1), ii, jj], costi[iy, np.clip(ix + 1, 0, n - 1), ii, jj]), 0)
    return fy.astype(np.float32), fx.astype(np.float32), minimo.astype(np.float32)


def _ingrandisci_campo(campo: np.ndarray, blocco_hr: int, h: int, w: int) -> np.ndarray:
    """Da un valore per blocco a un valore per pixel (bilineare tra i centri dei blocchi)."""
    hb, wb = campo.shape
    ys = (np.arange(h, dtype=np.float32) + 0.5) / blocco_hr - 0.5
    xs = (np.arange(w, dtype=np.float32) + 0.5) / blocco_hr - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, hb - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, wb - 1)
    y1, x1 = np.clip(y0 + 1, 0, hb - 1), np.clip(x0 + 1, 0, wb - 1)
    ay = np.clip(ys - y0, 0, 1)[:, None]
    ax = np.clip(xs - x0, 0, 1)[None, :]
    return ((1 - ay) * ((1 - ax) * campo[y0][:, x0] + ax * campo[y0][:, x1]) +
            ay * ((1 - ax) * campo[y1][:, x0] + ax * campo[y1][:, x1])).astype(np.float32)


def _campiona(img: np.ndarray, yy: np.ndarray, xx: np.ndarray) -> np.ndarray:
    """img (H, W, C) letto in punti non interi (bilineare, bordi bloccati)."""
    h, w = img.shape[:2]
    yy = np.clip(yy, 0, h - 1)
    xx = np.clip(xx, 0, w - 1)
    y0 = np.floor(yy).astype(np.int32)
    x0 = np.floor(xx).astype(np.int32)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)
    ay = (yy - y0)[..., None]
    ax = (xx - x0)[..., None]
    return ((1 - ay) * ((1 - ax) * img[y0, x0] + ax * img[y0, x1]) + ay * ((1 - ax) * img[y1, x0] + ax * img[y1, x1]))


def _min_max_3x3(a: np.ndarray):
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
    h, w = a.shape[:2]
    mn = a.copy()
    mx = a.copy()
    for dy in range(3):
        for dx in range(3):
            v = p[dy:dy + h, dx:dx + w]
            np.minimum(mn, v, out=mn)
            np.maximum(mx, v, out=mx)
    return mn, mx


class Stabilizzatore:
    """Rende piu' ferme da un fotogramma all'altro le uscite di un ingranditore (soprattutto le scritte piccole), come
    l'anti-aliasing temporale dei giochi: l'uscita di prima, spostata con il movimento misurato sull'originale, si
    mescola con quella nuova; dove non torna (fuori dai valori vicini della nuova) si scarta, cosi' niente scie.
    Ai cambi di scena riparte da zero. 'peso' e' la parte dell'immagine nuova a ogni passo."""

    def __init__(self, scala: int = 4, peso: float = 0.3, taglio: float = 30.0, blocco: int = 8):
        self.scala, self.peso, self.taglio, self.blocco = scala, peso, taglio, blocco
        self.lr = None
        self.y = None

    def passo(self, originale: np.ndarray, uscita: np.ndarray) -> np.ndarray:
        """originale (h, w, 3) uint8; uscita (s*h, s*w, 3) float32 in [0, 1]. Restituisce l'uscita stabilizzata."""
        lum = _luminanza(originale)
        if self.y is None or self.y.shape != uscita.shape or np.abs(lum - self.lr).mean() > self.taglio:
            self.lr, self.y = lum, uscita.astype(np.float32).copy()
            return self.y
        fy, fx, resto = flusso_blocchi(self.lr, lum, self.blocco)
        H, W = uscita.shape[:2]
        b = self.blocco * self.scala
        vy = _ingrandisci_campo(fy * self.scala, b, H, W)
        vx = _ingrandisci_campo(fx * self.scala, b, H, W)
        affid = _ingrandisci_campo(np.clip((resto - 6.0) / 10.0, 0, 1), b, H, W)   # 0 = movimento sicuro, 1 = no
        yy, xx = np.meshgrid(np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32), indexing='ij')
        storia = _campiona(self.y, yy + vy, xx + vx)
        mn, mx = _min_max_3x3(uscita)
        storia = np.clip(storia, mn, mx)
        a = (self.peso + (1 - self.peso) * affid)[..., None]
        self.y = (a * uscita + (1 - a) * storia).astype(np.float32)
        self.lr = lum
        return self.y


# ---------------------------------------------------------------- schede video e sessione onnxruntime

def schede_dxgi() -> list:
    """Schede video nell'ordine di DXGI (EnumAdapters1), che e' l'ordine dei device_id di DirectML. Solo Windows."""
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [('a', ctypes.c_uint32), ('b', ctypes.c_uint16), ('c', ctypes.c_uint16), ('d', ctypes.c_ubyte * 8)]

    class LUID(ctypes.Structure):
        _fields_ = [('LowPart', wintypes.DWORD), ('HighPart', wintypes.LONG)]

    class DESC1(ctypes.Structure):
        _fields_ = [('Description', wintypes.WCHAR * 128), ('VendorId', wintypes.UINT), ('DeviceId', wintypes.UINT),
                    ('SubSysId', wintypes.UINT), ('Revision', wintypes.UINT),
                    ('DedicatedVideoMemory', ctypes.c_size_t), ('DedicatedSystemMemory', ctypes.c_size_t),
                    ('SharedSystemMemory', ctypes.c_size_t), ('AdapterLuid', LUID), ('Flags', wintypes.UINT)]

    iid = GUID(0x770aae78, 0xf26f, 0x4dba, (ctypes.c_ubyte * 8)(0xa8, 0x29, 0x25, 0x3c, 0x83, 0xd1, 0xb3, 0x87))
    fab = ctypes.c_void_p()
    if ctypes.WinDLL('dxgi').CreateDXGIFactory1(ctypes.byref(iid), ctypes.byref(fab)) != 0:
        return []

    def metodo(obj, indice, *argt):
        vt = ctypes.cast(ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argt)(vt[indice])

    out = []
    for i in range(16):
        ad = ctypes.c_void_p()
        if metodo(fab, 12, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p))(fab, i, ctypes.byref(ad)) != 0:
            break                                                                   # EnumAdapters1
        d = DESC1()
        metodo(ad, 10, ctypes.POINTER(DESC1))(ad, ctypes.byref(d))                  # GetDesc1
        out.append({'device_id': i, 'nome': d.Description, 'memoria_mb': d.DedicatedVideoMemory // (1 << 20),
                    'software': bool(d.Flags & 2)})
        metodo(ad, 2)(ad)                                                           # Release
    metodo(fab, 2)(fab)
    return out


def scheda_migliore() -> dict | None:
    """La scheda video con piu' memoria propria (di solito quella dedicata); None se non ce n'e' una vera.
    SM2_IA_SCHEDA=<device_id> per sceglierne un'altra."""
    try:
        schede = [s for s in schede_dxgi() if not s['software']]
    except Exception:  # noqa: BLE001
        schede = []
    scelta = os.environ.get('SM2_IA_SCHEDA', '').strip()
    if scelta.isdigit():
        for s in schede:
            if s['device_id'] == int(scelta):
                return s
    return max(schede, key=lambda s: s['memoria_mb'], default=None)


class Sessione:
    """Un ingranditore x4 pronto sulla scheda video (DirectML) o, se non si puo', sul processore (molto lento)."""

    def __init__(self, file_onnx, tipo: str, scheda: dict | None = None):
        import onnxruntime as ort
        try:        # le versioni ufficiali per Windows hanno la telemetria di Microsoft accesa: la spegniamo
            ort.disable_telemetry_events()
        except Exception:  # noqa: BLE001
            pass
        self.tipo = tipo
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.enable_mem_pattern = False
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.log_severity_level = 3
        provider = ['CPUExecutionProvider']
        if scheda is not None and 'DmlExecutionProvider' in ort.get_available_providers():
            provider = [('DmlExecutionProvider', {'device_id': int(scheda['device_id'])}), 'CPUExecutionProvider']
        try:
            self.s = ort.InferenceSession(str(file_onnx), sess_options=so, providers=provider)
        except Exception:  # noqa: BLE001  (scheda che DirectML non accetta: si usa il processore)
            if provider == ['CPUExecutionProvider']:
                raise
            self.s = ort.InferenceSession(str(file_onnx), sess_options=so, providers=['CPUExecutionProvider'])
        self.scheda = scheda if 'DmlExecutionProvider' in self.s.get_providers() else None
        self.ing = self.s.get_inputs()[0].name
        self.usc = self.s.get_outputs()[0].name
        self.blocco = threading.Lock()     # con DirectML una sola chiamata alla volta per sessione

    def ingrandisci(self, img: np.ndarray) -> np.ndarray:
        """img (h, w, 3) uint8 -> (4h, 4w, 3) uint8."""
        h, w = img.shape[:2]
        x = img.astype(np.float32).transpose(2, 0, 1) / np.float32(255.0)
        if self.tipo == 'swin2sr':          # come lo script ufficiale: a specchio fino al multiplo di 8 successivo
            hp, wp = (h // 8 + 1) * 8 - h, (w // 8 + 1) * 8 - w
            x = np.concatenate([x, x[:, ::-1, :]], axis=1)[:, :h + hp, :]
            x = np.concatenate([x, x[:, :, ::-1]], axis=2)[:, :, :w + wp]
        x = np.ascontiguousarray(x[None])
        with self.blocco:
            y = self.s.run([self.usc], {self.ing: x})[0]
        y = np.clip(y[0, :, :h * 4, :w * 4], 0, 1)
        return np.round(y.transpose(1, 2, 0) * np.float32(255.0)).astype(np.uint8)


# ---------------------------------------------------------------- un filmato

def _leggi(f, n: int) -> bytes:
    b = f.read(n)
    return b if b is not None else b''


def fotogrammi_grezzi(fmv_str, dati, lba: int, settori: int, dest, ritardo: int):
    """fmv_str grezzi: (processo, generatore di (numero, immagine (h, w, 3) uint8)). Scrive dest/index.bin."""
    import subprocess
    p = subprocess.Popen([str(fmv_str), 'grezzi', str(dati), str(lba), str(settori), str(dest), str(ritardo)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def gen():
        while True:
            h = _leggi(p.stdout, 8)
            if len(h) < 8:
                return
            num, w, hh = struct.unpack('<IHH', h)
            raw = _leggi(p.stdout, w * hh * 3)
            if len(raw) < w * hh * 3:
                return
            yield num, np.frombuffer(raw, np.uint8).reshape(hh, w, 3)
    return p, gen()


def prepara_film(fmv_str, dati, lba: int, settori: int, dest, ritardo: int, sessione: 'Sessione', qualita: int = 90,
                 peso: int = 30, ferma=None, avanza=None) -> dict:
    """Un filmato nel formato fmv_hd di psxrecomp: dest/index.bin (da fmv_str grezzi) e dest/frames/NNNNNN.jpg
    ingranditi dal modello e stabilizzati nel tempo (fmv_str jpeg ... stabilizza <peso>; 100 = niente).
    ferma(): True per fermarsi (si riprende rifacendo il filmato); avanza(n): n fotogrammi fatti."""
    import subprocess
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'frames').mkdir(exist_ok=True)
    p1, gen = fotogrammi_grezzi(fmv_str, dati, lba, settori, dest, ritardo)
    cmd = [str(fmv_str), 'jpeg', str(dest / 'frames'), str(qualita)] + (['stabilizza', str(peso)] if peso < 100 else [])
    p2 = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    n, fermato, t_mod = 0, False, 0.0
    try:
        for num, img in gen:
            if ferma is not None and ferma():
                fermato = True
                break
            t0 = time.perf_counter()
            out = sessione.ingrandisci(img)
            t_mod += time.perf_counter() - t0
            h, w = img.shape[:2]
            p2.stdin.write(struct.pack('<IHHHH', num, out.shape[1], out.shape[0], w, h) + out.tobytes() + img.tobytes())
            n += 1
            if avanza is not None:
                avanza(1)
    except (BrokenPipeError, OSError):
        fermato = True
    finally:
        if fermato:
            for p in (p1, p2):
                try:
                    p.kill()
                except OSError:
                    pass
        try:
            p2.stdin.close()
        except OSError:
            pass
    o2, e2 = p2.communicate()
    o1, e1 = p1.communicate()
    if fermato:
        return {'fermato': True, 'fotogrammi': n}

    def ultima_json(b):
        try:
            return json.loads(b.decode('utf-8', 'replace').strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {}
    j1, j2 = ultima_json(e1), ultima_json(o2)
    ok = (p1.returncode == 0 and p2.returncode == 0 and n > 0 and j1.get('fotogrammi') == n and j2.get('jpeg') == n)
    return {'ok': ok, 'fotogrammi': n, 'byte': j2.get('byte', 0), 'secondi_modello': round(t_mod, 1),
            'grezzi': j1, 'jpeg': j2,
            'errori': (e1.decode('utf-8', 'replace') + e2.decode('utf-8', 'replace')).strip()[-600:] if not ok else ''}


def scrivi_ppm(path, a: np.ndarray) -> None:
    h, w = a.shape[:2]
    with open(path, 'wb') as f:
        f.write(b'P6\n%d %d\n255\n' % (w, h))
        f.write(np.ascontiguousarray(a, dtype=np.uint8).tobytes())
