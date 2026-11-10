/* psx_idle_state.h — the idle-loop skip detector's state (psx_cycles.c), in one
 * struct so the interrupt-check fast path (interrupts.c) can perform the
 * detector's trivial "new resume PC" step inline (SM2-Recomp, 2026-11-01).
 *
 * The detector itself is unchanged: psx_idle_note_check() in psx_cycles.c is
 * the only code that trains, snapshots or skips. The fast path only takes the
 * one step that psx_idle_note_check takes when the resume PC differs from the
 * remembered one and no extension anchor is listed: forget the old PC, reset
 * the evidence and re-stamp the counters (see psx_idle_note_fast_step). */
#ifndef PSX_IDLE_STATE_H
#define PSX_IDLE_STATE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

enum { PSX_IDLE_SITES_MAX = 16 };

typedef struct PsxIdleState {
    uint32_t pc;                 /* resume PC the evidence is about (0 = none) */
    uint32_t quantum;
    uint32_t streak;
    int      have_snap;          /* GPR snapshot valid for pc */
    uint32_t gpr[32];
    uint32_t hi, lo;
    int      progress_reg;       /* -2 unknown, -1 stable, 1..31 countdown */
    int32_t  progress_delta;
    uint64_t last_cycle;
    uint64_t last_stores;
    uint64_t last_mmio;
    uint32_t edges;              /* non-anchor edges since the anchor */
    uint32_t iter_edges;         /* edges in the last whole iteration */
    uint32_t store_addr;
    uint32_t store_val;
    int      mem_progress;
    uint32_t sites[PSX_IDLE_SITES_MAX];
    int      site_count;
    int      audited_only;
    /* Store-tracking gate shared with memory.c (psx_idle_skip_set_store_tracker)
     * and the value idle_skip_ext_on() writes to it on every full pass. */
    int     *track;
    int      track_value;
    /* 1 once a full psx_idle_note_check pass has run with the environment
     * latched (PSX_IDLE_SKIP_EXT read, *track set): only then may the inline
     * trivial step stand in for a full pass. */
    int      fast_ready;
} PsxIdleState;

extern PsxIdleState g_psx_idle;
/* psx_cycles.c: overlay loader suppression of idle-note observations. */
extern int g_idle_note_suppress;

/* 1 if pc is one of the audited store-counter anchor sites. */
static inline int psx_idle_site_listed(uint32_t pc) {
    for (int i = 0; i < g_psx_idle.site_count; i++)
        if (g_psx_idle.sites[i] == pc) return 1;
    return 0;
}

#ifdef __cplusplus
}
#endif

#endif /* PSX_IDLE_STATE_H */
