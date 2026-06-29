<#
.SYNOPSIS
    Simple LLM test to verify setup is working
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se:80",
    [string]$Model = "gpt-oss:20b"
)

Write-Host "`n" + ("="*80) -ForegroundColor Cyan
Write-Host "SIMPLE LLM TEST" -ForegroundColor Cyan
Write-Host ("="*80) -ForegroundColor Cyan + "`n"

Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "Model: $Model" -ForegroundColor Yellow
Write-Host ""

# Create test Python script
$testCode = @"
import sys
sys.path.insert(0, '.')

server = "$Server"
model = "$Model"

print(f"[*] Testing connection to: {server}")
print(f"[*] Using model: {model}")
print()

# Try direct API call
try:
    from litellm import completion
    import litellm
    litellm.set_verbose = False

    print("[*] Attempting API call...")

    response = completion(
        model=model,
        messages=[
            {"role": "user", "content": "You are a helpful assistant. Respond with exactly: WORKING"}
        ],
        api_base=server,
        timeout=15,
    )

    content = response.choices[0].message.content
    print(f"[OK] Response received!")
    print(f"[OK] Content: {content}")

    if "WORKING" in content or len(content) > 3:
        print(f"[OK] LLM is responding correctly!")
    else:
        print(f"[WARN] Unexpected response format")

except Exception as e:
    error = str(e)
    print(f"[FAIL] Error: {error[:200]}")

    # Try alternative model formats
    print()
    print("[*] Trying alternative model formats...")

    alternatives = [
        f"ollama/{model}",
        f"localhost/{model}",
        model.split(':')[0] if ':' in model else model,
    ]

    for alt_model in alternatives:
        if alt_model == model:
            continue

        try:
            print(f"[...] Trying: {alt_model}")
            response = completion(
                model=alt_model,
                messages=[{"role": "user", "content": "Say OK"}],
                api_base=server,
                timeout=10,
            )
            content = response.choices[0].message.content
            print(f"[OK] Success with: {alt_model}")
            print(f"[OK] Response: {content}")
            break
        except:
            continue
"@

$testCode | Out-File -FilePath "test_llm_simple.py" -Encoding UTF8

Write-Host "[*] Running test..." -ForegroundColor Yellow
Write-Host ""

$output = python test_llm_simple.py 2>&1

$output | ForEach-Object {
    if ($_ -match "^\[OK\]") {
        Write-Host $_ -ForegroundColor Green
    } elseif ($_ -match "^\[FAIL\]") {
        Write-Host $_ -ForegroundColor Red
    } elseif ($_ -match "^\[WARN\]") {
        Write-Host $_ -ForegroundColor Yellow
    } elseif ($_ -match "^\[\*\]") {
        Write-Host $_ -ForegroundColor Cyan
    } elseif ($_ -match "^\[...\]") {
        Write-Host $_ -ForegroundColor Gray
    } else {
        Write-Host $_
    }
}

Remove-Item "test_llm_simple.py" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host ("="*80) -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host ("="*80) -ForegroundColor Cyan
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  If [OK]: Your setup is working! Run: test-swe-bench.bat" -ForegroundColor Green
Write-Host "  If [FAIL]: Check troubleshooting guide: TROUBLESHOOTING_LLM.md" -ForegroundColor Red
Write-Host ""
