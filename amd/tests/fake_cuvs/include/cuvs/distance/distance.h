/* Minimal distance enum for the fake-cuVS logic test only. */
#ifndef FAKE_CUVS_DISTANCE_H
#define FAKE_CUVS_DISTANCE_H
#ifdef __cplusplus
extern "C" {
#endif
typedef enum { L2Expanded = 0, L2SqrtExpanded = 1, CosineExpanded = 2, InnerProduct = 6 } cuvsDistanceType;
#ifdef __cplusplus
}
#endif
#endif
