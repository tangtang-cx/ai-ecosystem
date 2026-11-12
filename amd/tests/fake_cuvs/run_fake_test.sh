#!/usr/bin/env bash
# Logic test for the bridge without AMD/hipVS: a CPU "fake cuVS" implements the
# small C API subset with brute-force search, while the real CUDA runtime is
# used for cudaMalloc/cudaMemcpy/pinned memory.  This validates threading,
# buffer reuse, ownership and serialization, NOT performance.
#
# Requirements: gcc + CUDA runtime (any NVIDIA dev box).  Do not run this on the
# contest AMD machine expecting meaningful timings.
set -Eeuo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOLUTION=$(cd "$DIR/../../solution" && pwd)
CUDA_ROOT=${CUDA_ROOT:-/usr/local/cuda}
CUDA_INC=${CUDA_INC:-$CUDA_ROOT/include}
CUDA_LIB=${CUDA_LIB:-$CUDA_ROOT/lib64}
# Use the real hipVS headers when HIPVS_INCLUDE is set; otherwise the minimal
# stub headers in ./include keep this logic test self-contained.
CUVS_INC=${HIPVS_INCLUDE:-$DIR/include}
CC=${CC:-gcc}
BUILD=${BUILD:-$DIR/build}

rm -rf "$BUILD"
mkdir -p "$BUILD"

"$CC" -shared -fPIC -O2 -I"$CUVS_INC" -I"$CUDA_INC" "$DIR/fake_cuvs.c" \
  -L"$CUDA_LIB" -lcudart -o "$BUILD/libcuvs_c.so"

"$CC" -shared -fPIC -O2 -pthread -I"$SOLUTION" -I"$CUVS_INC" -I"$CUDA_INC" \
  "$SOLUTION/seekdb_cuvs_bridge.c" \
  -L"$BUILD" -lcuvs_c -L"$CUDA_LIB" -lcudart \
  -Wl,-rpath,"$BUILD:$CUDA_LIB" -o "$BUILD/libseekdb_cuvs_bridge.so"

"$CC" -O2 -I"$SOLUTION" -I"$CUVS_INC" "$DIR/test_bridge.c" \
  -L"$BUILD" -lseekdb_cuvs_bridge -L"$CUDA_LIB" -lcudart -lpthread -lm \
  -Wl,-rpath,"$BUILD:$CUDA_LIB" -o "$BUILD/test_bridge"

echo "== normal ownership =="
"$BUILD/test_bridge"
echo "== index copies the dataset =="
FAKE_COPY_DATASET=1 "$BUILD/test_bridge"
echo "== GetDataset failure (conservative ownership) =="
FAKE_GETDATASET_FAIL=1 "$BUILD/test_bridge"
