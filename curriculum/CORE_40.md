# 大模型算法岗核心 40 项手撕

## 数据结构与算法（12）

1. LRU Cache；
2. LFU Cache；
3. Heap Top-K / 多路归并；
4. QuickSelect；
5. 滑动窗口 / 单调队列；
6. 二分边界；
7. 链表反转 / 环 / 合并；
8. 树遍历 / LCA / 序列化；
9. BFS / Dijkstra / 路径恢复；
10. 拓扑排序 / 环检测；
11. Union-Find；
12. Trie + 一类 DP。

## 深度学习组件（12）

13. Stable Softmax；
14. Cross Entropy + ignore_index；
15. Label Smoothing / Focal Loss；
16. Linear / MLP / SiLU / GELU；
17. LayerNorm / RMSNorm；
18. Causal MHA；
19. GQA / MQA；
20. RoPE；
21. KV Cache；
22. LoRA；
23. Top-k / Top-p / Temperature Sampling；
24. VLM Patchify / Projector / Multimodal Collator。

## 优化器、Loss 与 RL（8）

25. SGD / Momentum；
26. Adam / AdamW；
27. Warmup + Cosine Scheduler；
28. KL / JS / InfoNCE；
29. DPO Loss；
30. PPO clipped objective / value / entropy；
31. GAE；
32. GRPO group advantage 与核心 loss。

## 训练循环与 Agent（8）

33. SFT loop；
34. accumulation + AMP + clipping；
35. checkpoint/resume + RNG；
36. 最小 DDP；
37. Reward Model loop；
38. Tool-calling Agent loop；
39. Trajectory collector/replay；
40. rollout → reward → advantage → update。

## 掌握标准

每项必须：

- 解释；
- 写公式；
- 闭卷实现；
- 有测试；
- 处理边界；
- 说明复杂度或数值稳定；
- 完成 D+7 变式；
- 能与真实项目或框架源码关联。
