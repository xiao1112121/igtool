@echo off
echo Installing Instagram Automation Tool dependencies...
echo.

REM Install basic packages
python -m pip install --upgrade pip
python -m pip install PySide6>=6.5.0
python -m pip install pandas>=2.0.0
python -m pip install requests>=2.31.0
python -m pip install python-dotenv>=1.0.0
python -m pip install selenium>=4.0.0
python -m pip install webdriver-manager>=3.8.0
python -m pip install selenium-wire>=5.1.0
python -m pip install 2captcha-python>=1.1.3

echo.
echo Installation completed!
echo You can now run the application using run_app.bat
pause 