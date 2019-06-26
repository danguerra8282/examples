# This script will assume roles into each account listed in c:\user\userName\.aws\credentials file 
# and will create the specified parameters in SSM Parameter store.
# PREREQS:
#    The CLI AWS-Federator needs to have been installed, configured, and ran before this script
#    will execute successfully.    
#    NOTES:  
#    - This process may change at any time.
#    - This script relies on the AD rights and AWS role of the user who is executing it.  If
#      the user does not have access to create or modify SSM Parameters then this script will
#      execute successfully or complete the desired action.
#    - This script requires the AWS PS Module.

$encryptedParameter = $true
$parameterName = ""
$parameterValue = ""

Remove-Variable nonConfiguredAccounts
Remove-Variable successfullyAlteredAccounts
$awsRegionName = "us-east-1"
$allProfiles = Get-AWSCredential -ListProfileDetail
foreach ($profile in $allProfiles)
{
    if (($profile.ProfileName -match "-CloudAdmin-") -and (!($profile.ProfileName -match "Sandbox")))
    #if ($profile.ProfileName -match "InfraSvcsDev-CLOUDADMIN")
    {
        Initialize-AWSDefaultConfiguration -ProfileName $profile.ProfileName -Region $awsRegionName
        if ($encryptedParameter) # Create Encrypted Parameter
        {
            $kmsKey = Get-KMSKey -KeyId alias/aliasName
            if ($kmsKey -eq $null)
            {
                $nonConfiguredAccounts += "`n"
                $nonConfiguredAccounts += $profile.ProfileName
            }
            elseif ($kmsKey -ne $null)
            {
                Write-SSMParameter -Name $parameterName.ToString() -Value $parameterValue.ToString() -Type "SecureString" -KeyId $kmsKey.arn -Overwrite $true
                $tag1 = New-Object Amazon.SimpleSystemsManagement.Model.Tag
                $tag1.Key = "Infrastructure"
                $tag1.Value = "True"
                Add-SSMResourceTag -ResourceType "Parameter" -ResourceId $parameterName.ToString() -Tag $tag1
                $successfullyAlteredAccounts += "`n"
                $successfullyAlteredAccounts += $profile.ProfileName
            }
            remove-variable kmsKey
        }
        else # Create Un-encrypted Parameter
        {
            Write-SSMParameter -Name $parameterName -Value $parameterValue -Type "String" -Overwrite $true
            $successfullyAlteredAccounts += "`n"
            $successfullyAlteredAccounts += $profile.ProfileName
        }
    }   
}

write-host "NonConfigured Accounts: " $nonConfiguredAccounts
Write-Host "`n"
write-host "Successfully Configured Accounts: " $successfullyAlteredAccounts
Write-Host "`n"

