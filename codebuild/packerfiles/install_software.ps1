# -------------------
# Copy in software from S3
# -------------------
write-host("-------- Copy Software --------")
Copy-S3Object -BucketName windows-instance-builder -KeyPrefix InstanceBuilder -LocalFolder c:\tools\build\InstanceBuilder
Copy-S3Object -BucketName windows-instance-builder -KeyPrefix Software -LocalFolder c:\tools\build\Software

# -------------------
# Install Softare
# -------------------
write-host("-------- Install Software --------")
write-host("Remediate Log4j Vulnerability")
cd C:\tools\build\Software\log4j_fix
cmd.exe /c "log4j_fix.bat"

write-host(" --- Install McAfee ---")
cmd.exe /c C:\tools\build\Software\McAfee\VSCANSVR.exe
cd C:\tools\build\software\McAfee\Mcafee_Agent_ENS_Install
cmd.exe /c C:\tools\build\Software\McAfee\Mcafee_Agent_ENS_Install\Install_Agent.bat
# cmd.exe /c C:\tools\build\Software\McAfee\Mcafee_Agent_ENS_Install\Install_ENS.bat
cmd.exe /c C:\tools\build\Software\McAfee\Mcafee_Agent_ENS_Install\Install_EDR.bat

write-host(" --- Depersonalize McAfee ---")
cd "C:\Program Files\McAfee\Agent"
.\maconfig.exe -enforce -noguid

write-host(" --- Patch ESRI Software ---")
cd C:\Progra~1\ArcGIS\Server\tools\patchnotification
cmd.exe /c "patchnotification.bat -c -i all"



