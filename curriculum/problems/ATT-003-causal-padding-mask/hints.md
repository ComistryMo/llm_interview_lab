# 分级提示

## H1
H1：先确认接口约定：True 是可见；读取官方 attention 文档时留意其他 API 的反向约定。

## H2
把时间上的可见性和两侧 padding 分开；单 token 解码时，query 的绝对位置可能很大。

## H3
先形成 Q×K 的位置关系，再与 batch 的 query/key 有效性相交；head 轴只需增加一个可广播维度。
