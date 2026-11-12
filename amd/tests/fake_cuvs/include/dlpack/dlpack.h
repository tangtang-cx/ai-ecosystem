/* Minimal DLPack declarations for the fake-cuVS logic test only.
 * The real contest build uses the DLPack pulled in by hipVS. */
#ifndef FAKE_DLPACK_H
#define FAKE_DLPACK_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef enum { kDLInt = 0, kDLUInt = 1, kDLFloat = 2 } DLDataTypeCode;
typedef struct { uint8_t code; uint8_t bits; uint16_t lanes; } DLDataType;
typedef enum { kDLCPU = 1, kDLCUDA = 2 } DLDeviceType;
typedef struct { int device_type; int device_id; } DLDevice;
typedef struct {
  void* data;
  DLDevice device;
  int32_t ndim;
  DLDataType dtype;
  int64_t* shape;
  int64_t* strides;
  uint64_t byte_offset;
} DLTensor;
typedef struct DLManagedTensor {
  DLTensor dl_tensor;
  void* manager_ctx;
  void (*deleter)(struct DLManagedTensor* self);
} DLManagedTensor;
#ifdef __cplusplus
}
#endif
#endif
