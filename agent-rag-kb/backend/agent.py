"""
Agent 决策循环：手写 while loop，完全透明的工具调用流程。

核心理念（为什么手写而不是用 LangChain AgentExecutor）:
  AgentExecutor 把 tool call → execute → observe → synthesize 循环藏在
  框架内部。对于学习项目，我们要看到每一步：LLM 怎么输出 tool_call？
  工具怎么被调用？结果怎么传回 LLM？答案怎么合成？

  手写约 40 行代码，每个步骤都显式可控，完美满足"学习优先"原则。

决策流程（最多 2 轮）:
  Round 1: LLM 看到用户问题 + System Prompt → 决定是否调用工具
    ├─ 有 tool_call → 执行工具 → 将结果加入消息 → 进入 Round 2
    └─ 无 tool_call → 直接流式输出答案（astream, 逐 token）
  Round 2: LLM 看到检索结果 → 基于文档内容流式合成最终答案
    （此时 tools 已解除绑定，防止 LLM 幻觉多余 tool_call）
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from .config import get_llm
from .rag import create_rag_tool

# 决策日志配置
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# System Prompt: 指导 Agent 的决策规则
# —— Agent 靠 System Prompt 来决定何时用工具、何时直接回答，
#    所以规则必须明确、无歧义。
SYSTEM_PROMPT = """你是一个专业的知识库分析师。用户上传了文档，你需要基于文档内容给出准确、详细的回答。

{tools}

规则：
1. 凡是涉及文档内容、文件信息、或"文档里说了什么"类问题 → 必须先调用 retrieve_documents
2. 通用知识（数学、编程、常识、闲聊）→ 直接回答，不调用工具

回答要求（核心）:
- 简洁直接，像聊天一样自然回答，适当使用换行让内容更清晰
- 直接用文档中的信息回答，不要提"文档""原文""资料""上传"等字眼
- 把检索到的内容当作自己的知识来说，不要暴露信息来源
- 每条要点单独一行，不要挤成一大段
- 信息不足时直接说"未找到相关信息"
- 始终用中文回答"""


def log_decision(session_id: str, question: str, tool_call: dict) -> None:
    """
    记录 Agent 的每次工具调用决策到 JSON Lines 文件。

    日志格式: 每行一个 JSON 对象，字段包括:
    - timestamp: ISO 8601 UTC 时间
    - session_id: 会话标识
    - question: 用户问题
    - tool_name: 调用的工具名
    - tool_args: 传给工具的参数

    这些日志用于验收标准 AC2 的验证:
    "用 8 题测试集检查 Agent 决策正确率 ≥ 7/8"
    """
    log_path = LOG_DIR / f"decisions_{session_id}.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "question": question,
        "tool_name": tool_call.get("name", "unknown"),
        "tool_args": tool_call.get("args", {}),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def run_agent(question: str, session_id: str) -> AsyncGenerator[str, None]:
    """
    Agent 主循环 —— 异步生成器，逐 token yield SSE JSON 事件。

    参数:
    - question: 用户输入的问题
    - session_id: 会话 ID（决定查询哪个 Chroma collection）

    Yields:
    - data: {"type": "thinking"|"tool_call"|"answer"|"done"|"error", "content": "..."}
    - 每个 yield 是一个完整的 SSE 数据帧
    """
    llm = get_llm()

    # 为当前 session 创建 RAG 工具（scoped to session's Chroma collection）
    tools = [create_rag_tool(session_id)]
    # bind_tools: 将工具定义注入 LLM，LLM 会在需要时输出 tool_call JSON
    # —— 这是 LangChain 唯一帮我们做的事（处理不同提供商的 tool format）
    llm_with_tools = llm.bind_tools(tools)

    # 构建初始消息：System Prompt（含工具说明）+ 用户问题
    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description}" for t in tools
    )
    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(tools=tool_descriptions)),
        HumanMessage(content=question),
    ]

    # 通知前端 Agent 开始思考
    yield "data: " + json.dumps({"type": "thinking", "content": "正在思考..."}) + "\n\n"

    # ── Round 1: LLM 决定是否需要调用工具 ──
    # 必须用 ainvoke（完整响应）而非 astream（流式）：
    # tool_calls 只在完整 AIMessage 中可用，流式 chunk 不包含。
    try:
        response = await llm_with_tools.ainvoke(messages)
    except Exception as e:
        yield "data: " + json.dumps(
            {"type": "error", "content": f"LLM 调用失败: {e}"}
        ) + "\n\n"
        return
    messages.append(response)

    if response.tool_calls:
        # LLM 决定使用工具 → 执行工具并记录决策
        tool_call = response.tool_calls[0]
        log_decision(session_id, question, tool_call)

        yield "data: " + json.dumps(
            {"type": "tool_call", "content": "正在搜索文档..."}
        ) + "\n\n"

        # 执行工具（检索文档）
        # 使用 ainvoke 避免阻塞 asyncio event loop
        try:
            tool_result = await tools[0].ainvoke(tool_call["args"])
        except Exception as e:
            yield "data: " + json.dumps(
                {"type": "error", "content": f"检索失败: {e}"}
            ) + "\n\n"
            return

        # 将工具执行结果加入消息历史
        messages.append(
            ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
        )

        # ── Round 2: 基于检索结果流式合成答案 ──
        # 关键：解除 tools 绑定！只用纯 llm（无工具），
        # 防止 LLM 在合成阶段幻觉出多余的 tool_call，导致无限循环。
        synthesis_llm = llm
        async for chunk in synthesis_llm.astream(messages):
            if chunk.content:
                yield "data: " + json.dumps(
                    {"type": "answer", "content": chunk.content}
                ) + "\n\n"
        yield "data: " + json.dumps({"type": "done", "content": ""}) + "\n\n"

    else:
        # LLM 认为不需要工具 → 直接流式回答
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield "data: " + json.dumps(
                    {"type": "answer", "content": chunk.content}
                ) + "\n\n"
        yield "data: " + json.dumps({"type": "done", "content": ""}) + "\n\n"


async def ask_agent(question: str, session_id: str) -> AsyncGenerator[str, None]:
    """
    对外暴露的简洁接口 —— 与 run_agent 相同，名字更语义化。

    用法:
        async for event in ask_agent("这份文档讲了什么？", "abc123"):
            # event 是 SSE 格式的字符串: data: {json}\n\n
            yield event
    """
    async for event in run_agent(question, session_id):
        yield event
