# 候选版公共内容快照

源码版本：`0.4.0a4`。由 `scripts/report_public_coverage.py` 生成，不是第二份题库元数据。

Catalog 254 个节点；状态 {'ready': 96, 'planned': 158}；验证级别 {'oracle': 84, 'planned': 158, 'contract': 12}。
可推荐 84；此环境具备依赖的已验证代码题 84；D+2/D+7 均验证的节点 24。
知识卡 255，来源 258。

可运行资格不等于本轮逐题执行通过，也不等于解锁或 Mastery。未完成前置仍不可从 Practice 启动；面试候选继续使用自己的确定性规则。打包是否含 PyTorch/NumPy 需用包内环境重新检查，不能照抄开发环境数量。

| Track（交叉归属不相加） | 全部 | planned | 已验证可推荐 | 本环境代码可运行 | D+2/D+7 齐全 |
|---|---:|---:|---:|---:|---:|
| ai_foundation | 94 | 37 | 56 | 56 | 21 |
| llm_algorithm | 126 | 43 | 74 | 74 | 24 |
| vlm_algorithm | 82 | 28 | 47 | 47 | 23 |
| post_training | 65 | 21 | 33 | 33 | 16 |
| agent | 30 | 20 | 4 | 4 | 2 |
| systems | 78 | 48 | 27 | 27 | 14 |
| traditional_ml | 19 | 3 | 16 | 16 | 0 |
| recommendation | 11 | 6 | 5 | 5 | 0 |
| computer_vision | 14 | 9 | 5 | 5 | 0 |
| gnn | 5 | 5 | 0 | 0 | 0 |
| generative_models | 5 | 5 | 0 | 0 | 0 |
| traditional_rl | 8 | 6 | 2 | 2 | 0 |

## 候选闭环缺口

当前主要缺口是部分已验证训练题尚无 D+2/D+7 资产，而不是继续堆叠同主题主问题。新变式须经 Oracle/property 验证及准入检查后再登记；待审资产不得算进上表。

## Windows 候选包内核对

`f0b173c` 实际便携包使用包内 Python runtime 执行同一公共覆盖脚本，未设置 PYTHONPATH，PATH 仅保留 Windows 系统目录，没有读取 Profile：254 节点、96 ready、84 Oracle、12 contract、158 planned、255 知识卡及 258 来源与源码一致。641 个随包公共文件 SHA 与该源码逐项相符。

该包未内置 PyTorch，实际具备环境条件的已验证代码题是 **27 道，而不是开发机的 84 道**。按交叉 Track 分别为 ai_foundation 21、llm_algorithm 22、vlm_algorithm 8、post_training 3、agent 2、systems 2、traditional_ml 13、recommendation 3、computer_vision 1、traditional_rl 1；其余两个 planned-only Track 为 0。不能相加，也不等于这些题对每个新档案已解锁。

全部题面与公共测试资产仍随包提供；依赖不满足的题显示具体原因，不能宣称执行成功。NNL-018 的 D+2/D+7 AUTHOR 候选通过本轮原创 property/CPU 验证，但仍待独立准入审查，不计入 24 道 retention-ready。
