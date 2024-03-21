$blocked_apps_array = @(
    "msedge",
    "msedge.exe",
    "iexplore",
    "iexplore.exe",
    "powershell",
    "powershell.exe",
    "cmd",
    "cmd.exe"
)

# Create Logger Function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build_logging)){new-item -name aws_build_logging -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build_logging\aws_build_logging.log)){new-item -name aws_build_logging.log -path c:\aws_build_logging -itemtype file}
    add-content -path c:\aws_build_logging\aws_build_logging.log -value "$datetime - $message"
}

# Install modules
try{
    logger("Installing modules...")
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force;
    Install-Module -Name PolicyFileEditor -RequiredVersion 3.0.0  -Force -AllowClobber
}
catch{
    logger("Failed Installing modules")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Set Registry to Block Apps from Executing
try{
    logger("Start Set Registry to Block Apps from Executing...")

    $UserDir = "$env:windir\system32\GroupPolicy\User\registry.pol"
    $RegPath = 'Software\Microsoft\Windows\CurrentVersion\Policies\Explorer'
    $RegName = 'DisallowRun'
    $RegData = '1'
    $RegType = 'DWord'
    Set-PolicyFileEntry -Path $UserDir -Key $RegPath -ValueName $RegName -Data $RegData -Type $RegType

    # Start at 20 to avoid Image-Assistant overwrite
    $counter = 20
    foreach ($app in $blocked_apps_array){
        $RegPath = 'Software\Microsoft\Windows\CurrentVersion\Policies\Explorer\DisallowRun'
        $RegName = $counter
        $RegData = $app
        $RegType = 'String'
        Set-PolicyFileEntry -Path $UserDir -Key $RegPath -ValueName $RegName -Data $RegData -Type $RegType
        $counter += 1
    }

    gpupdate.exe /force
}
catch{
    logger("Failed Set Registry to Block Apps from Executing")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}