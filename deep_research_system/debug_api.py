"""Debug API call."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.schemas.task import ResearchRequest, TaskSpec

# 模拟 API 请求
request = ResearchRequest(
    query="测试查询",
    task_type="industry_report",
    depth="standard",
    budget_level="medium",
    max_sources=20
)

print("ResearchRequest created:")
print(f"  query: {request.query}")
print(f"  task_type: {request.task_type}")

# 转换为 dict
data = request.model_dump()
print("\nAfter model_dump():")
print(f"  data: {data}")

# 转换字段
data["user_query"] = data.pop("query", "")
print("\nAfter converting query -> user_query:")
print(f"  data: {data}")

# 尝试创建 TaskSpec
try:
    task = TaskSpec(task_id="task_test", **data)
    print("\nTaskSpec created successfully!")
    print(f"  task_id: {task.task_id}")
    print(f"  user_query: {task.user_query}")
except Exception as e:
    print(f"\nError creating TaskSpec: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
