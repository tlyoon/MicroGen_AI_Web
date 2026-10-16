# Speech output exclusively for an offline, NOT-APPROVED demonstration.
# Uses locally installed Windows SAPI to validate per-element WAV timing.
# Production MicroGen_AI_Web must replace this with reviewed Gemini TTS
# per-element segments of one consistent voice.
param(
    [Parameter(Mandatory=$true)][string]$Plan,
    [Parameter(Mandatory=$true)][string]$OutputFolder
)
$ErrorActionPreference = "Stop"
if (Test-Path -LiteralPath $OutputFolder) {
    throw "Refusing to overwrite an existing audio folder: $OutputFolder"
}
$planObj = Get-Content -LiteralPath $Plan -Raw -Encoding UTF8 | ConvertFrom-Json
if ($planObj.status -ne 'author_specified_unapproved_element_narration' -or
    $planObj.voice_id -ne 'windows_sapi_Microsoft_Zira_Desktop_REVIEW_ONLY') {
    throw "The audio generator accepts only an explicit unapproved demonstration plan"
}
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Zira Desktop')
$synth.Rate = -1
New-Item -ItemType Directory -Path $OutputFolder -ErrorAction Stop | Out-Null
$created = 0
try {
    foreach ($part in $planObj.parts) {
        foreach ($slide in $part.slides) {
            foreach ($el in $slide.elements) {
                $filename = [string]$el.wav
                if ($filename -notmatch '^[a-zA-Z0-9_.-]+\.wav$') {
                    throw "Unsafe narration WAV name"
                }
                $dest = Join-Path $OutputFolder $filename
                if (Test-Path -LiteralPath $dest) {
                    throw "Duplicate or preexisting WAV"
                }
                $text = [string]$el.spoken_text
                if ([string]::IsNullOrWhiteSpace($text)) {
                    throw "Empty spoken text"
                }
                $synth.SetOutputToWaveFile($dest)
                try {
                    $synth.Speak($text)
                } finally {
                    $synth.SetOutputToNull()
                }
                if ((Get-Item -LiteralPath $dest).Length -lt 2000) {
                    throw "Invalid WAV output size"
                }
                $created++
                Write-Output ("SAPI review segment {0} {1}" -f $created,$filename)
            }
        }
    }
} finally {
    $synth.Dispose()
}
Write-Output ("REVIEW_ONLY: created {0} WAV segments under {1}" -f $created,$OutputFolder)
