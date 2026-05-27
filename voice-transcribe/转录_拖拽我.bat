:: 拖拽音频文件到此 .bat 文件上即可转录
@echo off
chcp 65001 >nul
cd /d "%~dp0"
python transcribe.py "%~1"
pause
