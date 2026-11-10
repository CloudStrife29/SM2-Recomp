/* fmv_str.c - EnterElectro-Recomp 0.12: filmati STR (bitstream MDEC v2) letti dal disco del giocatore e decodificati con
 * l'MDEC di psxrecomp (runtime/src/mdec.c, lo stesso del gioco), per i filmati migliorati.
 * EnterElectro-Recomp 0.12: STR movies (MDEC v2 bitstream) read from the player's own disc and decoded with psxrecomp's MDEC.
 *
 * Niente dati del gioco nel programma: legge il disco dell'utente e scrive solo dove gli si dice.
 *
 * Uso / usage:
 *   fmv_str info      <disco.bin> <lba> <settori>
 *        un fotogramma per riga: numero, primo e ultimo settore, settori, byte, qscale, versione, MB, mezze parole RLE
 *   fmv_str confronta <disco.bin> <lba> <settori> <immagine.png> <scala> [uscita_dir]
 *        decodifica tutti i fotogrammi e cerca quello piu' vicino all'immagine presa dal gioco (present_shot,
 *        ingrandita <scala> volte senza filtro: 4 per 1280x960 da 320x240); per il migliore scrive la differenza media
 *        per canale e i pixel uguali; con uscita_dir scrive anche i due .ppm (decodificato e ritaglio del gioco)
 *   fmv_str estrai    <disco.bin> <lba> <settori> <uscita_dir> [ogni]
 *        scrive i fotogrammi decodificati come .ppm (uno ogni <ogni>, di default 1)
 *   fmv_str indice    <disco.bin> <lba> <settori> <uscita_dir> <ritardo|legacy> [sig_w sig_h]
 *        scrive <uscita_dir>/index.bin per il sistema fmv_hd di psxrecomp: una firma di luminosita' sig_w x sig_h
 *        (di default 32 x 24) per fotogramma, calcolata come fa il gioco; con un numero: formato FMVHD003 con i
 *        settori del filmato e, per ogni fotogramma, il suo primo settore + <ritardo>; con "legacy": FMVHD002, senza
 *        settori (solo per la taratura, con PSX_FMV_HD_LEGACY=1). Il filmato e' messo al centro dello schermo che il
 *        gioco presenta. Scrive anche <uscita_dir>/fotogrammi.tsv (numero, primo e ultimo settore).
 *   fmv_str sfondo <immagine> <uscita.ppm> <larghezza> <altezza> [centro_y [scuro]]
 *        (0.12) un'immagine (JPEG o PNG: un fotogramma migliorato o lo sfondo disegnato) diventa l'immagine di fondo
 *        della finestra del launcher, grande larghezza x altezza: l'immagine riempie tutto (ritagliata ai lati o in
 *        alto e in basso, con la fascia centrata su centro_y, millesimi dell'altezza, di default 500), piu' scura a
 *        sinistra (dove ci sono il titolo e le versioni) e in basso; scuro (0-100, di default 100) e' quanto si
 *        scurisce: 0 lascia i colori come sono. Scrive un .ppm (Tk lo mostra da solo)
 *   fmv_str pacchetto <disco.bin> <lba> <settori> <uscita_dir> <ritardo> <scala> <qualita> [sig_w sig_h]
 *        come "indice" (FMVHD003) e in piu' i fotogrammi migliorati in <uscita_dir>/frames/NNNNNN.jpg: piani YCbCr
 *        presi dall'MDEC del gioco, bordi dei blocchi 8x8 attenuati, colore interpolato invece che a quadretti,
 *        ingrandimento Lanczos x<scala> (2, 3 o 4), nitidezza adattiva al contrasto, JPEG di qualita' <qualita>. Controlla anche che i colori
 *        calcolati dai piani siano identici a quelli dell'MDEC a 24 bit (riga "diversi" nel risultato).
 *
 *   fmv_str grezzi    <disco.bin> <lba> <settori> <uscita_dir> <ritardo> [sig_w sig_h]
 *        (0.12, filmati IA) come "pacchetto" (stessi fotogrammi e stesso index.bin in <uscita_dir>), ma i fotogrammi
 *        escono come sono (RGB a 24 bit dell'MDEC del gioco) sull'uscita standard, ognuno preceduto da 8 byte
 *        little-endian: numero nel pacchetto (32 bit), larghezza e altezza (16 bit); il riassunto va su stderr
 *   fmv_str ritaglio  <immagine> <uscita.ppm> <x> <y> <larghezza> <altezza>
 *        (0.12, immagini di prova dei filmati IA) un pezzo di un'immagine JPEG o PNG come .ppm (per la finestra)
 *   fmv_str jpeg      <cartella> <qualita> [stabilizza <peso%>]
 *        (0.12, filmati IA) legge da stdin i fotogrammi ingranditi e li scrive come <cartella>/NNNNNN.jpg
 *        (NNNNNN = numero nel pacchetto) con il codificatore dei filmati migliorati. Ogni fotogramma: 12 byte
 *        little-endian (numero 32 bit; larghezza e altezza dell'immagine grande, 16 bit; larghezza e altezza
 *        dell'originale, 16 bit, 0 se non c'e'), poi l'immagine grande RGB e, se c'e', l'originale RGB.
 *        Con "stabilizza" (e gli originali) rende le immagini piu' ferme da un fotogramma all'altro, come
 *        l'anti-aliasing temporale dei giochi: l'immagine di prima, spostata con il movimento misurato a blocchi
 *        sull'originale, si mescola con la nuova (peso% della nuova a ogni passo) dove resta dentro i valori
 *        vicini della nuova; ai cambi di scena riparte da zero.
 *
 * Compilazione / build (dalla radice del progetto):
 *   clang -O2 -I psxrecomp/runtime/include -o fmv_str.exe tools/fmv/fmv_str.c psxrecomp/runtime/src/mdec.c
 */
#define _FILE_OFFSET_BITS 64
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined(_WIN32)
#include <fcntl.h>
#include <io.h>
#endif

#include "mdec.h"
#include "fmv_jpeg.h"

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_ONLY_JPEG
#define STBI_NO_HDR
#define STBI_NO_LINEAR
#include "../third_party/stb_image.h"

/* Simboli che mdec.c prende dal resto del runtime: qui non servono. */
uint64_t psx_cycle_count = 0;
uint64_t s_frame_count = 0;
int debug_server_fmv_quiet(void) { return 0; }

#define SETTORE 2352
#define CHUNK 2016

/* Spostamento a 64 bit nel file del disco (su Windows long e' a 32 bit). */
#if defined(_WIN32)
#define SPOSTA(f, off) _fseeki64((f), (long long)(off), SEEK_SET)
#else
#define SPOSTA(f, off) fseeko((f), (off_t)(off), SEEK_SET)
#endif

/* Tabelle standard delle librerie Sony (DecDCTReset), le stesse del gioco: quantizzazione nell'ordine a zig-zag
 * (matrice intra di MPEG-1 con DC = 2) e matrice della IDCT (coseni * 32768, i negativi come ~positivo). */
static const uint8_t QUANT[64] = {
     2, 16, 16, 19, 16, 19, 22, 22, 22, 22, 22, 22, 26, 24, 26, 27,
    27, 27, 26, 26, 26, 26, 27, 27, 27, 29, 29, 29, 34, 34, 34, 29,
    29, 29, 27, 27, 29, 29, 32, 32, 34, 34, 37, 38, 37, 35, 35, 34,
    35, 38, 38, 40, 40, 40, 48, 48, 46, 46, 56, 56, 58, 69, 69, 83
};
static const uint16_t SCALA[64] = {
    0x5A82, 0x5A82, 0x5A82, 0x5A82, 0x5A82, 0x5A82, 0x5A82, 0x5A82,
    0x7D8A, 0x6A6D, 0x471C, 0x18F8, 0xE707, 0xB8E3, 0x9592, 0x8275,
    0x7641, 0x30FB, 0xCF04, 0x89BE, 0x89BE, 0xCF04, 0x30FB, 0x7641,
    0x6A6D, 0xE707, 0x8275, 0xB8E3, 0x471C, 0x7D8A, 0x18F8, 0x9592,
    0x5A82, 0xA57D, 0xA57D, 0x5A82, 0x5A82, 0xA57D, 0xA57D, 0x5A82,
    0x471C, 0x8275, 0x18F8, 0x6A6D, 0x9592, 0xE707, 0x7D8A, 0xB8E3,
    0x30FB, 0x89BE, 0x7641, 0xCF04, 0xCF04, 0x7641, 0x89BE, 0x30FB,
    0x18F8, 0xB8E3, 0x6A6D, 0x8275, 0x7D8A, 0x9592, 0x471C, 0xE707
};

/* Codici dei coefficienti AC (tabella B.14 di MPEG-1, quella dei filmati STR v2): codice senza il bit del segno,
 * corsa (zeri prima) e livello. "10" = fine del blocco, "000001" = escape (6 bit di corsa e 10 di livello). */
typedef struct { const char *bit; int run, level; } Vlc;
static const Vlc VLC[] = {
    {"11", 0, 1}, {"011", 1, 1}, {"0100", 0, 2}, {"0101", 2, 1}, {"00101", 0, 3}, {"00111", 3, 1},
    {"00110", 4, 1}, {"000110", 1, 2}, {"000111", 5, 1}, {"000101", 6, 1}, {"000100", 7, 1},
    {"0000110", 0, 4}, {"0000100", 2, 2}, {"0000111", 8, 1}, {"0000101", 9, 1},
    {"00100110", 0, 5}, {"00100001", 0, 6}, {"00100101", 1, 3}, {"00100100", 3, 2}, {"00100111", 10, 1},
    {"00100011", 11, 1}, {"00100010", 12, 1}, {"00100000", 13, 1},
    {"0000001010", 0, 7}, {"0000001100", 1, 4}, {"0000001011", 2, 3}, {"0000001111", 4, 2},
    {"0000001001", 5, 2}, {"0000001110", 14, 1}, {"0000001101", 15, 1}, {"0000001000", 16, 1},
    {"000000011101", 0, 8}, {"000000011000", 0, 9}, {"000000010011", 0, 10}, {"000000010000", 0, 11},
    {"000000011011", 1, 5}, {"000000010100", 2, 4}, {"000000011100", 3, 3}, {"000000010010", 4, 3},
    {"000000011110", 6, 2}, {"000000010101", 7, 2}, {"000000010001", 8, 2}, {"000000011111", 17, 1},
    {"000000011010", 18, 1}, {"000000011001", 19, 1}, {"000000010111", 20, 1}, {"000000010110", 21, 1},
    {"0000000011010", 0, 12}, {"0000000011001", 0, 13}, {"0000000011000", 0, 14}, {"0000000010111", 0, 15},
    {"0000000010110", 1, 6}, {"0000000010101", 1, 7}, {"0000000010100", 2, 5}, {"0000000010011", 3, 4},
    {"0000000010010", 5, 3}, {"0000000010001", 9, 2}, {"0000000010000", 10, 2}, {"0000000011111", 22, 1},
    {"0000000011110", 23, 1}, {"0000000011101", 24, 1}, {"0000000011100", 25, 1}, {"0000000011011", 26, 1},
    {"00000000011111", 0, 16}, {"00000000011110", 0, 17}, {"00000000011101", 0, 18}, {"00000000011100", 0, 19},
    {"00000000011011", 0, 20}, {"00000000011010", 0, 21}, {"00000000011001", 0, 22}, {"00000000011000", 0, 23},
    {"00000000010111", 0, 24}, {"00000000010110", 0, 25}, {"00000000010101", 0, 26}, {"00000000010100", 0, 27},
    {"00000000010011", 0, 28}, {"00000000010010", 0, 29}, {"00000000010001", 0, 30}, {"00000000010000", 0, 31},
    {"000000000011000", 0, 32}, {"000000000010111", 0, 33}, {"000000000010110", 0, 34},
    {"000000000010101", 0, 35}, {"000000000010100", 0, 36}, {"000000000010011", 0, 37},
    {"000000000010010", 0, 38}, {"000000000010001", 0, 39}, {"000000000010000", 0, 40},
    {"000000000011111", 1, 8}, {"000000000011110", 1, 9}, {"000000000011101", 1, 10},
    {"000000000011100", 1, 11}, {"000000000011011", 1, 12}, {"000000000011010", 1, 13},
    {"000000000011001", 1, 14},
    {"0000000000010011", 1, 15}, {"0000000000010010", 1, 16}, {"0000000000010001", 1, 17},
    {"0000000000010000", 1, 18}, {"0000000000010100", 6, 3}, {"0000000000011010", 11, 2},
    {"0000000000011001", 12, 2}, {"0000000000011000", 13, 2}, {"0000000000010111", 14, 2},
    {"0000000000010110", 15, 2}, {"0000000000010101", 16, 2}, {"0000000000011111", 27, 1},
    {"0000000000011110", 28, 1}, {"0000000000011101", 29, 1}, {"0000000000011100", 30, 1},
    {"0000000000011011", 31, 1},
};
#define N_VLC ((int)(sizeof VLC / sizeof VLC[0]))

/* Albero binario dei codici: nodo = due figli; foglia = indice in VLC + 1 (negativo), -1000 = EOB, -2000 = escape. */
#define MAX_NODI 1024
static int albero[MAX_NODI][2];
static int n_nodi = 1;

static int aggiungi_codice(const char *bit, int valore) {
    int n = 0;
    for (const char *c = bit; *c; ++c) {
        int b = *c - '0';
        if (c[1] == 0) {
            if (albero[n][b] != 0) return 0;
            albero[n][b] = valore;
            return 1;
        }
        if (albero[n][b] < 0) return 0;
        if (albero[n][b] == 0) {
            if (n_nodi >= MAX_NODI) return 0;
            albero[n][b] = n_nodi++;
        }
        n = albero[n][b];
    }
    return 0;
}

static int prepara_albero(void) {
    memset(albero, 0, sizeof albero);
    n_nodi = 1;
    if (!aggiungi_codice("10", -1000) || !aggiungi_codice("000001", -2000)) return 0;
    for (int i = 0; i < N_VLC; ++i)
        if (!aggiungi_codice(VLC[i].bit, -(i + 1))) {
            fprintf(stderr, "codice VLC doppio o in conflitto: %s\n", VLC[i].bit);
            return 0;
        }
    return 1;
}

/* Lettore dei bit: parole da 16 bit little-endian, dal bit piu' alto. */
typedef struct { const uint8_t *d; size_t n, pos; uint32_t cur; int left; int fine; } Bit;

static int bit1(Bit *b) {
    if (b->left == 0) {
        if (b->pos + 1 >= b->n) { b->fine = 1; return 0; }
        b->cur = (uint32_t)b->d[b->pos] | ((uint32_t)b->d[b->pos + 1] << 8);
        b->pos += 2;
        b->left = 16;
    }
    b->left--;
    return (int)((b->cur >> b->left) & 1u);
}

static int bits(Bit *b, int n) {
    int v = 0;
    while (n--) v = (v << 1) | bit1(b);
    return v;
}

static int segno10(int v) { return (v & 0x200) ? v - 0x400 : v; }

/* Bitstream v2 di un fotogramma -> mezze parole RLE dell'MDEC (Cr, Cb, Y1..Y4 per macroblocco). */
static int vlc_v2(const uint8_t *dati, size_t n, int mb, uint16_t *rle, size_t cap, int *qscale_out,
                  int *versione_out) {
    if (n < 8) return -1;
    const int magic = dati[2] | (dati[3] << 8), qscale = dati[4] | (dati[5] << 8), ver = dati[6] | (dati[7] << 8);
    *qscale_out = qscale;
    *versione_out = ver;
    if (magic != 0x3800 || ver != 2) return -2;
    Bit b = { dati + 8, n - 8, 0, 0, 0, 0 };
    size_t k = 0;
    for (int m = 0; m < mb; ++m) {
        for (int blk = 0; blk < 6; ++blk) {
            if (k + 66 > cap) return -3;
            const int dc = segno10(bits(&b, 10));
            rle[k++] = (uint16_t)(((qscale & 0x3F) << 10) | (dc & 0x3FF));
            int coeff = 0;
            for (;;) {
                int nodo = 0;
                for (int prof = 0; prof < 20; ++prof) {
                    nodo = albero[nodo][bit1(&b)];
                    if (nodo <= 0) break;
                }
                if (b.fine) return -4;
                if (nodo == 0) return -5;               /* codice che non esiste */
                if (nodo == -1000) { rle[k++] = 0xFE00; break; }
                int run, level;
                if (nodo == -2000) {
                    run = bits(&b, 6);
                    level = segno10(bits(&b, 10));
                } else {
                    const Vlc *v = &VLC[-nodo - 1];
                    run = v->run;
                    level = bit1(&b) ? -v->level : v->level;
                }
                coeff += run + 1;
                if (coeff > 63) return -6;
                if (k + 2 > cap) return -3;
                rle[k++] = (uint16_t)(((run & 0x3F) << 10) | (level & 0x3FF));
            }
        }
    }
    return (int)k;
}

/* MDEC di psxrecomp: tabelle una volta, poi decodifica a 24 bit. */
static void mdec_prepara(void) {
    mdec_init();
    mdec_write(0, (2u << 29) | 1u);
    uint8_t q[128];
    memcpy(q, QUANT, 64);
    memcpy(q + 64, QUANT, 64);
    for (int i = 0; i < 128; i += 4)
        mdec_write(0, (uint32_t)q[i] | ((uint32_t)q[i + 1] << 8) | ((uint32_t)q[i + 2] << 16) | ((uint32_t)q[i + 3] << 24));
    mdec_write(0, (3u << 29));
    for (int i = 0; i < 64; i += 2) mdec_write(0, (uint32_t)SCALA[i] | ((uint32_t)SCALA[i + 1] << 16));
}

static int mdec_24(const uint16_t *rle, int n, uint8_t *uscita, size_t byte_attesi) {
    int pari = (n + 1) & ~1;
    mdec_write(0, (1u << 29) | (2u << 27) | (uint32_t)((pari / 2) & 0xFFFF));
    for (int i = 0; i < pari; i += 2) {
        uint32_t lo = rle[i], hi = (i + 1 < n) ? rle[i + 1] : 0xFE00u;
        mdec_write(0, lo | (hi << 16));
    }
    MDECDebugState st;
    mdec_debug_get_state(&st);
    if (st.output_size != byte_attesi) {
        /* svuota comunque l'uscita */
        while (mdec_dma_read_ready()) (void)mdec_dma_read_word();
        return -1;
    }
    for (size_t i = 0; i < byte_attesi; i += 4) {
        uint32_t v = mdec_dma_read_word();
        for (int j = 0; j < 4 && i + (size_t)j < byte_attesi; ++j) uscita[i + (size_t)j] = (uint8_t)(v >> (8 * j));
    }
    return 0;
}

/* Fotogramma: settori del disco in ordine, pezzi da 2016 byte. */
typedef struct {
    int numero, pezzi, ricevuti, w, h;
    long lba_primo, lba_ultimo;
    size_t byte;
    uint8_t *dati;
    uint8_t *visti;
} Foto;

typedef int (*Gestore)(const Foto *f, const uint8_t *rgb, int qscale, int ver, int n_rle, void *ctx);

static long settori_letti, settori_video;
static uint16_t *g_rle_ultimo;

static int scorri(const char *disco, long lba, long n, Gestore g, void *ctx, int decodifica) {
    FILE *fp = fopen(disco, "rb");
    if (!fp) { fprintf(stderr, "non apro %s\n", disco); return 1; }
    uint8_t s[SETTORE];
    Foto f = {0};
    f.numero = -1;
    uint16_t *rle = (uint16_t *)malloc(sizeof(uint16_t) * 400000);
    g_rle_ultimo = rle;
    uint8_t *rgb = NULL;
    size_t rgb_cap = 0;
    int esito = 0;
    for (long i = 0; i < n; ++i) {
        if (SPOSTA(fp, (long long)(lba + i) * SETTORE) != 0 || fread(s, 1, SETTORE, fp) != SETTORE) break;
        settori_letti++;
        const uint8_t *u = s + 24;
        if (!(u[0] == 0x60 && u[1] == 0x01 && u[2] == 0x01 && u[3] == 0x80)) continue;
        settori_video++;
        const int pezzo = u[4] | (u[5] << 8), pezzi = u[6] | (u[7] << 8);
        const int numero = (int)(u[8] | (u[9] << 8) | (u[10] << 16) | ((uint32_t)u[11] << 24));
        const size_t byte = (size_t)(u[12] | (u[13] << 8) | (u[14] << 16) | ((uint32_t)u[15] << 24));
        const int w = u[16] | (u[17] << 8), h = u[18] | (u[19] << 8);
        if (pezzi <= 0 || pezzi > 64 || pezzo >= pezzi || w <= 0 || h <= 0 || w > 640 || h > 512) continue;
        if (numero != f.numero) {
            free(f.dati); free(f.visti);
            memset(&f, 0, sizeof f);
            f.numero = numero; f.pezzi = pezzi; f.w = w; f.h = h; f.byte = byte;
            f.lba_primo = lba + i;
            f.dati = (uint8_t *)calloc((size_t)pezzi, CHUNK);
            f.visti = (uint8_t *)calloc((size_t)pezzi, 1);
        }
        if (!f.visti[pezzo]) { f.visti[pezzo] = 1; f.ricevuti++; }
        memcpy(f.dati + (size_t)pezzo * CHUNK, u + 32, CHUNK);
        f.lba_ultimo = lba + i;
        if (f.ricevuti == f.pezzi) {
            const int mbw = (f.w + 15) / 16, mbh = (f.h + 15) / 16, mb = mbw * mbh;
            int q = 0, ver = 0;
            int k = vlc_v2(f.dati, (size_t)f.pezzi * CHUNK, mb, rle, 400000, &q, &ver);
            uint8_t *img = NULL;
            if (k > 0 && decodifica) {
                const size_t serve = (size_t)mb * 768;
                uint8_t *mbuf = (uint8_t *)malloc(serve);
                if ((size_t)f.w * f.h * 3 > rgb_cap) { rgb_cap = (size_t)f.w * f.h * 3; rgb = (uint8_t *)realloc(rgb, rgb_cap); }
                if (mdec_24(rle, k, mbuf, serve) == 0) {
                    for (int m = 0; m < mb; ++m) {
                        const int cx = m / mbh, cy = m % mbh;       /* macroblocchi per colonne */
                        for (int y = 0; y < 16; ++y) {
                            const int py = cy * 16 + y;
                            if (py >= f.h) break;
                            for (int x = 0; x < 16; ++x) {
                                const int px = cx * 16 + x;
                                if (px >= f.w) break;
                                memcpy(rgb + ((size_t)py * f.w + px) * 3, mbuf + (size_t)m * 768 + ((size_t)y * 16 + x) * 3, 3);
                            }
                        }
                    }
                    img = rgb;
                }
                free(mbuf);
            }
            if (g(&f, img, q, ver, k, ctx)) { esito = 0; break; }
            f.numero = -2;      /* fatto: i pezzi ripetuti dello stesso numero non lo rifanno */
            f.ricevuti = -1000;
        }
    }
    free(f.dati); free(f.visti); free(rle); free(rgb);
    fclose(fp);
    return esito;
}

/* ---------------------------------------------------------------- info */
static int g_info(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    (void)rgb; (void)ctx;
    printf("%d\t%ld\t%ld\t%d\t%zu\t%d\t%d\t%dx%d\t%d\n", f->numero, f->lba_primo, f->lba_ultimo, f->pezzi, f->byte, q,
           ver, f->w, f->h, n_rle);
    return 0;
}

/* ---------------------------------------------------------------- rle (prove) */
static int g_rle(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    (void)rgb; (void)q; (void)ver;
    FILE *o = (FILE *)ctx;
    int32_t hdr[2] = { f->numero, n_rle };
    fwrite(hdr, sizeof hdr, 1, o);
    if (n_rle > 0) fwrite(g_rle_ultimo, sizeof(uint16_t), (size_t)n_rle, o);
    return 0;
}

/* ---------------------------------------------------------------- confronta */
typedef struct {
    const uint8_t *ref; int rw, rh, scala;
    double migliore; int numero, dy; long lba;
    uint8_t *copia; int w, h;
    long fotogrammi, errori;
} Confronto;

static double distanza(const uint8_t *rgb, int w, int h, const Confronto *c, int dy, long *uguali) {
    const int dw = c->rw / c->scala, dh = c->rh / c->scala;
    const int ox = (dw - w) / 2, oy = (dh - h) / 2 + dy;
    if (ox < 0 || oy < 0 || ox + w > dw || oy + h > dh) return 1e9;
    double somma = 0;
    long ug = 0;
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x) {
            const int sx = (ox + x) * c->scala + c->scala / 2, sy = (oy + y) * c->scala + c->scala / 2;
            const uint8_t *r = c->ref + ((size_t)sy * c->rw + sx) * 3, *p = rgb + ((size_t)y * w + x) * 3;
            const int d0 = abs(r[0] - p[0]), d1 = abs(r[1] - p[1]), d2 = abs(r[2] - p[2]);
            somma += d0 + d1 + d2;
            ug += (d0 == 0 && d1 == 0 && d2 == 0);
        }
    if (uguali) *uguali = ug;
    return somma / ((double)w * h * 3);
}

static int g_confronta(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    (void)q; (void)ver; (void)n_rle;
    Confronto *c = (Confronto *)ctx;
    c->fotogrammi++;
    if (!rgb) { c->errori++; return 0; }
    for (int dy = -24; dy <= 24; dy += 1) {
        const double d = distanza(rgb, f->w, f->h, c, dy, NULL);
        if (d < c->migliore) {
            c->migliore = d; c->numero = f->numero; c->dy = dy; c->lba = f->lba_primo;
            c->w = f->w; c->h = f->h;
            free(c->copia);
            c->copia = (uint8_t *)malloc((size_t)f->w * f->h * 3);
            memcpy(c->copia, rgb, (size_t)f->w * f->h * 3);
        }
    }
    return 0;
}

static int scrivi_ppm(const char *path, const uint8_t *rgb, int w, int h) {
    FILE *o = fopen(path, "wb");
    if (!o) return 1;
    fprintf(o, "P6\n%d %d\n255\n", w, h);
    fwrite(rgb, 1, (size_t)w * h * 3, o);
    fclose(o);
    return 0;
}

/* ---------------------------------------------------------------- indice (fmv_hd) */
/* Firma come signature() di psxrecomp (runtime/src/gpu_fmv_hd.c): media della luminosita' (r*77+g*150+b*29)>>8 di
 * ogni cella di una griglia sw x sh sull'immagine w x h. */
static void firma(const uint8_t *rgb, int w, int h, int sw, int sh, uint8_t *out) {
    for (int gy = 0; gy < sh; ++gy) {
        const int ya = gy * h / sh, yb = (gy + 1) * h / sh;
        for (int gx = 0; gx < sw; ++gx) {
            const int xa = gx * w / sw, xb = (gx + 1) * w / sw;
            uint64_t sum = 0;
            uint32_t n = 0;
            for (int y = ya; y < yb; ++y)
                for (int x = xa; x < xb; ++x) {
                    const uint8_t *p = rgb + ((size_t)y * w + x) * 3;
                    sum += ((uint32_t)p[0] * 77 + (uint32_t)p[1] * 150 + (uint32_t)p[2] * 29) >> 8;
                    ++n;
                }
            out[gy * sw + gx] = (uint8_t)(n ? sum / n : 0);
        }
    }
}

typedef struct {
    int sw, sh, w, h, n, cap, errori;
    uint8_t *firme;
    int32_t *lba;
    long *lba_ultimo;
} Indice;

static int g_indice(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    (void)q; (void)ver; (void)n_rle;
    Indice *x = (Indice *)ctx;
    if (!rgb) { x->errori++; return 0; }
    if (x->n == 0) { x->w = f->w; x->h = f->h; }
    if (f->w != x->w || f->h != x->h) { x->errori++; return 0; }
    if (x->n == x->cap) {
        x->cap = x->cap ? x->cap * 2 : 1024;
        x->firme = (uint8_t *)realloc(x->firme, (size_t)x->cap * x->sw * x->sh);
        x->lba = (int32_t *)realloc(x->lba, sizeof(int32_t) * (size_t)x->cap);
        x->lba_ultimo = (long *)realloc(x->lba_ultimo, sizeof(long) * (size_t)x->cap);
    }
    firma(rgb, f->w, f->h, x->sw, x->sh, x->firme + (size_t)x->n * x->sw * x->sh);
    x->lba[x->n] = (int32_t)f->lba_primo;
    x->lba_ultimo[x->n] = f->lba_ultimo;
    x->n++;
    return 0;
}

static void le32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }

static int cmd_indice(const char *disco, long lba, long n, const char *dir, const char *modo, int sw, int sh) {
    Indice x = {0};
    x.sw = sw; x.sh = sh;
    if (sw <= 0 || sw > 64 || sh <= 0 || sh > 64) { fprintf(stderr, "firma troppo grande (massimo 64 x 64)\n"); return 2; }
    const int legacy = !strcmp(modo, "legacy");
    const int ritardo = legacy ? 0 : atoi(modo);
    int r = scorri(disco, lba, n, g_indice, &x, 1);
    if (r || x.n == 0) { fprintf(stderr, "nessun fotogramma decodificato\n"); return 1; }
    for (int i = 1; i < x.n; ++i)
        if (x.lba[i] <= x.lba[i - 1]) { fprintf(stderr, "settori non crescenti al fotogramma %d\n", i); return 1; }
    char p[1100];
    snprintf(p, sizeof p, "%s/index.bin", dir);
    FILE *o = fopen(p, "wb");
    if (!o) { fprintf(stderr, "non scrivo %s\n", p); return 1; }
    uint8_t h[64];
    memset(h, 0, sizeof h);
    memcpy(h, legacy ? "FMVHD002" : "FMVHD003", 8);
    le32(h + 8, (uint32_t)x.n);      /* frames */
    le32(h + 12, (uint32_t)sw);      /* sig_w */
    le32(h + 16, (uint32_t)sh);      /* sig_h */
    le32(h + 20, 1);                 /* sub */
    le32(h + 24, 15);                /* fps_num: 10 settori per fotogramma a velocita' doppia */
    le32(h + 28, 1);                 /* fps_den */
    le32(h + 32, (uint32_t)x.w);     /* src_w */
    le32(h + 36, (uint32_t)x.h);     /* src_h */
    le32(h + 40, 0);                 /* disp_w: 0 = lo schermo che il gioco presenta */
    le32(h + 44, 0);                 /* disp_h */
    le32(h + 48, 0);                 /* off_x: a sinistra. Misurato il 4/11/2026 sulla versione europea: nel quadro PAL
                                      * largo 328 il filmato largo 320 sta a x = 0 (le ultime 8 colonne sono nere); "al
                                      * centro" (x = 4) alzava la distanza delle firme fino a 11. In NTSC (largo 320)
                                      * e' lo stesso. */
    le32(h + 52, (uint32_t)-1);      /* off_y: al centro (verificato: nessuno spostamento verticale in NTSC e PAL) */
    le32(h + 56, (uint32_t)lba);                 /* stream_lba_lo (solo FMVHD003) */
    le32(h + 60, (uint32_t)(lba + n - 1));       /* stream_lba_hi */
    fwrite(h, 1, legacy ? 56 : 64, o);
    fwrite(x.firme, 1, (size_t)x.n * sw * sh, o);
    if (!legacy)
        for (int i = 0; i < x.n; ++i) {
            uint8_t b[4];
            le32(b, (uint32_t)(x.lba[i] + ritardo));
            fwrite(b, 1, 4, o);
        }
    fclose(o);
    snprintf(p, sizeof p, "%s/fotogrammi.tsv", dir);
    o = fopen(p, "w");
    if (o) {
        fprintf(o, "indice\tlba_primo\tlba_ultimo\n");
        for (int i = 0; i < x.n; ++i) fprintf(o, "%d\t%d\t%ld\n", i, x.lba[i], x.lba_ultimo[i]);
        fclose(o);
    }
    printf("{\"fotogrammi\": %d, \"errori\": %d, \"w\": %d, \"h\": %d, \"formato\": \"%s\", \"ritardo\": %d}\n", x.n,
           x.errori, x.w, x.h, legacy ? "FMVHD002" : "FMVHD003", ritardo);
    free(x.firme); free(x.lba); free(x.lba_ultimo);
    return 0;
}

/* ---------------------------------------------------------------- filmati migliorati */
/* Piani Y, Cb, Cr di un fotogramma come li calcola l'MDEC (valori con segno -128..127): si ottengono decodificando gli
 * stessi codici RLE in modo monocromatico (8 bit), dove ogni blocco esce da solo; le tabelle di luminanza e colore
 * sono uguali, quindi i valori coincidono con quelli che l'MDEC usa a 24 bit. */
typedef struct { int w, h, cw, ch; int16_t *Y, *Cb, *Cr; } Piani;

static int mdec_piani(const uint16_t *rle, int n, int mbw, int mbh, Piani *p) {
    const int mb = mbw * mbh;
    const size_t serve = (size_t)mb * 384;
    uint8_t *out = (uint8_t *)malloc(serve);
    if (!out) return -1;
    int pari = (n + 1) & ~1;
    mdec_write(0, (1u << 29) | (1u << 27) | (uint32_t)((pari / 2) & 0xFFFF));
    for (int i = 0; i < pari; i += 2) {
        uint32_t lo = rle[i], hi = (i + 1 < n) ? rle[i + 1] : 0xFE00u;
        mdec_write(0, lo | (hi << 16));
    }
    MDECDebugState st;
    mdec_debug_get_state(&st);
    /* Con un numero dispari di mezze parole l'ultima 0xFE00 aggiunta per arrivare a parole intere diventa, in modo
     * monocromatico, un blocco in piu' alla fine: si prendono solo i blocchi del fotogramma. */
    if (st.output_size < serve || st.output_size > serve + 64) {
        fprintf(stderr, "piani: uscita %u byte invece di %zu (blocchi %u, fine %u, pos %u/%u)\n", st.output_size, serve,
                st.decode_blocks, st.decode_stop_reason, st.decode_input_pos, st.decode_input_end);
        while (mdec_dma_read_ready()) (void)mdec_dma_read_word();
        free(out);
        return -1;
    }
    for (size_t i = 0; i < serve; i += 4) {
        uint32_t v = mdec_dma_read_word();
        out[i] = (uint8_t)v; out[i + 1] = (uint8_t)(v >> 8); out[i + 2] = (uint8_t)(v >> 16); out[i + 3] = (uint8_t)(v >> 24);
    }
    while (mdec_dma_read_ready()) (void)mdec_dma_read_word();
    p->w = mbw * 16; p->h = mbh * 16; p->cw = mbw * 8; p->ch = mbh * 8;
    for (int m = 0; m < mb; ++m) {
        const int cx = m / mbh, cy = m % mbh;          /* macroblocchi per colonne */
        const uint8_t *b = out + (size_t)m * 384;      /* Cr, Cb, Y0, Y1, Y2, Y3 */
        for (int y = 0; y < 8; ++y)
            for (int x = 0; x < 8; ++x) {
                p->Cr[(size_t)(cy * 8 + y) * p->cw + cx * 8 + x] = (int16_t)(b[y * 8 + x] - 128);
                p->Cb[(size_t)(cy * 8 + y) * p->cw + cx * 8 + x] = (int16_t)(b[64 + y * 8 + x] - 128);
            }
        for (int k = 0; k < 4; ++k)
            for (int y = 0; y < 8; ++y)
                for (int x = 0; x < 8; ++x) {
                    const int px = cx * 16 + (k & 1) * 8 + x, py = cy * 16 + (k >> 1) * 8 + y;
                    p->Y[(size_t)py * p->w + px] = (int16_t)(b[128 + k * 64 + y * 8 + x] - 128);
                }
    }
    free(out);
    return 0;
}

static int m9(int v) {
    v = (int)(((int32_t)((uint32_t)v << 23)) >> 23);
    return v < -128 ? -128 : v > 127 ? 127 : v;
}

/* Colori come l'MDEC a 24 bit (colore a quadretti 2x2): per controllare i piani. */
static void rgb_gioco(const Piani *p, int w, int h, uint8_t *rgb) {
    for (int y = 0; y < h; ++y)
        for (int x = 0; x < w; ++x) {
            const int yy = p->Y[(size_t)y * p->w + x];
            const int cr = p->Cr[(size_t)(y >> 1) * p->cw + (x >> 1)], cb = p->Cb[(size_t)(y >> 1) * p->cw + (x >> 1)];
            const int r = m9(yy + (((359 * cr) + 0x80) >> 8));
            const int g = m9(yy + ((((-88 * cb) & ~0x1F) + ((-183 * cr) & ~0x07) + 0x80) >> 8));
            const int b = m9(yy + (((454 * cb) + 0x80) >> 8));
            uint8_t *o = rgb + ((size_t)y * w + x) * 3;
            o[0] = (uint8_t)(r ^ 0x80); o[1] = (uint8_t)(g ^ 0x80); o[2] = (uint8_t)(b ^ 0x80);
        }
}

static int cl(int v, int a, int b) { return v < a ? a : v > b ? b : v; }

/* Attenua i bordi dei blocchi 8x8 dove l'immagine e' piatta e il salto e' piccolo (come i filtri dei codec video):
 * i dettagli veri, con salti grandi o zone non piatte, restano. */
static void deblocca(int16_t *pl, int w, int h, int qscale) {
    /* Valori scelti il 4/11/2026 su VVINTRO (qscale fino a 10): piu' forti spianavano anche le fughe dei mattoni. */
    const int alfa = 2 + (3 * qscale) / 2, beta = 2 + qscale, tc = 1 + qscale / 2;
    for (int pass = 0; pass < 2; ++pass) {
        const int lim_i = pass == 0 ? w : h, lim_j = pass == 0 ? h : w;
        for (int i = 8; i < lim_i; i += 8)
            for (int j = 0; j < lim_j; ++j) {
                int16_t *q = pass == 0 ? pl + (size_t)j * w + i : pl + (size_t)i * w + j;
                const ptrdiff_t s = pass == 0 ? 1 : w;
                const int p2 = q[-3 * s], p1 = q[-2 * s], p0 = q[-s], q0 = q[0], q1 = q[s], q2 = q[2 * s];
                if (abs(q0 - p0) >= alfa || abs(p1 - p0) >= beta || abs(q1 - q0) >= beta) continue;
                const int d = cl(((q0 - p0) * 4 + (p1 - q1) + 4) >> 3, -tc, tc);
                q[-s] = (int16_t)cl(p0 + d, -128, 127);
                q[0] = (int16_t)cl(q0 - d, -128, 127);
                if (abs(p2 - p0) < beta) q[-2 * s] = (int16_t)cl(p1 + cl(((p2 + ((p0 + q0 + 1) >> 1)) >> 1) - p1, -tc / 2, tc / 2), -128, 127);
                if (abs(q2 - q0) < beta) q[s] = (int16_t)cl(q1 + cl(((q2 + ((p0 + q0 + 1) >> 1)) >> 1) - q1, -tc / 2, tc / 2), -128, 127);
            }
    }
}

/* Colore interpolato (bilineare, campioni al centro di ogni 2x2) e conversione con i coefficienti dell'MDEC. */
static void rgb_morbido(const Piani *p, int w, int h, float *rgb) {
    for (int y = 0; y < h; ++y) {
        float fy = (y - 0.5f) * 0.5f;
        int y0 = (int)floorf(fy);
        float ay = fy - (float)y0;
        int ya = cl(y0, 0, p->ch - 1), yb = cl(y0 + 1, 0, p->ch - 1);
        for (int x = 0; x < w; ++x) {
            float fx = (x - 0.5f) * 0.5f;
            int x0 = (int)floorf(fx);
            float ax = fx - (float)x0;
            int xa = cl(x0, 0, p->cw - 1), xb = cl(x0 + 1, 0, p->cw - 1);
            const float cr = (1 - ay) * ((1 - ax) * p->Cr[(size_t)ya * p->cw + xa] + ax * p->Cr[(size_t)ya * p->cw + xb]) +
                             ay * ((1 - ax) * p->Cr[(size_t)yb * p->cw + xa] + ax * p->Cr[(size_t)yb * p->cw + xb]);
            const float cb = (1 - ay) * ((1 - ax) * p->Cb[(size_t)ya * p->cw + xa] + ax * p->Cb[(size_t)ya * p->cw + xb]) +
                             ay * ((1 - ax) * p->Cb[(size_t)yb * p->cw + xa] + ax * p->Cb[(size_t)yb * p->cw + xb]);
            const float yy = p->Y[(size_t)y * p->w + x];
            float *o = rgb + ((size_t)y * w + x) * 3;
            o[0] = yy + 1.40234375f * cr + 128.0f;
            o[1] = yy - 0.34375f * cb - 0.71484375f * cr + 128.0f;
            o[2] = yy + 1.7734375f * cb + 128.0f;
        }
    }
}

/* Ingrandimento Lanczos (a = 3) di un fattore intero s, separabile, sui tre canali in virgola mobile. */
static float lanczos3(float x) {
    if (x == 0) return 1.0f;
    if (x <= -3.0f || x >= 3.0f) return 0.0f;
    const float px = 3.14159265358979f * x;
    return 3.0f * sinf(px) * sinf(px / 3.0f) / (px * px);
}

static void ingrandisci(const float *src, int w, int h, int s, float *dst) {
    const int W = w * s, H = h * s;
    float *tmp = (float *)malloc(sizeof(float) * (size_t)W * h * 3);
    float pesi[8][6];
    for (int f = 0; f < s; ++f) {
        const float c = (f + 0.5f) / s - 0.5f;          /* posizione nella sorgente rispetto al pixel 0 della fase */
        const int base = (int)floorf(c) - 2;
        float tot = 0;
        for (int k = 0; k < 6; ++k) { pesi[f][k] = lanczos3(c - (float)(base + k)); tot += pesi[f][k]; }
        for (int k = 0; k < 6; ++k) pesi[f][k] /= tot;
    }
    for (int y = 0; y < h; ++y)
        for (int X = 0; X < W; ++X) {
            const int sx = X / s, f = X % s;
            const float c = (f + 0.5f) / s - 0.5f;
            const int base = sx + (int)floorf(c) - 2;
            float a0 = 0, a1 = 0, a2 = 0;
            for (int k = 0; k < 6; ++k) {
                const int xx = cl(base + k, 0, w - 1);
                const float *q = src + ((size_t)y * w + xx) * 3;
                a0 += pesi[f][k] * q[0]; a1 += pesi[f][k] * q[1]; a2 += pesi[f][k] * q[2];
            }
            float *o = tmp + ((size_t)y * W + X) * 3;
            o[0] = a0; o[1] = a1; o[2] = a2;
        }
    for (int Y = 0; Y < H; ++Y) {
        const int sy = Y / s, f = Y % s;
        const float c = (f + 0.5f) / s - 0.5f;
        const int base = sy + (int)floorf(c) - 2;
        for (int X = 0; X < W; ++X) {
            float a0 = 0, a1 = 0, a2 = 0;
            for (int k = 0; k < 6; ++k) {
                const int yy = cl(base + k, 0, h - 1);
                const float *q = tmp + ((size_t)yy * W + X) * 3;
                a0 += pesi[f][k] * q[0]; a1 += pesi[f][k] * q[1]; a2 += pesi[f][k] * q[2];
            }
            float *o = dst + ((size_t)Y * W + X) * 3;
            o[0] = a0; o[1] = a1; o[2] = a2;
        }
    }
    free(tmp);
}

/* Nitidezza adattiva al contrasto (come il CAS di AMD, scritto da capo): rinforza i bordi dove il contrasto locale e'
 * basso e lascia stare quelli gia' netti, cosi' non crea aloni. Il peso viene dal verde, il piu' vicino alla luminanza. */
static void nitidezza(float *img, int w, int h, float forza, float *tmp) {
    memcpy(tmp, img, sizeof(float) * (size_t)w * h * 3);
    const float picco = -1.0f / (8.0f - 3.0f * forza);
    for (int y = 0; y < h; ++y) {
        const int yn = y > 0 ? y - 1 : 0, ys = y < h - 1 ? y + 1 : h - 1;
        for (int x = 0; x < w; ++x) {
            const int xw = x > 0 ? x - 1 : 0, xe = x < w - 1 ? x + 1 : w - 1;
            const float *c = tmp + ((size_t)y * w + x) * 3, *n = tmp + ((size_t)yn * w + x) * 3,
                        *s = tmp + ((size_t)ys * w + x) * 3, *e = tmp + ((size_t)y * w + xe) * 3,
                        *o = tmp + ((size_t)y * w + xw) * 3;
            float mn = c[1], mx = c[1];
            const float g[4] = { n[1], s[1], e[1], o[1] };
            for (int k = 0; k < 4; ++k) { if (g[k] < mn) mn = g[k]; if (g[k] > mx) mx = g[k]; }
            mn /= 255.0f; mx /= 255.0f;
            if (mn < 0) mn = 0;
            if (mx > 1) mx = 1;
            float a = mx > 1e-5f ? (mn < 1.0f - mx ? mn : 1.0f - mx) / mx : 0.0f;
            a = a < 0 ? 0 : a > 1 ? 1 : a;
            const float pw = sqrtf(a) * picco;
            float *d = img + ((size_t)y * w + x) * 3;
            for (int ch = 0; ch < 3; ++ch) d[ch] = (c[ch] + pw * (n[ch] + s[ch] + e[ch] + o[ch])) / (1.0f + 4.0f * pw);
        }
    }
}

typedef struct {
    Indice ix;
    const char *dir;
    int scala, qualita;
    long diversi, scritti, errori_jpeg;
    unsigned long long byte;
    Piani p;
    float *f1, *f2, *f3;
    uint8_t *rgb8, *chk;
} Pacchetto;

static int g_pacchetto(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    Pacchetto *k = (Pacchetto *)ctx;
    const int prima = k->ix.n;
    g_indice(f, rgb, q, ver, n_rle, &k->ix);
    if (k->ix.n == prima || !rgb) return 0;      /* fotogramma non usabile: gia' contato in errori */
    const int mbw = (f->w + 15) / 16, mbh = (f->h + 15) / 16;
    if (!k->p.Y) {
        k->p.Y = (int16_t *)malloc(sizeof(int16_t) * (size_t)mbw * 16 * mbh * 16);
        k->p.Cb = (int16_t *)malloc(sizeof(int16_t) * (size_t)mbw * 8 * mbh * 8);
        k->p.Cr = (int16_t *)malloc(sizeof(int16_t) * (size_t)mbw * 8 * mbh * 8);
        k->f1 = (float *)malloc(sizeof(float) * (size_t)f->w * f->h * 3);
        k->f2 = (float *)malloc(sizeof(float) * (size_t)f->w * f->h * 3 * k->scala * k->scala);
        k->f3 = (float *)malloc(sizeof(float) * (size_t)f->w * f->h * 3 * k->scala * k->scala);
        k->rgb8 = (uint8_t *)malloc((size_t)f->w * f->h * 3 * k->scala * k->scala);
        k->chk = (uint8_t *)malloc((size_t)f->w * f->h * 3);
    }
    if (mdec_piani(g_rle_ultimo, n_rle, mbw, mbh, &k->p) != 0) { fprintf(stderr, "piani non decodificati: fotogramma %d\n", f->numero); k->errori_jpeg++; return 0; }
    rgb_gioco(&k->p, f->w, f->h, k->chk);
    if (memcmp(k->chk, rgb, (size_t)f->w * f->h * 3) != 0) k->diversi++;
    deblocca(k->p.Y, k->p.w, k->p.h, q);
    deblocca(k->p.Cb, k->p.cw, k->p.ch, q);
    deblocca(k->p.Cr, k->p.cw, k->p.ch, q);
    rgb_morbido(&k->p, f->w, f->h, k->f1);
    const int W = f->w * k->scala, H = f->h * k->scala;
    if (k->scala > 1) ingrandisci(k->f1, f->w, f->h, k->scala, k->f2);
    float *src = k->scala > 1 ? k->f2 : k->f1;
    nitidezza(src, W, H, 0.6f, k->f3);
    for (size_t i = 0; i < (size_t)W * H * 3; ++i) {
        const float v = src[i] + 0.5f;
        k->rgb8[i] = (uint8_t)(v < 0 ? 0 : v > 255 ? 255 : (int)v);
    }
    char path[1100];
    snprintf(path, sizeof path, "%s/frames/%06d.jpg", k->dir, prima);
    if (jpeg_scrivi(path, k->rgb8, W, H, k->qualita) != 0) { fprintf(stderr, "jpeg non scritto: %s\n", path); k->errori_jpeg++; return 0; }
    FILE *t = fopen(path, "rb");
    if (t) {
        SPOSTA(t, 0);
        fseek(t, 0, SEEK_END);
        k->byte += (unsigned long long)ftell(t);
        fclose(t);
    }
    k->scritti++;
    return 0;
}

#if defined(_WIN32)
#include <direct.h>
static void crea_cartella(const char *p) { (void)_mkdir(p); }
#else
#include <sys/stat.h>
static void crea_cartella(const char *p) { (void)mkdir(p, 0755); }
#endif

static int cmd_pacchetto(const char *disco, long lba, long n, const char *dir, int ritardo, int scala, int qualita,
                         int sw, int sh) {
    if (scala < 1 || scala > 4 || qualita < 10 || qualita > 100) { fprintf(stderr, "scala 1-4, qualita' 10-100\n"); return 2; }
    char p[1100];
    snprintf(p, sizeof p, "%s/frames", dir);
    crea_cartella(dir);
    crea_cartella(p);
    Pacchetto k;
    memset(&k, 0, sizeof k);
    k.ix.sw = sw; k.ix.sh = sh;
    k.dir = dir; k.scala = scala; k.qualita = qualita;
    int r = scorri(disco, lba, n, g_pacchetto, &k, 1);
    if (r || k.ix.n == 0) { fprintf(stderr, "nessun fotogramma\n"); return 1; }
    /* index.bin come "indice", con i fotogrammi gia' raccolti */
    Indice *x = &k.ix;
    snprintf(p, sizeof p, "%s/index.bin", dir);
    FILE *o = fopen(p, "wb");
    if (!o) return 1;
    uint8_t h[64];
    memset(h, 0, sizeof h);
    memcpy(h, "FMVHD003", 8);
    le32(h + 8, (uint32_t)x->n); le32(h + 12, (uint32_t)sw); le32(h + 16, (uint32_t)sh); le32(h + 20, 1);
    le32(h + 24, 15); le32(h + 28, 1); le32(h + 32, (uint32_t)x->w); le32(h + 36, (uint32_t)x->h);
    le32(h + 40, 0); le32(h + 44, 0); le32(h + 48, 0); le32(h + 52, (uint32_t)-1);   /* off_x 0: vedi sopra */
    le32(h + 56, (uint32_t)lba); le32(h + 60, (uint32_t)(lba + n - 1));
    fwrite(h, 1, 64, o);
    fwrite(x->firme, 1, (size_t)x->n * sw * sh, o);
    for (int i = 0; i < x->n; ++i) { uint8_t b[4]; le32(b, (uint32_t)(x->lba[i] + ritardo)); fwrite(b, 1, 4, o); }
    fclose(o);
    printf("{\"fotogrammi\": %d, \"errori\": %d, \"jpeg\": %ld, \"errori_jpeg\": %ld, \"diversi_dall_mdec\": %ld, "
           "\"byte\": %llu, \"w\": %d, \"h\": %d, \"scala\": %d, \"qualita\": %d, \"ritardo\": %d}\n",
           x->n, x->errori, k.scritti, k.errori_jpeg, k.diversi, k.byte, x->w * scala, x->h * scala, scala, qualita,
           ritardo);
    return k.errori_jpeg || x->errori ? 1 : 0;
}

/* ---------------------------------------------------------------- grezzi e jpeg (0.12: filmati IA) */
typedef struct { Indice ix; long scritti, errori; } Grezzi;

static int g_grezzi(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    Grezzi *k = (Grezzi *)ctx;
    const int prima = k->ix.n;
    g_indice(f, rgb, q, ver, n_rle, &k->ix);
    if (k->ix.n == prima || !rgb) return 0;      /* fotogramma non usabile: gia' contato in errori */
    uint8_t h[8];
    le32(h, (uint32_t)prima);
    h[4] = (uint8_t)(f->w & 0xFF); h[5] = (uint8_t)(f->w >> 8);
    h[6] = (uint8_t)(f->h & 0xFF); h[7] = (uint8_t)(f->h >> 8);
    const size_t n = (size_t)f->w * f->h * 3;
    if (fwrite(h, 1, 8, stdout) != 8 || fwrite(rgb, 1, n, stdout) != n) {
        k->errori++;
        return 1;                                /* chi legge ha chiuso: basta */
    }
    k->scritti++;
    return 0;
}

static int cmd_grezzi(const char *disco, long lba, long n, const char *dir, int ritardo, int sw, int sh) {
#if defined(_WIN32)
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    crea_cartella(dir);
    Grezzi k;
    memset(&k, 0, sizeof k);
    k.ix.sw = sw; k.ix.sh = sh;
    int r = scorri(disco, lba, n, g_grezzi, &k, 1);
    fflush(stdout);
    Indice *x = &k.ix;
    if (r || x->n == 0) { fprintf(stderr, "nessun fotogramma\n"); return 1; }
    char p[1100];
    snprintf(p, sizeof p, "%s/index.bin", dir);
    FILE *o = fopen(p, "wb");
    if (!o) return 1;
    uint8_t h[64];
    memset(h, 0, sizeof h);
    memcpy(h, "FMVHD003", 8);
    le32(h + 8, (uint32_t)x->n); le32(h + 12, (uint32_t)sw); le32(h + 16, (uint32_t)sh); le32(h + 20, 1);
    le32(h + 24, 15); le32(h + 28, 1); le32(h + 32, (uint32_t)x->w); le32(h + 36, (uint32_t)x->h);
    le32(h + 40, 0); le32(h + 44, 0); le32(h + 48, 0); le32(h + 52, (uint32_t)-1);   /* come "pacchetto" */
    le32(h + 56, (uint32_t)lba); le32(h + 60, (uint32_t)(lba + n - 1));
    fwrite(h, 1, 64, o);
    fwrite(x->firme, 1, (size_t)x->n * sw * sh, o);
    for (int i = 0; i < x->n; ++i) { uint8_t b[4]; le32(b, (uint32_t)(x->lba[i] + ritardo)); fwrite(b, 1, 4, o); }
    fclose(o);
    fprintf(stderr, "{\"fotogrammi\": %d, \"errori\": %d, \"scritti\": %ld, \"errori_uscita\": %ld, \"w\": %d, "
            "\"h\": %d, \"ritardo\": %d}\n", x->n, x->errori, k.scritti, k.errori, x->w, x->h, ritardo);
    return x->errori || k.errori ? 1 : 0;
}

/* Stabilizzazione nel tempo (stessa matematica di sm2_ia.Stabilizzatore, provata in numpy sul laboratorio di HELLO). */
typedef struct {
    int lw, lh, W, H, pronto;
    float *lum_prec, *lum, *y, *storia, *vy, *vx, *af, *fby, *fbx, *fbr;
    float peso, taglio;
} Stab;

static void stab_libera(Stab *s) {
    free(s->lum_prec); free(s->lum); free(s->y); free(s->storia); free(s->vy); free(s->vx); free(s->af);
    free(s->fby); free(s->fbx); free(s->fbr);
    memset(s, 0, sizeof *s);
}

static float st_clampf(float v, float a, float b) { return v < a ? a : v > b ? b : v; }
static int st_clampi(int v, int a, int b) { return v < a ? a : v > b ? b : v; }

/* movimento a blocchi 8x8 (raggio 4) di cur rispetto a prec, mezzo pixel con la parabola; costo rimasto per blocco */
static void st_flusso(const float *prec, const float *cur, int w, int h, float *fy, float *fx, float *resto) {
    enum { B = 8, R = 4, N = 2 * R + 1 };
    const int hb = h / B, wb = w / B;
    float costi[N][N];
    for (int by = 0; by < hb; ++by)
        for (int bx = 0; bx < wb; ++bx) {
            for (int dy = -R; dy <= R; ++dy)
                for (int dx = -R; dx <= R; ++dx) {
                    float somma = 0;
                    for (int y = 0; y < B; ++y) {
                        const int cy = by * B + y, py = st_clampi(cy + dy, 0, h - 1);
                        for (int x = 0; x < B; ++x) {
                            const int cx = bx * B + x, px = st_clampi(cx + dx, 0, w - 1);
                            const float d = cur[(size_t)cy * w + cx] - prec[(size_t)py * w + px];
                            somma += d < 0 ? -d : d;
                        }
                    }
                    costi[dy + R][dx + R] = somma / (B * B);
                }
            costi[R][R] -= 0.25f;                 /* a parita', meglio fermo */
            int iy = 0, ix = 0;
            float m = costi[0][0];
            for (int a = 0; a < N; ++a)
                for (int b = 0; b < N; ++b)
                    if (costi[a][b] < m) { m = costi[a][b]; iy = a; ix = b; }
            const float c0 = costi[iy][ix];
            float sy = 0, sx = 0;
            if (iy > 0 && iy < N - 1) {
                const float ia = costi[iy - 1][ix], ib = costi[iy + 1][ix], den = ia - 2 * c0 + ib;
                if (den > 1e-6f || den < -1e-6f) sy = st_clampf(0.5f * (ia - ib) / den, -0.5f, 0.5f);
            }
            if (ix > 0 && ix < N - 1) {
                const float ia = costi[iy][ix - 1], ib = costi[iy][ix + 1], den = ia - 2 * c0 + ib;
                if (den > 1e-6f || den < -1e-6f) sx = st_clampf(0.5f * (ia - ib) / den, -0.5f, 0.5f);
            }
            const size_t k = (size_t)by * wb + bx;
            fy[k] = (float)(iy - R) + sy;
            fx[k] = (float)(ix - R) + sx;
            resto[k] = m + ((iy == R && ix == R) ? 0.25f : 0.0f);
        }
}

/* da un valore per blocco a un valore per pixel (bilineare tra i centri dei blocchi), moltiplicato per k */
static void st_campo(const float *c, int hb, int wb, int blocco, int H, int W, float k, float *out) {
    for (int y = 0; y < H; ++y) {
        const float ys = (y + 0.5f) / blocco - 0.5f;
        const int y0 = st_clampi((int)floorf(ys), 0, hb - 1), y1 = st_clampi(y0 + 1, 0, hb - 1);
        const float ay = st_clampf(ys - y0, 0, 1);
        for (int x = 0; x < W; ++x) {
            const float xs = (x + 0.5f) / blocco - 0.5f;
            const int x0 = st_clampi((int)floorf(xs), 0, wb - 1), x1 = st_clampi(x0 + 1, 0, wb - 1);
            const float ax = st_clampf(xs - x0, 0, 1);
            const float v = (1 - ay) * ((1 - ax) * c[(size_t)y0 * wb + x0] + ax * c[(size_t)y0 * wb + x1]) +
                            ay * ((1 - ax) * c[(size_t)y1 * wb + x0] + ax * c[(size_t)y1 * wb + x1]);
            out[(size_t)y * W + x] = v * k;
        }
    }
}

/* un passo: grande (W x H x 3) e originale (lw x lh x 3) in byte; scrive il risultato in byte in out */
static int stab_passo(Stab *s, const uint8_t *grande, int W, int H, const uint8_t *orig, int lw, int lh, uint8_t *out) {
    const size_t n = (size_t)W * H * 3, nl = (size_t)lw * lh;
    const int scala = lw > 0 ? W / lw : 0;
    if (!orig || lw <= 0 || lh <= 0 || scala <= 0 || scala * lw != W || scala * lh != H) {
        memcpy(out, grande, n);
        s->pronto = 0;
        return 0;
    }
    if (s->W != W || s->H != H || s->lw != lw || s->lh != lh) {
        const float peso = s->peso, taglio = s->taglio;
        stab_libera(s);
        s->peso = peso; s->taglio = taglio;
        s->W = W; s->H = H; s->lw = lw; s->lh = lh;
        const int hb = lh / 8, wb = lw / 8;
        s->lum_prec = (float *)malloc(sizeof(float) * nl); s->lum = (float *)malloc(sizeof(float) * nl);
        s->y = (float *)malloc(sizeof(float) * n); s->storia = (float *)malloc(sizeof(float) * n);
        s->vy = (float *)malloc(sizeof(float) * (size_t)W * H); s->vx = (float *)malloc(sizeof(float) * (size_t)W * H);
        s->af = (float *)malloc(sizeof(float) * (size_t)W * H);
        s->fby = (float *)malloc(sizeof(float) * (size_t)(hb > 0 ? hb : 1) * (wb > 0 ? wb : 1));
        s->fbx = (float *)malloc(sizeof(float) * (size_t)(hb > 0 ? hb : 1) * (wb > 0 ? wb : 1));
        s->fbr = (float *)malloc(sizeof(float) * (size_t)(hb > 0 ? hb : 1) * (wb > 0 ? wb : 1));
        if (!s->lum_prec || !s->lum || !s->y || !s->storia || !s->vy || !s->vx || !s->af || !s->fby || !s->fbx || !s->fbr)
            return 1;
    }
    for (size_t i = 0; i < nl; ++i)
        s->lum[i] = orig[i * 3] * 0.299f + orig[i * 3 + 1] * 0.587f + orig[i * 3 + 2] * 0.114f;
    double diff = 0;
    if (s->pronto)
        for (size_t i = 0; i < nl; ++i) diff += fabsf(s->lum[i] - s->lum_prec[i]);
    if (!s->pronto || diff / (double)nl > s->taglio || lw < 8 || lh < 8) {      /* inizio o cambio di scena */
        for (size_t i = 0; i < n; ++i) s->y[i] = grande[i] / 255.0f;
        memcpy(s->lum_prec, s->lum, sizeof(float) * nl);
        memcpy(out, grande, n);
        s->pronto = 1;
        return 0;
    }
    const int hb = lh / 8, wb = lw / 8, bh = 8 * scala;
    st_flusso(s->lum_prec, s->lum, lw, lh, s->fby, s->fbx, s->fbr);
    for (int i = 0; i < hb * wb; ++i) s->fbr[i] = st_clampf((s->fbr[i] - 6.0f) / 10.0f, 0, 1);
    st_campo(s->fby, hb, wb, bh, H, W, (float)scala, s->vy);
    st_campo(s->fbx, hb, wb, bh, H, W, (float)scala, s->vx);
    st_campo(s->fbr, hb, wb, bh, H, W, 1.0f, s->af);
    /* storia: l'uscita di prima letta dove il movimento dice (bilineare, bordi bloccati) */
    for (int y = 0; y < H; ++y)
        for (int x = 0; x < W; ++x) {
            const size_t p = (size_t)y * W + x;
            const float yy = st_clampf(y + s->vy[p], 0, (float)(H - 1)), xx = st_clampf(x + s->vx[p], 0, (float)(W - 1));
            const int y0 = (int)floorf(yy), x0 = (int)floorf(xx);
            const int y1 = y0 + 1 < H ? y0 + 1 : H - 1, x1 = x0 + 1 < W ? x0 + 1 : W - 1;
            const float ay = yy - y0, ax = xx - x0;
            for (int c = 0; c < 3; ++c) {
                const float v00 = s->y[((size_t)y0 * W + x0) * 3 + c], v01 = s->y[((size_t)y0 * W + x1) * 3 + c];
                const float v10 = s->y[((size_t)y1 * W + x0) * 3 + c], v11 = s->y[((size_t)y1 * W + x1) * 3 + c];
                s->storia[p * 3 + c] = (1 - ay) * ((1 - ax) * v00 + ax * v01) + ay * ((1 - ax) * v10 + ax * v11);
            }
        }
    /* dentro i valori 3x3 della nuova, poi la miscela */
    for (int y = 0; y < H; ++y)
        for (int x = 0; x < W; ++x) {
            const size_t p = (size_t)y * W + x;
            const float a = s->peso + (1 - s->peso) * s->af[p];
            for (int c = 0; c < 3; ++c) {
                float mn = 1e9f, mx = -1e9f;
                for (int dy = -1; dy <= 1; ++dy) {
                    const int yy = st_clampi(y + dy, 0, H - 1);
                    for (int dx = -1; dx <= 1; ++dx) {
                        const int xx = st_clampi(x + dx, 0, W - 1);
                        const float v = grande[((size_t)yy * W + xx) * 3 + c] / 255.0f;
                        if (v < mn) mn = v;
                        if (v > mx) mx = v;
                    }
                }
                const float st = st_clampf(s->storia[p * 3 + c], mn, mx);
                const float v = a * (grande[p * 3 + c] / 255.0f) + (1 - a) * st;
                s->y[p * 3 + c] = v;
                const float o = v * 255.0f + 0.5f;
                out[p * 3 + c] = (uint8_t)(o < 0 ? 0 : o > 255 ? 255 : (int)o);
            }
        }
    memcpy(s->lum_prec, s->lum, sizeof(float) * nl);
    return 0;
}

static int cmd_jpeg(const char *dir, int qualita, int peso) {
    if (qualita < 10 || qualita > 100 || peso < 0 || peso > 100) { fprintf(stderr, "qualita' 10-100, peso 0-100\n"); return 2; }
#if defined(_WIN32)
    _setmode(_fileno(stdin), _O_BINARY);
#endif
    crea_cartella(dir);
    uint8_t *grande = NULL, *orig = NULL, *usc = NULL;
    size_t cap = 0, cap_o = 0;
    long scritti = 0, errori = 0;
    unsigned long long byte = 0;
    Stab st;
    memset(&st, 0, sizeof st);
    st.peso = peso / 100.0f;
    st.taglio = 30.0f;
    for (;;) {
        uint8_t h[12];
        if (fread(h, 1, 12, stdin) != 12) break;
        const uint32_t num = (uint32_t)h[0] | ((uint32_t)h[1] << 8) | ((uint32_t)h[2] << 16) | ((uint32_t)h[3] << 24);
        const int W = h[4] | (h[5] << 8), H = h[6] | (h[7] << 8), lw = h[8] | (h[9] << 8), lh = h[10] | (h[11] << 8);
        if (W <= 0 || H <= 0 || W > 8192 || H > 8192 || lw > 4096 || lh > 4096) {
            fprintf(stderr, "dimensioni non valide\n"); errori++; break;
        }
        const size_t n = (size_t)W * H * 3, no = (size_t)lw * lh * 3;
        if (n > cap) {
            cap = n;
            grande = (uint8_t *)realloc(grande, cap);
            usc = (uint8_t *)realloc(usc, cap);
            if (!grande || !usc) return 1;
        }
        if (no > cap_o) { cap_o = no; orig = (uint8_t *)realloc(orig, cap_o); if (!orig) return 1; }
        if (fread(grande, 1, n, stdin) != n || (no && fread(orig, 1, no, stdin) != no)) {
            fprintf(stderr, "fotogramma %u incompleto\n", num); errori++; break;
        }
        const uint8_t *da_scrivere = grande;
        if (peso < 100 && no) {
            if (stab_passo(&st, grande, W, H, orig, lw, lh, usc) != 0) { fprintf(stderr, "memoria\n"); errori++; break; }
            da_scrivere = usc;
        }
        char p[1100];
        snprintf(p, sizeof p, "%s/%06u.jpg", dir, num);
        if (jpeg_scrivi(p, da_scrivere, W, H, qualita) != 0) { fprintf(stderr, "jpeg non scritto: %s\n", p); errori++; break; }
        FILE *t = fopen(p, "rb");
        if (t) {
            fseek(t, 0, SEEK_END);
            byte += (unsigned long long)ftell(t);
            fclose(t);
        }
        scritti++;
    }
    stab_libera(&st);
    free(grande); free(orig); free(usc);
    printf("{\"jpeg\": %ld, \"errori\": %ld, \"byte\": %llu}\n", scritti, errori, byte);
    return errori ? 1 : 0;
}

static int cmd_ritaglio(const char *in, const char *out, int x, int y, int w, int h) {
    int iw = 0, ih = 0, n = 0;
    uint8_t *img = stbi_load(in, &iw, &ih, &n, 3);
    if (!img) { fprintf(stderr, "immagine non letta: %s\n", in); return 1; }
    if (x < 0 || y < 0 || w <= 0 || h <= 0 || x + w > iw || y + h > ih) {
        fprintf(stderr, "ritaglio fuori dall'immagine (%dx%d)\n", iw, ih);
        stbi_image_free(img);
        return 1;
    }
    uint8_t *r = (uint8_t *)malloc((size_t)w * h * 3);
    if (!r) { stbi_image_free(img); return 1; }
    for (int j = 0; j < h; ++j) memcpy(r + (size_t)j * w * 3, img + ((size_t)(y + j) * iw + x) * 3, (size_t)w * 3);
    const int esito = scrivi_ppm(out, r, w, h);
    free(r);
    stbi_image_free(img);
    return esito ? 1 : 0;
}

/* ---------------------------------------------------------------- estrai */
typedef struct { const char *dir; int ogni; long scritti, errori; } Estrai;

static int g_estrai(const Foto *f, const uint8_t *rgb, int q, int ver, int n_rle, void *ctx) {
    (void)q; (void)ver; (void)n_rle;
    Estrai *e = (Estrai *)ctx;
    if (!rgb) { e->errori++; return 0; }
    if (e->ogni > 1 && (f->numero % e->ogni) != 1) return 0;
    char p[1024];
    snprintf(p, sizeof p, "%s/%06d.ppm", e->dir, f->numero);
    if (scrivi_ppm(p, rgb, f->w, f->h) == 0) e->scritti++;
    return 0;
}

/* ---------------------------------------------------------------- sfondo del launcher (0.12) */
static double liscio(double a, double b, double x) {
    x = (x - a) / (b - a);
    if (x < 0) x = 0;
    if (x > 1) x = 1;
    return x * x * (3 - 2 * x);
}

static int cmd_sfondo(const char *in, const char *out, int W, int H, int centro, int scuro) {
    int iw = 0, ih = 0, n = 0;
    if (W < 16 || H < 8 || W > 16384 || H > 4096) { fprintf(stderr, "grandezza non valida\n"); return 2; }
    if (scuro < 0 || scuro > 100) { fprintf(stderr, "scuro va da 0 a 100\n"); return 2; }
    const double p = scuro / 100.0;             /* quanto conta lo scurimento (1 = tutto, 0 = niente) */
    uint8_t *img = stbi_load(in, &iw, &ih, &n, 3);
    if (!img || iw < 2 || ih < 2) { fprintf(stderr, "immagine non letta: %s\n", in); return 1; }
    double s = (double)W / iw;                   /* il fotogramma intero in larghezza... */
    if (ih * s < H) s = (double)H / ih;          /* ...ma almeno tutta l'altezza */
    const double sw = W / s, sh = H / s;         /* parte del fotogramma usata */
    const double x0 = (iw - sw) / 2.0;
    double y0 = ih * (centro / 1000.0) - sh / 2.0;
    if (y0 < 0) y0 = 0;
    if (y0 > ih - sh) y0 = ih - sh;
    int k = s < 1.0 ? (int)(1.0 / s + 0.999) : 1;  /* campioni per lato quando si rimpicciolisce */
    if (k > 8) k = 8;
    uint8_t *o = (uint8_t *)malloc((size_t)W * H * 3);
    if (!o) { stbi_image_free(img); return 3; }
    for (int Y = 0; Y < H; ++Y) {
        const double scuro_y = 1.0 - 0.45 * liscio(0.55, 1.0, (Y + 0.5) / H);
        for (int X = 0; X < W; ++X) {
            double acc[3] = {0, 0, 0};
            for (int sy = 0; sy < k; ++sy) {
                for (int sx = 0; sx < k; ++sx) {
                    double u = x0 + (X + (sx + 0.5) / k) / s - 0.5, v = y0 + (Y + (sy + 0.5) / k) / s - 0.5;
                    if (u < 0) u = 0;
                    if (v < 0) v = 0;
                    if (u > iw - 1) u = iw - 1;
                    if (v > ih - 1) v = ih - 1;
                    const int xa = (int)u, ya = (int)v;
                    const int xb = xa + 1 < iw ? xa + 1 : xa, yb = ya + 1 < ih ? ya + 1 : ya;
                    const double fx = u - xa, fy = v - ya;
                    for (int c = 0; c < 3; ++c) {
                        const double p00 = img[((size_t)ya * iw + xa) * 3 + c], p10 = img[((size_t)ya * iw + xb) * 3 + c];
                        const double p01 = img[((size_t)yb * iw + xa) * 3 + c], p11 = img[((size_t)yb * iw + xb) * 3 + c];
                        acc[c] += (p00 * (1 - fx) + p10 * fx) * (1 - fy) + (p01 * (1 - fx) + p11 * fx) * fy;
                    }
                }
            }
            const double d = (0.28 + 0.72 * liscio(0.10, 0.62, (X + 0.5) / W)) * scuro_y;   /* 1 = come prima */
            const double f = (1.0 - p * (1.0 - d)) / (k * k);
            for (int c = 0; c < 3; ++c) {
                double val = acc[c] * f + 0.5;
                o[((size_t)Y * W + X) * 3 + c] = (uint8_t)(val < 0 ? 0 : (val > 255 ? 255 : val));
            }
        }
    }
    stbi_image_free(img);
    const int r = scrivi_ppm(out, o, W, H);
    free(o);
    if (r == 0) {                       /* percorso con le barre e le virgolette protette: JSON valido anche su Windows */
        printf("{\"sfondo\": \"");
        for (const char *c = out; *c; c++) {
            if (*c == '\\' || *c == '"') putchar('\\');
            putchar(*c);
        }
        printf("\", \"larghezza\": %d, \"altezza\": %d, \"da\": [%d, %d]}\n", W, H, iw, ih);
    }
    return r;
}

int main(int argc, char **argv) {
    if (argc >= 4 && !strcmp(argv[1], "jpeg"))
        return cmd_jpeg(argv[2], atoi(argv[3]), argc >= 6 && !strcmp(argv[4], "stabilizza") ? atoi(argv[5]) : 100);
    if (argc >= 8 && !strcmp(argv[1], "ritaglio"))
        return cmd_ritaglio(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]), atoi(argv[6]), atoi(argv[7]));
    if (argc >= 6 && !strcmp(argv[1], "sfondo"))
        return cmd_sfondo(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]), argc >= 7 ? atoi(argv[6]) : 500,
                          argc >= 8 ? atoi(argv[7]) : 100);
    if (argc < 5) {
        fprintf(stderr, "uso: fmv_str info|confronta|estrai <disco.bin> <lba> <settori> ...\n"
                        "     fmv_str sfondo <immagine> <uscita.ppm> <larghezza> <altezza> [centro_y [scuro]]\n");
        return 2;
    }
    if (!prepara_albero()) return 3;
    mdec_prepara();
    const char *cmd = argv[1], *disco = argv[2];
    const long lba = atol(argv[3]), n = atol(argv[4]);
    if (!strcmp(cmd, "info")) {
        printf("numero\tlba_primo\tlba_ultimo\tsettori\tbyte\tqscale\tversione\tgrandezza\tmezze_parole_rle\n");
        int r = scorri(disco, lba, n, g_info, NULL, 0);
        fprintf(stderr, "settori letti %ld, video %ld\n", settori_letti, settori_video);
        return r;
    }
    if (!strcmp(cmd, "confronta") && argc >= 7) {
        Confronto c = {0};
        int rn = 0;
        c.ref = stbi_load(argv[5], &c.rw, &c.rh, &rn, 3);
        c.scala = atoi(argv[6]);
        if (!c.ref || c.scala <= 0) { fprintf(stderr, "immagine non letta: %s\n", argv[5]); return 1; }
        c.migliore = 1e9;
        int r = scorri(disco, lba, n, g_confronta, &c, 1);
        long uguali = 0;
        double d = c.copia ? distanza(c.copia, c.w, c.h, &c, c.dy, &uguali) : 1e9;
        printf("{\"fotogrammi\": %ld, \"errori\": %ld, \"migliore\": %d, \"lba\": %ld, \"dy\": %d, "
               "\"differenza_media\": %.3f, \"pixel_uguali\": %ld, \"pixel\": %ld}\n",
               c.fotogrammi, c.errori, c.numero, c.lba, c.dy, d, uguali, (long)c.w * c.h);
        if (argc >= 8 && c.copia) {
            char p[1024];
            snprintf(p, sizeof p, "%s/decodificato_%06d.ppm", argv[7], c.numero);
            scrivi_ppm(p, c.copia, c.w, c.h);
            const int dw = c.rw / c.scala, dh = c.rh / c.scala;
            uint8_t *rid = (uint8_t *)malloc((size_t)dw * dh * 3);
            for (int y = 0; y < dh; ++y)
                for (int x = 0; x < dw; ++x)
                    memcpy(rid + ((size_t)y * dw + x) * 3,
                           c.ref + ((size_t)(y * c.scala + c.scala / 2) * c.rw + (x * c.scala + c.scala / 2)) * 3, 3);
            snprintf(p, sizeof p, "%s/gioco_ridotto.ppm", argv[7]);
            scrivi_ppm(p, rid, dw, dh);
            free(rid);
        }
        return r;
    }
    if (!strcmp(cmd, "indice") && argc >= 7) {
        const int sw = argc >= 9 ? atoi(argv[7]) : 32, sh = argc >= 9 ? atoi(argv[8]) : 24;
        return cmd_indice(disco, lba, n, argv[5], argv[6], sw, sh);
    }
    if (!strcmp(cmd, "pacchetto") && argc >= 9) {
        const int sw = argc >= 11 ? atoi(argv[9]) : 32, sh = argc >= 11 ? atoi(argv[10]) : 24;
        return cmd_pacchetto(disco, lba, n, argv[5], atoi(argv[6]), atoi(argv[7]), atoi(argv[8]), sw, sh);
    }
    if (!strcmp(cmd, "grezzi") && argc >= 7) {
        const int sw = argc >= 9 ? atoi(argv[7]) : 32, sh = argc >= 9 ? atoi(argv[8]) : 24;
        return cmd_grezzi(disco, lba, n, argv[5], atoi(argv[6]), sw, sh);
    }
    if (!strcmp(cmd, "rle") && argc >= 6) {
        FILE *o = fopen(argv[5], "wb");
        if (!o) return 1;
        int r = scorri(disco, lba, n, g_rle, o, 0);
        fclose(o);
        return r;
    }
    if (!strcmp(cmd, "estrai") && argc >= 6) {
        Estrai e = { argv[5], argc >= 7 ? atoi(argv[6]) : 1, 0, 0 };
        int r = scorri(disco, lba, n, g_estrai, &e, 1);
        printf("{\"scritti\": %ld, \"errori\": %ld}\n", e.scritti, e.errori);
        return r;
    }
    fprintf(stderr, "comando sconosciuto\n");
    return 2;
}
