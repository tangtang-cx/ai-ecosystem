# AMD 赛题（seekdb × AMD hipVS）

本目录包含 AMD 赛题的执行计划、可应用的优化实现与基准脚本。

| 内容 | 位置 |
| --- | --- |
| 执行计划（角色、阶段、红线、时间线） | [`EXECUTION_PLAN.md`](EXECUTION_PLAN.md) |
| 优化版 bridge 源码 | [`solution/seekdb_cuvs_bridge.c`](solution/seekdb_cuvs_bridge.c) |
| 可选 adaptor 快路径 patch | [`patches/0001-ob-vsag-adaptor-direct-search.patch`](patches/0001-ob-vsag-adaptor-direct-search.patch) |
| 一键应用到 seekdb | [`scripts/apply_to_seekdb.sh`](scripts/apply_to_seekdb.sh) |
| Bridge 级基准（构建/QPS/recall） | [`bench/bench_bridge.py`](bench/bench_bridge.py) |
| 性能设计与验证说明 | [`docs/PERF_NOTES.md`](docs/PERF_NOTES.md) |

## 当前状态

| 项目 | 状态 |
| --- | --- |
| 优化实现 | 已完成，保持基线 6 个 C 符号 ABI |
| 语法检查 | 已通过（hipVS 26.03 头文件，`gcc -fsyntax-only`） |
| 逻辑自测 | 已通过（fake cuVS + 真实 CUDA runtime：构建/批量/并发/快照/边界） |
| AMD GPU 实测 | **未执行**：本机为 NVIDIA GB10 + CUDA 13，无 `/dev/kfd`/ROCm/hipVS |
| 官方成绩 | 待 AMD 盒子按 `docs/PERF_NOTES.md` 复跑并回填 |

> 本仓库不是官方答题仓库。官方要求是把改动落到 seekdb fork
> （基线 commit `634888d9b037153fa143d2c913ba4b25503e1d62` 的后代）。
> 本分支（`amd-cagra-solution`）提供可直接 apply 的源码/patch/脚本；
> 提交时把 `solution/` 与 `patches/` 应用到 seekdb fork 即可。

## 优化一句话

保持 observer/ABI 不变，只改 bridge：

1. CAGRA 建图参数从 `128/256/100` 降到默认 `96/144/40`（可 env 覆盖），
   主阶段理论加速约 3.3x；
2. 用 `cuvsRMMAlloc` 设备缓冲 + `kDLCUDA` 张量建图，避免 cuVS 内部重复 H2D；
3. 查询的 RMM 缓冲、pinned 结果缓冲、search params 按 handle 缓存；
4. 搜索跑在常驻 32MB 栈 worker 上，配合可选 patch 去掉每查询 pthread。

详细推导、recall 风险和参数扫描见 [`docs/PERF_NOTES.md`](docs/PERF_NOTES.md)。

## 本地逻辑自测（无需 AMD）

```bash
bash amd/tests/fake_cuvs/run_fake_test.sh
```

该脚本用一个 CPU 版 fake cuVS（暴力检索）替换 hipVS，只验证 bridge 的线程、
缓冲复用、设备内存所有权、快照和边界处理；**不验证性能，也不验证真 cuVS 的
CAGRA 行为**。当前在 NVIDIA GB10 + CUDA 13 上三组用例（正常/索引复制数据集/
GetDataset 失败）全部 PASS。

## 快速开始

```bash
# 冻结基线
git clone https://github.com/zihaomu/seekdb.git
cd seekdb
git checkout amd-oceanbase-official-contest-base-v5

# 应用优化（编译 bridge）
bash /path/to/ai-ecosystem/amd/scripts/apply_to_seekdb.sh \
  --seekdb "$PWD" --with-adaptor-patch

# 直接测 bridge（不依赖 observer）
python3 /path/to/ai-ecosystem/amd/bench/bench_bridge.py \
  --bridge "$PWD/tools/hipvs_bridge/libseekdb_cuvs_bridge.so" \
  --n 250000 --dim 128 --nq 4096 --topk 10 --single-row \
  --json /tmp/sift250k.json --label default
```

回滚：

```bash
bash amd/scripts/apply_to_seekdb.sh --seekdb /path/to/seekdb --restore
```

## 参数与红线

默认参数是“先保证 recall”的保守起点：

| 档位 | degree | intermediate | niter | 说明 |
| --- | --- | --- | --- | --- |
| 安全 | 112 | 168 | 48 | recall 最稳，构建约 2.4x |
| 默认 | 96 | 144 | 40 | 推荐先测，目标 3x |
| 激进 | 80 | 120 | 32 | 需 recall 有余量 |

硬门槛：GPU 真建图、recall 与同轮基线差 ≤0.005、QPS ≥ 基线 90%、
显存 ≤ 基线 1.25x、`lib=vsag` 仍可用。任何一项失败都会导致 0 分，因此
**先跑官方冒烟和 recall，再谈加速**。

## 环境要求

- AMD Radeon PRO W7900D（或评测同款）、ROCm 7.2.4、hipVS（`/opt/hipvs`）；
- `hipcc` 可执行，`/opt/hipvs/lib/libcuvs_c.so` 存在；
- 若要端到端测试：按 seekdb GPU 文档编译 `OB_BUILD_CUVS=ON`，
  `CUVS_BRIDGE_LIB` 指向 bridge `.so`；
- 复现基线时使用官方 `validation/run_gpu_smoke.sh` 与真实 ground truth。
