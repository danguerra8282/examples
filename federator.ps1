# Description: 

# CONST
$LOGON_PAGE = "https://url.domain.com/page_1/page_2.aspx?CTAuthMode=BASIC&language=en"
$FIM_PAGE = "https://url.domain.com/sso/SSO?SPEntityID=urn:amazon:webservices"

# Generate profiles for the following AWS Accounts (***list the accounts you have access to here***)
$profileList = 
    "123456789" #account_name_x

$username = read-host 'Enter username: '
$password = read-host 'Enter password: ' -AsSecureString
$password = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($password)

# # Get Credentials from local credentials file
# try{
#     $ErrorActionPreference = "stop"
#     $creds = get-content -path $env:USERPROFILE\.aws\authentication
#     if($creds.length -gt 2)
#     {
#         write-host('Too many parameters found in $env:USERPROFILE\.aws\credentials.  Only include username & password.')
#         break
#     }
#     foreach($cred in $creds)
#     {
#         if($cred -match "username:")
#         {
#             $username = $cred.split(':')[1]
#             $username = $username.replace(' ','')
#         }
#         if($cred -match "password:")
#         {
#             $password = $cred.split(':')[1]
#             $password = $password.replace(' ','')
#         }
#     }
# }
# catch{
#     write-host('Failed to get credentials from credentials file.  Verify c:\users\.aws\credentials exists.')
# }

# $form = @{auth_mode='BASIC';orig_url='';app_name='';override_uri_retention='false';user='username';password=''}
$form = @{
    auth_mode='BASIC';
    orig_url='';
    app_name='';
    override_uri_retention='false';
    user=$username;
    password=$password
    }

$logonPageResponse = invoke-webrequest -uri $LOGON_PAGE -method 'POST' -body $form -sessionvariable session
$fimPageResponse = invoke-webrequest -uri $FIM_PAGE -method 'GET' -Websession $session
$samlAssertion = $fimPageResponse.InputFields.value[0]

foreach($item in $profileList)
{
    $rolearn = "arn:aws:iam::" + $item + ":role/Cloud_Role_Name"
    $principalarn = "arn:aws:iam::" + $item + ":saml-provider/samluuid"
    $response = use-stsrolewithsaml -rolearn $rolearn -samlassertion $samlAssertion -principalarn $principalarn
    $accesskey = $response.credentials.AccessKeyId
    $secretkey = $response.credentials.SecretAccessKey
    $sessionkey = $response.credentials.SessionToken
    set-awscredentials -accesskey $accesskey -secretkey $secretkey -sessiontoken $sessionkey -storeas temp
    initialize-awsdefaultconfiguration -profilename temp -region us-east-1
    $accountAlias = Get-IAMAccountAlias
    set-awscredentials -accesskey $accesskey -secretkey $secretkey -sessiontoken $sessionkey -storeas $accountAlias
    Remove-AWSCredentialProfile -ProfileName temp -confirm:$false
    # Get-AWSCredential -ListProfileDetail
}

# Final Action / Cleanup
remove-variable profileList
remove-variable form
remove-variable username
remove-variable password
remove-variable logonPageResponse
remove-variable fimPageResponse
remove-variable samlAssertion
remove-variable item
remove-variable rolearn
remove-variable principalarn
remove-variable accesskey
remove-variable secretkey
remove-variable sessionkey
remove-variable accountAlias





# initialize-awsdefaultconfiguration -profilename default -region us-east-1

# $roles = "CloudEngineer"
# $accounts = 
#     "123", #Sandbox
#     "456", #Dev_Sandbox_1
#     "798" #Dev_Sandbox_2
# foreach ($role in $roles)
# {
#     foreach($account in $accounts)
#     {
#         $tempCreds = use-stsrole -rolesessionname "temp" -rolearn arn:aws:iam::"$account":role/$role
#         ##### EXECUTE ACTIONS STARTING HERE #####
#         Get-IAMAccountAlias -Credential $tempCreds.Credentials
#         get-ec2instance -Credential $tempCreds.Credentials
#         get-s3bucket -Credential $tempCreds.Credentials
#         ##### END EXECUTING ACTIONS HERE #####
#     }
# }

# remove-variable profileList
# remove-variable form
# remove-variable username
# remove-variable password
# remove-variable logonPageResponse
# remove-variable fimPageResponse
# remove-variable samlAssertion
# remove-variable item
# remove-variable rolearn
# remove-variable principalarn
# remove-variable accesskey
# remove-variable secretkey
# remove-variable sessionkey
# remove-variable accountAlias
# remove-variable roles
