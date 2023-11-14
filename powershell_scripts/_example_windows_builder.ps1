<#
    This script will configure a newly deployed EC2 instance sourced from the Amazon Machine Image (AMI)
    created by the _example_windows_image_bootstrap.ps1 script.

    Includes:
    - Format Disks and Volumes
    - CrowdStrike installation
    - Automox installation
    - Domain join
    - Reboot
#>

# Create logger function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build)){new-item -name aws_build -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build\build_log.log)){new-item -name build_log.log -path c:\aws_build -itemtype file}
    add-content -path c:\aws_build\build_log.log -value "$datetime - $message"
}

# Format Disks and Volumes
try{
    $message = "Formatting disks and volumes..."
    logger($message)

}
catch{
    $message = "Failed formatting disks and volumes"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Install CrowdStrike (Move into Windows Image)
# https://www.crowdstrike.com/blog/tech-center/install-falcon-datacenter/
try{
    $message = "Installing CrowdStrike..."
    logger($message)
    $password = (Get-SSMParameter -Name crowdstrike_cid -WithDecryption $true).value
    $arguments = "/install /quiet /norestart CID=$password NO_START=1"
    Start-Process "C:\aws_build\software\Crowdstrike\Windows\WindowsSensor.MaverickGyr.exe" -ArgumentList $arguments -wait
}
catch{
    $message = "Failed installing CrowdStrike"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Install Automox
try{
    $message = "Installing Automox..."
    logger($message)
    $password = (Get-SSMParameter -Name automox_access_key -WithDecryption $true).value
    $arguments = "/i C:\aws_build\software\Automox\Automox_Installer-1.42.13.msi /qn /norestart ACCESSKEY=$password" # GROUP="Default Group/My Destination Group"'
    Start-Process C:\Windows\System32\msiexec.exe -ArgumentList $arguments -wait
}
catch{
    $message = "Failed installing Automox"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Join Domain
try{
    $username = (Get-SSMParameter -Name domain_join_username -WithDecryption $true).value
    $password = (Get-SSMParameter -Name domain_join_password -WithDecryption $true).value
    $password = ConvertTo-SecureString $password -AsPlainText -Force
    $domain = (Get-SSMParameter -Name domain_join_domain -WithDecryption $true).value
    $creds = New-Object System.Management.Automation.PSCredential -ArgumentList $username, $password
    Add-Computer -DomainName $domain -Credential $creds
}
catch{}

# Reboot
Shutdown -r -t 0
