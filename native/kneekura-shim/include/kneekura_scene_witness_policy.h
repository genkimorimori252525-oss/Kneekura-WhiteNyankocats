#ifndef KNEEKURA_SCENE_WITNESS_POLICY_H
#define KNEEKURA_SCENE_WITNESS_POLICY_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Isolated JP15.7.1 research observation only. This policy does NOT hook
 * functions, modify native scenes, inspect SAVE, or access the network.
 * UINT32_MAX is the sentinel for no previous scene.
 */
int kneekura_scene_witness_should_emit(uint32_t previous, uint32_t current);

#ifdef __cplusplus
}
#endif
#endif
