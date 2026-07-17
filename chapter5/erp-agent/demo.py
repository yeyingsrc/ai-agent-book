"""
实验 5-10：自然语言交互的 ERP Agent（NL -> SQL，artifact 模式）

运行流程：
  1) 用固定随机种子生成可复现的种子数据，建 SQLite 内存库并灌入；
  2) 对每个自然语言问题：
     Agent 生成 SQL（制品）-> 系统执行 SQL -> 返回结果表；
  3) 用独立的 Python 参考实现算出期望答案，与 SQL 执行结果比对，打印 通过/不通过；
  4) 打印总通过率。

用法：
  export OPENAI_API_KEY=sk-...
  python demo.py
"""

import os
import sqlite3
import sys
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import seed
import reference
from questions import QUESTIONS
from agent import SQLAgent


# ---------------- 结果比对 ----------------
def _norm(v):
    """把单个值归一化为 ('n', 数值) 或 ('s', 字符串)，便于容差比对。"""
    if isinstance(v, bool):
        return ("n", float(v))
    if isinstance(v, (int, float)):
        return ("n", round(float(v), 2))
    return ("s", str(v).strip())


def _row_match(a, b, tol):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x[0] != y[0]:
            return False
        if x[0] == "n":
            if abs(x[1] - y[1]) > tol:
                return False
        else:
            if x[1] != y[1]:
                return False
    return True


def compare(expected, actual, tol=0.1):
    """按多重集合（忽略行顺序）比对期望与实际结果，数值带容差。"""
    exp = [tuple(_norm(v) for v in r) for r in expected]
    act = [tuple(_norm(v) for v in r) for r in actual]
    if len(exp) != len(act):
        return False, f"行数不一致：期望 {len(exp)} 行，实际 {len(act)} 行"
    remaining = list(act)
    for er in exp:
        for i, ar in enumerate(remaining):
            if _row_match(er, ar, tol):
                remaining.pop(i)
                break
        else:
            return False, f"缺少匹配行：{_readable(er)}"
    return True, "结果一致"


def _readable(norm_row):
    return tuple(v[1] for v in norm_row)


# ---------------- 结果表打印 ----------------
def print_table(rows, max_rows=12):
    if not rows:
        print("    (空结果)")
        return
    for r in rows[:max_rows]:
        cells = []
        for v in r:
            if isinstance(v, float):
                cells.append(f"{v:.2f}")
            else:
                cells.append(str(v))
        print("    | " + " | ".join(cells) + " |")
    if len(rows) > max_rows:
        print(f"    ... 共 {len(rows)} 行")


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("请先设置 OPENAI_API_KEY 环境变量（可复制 env.example 为 .env）。")
        sys.exit(1)

    today = date.today()

    # 1) 生成种子数据 + 建库
    employees, salaries = seed.generate(today)
    conn = sqlite3.connect(":memory:")
    seed.create_db(conn, employees, salaries)

    print("=" * 70)
    print(f"ERP Agent 实验 5-10  |  模型：{os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}")
    print(f"今天：{today.isoformat()}  |  员工 {len(employees)} 人，工资记录 {len(salaries)} 条")
    print("=" * 70)

    agent = SQLAgent()
    passed = 0

    for q in QUESTIONS:
        qid, nl, hint = q["id"], q["nl"], q["hint"]
        print(f"\n【问题 {qid}】{nl}")

        # 2) Agent 生成 SQL（制品）
        try:
            sql = agent.generate_sql(nl, hint)
        except Exception as e:
            print(f"  [Agent 生成 SQL 失败] {e}")
            continue
        print("  生成的 SQL：")
        for line in sql.splitlines():
            print("    " + line)

        # 3) 系统执行 SQL
        try:
            cur = conn.cursor()
            cur.execute(sql)
            actual = cur.fetchall()
        except Exception as e:
            print(f"  [SQL 执行出错] {e}")
            print("  结果：不通过 ✗")
            continue

        print("  查询结果：")
        print_table(actual)

        # 4) 与参考实现比对
        expected = reference.REFERENCE[qid](employees, salaries, today)
        ok, msg = compare(expected, actual)
        if ok:
            passed += 1
            print(f"  校验：通过 ✓（{msg}）")
        else:
            print(f"  校验：不通过 ✗（{msg}）")
            print(f"       参考期望：{[tuple(r) for r in expected][:12]}")

    print("\n" + "=" * 70)
    print(f"总通过率：{passed}/{len(QUESTIONS)}  ({passed / len(QUESTIONS) * 100:.0f}%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
