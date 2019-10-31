@echo off

:: see https://github.com/vegardit/cygwin-portable-installer/blob/master/cygwin-portable-installer.cmd for original authors*
:: SPDX-License-Identifier: Apache-2.0

set PROXY_HOST=
set PROXY_PORT=8080
set ROLLING_TUI=rolling-tui.pyz
set ROLLING_TUI_URL=https://bux.fr/static/rolling-tui-latest.pyz
set CYGWIN_MIRROR=http://linux.rz.ruhr-uni-bochum.de/download/cygwin
set CYGWIN_ARCH=auto
set CYGWIN_USERNAME=root
set CYGWIN_PACKAGES=python37,wget,zip
set DELETE_CYGWIN_PACKAGE_CACHE=yes
set INSTALL_APT_CYG=yes
set CYGWIN_PATH=%%SystemRoot%%\system32;%%SystemRoot%%
set MINTTY_OPTIONS=--Rolling TUI ^
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
echo Installing ...
echo.

set INSTALL_ROOT=%~dp0
set CYGWIN_ROOT=%INSTALL_ROOT%cygwin
echo Creating Cygwin root [%CYGWIN_ROOT%]...
if not exist "%CYGWIN_ROOT%" (
    md "%CYGWIN_ROOT%"
)

:: create VB script that can download files
:: not using PowerShell which may be blocked by group policies
set DOWNLOADER=%INSTALL_ROOT%downloader.vbs
echo Creating [%DOWNLOADER%] script...
if "%PROXY_HOST%" == "" (
    set DOWNLOADER_PROXY=.
) else (
    set DOWNLOADER_PROXY= req.SetProxy 2, "%PROXY_HOST%:%PROXY_PORT%", ""
)

(
    echo url = Wscript.Arguments(0^)
    echo target = Wscript.Arguments(1^)
    echo WScript.Echo "Downloading '" ^& url ^& "' to '" ^& target ^& "'..."
    echo Set req = CreateObject("WinHttp.WinHttpRequest.5.1"^)
    echo%DOWNLOADER_PROXY%
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
if exist "%CYGWIN_ROOT%\%ROLLING_TUI%" (
    del "%CYGWIN_ROOT%\%ROLLING_TUI%" || goto :fail
)
cscript //Nologo "%DOWNLOADER%" https://cygwin.org/%CYGWIN_SETUP% "%CYGWIN_ROOT%\%CYGWIN_SETUP%" || goto :fail
cscript //Nologo "%DOWNLOADER%" %ROLLING_TUI_URL% "%CYGWIN_ROOT%\%ROLLING_TUI%" || goto :fail

:: Cygwin command line options: https://cygwin.com/faq/faq.html#faq.setup.cli
if "%PROXY_HOST%" == "" (
    set CYGWIN_PROXY=
) else (
    set CYGWIN_PROXY=--proxy "%PROXY_HOST%:%PROXY_PORT%"
)

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

if "%DELETE_CYGWIN_PACKAGE_CACHE%" == "yes" (
    rd /s /q "%CYGWIN_ROOT%\.pkg-cache"
)

set Updater_cmd=%INSTALL_ROOT%updater.cmd
echo Creating updater [%Updater_cmd%]...
(
    echo @echo off
    echo set CYGWIN_ROOT=%%~dp0cygwin
    echo echo.
    echo.
    echo echo ###########################################################
    echo echo # Updating [Cygwin Portable]...
    echo echo ###########################################################
    echo echo.
    echo "%%CYGWIN_ROOT%%\%CYGWIN_SETUP%" --no-admin ^^
    echo --site %CYGWIN_MIRROR% %CYGWIN_PROXY% ^^
    echo --root "%%CYGWIN_ROOT%%" ^^
    echo --local-package-dir "%%CYGWIN_ROOT%%\.pkg-cache" ^^
    echo --no-shortcuts ^^
    echo --no-desktop ^^
    echo --delete-orphans ^^
    echo --upgrade-also ^^
    echo --no-replaceonreboot ^^
    echo --quiet-mode ^|^| goto :fail
    if "%DELETE_CYGWIN_PACKAGE_CACHE%" == "yes" (
        echo rd /s /q "%%CYGWIN_ROOT%%\.pkg-cache"
    )
    echo if exist "%CYGWIN_ROOT%\%ROLLING_TUI%" (
    echo    del "%CYGWIN_ROOT%\%ROLLING_TUI%" || goto :fail
    echo )
    echo cscript //Nologo "%DOWNLOADER%" %ROLLING_TUI_URL% "%CYGWIN_ROOT%\%ROLLING_TUI%" || goto :fail
    echo echo.
    echo echo ###########################################################
    echo echo # Updating [Cygwin Portable] succeeded.
    echo echo ###########################################################
    echo timeout /T 60
    echo goto :eof
    echo echo.
    echo :fail
    echo echo ###########################################################
    echo echo # Updating [Cygwin Portable] FAILED!
    echo echo ###########################################################
    echo timeout /T 60
    echo exit /1
) >"%Updater_cmd%" || goto :fail

set Cygwin_bat=%CYGWIN_ROOT%\Cygwin.bat
if exist "%Cygwin_bat%" (
    echo Disabling default Cygwin launcher [%Cygwin_bat%]...
    if exist "%Cygwin_bat%.disabled" (
        del "%Cygwin_bat%.disabled" || goto :fail
    )
    rename "%Cygwin_bat%" Cygwin.bat.disabled || goto :fail
)

set Init_sh=%CYGWIN_ROOT%\init.sh
echo Creating [%Init_sh%]...
(
    echo #!/usr/bin/env bash
    echo.
    echo #
    echo # Map Current Windows User to root user
    echo #
    echo.
    echo # Check if current Windows user is in /etc/passwd
    echo USER_SID="$(mkpasswd -c | cut -d':' -f 5)"
    echo if ! grep -F "$USER_SID" /etc/passwd ^&^>/dev/null; then
    echo     echo "Mapping Windows user '$USER_SID' to cygwin '$USERNAME' in /etc/passwd..."
    echo     GID="$(mkpasswd -c | cut -d':' -f 4)"
    echo     echo $USERNAME:unused:1001:$GID:$USER_SID:$HOME:/bin/bash ^>^> /etc/passwd
    echo fi
    echo.
    echo cp -rn /etc/skel /home/$USERNAME
    echo.
    echo # already set in rolling-tui.cmd:
    echo # export CYGWIN_ROOT=$(cygpath -w /^)
    echo.
    echo #
    echo # adjust Cygwin packages cache path
    echo #
    echo pkg_cache_dir=$(cygpath -w "$CYGWIN_ROOT/.pkg-cache"^)
    echo sed -i -E "s/.*\\\.pkg-cache/"$'\t'"${pkg_cache_dir//\\/\\\\}/" /etc/setup/setup.rc
    echo.
    echo # Make python3 available as python if python2 is not installed
    echo [[ -e /usr/bin/python3 ]] ^|^| /usr/sbin/update-alternatives --install /usr/bin/python3 python3 $^(/usr/bin/find /usr/bin -maxdepth 1 -name "python3.*" -print -quit^) 1
    echo [[ -e /usr/bin/python  ]] ^|^| /usr/sbin/update-alternatives --install /usr/bin/python  python  $^(/usr/bin/find /usr/bin -maxdepth 1 -name "python3.*" -print -quit^) 1
    echo.
    if not "%PROXY_HOST%" == "" (
        echo if [[ $HOSTNAME == "%COMPUTERNAME%" ]]; then
        echo     export http_proxy=http://%PROXY_HOST%:%PROXY_PORT%
        echo     export https_proxy=$http_proxy
        echo fi
    )

) >"%Init_sh%" || goto :fail
"%CYGWIN_ROOT%\bin\dos2unix" "%Init_sh%" || goto :fail

set Start_cmd=%INSTALL_ROOT%rolling-tui.cmd
echo Creating launcher [%Start_cmd%]...
(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo set CWD=%%cd%%
    echo set CYGWIN_DRIVE=%%~d0
    echo set CYGWIN_ROOT=%%~dp0cygwin
    echo.
    echo for %%%%i in ^(adb.exe^) do ^(
    echo    set "ADB_PATH=%%%%~dp$PATH:i"
    echo ^)
    echo.
    echo set PATH=%CYGWIN_PATH%;%%CYGWIN_ROOT%%\bin;%%ADB_PATH%%
    echo set ALLUSERSPROFILE=%%CYGWIN_ROOT%%\.ProgramData
    echo set ProgramData=%%ALLUSERSPROFILE%%
    echo set CYGWIN=nodosfilewarning
    echo.
    echo set USERNAME=%CYGWIN_USERNAME%
    echo set HOME=/home/%%USERNAME%%
    echo set SHELL=/bin/bash
    echo set HOMEDRIVE=%%CYGWIN_DRIVE%%
    echo set HOMEPATH=%%CYGWIN_ROOT%%\home\%%USERNAME%%
    echo set GROUP=None
    echo set GRP=
    echo.
    echo echo Replacing [/etc/fstab]...
    echo ^(
    echo     echo # /etc/fstab
    echo     echo # IMPORTANT: this files is recreated on each start by rolling-tui.cmd
    echo     echo #
    echo     echo #    This file is read once by the first process in a Cygwin process tree.
    echo     echo #    To pick up changes, restart all Cygwin processes.  For a description
    echo     echo #    see https://cygwin.com/cygwin-ug-net/using.html#mount-table
    echo     echo.
    echo     echo # noacl = disable Cygwin's - apparently broken - special ACL treatment which prevents apt-cyg and other programs from working
    echo     echo none /cygdrive cygdrive binary,noacl,posix=0,user 0 0
    echo ^) ^> "%%CYGWIN_ROOT%%\etc\fstab"
    echo.
    echo %%CYGWIN_DRIVE%%
    echo chdir "%%CYGWIN_ROOT%%\bin"
    echo bash "%%CYGWIN_ROOT%%\init.sh"
    echo.
    echo if "%%1" == "" (
    if "%INSTALL_CONEMU%" == "yes" (
        if "%CYGWIN_ARCH%" == "64" (
            echo   start "" "%%~dp0conemu\ConEmu64.exe" %CON_EMU_OPTIONS%
        ) else (
            echo   start "" "%%~dp0conemu\ConEmu.exe" %CON_EMU_OPTIONS%
        )
    ) else (
        echo   mintty --nopin %MINTTY_OPTIONS% --icon %%CYGWIN_ROOT%%\Cygwin-Terminal.ico ./rolling-tui.pyz -
    )
    echo ^) else (
    echo   if "%%1" == "no-mintty" (
    echo     bash --login -i
    echo   ^) else (
    echo     bash --login -c %%*
    echo   ^)
    echo ^)
    echo.
    echo cd "%%CWD%%"
) >"%Start_cmd%" || goto :fail

:: launching Bash once to initialize user home dir
call "%Start_cmd%" whoami

set Bashrc_sh=%CYGWIN_ROOT%\home\%CYGWIN_USERNAME%\.bashrc

find "export PYTHONHOME" "%Bashrc_sh%" >NUL || (
    echo.
    echo export PYTHONHOME=/usr
) >>"%Bashrc_sh%" || goto :fail

if not "%CYGWIN_PACKAGES%" == "%CYGWIN_PACKAGES:ssh-pageant=%" (
    :: https://github.com/cuviper/ssh-pageant
    echo Adding ssh-pageant to [/home/%CYGWIN_USERNAME%/.bashrc]...
    find "ssh-pageant" "%Bashrc_sh%" >NUL || (
        echo.
        echo eval $(/usr/bin/ssh-pageant -r -a "/tmp/.ssh-pageant-$USERNAME"^)
    ) >>"%Bashrc_sh%" || goto :fail
)

if not "%PROXY_HOST%" == "" (
    echo Adding proxy settings for host [%COMPUTERNAME%] to [/home/%CYGWIN_USERNAME%/.bashrc]...
    find "export http_proxy" "%Bashrc_sh%" >NUL || (
        echo.
        echo if [[ $HOSTNAME == "%COMPUTERNAME%" ]]; then
        echo     export http_proxy=http://%PROXY_HOST%:%PROXY_PORT%
        echo     export https_proxy=$http_proxy
        echo     export no_proxy="::1,127.0.0.1,localhost,169.254.169.254,%COMPUTERNAME%,*.%USERDNSDOMAIN%"
        echo     export HTTP_PROXY=$http_proxy
        echo     export HTTPS_PROXY=$http_proxy
        echo     export NO_PROXY=$no_proxy
        echo fi
    ) >>"%Bashrc_sh%" || goto :fail
)
"%CYGWIN_ROOT%\bin\dos2unix" "%Bashrc_sh%" || goto :fail

echo.
echo ###########################################################
echo # Installing [Cygwin Portable] succeeded.
echo ###########################################################
echo.
echo Use [%Start_cmd%] to launch Cygwin Portable.
echo.
timeout /T 60
goto :eof

:fail
    if exist "%DOWNLOADER%" (
        del "%DOWNLOADER%"
    )
    echo.
    echo ###########################################################
    echo # Installing [Cygwin Portable] FAILED!
    echo ###########################################################
    echo.
    timeout /T 60
exit /b 1
