param([ValidateSet('Setup','Start','Stop','Validate','RestoreTest')][string]$Action='Setup')
$ErrorActionPreference='Stop'
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'
$rg='rg-ai103-runtime'; $app='ca-ai103-backend'; $acr='acrossiemateailab'; $site='https://mango-sea-0589cd400.6.azurestaticapps.net'
function Invoke-LabAzure { $r=& az @args; if($LASTEXITCODE -ne 0){throw "Azure CLI failed: $($args[0]) $($args[1])"}; $r }
# Use a distinct function name: PowerShell is case insensitive.
if ((Invoke-LabAzure account show --query id -o tsv).Trim() -ne 'a37bf3fc-3e0b-46ca-bdf7-defade9c9e93'){throw 'Wrong subscription'}
$root=(& git rev-parse --show-toplevel); if($LASTEXITCODE -ne 0){throw 'Run from repository'}
$statePath=Join-Path $root 'state/lab-runtime-v2.json'
function Get-App { Invoke-LabAzure containerapp show -g $rg -n $app -o json | Out-String | ConvertFrom-Json }
function Read-State { Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json }
function Get-Progress { $r=Invoke-LabAzure storage entity query --account-name stossiemateailab --table-name ExerciseProgress --auth-mode login -o json | Out-String | ConvertFrom-Json; @($r.items | Sort-Object PartitionKey,RowKey | Select-Object PartitionKey,RowKey,Status,CompletionPercentage,Notes) | ConvertTo-Json -Depth 5 -Compress }
function Validate-Lab {
 $s=Read-State; $ok=$false
 for($i=0;$i -lt 40;$i++){
  $a=Get-App
  if($a.properties.configuration.ingress.fqdn -ne $s.fqdn){throw 'Hostname changed; frontend configuration requires update'}
  if($a.properties.template.containers[0].image -eq $s.image -and $a.properties.latestRevisionName -eq $a.properties.latestReadyRevisionName -and $a.properties.provisioningState -eq 'Succeeded'){
   $url='https://'+$s.fqdn
   try{$h=Invoke-RestMethod "$url/health" -TimeoutSec 30; $info=Invoke-RestMethod "$url/api/info" -TimeoutSec 30; if($h.status -eq 'healthy' -and $info.model -eq 'gpt-5-mini-2' -and $info.live_ai_enabled -eq $false){$ok=$true;break}}catch{Write-Host $_.Exception.Message}
  }
  Start-Sleep 15
 }
 if(!$ok){throw 'Backend readiness not confirmed'}
 foreach($path in @('/api/auth/me','/api/lab/capabilities')){
  try{Invoke-WebRequest -UseBasicParsing "$url$path" -TimeoutSec 60 | Out-Null; throw 'Anonymous request accepted'}catch{if(!$_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 401){throw}}
 }
 if((Invoke-WebRequest -UseBasicParsing $site -TimeoutSec 60).StatusCode -ne 200){throw 'Public site unavailable'}
 Get-Progress | Out-Null
 Write-Host 'Backend, anonymous access, public site and storage checks passed.' -ForegroundColor Green
}
function Start-Lab {
 $s=Read-State
 $apps=@(Invoke-LabAzure containerapp list -g $rg --query '[].name' -o tsv)
 if($apps -notcontains $app){
  $vars=@($s.vars)
  Invoke-LabAzure containerapp create -g $rg -n $app --environment $s.environment --workload-profile-name Consumption --image $s.image --registry-server "$acr.azurecr.io" --registry-identity $s.identity --user-assigned $s.identity --cpu 0.5 --memory 1.0Gi --min-replicas 0 --max-replicas 1 --ingress external --target-port 8000 --env-vars @vars -o none
 }
 Validate-Lab
}
function Stop-Lab {
 $s=Read-State; $a=Get-App
 if($a.properties.template.containers[0].image -ne $s.image){throw 'Runtime differs from saved state; run Setup again'}
 if((Read-Host 'Type DELETE-BACKEND to delete only ca-ai103-backend') -ne 'DELETE-BACKEND'){throw 'Cancelled'}
 Invoke-LabAzure containerapp delete -g $rg -n $app --yes -o none
}
switch($Action){
 'Start' {Start-Lab; return}
 'Stop' {Stop-Lab; return}
 'Validate' {Validate-Lab; return}
 'RestoreTest' {$before=Get-Progress; Validate-Lab; Stop-Lab; Start-Lab; $after=Get-Progress; if($before -ne $after){throw 'Progress changed during restoration'}; Write-Host 'Progress persistence comparison passed'; return}
}
$a=Get-App; $c=$a.properties.template.containers[0]
if($c.image -ne 'acrossiemateailab.azurecr.io/ai103-backend@sha256:019b738dca83a1f2841978ec9a84051280d26eee3b16836cb08130473f53a4ed'){throw 'Unexpected image; verify deployment first'}
$vars=@($c.env | ForEach-Object {if($_.secretRef){throw 'Secret references require manual restoration'}; "$($_.name)=$($_.value)"})
if($vars -notcontains 'MODEL_DEPLOYMENT=gpt-5-mini-2' -or $vars -notcontains 'LIVE_CHAT_ENABLED=false'){throw 'Unexpected model or live mode'}
& git -C $root check-ignore -- state/lab-runtime-v2.json | Out-Null
if($LASTEXITCODE -ne 0){throw 'State path must be git ignored'}
$identity=Invoke-LabAzure identity show -g rg-ai103-persistent -n id-ai103-lab --query id -o tsv
$s=@{image=$c.image;environment='cae-ai103-lab';identity=$identity;vars=$vars;fqdn=$a.properties.configuration.ingress.fqdn}
New-Item -ItemType Directory -Force (Split-Path $statePath) | Out-Null
$s | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8
Validate-Lab
$target=Join-Path $root 'scripts/lab-lifecycle.ps1'
if($PSCommandPath -ne $target){Copy-Item -LiteralPath $PSCommandPath -Destination $target -Force}
Write-Host 'Lifecycle script installed. No resources deleted. RestoreTest requires separate explicit confirmation.' -ForegroundColor Green
