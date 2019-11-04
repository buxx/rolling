@echo off

:: see https://github.com/vegardit/cygwin-portable-installer/blob/master/cygwin-portable-installer.cmd for original authors*
:: SPDX-License-Identifier: Apache-2.0

set DOWNLOADER=%INSTALL_ROOT%downloader.vbs
set CYGWIN_MIRROR=http://linux.rz.ruhr-uni-bochum.de/download/cygwin
set CYGWIN_ARCH=auto
set CYGWIN_USERNAME=root
set CYGWIN_PACKAGES=python37,wget,zip,python37-pip,gcc-g++,make,python37-devel,zlib,zlib-devel,libjpeg8,libjpeg-devel
set MINTTY_OPTIONS=--Title Rolling ^
  -o Columns=160 ^
  -o Rows=50 ^
  -o BellType=0 ^
  -o ClicksPlaceCursor=yes ^
  -o CursorBlinks=yes ^
  -o CursorColour=96,96,255 ^
  -o CursorType=Block ^
  -o CopyOnSelect=yes ^
  -o RightClickAction=Paste ^
  -o Font="Courier New" ^
  -o FontHeight=10 ^
  -o FontSmoothing=None ^
  -o ScrollbackLines=10000 ^
  -o Transparency=off ^
  -o Term=xterm-256color ^
  -o Charset=UTF-8 ^
-o Locale=C

echo.
echo Installing Cygwin...
echo.

set INSTALL_ROOT=%~dp0
set CYGWIN_ROOT=%INSTALL_ROOT%cygwin
echo Creating Cygwin root [%CYGWIN_ROOT%]...
if not exist "%CYGWIN_ROOT%" (
    md "%CYGWIN_ROOT%"
)

:: https://blogs.msdn.microsoft.com/david.wang/2006/03/27/howto-detect-process-bitness/
if "%CYGWIN_ARCH%" == "auto" (
    if "%PROCESSOR_ARCHITECTURE%" == "x86" (
        if defined PROCESSOR_ARCHITEW6432 (
            set CYGWIN_ARCH=64
        ) else (
            set CYGWIN_ARCH=32
        )
    ) else (
        set CYGWIN_ARCH=64
    )
)

:: download Cygwin 32 or 64 setup exe depending on detected architecture
if "%CYGWIN_ARCH%" == "64" (
    set CYGWIN_SETUP=setup-x86_64.exe
) else (
    set CYGWIN_SETUP=setup-x86.exe
)

if exist "%CYGWIN_ROOT%\%CYGWIN_SETUP%" (
    del "%CYGWIN_ROOT%\%CYGWIN_SETUP%" || goto :fail
)

:: create VB script that can download files
:: not using PowerShell which may be blocked by group policies
set DOWNLOADER=%INSTALL_ROOT%downloader.vbs
echo Creating [%DOWNLOADER%] script...

(
    echo url = Wscript.Arguments(0^)
    echo target = Wscript.Arguments(1^)
    echo WScript.Echo "Downloading '" ^& url ^& "' to '" ^& target ^& "'..."
    echo Set req = CreateObject("WinHttp.WinHttpRequest.5.1"^)
    echo req.Open "GET", url, False
    echo req.Send
    echo If req.Status ^<^> 200 Then
    echo    WScript.Echo "FAILED to download: HTTP Status " ^& req.Status
    echo    WScript.Quit 1
    echo End If
    echo Set buff = CreateObject("ADODB.Stream"^)
    echo buff.Open
    echo buff.Type = 1
    echo buff.Write req.ResponseBody
    echo buff.Position = 0
    echo buff.SaveToFile target
    echo buff.Close
    echo.
) >"%DOWNLOADER%" || goto :fail

cscript //Nologo "%DOWNLOADER%" https://cygwin.org/%CYGWIN_SETUP% "%CYGWIN_ROOT%\%CYGWIN_SETUP%" || goto :fail

echo Running Cygwin setup...
"%CYGWIN_ROOT%\%CYGWIN_SETUP%" --no-admin ^
 --site %CYGWIN_MIRROR% %CYGWIN_PROXY% ^
 --root "%CYGWIN_ROOT%" ^
 --local-package-dir "%CYGWIN_ROOT%\.pkg-cache" ^
 --no-shortcuts ^
 --no-desktop ^
 --delete-orphans ^
 --upgrade-also ^
 --no-replaceonreboot ^
 --quiet-mode ^
 --packages dos2unix,wget,%CYGWIN_PACKAGES% || goto :fail

:: delete pkgs cache
rd /s /q "%CYGWIN_ROOT%\.pkg-cache"

copy install_rolling.sh %CYGWIN_ROOT%\bin\install_rolling.sh
copy start_rolling_tui.sh %CYGWIN_ROOT%\bin\start_rolling_tui.sh

cygwin\bin\mintty --nopin %MINTTY_OPTIONS% /bin/bash /bin/install_rolling.sh -

timeout /T 60
