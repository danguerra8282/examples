<#  This script enables wmi_class to be accessable on the local server
    by remote users (anyone in both the Performance Moonitor Users & 
    Distributed COM Users local group).  If the wmi modules/security 
    is modified after the script is executed it will overwrite some of 
    the configurations that was applied by this script.  
    
    This script will call 'Set-WmiNamespaceSecurity.ps1' from the 
    directory that this script is executed from and is to be 
    considered a dependancy.
    
    Example Commands that can be called remotely:
    get-wmiobject -query "SELECT * FROM MSFC_FCAdapterHBAAttributes" -Computername computerName1
    get-wmiobject -query "SELECT * FROM MSFC_FibrePortHBAAttributes" -Computername computerName1
#>

########## THIS ENABLES REMOTE WMI CALLS ##########
add-localgroupmember -group "Distributed COM Users" -member "domain\user" -confirm:$false
add-localgroupmember -group "Performance Monitor Users" -member "domain\user" -confirm:$false

# Execute WMI Security Changes
.\Set-WmiNamespaceSecurity.ps1 root add "Distributed COM Users" Enable,Enable
.\Set-WmiNamespaceSecurity.ps1 root add "Distributed COM Users" Enable,MethodExecute
.\Set-WmiNamespaceSecurity.ps1 root add "Distributed COM Users" Enable,RemoteAccess
.\Set-WmiNamespaceSecurity.ps1 root add "Performance Monitor Users" Enable,Enable
.\Set-WmiNamespaceSecurity.ps1 root add "Performance Monitor Users" Enable,MethodExecute
.\Set-WmiNamespaceSecurity.ps1 root add "Performance Monitor Users" Enable,RemoteAccess

# Set Service Control Manager level permissions
sc.exe sdset SCMANAGER "D:(A;;CCLCRPRC;;;AU)(A;;CCLCRPWPRC;;;SY)(A;;KA;;;BA)S:(AU;FA;KA;;;WD)(AU;OIIOFA;GA;;;WD)"
########## THIS ENABLES REMOTE WMI CALLS ##########
