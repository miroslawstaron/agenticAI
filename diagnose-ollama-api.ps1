<#
.SYNOPSIS
    Diagnose which Ollama API endpoint works
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se",
    [string]$Model = "gpt-oss:20b"
)

Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "OLLAMA API ENDPOINT DIAGNOSIS" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta + "`n"

Write-Host "Server: $Server" -ForegroundColor Cyan
Write-Host "Model: $Model" -ForegroundColor Cyan
Write-Host ""

# Create Python diagnostic script
$pythonScript = @"
import sys
import requests
import json

server = "$Server"
model = "$Model"

print("Testing different Ollama API endpoints...\n")

# Test 1: /api/tags - Check available models
print("[1] Testing /api/tags endpoint")
try:
    response = requests.get(f"{server}/api/tags", timeout=10)
    if response.status_code == 200:
        data = response.json()
        models = [m.get("name") for m in data.get("models", [])]
        print(f"    [OK] Status: {response.status_code}")
        print(f"    [OK] Available models: {', '.join(models[:3])}")
        if model in models:
            print(f"    [OK] Model '{model}' found!")
        else:
            print(f"    [WARN] Model '{model}' NOT in list")
    else:
        print(f"    [FAIL] Status: {response.status_code}")
except Exception as e:
    print(f"    [ERROR] {e}")

# Test 2: /api/chat endpoint
print("\n[2] Testing /api/chat endpoint")
try:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": False
    }
    response = requests.post(
        f"{server}/api/chat",
        json=payload,
        timeout=10,
        headers={"Content-Type": "application/json"}
    )
    print(f"    [*] Status: {response.status_code}")

    if response.status_code == 200:
        print(f"    [OK] /api/chat works!")
    elif response.status_code == 500:
        print(f"    [FAIL] /api/chat returned 500 error")
        print(f"    [*] Response: {response.text[:200]}")
    else:
        print(f"    [WARN] /api/chat status: {response.status_code}")
except Exception as e:
    print(f"    [ERROR] {e}")

# Test 3: /api/generate endpoint (older Ollama)
print("\n[3] Testing /api/generate endpoint")
try:
    payload = {
        "model": model,
        "prompt": "Hi",
        "stream": False
    }
    response = requests.post(
        f"{server}/api/generate",
        json=payload,
        timeout=10,
        headers={"Content-Type": "application/json"}
    )
    print(f"    [*] Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        content = data.get("response", "")
        print(f"    [OK] /api/generate works!")
        print(f"    [OK] Response: {content[:50]}...")
    else:
        print(f"    [FAIL] /api/generate status: {response.status_code}")
except Exception as e:
    print(f"    [ERROR] {e}")

# Test 4: OpenAI-compatible /v1/chat/completions
print("\n[4] Testing /v1/chat/completions endpoint")
try:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    response = requests.post(
        f"{server}/v1/chat/completions",
        json=payload,
        timeout=10,
        headers={"Content-Type": "application/json"}
    )
    print(f"    [*] Status: {response.status_code}")

    if response.status_code == 200:
        print(f"    [OK] /v1/chat/completions works!")
    else:
        print(f"    [FAIL] Status: {response.status_code}")
except Exception as e:
    print(f"    [INFO] Not available: {str(e)[:50]}")

# Test 5: Try different model name formats
print("\n[5] Testing different model name formats")
endpoints = ["/api/chat", "/api/generate"]
model_formats = [
    model,
    model.replace(":", "-"),
    model.split(":")[0],
]

for endpoint in endpoints:
    print(f"\n    Trying {endpoint}:")
    for model_fmt in model_formats:
        try:
            if "chat" in endpoint:
                payload = {
                    "model": model_fmt,
                    "messages": [{"role": "user", "content": "OK"}],
                    "stream": False
                }
            else:
                payload = {
                    "model": model_fmt,
                    "prompt": "OK",
                    "stream": False
                }

            response = requests.post(
                f"{server}{endpoint}",
                json=payload,
                timeout=5,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                print(f"      [SUCCESS] {model_fmt} → Status 200")
            elif response.status_code == 500:
                error = response.text[:100] if response.text else ""
                print(f"      [500 ERROR] {model_fmt} → {error}")
            else:
                print(f"      [{response.status_code}] {model_fmt}")
        except:
            pass

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
"@

$pythonScript | Out-File -FilePath "diagnose_api.py" -Encoding UTF8

Write-Host "[*] Running diagnosis..." -ForegroundColor Yellow
Write-Host ""

python diagnose_api.py 2>&1 | ForEach-Object {
    if ($_ -match "^\[OK\]|SUCCESS") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "FAIL|ERROR|500") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "WARN|DIAGNOSIS") {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match "Testing|Testing different|Trying") {
        Write-Host $_ -ForegroundColor Cyan
    } else {
        Write-Host $_
    }
}

Remove-Item "diagnose_api.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Look for [SUCCESS] or [OK] in the output above" -ForegroundColor White
Write-Host "2. If /api/generate works: use test-ollama-generate.ps1" -ForegroundColor White
Write-Host "3. If /api/chat works: use test-swe-bench-simple.ps1" -ForegroundColor White
Write-Host "4. If you see a 500 error with specific message: that's the issue to fix" -ForegroundColor White
Write-Host ""
