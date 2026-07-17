"""
实验 3-13 全流程演示：从司法判例中提取隐性知识 -> 因子重要性建模 -> 对话式量刑建议。

运行：
    python demo.py

依次执行：
  阶段 1  对合成判例数据集做 LLM 结构化抽取（带缓存），并给出抽取准确率；
  阶段 2  用(抽取因子 -> 刑期)样本拟合因子重要性模型，打印权重排序与拟合优度；
  阶段 3  对话 Agent 处理一个新案情：先追问缺失的重要因子，补全后给出引用关键因子的量刑建议。
"""
import json
import os
import sys

from advisor_agent import LegalAdvisorAgent
from extractor import extract_dataset, extraction_accuracy
from factor_model import print_importance, train


def section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main():
    # ---------- 阶段 1：结构化知识抽取 ----------
    section("阶段 1 / 结构化知识抽取（LLM 从判例文本抽取因子）")
    results = extract_dataset(use_cache=True, verbose=True)

    print("\n抽取样例（前 2 条，对比 gold 真值）:")
    for r in results[:2]:
        print(f"\n[{r['id']}] {r['fact'][:60]}...")
        print(f"  抽取: {json.dumps(r['extracted'], ensure_ascii=False)}")
        print(f"  真值: {json.dumps(r['gold'], ensure_ascii=False)}")

    acc = extraction_accuracy(results)
    print("\n各字段抽取准确率(对比 gold):")
    for k, v in acc.items():
        print(f"  {k:<14} {v*100:5.1f}%")

    # ---------- 阶段 2：因子重要性建模 ----------
    section("阶段 2 / 因子重要性建模（回归学出可解释的判决经验模型）")
    model = train(results, save=True)
    print_importance(model)
    print(f"\n  判决经验模型已保存 -> {os.path.join('data', 'factor_model.json')}")

    # ---------- 阶段 3：对话式量刑建议 Agent ----------
    section("阶段 3 / 对话式量刑建议 Agent")
    agent = LegalAdvisorAgent(model)

    # 用户第一轮：信息不完整（未提金额、是否退赃等）
    user_turn1 = (
        "我朋友之前因为盗窃被判过刑，这次他撬门进了别人家里偷东西，被抓的时候没反抗。"
        "这种情况大概会判多久？"
    )
    print(f"\n用户: {user_turn1}")
    known = agent.extract_known(user_turn1)
    print(f"\nAgent 已识别因子: {json.dumps(known, ensure_ascii=False)}")

    questions = agent.missing_important_questions(known)
    print("\nAgent 追问（按因子重要性排序，只问缺失且重要的）:")
    for q in questions[:5]:
        print(f"  - [{q['name_cn']} 权重{q['weight']:+.2f}] {q['question']}")

    # 用户第二轮：补全关键信息
    user_turn2 = (
        "补充一下：这次偷的东西价值大概 5 万元，事后他没有退赃，"
        "作案时也没带凶器，是他一个人干的，到了法庭上他认罪认罚了。"
    )
    print(f"\n用户: {user_turn2}")
    known2 = agent.extract_known(user_turn1 + " " + user_turn2)
    print(f"\nAgent 更新后的因子: {json.dumps(known2, ensure_ascii=False)}")

    print("\nAgent 量刑建议:\n")
    print(agent.advise(known2))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        # 常见于未配置 OPENAI_API_KEY：给出清晰提示而非原始堆栈。
        print(f"启动失败：{exc}", file=sys.stderr)
        sys.exit(1)
