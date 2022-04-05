<# 
Name:           federator-f5apm.ps1
Description:    This script prompts for username & password and will then log into 
                Federated Identity Management webpage.  Each account specified
                in the $profileList will be attempted to authenticate to and 
                temporary (1 Hour) AWS credentials will be stored locally.  These
                credentials can then be assumed using the following commands and 
                then any API actions can be executed as long as they are allowed
                by your role in AWS.
                EXAMPLE:
                $awsRegionName = "us-east-1"
                $allProfiles = Get-AWSCredential -ListProfileDetail
                foreach ($profile in $allProfiles)
                {
                    Initialize-AWSDefaultConfiguration -ProfileName $profile.ProfileName -Region $awsRegionName
                    Get-IamAccountAlias
                    Get-ec2instance
                }
Requirements:   powershell & aws powershell module
                https://aws.amazon.com/powershell/
Notes:          Actually federated access...
#>

# Addresses SSL/TLS; which may be encountered
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Ssl3, [Net.SecurityProtocolType]::Tls, [Net.SecurityProtocolType]::Tls11, [Net.SecurityProtocolType]::Tls12

# Remove All Previous Profiles (this makes everything happen a little faster)
$all_profiles = Get-AWSCredential -ListProfileDetail
foreach($profile in $all_profiles){
    "Removing Profile: " + $profile.ProfileName
    remove-awscredentialprofile -profilename $profile.ProfileName -confirm:$false
}

# CONST
$F5_APM_PAGE = "https://site.domain.com"
$F5_APM_POLICY_PAGE = $F5_APM_PAGE + "/my.policy"
$F5_APM_PAGE_RES_PAGE = $F5_APM_PAGE + "/saml/idp/res?id=/Common/AWS.res"

$username = read-host 'Enter username: '
$password = read-host 'Enter password: ' -AsSecureString
$password = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($password)

$form = @{
    auth_mode='BASIC';
    orig_url='';
    app_name='';
    override_uri_retention='false';
    fieldId='';
    username=$username;
    password=$password
    }

$c = invoke-webrequest -uri $F5_APM_PAGE -method 'POST' -SessionVariable session
$s = invoke-webrequest -uri $F5_APM_POLICY_PAGE -method 'POST' -body $form -Websession $session
$t = invoke-webrequest -uri $F5_APM_PAGE_RES_PAGE -method 'POST' -body $form -Websession $session
$saml_assertion = $t.RawContent
$saml_assertion = $saml_assertion -split ' <input type="hidden" name="SAMLResponse" value="'
$saml_assertion = $saml_assertion[1] -split '"/><noscript>'
$decoded_saml = [System.Text.Encoding]::ASCII.GetString([System.Convert]::FromBase64String($saml_assertion[0]))

$roles = $decoded_saml -split '<saml2:Attribute xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion" Name="https://aws.amazon.com/SAML/Attributes/Role" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">'
$roles = [System.Collections.Generic.List[System.Object]]($roles)
$roles.RemoveAt(0)

$roles = $roles -split '<saml2:AttributeValue xmlns:saml2="urn:oasis:names:tc:SAML:2.0:assertion">'
$roles = [System.Collections.Generic.List[System.Object]]($roles)
$roles.RemoveAt(0)
$roles.RemoveAt($roles.count - 1)

try{
    foreach($item in $roles){
        $region = 'us-east-1'
        $item = ($item -split '</saml2:AttributeValue>')[0]
        $principalarn,$rolearn = ($item -split ',')
        $role = ($rolearn -split '/')[1]

        if ($role -match 'DR_'){
            $region = 'us-west-2'
        }

        if ($role -notmatch 'DR_'){
            Write-Host("Creating profile for $rolearn...") -ForegroundColor Yellow
            $response = use-stsrolewithsaml -rolearn $rolearn.trim() -samlassertion $saml_assertion[0] -principalarn $principalarn.trim()
            $accesskey = $response.credentials.AccessKeyId
            $secretkey = $response.credentials.SecretAccessKey
            $sessionkey = $response.credentials.SessionToken
            set-awscredentials -accesskey $accesskey -secretkey $secretkey -sessiontoken $sessionkey -storeas temp
            initialize-awsdefaultconfiguration -profilename temp -region $region
            $accountAlias = Get-IAMAccountAlias
            set-awscredentials -accesskey $accesskey -secretkey $secretkey -sessiontoken $sessionkey -storeas $accountAlias/$role
            Remove-AWSCredentialProfile -ProfileName temp -confirm:$false
            ''
        }
    }
}
catch{
    write-host("An error occurred!") -ForegroundColor Red
}

# Final Action / Cleanup
remove-awscredentialprofile -profilename default -confirm:$false
remove-variable form
remove-variable username
remove-variable password
remove-variable c
remove-variable s
remove-variable t
remove-variable decoded_saml
remove-variable saml_assertion
remove-variable roles
remove-variable item
remove-variable rolearn
remove-variable principalarn
remove-variable accesskey
remove-variable secretkey
remove-variable sessionkey
remove-variable accountAlias
