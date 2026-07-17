"""
实验 5-3 主程序：控制组（纯自然语言规则） vs 实验组（代码化规则三重保障）

跑法：
    python demo.py            # 跑全部 8 个 case，两组对比
    python demo.py --quick    # 只跑前 4 个 case（省钱快看）
    python demo.py -v         # 打印每步工具调用

指标：
    - 任务成功率：最终退款结果是否符合代码化政策真值。
    - 政策违规次数：多退款（该拒不拒） + 该退不退，两个方向都算。
    - 无效工具调用次数：被代码校验拒绝 / 未知预订等返回 error/rejected 的调用。
    - expected_* 自报值 vs 数据库真值 不一致比例（仅实验组，验证服务端真值校验的必要性）。
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()  # 若存在 .env 则加载 OPENAI_API_KEY / MODEL
except ImportError:
    pass

from airline_env import AirlineEnv
from agent import run_agent, MODEL
from tasks import TASKS


ALT_KEYWORDS = ["改签", "信用", "credit", "保留", "替代", "积分", "凭证", "备选"]


def judge(task, env, final_text) -> dict:
    """基于环境真值（状态即真值）做规则判据评分。"""
    refunded = env.res.refund_issued > 0
    expect_refundable = task.expect_refundable

    wrongful_refund = (not expect_refundable) and refunded      # 该拒不拒
    wrongful_refusal = expect_refundable and (not refunded)     # 该退不退
    violation = wrongful_refund or wrongful_refusal
    success = not violation

    offered_alt = any(k.lower() in final_text.lower() for k in ALT_KEYWORDS)

    return {
        "task_id": task.task_id,
        "expect_refundable": expect_refundable,
        "refunded": refunded,
        "success": success,
        "wrongful_refund": wrongful_refund,
        "wrongful_refusal": wrongful_refusal,
        "invalid_tool_calls": env.invalid_tool_calls,
        "offered_alt": offered_alt if not expect_refundable else None,
        "checklist_records": env.checklist_records,
    }


def run_group(mode: str, tasks, verbose: bool) -> list[dict]:
    print(f"\n{'='*72}\n运行 {'控制组 (纯自然语言规则)' if mode=='control' else '实验组 (代码化规则·三重保障)'}  模型={MODEL}\n{'='*72}")
    results = []
    for task in tasks:
        env = AirlineEnv(task.reservation)
        out = run_agent(env, task.user_message, mode, verbose=verbose)
        r = judge(task, env, out["final_text"])
        r["final_text"] = out["final_text"]
        r["transcript"] = out["transcript"]
        results.append(r)
        flag = "✅" if r["success"] else "❌"
        detail = "多退款" if r["wrongful_refund"] else ("该退未退" if r["wrongful_refusal"] else "")
        print(f"  {flag} {task.task_id:<26} 应退={str(r['expect_refundable']):<5} 实退={str(r['refunded']):<5} "
              f"无效调用={r['invalid_tool_calls']} {detail}")
    return results


def summarize(results: list[dict]) -> dict:
    n = len(results)
    succ = sum(r["success"] for r in results)
    violations = sum(r["wrongful_refund"] + r["wrongful_refusal"] for r in results)
    invalid = sum(r["invalid_tool_calls"] for r in results)
    # expected_* vs 真值 一致性（合并所有 checklist 记录）
    records = [rec for r in results for rec in r["checklist_records"]]
    mism = sum(1 for rec in records if not rec["match"])
    return {
        "n": n, "success": succ, "success_rate": succ / n if n else 0.0,
        "violations": violations, "invalid": invalid,
        "checklist_total": len(records), "checklist_mismatch": mism,
    }


def print_comparison(sc, se):
    print(f"\n{'#'*72}\n# 指标对比：控制组 vs 实验组\n{'#'*72}")
    rows = [
        ("任务成功率", f"{sc['success']}/{sc['n']} = {sc['success_rate']*100:.0f}%",
                       f"{se['success']}/{se['n']} = {se['success_rate']*100:.0f}%"),
        ("政策违规次数", str(sc["violations"]), str(se["violations"])),
        ("无效工具调用次数", str(sc["invalid"]), str(se["invalid"])),
    ]
    w1, w2, w3 = 20, 24, 24
    print(f"{'指标':<{w1}}{'控制组':<{w2}}{'实验组':<{w3}}")
    print("-" * (w1 + w2 + w3))
    for name, a, b in rows:
        print(f"{name:<{w1}}{a:<{w2}}{b:<{w3}}")

    print(f"\n[实验组] expected_* 自报值 vs 数据库真值：")
    if se["checklist_total"]:
        ratio = se["checklist_mismatch"] / se["checklist_total"]
        print(f"  共 {se['checklist_total']} 次带 checklist 的取消调用，其中 {se['checklist_mismatch']} 次"
              f"与真值不一致 —— 不一致比例 = {ratio*100:.0f}%")
        print("  （说明：模型的自我认知会出错；若无服务端真值校验，这些错误会直接变成违规操作。）")
    else:
        print("  本次运行无 checklist 记录。")


def print_interception_example(se_results):
    """找一例：实验组模型自报可退(expected_refundable=True)，但数据库真值不可退，被代码拦截。"""
    for r in se_results:
        for rec in r["checklist_records"]:
            if rec["expected_refundable"] is True and rec["actual_refundable"] is False:
                print(f"\n{'*'*72}\n* 代码化校验拦截示例（{r['task_id']}）\n{'*'*72}")
                print(f"模型 checklist 自报：expected_refundable=True（认为可退）")
                print(f"数据库真值        ：refundable=False，原因={rec['actual_reason']}")
                for step in r["transcript"]:
                    if step["tool"] == "cancel_reservation":
                        print(f"\n模型发起取消调用：{step['args']}")
                        print(f"工具代码化校验返回：status={step['result'].get('status')}，"
                              f"reason={step['result'].get('reason')}")
                        print(f"  → {step['result'].get('message')}")
                        break
                print(f"\n模型最终回复用户（被拦截后转为解释/提议替代）：\n  {r['final_text'][:400]}")
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="只跑前 4 个 case")
    ap.add_argument("-v", "--verbose", action="store_true", help="打印每步工具调用")
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("错误：未设置 OPENAI_API_KEY，请复制 env.example 为 .env 并填入，或直接 export。")

    tasks = TASKS[:4] if args.quick else TASKS
    print(f"实验 5-3：小模型通过代码化知识提升执行规则的准确性")
    print(f"共 {len(tasks)} 个 case（可退 {sum(t.expect_refundable for t in tasks)} / "
          f"不可退 {sum(not t.expect_refundable for t in tasks)}）")

    control = run_group("control", tasks, args.verbose)
    experiment = run_group("codified", tasks, args.verbose)

    sc, se = summarize(control), summarize(experiment)
    print_comparison(sc, se)
    ok = print_interception_example(experiment)
    if not ok:
        print("\n（本次运行实验组未出现 expected=可退/真值=不可退 的拦截样例；"
              "可重跑或调高温度观察。）")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
