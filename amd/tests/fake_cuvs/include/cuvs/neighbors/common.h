/* Minimal filter types for the fake-cuVS logic test only. */
#ifndef FAKE_CUVS_COMMON_H
#define FAKE_CUVS_COMMON_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum cuvsFilterType { NO_FILTER, BITSET, BITMAP };
typedef struct {
  enum cuvsFilterType type;
  uintptr_t addr;
} cuvsFilter;
#ifdef __cplusplus
}
#endif
#endif
