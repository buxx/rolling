@echo off

echo Update rolling ...
cygwin\bin\bash --login -i -c "/bin/bash /bin/update_rolling.sh" || goto :fail

echo Updated finished
timeout /T 20
