<# Description: 
    Installs UI_Planner Software
    - apache-tomcat-9.0.53-windows-x64             -
    - BCompare-4.3.3.24545.exe                      -
    - eclipse-jee-2021-09-R-win32-x86_64           -
    - jdk-8u291-windows-x64.exe                     -
    - npp.7.8.Installer.x64.exe (Notepad++)         -
    - Office2010Pro64 (excel)                       -
    - putty-64bit-0.70-installer.msi                -
    - sqldeveloper-19.2.1.247.2212-x64              -
    - TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi   -
    - WinSCP.exe                                    -
#>

# CONSTANTS
$softwareDirectory = 'c:\software'

# Copy software from s3
# copy-s3object -bucketname software-01 -keyprefix / -localfolder $softwareDirectory

# Create logger function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build)){new-item -name aws_build -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build\build_log.log)){new-item -name build_log.log -path c:\aws_build -itemtype file}
    add-content -path c:\aws_build\build_log.log -value "$datetime - $message"
}

# # Verify jdk-8u241-windows-x64.exe is Present
# try{
#     $message = "Checking for jdk-8u241-windows-x64.exe..."
#     logger($message)
#     $installerPresent = test-path $softwareDirectory\jdk-8u241-windows-x64.exe
# }
# catch{
#     $message = "Failed while checking for jdk-8u241-windows-x64.exe"
#     logger($message)
# }

# # Install jdk-8u241-windows-x64.exe
# try{
#     if($installerPresent)
#     {
#         $message = "Installing jdk-8u241-windows-x64.exe..."
#         logger($message)
#         $argumentList = 'INSTALL_SILENT=Enable'
#         start-process -filepath $softwareDirectory\jdk-8u241-windows-x64.exe -argumentlist $argumentList -wait
#         if(test-path "c:\Program Files\Java\jdk1.8.0_241"){logger('jdk-8u241-windows-x64.exe installed successfully')}
#         else{logger('jdk-8u241-windows-x64.exe installation failed')}
#     }
#     else {
#         $message = "Could not install jdk-8u241-windows-x64.exe since it is not in $softwareDirectory"
#         logger($message)
#     }
# }
# catch{
#     $message = "Failed installing jdk-8u241-windows-x64.exe"
#     logger($message)
# }

# Verify jdk-8u291-windows-x64.exe is Present
try{
    $message = "Checking for jdk-8u291-windows-x64.exe..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\jdk-8u291-windows-x64.exe
}
catch{
    $message = "Failed while checking for jdk-8u291-windows-x64.exe"
    logger($message)
}

# Install jdk-8u291-windows-x64.exe
try{
    if($installerPresent)
    {
        $message = "Installing jdk-8u291-windows-x64.exe..."
        logger($message)
        $argumentList = 'INSTALL_SILENT=Enable'
        start-process -filepath $softwareDirectory\jdk-8u291-windows-x64.exe -argumentlist $argumentList -wait
        if(test-path "c:\Program Files\Java\jdk1.8.0_241"){logger('jdk-8u291-windows-x64.exe installed successfully')}
        else{logger('jdk-8u291-windows-x64.exe installation failed')}
    }
    else {
        $message = "Could not install jdk-8u291-windows-x64.exe since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing jdk-8u291-windows-x64.exe"
    logger($message)
}

# # Unzip apache-tomcat-8.5.51-windows-x64.zip
# try{
#     Expand-Archive -path $softwareDirectory\apache-tomcat-8.5.51-windows-x64.zip -destination $softwareDirectory -force
# }
# catch{
#     $message = "Failed unzipping apache-tomcat-8.5.51-windows-x64.zip"
#     logger($message)
# }

# # Verify apache-tomcat-8.5.51 Installer is Present
# try{
#     $message = "Checking for apache-tomcat-8.5.51 installer..."
#     logger($message)
#     $installerPresent = test-path $softwareDirectory\apache-tomcat-8.5.51\bin\service.bat
# }
# catch{
#     $message = "Failed while checking for apache-tomcat-8.5.51 installer"
#     logger($message)
# }

# # Install apache-tomcat-8.5.51
# try{
#     if($installerPresent)
#     {
#         $message = "Installing apache-tomcat-8.5.51..."
#         logger($message)
#         cd $softwareDirectory\apache-tomcat-8.5.51\bin
#         $argumentList = 'install'
#         start-process -filepath $softwareDirectory\apache-tomcat-8.5.51\bin\service.bat -argumentlist $argumentList -wait
#         start-sleep 3
#         try{
#             $servicePresent = get-service 'Tomcat8'
#             if($servicePresent)
#             {
#                 $message = 'apache-tomcat-8.5.51 installed successfully'
#                 logger($message)
#             }
#             else{
#                 $message = "Tomcat8 service not found.  Installation may have failed."
#                 logger($message)
#             }
#         }
#         catch{
#             $message = "Tomcat8 service not found.  Installation may have failed."
#             logger($message)
#         }
        
#     }
#     else {
#         $message = "Could not install apache-tomcat-8.5.51 since it is not in $softwareDirectory"
#         logger($message)
#     }
# }
# catch{
#     $message = "Failed installing apache-tomcat-8.5.51"
#     logger($message)
# }

# Unzip apache-tomcat-9.0.53-windows-x64.zip
try{
    Expand-Archive -path $softwareDirectory\apache-tomcat-9.0.53-windows-x64.zip -destination $softwareDirectory -force
}
catch{
    $message = "Failed unzipping apache-tomcat-9.0.53-windows-x64.zip"
    logger($message)
}

# Verify apache-tomcat-9.0.53 Installer is Present
try{
    $message = "Checking for apache-tomcat-9.0.53 installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\apache-tomcat-9.0.53\bin\service.bat
}
catch{
    $message = "Failed while checking for apache-tomcat-9.0.53 installer"
    logger($message)
}

# Install apache-tomcat-9.0.53
try{
    if($installerPresent)
    {
        $message = "Installing apache-tomcat-9.0.53..."
        logger($message)
        cd $softwareDirectory\apache-tomcat-9.0.53\bin
        $argumentList = 'install'
        start-process -filepath $softwareDirectory\apache-tomcat-9.0.53\bin\service.bat -argumentlist $argumentList -wait
        start-sleep 3
        try{
            $servicePresent = get-service 'Tomcat8'
            if($servicePresent)
            {
                $message = 'apache-tomcat-9.0.53 installed successfully'
                logger($message)
            }
            else{
                $message = "Tomcat8 service not found.  Installation may have failed."
                logger($message)
            }
        }
        catch{
            $message = "Tomcat8 service not found.  Installation may have failed."
            logger($message)
        }
        
    }
    else {
        $message = "Could not install apache-tomcat-9.0.53 since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing apache-tomcat-9.0.53"
    logger($message)
}

# Verify Notepad++ Installer is Present
try{
    $message = "Checking for Notepad++ installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\npp.7.8.Installer.x64.exe
}
catch{
    $message = "Failed while checking for Notepad++ installer"
    logger($message)
}

# Install Notepad++
try{
    if($installerPresent)
    {
        $message = "Installing Notepad++..."
        logger($message)
        $argumentList = '/S'
        start-process -filepath $softwareDirectory\npp.7.8.Installer.x64.exe -argumentlist $argumentList -wait
        if(test-path "c:\Program Files\Notepad++"){logger('Notepad++ installed successfully')}
        else{logger('Notepad++ installation failed')}
    }
    else{
        $message = "Could not install Notepad++ since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing Notepad++"
    logger($message)
}

# Verify BCompare-4.3.3.24545.exe installer is present
try{
    $message = "Checking for BCompare-4.3.3.24545.exe installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\BCompare-4.3.3.24545.exe
}
catch{
    $message = "Failed while checking for BCompare-4.3.3.24545.exe installer"
    logger($message)
}

# Install BCompare-4.3.3.24545.exe
## Installer may be affected by mcafee and not releasing the process ##
### Avoid this situation by sleeping instead of using -wait ###
try{
    if($installerPresent)
    {
        $message = "Installing BCompare-4.3.3.24545.exe..."
        logger($message)
        $argumentList = '/SILENT'
        start-process -filepath $softwareDirectory\BCompare-4.3.3.24545.exe -argumentlist $argumentList
        start-sleep 10
        if(test-path "c:\Program Files\Beyond Compare 4\BCompare.exe"){logger('BCompare-4.3.3.24545.exe installed successfully')}
        else{logger('BCompare-4.3.3.24545.exe installation failed')}
    }
    else{
        $message = "Could not install BCompare-4.3.3.24545.exe since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing BCompare-4.3.3.24545.exe"
    logger($message)
}

# Verify putty-64bit-0.70-installer.msi is present
try{
    $message = "Checking for putty-64bit-0.70-installer.msi installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\putty-64bit-0.70-installer.msi
}
catch{
    $message = "Failed while checking for putty-64bit-0.70-installer.msi installer"
    logger($message)
}

# Install putty-64bit-0.70
try{
    if($installerPresent)
    {
        $message = "Installing putty-64bit-0.70-installer.msi..."
        logger($message)
        msiexec.exe /i $softwareDirectory\putty-64bit-0.70-installer.msi /q
        for($i=0; $i -lt 10; $i++)
        {
            if(test-path "c:\program files\Putty\putty.exe"){$installationPresent = $true; $i=10}
            else{start-sleep 3}
        }
        if($installationPresent){logger('putty-64bit-0.70 installed successfully')}
        else{logger('putty-64bit-0.70 installation failed')}
    }
    else{
        $message = "Could not install putty-64bit-0.70 since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing putty-64bit-0.70"
    logger($message)
}

# Verify TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi is present
try{
    $message = "Checking for TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi
}
catch{
    $message = "Failed while checking for TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi installer"
    logger($message)
}

# Install TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi
try{
    if($installerPresent)
    {
        $message = "Installing TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi..."
        logger($message)
        msiexec.exe /i $softwareDirectory\TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi /q
        for($i=0; $i -lt 10; $i++)
        {
            if(test-path "c:\program files\TortoiseSVN\bin\TortoiseMerge.exe"){$i=10; $installationPresent = $true}
            else{start-sleep 3}
        }
        if($installationPresent){logger('TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi installed successfully')}
        else{logger('TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi installation failed')}
    }
    else{
        $message = "Could not install TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing TortoiseSVN-1.13.1.28686-x64-svn-1.13.0.msi"
    logger($message)
}

# Verify WinSCP.exe is present
try{
    $message = "Checking for WinSCP.exe installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\WinSCP-5.9.6-portable\WinSCP.exe
}
catch{
    $message = "Failed while checking for WinSCP.exe installer"
    logger($message)
}

# Install WinSCP.exe
try{
    if($installerPresent)
    {
        $message = "Installing WinSCP.exe..."
        logger($message)
        new-item "c:\Program Files\WinSCP" -itemtype directory
        copy-item $softwareDirectory\WinSCP-5.9.6-portable\*.* "c:\Program Files\WinSCP\"
        start-sleep 3
        if(test-path "c:\Program Files\WinSCP\WinSCP.exe"){logger('WinSCP.exe installed successfully')}
        else{logger('WinSCP.exe installation failed')}
    }
    else{
        $message = "Could not install WinSCP.exe since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing WinSCP.exe"
    logger($message)
}

# # Unzip eclipse-jee-kepler-SR2-win32-x86_64.zip
# try{
#     Expand-Archive -path $softwareDirectory\eclipse-jee-kepler-SR2-win32-x86_64.zip -destination "c:\program files" -force
# }
# catch{
#     $message = "Failed unzipping eclipse-jee-kepler-SR2-win32-x86_64.zip"
#     logger($message)
# }

# # Verify eclipse.exe is present
# try{
#     $message = "Checking for eclipse.exe installer..."
#     logger($message)
#     $installerPresent = test-path "c:\program files\eclipse\eclipse.exe"
#     if(test-path "c:\Program Files\eclipse\eclipse.exe"){logger('eclipse.exe installed successfully')}
#     else{logger('eclipse.exe installation failed')}
# }
# catch{
#     $message = "Failed while checking for eclipse.exe installer"
#     logger($message)
# }

# Unzip eclipse-jee-2021-09-R-win32-x86_64.zip
try{
    Expand-Archive -path $softwareDirectory\eclipse-jee-2021-09-R-win32-x86_64.zip -destination "c:\program files" -force
}
catch{
    $message = "Failed unzipping eclipse-jee-2021-09-R-win32-x86_64.zip"
    logger($message)
}

# Verify eclipse.exe is present
try{
    $message = "Checking for eclipse.exe installer..."
    logger($message)
    $installerPresent = test-path "c:\program files\eclipse\eclipse.exe"
    if(test-path "c:\Program Files\eclipse\eclipse.exe"){logger('eclipse.exe installed successfully')}
    else{logger('eclipse.exe installation failed')}
}
catch{
    $message = "Failed while checking for eclipse.exe installer"
    logger($message)
}

# Verify Office2010Pro64 (excel) is present
try{
    $message = "Checking for Office2010Pro64 (excel) installer..."
    logger($message)
    $installerPresent = test-path $softwareDirectory\Office2010Pro64\setup.exe
}
catch{
    $message = "Failed while checking for Office2010Pro64 (excel) installer"
    logger($message)
}

# Install Office2010Pro64 (excel)
try{
    if($installerPresent)
    {
        $message = "Installing Office2010Pro64 (excel)..."
        logger($message)
        start-process -filepath $softwareDirectory\Office2010Pro64\setup.exe -wait
        if(test-path "c:\Program Files\Microsoft Office\office14\excel.exe"){logger('Office2010Pro64 (excel) installed successfully')}
        else{logger('Office2010Pro64 (excel) installation failed')}
    }
    else{
        $message = "Could not install Office2010Pro64 (excel) since it is not in $softwareDirectory"
        logger($message)
    }
}
catch{
    $message = "Failed installing Office2010Pro64 (excel)"
    logger($message)
}

# Unzip sqldeveloper-19.2.1.247.2212-x64.zip
try{
    Expand-Archive -path $softwareDirectory\sqldeveloper-19.2.1.247.2212-x64.zip -destination "c:\program files" -force
}
catch{
    $message = "Failed unzipping sqldeveloper-19.2.1.247.2212-x64.zip"
    logger($message)
}

# Verify sqldeveloper-19.2.1.247.2212-x64 is present
try{
    $message = "Checking for sqldeveloper.exe..."
    logger($message)
    $installerPresent = test-path "c:\program files\sqldeveloper\sqldeveloper.exe"
    if($installerPresent){logger('sqldeveloper installed successfully')}
    else{logger('sqldeveloper installation failed')}
}
catch{
    $message = "Failed while checking for sqldeveloper.exe"
    logger($message)
}
