param(
  [Parameter(Mandatory=$true)]
  [String] $ImagePath
)

Write-Host "`nReading PNG file from: $ImagePath"

$bytes = Get-Content -Path $ImagePath -Encoding Byte
$base64Encoded = [Convert]::ToBase64String($bytes)

$uri = "data:image/png;base64,$base64Encoded"

# Get filename and change extension to .uri
$filename = (Get-Item $ImagePath).BaseName + ".uri"

# Build output path with modified filename
$outputPath = Join-Path (Split-Path -Path $ImagePath) -ChildPath $filename 

# Write data URI to file
Set-Content -Path $outputPath -Value $uri -Encoding UTF8

Write-Host "Data URI written to:  $outputPath"
