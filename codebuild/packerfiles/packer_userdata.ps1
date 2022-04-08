<powershell>
Start-Transcript -Path C:\Windows\Temp\transscript_packer_userdata.ps1.txt -Append
write-output "Running User Data Script"
write-host "(host) Running User Data Script"

Set-ExecutionPolicy Unrestricted -Scope LocalMachine -Force -ErrorAction Ignore

# Don't set this before Set-ExecutionPolicy as it throws an error
# $ErrorActionPreference = "stop"

# Remove HTTP listener
Remove-Item -Path WSMan:\Localhost\listener\listener* -Recurse

$Cert = New-SelfSignedCertificate -CertstoreLocation Cert:\LocalMachine\My -DnsName "packer"
New-Item -Path WSMan:\LocalHost\Listener -Transport HTTPS -Address * -CertificateThumbPrint $Cert.Thumbprint -Force

# WinRM
write-output "Setting up WinRM"
write-host "(host) setting up WinRM"

cmd.exe /c winrm quickconfig -q
cmd.exe /c winrm set "winrm/config" '@{MaxTimeoutms="1800000"}'
cmd.exe /c winrm set "winrm/config/winrs" '@{MaxMemoryPerShellMB="1024"}'
cmd.exe /c winrm set "winrm/config/service" '@{AllowUnencrypted="true"}'
cmd.exe /c winrm set "winrm/config/client" '@{AllowUnencrypted="true"}'
cmd.exe /c winrm set "winrm/config/service/auth" '@{Basic="true"}'
cmd.exe /c winrm set "winrm/config/client/auth" '@{Basic="true"}'
cmd.exe /c winrm set "winrm/config/service/auth" '@{CredSSP="true"}'
cmd.exe /c winrm set "winrm/config/listener?Address=*+Transport=HTTPS" "@{Port=`"5986`";Hostname=`"packer`";CertificateThumbprint=`"$($Cert.Thumbprint)`"}"
cmd.exe /c netsh advfirewall firewall set rule group="remote administration" new enable=yes
cmd.exe /c netsh firewall add portopening TCP 5986 "Port 5986"
cmd.exe /c net stop winrm
cmd.exe /c sc config winrm start= auto
cmd.exe /c net start winrm

# Set-ExecutionPolicy RemoteSigned
# Open Port 80 for ELB HealthCheck and Port 443 for CodeDeploy Agent
write-output "Setting up Windows Firewall for ELB HealthCheck"
cmd.exe /c netsh advfirewall firewall add rule name="ELB HealthCheck on Port 80" dir=in action=allow protocol=TCP localport=80
cmd.exe /c netsh advfirewall firewall add rule name="CodeDeploy Comm on Port 443" dir=in action=allow protocol=TCP localport=443
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

##### TEMPORARY - REMOVE THIS ONCE WORKING - #####
$aPassword = convertto-securestring "_password_value_" -asplaintext -force
new-localuser "_name_" -password $aPassword -Fullname "_name_" -Description "_name_ local user"
add-localgroupmember -group "Administrators" -member "_name_"
##### TEMPORARY - REMOVE THIS ONCE WORKING - #####

</powershell>
