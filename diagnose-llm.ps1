<#
.SYNOPSIS
    Diagnostic script for LLM server and model connectivity

.DESCRIPTION
    Tests connection to LLM server and verifies model availability
    Helps troubleshoot issues with the SWE-bench testing framework
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se:80",
    [string]$Model = "gpt-oss:20b"
)

Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host "LLM CONNECTIVITY DIAGNOSTIC" -ForegroundColor Magenta
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host ""

# Test 1: Check Python
Write-Host "[TEST 1] Python Installation" -ForegroundColor Cyan
try {
    $pyVersion = python --version 2>&1
    Write-Host "[OK] $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Python not found" -ForegroundColor Red
    exit 1
}

# Test 2: Check LiteLLM
Write-Host ""
Write-Host "[TEST 2] LiteLLM Installation" -ForegroundColor Cyan
$checkLitellm = python -c "import litellm; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] LiteLLM installed" -ForegroundColor Green
} else {
    Write-Host "[FAIL] LiteLLM not found or error" -ForegroundColor Red
    Write-Host "Install with: pip install litellm" -ForegroundColor Yellow
    exit 1
}

# Test 3: Test server connectivity
Write-Host ""
Write-Host "[TEST 3] Server Connectivity" -ForegroundColor Cyan
Write-Host "Testing: $Server"
try {
    $response = Invoke-WebRequest -Uri "$Server" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "[OK] Server is reachable" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Server may not be responding directly" -ForegroundColor Yellow
    Write-Host "This might be OK if it's an LLM API endpoint" -ForegroundColor Yellow
}

# Test 4: Test LLM API call
Write-Host ""
Write-Host "[TEST 4] LLM API Call" -ForegroundColor Cyan
Write-Host "Server: $Server"
Write-Host "Model: $Model"
Write-Host ""

$testScript = @"
import sys
import os
sys.path.insert(0, '.')

# Test different model formats
models_to_try = [
    "$Model",
    "ollama/$Model",
    "localhost/$Model",
]

server = "$Server"

from litellm import completion
import litellm

# Enable debug mode
litellm.set_verbose = True

print("[INFO] Attempting to call LLM...")
print(f"[INFO] Server: {server}")
print()

success = False
for model_name in models_to_try:
    try:
        print(f"[...] Trying model format: {model_name}")

        response = completion(
            model=model_name,
            messages=[{"role": "user", "content": "Say 'OK'"}],
            api_base=server if not model_name.startswith("ollama") else None,
            timeout=10,
        )

        result = response.choices[0].message.content
        print(f"[OK] Success with model: {model_name}")
        print(f"[OK] Response: {result}")
        success = True
        break

    except Exception as e:
        error_msg = str(e)
        if "Provider NOT provided" in error_msg:
            print(f"[...] Model format issue: {model_name}")
        else:
            print(f"[FAIL] Error: {error_msg[:100]}")

if not success:
    print()
    print("[FAIL] Could not connect to LLM")
    print()
    print("TROUBLESHOOTING:")
    print("1. Check if server is running at: $Server")
    print("2. Verify model name: $Model")
    print("3. For Ollama, try: ollama/$Model")
    print("4. Check firewall and network connectivity")
    print()
    sys.exit(1)
"@

$testScript | Out-File -FilePath "test_llm.py" -Encoding UTF8
$output = python test_llm.py 2>&1
Remove-Item "test_llm.py" -ErrorAction SilentlyContinue

Write-Host ""
$output | ForEach-Object {
    if ($_ -match "^\[OK\]") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "^\[FAIL\]") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "^\[WARN\]") {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match "^\[INFO\]|^\[...\]") {
        Write-Host $_ -ForegroundColor Cyan
    } else {
        Write-Host $_
    }
}

# Test 5: Agent connectivity
Write-Host ""
Write-Host "[TEST 5] AgenticAI Agent" -ForegroundColor Cyan

$agentTest = @"
import sys
sys.path.insert(0, '.')

try:
    from agent import AgentAI
    print("[OK] AgentAI imported successfully")

    # Try to create an agent
    agent = AgentAI(
        server_address="$Server",
        model_name="$Model",
        my_role="You are a helpful assistant"
    )
    print("[OK] AgentAI instance created")

    # Try a simple response
    print("[...] Testing agent response...")
    response = agent.get_response("Say OK")
    if response:
        print(f"[OK] Agent response received: {response[:50]}...")
    else:
        print("[WARN] Agent returned empty response")

except Exception as e:
    print(f"[FAIL] Error: {e}")
    import traceback
    traceback.print_exc()
"@

$agentTest | Out-File -FilePath "test_agent.py" -Encoding UTF8
$output = python test_agent.py 2>&1
Remove-Item "test_agent.py" -ErrorAction SilentlyContinue

Write-Host ""
$output | ForEach-Object {
    if ($_ -match "^\[OK\]") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "^\[FAIL\]") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "^\[WARN\]") {
        Write-Host $_ -ForegroundColor Yellow
    } else {
        Write-Host $_
    }
}

# Summary
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host "DIAGNOSTIC COMPLETE" -ForegroundColor Magenta
Write-Host "=" * 80 -ForegroundColor Magenta
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. If all tests passed, the setup is working correctly"
Write-Host "2. If LLM test failed, check:"
Write-Host "   - Server is running and accessible"
Write-Host "   - Model name is correct for your LLM setup"
Write-Host "   - Network connectivity to server"
Write-Host "3. Update test-swe-bench.bat with correct parameters if needed"
Write-Host ""
