Add-Type -AssemblyName System.Drawing
$src = "C:\Users\FAST\.gemini\antigravity-ide\brain\a38a0dbe-aec1-44cf-a091-43a4557e52ca\.user_uploaded\media_1791345620445.png"
$img = [System.Drawing.Image]::FromFile($src)
$thumb = New-Object System.Drawing.Bitmap(64, 64)
$g = [System.Drawing.Graphics]::FromImage($thumb)
$g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.DrawImage($img, 0, 0, 64, 64)
$ms = New-Object System.IO.MemoryStream
$thumb.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$b64 = [Convert]::ToBase64String($ms.ToArray())
[System.IO.File]::WriteAllText("c:\Users\FAST\Desktop\Multi-agents\scratch\logo_64.txt", $b64)
Write-Output "Done: $($b64.Length)"
$img.Dispose()
$thumb.Dispose()
$g.Dispose()
