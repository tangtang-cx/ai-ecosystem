#include "seekdb_cuvs_bridge.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 3000
#define DIM 24
#define NQ 32
#define TOPK 10

static float base[N * DIM];
static float query[NQ * DIM];

static float lcgf(unsigned* s) {
  *s = *s * 1664525u + 1013904223u;
  return ((float)((*s >> 8) & 0xffffff) / 16777216.0f) * 2.0f - 1.0f;
}

static void ref_topk(const float* q, unsigned* ids, float* dist) {
  for (int j = 0; j < TOPK; ++j) { ids[j] = 0xffffffffu; dist[j] = 3.4e38f; }
  for (int i = 0; i < N; ++i) {
    float d = 0.0f;
    for (int t = 0; t < DIM; ++t) { float x = q[t] - base[i * DIM + t]; d += x * x; }
    if (d < dist[TOPK - 1]) {
      int p = TOPK - 1;
      while (p > 0 && d < dist[p - 1]) { dist[p] = dist[p - 1]; ids[p] = ids[p - 1]; --p; }
      dist[p] = d; ids[p] = (unsigned)i;
    }
  }
}

static int same_set(const unsigned* a, const unsigned* b) {
  for (int i = 0; i < TOPK; ++i) {
    int found = 0;
    for (int j = 0; j < TOPK; ++j) if (a[i] == b[j]) { found = 1; break; }
    if (!found) return 0;
  }
  return 1;
}

static int check_batch(void* h, int nq, const char* tag) {
  unsigned* ids = (unsigned*)malloc(sizeof(unsigned) * nq * TOPK);
  float* dist = (float*)malloc(sizeof(float) * nq * TOPK);
  int rc = seekdb_cuvs_search(h, query, nq, TOPK, ids, dist);
  if (rc) { fprintf(stderr, "FAIL %s: search rc=%d\n", tag, rc); free(ids); free(dist); return 1; }
  for (int i = 0; i < nq; ++i) {
    unsigned ref_ids[TOPK]; float ref_dist[TOPK];
    ref_topk(query + i * DIM, ref_ids, ref_dist);
    if (ids[i * TOPK] != ref_ids[0] || !same_set(ids + i * TOPK, ref_ids)) {
      fprintf(stderr, "FAIL %s query %d: got %u want %u\n", tag, i, ids[i * TOPK], ref_ids[0]);
      free(ids); free(dist); return 1;
    }
    if (fabsf(dist[i * TOPK] - ref_dist[0]) > 1e-3f) {
      fprintf(stderr, "FAIL %s query %d dist: got %f want %f\n", tag, i, dist[i * TOPK], ref_dist[0]);
      free(ids); free(dist); return 1;
    }
  }
  free(ids); free(dist);
  printf("PASS %s\n", tag);
  return 0;
}

struct thread_arg { void* h; int tid; int rc; };
static void* thread_fn(void* p) {
  struct thread_arg* a = (struct thread_arg*)p;
  unsigned* ids = (unsigned*)malloc(sizeof(unsigned) * TOPK);
  for (int r = 0; r < 50; ++r) {
    int qi = (a->tid * 7 + r) % NQ;
    if (seekdb_cuvs_search(a->h, query + qi * DIM, 1, TOPK, ids, NULL) != 0) { a->rc = 1; break; }
    unsigned ref[TOPK]; float rd[TOPK];
    ref_topk(query + qi * DIM, ref, rd);
    if (ids[0] != ref[0] || !same_set(ids, ref)) { a->rc = 2; break; }
  }
  free(ids);
  return NULL;
}

int main(void) {
  unsigned seed = 12345;
  for (int i = 0; i < N * DIM; ++i) base[i] = lcgf(&seed);
  for (int i = 0; i < NQ * DIM; ++i) query[i] = lcgf(&seed);

  setenv("SEEKDB_CUVS_VERBOSE", "1", 1);
  setenv("SEEKDB_CUVS_GRAPH_DEGREE", "96", 1);
  setenv("SEEKDB_CUVS_INTERMEDIATE_GRAPH_DEGREE", "144", 1);
  setenv("SEEKDB_CUVS_NITER", "40", 1);

  void* h = seekdb_cuvs_build(base, N, DIM);
  if (!h) { fprintf(stderr, "FAIL build\n"); return 1; }
  printf("PASS build\n");

  if (check_batch(h, 1, "single-query")) return 1;
  if (check_batch(h, NQ, "batch-query")) return 1;

  pthread_t th[4]; struct thread_arg args[4];
  for (int i = 0; i < 4; ++i) { args[i].h = h; args[i].tid = i; args[i].rc = 0; pthread_create(&th[i], NULL, thread_fn, &args[i]); }
  for (int i = 0; i < 4; ++i) { pthread_join(th[i], NULL); if (args[i].rc) { fprintf(stderr, "FAIL thread %d rc=%d\n", i, args[i].rc); return 1; } }
  printf("PASS concurrent-search\n");

  unsigned bad[TOPK];
  int rc = seekdb_cuvs_search(h, query, 1, N + 1, bad, NULL);
  if (rc != 2) { fprintf(stderr, "FAIL topk>n expected rc=2 got %d\n", rc); return 1; }
  printf("PASS topk-guard\n");

  const char* path = "/home/wzh_linux/Desktop/amd-work/fake_cuvs/index.bin";
  if (seekdb_cuvs_serialize(h, path) != 0) { fprintf(stderr, "FAIL serialize\n"); return 1; }
  seekdb_cuvs_free(h);
  h = seekdb_cuvs_deserialize(path, N, DIM);
  if (!h) { fprintf(stderr, "FAIL deserialize\n"); return 1; }
  if (check_batch(h, NQ, "deserialized")) return 1;
  seekdb_cuvs_free(h);

  void* h2 = NULL;
  unsigned ids[NQ * TOPK];
  rc = seekdb_cuvs_cagra_knn(base, N, DIM, query, NQ, TOPK, ids);
  if (rc != 0) { fprintf(stderr, "FAIL one-shot rc=%d\n", rc); return 1; }
  for (int i = 0; i < NQ; ++i) {
    unsigned ref[TOPK]; float rd[TOPK];
    ref_topk(query + i * DIM, ref, rd);
    if (ids[i * TOPK] != ref[0]) { fprintf(stderr, "FAIL one-shot q%d\n", i); return 1; }
  }
  printf("PASS one-shot\n");
  (void)h2;
  printf("ALL PASS\n");
  return 0;
}
