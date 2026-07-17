"""
实验 8-5 一键演示：`python demo.py`

演示两件事：
  1) 进化：Agent 从零基础工具出发 —— 搜索 → 读文档 → 沙箱测试 → 封装工具 →
     用新工具给出 NVIDIA(NVDA) 的真实股价与「相对一周前」的真实涨跌幅。
  2) 复用：换一支股票(AAPL) 再问一次。Agent 应先 search_tools 命中已创建的工具并直接复用，
     不再重新上网搜索、重新造轮子。程序会打印轨迹并自动校验「复用」是否成立。

注意：真实联网 + 真实调用 OpenAI，请先在环境中配置 OPENAI_API_KEY。
"""

import sys

from agent import SelfEvolvingAgent


TASK_1 = "查询 NVIDIA(股票代码 NVDA) 的最新股价，以及与一周前相比的涨跌幅（百分比）。请给出真实数据。"
TASK_2 = "查询 Apple(股票代码 AAPL) 的最新股价，以及与一周前相比的涨跌幅（百分比）。请给出真实数据。"


def main():
    try:
        agent = SelfEvolvingAgent(verbose=True)
    except RuntimeError as e:
        print(f"[配置错误] {e}", file=sys.stderr)
        print(
            "请先配置对应供应商的 API Key（默认 OpenAI）：\n"
            "  cp env.example .env  然后在 .env 中填入 OPENAI_API_KEY；\n"
            "  或直接 export OPENAI_API_KEY=sk-...\n"
            "如需切换供应商：export LLM_PROVIDER=moonshot|ark 并配置对应的 "
            "MOONSHOT_API_KEY / ARK_API_KEY。",
            file=sys.stderr,
        )
        return 2

    # ---------- 任务一：从零进化 ----------
    print("\n########## 任务一：NVDA（演示 搜索→测试→封装→用）##########")
    agent.trajectory = []
    ans1 = agent.run(TASK_1)
    traj1 = list(agent.trajectory)

    created = [t for t in agent.library.list_tools()]
    print(f"\n>>> 任务一结束。当前工具库已封装工具: {[t['name'] for t in created]}")
    print(f">>> 任务一动作轨迹: {traj1}")

    # ---------- 任务二：复用 ----------
    print("\n########## 任务二：AAPL（演示 工具复用）##########")
    agent.trajectory = []
    ans2 = agent.run(TASK_2)
    traj2 = list(agent.trajectory)
    print(f"\n>>> 任务二动作轨迹: {traj2}")

    # ---------- 复用校验 ----------
    reused = (
        "search_tools" in traj2
        and "web_search" not in traj2
        and "create_tool" not in traj2
        and any(t not in {"web_search", "read_webpage", "code_interpreter",
                          "create_tool", "search_tools"} for t in traj2)
    )
    print("\n" + "=" * 70)
    print("结论汇总")
    print("=" * 70)
    print(f"[任务一 · NVDA] {ans1}")
    print(f"[任务二 · AAPL] {ans2}")
    print("-" * 70)
    print(f"任务二是否复用了已创建工具(未重新搜索/创建): {'是 ✅' if reused else '否 ❌'}")
    print(f"  证据：任务二轨迹调用了 search_tools 且未出现 web_search/create_tool。")
    return 0 if reused else 1


if __name__ == "__main__":
    sys.exit(main())
