# shamir-secret-sharing

从零手写的 Shamir $(t,n)$ 门限秘密分享：自己实现有限域运算和扩展欧几里得求逆，**不调用任何现成密码学库**（无 secretsharing、pycryptodome 等）。

包含两个有限域上的实现：

- 素数域 $GF(p)$，$p=2^{128}+51$；
- 二元扩域 $GF(2^{128})$，不可约多项式 $x^{128}+x^7+x^2+x+1$（GCM 多项式）。

## 环境要求

- Python 3.8+；
- 仅 Part 3 / Part 5 的绘图需要 matplotlib：

```bash
pip install matplotlib
```

其余代码只使用 Python 标准库。

## 怎么跑

所有命令均在本目录（`shamir-secret-sharing/`）下执行：

```bash
# Part 2：GF(p) 四则运算、手写 extgcd 逆元、基础分享与重构演示
python part2.py

# Part 3：1000 次正确性测试 + 边界情况
#         + t-1 份额小尺度枚举（直方图/熵/卡方）+ 合数模数对比
python part3.py

# Part 4：GF(2^128) 版本
#         域公理测试、已知答案向量、Fermat 与多项式 extgcd 两版逆元交叉验证、
#         100 次随机正确性测试、边界情况
python part4.py

# Part 5：性能基准（n=10..1000，t≈n/2）
#         同规模对比 GF(p) 与 GF(2^128)，每点 best-of-5
#         生成 data/part5_performance.csv（含 field 列）和 log-log 图 data/part5_performance.png
python part5.py
```


## 文件说明

| 文件 | 内容 |
| --- | --- |
| `part2.py` | $GF(p)$ 加/减/乘/幂、手写扩展欧几里得逆元、分享与 Lagrange 重构 |
| `part3.py` | 正确性、$t-1$ 安全经验验证（枚举/熵/卡方）、合数对比、边界测试 |
| `part4.py` | $GF(2^{128})$ 域运算、Fermat 与多项式 extgcd 两版逆元、Shamir 实现与测试 |
| `part5.py` | $GF(p)$ 与 $GF(2^{128})$ 同规模性能基准、log-log 绘图与斜率拟合 |
| `data/part5_performance.csv` / `.png` | Part 5 性能数据与 log-log 图 |
| `data/part3_*.csv` / `.png` | Part 3 安全性实验的分布数据与直方图 |
| `Shamir Secret Sharing 笔记.md` | Part 1 阅读笔记 |
| `Part5_报告.md` | Part 5 实验报告（含全部设计选择与实验分析） |
| `.gitignore` | Git 忽略规则（`__pycache__/`、`*.pyc`、`*.log` 等） |

## 关键设计

- 素数 $p=2^{128}+51$：$2^{128}$ 之上最小的素数，任意 128 位秘密可直接放入；
- $GF(2^{128})$ 模 $x^{128}+x^7+x^2+x+1$：GCM 标准多项式，不可约且约简常数项小；
- 全部随机数来自 `secrets`（操作系统 CSPRNG）：$GF(p)$ 用 `randbelow(p)`，$GF(2^{128})$ 用 `randbits(128)`；
- 求值点取 $x_i=1,\ldots,n$，刻意避开 $x=0$，因为 $f(0)$ 就是秘密本身。
