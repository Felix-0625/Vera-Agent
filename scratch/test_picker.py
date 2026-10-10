import subprocess
import os

def choose_dir() -> str:
    script = (
        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;\n"
        "$dlg = New-Object System.Windows.Forms.FolderBrowserDialog;\n"
        "$dlg.Description = '选择项目文件夹';\n"
        "$dlg.ShowNewFolderButton = $true;\n"
        "$form = New-Object System.Windows.Forms.Form;\n"
        "$form.TopMost = $true;\n"
        "if ($dlg.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {\n"
        "    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;\n"
        "    Write-Output $dlg.SelectedPath;\n"
        "}\n"
    )
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    return res.stdout.strip()

if __name__ == "__main__":
    print("Script ready")
