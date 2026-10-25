param([string]$NinjaTraderBin, [string]$NinjaTraderCustomAssembly)
$ErrorActionPreference = 'Stop'
$testRoot = $PSScriptRoot
$artifactRoot = Join-Path $testRoot '.artifacts'
New-Item -ItemType Directory -Force -Path $artifactRoot | Out-Null
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$executable = Join-Path $artifactRoot 'LoggerHarness.exe'
& $compiler /nologo "/out:$executable" (Join-Path $testRoot '../ContRevCsvLogger.cs') (Join-Path $testRoot 'LoggerHarness.cs')
if ($LASTEXITCODE -ne 0) { throw 'C# harness compilation failed' }
$fixtureRoot = Join-Path $artifactRoot ([guid]::NewGuid().ToString('N'))
& $executable $fixtureRoot
if ($LASTEXITCODE -ne 0) { throw 'C# harness failed' }
python (Join-Path $testRoot 'verify_logs.py') $fixtureRoot
if ($LASTEXITCODE -ne 0) { throw 'CSV validation failed' }
python (Join-Path $testRoot 'verify_strategy.py')
if ($LASTEXITCODE -ne 0) { throw 'Trading behavior source contract failed' }
if ($NinjaTraderBin -and $NinjaTraderCustomAssembly) {
    $wpf = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/WPF'
    $output = Join-Path $artifactRoot 'StrategyCompile.dll'
    # The installed custom assembly may contain the old strategy enum; prefer this source.
    & $compiler /nologo /target:library /nowarn:0436 "/out:$output" `
        "/reference:$NinjaTraderBin/NinjaTrader.Core.dll" "/reference:$NinjaTraderBin/NinjaTrader.Gui.dll" `
        "/reference:$NinjaTraderCustomAssembly" "/reference:$wpf/PresentationCore.dll" `
        "/reference:$wpf/PresentationFramework.dll" "/reference:$wpf/WindowsBase.dll" `
        /reference:System.ComponentModel.DataAnnotations.dll `
        (Join-Path $testRoot '../NYOpenFairPriceStrategy.cs') (Join-Path $testRoot '../ContRevCsvLogger.cs')
    if ($LASTEXITCODE -ne 0) { throw 'NinjaTrader reference compilation failed' }
    Write-Output 'Strategy compiled against installed NinjaTrader assemblies'
}
