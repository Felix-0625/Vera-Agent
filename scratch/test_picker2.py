import subprocess
import shutil

def pick() -> str:
    script = (
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;\n"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;\n"
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog;\n"
        "$dialog.Description = '选择项目文件夹';\n"
        "$dialog.ShowNewFolderButton = $true;\n"
        "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {\n"
        "    Write-Output $dialog.SelectedPath;\n"
        "}\n"
    )
    res = subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=120,
    )
    return res.stdout.strip()

if __name__ == "__main__":
    print("Test OK")
