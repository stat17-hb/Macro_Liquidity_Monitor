@echo off
chcp 65001 > nul
echo ========================================
echo   유동성 모니터링 대시보드 실행
echo ========================================
echo.

cd /d "%~dp0"

echo Streamlit 앱을 시작합니다...
echo 브라우저에서 http://localhost:8501 로 접속하세요.
echo.
echo 종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.
echo.

REM Streamlit 앱 실행 (서버 준비되면 자동으로 브라우저 열림)
streamlit run app.py

pause
