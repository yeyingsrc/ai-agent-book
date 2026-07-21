#!/usr/bin/env python3
"""Chapter 8 figures — Agent 的自我进化.

NOTE: this generator was previously a stray copy of chapter 9's figures, which
left fig8-1..fig8-7 showing chapter-9 content. It has been rewritten so each
figure matches its caption in chapter8.md. Figures are built with svg_lib;
titles live in the body text (svg_lib strips in-figure titles).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_lib import SVG, FS_SMALL, FS_TINY, FS_BODY

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')


def _pipeline(stages, fname, W=880, feedback=None):
    """Horizontal stage pipeline with an optional dashed feedback loop."""
    n = len(stages)
    bw = min(190, (W - 40 - (n - 1) * 22) // n)
    bh, gap = 84, 22
    H = 234 if feedback else 174   # +24 for the 40px title-crop margin
    s = SVG(W, H)
    x0 = (W - (n * bw + (n - 1) * gap)) / 2
    y = 48                          # start below the TITLE_CROP_PX=40 line
    pos = []
    for i, (lab, sub) in enumerate(stages):
        x = x0 + i * (bw + gap)
        s.box(x, y, bw, bh, lab, sublabel=sub, bold=True, fill='light')
        pos.append(x)
        if i > 0:
            s.arrow(pos[i - 1] + bw + 2, y + bh / 2, x - 2, y + bh / 2)
    if feedback:
        lx = pos[-1] + bw / 2
        fx = pos[0] + bw / 2
        ry = y + bh + 34
        s.line(lx, y + bh, lx, ry, dash=True)
        s.line(lx, ry, fx, ry, dash=True)
        s.arrow(fx, ry, fx, y + bh + 2, dash=True)
        s.text((lx + fx) / 2, ry + 18, feedback, size=FS_SMALL, fill='text_light')
    s.save(os.path.join(OUT, fname + '.svg'))


def fig8_1():  # 外部化学习循环
    _pipeline([("完成任务", "产生原始经验"), ("提炼经验", "总结·压缩·结构化"),
               ("存入外部系统", "知识库/工具，可检索"), ("检索复用", "下次任务调用")],
              'fig8-1', feedback="经验持续沉淀，跨会话复用")


def fig8_2():  # GAIA 经验学习系统
    _pipeline([("成功轨迹", "完成任务的过程"), ("策略总结", "提炼为知识摘要"),
               ("知识摘要库", "建立语义索引"), ("检索注入", "Agent 决策时取用")],
              'fig8-2', feedback="相似任务复用历史经验")


def fig8_3():  # Agent 自我进化流水线（需求识别→工具搜索→代码封装→工具注册）
    _pipeline([("① 需求识别", "现有工具不足"), ("② 工具搜索", "开放世界查找"),
               ("③ 代码封装", "生成并封装"), ("④ 工具注册", "纳入库可复用")],
              'fig8-3', feedback="新工具注册后可被后续任务复用，持续扩展能力边界")


def fig8_4():  # Voyager 持续学习架构（课程生成器 + 技能库 + 迭代提示）
    _pipeline([("课程生成器", "提出渐进式新任务"), ("迭代提示机制", "生成并调试技能代码"),
               ("技能库", "存储可复用技能")],
              'fig8-4', W=760, feedback="技能积累后解锁更难的任务（开放世界探索）")


def fig8_5():  # 实验 8-4 自我进化流水线（搜索→评估→测试→封装→复用）
    _pipeline([("① 搜索", "开放网络找工具"), ("② 评估", "判断是否合适"), ("③ 测试", "验证可用性"),
               ("④ 封装", "包成标准工具"), ("⑤ 复用", "纳入工具库")],
              'fig8-5', W=940, feedback="新工具沉淀后供后续任务复用")


if __name__ == '__main__':
    for fn in (fig8_1, fig8_2, fig8_3, fig8_4, fig8_5):
        fn()
        print('saved', fn.__name__)
