#include "kneekura_scene_witness_policy.h"

int kneekura_scene_witness_should_emit(uint32_t previous, uint32_t current) {
    /* Source-pinned scene IDs: 4=error, 97=download, 101/102=launch,
     * 104=other load transition. Never log cat levels, account, UI or SAVE.
     */
    if (previous == current) {
        return 0;
    }
    switch (current) {
        case 4u:
        case 97u:
        case 101u:
        case 102u:
        case 104u:
            return 1;
        default:
            return 0;
    }
}
