"""Detection of explicit subagent requests in chat messages and the chosen delegate role."""

import pytest

from vera_agent.server.routes.chat import _explicit_subagent_request


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("请调用审查子智能体，审查 calc.py", "delegate_review"),
        ("请创建 reviewer 子代理", "delegate_review"),
        ("start a reviewer subagent", "delegate_review"),
        ("让审查员执行一次审查", "delegate_review"),
        ("请启动研究子智能体，调研 pkg 目录", "delegate_research"),
        ("让研究员看看依赖关系", "delegate_research"),
        ("请调用子智能体分析代码", "delegate_research"),
        ("不要创建子智能体，直接回答", None),
        ("审查一下这段代码", None),
        ("帮我 review 这个函数", None),
    ],
)
def test_explicit_subagent_request(message: str, expected: str | None):
    assert _explicit_subagent_request(message) == expected
