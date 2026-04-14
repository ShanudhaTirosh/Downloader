
$certName = "ShanuFx Free Cert"
$exePath = "dist\ShanuFxDownloader.exe"
$cerPath = "shanu_root.cer"

Write-Host "Searching for certificate: $certName"
$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object { $_.FriendlyName -eq $certName } | Select-Object -First 1

if ($null -eq $cert) {
    Write-Host "Creating new self-signed certificate..."
    $cert = New-SelfSignedCertificate -Type CodeSigning -Subject "CN=ShanuFx" -KeyUsage DigitalSignature -FriendlyName $certName -CertStoreLocation "Cert:\CurrentUser\My"
}

if ($null -eq $cert) {
    Write-Error "Failed to acquire certificate."
    exit 1
}

Write-Host "Exporting certificate to $cerPath"
Export-Certificate -Cert $cert -FilePath $cerPath -Force

Write-Host "Importing certificate to Trusted Root store..."
# Use ErrorAction SilentlyContinue if it already exists
Import-Certificate -FilePath $cerPath -CertStoreLocation "Cert:\CurrentUser\Root" -ErrorAction SilentlyContinue

Write-Host "Signing executable: $exePath"
$result = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert

Write-Host "Signature Result:"
$result | Format-List

if ($result.Status -eq "Valid") {
    Write-Host "SUCCESS: Application signed successfully."
} else {
    Write-Host "WARNING: Signature status is $($result.Status). You may need to manually trust the cert."
}
