import secrets
import random
# GF(2^128)
#
# 不可约多项式：
# x^128 + x^7 + x^2 + x + 1
M = 128
MASK = (1 << M) - 1
MOD_POLY = (
    (1 << 128)
    | (1 << 7)
    | (1 << 2)
    | (1 << 1)
    | 1
)
# GF(2^128) 基本运算
# 加法 = XOR
def gf2_add(a, b):
    return a ^ b
# 把任意次数的二进制多项式按 m(x) 约减到 [0, 2^128)
def gf2_reduce(a):
    while a.bit_length() > M:
        # 最高次项 x^k 用 x^128 ≡ x^7+x^2+x+1 替换，
        # 即把 m(x) 平移到与最高次项对齐后 XOR
        a ^= MOD_POLY << (a.bit_length() - 1 - M)
    return a


# 乘法：无进位乘法 + 模不可约多项式
def gf2_mul(a, b):
    # 先把输入约简成域元素，否则高位输入会被静默算错
    a = gf2_reduce(a)
    b = gf2_reduce(b)
    result = 0
    while b > 0:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        # 如果超过 128 位，进行模多项式约减
        if a & (1 << M):
            a ^= MOD_POLY
    return result

# 幂：快速幂
def gf2_pow(a, e):
    result = 1
    while e > 0:
        if e & 1:
            result = gf2_mul(result, a)
        a = gf2_mul(a, a)
        e >>= 1
    return result


# 逆元
# GF(2^128) 的乘法群有 2^128 - 1 个元素：
# a^(2^128 - 1) = 1
# a^(-1) = a^(2^128 - 2)
def gf2_inv(a):
    a = gf2_reduce(a)
    if a == 0:
        raise ZeroDivisionError("0 has no inverse")
    return gf2_pow(a, (1 << 128) - 2)


# 逆元（方法二：手写 GF(2)[x] 多项式扩展欧几里得）
# 与整数 extgcd 完全平行，只是把"整数"换成"二进制多项式"：
#   整数版本用 a = q*b + r（普通带余除法）
#   这里用   old_r = q * r + rem（多项式带余除法，减法=XOR）
# 维护 Bézout 系数 t，使不变量始终成立：
#   r == t * a  (mod m(x))
# 当 r 变成 gcd = 1 时，t 就是 a^(-1)。
def gf2_inv_extgcd(a):
    a = gf2_reduce(a)
    if a == 0:
        raise ZeroDivisionError("0 has no inverse")
    old_r, r = MOD_POLY, a  #追踪余数
    old_t, t = 0, 1  #追踪 Bézout 系数 t
    while r != 0:
        # ---------- GF(2)[x] 带余除法：old_r = q * r + rem ----------
        q = 0
        rem = old_r
        deg_r = r.bit_length()
        # 每次消掉 rem 的最高次项
        while rem.bit_length() >= deg_r:
            shift = rem.bit_length() - deg_r
            rem ^= r << shift
            q ^= 1 << shift 
        # 首步 old_r = m(x) 次数为 128，q 可能带 x^128 项，
        # 先约减成域元素，再与 t 相乘
        # if q & (1 << M):    #检查 q 的第 128 位是不是 1
        #     q ^= MOD_POLY
        # ---------- 特征 2 下减法就是 XOR ----------
        old_r, r = r, rem
        old_t, t = t, old_t ^ gf2_mul(q, t)

    # m(x) 不可约且 a != 0，gcd 必为 1
    if old_r != 1:
        raise ValueError("inverse does not exist")
    return old_t


# Shamir 秘密分享
def share_secret(secret, t, n):
    if not 1 <= t <= n:
        raise ValueError("need 1 <= t <= n")
    secret &= MASK
    # f(0) = secret
    coeffs = [secret]
    # 随机生成 t-1 个系数
    for _ in range(t - 1):
        coeffs.append(secrets.randbits(128))
    shares = []
    # x = 1, 2, ..., n
    for x in range(1, n + 1):
        y = 0
        # 霍纳法则
        for a in reversed(coeffs):
            y = gf2_add(gf2_mul(y, x), a)
        shares.append((x, y))
    return shares


# Lagrange 插值重构
def reconstruct(shares):
    if len(shares) == 0:
        raise ValueError("shares cannot be empty")
    # 检查 x 是否重复
    xs = [x for x, _ in shares]
    if len(xs) != len(set(xs)):
        raise ValueError("duplicate x")
    secret = 0

    for i, (xi, yi) in enumerate(shares):
        numerator = 1
        denominator = 1
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            # GF(2) 中 -x = x
            numerator = gf2_mul(
                numerator,
                xj
            )
            # xi - xj = xi + xj = xi XOR xj
            denominator = gf2_mul(
                denominator,
                gf2_add(xi, xj)
            )
        li = gf2_mul(
            numerator,
            gf2_inv_extgcd(denominator)
        )
        secret = gf2_add(
            secret,
            gf2_mul(yi, li)
        )
    return secret


# 1. GF(2^128) 基本运算测试

def test_field():
    print("\n========== GF(2^128) 测试 ==========")
    a = secrets.randbits(128)
    b = secrets.randbits(128)
    c = secrets.randbits(128)
    # a + a = 0
    assert gf2_add(a, a) == 0
    print("[PASS] a + a = 0")
    # a + 0 = a
    assert gf2_add(a, 0) == a
    print("[PASS] a + 0 = a")
    # a * 0 = 0
    assert gf2_mul(a, 0) == 0
    print("[PASS] a * 0 = 0")
    # a * 1 = a
    assert gf2_mul(a, 1) == a
    print("[PASS] a * 1 = a")
    # 逆元（两种实现）
    if a != 0:
        assert gf2_mul(a, gf2_inv(a)) == 1
        assert gf2_mul(a, gf2_inv_extgcd(a)) == 1
        print("[PASS] a * a^(-1) = 1（Fermat 与 extgcd 两版）")

    # 乘法交换律
    assert gf2_mul(a, b) == gf2_mul(b, a)
    print("[PASS] a * b = b * a")

    # 结合律、分配律（随机抽测）
    assert gf2_mul(gf2_mul(a, b), c) == gf2_mul(a, gf2_mul(b, c))
    assert gf2_mul(a, gf2_add(b, c)) == gf2_add(
        gf2_mul(a, b), gf2_mul(a, c)
    )
    print("[PASS] 结合律 / 分配律")

    # ---------- 已知答案向量：锁定位序与约简约定 ----------
    # 整数 2 代表多项式 x
    assert gf2_mul(2, 2) == 4          # x * x = x^2
    print("[PASS] 2 * 2 = 4 (x*x = x^2)")
    # 特征 2 的关键现象：(x+1)^2 = x^2 + 1，没有 2x 交叉项
    assert gf2_mul(3, 3) == 5
    print("[PASS] 3 * 3 = 5 ((x+1)^2 = x^2+1，无交叉项)")

    # x^127 * x = x^128 ≡ x^7 + x^2 + x + 1 = 128+4+2+1 = 135
    assert gf2_mul(1 << 127, 2) == 135
    print("[PASS] x^127 * x = 135 (m(x) 约简)")

    # 高位输入必须先被约简：x^128 与 1 相乘也应为 135
    assert gf2_mul(1 << 128, 1) == 135
    print("[PASS] gf2_mul 对高位输入先约简")


# 2. 两种逆元实现的等价性测试

def test_inverse_methods(times=300):

    # 边界元素 + 随机元素
    candidates = [
        1, 2, 3, 4,
        MASK, MASK - 1,
        1 << 127, (1 << 127) | 1
    ]
    candidates.extend(
        secrets.randbits(128) for _ in range(times)
    )

    for a in candidates:
        if a == 0:
            continue
        inv_f = gf2_inv(a)
        inv_e = gf2_inv_extgcd(a)

        assert inv_f == inv_e, f"两版逆元不一致：a={a}"
        assert gf2_mul(a, inv_e) == 1

    print(f"[PASS] Fermat 与 extgcd 逆元在 {len(candidates)} 个元素上完全一致")


# 3. Shamir 正确性测试

def test_shamir(times=100):
    print("\n========== Shamir 正确性测试 ==========")
    for _ in range(times):
        n = random.randint(2, 10)
        t = random.randint(1, n)
        secret = secrets.randbits(128)
        shares = share_secret(
            secret,
            t,
            n
        )
        selected = random.sample(
            shares,
            t
        )
        recovered = reconstruct(selected)
        if recovered != secret:

            print("[FAIL] Shamir 测试")
            print("t =", t)
            print("n =", n)
            print("secret =", secret)
            print("recovered =", recovered)
            return False
    print(f"[PASS] Shamir 正确性测试：{times} 次全部通过")
    return True


# 4. 边界情况测试

def test_boundary():
    print("\n========== 边界情况测试 ==========")
    # t = 1
    secret = secrets.randbits(128)
    shares = share_secret(secret, 1, 5)
    assert reconstruct([shares[0]]) == secret
    print("[PASS] t = 1")
    # t = n
    secret = secrets.randbits(128)
    shares = share_secret(secret, 5, 5)
    assert reconstruct(shares) == secret
    print("[PASS] t = n")
    # secret = 0
    secret = 0
    shares = share_secret(secret, 3, 5)
    selected = random.sample(shares, 3)
    assert reconstruct(selected) == 0
    print("[PASS] secret = 0")
    # x = 0 会直接暴露秘密
    secret = secrets.randbits(128)
    zero_share = (0, secret)
    assert zero_share[1] == secret
    print("[PASS] x = 0 会直接暴露秘密")

    # 重复 x
    bad_shares = [
        (1, 100),
        (1, 200),
        (2, 300)
    ]

    try:
        reconstruct(bad_shares)
        print("[FAIL] 重复 x 没有检测")
    except ValueError:
        print("[PASS] 重复 x 被检测")



# 5. 主程序

if __name__ == "__main__":
    print("========== Part 4 GF(2^128) ==========")
    test_field()
    test_inverse_methods(300)
    test_shamir(100)
    test_boundary()
    print("\n========== Part 4 测试结束 ==========")