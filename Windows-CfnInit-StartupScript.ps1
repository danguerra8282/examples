<#
    Startup script that sleeps for 1 minute and then executes the cfn-init.exe if it hasn't already executed
#>


$loggingLocation = "c:\nwtools\build"
function logger ($argument)
{
    if (!(get-command logger -ErrorAction SilentlyContinue))
    {
        if (!(test-path $loggingLocation)){new-item -path $loggingLocation -ItemType Directory}
        new-item -Path $loggingLocation -ItemType file -name "nwBuildLog.txt"
    }
    $dateTime = get-date
    out-file -filepath $loggingLocation\nwBuildLog.txt -inputObject "$dateTime - " -append
    out-file -filepath $loggingLocation\nwBuildLog.txt -inputObject $argument -append
}

# Sleep for 1 minute
Start-Sleep -s 60

# Check for c:\cfn
try{
    $pathExists = test-path C:\cfn
    if($pathExists){
        $executeScript = $false
    }
    if(!($pathExists)){
        $executeScript = $true
    }
}
catch{
    $Error
    logger("Failed checking cfn path")
}

# Execute Startup Script if necessary.  
#  If the user-data cannot be returned then the InitializeInstance commands will be reset and the server rebooted.
#   This is to attempt to handle potential issues between the instance and AWS.
try {
    if($executeScript -eq $true){
        # Get cfn-init execution for local instance
        $cfnScript = Invoke-RestMethod -uri http://169.254.169.254/latest/user-data

        # Execute cfn-init.exe
        if($cfnScript.script)
        {
            logger("Executing " + $cfnScript.script)
            invoke-expression $cfnScript.script
            $removeStartUpTask = $true
        }
        elseif($cfnScript.powershell)
        {
            logger("Executing " + $cfnScript.powershell)
            invoke-expression $cfnScript.powershell
            $removeStartUpTask = $true
        }
        elseif($cfnScript)
        {
            logger("Executing " + $cfnScript)
            invoke-expression $cfnScript
            $removeStartUpTask = $true
        }
        else{logger("cfnScript was unretrievable.  Resetting agents...");. C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\InitializeInstance.ps1 -schedule; start-sleep -s 5; restart-computer -force}

        # Remove Startup Tasks
        if($removeStartUpTask)
        {
            schtasks.exe /Delete /tn "cfn-init_startup" /f
        }
    }
    if($executeScript -eq $false){
        # Cleanup startup script to prevent future executions
        logger("cfn-init already running")
        schtasks.exe /Delete /tn "cfn-init_startup" /f
    }
}
catch {
    $error
    logger("Failed during cfnScript execution")
    logger($error)
}


