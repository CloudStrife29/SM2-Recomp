/* fmv_jpeg.h - EnterElectro-Recomp 0.12: codificatore JPEG baseline minimo (4:2:0, tabelle standard dell'allegato K), per i
 * fotogrammi dei filmati migliorati. Scritto per EnterElectro-Recomp, senza librerie esterne.
 * Minimal baseline JPEG encoder (4:2:0, standard Annex K tables) for the enhanced movie frames.
 *
 *   int jpeg_scrivi(const char *path, const uint8_t *rgb, int w, int h, int qualita);   0 = ok
 */
#ifndef SM2_FMV_JPEG_H
#define SM2_FMV_JPEG_H

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint8_t JZ[64] = {   /* posizione naturale del k-esimo coefficiente a zig-zag */
     0,  1,  8, 16,  9,  2,  3, 10, 17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63
};
static const uint8_t JQ_Y[64] = {   /* allegato K, tabella K.1 (ordine naturale) */
    16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68,109,103, 77, 24, 35, 55, 64, 81,104,113, 92,
    49, 64, 78, 87,103,121,120,101, 72, 92, 95, 98,112,100,103, 99
};
static const uint8_t JQ_C[64] = {   /* tabella K.2 */
    17, 18, 24, 47, 99, 99, 99, 99, 18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99, 47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99
};
/* Tabelle di Huffman standard (K.3-K.6): numero di codici per lunghezza 1..16, poi i valori. */
static const uint8_t JH_DC_Y_N[16] = {0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0};
static const uint8_t JH_DC_Y_V[12] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
static const uint8_t JH_DC_C_N[16] = {0, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0};
static const uint8_t JH_DC_C_V[12] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
static const uint8_t JH_AC_Y_N[16] = {0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 0x7d};
static const uint8_t JH_AC_Y_V[162] = {
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08, 0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
    0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
    0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa
};
static const uint8_t JH_AC_C_N[16] = {0, 2, 1, 2, 4, 4, 3, 4, 7, 5, 4, 4, 0, 1, 2, 0x77};
static const uint8_t JH_AC_C_V[162] = {
    0x00, 0x01, 0x02, 0x03, 0x11, 0x04, 0x05, 0x21, 0x31, 0x06, 0x12, 0x41, 0x51, 0x07, 0x61, 0x71,
    0x13, 0x22, 0x32, 0x81, 0x08, 0x14, 0x42, 0x91, 0xa1, 0xb1, 0xc1, 0x09, 0x23, 0x33, 0x52, 0xf0,
    0x15, 0x62, 0x72, 0xd1, 0x0a, 0x16, 0x24, 0x34, 0xe1, 0x25, 0xf1, 0x17, 0x18, 0x19, 0x1a, 0x26,
    0x27, 0x28, 0x29, 0x2a, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48,
    0x49, 0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68,
    0x69, 0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7a, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
    0x88, 0x89, 0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5,
    0xa6, 0xa7, 0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6, 0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3,
    0xc4, 0xc5, 0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda,
    0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa
};

typedef struct { uint16_t cod[256]; uint8_t len[256]; } JHuff;

static void jh_costruisci(JHuff *t, const uint8_t *n, const uint8_t *v) {
    memset(t, 0, sizeof *t);
    int k = 0, codice = 0;
    for (int l = 1; l <= 16; ++l) {
        for (int i = 0; i < n[l - 1]; ++i) {
            t->cod[v[k]] = (uint16_t)codice;
            t->len[v[k]] = (uint8_t)l;
            ++k; ++codice;
        }
        codice <<= 1;
    }
}

typedef struct { FILE *f; uint32_t acc; int nbit; int errore; } JBit;

static void jb_byte(JBit *b, int v) { if (fputc(v, b->f) == EOF) b->errore = 1; }

static void jb_scrivi(JBit *b, uint32_t codice, int lun) {
    b->acc = (b->acc << lun) | (codice & ((1u << lun) - 1u));
    b->nbit += lun;
    while (b->nbit >= 8) {
        const int c = (int)((b->acc >> (b->nbit - 8)) & 0xFF);
        jb_byte(b, c);
        if (c == 0xFF) jb_byte(b, 0);
        b->nbit -= 8;
    }
}

static void jb_chiudi(JBit *b) {
    if (b->nbit > 0) jb_scrivi(b, 0x7F, 8 - b->nbit);   /* riempie con bit a 1 */
}

static void j16(FILE *f, int v) { fputc((v >> 8) & 0xFF, f); fputc(v & 0xFF, f); }

/* DCT 8x8 in virgola mobile (definizione diretta separabile, con coseni precalcolati). */
static float JC[8][8];
static int j_init_fatto = 0;
static void j_init(void) {
    if (j_init_fatto) return;
    for (int u = 0; u < 8; ++u)
        for (int x = 0; x < 8; ++x)
            JC[u][x] = (float)((u == 0 ? sqrt(0.125) : 0.5) * cos((2 * x + 1) * u * 3.14159265358979323846 / 16.0));
    j_init_fatto = 1;
}

static void j_fdct(const float *in, float *out) {
    float t[64];
    for (int y = 0; y < 8; ++y)
        for (int u = 0; u < 8; ++u) {
            float s = 0;
            for (int x = 0; x < 8; ++x) s += JC[u][x] * in[y * 8 + x];
            t[y * 8 + u] = s;
        }
    for (int u = 0; u < 8; ++u)
        for (int v = 0; v < 8; ++v) {
            float s = 0;
            for (int y = 0; y < 8; ++y) s += JC[v][y] * t[y * 8 + u];
            out[v * 8 + u] = s;
        }
}

static int j_categoria(int v) { int a = v < 0 ? -v : v, n = 0; while (a) { ++n; a >>= 1; } return n; }

static void j_blocco(JBit *b, const float *px, const float *qinv, int *dc_prec, const JHuff *hdc, const JHuff *hac) {
    float c[64];
    j_fdct(px, c);
    int z[64];
    for (int k = 0; k < 64; ++k) {
        const float v = c[JZ[k]] * qinv[JZ[k]];
        z[k] = (int)(v < 0 ? v - 0.5f : v + 0.5f);
    }
    const int diff = z[0] - *dc_prec;
    *dc_prec = z[0];
    int cat = j_categoria(diff);
    jb_scrivi(b, hdc->cod[cat], hdc->len[cat]);
    if (cat) jb_scrivi(b, (uint32_t)(diff < 0 ? diff - 1 : diff), cat);
    int zeri = 0;
    for (int k = 1; k < 64; ++k) {
        if (z[k] == 0) { ++zeri; continue; }
        while (zeri >= 16) { jb_scrivi(b, hac->cod[0xF0], hac->len[0xF0]); zeri -= 16; }
        cat = j_categoria(z[k]);
        const int sym = (zeri << 4) | cat;
        jb_scrivi(b, hac->cod[sym], hac->len[sym]);
        jb_scrivi(b, (uint32_t)(z[k] < 0 ? z[k] - 1 : z[k]), cat);
        zeri = 0;
    }
    if (zeri) jb_scrivi(b, hac->cod[0x00], hac->len[0x00]);
}

static int jpeg_scrivi(const char *path, const uint8_t *rgb, int w, int h, int qualita) {
    j_init();
    if (qualita < 1) qualita = 1;
    if (qualita > 100) qualita = 100;
    const int scala = qualita < 50 ? 5000 / qualita : 200 - qualita * 2;
    uint8_t qy[64], qc[64];
    float qyi[64], qci[64];
    for (int i = 0; i < 64; ++i) {
        int a = (JQ_Y[i] * scala + 50) / 100, b2 = (JQ_C[i] * scala + 50) / 100;
        qy[i] = (uint8_t)(a < 1 ? 1 : a > 255 ? 255 : a);
        qc[i] = (uint8_t)(b2 < 1 ? 1 : b2 > 255 ? 255 : b2);
        qyi[i] = 1.0f / qy[i];
        qci[i] = 1.0f / qc[i];
    }
    FILE *f = fopen(path, "wb");
    if (!f) return 1;
    /* SOI, APP0 JFIF */
    fputc(0xFF, f); fputc(0xD8, f);
    fputc(0xFF, f); fputc(0xE0, f); j16(f, 16);
    fwrite("JFIF\0", 1, 5, f); fputc(1, f); fputc(1, f); fputc(0, f); j16(f, 1); j16(f, 1); fputc(0, f); fputc(0, f);
    /* DQT */
    fputc(0xFF, f); fputc(0xDB, f); j16(f, 2 + 2 * 65);
    fputc(0, f); for (int k = 0; k < 64; ++k) fputc(qy[JZ[k]], f);
    fputc(1, f); for (int k = 0; k < 64; ++k) fputc(qc[JZ[k]], f);
    /* SOF0: Y 2x2, Cb e Cr 1x1 */
    fputc(0xFF, f); fputc(0xC0, f); j16(f, 17); fputc(8, f); j16(f, h); j16(f, w); fputc(3, f);
    fputc(1, f); fputc(0x22, f); fputc(0, f);
    fputc(2, f); fputc(0x11, f); fputc(1, f);
    fputc(3, f); fputc(0x11, f); fputc(1, f);
    /* DHT */
    const uint8_t *hn[4] = { JH_DC_Y_N, JH_AC_Y_N, JH_DC_C_N, JH_AC_C_N };
    const uint8_t *hv[4] = { JH_DC_Y_V, JH_AC_Y_V, JH_DC_C_V, JH_AC_C_V };
    const int classe[4] = { 0x00, 0x10, 0x01, 0x11 };
    for (int t = 0; t < 4; ++t) {
        int tot = 0;
        for (int i = 0; i < 16; ++i) tot += hn[t][i];
        fputc(0xFF, f); fputc(0xC4, f); j16(f, 2 + 1 + 16 + tot);
        fputc(classe[t], f);
        fwrite(hn[t], 1, 16, f);
        fwrite(hv[t], 1, (size_t)tot, f);
    }
    /* SOS */
    fputc(0xFF, f); fputc(0xDA, f); j16(f, 12); fputc(3, f);
    fputc(1, f); fputc(0x00, f); fputc(2, f); fputc(0x11, f); fputc(3, f); fputc(0x11, f);
    fputc(0, f); fputc(63, f); fputc(0, f);
    JHuff hdy, hay, hdc, hac;
    jh_costruisci(&hdy, JH_DC_Y_N, JH_DC_Y_V);
    jh_costruisci(&hay, JH_AC_Y_N, JH_AC_Y_V);
    jh_costruisci(&hdc, JH_DC_C_N, JH_DC_C_V);
    jh_costruisci(&hac, JH_AC_C_N, JH_AC_C_V);
    JBit b = { f, 0, 0, 0 };
    int dy = 0, dcb = 0, dcr = 0;
    for (int my = 0; my < h; my += 16)
        for (int mx = 0; mx < w; mx += 16) {
            float Y[4][64], Cb[64], Cr[64];
            float cb16[16][16], cr16[16][16];
            for (int y = 0; y < 16; ++y)
                for (int x = 0; x < 16; ++x) {
                    int sx = mx + x, sy = my + y;
                    if (sx >= w) sx = w - 1;
                    if (sy >= h) sy = h - 1;
                    const uint8_t *p = rgb + ((size_t)sy * w + sx) * 3;
                    const float r = p[0], g = p[1], bl = p[2];
                    const float yy = 0.299f * r + 0.587f * g + 0.114f * bl;
                    Y[(y >> 3) * 2 + (x >> 3)][(y & 7) * 8 + (x & 7)] = yy - 128.0f;
                    cb16[y][x] = -0.168736f * r - 0.331264f * g + 0.5f * bl;
                    cr16[y][x] = 0.5f * r - 0.418688f * g - 0.081312f * bl;
                }
            for (int y = 0; y < 8; ++y)
                for (int x = 0; x < 8; ++x) {
                    Cb[y * 8 + x] = 0.25f * (cb16[2 * y][2 * x] + cb16[2 * y][2 * x + 1] + cb16[2 * y + 1][2 * x] + cb16[2 * y + 1][2 * x + 1]);
                    Cr[y * 8 + x] = 0.25f * (cr16[2 * y][2 * x] + cr16[2 * y][2 * x + 1] + cr16[2 * y + 1][2 * x] + cr16[2 * y + 1][2 * x + 1]);
                }
            for (int k = 0; k < 4; ++k) j_blocco(&b, Y[k], qyi, &dy, &hdy, &hay);
            j_blocco(&b, Cb, qci, &dcb, &hdc, &hac);
            j_blocco(&b, Cr, qci, &dcr, &hdc, &hac);
        }
    jb_chiudi(&b);
    fputc(0xFF, f); fputc(0xD9, f);
    const int err = b.errore || ferror(f);
    if (fclose(f) != 0) return 1;
    return err ? 1 : 0;
}

#endif
