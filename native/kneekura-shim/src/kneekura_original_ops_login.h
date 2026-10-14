#ifndef KNEEKURA_ORIGINAL_OPS_LOGIN_H
#define KNEEKURA_ORIGINAL_OPS_LOGIN_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* JP15.7.1 DailyLogin grant's std::map<int,int> at context+0x333510.
 * Read only requested local event keys. No grant, clear or SAVE write.
 * Source: runtime 0x62e154 (Ghidra 0x72e154), pinned original SHA/BuildID.
 */
typedef int (*KneekuraOpsReadFn)(uintptr_t, void *, size_t);
/* One bounded in-order snapshot, rather than one remote read path per key.
 * Requested keys are strictly increasing. Missing keys have original count 0.
 * Validate the complete tree before returning any values to Java. */
static inline int kneekura_original_login_counts(uintptr_t root, uint64_t size,
        const int32_t *keys, size_t length, KneekuraOpsReadFn read_memory,
        int32_t *counts) {
    if (!keys || !counts || !read_memory || !length || length > 4096u
            || size > 4096u || ((root == 0u) != (size == 0u))) return 0;
    for (size_t i = 0; i < length; ++i) {
        if (keys[i] < 700001 || keys[i] > 704096 || (i && keys[i] <= keys[i-1])) return 0;
        counts[i] = 0;
    }
    uint8_t stack[64][40];
    size_t depth = 0u, requested = 0u;
    uint64_t visited = 0u, pushed = 0u;
    int32_t previous = 0;
    int has_previous = 0;
    while (root || depth) {
        while (root) {
            if (depth == 64u || pushed++ >= size
                    || !read_memory(root, stack[depth], 40u)) return 0;
            memcpy(&root, stack[depth], sizeof(root));
            ++depth;
        }
        uint8_t *node = stack[--depth];
        int32_t key, value;
        memcpy(&key, node + 28u, sizeof(key));
        memcpy(&value, node + 32u, sizeof(value));
        if ((has_previous && key <= previous) || ++visited > size) return 0;
        previous = key; has_previous = 1;
        while (requested < length && keys[requested] < key) ++requested;
        if (requested < length && keys[requested] == key) {
            if (value < 0 || value > 365) return 0;
            counts[requested++] = value;
        }
        memcpy(&root, node + 8u, sizeof(root));
    }
    return visited == size;
}
static inline int kneekura_original_login_count(uintptr_t root, uint64_t size,
        int32_t event_key, KneekuraOpsReadFn read_memory, int32_t *count) {
    if (count == NULL || read_memory == NULL || size > 4096u || event_key < 700000)
        return 0;
    *count = 0;
    if ((root == 0u) != (size == 0u)) return 0;
    for (uint64_t steps = 0; root != 0u; ++steps) {
        if (steps >= size || steps >= 64u) return 0;
        uint8_t node[40];
        if (!read_memory(root, node, sizeof(node))) return 0;
        int32_t key, value;
        memcpy(&key, node + 28u, sizeof(key));
        memcpy(&value, node + 32u, sizeof(value));
        if (event_key == key) {
            if (value < 0 || value > 365) return 0;
            *count = value;
            return 1;
        }
        memcpy(&root, node + (event_key < key ? 0u : 8u), sizeof(root));
    }
    return 1;
}
#endif
