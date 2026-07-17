# use-computer-while-calling · 双 Agent 架构（电话 + Computer Use）

> **📦 完整代码位于独立仓库：[`git@github.com:19PINE-AI/TalkAct`](https://github.com/19PINE-AI/TalkAct)**
>
> 本示例已发展为一个持续维护的独立研究项目 **TalkAct**（Duplex Voice + Computer-Use Agent）。
> 由于体积较大（内含 vendored 依赖、模型与实验数据），本书主仓库不再内置其源码，请按下方指引单独获取：
>
> ```bash
> git clone git@github.com:19PINE-AI/TalkAct.git
> # 或使用 HTTPS
> git clone https://github.com/19PINE-AI/TalkAct.git
> ```
>
> 环境搭建、运行方式与最新进展以 TalkAct 仓库中的文档为准。

---

## 项目简介

本项目实现了**电话呼叫 Agent** 与 **Computer Use Agent** 的双 Agent 协作架构：两个 Agent 通过 WebSocket 直接通信、无需协调器，并行完成同时需要语音交互和网页操作的复杂任务。

核心动机：Computer-use 模型每一步"感知—思考—行动"需要 3–10 秒（截图 token + 长上下文 + 工具调用），而自然的语音对话要求首字响应 ≲1 秒。单个模型无法同时兼顾两者，因此将其**解耦**——一个快速对话模型负责语音通道，一个慢速 computer-use 模型负责浏览器，二者通过消息桥保持一致。

## 架构概览

```
┌─────────────────┐                    ┌──────────────────┐
│   Phone Call    │◄──────WebSocket────►│  Computer Use    │
│     Agent       │                    │     Agent        │
│ - 语音 I/O       │                    │ - 浏览器自动化    │
│ - ASR / TTS     │                    │ - Browser-Use    │
│ - LLM 对话       │                    │ - 网页抓取        │
└────────┬────────┘                    └────────┬─────────┘
         │                                      │
    ┌────▼──────────────────────────────────────▼────┐
    │                Frontend (Browser)              │
    │            音频采集与播放 · UI 控制             │
    └────────────────────────────────────────────────┘
```

## 关键设计

- **直接 Agent 间通信**：两个 Agent 通过 WebSocket 直接交换消息，而非经由中央协调器；来自对方的消息以带特殊前缀的 user message 形式注入各自上下文。
- **标准工具调用传递消息**：Agent 间通信复用标准的 tool call 机制，无需自定义协议。
- **并行操作**：电话 Agent 实时处理语音对话，计算机 Agent 同时执行浏览器自动化，二者互不阻塞。

## 架构组件

- **Phone Call Agent**：语音 I/O、ASR/TTS、LLM 对话
- **Computer Use Agent**：浏览器自动化（browser-use）、网页抓取
- **WebSocket 通信**：Agent 间直接消息传递

**核心概念**：多 Agent 协作、Agent 间通信、并行任务处理、语音 + 浏览器集成
