# convert-to-batch.ps1
# Encodes relatively small PowerShell scripts and wraps them into a CMD/DOS batch file.

# Source material:
# https://dmitrysotnikov.wordpress.com/2008/06/27/powershell-script-in-a-bat-file/
# https://jrich523.wordpress.com/2011/06/15/file-to-function-string-to-scriptblock/
# https://dmitrysotnikov.wordpress.com/2011/07/06/passing-parameters-to-encodedcommand/
# http://www.thomasmaurer.ch/2011/11/powershell-convert-string-to-scriptblock/
# https://blogs.msdn.microsoft.com/timid/2014/03/26/powershell-encodedcommand-and-round-trips/
# http://systemcentersynergy.com/max-script-block-size-when-passing-to-powershell-exe-or-invoke-command/
# https://adsecurity.org/?p=478

param (
	[Parameter(Mandatory=$true)]
	[string] $PS1File
)

$batchFile = $PS1File -replace ".ps1",".bat"
$a=$([regex]".*\\(.*)").Matches("$batchFile")
$batchFilename = $a.groups[1].value
$codeString = @"
function main1 {
  $([string]::join([environment]::newline,(Get-Content $PS1File)))
}

invoke-expression "main1 `$(Get-Content `$env:TEMP\params.txt)"
"@
$encodedCode = [convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([scriptblock]::Create($codeString)))
write-host -ForegroundColor Yellow "Encoded command length:  $($encodedCode.length)"
if ($encodedCode.length -gt 8140) { write-host -ForegroundColor Yellow "Houston, we may have a problem here.... (Max size: 8140)" }

@"
@echo off
goto startCode

===========================================================================
$batchFilename
$env:Username
$((get-date).ToString())
=====start powershell code=================================================
$codeString
===========================================================================
:startCode
echo %* > %TEMP%\params.txt

powershell.exe -NoLogo -NoProfile -EncodedCommand $encodedCode

del %TEMP%\params.txt
"@ | out-file -Encoding ascii $batchFile
