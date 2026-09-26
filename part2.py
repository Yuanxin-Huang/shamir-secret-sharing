import secrets
P = 2**128 + 51

# GF(p) 基础运算
def gf_add(a, b, p):
    return (a + b) % p

def gf_sub(a, b, p):
    return (a - b) % p

def gf_mul(a, b, p):
    return (a * b) % p

def gf_pow(a, e, p):
    result = 1
    while e > 0:
        if e & 1:
            result = result * a % p
        a = a * a % p
        e >>= 1
    return result

# 扩展欧几里得算法
def extgcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extgcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def gf_inv(a, p):
    a %= p
    if a == 0:
        raise ZeroDivisionError("0 has no inverse")
    g, x, _ = extgcd(a, p)
    if g != 1:
        raise ValueError("inverse does not exist")
    return x % p

# Shamir 秘密分享
def share_secret(s, t, n, p=P):
    if not 1 <= t <= n:
        raise ValueError("need 1 <= t <= n")
    s %= p
    coeffs = [s]
    # t-1 个随机系数，构造 t-1次多项式
    for _ in range(t - 1):
        coeffs.append(secrets.randbelow(p))
    shares = []
    for x in range(1, n + 1):
        y = 0
        # 霍纳法则求值 f(x)
        for a in reversed(coeffs):
            y = (y * x + a) % p
        shares.append((x, y))
    return shares

#Lagrange插值重构
def reconstruct(shares, p=P):
    secret = 0
    for i, (xi, yi) in enumerate(shares):
        numerator = 1   #分子
        denominator = 1     #分母
        for j, (xj, _) in enumerate(shares):
            if i == j:
                continue
            numerator = numerator * (-xj) % p
            denominator = denominator * (xi - xj) % p
        li = numerator * gf_inv(denominator, p) % p
        secret = (secret + yi * li) % p
    return secret

# 测试
if __name__ == "__main__":
    secret = 9876543210123456789
    t = 4
    n = 5
    shares = share_secret(secret, t, n)
    print("生成分片 (x_i, y_i):")
    for s in shares:
        print(s)
    # 选取任意t份分片恢复
    selected_shares = [shares[0], shares[1],shares[2], shares[4]]
    recovered_s = reconstruct(selected_shares)
    print(f"\n原始秘密: {secret}")
    print(f"插值恢复秘密: {recovered_s}")
    print(f"恢复是否正确: {secret % P == recovered_s}")
