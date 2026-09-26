import random
import math
import csv
import itertools
from pathlib import Path

import matplotlib.pyplot as plt

from part2 import P, share_secret, reconstruct, gf_inv

# 所有实验输出（CSV/PNG）统一写到脚本旁的 data/ 目录
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 1. 正确性测试
def test_correctness(times=1000):

    for _ in range(times):
        n = random.randint(2, 20)
        t = random.randint(1, n)
        secret = random.randrange(P)
        shares = share_secret(secret, t, n)
        selected = random.sample(shares, t)
        recovered = reconstruct(selected)
        if recovered != secret:
            print("[FAIL] 正确性测试")
            print("t =", t)
            print("n =", n)
            print("secret =", secret)
            print("recovered =", recovered)
            return False

    print(f"[PASS] 正确性测试：{times} 次全部通过")
    return True


# 2. 边界情况

def test_boundary_cases():

    print("\n========== 边界情况测试 ==========")

    # ---------- t = 1 ----------
    secret = 123456
    shares = share_secret(secret, 1, 5)
    assert reconstruct([shares[0]]) == secret
    print("[PASS] t = 1")

    # ---------- t = n ----------
    secret = 987654321
    t = 5
    n = 5
    shares = share_secret(secret, t, n)
    assert reconstruct(shares) == secret
    print("[PASS] t = n")

    # ---------- secret = 0 ----------
    secret = 0
    shares = share_secret(secret, 3, 5)
    selected = random.sample(shares, 3)
    assert reconstruct(selected) == 0
    print("[PASS] secret = 0")

    # ---------- x_i = 0 ----------
    secret = 123456789
    zero_share = (0, secret)
    # f(0) = secret，因此 x=0 会直接暴露秘密
    assert zero_share[1] == secret
    print("[PASS] x_i = 0：share 直接暴露秘密")

    # ---------- 重复 x_i ----------
    bad_shares = [
        (1, 100),
        (1, 200),
        (2, 300)
    ]

    try:
        reconstruct(bad_shares)
        print("[FAIL] 重复 x_i 没有触发异常")
    except (ValueError, ZeroDivisionError):
        print("[PASS] 重复 x_i 被检测为非法情况")


# 3. 计算 t-1 个 share 对应的 g(0)
def calculate_base(shares, q):

    base = 0
    for i, (xi, yi) in enumerate(shares):
        numerator = 1
        denominator = 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            numerator = numerator * (-xj) % q
            denominator = denominator * (xi - xj) % q
        inv = gf_inv(denominator, q)
        li = numerator * inv % q
        base = (base + yi * li) % q
    return base



# 4. 枚举 t-1 个 share 对应的所有可能秘密（素数模）
def possible_secrets_prime(shares, t, q):

    if len(shares) != t - 1:
        raise ValueError("需要输入 t-1 个 share")
    # g(0)：用拉格朗日插值，在 x=0 处求出 g(x) 的值
    base = calculate_base(shares, q)
    # h(0) = h(x) 在 x=0 处的值 = ∏(0 - xᵢ) = ∏(-xᵢ)
    h0 = 1
    for xi, _ in shares:
        h0 = h0 * (-xi) % q
    if h0 == 0:
        raise ValueError("存在 x_i = 0，无法进行该安全性实验")
    counts = [0] * q
    # 枚举自由系数 a
    for a in range(q):
        secret = (base + a * h0) % q# f(0) = g(0) + a·h(0)
        counts[secret] += 1
    return counts

# 5. Shannon 熵
def calculate_entropy(counts):

    total = sum(counts)
    entropy = 0
    for count in counts:
        if count == 0:
            continue
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


# 6. 卡方统计量
def calculate_chi_square(counts):

    total = sum(counts)
    k = len(counts)
    expected = total / k
    chi_square = 0
    for observed in counts:
        chi_square += (observed - expected) ** 2 / expected
    return chi_square


# 7. 卡方 p-value
#
# 这里使用 Wilson-Hilferty 近似。
# 不依赖 scipy。


def chi_square_p_value(chi_square, df):

    if chi_square <= 0:
        return 1.0
    # Wilson-Hilferty 近似
    z = (
        (chi_square / df) ** (1 / 3)
        - 1
        + 2 / (9 * df)
    ) / math.sqrt(2 / (9 * df))
    # 标准正态分布右尾概率
    p_value = 0.5 * math.erfc(z / math.sqrt(2))
    return p_value


# 8. 保存后验分布
def save_distribution(counts, filename):

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        writer.writerow([
            "secret",
            "count"
        ])
        for secret, count in enumerate(counts):
            writer.writerow([
                secret,
                count
            ])


# 9. 素数 t-1 安全性实验

def prime_security_experiment(
    q=100003,
    t=4,
    n=6
):

    print("\n========== 素数 t-1 安全性实验 ==========")

    # 固定秘密
    secret = random.randrange(q)

    # 生成 n 个 share
    shares = share_secret(
        secret,
        t,
        n,
        q
    )

    # 攻击者只获得 t-1 个 share
    leaked = random.sample(
        shares,
        t - 1
    )

    # 枚举所有可能秘密
    counts = possible_secrets_prime(
        leaked,
        t,
        q
    )

    # 熵
    entropy = calculate_entropy(counts)

    max_entropy = math.log2(q)

    # 卡方
    chi_square = calculate_chi_square(counts)

    df = q - 1

    p_value = chi_square_p_value(
        chi_square,
        df
    )

    # 可能秘密数量
    candidate_count = sum(
        1 for count in counts
        if count > 0
    )

    print("q =", q)
    print("t =", t)
    print("n =", n)

    print("真实秘密 =", secret)

    print("\n攻击者拥有的 t-1 个 share：")

    for share in leaked:
        print(share)

    print("\n可能秘密数量 =", candidate_count)
    print("理论秘密总数 =", q)

    print("\n后验熵 =", entropy)
    print("均匀分布最大熵 =", max_entropy)
    print("熵差 =", entropy - max_entropy)

    print("\n卡方统计量 =", chi_square)
    print("自由度 =", df)
    print("p-value ≈", p_value)


    uniform = all(
        count == 1
        for count in counts
    )

    print("\n每个秘密是否恰好出现一次 =", uniform)

    # 保存 CSV
    save_distribution(
        counts,
        DATA_DIR / "part3_prime_posterior.csv"
    )

    # 画图
    plt.figure(figsize=(10, 4))

    plt.hist(
        range(q),
        bins=100,
        weights=counts,
        edgecolor="black"
    )

    plt.xlabel("Secret")
    plt.ylabel("Frequency")
    plt.title(
        f"Prime Modulus Posterior Distribution "
        f"(q={q}, t={t}, leaked={t-1})"
    )

    plt.tight_layout()

    plt.savefig(
        DATA_DIR / "part3_prime_posterior.png",
        dpi=150
    )

    plt.close()

    return {
        "q": q,
        "t": t,
        "n": n,
        "secret": secret,
        "leaked": leaked,
        "candidate_count": candidate_count,
        "entropy": entropy,
        "max_entropy": max_entropy,
        "chi_square": chi_square,
        "p_value": p_value
    }


# 10. 合数模数实验：逆元统计
#
# 合数不是有限域。
# 因此不是所有非零元素都有逆元。

def composite_inverse_experiment(q=100000):

    print("\n========== 合数模数实验（逆元统计） ==========")
    nonzero = q - 1
    invertible = 0
    no_inverse = 0
    bad_elements = []
    for a in range(1, q):
        try:
            gf_inv(a, q)
            invertible += 1
        except (ValueError, ZeroDivisionError):
            no_inverse += 1
            if len(bad_elements) < 20:
                bad_elements.append(a)

    print("合数 q =", q)
    print("非零元素数量 =", nonzero)
    print("存在逆元的非零元素 =", invertible)
    print("不存在逆元的非零元素 =", no_inverse)

    print("\n前 20 个没有逆元的元素：")
    print(bad_elements)

    # 保存数据
    with open(
        DATA_DIR / "part3_composite_inverse.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)
        writer.writerow([
            "element",
            "invertible"
        ])

        # 只保存前 1000 个，避免 CSV 过大
        for a in range(1, min(q, 1001)):
            try:
                gf_inv(a, q)
                value = 1
            except (ValueError, ZeroDivisionError):
                value = 0
            writer.writerow([
                a,
                value
            ])

    return {
        "q": q,
        "nonzero": nonzero,
        "invertible": invertible,
        "no_inverse": no_inverse
    }


# 11. 自动寻找"能暴露合数问题"的 x 组合
#
# 关键点：合数是否破坏安全性，不取决于 q 是不是合数，
# 而取决于 h0 = prod(-xi) 是否与 q 互质。
#
# 需要同时满足：
#   (a) 两两之差 (xi - xj) 都与 q 互质 —— 否则插值本身直接抛异常，
#       没法拿到一组"看似合法"的 base，也就没法演示"分布不均匀"；
#   (b) h0 = prod(-xi) 与 q 不互质 —— 这样 a -> secret 就不是双射，
#       后验分布会坍缩到一个真子集上。


def find_bad_xs(q, k, x_range=None, search_limit=200):

    # 只在一个较小的窗口内搜索即可：我们只需要找到"一组"满足条件的
    # x 值来演示问题，不需要遍历整个 [1, q) 的组合空间（那样组合数
    # 会随 q 迅速爆炸，导致不可接受的运行时间）。
    if x_range is None:
        x_range = range(1, min(q, search_limit))
    for xs in itertools.combinations(x_range, k):
        # (a) 两两之差 (xi - xj) 都与 q 互质
        ok = all(
            math.gcd(xs[i] - xs[j], q) == 1
            for i in range(k)
            for j in range(k)
            if i != j
        )
        if not ok:
            continue
        h0 = 1
        for x in xs:
            h0 = (h0 * (-x)) % q
        # (b) h0 = prod(-xi) 与 q 不互质
        if math.gcd(h0, q) != 1:
            return list(xs)
    return None



# 12. 合数后验分布实验（对比实验）
#
# 为了展示合数导致的非域结构，
# 使用较小的合数进行枚举，并自动搜索一组
# "两两之差可逆、但 h0 与 q 不互质" 的 x 值。
# 这样才能真正演示出"合数模数下 t-1 个 share
# 会把秘密收窄到一个远小于 q 的子集"。

def composite_posterior_experiment(
    q=15,
    t=3
):

    print("\n========== 合数后验分布对比实验 ==========")
    k = t - 1
    xs = find_bad_xs(q, k)
    if xs is None:
        print(
            f"未能在 q={q} 下找到能暴露问题的 x 组合，"
            "请换一个合数（建议使用含平方因子或多个小素因子的合数）。"
        )
        return None

    # 用找到的 x 值构造 t-1 个 "share"
    # y 值任意选取（这里用固定的小正整数），
    # 因为我们关心的是分布的形状，而不是某个具体秘密
    leaked = [(x, (3 * x + 1) % q) for x in xs]

    print("合数 q =", q)
    print("自动搜索得到的泄露 share =", leaked)
    h0 = 1
    for x in xs:
        h0 = (h0 * (-x)) % q    # h0 = ∏(-xi) mod q
    print(
        f"h0 = prod(-xi) mod q = {h0}, "
        f"gcd(h0, q) = {math.gcd(h0, q)} (≠1 说明 a->secret 不是双射)"
    )

    counts = [0] * q
    base = calculate_base(leaked, q)
    # 枚举自由系数 a
    for a in range(q):
        secret = (base + a * h0) % q
        counts[secret] += 1

    valid_total = sum(counts)
    entropy = calculate_entropy(counts)
    max_entropy = math.log2(q)
    candidate_count = sum(
        1 for x in counts
        if x > 0
    )

    chi_square = calculate_chi_square(counts)
    df = q - 1
    p_value = chi_square_p_value(chi_square, df)

    print("有效候选数量 =", candidate_count, "/", q)

    print("后验熵 =", entropy)
    print("均匀分布最大熵 =", max_entropy)
    print("熵差 =", entropy - max_entropy)

    print("\n卡方统计量 =", chi_square)
    print("自由度 =", df)
    print("p-value ≈", p_value)
    print("\n后验分布（仅列出前 20 个非零项，完整数据见 CSV）：")

    shown = 0
    for secret, count in enumerate(counts):

        if count > 0:
            print(
                f"secret={secret}, "
                f"count={count}"
            )
            shown += 1
            if shown >= 20:
                if candidate_count > 20:
                    print(f"... 其余 {candidate_count - 20} 个候选省略，完整列表见 CSV")
                break

    # 保存
    save_distribution(
        counts,
        DATA_DIR / "part3_composite_posterior.csv"
    )

    # 画图
    plt.figure(figsize=(8, 4))

    plt.bar(
        range(q),
        counts
    )

    plt.xlabel("Secret")
    plt.ylabel("Frequency")

    plt.title(
        f"Composite Modulus Posterior Distribution "
        f"(q={q}, candidates={candidate_count}/{q})"
    )

    plt.tight_layout()

    plt.savefig(
        DATA_DIR / "part3_composite_posterior.png",
        dpi=150
    )

    plt.close()

    return {
        "q": q,
        "xs": xs,
        "leaked": leaked,
        "entropy": entropy,
        "max_entropy": max_entropy,
        "chi_square": chi_square,
        "p_value": p_value,
        "candidate_count": candidate_count,
        "counts": counts
    }



# 13. 主程序

if __name__ == "__main__":

    print("========== Part 3 测试开始 ==========")
    # 1. 1000 次正确性测试
    test_correctness(1000)
    # 2. 边界情况
    test_boundary_cases()
    # 3. 素数 t-1 安全性实验
    prime_result = prime_security_experiment(
        q=100003,
        t=4,
        n=6
    )
    # 4. 合数逆元实验
    composite_inverse_result = (
        composite_inverse_experiment(
            q=100000
        )
    )
    # 5. 合数后验分布实验（对比实验）
    composite_posterior_result = (
        composite_posterior_experiment(
            q=15,
            t=3
        )
    )

    # 这里用 q~10^4 量级即可清楚展示分布不均匀的现象）
    composite_posterior_experiment(
        q=9973 * 3,   # 一个中等大小、含小素因子的合数
        t=4
    )
    print("\n========== Part 3 测试结束 ==========")