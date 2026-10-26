"""Browser regressions for stale sessions, initial tasks and the default team."""

import argparse
import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8876")
parser.add_argument("--credentials-file", type=Path)
args = parser.parse_args()
credentials = None
if args.credentials_file:
    private = json.loads(args.credentials_file.read_text(encoding="utf-8-sig"))
    credentials = {"username": private["username"], "password": private["password"]}

checks = []
temporary_ids = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(
        http_credentials=credentials, viewport={"width": 1440, "height": 960}
    )
    page = context.new_page()
    errors = []
    responses = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "response", lambda response: responses.append((response.url, response.status))
    )
    sessions = [0]

    def stale_session_once(route):
        response = route.fetch()
        data = response.json()
        sessions[0] += 1
        if sessions[0] == 1:
            data["token"] = "expired-token-from-before-restart"
        route.fulfill(response=response, json=data)

    page.route("**/api/v1/session", stale_session_once)
    try:
        page.goto(args.url)
        expect(page.get_by_label("Network name", exact=True)).to_have_value(
            "Programmer & designer"
        )
        expect(page.locator(".start-node")).to_be_visible()
        expect(
            page.locator(".inspector").get_by_label("Programmer", exact=True)
        ).to_be_checked()
        expect(
            page.locator(".inspector").get_by_label("Designer", exact=True)
        ).not_to_be_checked()
        checks.append(
            "Fresh browser opens Programmer/Designer with Start connected to Programmer"
        )
        page.screenshot(path=str(ROOT / ".build/workflow-start.png"))

        page.get_by_role("button", name="Validate", exact=True).click()
        page.get_by_text("Network is valid", exact=False).wait_for()
        assert sessions[0] == 2
        assert any(
            status == 403 and url.endswith("/networks/validate")
            for url, status in responses
        )
        assert not page.locator(".error-banner").count()
        checks.append("Expired tab token renews automatically and validation succeeds")

        page.get_by_role("button", name="Duplicate network", exact=True).click()
        task = 'Implement a C greeting: "Hej, världen!"\nUse the designer feedback to improve it.'
        page.locator(".start-node").get_by_role(
            "button", name="Edit initial task"
        ).click()
        page.locator(".inspector").get_by_label("Initial task", exact=False).fill(task)
        with page.expect_response(
            lambda r: r.request.method == "PUT" and "/api/v1/networks/" in r.url
        ) as saved:
            page.get_by_role("button", name="Save", exact=True).click()
        network = saved.value.json()
        temporary_ids.append(network["id"])
        assert network["initial_task"] == task and network["entry_agents"] == [
            "programmer"
        ]
        assert len(network["agents"]) == 2
        page.reload()
        expect(page.get_by_label("Network name", exact=True)).to_have_value(
            network["name"]
        )
        expect(
            page.get_by_label("INITIAL TASK FOR NEXT RUN", exact=True)
        ).to_have_value(task)
        expect(
            page.locator(".inspector").get_by_label("Initial task", exact=False)
        ).to_have_value(task)

        with page.expect_download() as downloaded:
            page.get_by_role("button", name="Export network", exact=True).click()
        exported = json.loads(Path(downloaded.value.path()).read_text(encoding="utf-8"))
        assert exported["initial_task"] == task
        assert exported["entry_agents"] == ["programmer"]
        checks.append(
            "Initial task and first recipients survive saving, reloading and JSON export"
        )

        # Removing a Start link changes entries without deleting a real agent link.
        page.locator(
            '.react-flow__edge[data-id="__workflow_start__:programmer"]'
        ).dispatch_event("click")
        page.keyboard.press("Delete")
        expect(
            page.locator(".inspector").get_by_label("Programmer", exact=True)
        ).not_to_be_checked()
        expect(
            page.locator('.react-flow__edge:not([data-id^="__workflow_start__"])')
        ).to_have_count(2)
        page.locator(".inspector").get_by_label("Programmer", exact=True).check()
        expect(
            page.locator('.react-flow__edge[data-id="__workflow_start__:programmer"]')
        ).to_have_count(1)
        checks.append(
            "Start connections update first recipients independently of communication links"
        )

        with page.expect_response(
            lambda r: r.request.method == "POST" and r.url.endswith("/api/v1/runs")
        ) as launched:
            page.get_by_role("button", name="Run network", exact=True).click()
        run_id = launched.value.json()["id"]
        page.locator(".status.completed").first.wait_for()
        details = context.request.get(args.url + "/api/v1/runs/" + run_id).json()
        assert details["prompt"] == task
        first_user = next(m for m in details["messages"] if m["role"] == "user")
        assert first_user["agent_id"] == "programmer" and first_user["content"] == task
        timeline = context.request.get(
            args.url + f"/api/v1/runs/{run_id}/events?stream=false"
        ).json()
        assert [
            e["body"]["agent_id"] for e in timeline if e["kind"] == "agent_started"
        ] == ["programmer", "designer"] * 3
        checks.append(
            "Saved task reaches Programmer first and three feedback rounds complete"
        )

        # Import the exported configuration as a separate definition.
        exported["id"] = "browser-start-" + uuid4().hex[:12]
        exported["name"] = "Imported starting point"
        temporary_ids.append(exported["id"])
        page.locator('input[type="file"]').first.set_input_files(
            {
                "name": "network.json",
                "mimeType": "application/json",
                "buffer": json.dumps(exported).encode(),
            }
        )
        expect(page.get_by_label("Network name", exact=True)).to_have_value(
            exported["name"]
        )
        expect(
            page.locator(".inspector").get_by_label("Initial task", exact=False)
        ).to_have_value(task)
        checks.append("Imported network restores the same starting point and task")
        assert not errors, errors
    finally:
        token = context.request.get(args.url + "/api/v1/session").json()["token"]
        for id in temporary_ids:
            context.request.delete(
                args.url + "/api/v1/networks/" + id, headers={"X-Studio-Token": token}
            )
        browser.close()

report = {"url": args.url, "checks": checks, "javascript_errors": errors}
(ROOT / ".build/workflow-start-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
