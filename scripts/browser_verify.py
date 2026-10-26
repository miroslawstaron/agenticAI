"""Production UI checks and real screenshots used by the bundled tutorial."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8876")
args = parser.parse_args()
screens = ROOT / "agenticai/static/tutorial/images"
screens.mkdir(parents=True, exist_ok=True)
report = {"checks": [], "console_errors": [], "screenshots": []}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1440, "height": 960}, device_scale_factor=1
    )
    page.on("pageerror", lambda error: report["console_errors"].append(str(error)))
    page.goto(args.url)
    page.get_by_role("button", name="Teacher & student", exact=True).wait_for()
    page.get_by_role("button", name="Programmer & designer", exact=True).click()
    page.wait_for_timeout(350)

    def shot(name, locator=None):
        if page.locator(".toast").count():
            page.locator(".toast").wait_for(state="hidden", timeout=6000)
        page.wait_for_timeout(250)
        (locator or page).screenshot(path=str(screens / (name + ".png")))
        report["screenshots"].append(name)

    shot("workspace")
    page.locator(".agent-node").get_by_text("Programmer", exact=True).click()
    page.locator(".inspector").get_by_label("Name", exact=True).fill("Programmer")
    shot("agent-settings")
    page.locator(".inspector-body").evaluate("(el)=>el.scrollTop=310")
    shot("agent-inspector", page.locator(".inspector"))
    page.locator(".inspector-body").evaluate("(el)=>el.scrollTop=0")
    page.get_by_role("button", name="Run limits", exact=True).click()
    shot("run-limits", page.get_by_role("dialog"))
    page.get_by_role("button", name="Done", exact=True).click()
    page.locator(
        '.react-flow__edge:not([data-id^="__workflow_start__"])'
    ).first.dispatch_event("click")
    page.get_by_text("Communication link", exact=True).wait_for()
    shot("communication")
    page.get_by_role("button", name="Save", exact=True).click()
    page.get_by_text("Network saved", exact=True).wait_for()
    page.get_by_role("button", name="Run network", exact=True).click()
    page.locator(".status.completed").first.wait_for()
    shot("run-activity")
    report["checks"].append(
        "Saved and ran Programmer/Designer workflow from the browser"
    )
    page.get_by_role("button", name="Tools & CLI", exact=False).click()
    page.get_by_role("heading", name="Tools & CLI", exact=True).wait_for()
    shot("tool-registry")
    page.get_by_role("heading", name="Python version", exact=True).click()
    page.get_by_role("dialog").wait_for()
    shot("cli-editor")
    page.get_by_role("button", name="Test", exact=True).click()
    page.locator(".test-result").filter(has_text='"ok": true').wait_for()
    page.locator(".test-result").scroll_into_view_if_needed()
    shot("cli-test")
    page.get_by_role("button", name="Close", exact=True).click()
    page.get_by_role("heading", name="Shell", exact=True).click()
    shot("shell-settings")
    page.get_by_role("button", name="Close", exact=True).click()
    report["checks"].append(
        "Tested registered Python CLI executable and captured result"
    )
    page.get_by_role("button", name="Install & manage", exact=True).click()
    page.get_by_label("Package identifier", exact=True).fill("ruff")
    page.get_by_role("button", name="Preview installation", exact=True).click()
    page.get_by_role("dialog", name="Review installation").wait_for()
    shot("install-preview")
    page.get_by_role("button", name="Cancel", exact=True).click()
    shot("installation")
    report["checks"].append(
        "Previewed installation without performing a host installation"
    )
    page.get_by_role("button", name="Model providers", exact=True).click()
    shot("providers")
    page.get_by_role("button", name="Demo provider", exact=False).click()
    shot("provider-settings", page.get_by_role("dialog"))
    page.get_by_role("button", name="Test", exact=True).click()
    page.locator(".test-result").wait_for()
    page.get_by_role("button", name="Close", exact=True).click()
    page.get_by_role("button", name="Autonomous team", exact=False).click()
    page.get_by_role("button", name="Run network", exact=True).click()
    page.locator(".status.completed").first.wait_for()
    shot("autonomous-activity")
    page.get_by_role("button", name="Use evolved network", exact=True).click()
    page.get_by_text("Research assistant", exact=True).first.wait_for()
    shot("autonomous-network")
    report["checks"].append(
        "Autonomous demo spawned a child, delegated work, and loaded the evolved graph"
    )
    # Capture a real fan-out workflow without reusing the cover's graph image.
    page.on("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="C verification", exact=True).click()
    page.wait_for_timeout(350)
    shot("parallel-workflow")
    # Inspect deterministic human waiting and UI response submission.
    token = page.request.get(args.url + "/api/v1/session").json()["token"]
    from agenticai.models import Agent, Network

    network = Network(
        id="browser-human",
        name="Browser review",
        agents=[Agent(id="review", kind="human", name="Reviewer")],
        entry_agents=["review"],
        initial_task="Review the generated result before approving it.",
    )
    page.request.put(
        args.url + "/api/v1/networks/browser-human",
        headers={"X-Studio-Token": token},
        data=network.model_dump(),
    )
    page.reload()
    page.get_by_role("button", name="Browser review", exact=True).click()
    page.get_by_role("button", name="Run network", exact=True).click()
    page.get_by_label("Human response").wait_for()
    shot("human-review")
    page.get_by_label("Human response").fill(
        "Approved after checking the generated result."
    )
    page.get_by_role("button", name="Send response", exact=True).click()
    page.locator(".status.completed").first.wait_for()
    report["checks"].append("Submitted human input and completed a waiting run")
    page.get_by_role("button", name="Run history", exact=True).click()
    shot("run-history")
    page.get_by_role("button", name="Documentation", exact=True).click()
    page.locator(".markdown").wait_for()
    shot("documentation")
    page.set_viewport_size({"width": 768, "height": 1024})
    page.get_by_role("button", name="Tools & CLI", exact=False).click()
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    shot("tablet-tools")
    report["checks"].append("Tablet viewport has no horizontal page overflow")
    assert not report["console_errors"], report["console_errors"]
    browser.close()

target = ROOT / ".build/browser-verification.json"
target.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
