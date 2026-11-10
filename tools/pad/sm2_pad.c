/* sm2_pad.c - EnterElectro-Recomp 0.12: controller e tastiera per il riquadro "Comandi" del launcher.
 * EnterElectro-Recomp 0.12: gamepad and keyboard reader for the launcher's "Controls" panel.
 *
 * Usa la stessa SDL3 del gioco (la libreria statica del toolchain), quindi nomi, GUID e tasti sono quelli che legge
 * il gioco: GUID come SDL_GetJoystickGUIDForID + SDL_GUIDToString (psx_sdl.h), tasti del controller con i nomi di
 * input.ini (a, b, x, y, back, start, leftshoulder, lefttrigger, leftx, ...), tasti della tastiera con i nomi di
 * keybinds.ini (SDL_GetScancodeName, per posizione fisica).
 *
 *   sm2_pad elenco                    una riga JSON: versione di SDL e controller collegati
 *   sm2_pad ascolta [secondi]         righe JSON finche' lo stdin resta aperto (o "esci", o i secondi, di default 1800):
 *                                     {"ev":"pronto"}, {"ev":"pad",...}, {"ev":"via","id":N},
 *                                     {"ev":"tasto","id":N,"tasto":"a","giu":1}, {"ev":"asse","id":N,"asse":"leftx","v":-32768}
 *   sm2_pad tasto "<testo>" [secondi] piccola finestra "premi un tasto" (Esc annulla, di default 5 secondi):
 *                                     {"tasto":"<nome SDL>"} oppure {"annullato":true} oppure {"scaduto":true}
 * Codice di uscita 0, 1 se SDL non parte (il messaggio e' nella riga JSON "errore").
 */
#define SDL_MAIN_HANDLED
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#else
#include <poll.h>
#include <unistd.h>
#endif

static void js_str(const char *s) {
    putchar('"');
    for (; s && *s; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c < 0x20) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static void errore(const char *dove) {
    printf("{\"errore\":");
    js_str(dove);
    printf(",\"sdl\":");
    js_str(SDL_GetError());
    printf("}\n");
    fflush(stdout);
}

/* nomi di input.ini per i tasti e gli assi del controller (rt/main.cpp, parse_controller_source) */
static const char *nome_tasto(int b) {
    switch (b) {
    case SDL_GAMEPAD_BUTTON_SOUTH: return "a";
    case SDL_GAMEPAD_BUTTON_EAST: return "b";
    case SDL_GAMEPAD_BUTTON_WEST: return "x";
    case SDL_GAMEPAD_BUTTON_NORTH: return "y";
    case SDL_GAMEPAD_BUTTON_BACK: return "back";
    case SDL_GAMEPAD_BUTTON_GUIDE: return "guide";
    case SDL_GAMEPAD_BUTTON_START: return "start";
    case SDL_GAMEPAD_BUTTON_LEFT_STICK: return "leftstick";
    case SDL_GAMEPAD_BUTTON_RIGHT_STICK: return "rightstick";
    case SDL_GAMEPAD_BUTTON_LEFT_SHOULDER: return "leftshoulder";
    case SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER: return "rightshoulder";
    case SDL_GAMEPAD_BUTTON_DPAD_UP: return "dpup";
    case SDL_GAMEPAD_BUTTON_DPAD_DOWN: return "dpdown";
    case SDL_GAMEPAD_BUTTON_DPAD_LEFT: return "dpleft";
    case SDL_GAMEPAD_BUTTON_DPAD_RIGHT: return "dpright";
    default: {
        const char *s = SDL_GetGamepadStringForButton((SDL_GamepadButton)b);
        return s ? s : "";
    }
    }
}

static const char *nome_asse(int a) {
    switch (a) {
    case SDL_GAMEPAD_AXIS_LEFTX: return "leftx";
    case SDL_GAMEPAD_AXIS_LEFTY: return "lefty";
    case SDL_GAMEPAD_AXIS_RIGHTX: return "rightx";
    case SDL_GAMEPAD_AXIS_RIGHTY: return "righty";
    case SDL_GAMEPAD_AXIS_LEFT_TRIGGER: return "lefttrigger";
    case SDL_GAMEPAD_AXIS_RIGHT_TRIGGER: return "righttrigger";
    default: {
        const char *s = SDL_GetGamepadStringForAxis((SDL_GamepadAxis)a);
        return s ? s : "";
    }
    }
}

static const char *nome_etichetta(SDL_GamepadButtonLabel l) {
    switch (l) {
    case SDL_GAMEPAD_BUTTON_LABEL_A: return "A";
    case SDL_GAMEPAD_BUTTON_LABEL_B: return "B";
    case SDL_GAMEPAD_BUTTON_LABEL_X: return "X";
    case SDL_GAMEPAD_BUTTON_LABEL_Y: return "Y";
    case SDL_GAMEPAD_BUTTON_LABEL_CROSS: return "cross";
    case SDL_GAMEPAD_BUTTON_LABEL_CIRCLE: return "circle";
    case SDL_GAMEPAD_BUTTON_LABEL_SQUARE: return "square";
    case SDL_GAMEPAD_BUTTON_LABEL_TRIANGLE: return "triangle";
    default: return "";
    }
}

/* un controller in JSON (senza graffe): id, nome, tipo, guid, etichette dei quattro tasti frontali */
static void js_pad(SDL_JoystickID id) {
    char guid[64];
    SDL_GUIDToString(SDL_GetJoystickGUIDForID(id), guid, (int)sizeof guid);
    SDL_GamepadType t = SDL_GetGamepadTypeForID(id);
    const char *tipo = SDL_GetGamepadStringForType(t);
    printf("\"id\":%u,\"nome\":", (unsigned)id);
    js_str(SDL_GetGamepadNameForID(id));
    printf(",\"tipo\":");
    js_str(tipo ? tipo : "");
    printf(",\"guid\":");
    js_str(guid);
    printf(",\"etichette\":{");
    static const SDL_GamepadButton facce[4] = {SDL_GAMEPAD_BUTTON_SOUTH, SDL_GAMEPAD_BUTTON_EAST,
                                               SDL_GAMEPAD_BUTTON_WEST, SDL_GAMEPAD_BUTTON_NORTH};
    for (int i = 0; i < 4; i++) {
        printf("%s\"%s\":", i ? "," : "", nome_tasto(facce[i]));
        js_str(nome_etichetta(SDL_GetGamepadButtonLabelForType(t, facce[i])));
    }
    printf("}");
}

static void js_versione(void) {
    const int v = SDL_GetVersion();
    printf("\"sdl\":\"%d.%d.%d\"", SDL_VERSIONNUM_MAJOR(v), SDL_VERSIONNUM_MINOR(v), SDL_VERSIONNUM_MICRO(v));
}

static int avvia_sdl(SDL_InitFlags flags) {
    /* il riquadro del launcher e' una finestra tkinter, non di SDL: senza questo SDL non manda i tasti del
     * controller quando la sua finestra (che non c'e') non e' in primo piano */
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
    SDL_SetMainReady();
    if (!SDL_Init(flags)) {
        errore("SDL_Init");
        return 0;
    }
    return 1;
}

static int cmd_elenco(void) {
    if (!avvia_sdl(SDL_INIT_GAMEPAD)) return 1;
    /* i controller HIDAPI (DualShock, DualSense, Switch) arrivano dopo qualche decina di millisecondi */
    const Uint64 fine = SDL_GetTicks() + 400;
    while (SDL_GetTicks() < fine) {
        SDL_PumpEvents();
        SDL_Delay(20);
    }
    int n = 0;
    SDL_JoystickID *ids = SDL_GetGamepads(&n);
    printf("{");
    js_versione();
    printf(",\"pad\":[");
    for (int i = 0; ids && i < n; i++) {
        printf("%s{", i ? "," : "");
        js_pad(ids[i]);
        printf("}");
    }
    printf("]}\n");
    fflush(stdout);
    SDL_free(ids);
    SDL_Quit();
    return 0;
}

/* lo stdin del launcher: 1 se e' chiuso o se ha scritto "esci" */
static int stdin_finito(void) {
    static char buf[512];
    static size_t len = 0;
#ifdef _WIN32
    HANDLE h = GetStdHandle(STD_INPUT_HANDLE);
    if (h == NULL || h == INVALID_HANDLE_VALUE || GetFileType(h) != FILE_TYPE_PIPE) return 0;
    DWORD n = 0;
    if (!PeekNamedPipe(h, NULL, 0, NULL, &n, NULL)) return GetLastError() == ERROR_BROKEN_PIPE;
    if (n == 0) return 0;
    DWORD letti = 0;
    if (n > sizeof buf - 1 - len) n = (DWORD)(sizeof buf - 1 - len);
    if (n == 0) { len = 0; return 0; }
    if (!ReadFile(h, buf + len, n, &letti, NULL)) return 1;
    len += letti;
#else
    struct pollfd p = {0, POLLIN, 0};
    if (poll(&p, 1, 0) <= 0) return 0;
    if (p.revents & (POLLHUP | POLLERR)) {
        if (!(p.revents & POLLIN)) return 1;
    }
    ssize_t r = read(0, buf + len, sizeof buf - 1 - len);
    if (r <= 0) return 1;
    len += (size_t)r;
#endif
    buf[len] = 0;
    if (strstr(buf, "esci")) return 1;
    if (len > sizeof buf / 2) {          /* tiene solo la coda */
        memmove(buf, buf + len - 8, 8);
        len = 8;
    }
    return 0;
}

#define MAX_PAD 16

static int cmd_ascolta(int secondi) {
    if (!avvia_sdl(SDL_INIT_GAMEPAD)) return 1;
    SDL_Gamepad *aperti[MAX_PAD] = {0};
    int ultimo_asse[MAX_PAD][SDL_GAMEPAD_AXIS_COUNT];
    SDL_JoystickID ids[MAX_PAD] = {0};
    for (int i = 0; i < MAX_PAD; i++)
        for (int a = 0; a < SDL_GAMEPAD_AXIS_COUNT; a++) ultimo_asse[i][a] = 0;
    printf("{\"ev\":\"pronto\",");
    js_versione();
    printf("}\n");
    fflush(stdout);
    const Uint64 fine = SDL_GetTicks() + (Uint64)secondi * 1000u;
    Uint64 prossimo_controllo = 0;
    for (;;) {
        SDL_Event e;
        if (SDL_WaitEventTimeout(&e, 50)) {
            do {
                switch (e.type) {
                case SDL_EVENT_GAMEPAD_ADDED: {
                    int libero = -1;
                    for (int i = 0; i < MAX_PAD; i++) {
                        if (aperti[i] && ids[i] == e.gdevice.which) { libero = -2; break; }
                        if (!aperti[i] && libero < 0) libero = i;
                    }
                    if (libero >= 0) {
                        aperti[libero] = SDL_OpenGamepad(e.gdevice.which);
                        ids[libero] = e.gdevice.which;
                        for (int a = 0; a < SDL_GAMEPAD_AXIS_COUNT; a++) ultimo_asse[libero][a] = 0;
                        printf("{\"ev\":\"pad\",");
                        js_pad(e.gdevice.which);
                        printf(",\"aperto\":%d}\n", aperti[libero] ? 1 : 0);
                        if (!aperti[libero]) errore("SDL_OpenGamepad");
                    }
                    break;
                }
                case SDL_EVENT_GAMEPAD_REMOVED:
                    for (int i = 0; i < MAX_PAD; i++) {
                        if (aperti[i] && ids[i] == e.gdevice.which) {
                            SDL_CloseGamepad(aperti[i]);
                            aperti[i] = NULL;
                        }
                    }
                    printf("{\"ev\":\"via\",\"id\":%u}\n", (unsigned)e.gdevice.which);
                    break;
                case SDL_EVENT_GAMEPAD_BUTTON_DOWN:
                case SDL_EVENT_GAMEPAD_BUTTON_UP:
                    printf("{\"ev\":\"tasto\",\"id\":%u,\"tasto\":", (unsigned)e.gbutton.which);
                    js_str(nome_tasto(e.gbutton.button));
                    printf(",\"giu\":%d}\n", e.gbutton.down ? 1 : 0);
                    break;
                case SDL_EVENT_GAMEPAD_AXIS_MOTION: {
                    /* solo i cambi di almeno 1/32 della corsa, e sempre il ritorno a zero */
                    for (int i = 0; i < MAX_PAD; i++) {
                        if (!aperti[i] || ids[i] != e.gaxis.which || e.gaxis.axis >= SDL_GAMEPAD_AXIS_COUNT) continue;
                        const int v = e.gaxis.value, prima = ultimo_asse[i][e.gaxis.axis];
                        if (abs(v - prima) >= 1024 || (v == 0 && prima != 0)) {
                            ultimo_asse[i][e.gaxis.axis] = v;
                            printf("{\"ev\":\"asse\",\"id\":%u,\"asse\":", (unsigned)e.gaxis.which);
                            js_str(nome_asse(e.gaxis.axis));
                            printf(",\"v\":%d}\n", v);
                        }
                    }
                    break;
                }
                case SDL_EVENT_QUIT:
                    goto fine_ascolto;
                default:
                    break;
                }
            } while (SDL_PollEvent(&e));
            fflush(stdout);
        }
        const Uint64 ora = SDL_GetTicks();
        if (ora >= prossimo_controllo) {
            prossimo_controllo = ora + 200;
            if (stdin_finito()) break;
        }
        if (ora >= fine) break;
    }
fine_ascolto:
    for (int i = 0; i < MAX_PAD; i++)
        if (aperti[i]) SDL_CloseGamepad(aperti[i]);
    printf("{\"ev\":\"fine\"}\n");
    fflush(stdout);
    SDL_Quit();
    return 0;
}

static int cmd_tasto(const char *testo, int secondi) {
    if (!avvia_sdl(SDL_INIT_VIDEO)) return 1;
    SDL_Window *w = NULL;
    SDL_Renderer *r = NULL;
    const int scala = 2;
    if (!SDL_CreateWindowAndRenderer("EnterElectro-Recomp", 360 * scala, 64 * scala, SDL_WINDOW_ALWAYS_ON_TOP, &w, &r)) {
        errore("SDL_CreateWindowAndRenderer");
        SDL_Quit();
        return 1;
    }
    SDL_SetWindowPosition(w, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED);
    SDL_SetRenderScale(r, (float)scala, (float)scala);
    SDL_RaiseWindow(w);
    const Uint64 inizio = SDL_GetTicks();
    const Uint64 fine = inizio + (Uint64)secondi * 1000u;
    int esito = 0;                       /* 1 tasto, 2 annullato, 3 scaduto */
    const char *nome = "";
    while (!esito) {
        const Uint64 ora = SDL_GetTicks();
        if (ora >= fine) { esito = 3; break; }
        char riga[64];
        snprintf(riga, sizeof riga, "Esc = annulla / cancel   %d s", (int)((fine - ora + 999) / 1000));
        SDL_SetRenderDrawColor(r, 24, 28, 36, 255);
        SDL_RenderClear(r);
        SDL_SetRenderDrawColor(r, 235, 235, 235, 255);
        SDL_RenderDebugText(r, 12.0f, 12.0f, testo);
        SDL_SetRenderDrawColor(r, 160, 170, 185, 255);
        SDL_RenderDebugText(r, 12.0f, 40.0f, riga);
        SDL_RenderPresent(r);
        SDL_Event e;
        if (SDL_WaitEventTimeout(&e, 100)) {
            do {
                if (e.type == SDL_EVENT_KEY_DOWN && !e.key.repeat) {
                    if (e.key.scancode == SDL_SCANCODE_ESCAPE) { esito = 2; break; }
                    const char *n = SDL_GetScancodeName(e.key.scancode);
                    if (n && n[0]) { nome = n; esito = 1; break; }
                } else if (e.type == SDL_EVENT_QUIT || e.type == SDL_EVENT_WINDOW_CLOSE_REQUESTED) {
                    esito = 2;
                    break;
                }
            } while (SDL_PollEvent(&e));
        }
    }
    if (esito == 1) {
        printf("{\"tasto\":");
        js_str(nome);
        printf("}\n");
    } else if (esito == 2) {
        printf("{\"annullato\":true}\n");
    } else {
        printf("{\"scaduto\":true}\n");
    }
    fflush(stdout);
    SDL_DestroyRenderer(r);
    SDL_DestroyWindow(w);
    SDL_Quit();
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 2 && !strcmp(argv[1], "elenco")) return cmd_elenco();
    if (argc >= 2 && !strcmp(argv[1], "ascolta")) {
        int s = argc >= 3 ? atoi(argv[2]) : 1800;
        return cmd_ascolta(s > 0 ? s : 1800);
    }
    if (argc >= 3 && !strcmp(argv[1], "tasto")) {
        int s = argc >= 4 ? atoi(argv[3]) : 5;
        return cmd_tasto(argv[2], s > 0 ? s : 5);
    }
    fprintf(stderr, "uso: sm2_pad elenco | ascolta [secondi] | tasto \"<testo>\" [secondi]\n");
    return 2;
}
