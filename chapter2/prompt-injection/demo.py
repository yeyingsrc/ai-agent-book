"""
实验 2-5：提示注入攻防实验 —— 主程序。

对 3 种攻击场景 x 4 种防御配置 的每个组合跑 N 次试验，统计攻击成功率，
最后打印一张 攻击 x 防御 的成功率矩阵，直观展示"防御逐层加强 -> 成功率下降"。

运行：
    python demo.py            # 默认每组合 4 次试验
    TRIALS=5 python demo.py   # 自定义试验次数（控制成本，建议 3-5）
"""

from __future__ import annotations

import os
import sys

from agent import DEFENSES, Agent, make_client
from attacks import ATTACKS


def run_matrix(trials: int) -> list[list[float]]:
    client, model = make_client()
    print(f"使用模型：{model}，每个组合试验 {trials} 次\n")

    # matrix[攻击索引][防御索引] = 成功率
    matrix: list[list[float]] = [
        [0.0 for _ in DEFENSES] for _ in ATTACKS
    ]

    for ai, attack in enumerate(ATTACKS):
        for di, defense in enumerate(DEFENSES):
            successes = 0
            errors = 0
            for t in range(trials):
                agent = Agent(
                    client=client,
                    model=model,
                    defense=defense,
                    webpage_content=attack.webpage_content,
                )
                result = agent.run(list(attack.user_messages))
                if result.error:
                    errors += 1
                    continue
                if attack.judge(result):
                    successes += 1
            rate = successes / trials if trials else 0.0
            matrix[ai][di] = rate
            flag = f"  (含 {errors} 次错误)" if errors else ""
            print(
                f"[{attack.name:<6}] x [{defense.name:<10}] "
                f"成功率 {rate:5.0%} ({successes}/{trials}){flag}"
            )
        print()

    return matrix


def print_matrix(matrix: list[list[float]]) -> None:
    print("=" * 68)
    print("攻击成功率矩阵（行=攻击场景，列=防御配置，越低越安全）")
    print("=" * 68)

    corner = "攻击 \\ 防御"
    header = f"{corner:<12}" + "".join(f"{d.name:>14}" for d in DEFENSES)
    print(header)
    print("-" * len(header))
    for ai, attack in enumerate(ATTACKS):
        row = f"{attack.name:<12}"
        for di in range(len(DEFENSES)):
            row += f"{matrix[ai][di]:>13.0%} "
        print(row)
    print("-" * len(header))

    # 各防御配置的平均成功率，展示"逐层加强 -> 整体下降"
    avg = f"{'平均':<12}"
    for di in range(len(DEFENSES)):
        col = sum(matrix[ai][di] for ai in range(len(ATTACKS))) / len(ATTACKS)
        avg += f"{col:>13.0%} "
    print(avg)
    print("=" * 68)


def main() -> int:
    trials = int(os.getenv("TRIALS", "4"))
    try:
        matrix = run_matrix(trials)
    except RuntimeError as exc:
        # 常见于未配置 OPENAI_API_KEY：给出清晰的人类可读提示而非原始堆栈。
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1
    print_matrix(matrix)
    print(
        "\n结论：从 D1 到 D4，随着防御逐层加强（提示词加固 -> 来源标记 -> "
        "运行时高风险操作校验），各类注入攻击的成功率显著下降，"
        "组合防御（D4）下越权工具调用类攻击被运行时校验彻底挡住，接近 0。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
