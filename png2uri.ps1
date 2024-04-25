##############################################################
# png2uri.ps1
#
# Powershell script to convert a PNG image to URI. Writes a
# ".uri" file with just the image data and an HTML page with
# the image inside it.
##############################################################
param(
  [Parameter(Mandatory=$true)]
  [String] $ImagePath
)

Write-Host "`nReading PNG file from: $ImagePath"

$bytes = Get-Content -Path $ImagePath -Encoding Byte
$base64Encoded = [Convert]::ToBase64String($bytes)
$mimeType = Get-Item $ImagePath -Force | Select-Object ContentType

$uri = "data:image/png;base64,$base64Encoded"

# Get filename and change extension to .uri
$filename = (Get-Item $ImagePath).BaseName + ".uri"

# Build output path with modified filename
$outputPath = Join-Path (Split-Path -Path $ImagePath) -ChildPath $filename 

# Write data URI to file
Set-Content -Path $outputPath -Value $uri -Encoding UTF8

Write-Host "Data URI written to:  $outputPath"

# Get filename and change extension to .html
$htmlfilename = (Get-Item $ImagePath).BaseName + ".html"

# Build output path with modified filename
$htmloutputPath = Join-Path (Split-Path -Path $ImagePath) -ChildPath $htmlfilename 

# Write web page to file
@"
<!DOCTYPE html>
<html lang="en">
<body>
  <img src="$uri">
</body>
</html>
"@ | out-file -Encoding UTF8 $htmloutputPath

Write-Host "HTML page written to:  $htmloutputPath"
