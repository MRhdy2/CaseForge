"""评测默认启用 RAG，并从所选业务项目知识库检索。"""

import json
import time


SAMPLE_CONTENT = "用户登录：支持账号密码登录和手机号验证码登录。"
KNOWLEDGE_CONTENT = (
    "# 用户登录\n## 账号密码登录\n"
    "用户登录 账号密码登录 用户使用账号和密码登录系统。"
    "密码连续错误 5 次时锁定账号 30 分钟。"
)


def _create_sample(client):
    response = client.post(
        "/evaluations/samples",
        json={
            "title": "登录需求评测",
            "content": SAMPLE_CONTENT,
            "checkpoints": [{"text": "账号密码登录"}],
        },
    )
    response.raise_for_status()
    return response.json()


def test_rag_run_requires_ready_knowledge_source(client, project):
    sample = _create_sample(client)
    payload = {"label": "rag-validation", "sample_ids": [sample["id"]], "strategy": "quick"}

    missing = client.post("/evaluations/runs", json=payload)
    assert missing.status_code == 400
    assert "知识来源项目" in missing.json()["detail"]

    empty = client.post(
        "/evaluations/runs",
        json={**payload, "knowledge_project_id": project["id"]},
    )
    assert empty.status_code == 400
    assert "没有已入库" in empty.json()["detail"]


def test_evaluation_uses_selected_project_knowledge_by_default(client, project):
    knowledge = client.create_knowledge_doc(project["id"], "登录规则", KNOWLEDGE_CONTENT)
    assert knowledge["status"] == "ready"
    sample = _create_sample(client)

    sources = client.get("/evaluations/knowledge-sources")
    sources.raise_for_status()
    assert any(s["id"] == project["id"] for s in sources.json())

    response = client.post(
        "/evaluations/runs",
        json={
            "label": "rag-default",
            "sample_ids": [sample["id"]],
            "strategy": "quick",
            "knowledge_project_id": project["id"],
        },
    )
    response.raise_for_status()
    run = response.json()
    assert run["config"]["use_knowledge"] is True
    assert run["config"]["knowledge_project_id"] == project["id"]

    deadline = time.time() + 60
    while time.time() < deadline:
        run = client.get(f"/evaluations/runs/{run['id']}").json()
        if run["status"] in ("completed", "failed"):
            break
        time.sleep(0.3)
    assert run["status"] == "completed", run.get("error_message")

    task_id = run["results"][0]["task_id"]
    task_response = client.get(f"/evaluations/tasks/{task_id}")
    task_response.raise_for_status()
    task = task_response.json()
    task_config = json.loads(task["strategy_config"])
    assert task_config["use_knowledge"] is True
    assert task_config["knowledge_project_id"] == project["id"]
    refs = json.loads(task["knowledge_refs"] or "{}")
    assert any(ref["title"] == "登录规则" for hits in refs.values() for ref in hits)
