$AwsRegion = "us-east-1"
Set-DefaultAWSRegion -Region $AwsRegion
Start-Transcript -Path C:\Windows\Temp\transscript_install_aws_services.ps1.txt -Append
Import-Module -Name C:\ProgramData\Amazon\EC2-Windows\Launch\Module\Ec2Launch.psd1; (Get-Module EC2Launch).Version.ToString()

#--------------------
# Set IP-hexadecimal Naming Convention
#--------------------
try {
    $file = get-content -path C:\programdata\Amazon\EC2-Windows\Launch\Config\LaunchConfig.json
    $file = $file -replace '"setComputerName": false', '"setComputerName": true'
    set-content -path C:\programdata\Amazon\EC2-Windows\Launch\Config\LaunchConfig.json $file
}
catch {
    Write-Host("Failed setting IP-hexadecimal host naming convention")
}

#--------------------
# Install WindowsFeatures
#--------------------
Add-WindowsFeature -Name RSAT-AD-Tools 

#--------------------
# Setup Password Retrieval
#--------------------
"Setting password retrieval..."
C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\InitializeInstance.ps1 -Schedule
"Set password retrieval!"

#--------------------
# Set Startup Script
#--------------------
# schtasks.exe /create /tn "cfn-init_startup" /ru SYSTEM /Sc ONSTART /tr "powershell C:\tools\build\InstanceBuilder\Windows-CfnInit-StartupScript.ps1"

#--------------------
# Sysprep Image
#--------------------
$sysPrepInstanceFile = "C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\SysprepInstance.ps1"
(Get-Content $sysPrepInstanceFile -Verbose).Replace("/shutdown ", "") | Set-Content $sysPrepInstanceFile -Verbose
"Set Content for Sysprep Image..."
Start-Sleep -s 10
"Sysprep Image..."
C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\SysprepInstance.ps1
