# Create Logger Function
function logger ($message)
{
    $datetime = get-date -format "MM/dd/yyyy HH:mm:ss"
    if(!(test-path c:\aws_build_logging)){new-item -name aws_build_logging -path c:\ -itemtype directory}
    if(!(test-path c:\aws_build_logging\aws_build_logging.log)){new-item -name aws_build_logging.log -path c:\aws_build_logging -itemtype file}
    add-content -path c:\aws_build_logging\aws_build_logging.log -value "$datetime - $message"
}

# Install Firefox
try {
    logger("Start Install Firefox...")
    $arguments = "/s"
    Start-Process "C:\aws_build\Firefox\Firefox Installer.exe" -argumentlist $arguments
    start-sleep -s 90
}
catch {
    logger("Failed Install Firefox")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Kill Firefox Process
try{
    logger("Killing Firefox Processes...")
    $firefox_processes = get-process firefox
    foreach($process in $firefox_processes){
        Stop-Process $process.id -force
    }
}
catch{
    logger("Failed Killing Firefox Processes")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Configure Firefox
try {
    logger("Start Configure Firefox...")
    copy-item "C:\aws_build\Firefox\local-settings.js" "C:\Program Files\Mozilla Firefox\defaults\pref"
    copy-item "C:\aws_build\Firefox\mozilla.cfg" "C:\Program Files\Mozilla Firefox"
    copy-item "C:\aws_build\Firefox\override.ini" "C:\Program Files\Mozilla Firefox"
}
catch {
    logger("Failed Configure Firefox")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Launch Firefox for the First Time
try {
    logger("Launch Firefox for the First Time...")
    start-process "C:\Program Files\Mozilla Firefox\firefox.exe"
    start-sleep -s 5
    logger("Killing Firefox Processes...")
    $firefox_processes = get-process firefox
    foreach($process in $firefox_processes){
        Stop-Process $process.id -force
    }
}
catch {
    logger("Failed Launch Firefox for the First Time")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# # Prevent Disabling of Firefox Add-ons
# try{
#     logger("Prevent Disabling of Firefox Add-ons...")
#     new-item -type directory "c:\Program Files\Mozilla Firefox" -name distribution
#     new-item -type file -path "c:\Program Files\Mozilla Firefox\distribution" -name policies.json

#     add-content -path "c:\Program Files\Mozilla Firefox\distribution\policies.json" -value '{
#     "policies": {
#         "Extensions": {
#             "Install": [
#                 "https://addons.mozilla.org/firefox/downloads/file/4173260/block_website-0.5.1.1.xpi"
#             ],
#             "Locked":  [
#                 "{54e2eb33-18eb-46ad-a4e4-1329c29f6e17}"
#             ]
#         },
#         "DisablePrivateBrowsing": true
#     }
# }
#     '
# }
# catch{
#     logger("Failed Prevent Disabling of Firefox Add-ons")
#     $Error[0].Exception.Message
#     logger($Error[0].Exception.Message)
# }

# Block All Website Browsing Except for Wizer, Disable Private Browsing, and other Firefox Configurations
try{
    logger("Prevent Disabling of Firefox Add-ons...")
    new-item -type directory "c:\Program Files\Mozilla Firefox" -name distribution
    new-item -type file -path "c:\Program Files\Mozilla Firefox\distribution" -name policies.json

    # THIS METHOD USES JUST FIREFOX TO ADD URLS TO THE BLOCK / ALLOW LIST
    add-content -path "c:\Program Files\Mozilla Firefox\distribution\policies.json" -value '{
    "policies": {
        "WebsiteFilter": {
            "Block": ["<all_urls>"],
            "Exceptions": [
                "https://app.wizer-training.com/home/learning",
	            "https://app.wizer-training.com/login"
            ]
        },
        "DisablePrivateBrowsing": true,
        "Bookmarks": [
      		{
        		"Title": "Wizer-Training",
        		"URL": "https://app.wizer-training.com/home/learning",
        		"Placement": "toolbar"
      		}
   	    ],
        "FirefoxHome": {
            "Search": false,
            "TopSites": false,
            "SponsoredTopSites": false,
            "Highlights": false,
            "Pocket": false,
            "SponsoredPocket": false,
            "Snippets": false,
            "Locked": true
        },
        "FirefoxSuggest": {
            "WebSuggestions": false,
            "SponsoredSuggestions": false,
            "ImproveSuggest": false,
            "Locked": true
        },
        "OverrideFirstRunPage": "https://app.wizer-training.com/home/learning"
    }
}
    '
}
catch{
    logger("Failed Prevent Disabling of Firefox Add-ons")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Add Firefox (Wizer_Security_Training) to Image-Assistant
try{
    logger("Add Firefox (Wizer_Security_Training) to Image-Assistant...")
    . "c:\Program Files\Amazon\Photon\ConsoleImageBuilder\image-assistant.exe" add-application --name "Wizer_Security_Training" --display-name "Wizer_Security_Training" --absolute-app-path "C:\Program Files\Mozilla Firefox\firefox.exe"
}
catch{
    logger("Failed Add Firefox (Wizer_Security_Training) to Image-Assistant")
    $Error[0].Exception.Message
    logger($Error[0].Exception.Message)
}

# Signal Completion
# How can this be done?
