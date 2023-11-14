<#
    This script will prepare a newly deployed EC2 instance to be turned into an Amazon Machine Image (AMI).

    Includes:
    - Logger Function
    - AWS Powershell module installation
    - AWS CLI installation
    - RSAT tools
    - Setting Timezone
    - Setting Hexidecimal naming convention
    - Setting the local Administrator & password
    - Setting DNS Servers
    - Setting DNS Search Suffix
    - Copying required software locally to be included in the image
    - .NET 3.5 installation
    - Validation of the EC2Launch config
    - Sysprep execution
#>

# CONST
$DNS_SERVER_0 = "1.2.3.4"
$DNS_SERVER_1 = "2.3.4.5"


# Create logger function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build)){new-item -name aws_build -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build\build_log.log)){new-item -name build_log.log -path c:\aws_build -itemtype file}
    add-content -path c:\aws_build\build_log.log -value "$datetime - $message"
}

# Import AWS Powershell Module
try{
    $message = "Importing AWS Powershell Module..."
    logger($message)
    Import-Module AWSPowerShell
}
catch{
    $message = "Failed importing AWS Powershell Module"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Install AWS CLI
try{
    $message = "Installing AWS CLI..."
    logger($message)
    Start-Process C:\Windows\System32\msiexec.exe -ArgumentList "/i https://awscli.amazonaws.com/AWSCLIV2.msi /passive" -wait
}
catch{
    $message = "Failed while installing AWS CLI"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Install RSAT Tools
try{
    $message = "Installing Windows RSAT Tools..."
    logger($message)
    Add-WindowsFeature -Name RSAT-AD-Tools 
}
catch{
    $message = "Failed installing Windows RSAT Tools"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Set EST Timezone
try{
    $message = "Setting EST Timezone..."
    logger($message)
    Set-TimeZone -Id "Eastern Standard Time"
}
catch{
    $message = "Failed setting EST Timezone"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Set Hexadecimal Naming Convention
try{
    $message = "Setting Hexadecimal Naming Convention..."
    logger($message)
    $file = get-content -path C:\ProgramData\Amazon\EC2Launch\config\agent-config.yml
    Add-Content -Path C:\ProgramData\Amazon\EC2Launch\config\agent-config.yml -Value '  - task: setHostName'
    Add-Content -Path C:\ProgramData\Amazon\EC2Launch\config\agent-config.yml -Value '    inputs:'
    Add-Content -Path C:\ProgramData\Amazon\EC2Launch\config\agent-config.yml -Value '      reboot: false'
}
catch{
    $message = "Failed setting Hexadecimal Naming Convention"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Set Windows Admin Password - WE SHOULD CHANGE THIS TO DISABLE "ADMINISTRATOR" AND CREATE A NEW USER FOR SECURITY BEST PRACTICES
try{
    $message = "Setting Windows Server Admin Password..."
    logger($message)
    $password = (Get-SSMParameter -Name windows_server_admin -WithDecryption $true).value
    $password = ConvertTo-SecureString $password -AsPlainText -Force
    Set-LocalUser -name "Administrator" -Password $password
}
catch{
    $message = "Failed setting Windows Server Admin Password"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Set DNS Servers
try{
    $message = "Setting DNS Servers..."
    logger($message)
    $interface_index = (Get-DnsClientServerAddress -AddressFamily "IPv4" -InterfaceAlias "Ethernet*").InterfaceIndex
    Set-DnsClientServerAddress -InterfaceIndex $interface_index -ServerAddresses ($DNS_SERVER_0, $DNS_SERVER_1)
}
catch{
    $message = "Failed setting DNS Servers"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Set DNS Search Suffixes
try{
    $message = "Setting DNS Search Suffixes..."
    logger($message)
    Set-DnsClientGlobalSetting -SuffixSearchList @("domain.net", "us-east-1.ec2-utilities.amazonaws.com", "ec2.internal")
}
catch{
    $message = "Failed setting DNS Search Suffixes"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Copy Software Locally
try{
    $message = "Copying software locally ..."
    logger($message)
    Copy-S3Object -BucketName "%account_id%-bucket-name" -KeyPrefix * -LocalFolder c:\aws_build\software
}
catch{
    $message = "Failed copying software locally"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Install .NET 3.5
try{
    $message = "Installing .NET 3.5 ..."
    logger($message)
    install-WindowsFeature -name "NET-Framework-Features"
}
catch{
    $message = "Failed installing .NET 3.5"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# Validate EC2Launch agent-config.yml
try{
    $message = "Validating EC2Launch agent-config.yml..."
    logger($message)
    $response = C:\"Program Files"\Amazon\EC2Launch\EC2Launch.exe validate
    if ($response -match "Valid EC2Launch configuration file agent-config.yml"){
        $message = $response
        logger($message)
    }
    else{
        $message = $response
        logger($message)
        write-host("Review C:\aws_build\build_log.txt for more information") -ForegroundColor Red
        break
    }
}
catch{
    $message = "Failed validating EC2Launch agent-config.yml"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}

# SysPrep and Shutdown
try{
    $message = "SysPrepping Instance and Shutting Down..."
    logger($message)
    C:\"Program Files"\Amazon\EC2Launch\EC2Launch.exe sysprep -s
}
catch{
    $message = "Failed SysPrep"
    logger($message)
    write-host($message) -ForegroundColor Red
    break
}
