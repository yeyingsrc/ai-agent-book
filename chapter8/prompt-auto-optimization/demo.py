"""
实验 8-3：系统提示词的自动优化（基于人类反馈的自动化系统提示学习）

一条命令跑通完整流程：
  1. 用【初始 prompt】评测 → 暴露"政策争议就转人工"的过度转接问题；
  2. Coding Agent 读取 prompt 文件、定位转接规则、生成精确编辑并【真的改写文件】→ 展示 diff；
  3. 用【自动优化后的 prompt】重新评测；
  4. 对照【人工调优版 prompt】；
  5. 打印"保留任务集 / 边界案例集"在优化前后 + 人工版的正确率对比表。

    python demo.py
"""

import os
import shutil

from evaluate import evaluate_prompt
from coding_agent import optimize_prompt
from config import get_provider, get_model

HERE = os.path.dirname(os.path.abspath(__file__))
INITIAL_PROMPT = os.path.join(HERE, "prompts", "system_prompt.txt")
MANUAL_PROMPT = os.path.join(HERE, "prompts", "system_prompt_manual.txt")
WORKING_PROMPT = os.path.join(HERE, "runtime", "system_prompt_working.txt")

# 人类专家反馈：这就是驱动"自动系统提示学习"的信号
HUMAN_FEEDBACK = (
    "评测发现 Agent 存在【过度转接】问题：一遇到政策争议（如乘客要求超政策退款、"
    "要求免费、要求豁免费用）就直接转人工，而不尝试向乘客解释政策。\n"
    "正确做法应该是：通过耐心、共情地解释政策来处理这类争议，并提供合规的替代方案，"
    "而不是一转了之。真正需要转接人工的，只有两种情况——乘客明确要求人工客服，"
    "以及出现紧急安全 / 人身健康风险。"
)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _pct(cn):
    c, n = cn
    return f"{c}/{n} ({100 * c / n:.0f}%)" if n else "-"


def print_table(rows):
    """rows: list of (label, holdout_tuple, boundary_tuple)"""
    print("\n" + "=" * 74)
    print("正确率对比（保留任务集 = 既有正确行为不能退化；边界案例集 = 过度转接应改善）")
    print("=" * 74)
    header = f"{'系统提示词版本':<26}{'保留任务集(holdout)':<20}{'边界案例集(boundary)':<20}"
    print(header)
    print("-" * 74)
    for label, holdout, boundary in rows:
        print(f"{label:<24}{_pct(holdout):<22}{_pct(boundary):<22}")
    print("=" * 74)


def main():
    print("#" * 74)
    print("# 实验 8-3：基于人类反馈的系统提示词自动优化（航空客服场景）")
    print(f"# LLM 提供商: {get_provider()}   模型: {get_model()}")
    print("#" * 74)

    # ---- 准备：把初始 prompt 复制成本次运行的工作副本（Coding Agent 会改写它）----
    os.makedirs(os.path.dirname(WORKING_PROMPT), exist_ok=True)
    shutil.copyfile(INITIAL_PROMPT, WORKING_PROMPT)

    # ---- 步骤 1：评测初始 prompt ----
    print("\n【步骤 1】用初始系统提示词评测（观察是否过度转接）")
    before = evaluate_prompt(_read(INITIAL_PROMPT), label="初始 prompt")
    print(
        f"\n  初始结果：保留集 {_pct(before['holdout'])}，"
        f"边界集 {_pct(before['boundary'])}"
    )
    over_transfer = [
        r for r in before["results"]
        if r["group"] == "boundary" and not r["should_transfer"] and r["transferred"]
    ]
    print(f"  边界案例中出现【过度转接】的用例数：{len(over_transfer)} / "
          f"{len([r for r in before['results'] if r['group'] == 'boundary'])}")
    for r in over_transfer:
        print(f"    - {r['id']}：政策争议却直接转人工，原因『{r['transfer_reason']}』")

    # ---- 步骤 2：Coding Agent 自动改写 prompt 文件 ----
    print("\n【步骤 2】Coding Agent 读取并改写系统提示词文件……")
    opt = optimize_prompt(WORKING_PROMPT, HUMAN_FEEDBACK, verbose=True)
    print(f"\n  Coding Agent 改动说明：{opt['rationale']}")
    print("\n  ---------- 系统提示词文件 diff（真实写入磁盘）----------")
    print(opt["diff"] if opt["diff"].strip() else "  (无改动)")
    print("  --------------------------------------------------------")

    # ---- 步骤 3：评测自动优化后的 prompt ----
    print("\n【步骤 3】用自动优化后的系统提示词重新评测")
    after = evaluate_prompt(opt["after"], label="自动优化后 prompt")

    # ---- 步骤 4：对照人工调优版 ----
    print("\n【步骤 4】对照组：人工调优版系统提示词")
    manual = evaluate_prompt(_read(MANUAL_PROMPT), label="人工调优版 prompt(对照)")

    # ---- 步骤 5：对比表 ----
    print_table([
        ("初始 prompt(优化前)", before["holdout"], before["boundary"]),
        ("自动优化后 prompt", after["holdout"], after["boundary"]),
        ("人工调优版(对照)", manual["holdout"], manual["boundary"]),
    ])

    # ---- 结论 ----
    b_before_c, b_before_n = before["boundary"]
    b_after_c, _ = after["boundary"]
    h_before_c, _ = before["holdout"]
    h_after_c, _ = after["holdout"]
    print("\n【结论】")
    print(f"  · 边界案例集正确率：{b_before_c}/{b_before_n} → {b_after_c}/{b_before_n} "
          f"（{'提升 ✓' if b_after_c > b_before_c else '未提升'}）")
    print(f"  · 保留任务集正确率：{h_before_c} → {h_after_c} "
          f"（{'未退化 ✓' if h_after_c >= h_before_c else '退化 ✗'}）")
    print(f"\n  优化后的工作副本已写入：{WORKING_PROMPT}")


if __name__ == "__main__":
    main()
