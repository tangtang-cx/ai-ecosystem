# 性能设计与验证说明（hipVS CAGRA）

本文记录 `amd/solution/seekdb_cuvs_bridge.c` 相对官方冻结基线的改动、预期收益、
风险与在 AMD 机器上的复跑方法。**当前未在 AMD GPU 上实测**：本机是
NVIDIA GB10（ARM64 + CUDA 13），没有 `/dev/kfd`、ROCm 和 hipVS，无法运行
官方评测。代码已用 hipVS 26.03 头文件做 `gcc -fsyntax-only` 检查；另用
**fake cuVS（CPU 暴力检索）+ 真实 CUDA runtime** 在 GB10 上跑通了构建、批量/
单行/并发查询、快照和边界用例（见 `amd/tests/fake_cuvs/`）。这只能证明
bridge 自身的线程/内存/所有权逻辑，不能替代 AMD 上的真 cuVS 性能与 recall。

## 1. 基线与优化对照

官方基线（commit `634888d9…`）的 `tools/hipvs_bridge/seekdb_cuvs_bridge.c`：

| 项目 | 基线 |
| --- | --- |
| 建图算法 | `NN_DESCENT` |
| `graph_degree` | 128 |
| `intermediate_graph_degree` | 256 |
| `nn_descent_niter` | 100 |
| 数据集传入 | `kDLCPU` 主机张量，由 cuVS 内部再拷贝到显存 |
| 查询设备缓冲 | 每次调用 `cuvsRMMAlloc/Free` ×3 |
| 查询参数 | 每次调用 `cuvsCagraSearchParamsCreate/Destroy` |
| 查询线程 | seekdb adaptor 每次查询新建 32MB 栈 pthread |
| 查询结果回传 | pageable `cudaMemcpy` |

优化版默认值：

| 项目 | 优化版 |
| --- | --- |
| 建图算法 | `NN_DESCENT`（可用 `SEEKDB_CUVS_BUILD_ALGO` 切换） |
| `graph_degree` | 96（可覆盖） |
| `intermediate_graph_degree` | 144（可覆盖） |
| `nn_descent_niter` | 40（可覆盖） |
| 数据集传入 | `cuvsRMMAlloc` 设备缓冲 + `kDLCUDA` DLPack 张量；若 index 复用该缓冲则保持存活，否则建图后立即释放 |
| 查询设备缓冲 | 每 handle 分配一次，按 `nq`/`topk` 增长复用 |
| 查询参数 | 按 `topk` 缓存复用 |
| 查询线程 | bridge 内部常驻 32MB 栈 worker（同时提供临时大栈线程兜底），adaptor 可去掉每查询 pthread |
| 查询结果回传 | 复用 `cudaMallocHost` pinned 缓冲，再 `memcpy` 给调用方 |

## 2. 构建路径

### 2.1 参数收益模型

NN-Descent 阶段的计算量近似正比于 `niter × graph_degree`：

```text
baseline:  100 × 128 = 12800
optimized:  40 ×  96 =  3840
ratio:      12800 / 3840 = 3.33x
```

中间图从 256 降到 144（约 1.78x），但它在总构建时间中占比低于 NN-Descent 主循环。
因此**理论上主阶段有 3.3x 左右的空间**，正好覆盖 3.0x 的满分线；实际还会受
CAGRA 内部固定开销、数据传输、GPU 利用率影响，预计整体 2.8x–3.5x。

> 这是模型估算，不是实测。必须以 AMD 机器上的 `build_seconds` 为准。

### 2.2 设备张量建图

基线把主机指针包成 `kDLCPU` 张量，`cuvsCagraBuild` 内部必须分配显存并做 H2D。
优化版先 `cuvsRMMAlloc` 一块设备缓冲，直接以 `kDLCUDA` 张量建图：

- 若 CAGRA 复用输入缓冲（`cuvsCagraIndexGetDataset` 返回的指针落在我们的
  `[dev, dev+bytes)` 区间），handle 持有这块显存直到 `seekdb_cuvs_free`；
- 若 CAGRA 内部另拷贝一份，则建图后立即 `cuvsRMMFree`，不增加常驻显存；
- 建图前尝试 `cudaHostRegister` 输入（成功则 pinned H2D，失败则普通 pageable
  H2D），建图后立即 `cudaHostUnregister`。

这避免了一次可能重复的 H2D 拷贝，并且对 250K×256（约 256MB）数据更明显。
显存峰值最多增加一份临时数据集，建图结束后释放；对 45GB 卡可忽略。

### 2.3 构建线程

cuVS 的 CAGRA build 在部分环境会占用较大栈。基线由 seekdb adaptor 用 32MB
pthread 包住；优化版在 `seekdb_cuvs_build` 内部也创建临时 32MB 栈线程，因此
即使调用方忘记包大栈线程也不会栈溢出。

## 3. 查询路径

基线每次查询的固定开销大致包括：

1. 3 次 `cuvsRMMAlloc` + 3 次 `cuvsRMMFree`；
2. `cuvsCagraSearchParamsCreate/Destroy`；
3. seekdb adaptor 的 `pthread_create/pthread_join`（32MB 栈）；
4. 查询/结果的 pageable 拷贝。

优化版把这些全部移出热路径：

- 设备查询缓冲、pinned 结果缓冲、search params 都按 handle 缓存；
- 常驻 worker 线程（32MB 栈）通过 condvar 接活，单次同步开销约几微秒；
- 结果先到 pinned 缓冲，再 `memcpy` 给调用方；
- `cudaDeviceSynchronize` 保证 CAGRA 内部 stream 完成后才 D2H（基线依赖
  `cudaMemcpy` 的隐式同步；这里显式化，避免 stream 语义差异）。

配套的 `amd/patches/0001-ob-vsag-adaptor-direct-search.patch` 去掉
`ob_cuvs_try_search` 里每查询一次的 pthread，改为直接调用。bridge 的 worker
负责大栈，所以不会回归栈溢出。该 patch 是**可选**的：不打也能工作，只是少了
pthread create/join 的收益。

### 查询收益估算

250K×128、top-10 时，CAGRA search 本体大约几十到一百多微秒；基线每查询的
分配/参数/线程开销约占 30–70µs。去掉后单查询延迟有望下降 20%–40%，即
1.25x–1.6x QPS。是否达到 1.5x 取决于卡型、topk、并发方式和 SQL 层开销。

## 4. Recall 风险

降低 `graph_degree` / `niter` 会损失少量 recall。硬门槛是“与同轮基线差
≤0.005”：

- SIFT250K（128d）基线 recall 1.000，优化后必须 ≥0.995；
- 隐藏 250K×256 基线 0.985/0.914，优化后必须 ≥0.980/0.909。

默认 `96/144/40` 是保守起点。建议在 AMD 机器上按以下顺序扫描（每次只改一档）：

| 档位 | degree | intermediate | niter | 预期构建 | 风险 |
| --- | --- | --- | --- | --- | --- |
| 安全 | 112 | 168 | 48 | ~2.4x | recall 最稳 |
| 默认 | 96 | 144 | 40 | ~3.0x | 推荐先测 |
| 激进 | 80 | 120 | 32 | ~4.0x | recall 可能贴近红线 |
| 极激进 | 64 | 96 | 24 | ~5.3x | 仅在前两档 recall 余量很大时用 |

查询侧 `search_width` 默认 4；如果 recall 有余量且需要吞吐，可试 2（`itopk_size`
仍保持 ≥512），但这是第二优先级。

## 5. 环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `SEEKDB_CUVS_GRAPH_DEGREE` | 96 | CAGRA 输出图度数 |
| `SEEKDB_CUVS_INTERMEDIATE_GRAPH_DEGREE` | 144 | 中间图度数，必须 ≥ degree |
| `SEEKDB_CUVS_NITER` | 40 | NN-Descent 迭代次数 |
| `SEEKDB_CUVS_SEARCH_WIDTH` | 4 | CAGRA 搜索宽度 |
| `SEEKDB_CUVS_MAX_QUERIES` | 0 | 0 = 自动 batch |
| `SEEKDB_CUVS_BUILD_ALGO` | `nn_descent` | `nn_descent` / `auto` / `iterative` |
| `SEEKDB_CUVS_PIN_BUILD_INPUT` | 1 | 建图前尝试 `cudaHostRegister` |
| `SEEKDB_CUVS_VERBOSE` | 0 | 打印实际使用的构建参数 |

建图参数在 `seekdb_cuvs_build` 时读取；改 env 后必须重新 load bridge 或重启
observer。查询参数在首次 search 时读取并缓存。

## 6. AMD 机器复跑步骤

```bash
# 1) 准备冻结基线
git clone https://github.com/zihaomu/seekdb.git
cd seekdb
git checkout amd-oceanbase-official-contest-base-v5
# 确认 HEAD 是 634888d9b037153fa143d2c913ba4b25503e1d62 的后代

# 2) 应用优化（源码 + 可选 adaptor patch + 编译 bridge）
bash /path/to/ai-ecosystem/amd/scripts/apply_to_seekdb.sh \
  --seekdb "$PWD" --with-adaptor-patch

# 3) 按官方文档编译 observer（OB_BUILD_CUVS=ON + bridge 路径）

# 4) 先跑官方冒烟（必须包含 recall 用例）
bash docs/gpu-vector-index-hipvs-cuvs/validation/run_gpu_smoke.sh ...

# 5) 直接基准 bridge（不依赖 observer，便于参数扫描）
python3 /path/to/ai-ecosystem/amd/bench/bench_bridge.py \
  --bridge "$PWD/tools/hipvs_bridge/libseekdb_cuvs_bridge.so" \
  --n 250000 --dim 128 --nq 4096 --topk 10 --single-row \
  --json /tmp/sift250k_default.json --label default
```

基线对照时把参数显式设回 128/256/100：

```bash
python3 bench_bridge.py --bridge ./libseekdb_cuvs_bridge.so \
  --graph-degree 128 --intermediate-degree 256 --niter 100 \
  --json /tmp/sift250k_baseline.json --label baseline
```

注意：`bench_bridge.py` 的 `--build-script` 会在构建前设置 env；不传时请确保
bridge 已按目标参数构建。

## 7. 必须记录的证据

1. `build_seconds`：同一数据、同一轮次、基线与优化各 3 次，取中位数；
2. recall@10 / recall@100：必须用官方 ground truth；
3. 批查询 QPS 与单行查询 QPS：注明 nq、topk、并发连接数；
4. 显存峰值：`rocm-smi --showmeminfo vram` 或评测脚本自带的采样；
5. 构建参数日志：`SEEKDB_CUVS_VERBOSE=1` 的输出；
6. 若 recall 掉线，回退到安全档并重新测，不要带病提交。

## 8. 回滚

- 全部回退：`apply_to_seekdb.sh --seekdb "$PWD" --restore`；
- 仅回退参数：设置 `SEEKDB_CUVS_GRAPH_DEGREE=128`、
  `SEEKDB_CUVS_INTERMEDIATE_GRAPH_DEGREE=256`、`SEEKDB_CUVS_NITER=100` 后重启；
- 仅回退 adaptor patch：`git apply -R amd/patches/0001-ob-vsag-adaptor-direct-search.patch`
  （或 `--restore`）。

## 9. 本地逻辑自测记录

```bash
bash amd/tests/fake_cuvs/run_fake_test.sh
```

- 环境：NVIDIA GB10、CUDA 13、gcc；fake cuVS 用 CPU 暴力 L2 检索；
- 覆盖：`n=3000, dim=24, nq=32, topk=10`，单查询/批量/4 线程并发/序列化/
  反序列化/one-shot/`topk>n` 保护；
- 三种所有权分支：索引复用输入设备缓冲、索引内部复制数据集、
  `GetDataset` 失败时保守持有；
- 结果：三组均 ALL PASS；
- 同一 fake bridge 上跑通了 `bench_bridge.py`（n=1000, dim=16, nq=32, topk=10）：
  JSON 输出、单行/批量 QPS、recall=1.0 均正常；
- 未覆盖：真 hipVS CAGRA 建图/搜索数值、AMD 性能、recall、显存峰值。

## 10. 兼容性

- 导出的 6 个 C 符号和 `seekdb_cuvs_bridge.h` 与基线完全一致，observer 无需改
  链接参数；
- 快照格式仍用 `cuvsCagraSerialize(..., include_dataset=true)`，旧快照可直接
  `seekdb_cuvs_deserialize`；
- `cuvsResources_t` 在本版 hipVS 是 `uintptr_t` 句柄，代码按 `!= 0` 判断有效性；
- 若 HIP 版本的 `cudaMemcpyDefault` / `cudaHostRegister` 行为有差异，可用
  `SEEKDB_CUVS_PIN_BUILD_INPUT=0` 关闭 pin 路径。
