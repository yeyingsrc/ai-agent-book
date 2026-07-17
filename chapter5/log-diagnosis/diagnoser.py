"""
diagnoser.py —— 诊断 Agent（真实调用 OpenAI）

两个阶段，均为真实 LLM 调用：
  1) diagnose()        读轨迹集合 + 架构 + PRD -> 结构化问题报告(优先级/模块/描述/建议)
  2) gen_test_cases()  基于问题报告 -> 生成可被 replay.py 自动执行的回归测试用例

模型固定 gpt-4o-mini，输出走 JSON 模式，尽量稳定可解析。
"""

import json
import os
from typing import Dict, Any, List

from openai import OpenAI

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 供 LLM 生成测试用例时使用的断言 DSL 说明（须与 replay.py 保持一致）
_ASSERTION_SPEC = """可用断言类型（assertion.type 只能取以下之一）：
- "step_present"    params: {"tool": <工具名>}                 该工具必须在轨迹中出现
- "tool_succeeds"   params: {"tool": <工具名>}                 该工具最终成功且无"多次失败后误报成功"
- "latency_under"   params: {"tool": <工具名>, "threshold_ms": <整数>}  该工具单次延迟须低于阈值
- "final_status_is" params: {"value": "success"|"failed"}      任务最终状态必须等于给定值"""


class Diagnoser:
    def __init__(self, model: str = MODEL):
        # timeout / max_retries：让偶发的网络/SSL 抖动自动重试，不至于整轮崩溃
        self.client = OpenAI(timeout=60.0, max_retries=3)
        self.model = model

    # ---------- 阶段一：诊断 ----------
    def diagnose(self, architecture: str, prd: str,
                 trajectories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        traj_text = json.dumps(trajectories, ensure_ascii=False, indent=2)
        system = (
            "你是资深的 Agent 系统诊断专家。给定系统架构文档、PRD 与一组生产轨迹，"
            "你要判断每条轨迹的执行流程是否符合架构与 PRD 的要求，识别问题模式、定位到具体模块，"
            "输出结构化问题报告。只报告确有证据的问题，不要臆造。"
        )
        user = f"""# 系统架构
{architecture}

# PRD
{prd}

# 生产轨迹集合（JSON）
{traj_text}

# 任务
逐条核对轨迹与 PRD/架构，找出偏离项。以 JSON 输出，结构：
{{
  "problems": [
    {{
      "title": "一句话问题标题",
      "priority": "P0|P1|P2|P3",
      "module": "涉及的模块名(取架构中的模块)",
      "description": "问题描述，引用具体轨迹与轮次作为证据",
      "suggestion": "可操作的改进建议",
      "trajectory_ids": ["涉及的轨迹ID"],
      "focus_turns": [关键交互轮次的index],
      "prd_ref": "对应的PRD条目(如 R1/R2/R3)",
      "suggested_assignee": "建议负责人(可留空)"
    }}
  ]
}}
只输出 JSON。"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("problems", [])

    # ---------- 阶段二：生成回归测试用例 ----------
    def gen_test_cases(self, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prob_text = json.dumps(problems, ensure_ascii=False, indent=2)
        system = (
            "你是测试工程师。基于诊断出的问题，为每个问题生成一条回归测试用例，"
            "用例引用问题轨迹 ID 与关键交互轮次，并给出一个可被自动重放框架求值的断言。"
        )
        user = f"""# 已诊断的问题
{prob_text}

# 断言 DSL
{_ASSERTION_SPEC}

# 任务
为每个问题生成 1 条回归测试用例。断言应表达"修复后系统应满足的正确行为"
（例如：退款前应出现 verify_refund_eligibility；process_refund 应最终成功；check_stock 延迟应 < 5000ms）。
以 JSON 输出：
{{
  "test_cases": [
    {{
      "test_id": "RT-001",
      "trajectory_id": "引用的问题轨迹ID",
      "focus_turn": 关键轮次index,
      "description": "该用例验证什么",
      "assertion": {{"type": "...", "params": {{...}}}}
    }}
  ]
}}
只输出 JSON。"""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(resp.choices[0].message.content)
        return data.get("test_cases", [])
