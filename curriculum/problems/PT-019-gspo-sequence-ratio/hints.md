# 分级提示

## H1
H1：对照原论文 §4.1 的 sequence likelihood ratio；区分先取 log 均值再 exp 与先 exp 再均值。

## H2
裁剪单位与最终平均单位都是序列；负 advantage 的最小值选择方向尤其容易写反。

## H3
先按 mask 得到每条序列的 log 比率均值，再形成原始/裁剪 surrogate。用一长一短两条序列检查权重，并检查 old/adv 的梯度。
