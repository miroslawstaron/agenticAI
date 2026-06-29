<#
.SYNOPSIS
    Direct Ollama API test
    Tests the Ollama server at http://lazythought.cse.chalmers.se using native Ollama API
#>

param(
    [string]$Server = "http://lazythought.cse.chalmers.se",
    [string]$Model = "gpt-oss:20b"
)

Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "OLLAMA DIRECT API TEST" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta + "`n"

Write-Host "Server: $Server" -ForegroundColor Cyan
Write-Host "Model: $Model" -ForegroundColor Cyan
Write-Host ""

# Step 1: Test basic connectivity
Write-Host "[1] Testing server connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$Server/api/tags" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "[OK] Server is reachable" -ForegroundColor Green

    # Parse tags
    $tags = $response.Content | ConvertFrom-Json
    $models = $tags.models | ForEach-Object { $_.name }
    Write-Host "[OK] Available models:" -ForegroundColor Green
    $models | ForEach-Object { Write-Host "     - $_" -ForegroundColor Green }

    if ($models -contains $Model) {
        Write-Host "[OK] Model '$Model' is available" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Model '$Model' not found in tags" -ForegroundColor Yellow
        Write-Host "       Available: $($models -join ', ')" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[FAIL] Cannot reach server at $Server/api/tags" -ForegroundColor Red
    Write-Host "       Error: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Test Ollama generate API
Write-Host "`n[2] Testing Ollama /api/generate endpoint..." -ForegroundColor Yellow

$payload = @{
    model = $Model
    prompt = "You are a helpful assistant. Respond with exactly: WORKING"
    stream = $false
} | ConvertTo-Json

try {
    Write-Host "[...] Sending request to $Server/api/generate" -ForegroundColor Cyan

    $response = Invoke-WebRequest `
        -Uri "$Server/api/generate" `
        -Method Post `
        -Headers @{"Content-Type" = "application/json"} `
        -Body $payload `
        -TimeoutSec 30 `
        -ErrorAction Stop

    $result = $response.Content | ConvertFrom-Json
    $response_text = $result.response

    Write-Host "[OK] Response received!" -ForegroundColor Green
    Write-Host "[OK] Response: $response_text" -ForegroundColor Green

    if ($response_text.Length -gt 3) {
        Write-Host "[OK] Ollama API is working correctly!" -ForegroundColor Green
    }
} catch {
    Write-Host "[FAIL] Error calling /api/generate" -ForegroundColor Red
    Write-Host "       Error: $_" -ForegroundColor Red
}

# Step 3: Test with curl (alternative)
Write-Host "`n[3] Testing with curl (alternative method)..." -ForegroundColor Yellow

$curlCmd = @"
curl -X POST "$Server/api/generate" `
  -H "Content-Type: application/json" `
  -d '{
    "model": "$Model",
    "prompt": "Say OK",
    "stream": false
  }' `
  -s -m 30
"@

Write-Host "[...] Running curl command..." -ForegroundColor Cyan
try {
    $curlResult = Invoke-Expression $curlCmd 2>&1
    if ($curlResult) {
        Write-Host "[OK] Curl response received" -ForegroundColor Green
        Write-Host "[OK] Result: $($curlResult.Substring(0, [Math]::Min(100, $curlResult.Length)))..." -ForegroundColor Green
    }
} catch {
    Write-Host "[INFO] Curl test skipped" -ForegroundColor Gray
}

# Step 4: Summary
Write-Host "`n" + ("="*80) -ForegroundColor Magenta
Write-Host "CONFIGURATION FOR AGENTICAI" -ForegroundColor Magenta
Write-Host ("="*80) -ForegroundColor Magenta
Write-Host ""

Write-Host "If tests above show [OK], use these settings:" -ForegroundColor Green
Write-Host ""
Write-Host "Option 1: Use Ollama provider in LiteLLM" -ForegroundColor Cyan
Write-Host '  Model: "ollama/' + $Model + '"' -ForegroundColor White
Write-Host '  Server: "' + $Server + '"' -ForegroundColor White
Write-Host ""

Write-Host "Option 2: Use OpenAI-compatible endpoint (if Ollama has it)" -ForegroundColor Cyan
Write-Host '  Model: "' + $Model + '"' -ForegroundColor White
Write-Host '  Base URL: "' + $Server + '/v1"' -ForegroundColor White
Write-Host ""

Write-Host "Option 3: Direct Ollama API (native)" -ForegroundColor Cyan
Write-Host '  Server: "' + $Server + '"' -ForegroundColor White
Write-Host '  Model: "' + $Model + '"' -ForegroundColor White
Write-Host '  API Endpoint: /api/generate' -ForegroundColor White
Write-Host ""

Write-Host "NEXT STEP:" -ForegroundColor Yellow
Write-Host "Run: test-swe-bench.bat 5 $Server ollama/$Model" -ForegroundColor Green
Write-Host ""
