/* Minimal cuVS C API for the fake-cuVS logic test only. */
#ifndef FAKE_CUVS_C_API_H
#define FAKE_CUVS_C_API_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef enum { CUVS_ERROR, CUVS_SUCCESS } cuvsError_t;
typedef uintptr_t cuvsResources_t;
const char* cuvsGetLastErrorText(void);
void cuvsLogLastErrorText(void);
void cuvsSetLastErrorText(const char* msg);
cuvsError_t cuvsResourcesCreate(cuvsResources_t* res);
cuvsError_t cuvsResourcesDestroy(cuvsResources_t res);
cuvsError_t cuvsRMMAlloc(cuvsResources_t res, void** ptr, size_t bytes);
cuvsError_t cuvsRMMFree(cuvsResources_t res, void* ptr, size_t bytes);
#ifdef __cplusplus
}
#endif
#endif
