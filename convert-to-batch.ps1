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
$batchFilename = $($([regex]".*\\(.*)").Matches("$batchFile")).groups[1].value
$codeString = @"
function main {
$([string]::join([environment]::newline,(Get-Content $PS1File)))
}

invoke-expression "main `$(Get-Content `$env:TEMP\params.txt)"
"@
$encodedCode = [convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes([scriptblock]::Create($codeString)))
write-host -ForegroundColor Yellow "Encoded command length:  $($encodedCode.length)"
if ($encodedCode.length -gt 8140) { write-host -ForegroundColor Yellow "Houston, we may have a problem here.... (Max size: 8140)" }

@"
@echo off
goto startCode

### Start comment block ###
===========================================================================
$batchFilename
$env:Username
$((get-date).ToString())
=====start powershell code=================================================
$codeString
===========================================================================
Use
  `$encodedText = '<Encoded text after "powershell.exe -NoLogo -NoProfile -EncodedCommand">'
  [System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String(`$encodedText))
to confirm encoded PowerShell code contents.
===========================================================================
### End comment block ###

:startCode
echo %* > %TEMP%\params.txt

powershell.exe -NoLogo -NoProfile -EncodedCommand $encodedCode

del %TEMP%\params.txt
"@ | out-file -Encoding ascii $batchFile
del %TEMP%\params.txt
"@ | out-file -Encoding ascii $batchFile
