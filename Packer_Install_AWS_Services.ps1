$AwsRegion = "us-east-1"
Set-DefaultAWSRegion -Region $AwsRegion
Start-Transcript -Path C:\Windows\Temp\transscript_install_aws_services.ps1.txt -Append
Import-Module -Name C:\ProgramData\Amazon\EC2-Windows\Launch\Module\Ec2Launch.psd1; (Get-Module EC2Launch).Version.ToString()
 
#-------------------
# Install CodeDeploy
#-------------------

$BucketName = "aws-codedeploy-us-east-1"

Import-Module AWSPowerShell
Write-Host("Getting CodeDeploy Agent")
Read-S3Object -BucketName $BucketName -Key latest/codedeploy-agent.msi -File C:\Windows\Temp\codedeploy-agent.msi
if (-Not(Test-Path -Path C:\Windows\Temp\codedeploy-agent.msi)) {
  Write-Host("C:\Windows\Temp\codedeploy-agent.msi does not exist")
} else {
  Write-Host("C:\Windows\Temp\codedeploy-agent.msi exist")
}

Write-Host("Installing CodeDeploy Agent")
Start-Process "C:\Windows\Temp\codedeploy-agent.msi" -ArgumentList "/quiet /l C:\Windows\Temp\host-agent-install-log.txt" -Wait
Write-Host("Checking if CodeDeploy Agent is running")
$CodeDeployService = Get-Service -Name codedeployagent -erroraction 'silentlycontinue'
Write-Host("CodeDeploy Agent Status is " + $CodeDeployService.Status)

#-------------------
# Install IIS
#-------------------
#Write-Host("Installing WebServer")
#Install-WindowsFeature -name Web-Server -IncludeManagementTools
#Import-Module WebAdministration

#$sites = Get-Website | where {$_.State -eq 'Stopped'}
#if ($sites) {
#  Write-Host($sites)
#  Write-Host("Starting WebSite " + $site.Name)
#  Start-Website $sites.Name
#} else {
#  Write-Host("Default Website started")
#}
#-------------------
#copy in software from S3
#-------------------
Copy-S3Object -BucketName bucketName -KeyPrefix InstanceBuilder -LocalFolder c:\nwtools\build\InstanceBuilder
New-Item -itemtype  directory -path c:\nwtools\build\software
try
{
    
    $keys = @()
    $contents = get-s3object -bucketname bucketName -keyprefix Software
    $allKeys = $contents.key
    foreach ($key in $allKeys)
    {
        if ($keys -notcontains ($key.split('/')[1]))
        {
            $keys += $key.split('/')[1]
        }
    }
    $keys

    if (test-path c:\nwtools\build\software)
    {
        foreach ($folderkey in $keys)
        {
            if ($folderkey -ne "")
            {
                if ((get-childitem -path c:\nwtools\build\software).name -notcontains $folderkey)
                {
                    Copy-S3Object -BucketName bucketName -KeyPrefix Software/$folderkey -LocalFolder c:\nwtools\build\Software\$folderkey
                }
            }
        }
    }
}
catch [Exception]{
Write-Host $_.Exception.ToString()
Write-Host 'Command execution failed.'
$host.SetShouldExit(1)
}

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
C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\InitializeInstance.ps1 -Schedule

#--------------------
# Set Startup Script
#--------------------
schtasks.exe /create /tn "cfn-init_startup" /ru SYSTEM /Sc ONSTART /tr "powershell C:\nwtools\build\InstanceBuilder\Windows-CfnInit-StartupScript.ps1"

#--------------------
# Sysprep Image
#--------------------
$sysPrepInstanceFile = "C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\SysprepInstance.ps1"
(Get-Content $sysPrepInstanceFile -Verbose).Replace("/shutdown ", "") | Set-Content $sysPrepInstanceFile -Verbose
Start-Sleep -s 20
C:\ProgramData\Amazon\EC2-Windows\Launch\Scripts\SysprepInstance.ps1
