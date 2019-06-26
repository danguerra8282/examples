# This will change the IAM Instance Profile to the parameter that is passed in
# This will check to see if the NW-Cloudformation-Instance-Build role is attached to the instance
# and will remove it if found.  This is necessary as the Cloudformation-Instance-Build role
# has a high level of access into AWS.  Leaving the profile attached will be considered a 
# security vulnerability.

# Start log
$logLocation = "c:\nwtools\build"
new-item -path $logLocation -itemType directory -ea SilentlyContinue
new-item -path $logLocation -name nwBuildLog.txt -ItemType file -ea SilentlyContinue
$dateTime = get-date

out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Assigning instance profile:" -append
$localInstanceId = Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/instance-id -ErrorAction SilentlyContinue
$localAssociationId = (Get-EC2IamInstanceProfileAssociation | where {$_.InstanceId -eq $localInstanceId}).AssociationId
$localInstanceId = Get-EC2Instance $localInstanceId
$localInstanceProfile = $localInstanceId.instances.IamInstanceProfile
$instanceTags = $localInstanceId.instances.tags
$iamInstanceProfileTag = ($instanceTags | where {$_.key -eq "IamInstanceProfile"}).value
if($iamInstanceProfileTag -match "CloudFormation-Instance-Build")
{
    out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Restricted IamInstanceProfile:" -append
    out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Removing build profile:" -append
    Unregister-EC2IamInstanceProfile -AssociationId $localAssociationId
}
elseif($iamInstanceProfileTag -eq $null)
{
    out-file -filepath $logLocation\nwBuildLog.txt -inputObject "IamInstanceProfile not specified:" -append
    out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Removing build profile:" -append
    Unregister-EC2IamInstanceProfile -AssociationId $localAssociationId
}
else{
    if($localInstanceProfile.arn -match "CloudFormation-Instance-Build")
    {
        $iamInstanceProfileArn = (Get-IAMInstanceProfile -InstanceProfileName $iamInstanceProfileTag).arn
        $iamInstanceProfileName = (Get-IAMInstanceProfile -InstanceProfileName $iamInstanceProfileTag).InstanceProfileName
        Set-EC2IamInstanceProfileAssociation -AssociationId $localAssociationId -IamInstanceProfile_Arn $iamInstanceProfileArn -IamInstanceProfile_Name $iamInstanceProfileName
        start-sleep -s 3
    }
    remove-variable localInstanceId 
    remove-variable localAssociationId
    remove-variable localInstanceProfile
    $localInstanceProfile = Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/iam/info
    $localInstanceProfile = ($localInstanceProfile.InstanceProfileArn).split('/')[1]
    $localInstanceId = Invoke-RestMethod -uri http://169.254.169.254/latest/meta-data/instance-id -ErrorAction SilentlyContinue
    $localAssociationId = (Get-EC2IamInstanceProfileAssociation | where {$_.InstanceId -eq $localInstanceId}).AssociationId
    if($localInstanceProfile -eq $iamInstanceProfileTag)
    {
        out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Completed assigning instance profile:" -append
    }
    else{
        out-file -FilePath $logLocation\nwBuildLog.txt -inputObject "Assigning instance profile: Failed" -append
        out-file -filepath $logLocation\nwBuildLog.txt -inputObject "Removing build profile:" -append
        Unregister-EC2IamInstanceProfile -AssociationId $localAssociationId
    }
}
