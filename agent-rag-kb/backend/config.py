"""
配置模块：多模型切换与设置管理

设计模式：工厂函数 (Factory Pattern)
—— get_llm() 和 get_embeddings() 根据配置返回不同的实现，
    调用方不需要知道具体是哪个 LLM 提供商，只需要调用 get_llm()。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 backend/ 目录的 .env 文件（必须在 import LLM/Embedding 库之前，
# 因为 huggingface_hub 在 import 时就会读取 HF_ENDPOINT 环境变量）
env_path = Path(__file__).resolve().parent / ".env"
if not env_path.exists():
    print(f"[警告] 未找到 .env 文件 (期望路径: {env_path})")
    print(f"       请从 .env.example 复制并填写实际的 API Key")
load_dotenv(env_path)

# 强制设置 HF 镜像（必须在 huggingface_hub 被 import 之前设置，
# load_dotenv 可能未覆盖已存在的值，因此直接设置 os.environ）
_hf_endpoint = os.getenv("HF_ENDPOINT", "")
if _hf_endpoint:
    os.environ["HF_ENDPOINT"] = _hf_endpoint

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings


class Settings:
    """
    应用配置 —— 所有配置项从环境变量读取，支持 .env 文件覆盖。

    为什么用 pydantic-free 的纯 Python 类：
    - 避免引入 pydantic-settings 依赖
    - 学习项目，手动读取环境变量更直观
    - os.getenv 的默认值机制已足够
    """

    def __init__(self):
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")
        self.EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.HUGGINGFACE_MODEL_NAME = os.getenv("HUGGINGFACE_MODEL_NAME", "BAAI/bge-small-zh")
        self.CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))


# 全局单例 —— 整个应用共享一份配置
settings = Settings()


def get_llm():
    """
    LLM 工厂函数 —— 根据 LLM_PROVIDER 返回对应的 ChatModel 实例。

    工厂函数的好处：
    - 调用方不需要 import 具体的模型类
    - 切换模型只需改 .env 文件，不需要改任何代码
    - 新增提供商只需在此函数中添加一个 elif 分支

    temperature 统一设为 settings.LLM_TEMPERATURE（默认 0.0），
    因为在 Agent 工具调用场景中，低 temperature 能减少 LLM
    胡乱调用工具的概率，让决策更可预测。
    """
    temperature = settings.LLM_TEMPERATURE
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        model = settings.LLM_MODEL_NAME or "gpt-4o"
        return ChatOpenAI(model=model, temperature=temperature, api_key=settings.OPENAI_API_KEY)

    elif provider == "deepseek":
        model = settings.LLM_MODEL_NAME or "deepseek-chat"
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

    elif provider == "anthropic":
        model = settings.LLM_MODEL_NAME or "claude-sonnet-4-6"
        return ChatAnthropic(model=model, temperature=temperature, api_key=settings.ANTHROPIC_API_KEY)

    elif provider == "ollama":
        model = settings.LLM_MODEL_NAME or "qwen2.5"
        return ChatOllama(model=model, temperature=temperature, base_url=settings.OLLAMA_BASE_URL)

    else:
        raise ValueError(
            f"不支持的 LLM_PROVIDER: '{settings.LLM_PROVIDER}'。"
            f"可选值: openai, deepseek, anthropic, ollama"
        )


def get_embeddings():
    """
    Embedding 工厂函数 —— 根据 EMBEDDING_PROVIDER 返回对应的 Embeddings 实例。

    支持:
    - openai: OpenAIEmbeddings (付费 API)
    - huggingface: HuggingFaceEmbeddings (本地免费，BGE 中文模型)
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "openai":
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            api_key=settings.OPENAI_API_KEY,
        )

    elif provider == "huggingface":
        # HuggingFace Hub 在国内可能被墙，使用镜像站加速下载
        hf_endpoint = os.getenv("HF_ENDPOINT", "")
        model_kw = {"device": "cpu"}
        if hf_endpoint:
            os.environ.setdefault("HF_ENDPOINT", hf_endpoint)
        return HuggingFaceEmbeddings(
            model_name=settings.HUGGINGFACE_MODEL_NAME,
            model_kwargs=model_kw,
            encode_kwargs={"normalize_embeddings": True},
        )

    else:
        raise ValueError(
            f"不支持的 EMBEDDING_PROVIDER: '{settings.EMBEDDING_PROVIDER}'。"
            f"可选值: openai, huggingface"
        )
