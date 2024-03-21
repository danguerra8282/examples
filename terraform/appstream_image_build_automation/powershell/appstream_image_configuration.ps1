# # CONST
# $ACCOUNT_ID = "678045222280"

# Create Logger Function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build_logging)){new-item -name aws_build_logging -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build_logging\aws_build_logging.log)){new-item -name aws_build_logging.log -path c:\aws_build_logging -itemtype file}
    add-content -path c:\aws_build_logging\aws_build_logging.log -value "$datetime - $message"
}

# # Copy Software from S3
# try {
#     logger("Start Copy Software from S3...")
#     # Copy-S3Object -BucketName "$ACCOUNT_ID-appstream-software" -KeyPrefix * -LocalFolder c:\aws_build\software -profilename appstream_machine_role
#     Read-S3Object -BucketName "$ACCOUNT_ID-appstream-software" -KeyPrefix * -Folder c:\aws_build\software -ProfileName appstream_machine_role
# }
# catch {
#     logger("Failed Copy Software from S3")
#     $Error[0].Exception.Message
#     logger($Error[0].Exception.Message)
# }

# Install Firefox
try {
    logger("Start Install Firefox...")
    $arguments = "/s"
    Start-Process "C:\aws_build\software\Firefox\Firefox Installer.exe" -argumentlist $arguments
    start-sleep -s 180
}
catch {
    logger("Failed Install Firefox")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Kill Firefox Process
try{
    logger("Killing Firefox Processes...")
    $firefox_processes = get-process firefox
    foreach($process in $firefox_processes){
        Stop-Process $process.id -force
    }
}
catch{
    logger("Failed Killing Firefox Processes")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Configure Firefox
try {
    logger("Start Configure Firefox...")
    copy-item "C:\aws_build\software\Firefox\local-settings.js" "C:\Program Files\Mozilla Firefox\defaults\pref"
    copy-item "C:\aws_build\software\Firefox\mozilla.cfg" "C:\Program Files\Mozilla Firefox"
    copy-item "C:\aws_build\software\Firefox\override.ini" "C:\Program Files\Mozilla Firefox"
}
catch {
    logger("Failed Configure Firefox")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Launch Firefox for the First Time
try {
    logger("Launch Firefox for the First Time...")
    start-process "C:\Program Files\Mozilla Firefox\firefox.exe"
    start-sleep -s 5
    logger("Killing Firefox Processes...")
    $firefox_processes = get-process firefox
    foreach($process in $firefox_processes){
        Stop-Process $process.id -force
    }
}
catch {
    logger("Failed Launch Firefox for the First Time")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Signal Completion
# How can this be done?
