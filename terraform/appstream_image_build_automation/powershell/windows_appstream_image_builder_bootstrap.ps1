Import-Module Microsoft.Powershell.LocalAccounts

#Create local administrator for remote WinRM
Write-Host "Obtaining local administrator credentials from Secrets Manager."
$secret_response = Get-SECSecretValue -SecretId "appstream_image_builder_admin" -ProfileName appstream_machine_role
$secret = $secret_response.SecretString | ConvertFrom-Json

$username = $secret.username
$password = $secret.password | ConvertTo-SecureString -AsPlainText -Force

Write-Host "Found credentials for $username."

Write-Host "Creating local user and adding to local administrators group."
New-LocalUser $username -Password $password -Description "Image Builder Remote WinRM administrator"
Add-LocalGroupMember -Group "Administrators" -Member $username

#Configure remote WinRM services
Write-Host "Enabling PSRemoting and WinRM Configuration."
Enable-PSRemoting -SkipNetworkProfileCheck -Force

#Opens basic authentication from Lambda functions to Image Builder
#These settings should be reviewed and modified as appropriate for fleet instances
winrm set winrm/config/client/auth '@{Basic="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

#The network connection profile for non-domain joined machines defaults to Public
#This needs to be set to Private to allow the default Remote WinRM Firewall rules to function
$DomainCheck = (Get-WmiObject -Class Win32_computerSystem).PartOfDomain
if (-not $DomainCheck) {
    #The Unidentified network is the AppStream streaming/mangement network
	#Select the other network in customer VPC
	$ConnProfiles = Get-NetConnectionProfile | Where-Object {$_.Name  -NotLike "*Unidentified network*"}
    ForEach ($Profile in $ConnProfiles)
    {
        #Change Network Category to Private
		Set-NetConnectionProfile -Name $Profile.Name -NetworkCategory Private
    }
}
