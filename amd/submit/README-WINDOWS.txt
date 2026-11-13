seekdb AMD CAGRA 提交包（Windows 上传用）
==========================================

重要：不要上传整个 seekdb 工程。GitHub 网页上传不适合几百 MB、上千文件的项目；
而且提测要求 commit 必须是冻结基线 634888d... 的后代，必须基于 fork 仓库建新分支。
本包只需要把下面 6 个文件的改动应用到 wzhaihqy/seekdb 的新分支。

目标仓库: https://github.com/wzhaihqy/seekdb
目标分支: amd-cagra-submit
基线 commit: 634888d9b037153fa143d2c913ba4b25503e1d62
本地等价 commit: 483d301134769b6adc5c84f8744fb1a2f308aec4

包内文件：
  amd-cagra-submit.patch   完整 format-patch，含作者/时间/6 个文件改动（推荐）
  files/                   6 个文件的最终版本，供方案 B 网页上传
  README-WINDOWS.txt       本说明

------------------------------------------------------------
方案 A（推荐，Git for Windows / Git Bash）
------------------------------------------------------------
1. 安装 Git for Windows（已安装可跳过）。
2. 打开 Git Bash，执行：

   git clone https://github.com/wzhaihqy/seekdb.git
   cd seekdb
   git config user.name "wzhaihqy"
   git config user.email "wzhaihqy@users.noreply.github.com"
   git checkout -B amd-cagra-submit 634888d9b037153fa143d2c913ba4b25503e1d62
   git am "C:/Users/你的用户名/Downloads/amd-cagra-submit.patch"
   git log --oneline -2
   git push origin amd-cagra-submit

3. 如果 git am 报 "patch does not apply"，先确认在基线再重试：

   git reset --hard 634888d9b037153fa143d2c913ba4b25503e1d62
   git am "C:/Users/你的用户名/Downloads/amd-cagra-submit.patch"

4. push 时用 wzhaihqy 账号认证（浏览器登录，或你已加到 GitHub 的 i7k8... SSH key）。
5. 成功后把下面地址和 commit SHA 发给对方：
   https://github.com/wzhaihqy/seekdb/tree/amd-cagra-submit

------------------------------------------------------------
方案 B（完全不用 Git，GitHub 网页手动上传 6 个文件）
------------------------------------------------------------
1. 打开 https://github.com/wzhaihqy/seekdb/branches
2. New branch：名字 amd-cagra-submit，源分支选
   amd-oceanbase-official-contest-base-v5（即冻结基线）。
3. 在新分支上，按下面路径进入对应目录，点 Add file -> Upload files，
   上传 files/ 下的文件（覆盖同名文件）：

   docs/AMD_PERF_REPORT.md                                      （新增）
   src/oblib/lib/vector/ob_vsag_adaptor.cpp                     （替换）
   tools/hipvs_bridge/0001-ob-vsag-adaptor-direct-search.patch  （新增）
   tools/hipvs_bridge/bench_bridge.py                           （新增）
   tools/hipvs_bridge/build.sh                                  （替换）
   tools/hipvs_bridge/seekdb_cuvs_bridge.c                      （替换）

   每次上传会生成一个 commit，6 个文件传完即可。
4. 注意：网页上传无法保留 build.sh / bench_bridge.py 的可执行位（会变成 100644）。
   如果平台用 `bash build.sh` 调用则没问题；如果必须可执行，请用方案 A。
5. 上传完把分支链接和最新 commit SHA 发给对方。
