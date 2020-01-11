@echo off

echo Creating new build...
pyinstaller -F playscii.py
echo Build done!

echo -----------

echo Copying external files...
REM xcopy dirs recursively
for /f "tokens=*" %%i in (win_xcopy_include) DO (
echo %%i
xcopy /E/Y "%%i" "dist\%%i" /exclude:win_copy_exclude
)
REM regular copy files (non-recursively)
for /f "tokens=*" %%i in (win_copy_include) DO (
echo %%i
copy /Y "%%i" "dist\" > NUL
)

echo -----------
echo Done!

pause
