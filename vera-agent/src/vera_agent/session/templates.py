"""Built-in multi-agent topology templates.

Every template must be runnable by the run scheduler: organizations
(`topology_type == "architecture"`) are reporting trees, workflows are acyclic
graphs with a single start node (checked by tests/server/test_builtin_templates.py).

- supervisor_dev: organization, a lead managing an implementer and a reviewer
- sequential_workflow: workflow, research -> design -> implement -> test
- adversarial_audit: workflow, implement -> red-team review
- swarm_mesh: workflow, backend contract first, then frontend and QA; QA joins both

Node prompts are product content in Chinese and use `{{goal}}` as the
placeholder for the project goal.
Custom templates saved by users are plain JSON (see server/routes/groups.py).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NodeBlueprint(BaseModel):
    """Blueprint defining an agent window within a topology."""

    role_key: str
    title: str
    role: str
    responsibilities: list[str] = Field(default_factory=list)
    prompt_template: str
    allowed_tools: list[str] = Field(default_factory=list)


class EdgeBlueprint(BaseModel):
    """Blueprint defining directed coordination between agent windows."""

    source_role: str
    target_role: str
    relation: str = "connected_to"


class TopologyTemplate(BaseModel):
    """Declarative blueprint for one-click multi-agent group provisioning."""

    template_id: str
    name: str
    description: str
    topology_type: str
    nodes: list[NodeBlueprint]
    edges: list[EdgeBlueprint]


BUILTIN_TEMPLATES: dict[str, TopologyTemplate] = {
    "supervisor_dev": TopologyTemplate(
        template_id="supervisor_dev",
        name="Supervisor 主管敏捷研发架构",
        description="组织架构：1 位技术主管统筹需求并向实施员、测试员分派任务，下级完成后由主管复核汇总。",
        topology_type="architecture",
        nodes=[
            NodeBlueprint(
                role_key="supervisor",
                title="技术架构主管",
                role="supervisor",
                responsibilities=[
                    "深入理解用户业务总目标并制定总体技术方案",
                    "将复杂任务拆解为清晰的子任务并委派给实施员",
                    "审核测试员报告并向用户做最终交付汇总",
                ],
                prompt_template=(
                    "你是技术架构主管。当前团队总业务目标为：\n{{goal}}\n\n"
                    "你的核心职责是：分析总体架构、制定技术路线，将实施任务派发给实施员，并汇总验收测试结果。\n"
                    "你的输出会作为任务交给实施员和测试审查员。"
                ),
                allowed_tools=["read", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="implementer",
                title="核心功能实施员",
                role="implementer",
                responsibilities=[
                    "根据主管的架构方案编写业务核心代码",
                    "修改与新增相关源文件",
                    "编写初步的单元测试确保逻辑自洽",
                ],
                prompt_template=(
                    "你是核心功能实施工程师。当前团队总业务目标为：\n{{goal}}\n\n"
                    "你的核心职责是：严格按照主管的架构要求编写高质量、交付级代码，"
                    "使用 write/edit 工具修改文件，完成自测后提交给审查测试员进行评审。"
                ),
                allowed_tools=["read", "write", "edit", "bash", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="reviewer",
                title="测试与质量审查员",
                role="reviewer",
                responsibilities=[
                    "执行对抗性静态语法检查与单测回归",
                    "审查实施员提交的代码改动是否存在漏洞或规范问题",
                    "列出明确的整改待办清单 (Action Items) 或放行",
                ],
                prompt_template=(
                    "你是质量与测试审查员。当前团队总业务目标为：\n{{goal}}\n\n"
                    "你的核心职责是：对实施员提交的代码改动进行严格质检，运行单测与 check_syntax，"
                    "确保零测试失败和零语法错误，列出明确的整改清单或放行结论。"
                ),
                allowed_tools=["read", "check_syntax", "symbol_search", "bash"],
            ),
        ],
        edges=[
            EdgeBlueprint(source_role="supervisor", target_role="implementer", relation="manages"),
            EdgeBlueprint(source_role="supervisor", target_role="reviewer", relation="manages"),
        ],
    ),
    "sequential_workflow": TopologyTemplate(
        template_id="sequential_workflow",
        name="Sequential Workflow 顺序流水线架构",
        description="标准线性交付链路：需求调研 -> 方案设计 -> 代码实现 -> 集成测试，阶段式递进消除上下文膨胀。",
        topology_type="workflow",
        nodes=[
            NodeBlueprint(
                role_key="analyst",
                title="需求与代码调研员",
                role="researcher",
                responsibilities=[
                    "检索代码库依赖与现有实现",
                    "排查关键调用栈与重构难点",
                    "输出分析报告交接给设计架构师",
                ],
                prompt_template=(
                    "你是需求与代码调研专家。当前项目总目标：\n{{goal}}\n\n"
                    "你的核心职责是：纯只读检索现有代码库，找出所有受影响的文件与潜在瓶颈，"
                    "提炼出 Handover 交付物移交给架构师。"
                ),
                allowed_tools=["read", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="architect",
                title="系统方案架构师",
                role="architect",
                responsibilities=[
                    "根据调研结论设计模块接口与数据模型",
                    "制定模块划分与改动规范清单",
                ],
                prompt_template=(
                    "你是系统方案架构师。当前项目总目标：\n{{goal}}\n\n"
                    "根据调研员成果，制定具体的接口契约、类设计与目录结构，输出实施指南移交给开发员。"
                ),
                allowed_tools=["read", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="developer",
                title="功能实现开发员",
                role="implementer",
                responsibilities=[
                    "依据架构方案落地代码修改",
                    "编写核心业务代码与单测",
                ],
                prompt_template=(
                    "你是功能开发员。当前项目总目标：\n{{goal}}\n\n"
                    "按照架构师的方案进行物理编码，使用 write/edit 工具修改文件，完成后移交给测试员。"
                ),
                allowed_tools=["read", "write", "edit", "bash", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="tester",
                title="集成验收测试员",
                role="tester",
                responsibilities=[
                    "运行全量回归单测与端到端用例",
                    "验证功能是否完全达成总目标",
                ],
                prompt_template=(
                    "你是集成验收测试员。当前项目总目标：\n{{goal}}\n\n"
                    "运行 pytest 与测试脚本，核验所有验收标准是否达成，产出最终交付验收报告。"
                ),
                allowed_tools=["read", "bash", "check_syntax"],
            ),
        ],
        edges=[
            EdgeBlueprint(source_role="analyst", target_role="architect", relation="handoff_to"),
            EdgeBlueprint(source_role="architect", target_role="developer", relation="handoff_to"),
            EdgeBlueprint(source_role="developer", target_role="tester", relation="handoff_to"),
        ],
    ),
    "adversarial_audit": TopologyTemplate(
        template_id="adversarial_audit",
        name="Adversarial 对抗审查与安全博弈架构",
        description="工作流：实施员先完成修改，再由红队审查员做一轮对抗审查；需要多轮返工时可在编辑器中加入循环节点。",
        topology_type="workflow",
        nodes=[
            NodeBlueprint(
                role_key="implementer",
                title="特性实施工程师",
                role="implementer",
                responsibilities=[
                    "实现业务重构与高危修改",
                    "针对审查员提出的缺陷快速修改补正",
                ],
                prompt_template=(
                    "你是特性实施工程师。当前重构目标：\n{{goal}}\n\n"
                    "完成代码修改并说明改动点与自测结果，结果会交给红队审查员。"
                ),
                allowed_tools=["read", "write", "edit", "bash", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="critic",
                title="红队对抗审查员",
                role="reviewer",
                responsibilities=[
                    "严苛审查所有 Diff 差异与边缘情况",
                    "模拟异常入参，主动挖掘潜在漏洞与回归风险",
                ],
                prompt_template=(
                    "你是严苛的红队对抗审查专家。当前审查目标：\n{{goal}}\n\n"
                    "以极其批判的视角审视实施员的代码，检查边界异常、SQL/命令注入、性能陷阱与覆盖率缺失。"
                ),
                allowed_tools=["read", "check_syntax", "symbol_search", "bash"],
            ),
        ],
        edges=[
            EdgeBlueprint(source_role="implementer", target_role="critic", relation="submits_code"),
        ],
    ),
    "swarm_mesh": TopologyTemplate(
        template_id="swarm_mesh",
        name="全栈协同工作流",
        description="工作流：后端先确定接口契约，前端据此实现，测试专家汇合前后端结果做全链路验证。",
        topology_type="workflow",
        nodes=[
            NodeBlueprint(
                role_key="backend_dev",
                title="后端服务专家",
                role="backend",
                responsibilities=["负责后端核心 API、业务逻辑与数据存储"],
                prompt_template="你是后端专家。当前目标：{{goal}}。先给出接口契约，再实现 REST/SSE 接口与持久化层。",
                allowed_tools=["read", "write", "edit", "bash", "symbol_search"],
            ),
            NodeBlueprint(
                role_key="frontend_dev",
                title="前端界面专家",
                role="frontend",
                responsibilities=["负责前端 UI/UX 与客户端接口联调"],
                prompt_template="你是前端专家。当前目标：{{goal}}。按后端给出的接口契约编写前端界面。",
                allowed_tools=["read", "write", "edit", "bash"],
            ),
            NodeBlueprint(
                role_key="qa_dev",
                title="全链路测试专家",
                role="qa",
                responsibilities=["联调验证全流程业务通路"],
                prompt_template="你是全链路测试专家。当前目标：{{goal}}。验证前后端闭环并把关系统稳定性。",
                allowed_tools=["read", "bash"],
            ),
        ],
        edges=[
            EdgeBlueprint(source_role="backend_dev", target_role="frontend_dev", relation="api_contract"),
            EdgeBlueprint(source_role="backend_dev", target_role="qa_dev", relation="submits_to"),
            EdgeBlueprint(source_role="frontend_dev", target_role="qa_dev", relation="submits_to"),
        ],
    ),
}


def list_topology_templates() -> list[dict[str, Any]]:
    """Return serialized list of all built-in templates for UI selection."""
    return [tpl.model_dump() for tpl in BUILTIN_TEMPLATES.values()]


def get_topology_template(template_id: str) -> TopologyTemplate | None:
    """Retrieve a template blueprint by its identifier."""
    return BUILTIN_TEMPLATES.get(template_id)
