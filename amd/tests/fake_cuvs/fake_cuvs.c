#include <cuvs/core/c_api.h>
#include <cuvs/neighbors/cagra.h>
#include <dlpack/dlpack.h>
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef struct FakeIndex {
  int64_t n, dim;
  float* host_base;
  void* dev_dataset;
  int owns_dev;
} FakeIndex;

static FakeIndex* F(cuvsCagraIndex_t index) { return (FakeIndex*)index->addr; }

static __thread char g_err[256];
const char* cuvsGetLastErrorText(void) { return g_err[0] ? g_err : NULL; }
void cuvsLogLastErrorText(void) { if (g_err[0]) fprintf(stderr, "%s\n", g_err); }
void cuvsSetLastErrorText(const char* msg) { snprintf(g_err, sizeof(g_err), "%s", msg ? msg : ""); }

cuvsError_t cuvsResourcesCreate(cuvsResources_t* res) { *res = (uintptr_t)1; return CUVS_SUCCESS; }
cuvsError_t cuvsResourcesDestroy(cuvsResources_t res) { (void)res; return CUVS_SUCCESS; }

cuvsError_t cuvsRMMAlloc(cuvsResources_t res, void** ptr, size_t bytes) {
  (void)res;
  if (cudaMalloc(ptr, bytes) != cudaSuccess) { snprintf(g_err, sizeof(g_err), "cudaMalloc: %s", cudaGetErrorString(cudaGetLastError())); return CUVS_ERROR; }
  return CUVS_SUCCESS;
}
cuvsError_t cuvsRMMFree(cuvsResources_t res, void* ptr, size_t bytes) {
  (void)res; (void)bytes;
  cudaFree(ptr);
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraIndexParamsCreate(cuvsCagraIndexParams_t* params) {
  *params = (cuvsCagraIndexParams_t)calloc(1, sizeof(**params));
  if (!*params) return CUVS_ERROR;
  (*params)->metric = L2Expanded;
  (*params)->graph_degree = 64;
  (*params)->intermediate_graph_degree = 128;
  (*params)->build_algo = NN_DESCENT;
  (*params)->nn_descent_niter = 50;
  return CUVS_SUCCESS;
}
cuvsError_t cuvsCagraIndexParamsDestroy(cuvsCagraIndexParams_t params) { free(params); return CUVS_SUCCESS; }

cuvsError_t cuvsCagraIndexCreate(cuvsCagraIndex_t* index) {
  *index = (cuvsCagraIndex_t)calloc(1, sizeof(**index));
  if (!*index) return CUVS_ERROR;
  (*index)->addr = (uintptr_t)calloc(1, sizeof(FakeIndex));
  if ((*index)->addr == 0) { free(*index); *index = NULL; return CUVS_ERROR; }
  return CUVS_SUCCESS;
}
cuvsError_t cuvsCagraIndexDestroy(cuvsCagraIndex_t index) {
  if (index) {
    FakeIndex* f = F(index);
    if (f) {
      if (f->owns_dev && f->dev_dataset) { cudaFree(f->dev_dataset); }
      free(f->host_base); free(f);
    }
    free(index);
  }
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraBuild(cuvsResources_t res, cuvsCagraIndexParams_t params,
                           DLManagedTensor* dataset, cuvsCagraIndex_t index) {
  (void)res;
  if (!params || !dataset || !index) return CUVS_ERROR;
  int64_t n = dataset->dl_tensor.shape[0];
  int64_t dim = dataset->dl_tensor.shape[1];
  size_t bytes = (size_t)n * (size_t)dim * sizeof(float);
  float* host = (float*)malloc(bytes);
  if (!host) return CUVS_ERROR;
  if (dataset->dl_tensor.device.device_type == kDLCUDA) {
    if (cudaMemcpy(host, dataset->dl_tensor.data, bytes, cudaMemcpyDeviceToHost) != cudaSuccess) {
      free(host); snprintf(g_err, sizeof(g_err), "build D2H failed"); return CUVS_ERROR;
    }
  } else {
    memcpy(host, dataset->dl_tensor.data, bytes);
  }
  {
    FakeIndex* f = F(index);
    f->n = n; f->dim = dim; f->host_base = host;
    if (getenv("FAKE_COPY_DATASET") != NULL) {
      void* copy = NULL;
      if (cudaMalloc(&copy, bytes) != cudaSuccess) { free(host); return CUVS_ERROR; }
      if (cudaMemcpy(copy, dataset->dl_tensor.data, bytes, cudaMemcpyDeviceToDevice) != cudaSuccess) {
        cudaFree(copy); free(host); return CUVS_ERROR;
      }
      f->dev_dataset = copy; f->owns_dev = 1;
    } else {
      f->dev_dataset = dataset->dl_tensor.data;
    }
  }
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraIndexGetSize(cuvsCagraIndex_t index, int64_t* size) {
  if (!index || !size) return CUVS_ERROR;
  *size = F(index)->n; return CUVS_SUCCESS;
}
cuvsError_t cuvsCagraIndexGetDims(cuvsCagraIndex_t index, int64_t* dim) {
  if (!index || !dim) return CUVS_ERROR;
  *dim = F(index)->dim; return CUVS_SUCCESS;
}

static void fake_del(DLManagedTensor* self) { free(self->manager_ctx); }

cuvsError_t cuvsCagraIndexGetDataset(cuvsCagraIndex_t index, DLManagedTensor* dataset) {
  if (!index || !dataset) return CUVS_ERROR;
  if (getenv("FAKE_GETDATASET_FAIL") != NULL) {
    snprintf(g_err, sizeof(g_err), "fake GetDataset failure");
    return CUVS_ERROR;
  }
  FakeIndex* f = F(index);
  int64_t* shape = (int64_t*)malloc(2 * sizeof(int64_t));
  if (!shape) return CUVS_ERROR;
  shape[0] = f->n; shape[1] = f->dim;
  memset(dataset, 0, sizeof(*dataset));
  dataset->dl_tensor.data = f->dev_dataset ? f->dev_dataset : f->host_base;
  dataset->dl_tensor.device.device_type = f->dev_dataset ? kDLCUDA : kDLCPU;
  dataset->dl_tensor.device.device_id = 0;
  dataset->dl_tensor.ndim = 2;
  dataset->dl_tensor.dtype.code = kDLFloat;
  dataset->dl_tensor.dtype.bits = 32;
  dataset->dl_tensor.dtype.lanes = 1;
  dataset->dl_tensor.shape = shape;
  dataset->dl_tensor.strides = NULL;
  dataset->manager_ctx = shape;
  dataset->deleter = fake_del;
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraSearchParamsCreate(cuvsCagraSearchParams_t* params) {
  *params = (cuvsCagraSearchParams_t)calloc(1, sizeof(**params));
  if (!*params) return CUVS_ERROR;
  (*params)->itopk_size = 64;
  (*params)->search_width = 1;
  return CUVS_SUCCESS;
}
cuvsError_t cuvsCagraSearchParamsDestroy(cuvsCagraSearchParams_t params) { free(params); return CUVS_SUCCESS; }

static void topk_l2(const float* base, int64_t n, int64_t dim, const float* q,
                    int64_t k, uint32_t* ids, float* dist) {
  for (int64_t j = 0; j < k; ++j) { ids[j] = 0xffffffffu; dist[j] = 3.4e38f; }
  for (int64_t i = 0; i < n; ++i) {
    float d = 0.0f;
    for (int64_t t = 0; t < dim; ++t) {
      float x = q[t] - base[i * dim + t];
      d += x * x;
    }
    if (d < dist[k - 1]) {
      int64_t pos = k - 1;
      while (pos > 0 && d < dist[pos - 1]) {
        dist[pos] = dist[pos - 1];
        ids[pos] = ids[pos - 1];
        --pos;
      }
      dist[pos] = d;
      ids[pos] = (uint32_t)i;
    }
  }
}

cuvsError_t cuvsCagraSearch(cuvsResources_t res, cuvsCagraSearchParams_t params,
                            cuvsCagraIndex_t index, DLManagedTensor* queries,
                            DLManagedTensor* neighbors, DLManagedTensor* distances,
                            cuvsFilter filter) {
  (void)res; (void)params; (void)filter;
  if (!index || !queries || !neighbors || !distances) return CUVS_ERROR;
  FakeIndex* f = F(index);
  int64_t nq = queries->dl_tensor.shape[0];
  int64_t k = neighbors->dl_tensor.shape[1];
  size_t qbytes = (size_t)nq * (size_t)f->dim * sizeof(float);
  size_t obytes = (size_t)nq * (size_t)k * sizeof(uint32_t);
  float* qhost = (float*)malloc(qbytes);
  uint32_t* idhost = (uint32_t*)malloc(obytes);
  float* dhost = (float*)malloc((size_t)nq * (size_t)k * sizeof(float));
  if (!qhost || !idhost || !dhost) { free(qhost); free(idhost); free(dhost); return CUVS_ERROR; }
  if (cudaMemcpy(qhost, queries->dl_tensor.data, qbytes, cudaMemcpyDeviceToHost) != cudaSuccess) {
    snprintf(g_err, sizeof(g_err), "search query D2H failed");
    free(qhost); free(idhost); free(dhost); return CUVS_ERROR;
  }
  for (int64_t i = 0; i < nq; ++i) {
    topk_l2(f->host_base, f->n, f->dim, qhost + i * f->dim, k,
            idhost + i * k, dhost + i * k);
  }
  if (cudaMemcpy(neighbors->dl_tensor.data, idhost, obytes, cudaMemcpyHostToDevice) != cudaSuccess ||
      cudaMemcpy(distances->dl_tensor.data, dhost, (size_t)nq * (size_t)k * sizeof(float),
                 cudaMemcpyHostToDevice) != cudaSuccess) {
    snprintf(g_err, sizeof(g_err), "search result H2D failed");
    free(qhost); free(idhost); free(dhost); return CUVS_ERROR;
  }
  free(qhost); free(idhost); free(dhost);
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraSerialize(cuvsResources_t res, const char* filename,
                               cuvsCagraIndex_t index, bool include_dataset) {
  (void)res; (void)include_dataset;
  if (!filename || !index) return CUVS_ERROR;
  FILE* f = fopen(filename, "wb");
  if (!f) return CUVS_ERROR;
  uint64_t magic = 0x534b435547415356ULL; /* SKCUGASV */
  fwrite(&magic, sizeof(magic), 1, f);
  FakeIndex* fi = F(index);
  fwrite(&fi->n, sizeof(fi->n), 1, f);
  fwrite(&fi->dim, sizeof(fi->dim), 1, f);
  fwrite(fi->host_base, (size_t)fi->n * (size_t)fi->dim * sizeof(float), 1, f);
  fclose(f);
  return CUVS_SUCCESS;
}

cuvsError_t cuvsCagraDeserialize(cuvsResources_t res, const char* filename,
                                 cuvsCagraIndex_t index) {
  (void)res;
  if (!filename || !index) return CUVS_ERROR;
  FILE* f = fopen(filename, "rb");
  if (!f) return CUVS_ERROR;
  uint64_t magic = 0;
  int64_t n = 0, dim = 0;
  if (fread(&magic, sizeof(magic), 1, f) != 1 || magic != 0x534b435547415356ULL ||
      fread(&n, sizeof(n), 1, f) != 1 || fread(&dim, sizeof(dim), 1, f) != 1) {
    fclose(f); return CUVS_ERROR;
  }
  size_t bytes = (size_t)n * (size_t)dim * sizeof(float);
  float* host = (float*)malloc(bytes);
  if (!host) { fclose(f); return CUVS_ERROR; }
  if (fread(host, bytes, 1, f) != 1) { free(host); fclose(f); return CUVS_ERROR; }
  fclose(f);
  {
    FakeIndex* f = F(index);
    f->n = n; f->dim = dim; f->host_base = host; f->dev_dataset = NULL;
  }
  return CUVS_SUCCESS;
}
