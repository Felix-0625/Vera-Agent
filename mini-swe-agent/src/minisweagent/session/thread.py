"""ThreadSession 实体与上下文交接接口抽象。

负责收拢 Agent 对话消息生命周期、统计指标与持久化，并提供跨窗口/子 Agent 间
的上下文交接简报（Handover Summary）导出能力。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any
import uuid


@dataclass
class ThreadSession:
    """轻量级会话实体。

    统一管理单次对话/窗口内的全量状态：
    - 唯一标识（thread_id, parent_thread_id, group_id）
    - 角色设定（role: main / researcher / reviewer 等）
    - 消息历史轨迹（messages）
    - 资源消耗统计（cost, n_calls）
    - 上下文交接与快照存盘能力
    """

    thread_id: str = field(default_factory=lambda: f"th_{uuid.uuid4().hex[:12]}")
    role: str = "main"
    parent_thread_id: str | None = None
    group_id: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)
    cost: float = 0.0
    n_calls: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_messages(self, *messages: dict) -> list[dict]:
        """向会话追加多条消息，并自动刷新最近更新时间。"""
        new_msgs = list(messages)
        self.messages.extend(new_msgs)
        self.updated_at = time.time()
        return new_msgs

    def add_cost(self, amount: float) -> None:
        """累加当前会话的模型调用开销。"""
        self.cost += max(0.0, amount)

    def increment_calls(self) -> None:
        """模型调用次数自增。"""
        self.n_calls += 1

    def get_touched_files(self) -> list[dict[str, str]]:
        """从历史消息动作中扫描并提取涉及变动或读取的文件清单。

        返回列表，每个元素形如：{"path": "foo/bar.py", "action": "read"|"write"|"edit"}
        """
        seen_paths: set[str] = set()
        touched: list[dict[str, str]] = []

        for msg in self.messages:
            # 扫描 message['extra']['actions']
            actions = msg.get("extra", {}).get("actions", [])
            for act in actions:
                path = act.get("path")
                tool = act.get("tool_name") or ("bash" if "command" in act else "unknown")
                if path and path not in seen_paths:
                    seen_paths.add(path)
                    touched.append({"path": str(path), "action": tool})

        return touched

    def get_last_assistant_text(self) -> str:
        """获取最近一次 Assistant 生成的文本总结或答复。"""
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant":
                content = msg.get("content")
                if content and isinstance(content, str):
                    return content.strip()
                elif isinstance(content, list):
                    # 处理多模态或 block content
                    texts = [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item]
                    if texts:
                        return "\n".join(texts).strip()
            elif msg.get("role") == "exit":
                sub = msg.get("extra", {}).get("submission") or msg.get("content", "")
                if sub:
                    return str(sub).strip()
        return ""

    def export_handover_summary(
        self,
        target_role: str = "main",
        extra_notes: str = "",
    ) -> str:
        """生成 Markdown 格式的结构化上下文交接简报（Handover Summary）。

        核心目的：
        1. 避免长上下文窗口信息膨胀导致模型认知污染或幻觉；
        2. 为 Subagent（如调研员）向主 Agent 汇报，或主 Agent 向审查员交接提供统一格式协议。
        """
        touched_files = self.get_touched_files()
        last_text = self.get_last_assistant_text()
        created_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))

        lines = [
            "# 上下文交接简报 (Handover Summary)",
            "",
            "## 一、源会话元数据 (Source Metadata)",
            f"- **会话 ID (thread_id)**: `{self.thread_id}`",
            f"- **发起角色 (Source Role)**: `{self.role}`",
            f"- **目标角色 (Target Role)**: `{target_role}`",
            f"- **创建时间**: {created_time_str}",
            f"- **消耗统计**: API 调用 {self.n_calls} 次 | 累计成本 ${self.cost:.4f}",
        ]

        if self.parent_thread_id:
            lines.append(f"- **父级会话 (Parent)**: `{self.parent_thread_id}`")
        if self.group_id:
            lines.append(f"- **所属工作组 (Group)**: `{self.group_id}`")

        lines.extend([
            "",
            "## 二、涉及文件清单 (Touched Files)",
        ])

        if touched_files:
            for item in touched_files:
                lines.append(f"- `[{item['action']}]` {item['path']}")
        else:
            lines.append("- *(本次会话未直接触发读写基元文件变动)*")

        lines.extend([
            "",
            "## 三、核心交付与结论提炼 (Key Findings & Output)",
        ])

        if last_text:
            lines.append(last_text)
        else:
            lines.append("- *(无明确最终结论输出)*")

        if extra_notes:
            lines.extend([
                "",
                "## 四、移交附注与待办 (Handover Notes & Next Steps)",
                extra_notes.strip(),
            ])

        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict[str, Any]:
        """将当前会话序列化为字典结构。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThreadSession:
        """从字典反序列化创建 ThreadSession 实体。"""
        filtered = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**filtered)

    def save(self, file_path: Path | str) -> Path:
        """将会话状态完整保存为 JSON 文件。"""
        path = Path(file_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, file_path: Path | str) -> ThreadSession:
        """从磁盘 JSON 快照恢复 ThreadSession 实体。"""
        path = Path(file_path).resolve()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)
