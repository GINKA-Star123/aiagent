"""Project path definitions placeholder."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
CHARACTER_DIR = DATA_DIR / "characters"
RUNTIME_DIR = DATA_DIR / "runtime"

MEMORY_PREFERENCES_FILE = RUNTIME_DIR / "memory_preferences.json"

# 长期记忆写入审计日志（JSONL 追加写，供用户查看"都记了什么、为什么记"）。
MEMORY_WRITE_AUDIT_FILE = RUNTIME_DIR / "memory_write_audit.jsonl"

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
KNOWLEDGE_PUBLIC_DIR = KNOWLEDGE_DIR / "public"
KNOWLEDGE_CACHE_DIR = CACHE_DIR / "knowledge"

# 知识索引清单文件名。注意这里只放"文件名"，
# 实际路径由 RAGPipeline 依据 docs_index_path.parent 推导，
# 这样测试用 tmp_path 时清单也落在 tmp 里，不会污染生产缓存。
KNOWLEDGE_INDEX_MANIFEST_NAME = "index_manifest.json"
# 生产默认位置，仅用于展示/诊断。
KNOWLEDGE_INDEX_MANIFEST_FILE = KNOWLEDGE_CACHE_DIR / KNOWLEDGE_INDEX_MANIFEST_NAME