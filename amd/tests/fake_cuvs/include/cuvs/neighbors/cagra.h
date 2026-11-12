/* Minimal CAGRA C API for the fake-cuVS logic test only. */
#ifndef FAKE_CUVS_CAGRA_H
#define FAKE_CUVS_CAGRA_H
#include <cuvs/core/c_api.h>
#include <cuvs/distance/distance.h>
#include <cuvs/neighbors/common.h>
#include <cuvs/neighbors/ivf_pq.h>
#include <dlpack/dlpack.h>
#include <stdbool.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum cuvsCagraGraphBuildAlgo { AUTO_SELECT, IVF_PQ, NN_DESCENT, ITERATIVE_CAGRA_SEARCH };

typedef void* cuvsCagraCompressionParams_t;
typedef struct cuvsIvfPqParams* cuvsIvfPqParams;

typedef struct cuvsCagraIndexParams {
  cuvsDistanceType metric;
  size_t intermediate_graph_degree;
  size_t graph_degree;
  enum cuvsCagraGraphBuildAlgo build_algo;
  size_t nn_descent_niter;
  cuvsCagraCompressionParams_t compression;
  cuvsIvfPqParams_t graph_build_params;
}* cuvsCagraIndexParams_t;

typedef struct cuvsCagraSearchParams {
  size_t max_queries;
  size_t itopk_size;
  size_t max_iterations;
  int algo;
  size_t team_size;
  size_t search_width;
  size_t min_iterations;
  size_t thread_block_size;
  int hashmap_mode;
  size_t hashmap_min_bitlen;
  float hashmap_max_fill_rate;
  size_t num_random_samplings;
  uint64_t seed;
}* cuvsCagraSearchParams_t;

typedef struct {
  uintptr_t addr;
  DLDataType dtype;
} cuvsCagraIndex;
typedef cuvsCagraIndex* cuvsCagraIndex_t;

cuvsError_t cuvsCagraIndexParamsCreate(cuvsCagraIndexParams_t* params);
cuvsError_t cuvsCagraIndexParamsDestroy(cuvsCagraIndexParams_t params);
cuvsError_t cuvsCagraSearchParamsCreate(cuvsCagraSearchParams_t* params);
cuvsError_t cuvsCagraSearchParamsDestroy(cuvsCagraSearchParams_t params);
cuvsError_t cuvsCagraIndexCreate(cuvsCagraIndex_t* index);
cuvsError_t cuvsCagraIndexDestroy(cuvsCagraIndex_t index);
cuvsError_t cuvsCagraBuild(cuvsResources_t res, cuvsCagraIndexParams_t params,
                           DLManagedTensor* dataset, cuvsCagraIndex_t index);
cuvsError_t cuvsCagraSearch(cuvsResources_t res, cuvsCagraSearchParams_t params,
                            cuvsCagraIndex_t index, DLManagedTensor* queries,
                            DLManagedTensor* neighbors, DLManagedTensor* distances,
                            cuvsFilter filter);
cuvsError_t cuvsCagraIndexGetSize(cuvsCagraIndex_t index, int64_t* size);
cuvsError_t cuvsCagraIndexGetDims(cuvsCagraIndex_t index, int64_t* dim);
cuvsError_t cuvsCagraIndexGetDataset(cuvsCagraIndex_t index, DLManagedTensor* dataset);
cuvsError_t cuvsCagraSerialize(cuvsResources_t res, const char* filename,
                               cuvsCagraIndex_t index, bool include_dataset);
cuvsError_t cuvsCagraDeserialize(cuvsResources_t res, const char* filename,
                                 cuvsCagraIndex_t index);
#ifdef __cplusplus
}
#endif
#endif
