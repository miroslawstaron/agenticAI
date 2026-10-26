"""Render all eighteen slides and check text geometry and offline resources."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8876")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
target = root / ".build/tutorial-review"
target.mkdir(parents=True, exist_ok=True)
report = {"slides": [], "errors": [], "external_resources": []}
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1440, "height": 810}, device_scale_factor=1
    )
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.on(
        "request",
        lambda request: (
            report["external_resources"].append(request.url)
            if not request.url.startswith(args.url)
            else None
        ),
    )
    page.goto(args.url + "/tutorial/")
    page.wait_for_function("window.Reveal && Reveal.isReady()")
    assert page.locator(".slides>section").count() == 18
    for index in range(18):
        page.evaluate("(i)=>Reveal.slide(i)", index)
        page.wait_for_timeout(160)
        sizes = page.locator(".present .copy").evaluate(
            "(el)=>({width:el.scrollWidth,clientWidth:el.clientWidth,height:el.getBoundingClientRect().height})"
        )
        assert sizes["width"] <= sizes["clientWidth"] + 2, (index, sizes)
        assert sizes["height"] <= 700, (index, sizes)
        assert page.locator(".present img").evaluate_all(
            "(images)=>images.every(img=>img.complete && img.naturalWidth>0)"
        )
        page.screenshot(path=str(target / f"{index + 1:02d}.png"))
        report["slides"].append(
            {
                "number": index + 1,
                "title": page.locator(".present h1").inner_text(),
                **sizes,
            }
        )
    assert not report["errors"], report["errors"]
    assert not report["external_resources"], report["external_resources"]
    with page.expect_popup() as popup_info:
        page.keyboard.press("s")
    speaker = popup_info.value
    speaker.frame_locator("#current-slide iframe").locator(".reveal").wait_for(
        timeout=15000
    )
    report["speaker_view"] = "Current-slide preview loaded in same-origin iframe"
    speaker.close()
    browser.close()
(root / ".build/tutorial-verification.json").write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
