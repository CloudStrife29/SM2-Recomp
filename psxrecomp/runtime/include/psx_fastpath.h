/* psx_fastpath.h — hot-path state mirrored as plain globals (SM2-Recomp, 2026-11-01).
 *
 * The per-block-edge interrupt check, the dispatch trampoline and the guest
 * store path used to learn "is anything special going on?" by CALLING into
 * half a dozen translation units (netplay, self-check, fntrace, parity trace,
 * card audit, text translation). None of those answers changes more than a
 * few times per session, so each is mirrored here as a plain int that the
 * owning file keeps up to date, and the hot paths test the mirror inline.
 *
 * Contract: every mirror is CONSERVATIVE. "Clear" means the full path would
 * find nothing to do; "set" only means "ask the full path", which stays the
 * source of truth. Guest-visible behaviour is identical either way — the
 * mirrors only decide whether a call that would have returned immediately is
 * made at all. */
#ifndef PSX_FASTPATH_H
#define PSX_FASTPATH_H

#include <stdint.h>
#include "psx_cycles.h"

#ifdef __cplusplus
extern "C" {
#endif

#if !defined(PSX_OVERLAY_DLL_BUILD) && !defined(__cplusplus)
/* psx_get_cycle_count()'s value, inline, for runtime hot paths (the deferred
 * charge batch and the function-local sink included). Lives here rather than
 * in psx_cycles.h: that header is part of the overlay shard compile surface
 * (codegen_hash_sources.cmake) and must not move for a runtime-only change. */
static inline uint64_t psx_cycle_count_now(void) {
    uint64_t n = psx_cycle_count + (uint64_t)g_psx_cyc_batch;
    if (g_psx_cyc_local_acc) n += (uint64_t)(*g_psx_cyc_local_acc);
    return n;
}
#endif

/* psx_netplay.c: set with g_np.active. psx_netplay_active() additionally
 * requires a live session, so this is a superset (clear => inactive). */
extern int g_psx_netplay_flag;
/* psx_selfcheck.c: the self-check phase; 0 == SC_OFF (psx_selfcheck_enabled()). */
extern int g_psx_selfcheck_phase;
/* fntrace.c: the game-start latch (fntrace_is_game_started()). */
extern int g_fntrace_game_started;
/* parity_trace.c: parity_trace_is_armed(). */
extern uint32_t g_parity_trace_armed;
/* card_data_writes.c: a card-byte destination capture is armed. */
extern int g_card_data_writes_armed;
/* text_xlate.cpp: capture or apply armed (text_xlate_on_dispatch has work). */
extern int g_text_xlate_armed;
/* mod_runtime.cpp: the main-EXE mod plan has been applied (or rejected), so
 * mod_runtime_on_dispatch has nothing left to do. */
extern int g_mod_runtime_main_done;

/* memory.c: generation of "what can change whether static game text is still
 * valid": every dirty-page mark, guarded-write mismatch, divergence flag,
 * baseline clear, reference-image change, bitmap restore and every direct
 * RAM write that bypasses the store path (dirty_ram_text_gen_bump) bumps it. Never 0. dirty_ram_text_native_ok_ranges_from
 * caches a positive verdict per entry PC under this generation. */
extern uint32_t g_psx_text_gen;

#ifdef __cplusplus
}
#endif

#endif /* PSX_FASTPATH_H */
