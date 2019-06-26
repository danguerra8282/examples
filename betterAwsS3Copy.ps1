Remove-Variable keys
$keys = @()
$contents = get-s3object -bucketname bucketName -keyprefix Software
$allKeys = $contents.key
foreach ($key in $allKeys)
{
    if ($keys -notcontains ($key.split('/')[1]))
    {
        $keys += $key.split('/')[1]
    }
}
$keys

if (test-path c:\nwtools\build\software)
{
    foreach ($folderkey in $keys)
    {
        if ($folderkey -ne "")
        {
            if ((get-childitem -path c:\nwtools\build\software).name -notcontains $folderkey)
            {
                Copy-S3Object -BucketName bucketName -KeyPrefix Software/$folderkey -LocalFolder c:\nwtools\build\Software\$folderkey
            }
        }
    }
}
