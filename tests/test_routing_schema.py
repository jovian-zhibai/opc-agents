"""routing.yaml 结构校验：单一真相源必须保持结构合法、agent 引用有效、ID 唯一。

本测试作为 quality-gate.sh 的补充——quality-gate 检查 prompts/ 与 .opencode/agents/ 的
引用一致性，本测试锁住 routing.yaml 自身的结构契约，防止改坏归属表。
"""

import os
import re

import pytest
import yaml

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTING_YAML = os.path.join(PROJECT_DIR, "routing.yaml")

# 合法 agent 集合：与 prompts/（及 .opencode/agents/）一致（连字符小写形式）
VALID_AGENTS = {
    "director", "advisor", "dev", "product", "ui-ux", "qa",
    "guardian", "growth", "finance", "agent-manager",
}


@pytest.fixture(scope="module")
def routing():
    with open(ROUTING_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _normalize_agent(value):
    """routing.yaml 中 agent 字段可能为 str 或 list。

    统一归一化为 prompts 文件名风格（连字符小写）：
    - AgentManager → agent-manager（驼峰转连字符）
    - UI-UX → ui-ux（已有连字符，转小写）
    """
    def to_snake(a):
        a = a.strip()
        if "-" in a:
            return a.lower()
        # 全大写缩写（如 QA、UI）直接小写，不拆连字符
        if a.isupper():
            return a.lower()
        return re.sub(r"(?<!^)(?=[A-Z])", "-", a).lower()

    if isinstance(value, str):
        return {to_snake(value)}
    if isinstance(value, list):
        return {to_snake(str(v)) for v in value}
    return set()


class TestTopLevel:
    def test_top_level_keys(self, routing):
        for key in ("version", "description", "exemptions", "routes",
                    "fallback", "skill_routes", "mcp_routes"):
            assert key in routing, f"routing.yaml 缺少顶层键: {key}"

    def test_version_is_string(self, routing):
        assert isinstance(routing["version"], str) and routing["version"]

    def test_fallback_is_director_intent(self, routing):
        assert routing["fallback"] == "director-intent"


class TestRoutes:
    def test_routes_is_list(self, routing):
        assert isinstance(routing["routes"], list)
        assert len(routing["routes"]) > 0

    def test_route_required_fields(self, routing):
        required = {"id", "operation", "triggers", "agent", "director_action"}
        for route in routing["routes"]:
            missing = required - set(route.keys())
            assert not missing, f"route {route.get('id', '?')} 缺少字段: {missing}"

    def test_route_ids_unique(self, routing):
        ids = [r["id"] for r in routing["routes"]]
        assert len(ids) == len(set(ids)), "route id 存在重复"

    def test_route_triggers_is_list(self, routing):
        for route in routing["routes"]:
            assert isinstance(route["triggers"], list), \
                f"route {route['id']} 的 triggers 应为 list"

    def test_route_agents_valid(self, routing):
        for route in routing["routes"]:
            agents = _normalize_agent(route.get("agent"))
            assert agents, f"route {route['id']} 的 agent 字段为空"
            unknown = agents - VALID_AGENTS
            assert not unknown, f"route {route['id']} 引用未知 agent: {unknown}"

    def test_every_agent_has_route(self, routing):
        """每个子 Agent 至少在归属表中出现一次（防止新增 Agent 未接线）。"""
        routed = set()
        for route in routing["routes"]:
            routed |= _normalize_agent(route.get("agent"))
        # director 有专属豁免项可不出现在 routes，但其他子 Agent 必须可达
        for agent in VALID_AGENTS - {"director"}:
            assert agent in routed, f"Agent {agent} 未出现在任何 route 中"


class TestSkillRoutes:
    def test_skill_routes_structure(self, routing):
        assert isinstance(routing["skill_routes"], list)
        for sr in routing["skill_routes"]:
            assert "intent" in sr and isinstance(sr["intent"], list), "skill route 缺 intent"
            assert "skills" in sr, "skill route 缺 skills"

    def test_skill_route_intents_nonempty(self, routing):
        for sr in routing["skill_routes"]:
            assert sr["intent"], "skill route intent 为空"


class TestMcpRoutes:
    def test_mcp_routes_structure(self, routing):
        assert isinstance(routing["mcp_routes"], list)
        for mr in routing["mcp_routes"]:
            assert "intent" in mr and isinstance(mr["intent"], list), "mcp route 缺 intent"
            assert "mcp" in mr and isinstance(mr["mcp"], str) and mr["mcp"], "mcp route 缺 mcp"
