import csv
import gc
import math
import secrets
import time
from pathlib import Path

import matplotlib.pyplot as plt

from part2 import P, share_secret as share_gfp, reconstruct as rec_gfp
from part4 import share_secret as share_gf128, reconstruct as rec_gf128


# 两套实现的统一适配层：输入秘密、t、n，返回 (shares, 恢复函数)
IMPLS = {
    "GF(p)": (
        lambda secret, t, n: share_gfp(secret, t, n, P),
        lambda shares: rec_gfp(shares, P),
    ),
    "GF(2^128)": (
        lambda secret, t, n: share_gf128(secret, t, n),
        rec_gf128,
    ),
}


# 测一次完整的分享 + 重构，返回各自墙钟耗时
def measure_once(n, share_fn, rec_fn):
    t = max(2, n // 2)

    # 秘密来自密码学安全随机源；对两个域都合法：
    #   s < 2^128 < p，且 s 恰好落在 GF(2^128) 元素范围内
    secret = secrets.randbits(128)

    start = time.perf_counter()
    shares = share_fn(secret, t, n)
    share_seconds = time.perf_counter() - start

    selected = shares[:t]
    start = time.perf_counter()
    recovered = rec_fn(selected)
    reconstruct_seconds = time.perf_counter() - start

    if recovered != secret:
        raise AssertionError(f"reconstruction failed for n={n}, t={t}")

    return t, share_seconds, reconstruct_seconds


# 对 log-log 数据做最小二乘拟合，返回直线斜率（即时间 ~ n^slope）
def fit_slope(ns, seconds):
    lx = [math.log10(n) for n in ns]
    ly = [math.log10(s) for s in seconds]
    size = len(lx)
    mean_x = sum(lx) / size
    mean_y = sum(ly) / size
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(lx, ly))
    denominator = sum((x - mean_x) ** 2 for x in lx)
    return numerator / denominator


def run_benchmark(
    ns=(10, 20, 30, 50, 70, 100, 200, 300, 500, 700, 1000),
    repeats=5,
):
    # 预热：避免首次调用的解释器/分配开销污染最小 n 的数据
    for share_fn, rec_fn in IMPLS.values():
        measure_once(10, share_fn, rec_fn)

    rows = []
    results = {}  # 供绘图使用：{field: {"ns": [...], "share": [...], "rec": [...]}}

    gc.collect()
    gc_enabled = gc.isenabled()
    gc.disable()  # 计时期间关掉 GC，减少随机停顿

    try:
        for field, (share_fn, rec_fn) in IMPLS.items():

            print(f"\n----- {field} -----")

            field_rows = []

            for n in ns:
                measurements = [
                    measure_once(n, share_fn, rec_fn) for _ in range(repeats)
                ]
                t = measurements[0][0]

                # 取最小值而不是均值：墙钟时间只会被调度/中断拖慢，
                # 最小值最接近"没有干扰时的真实耗时"
                share_seconds = min(row[1] for row in measurements)
                reconstruct_seconds = min(row[2] for row in measurements)

                rows.append((field, n, t, share_seconds, reconstruct_seconds))
                field_rows.append((n, share_seconds, reconstruct_seconds))

                print(
                    f"n={n:4d}, t={t:4d}, "
                    f"share={share_seconds:.6f}s, "
                    f"reconstruct={reconstruct_seconds:.6f}s "
                    f"(best of {repeats})"
                )

            ns_values = [row[0] for row in field_rows]
            share_values = [row[1] for row in field_rows]
            rec_values = [row[2] for row in field_rows]

            results[field] = {
                "ns": ns_values,
                "share": share_values,
                "rec": rec_values,
                "share_slope": fit_slope(ns_values, share_values),
                "rec_slope": fit_slope(ns_values, rec_values),
            }
    finally:
        if gc_enabled:
            gc.enable()

    output_dir = Path(__file__).resolve().parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "part5_performance.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["field", "n", "t", "share_seconds", "reconstruct_seconds"]
        )
        writer.writerows(rows)

    # ---------- log-log 图：4 条线，每条标注实测斜率 ----------
    markers = {
        "GF(p)": ("o", "#1f77b4"),
        "GF(2^128)": ("s", "#ff7f0e"),
    }

    plt.figure(figsize=(8.5, 5.5))

    for field, data in results.items():
        marker, color = markers[field]
        plt.loglog(
            data["ns"], data["share"], marker + "--", color=color,
            label=f"{field} share (slope={data['share_slope']:.2f})",
        )
        plt.loglog(
            data["ns"], data["rec"], marker + "-", color=color,
            label=f"{field} reconstruct (slope={data['rec_slope']:.2f})",
        )

    plt.xlabel("n (log scale)")
    plt.ylabel("time in seconds (log scale)")
    plt.title("Shamir Secret Sharing Performance: GF(p) vs GF(2^128)")
    plt.grid(True, which="both", linestyle=":", alpha=0.5)
    plt.legend(fontsize=9)
    plt.tight_layout()
    figure_path = output_dir / "part5_performance.png"
    plt.savefig(figure_path, dpi=150)
    plt.close()

    print("\n拟合幂次：")
    for field, data in results.items():
        print(
            f"  {field:10s} share ~ n^{data['share_slope']:.2f}, "
            f"reconstruct ~ n^{data['rec_slope']:.2f}"
        )
    print(f"\nCSV saved to {csv_path}")
    print(f"Figure saved to {figure_path}")
    return rows


if __name__ == "__main__":
    run_benchmark()
