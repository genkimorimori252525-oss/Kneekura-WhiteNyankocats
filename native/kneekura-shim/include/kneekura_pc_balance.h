#ifndef KNEEKURA_PC_BALANCE_H
#define KNEEKURA_PC_BALANCE_H
#include <stdint.h>
#define KNEEKURA_PC_BALANCE_COUNTERS 12u
__attribute__((visibility("default")))
void kneekura_pc_balance_dispatch(uint64_t *registers, uint32_t operation);
__attribute__((visibility("default")))
void kneekura_pc_balance_counters(uint64_t *output, uint32_t capacity);
#endif
