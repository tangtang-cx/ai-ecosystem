# AMD 赛题：seekdb × AMD hipVS

## 状态

**未实现。** 本机没有 AMD Radeon GPU，也没有 ROCm 7.2.4 / hipVS 环境；
本题的硬门槛要求 GPU 实质参与 CAGRA 建图与查询，CPU 平替会直接判 0，不能提交。

## 官方基线（已核对）

| 项 | 值 |
| --- | --- |
| 仓库 | https://github.com/zihaomu/seekdb |
| 分支 | `amd-oceanbase-official-contest-base-v5` |
| Tag | `amd-cagra-contest-baseline-v5` |
| 冻结 commit | `634888d9b037153fa143d2c913ba4b25503e1d62` |
| 评测 GPU | AMD Radeon PRO W7900D，ROCm 7.2.4，24 核，45 GB 显存 |
| 总分 | 20（硬门槛 4 + 构建 14 + 查询 2） |

## 启动方式（有 GPU 环境时）

```bash
git clone https://github.com/<你的账号>/seekdb.git
cd seekdb
git remote add contest-base https://github.com/zihaomu/seekdb.git
git fetch contest-base amd-oceanbase-official-contest-base-v5 --tags
git switch -c amd-cagra-submit contest-base/amd-oceanbase-official-contest-base-v5

HIPVS_ROOT=/opt/hipvs ROCM_ROOT=/opt/rocm \
  tools/hipvs_bridge/build.sh <输出目录>/libseekdb_cuvs_bridge.so

cmake -S . -B build_release -G "Unix Makefiles" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DOB_ENABLE_UNITY=ON \
  -DOB_USE_LLD=ON \
  -DOB_BUILD_CUVS=ON \
  -DOB_BUILD_CUVS_TRACE=OFF \
  -DCUVS_BRIDGE_LIB=<输出目录>/libseekdb_cuvs_bridge.so
cmake --build build_release --target seekdb
```

## 为什么没有继续

- 需要 AMD Radeon GPU 与 ROCm；本机只有普通显卡，无 `rocminfo` / `hipcc`。
- 评测会做 GPU 路径抽检；用 CPU / FAISS 代替会被判 `gpu_path` 失败。
- 没有云端 AMD 算力账号，无法产生可复现的构建加速比与显存数据。

如果后续拿到 AMD 云端实例（官方报名页可申请 Credits），应优先做：
1. 跑通 V5 基线并记录 `SIFT250K` / `Hidden250K` 的构建时间与 Recall；
2. 用 profiler 确认 `CREATE VECTOR INDEX ... lib=cuvs` 真正在 GPU 上建图；
3. 再做数据布局、批量传输或显存复用优化，避免改查询语义。
