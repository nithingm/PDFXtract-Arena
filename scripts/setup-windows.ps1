# PDFX-Bench Windows Setup Script
# Automatically installs Tesseract OCR, Poppler, and Python dependencies

param(
    [switch]$SkipTesseract,
    [switch]$SkipPoppler,
    [switch]$SkipPython,
    [switch]$Force
)

Write-Host "PDFX-Bench Windows Setup Script" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "Warning: Not running as administrator. Some installations may fail." -ForegroundColor Yellow
    Write-Host "Consider running PowerShell as Administrator for best results." -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if a command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to add to PATH
function Add-ToPath {
    param($Path)
    
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$Path*") {
        Write-Host "Adding $Path to user PATH..." -ForegroundColor Yellow
        $newPath = "$currentPath;$Path"
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        
        # Update current session PATH
        $env:PATH = "$env:PATH;$Path"
        Write-Host "Added $Path to PATH" -ForegroundColor Green
    } else {
        Write-Host "$Path already in PATH" -ForegroundColor Green
    }
}

# Function to download file
function Download-File {
    param($Url, $OutputPath)
    
    Write-Host "Downloading from $Url..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutputPath -UseBasicParsing
        Write-Host "Downloaded successfully" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "Download failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Check for winget
$hasWinget = Test-Command "winget"

# Install Tesseract OCR
if (-not $SkipTesseract) {
    Write-Host "`nChecking Tesseract OCR..." -ForegroundColor Cyan
    
    if ((Test-Command "tesseract") -and (-not $Force)) {
        Write-Host "Tesseract already installed" -ForegroundColor Green
    } else {
        Write-Host "Installing Tesseract OCR..." -ForegroundColor Yellow
        
        if ($hasWinget) {
            Write-Host "Using winget to install Tesseract..." -ForegroundColor Yellow
            try {
                winget install --id UB-Mannheim.TesseractOCR --silent --accept-package-agreements --accept-source-agreements
                Add-ToPath "C:\Program Files\Tesseract-OCR"
                Write-Host "Tesseract installed successfully via winget" -ForegroundColor Green
            } catch {
                Write-Host "Winget installation failed, trying manual download..." -ForegroundColor Yellow
                $tesseractInstaller = "$env:TEMP\tesseract-installer.exe"
                $tesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
                
                if (Download-File $tesseractUrl $tesseractInstaller) {
                    Write-Host "Running Tesseract installer..." -ForegroundColor Yellow
                    Start-Process -FilePath $tesseractInstaller -ArgumentList "/S" -Wait
                    Add-ToPath "C:\Program Files\Tesseract-OCR"
                    Remove-Item $tesseractInstaller -Force -ErrorAction SilentlyContinue
                    Write-Host "Tesseract installed successfully" -ForegroundColor Green
                }
            }
        } else {
            Write-Host "Winget not available, downloading manually..." -ForegroundColor Yellow
            $tesseractInstaller = "$env:TEMP\tesseract-installer.exe"
            $tesseractUrl = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
            
            if (Download-File $tesseractUrl $tesseractInstaller) {
                Write-Host "Running Tesseract installer..." -ForegroundColor Yellow
                Start-Process -FilePath $tesseractInstaller -ArgumentList "/S" -Wait
                Add-ToPath "C:\Program Files\Tesseract-OCR"
                Remove-Item $tesseractInstaller -Force -ErrorAction SilentlyContinue
                Write-Host "Tesseract installed successfully" -ForegroundColor Green
            }
        }
    }
}

# Install Poppler
if (-not $SkipPoppler) {
    Write-Host "`nChecking Poppler..." -ForegroundColor Cyan
    
    if ((Test-Command "pdftoppm") -and (-not $Force)) {
        Write-Host "Poppler already installed" -ForegroundColor Green
    } else {
        Write-Host "Installing Poppler..." -ForegroundColor Yellow
        
        $popplerDir = "C:\poppler"
        $popplerZip = "$env:TEMP\poppler.zip"
        $popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v23.11.0-0/Release-23.11.0-0.zip"
        
        if (Download-File $popplerUrl $popplerZip) {
            Write-Host "Extracting Poppler..." -ForegroundColor Yellow
            
            # Remove existing directory if it exists
            if (Test-Path $popplerDir) {
                Remove-Item $popplerDir -Recurse -Force
            }
            
            # Extract zip
            Expand-Archive -Path $popplerZip -DestinationPath $popplerDir -Force
            
            # Find the actual poppler directory (it's nested)
            $popplerBinPath = Get-ChildItem -Path $popplerDir -Recurse -Directory -Name "bin" | Select-Object -First 1
            if ($popplerBinPath) {
                $fullBinPath = Join-Path $popplerDir $popplerBinPath
                Add-ToPath $fullBinPath
                Write-Host "Poppler installed successfully" -ForegroundColor Green
            } else {
                Write-Host "Could not find Poppler bin directory" -ForegroundColor Red
            }
            
            Remove-Item $popplerZip -Force -ErrorAction SilentlyContinue
        }
    }
}

# Install Python dependencies
if (-not $SkipPython) {
    Write-Host "`nInstalling Python dependencies..." -ForegroundColor Cyan
    
    try {
        python -m pip install pytesseract pdf2image
        Write-Host "Python dependencies installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "Failed to install Python dependencies: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Please restart your terminal or PowerShell session to ensure PATH changes take effect." -ForegroundColor Yellow

# Verify installations
Write-Host "`nVerifying installations..." -ForegroundColor Cyan

# Refresh PATH for current session
$env:PATH = [Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [Environment]::GetEnvironmentVariable("PATH", "Machine")

if (Test-Command "tesseract") {
    try {
        $tesseractVersion = tesseract --version 2>&1 | Select-Object -First 1
        Write-Host "Tesseract: $tesseractVersion" -ForegroundColor Green
    } catch {
        Write-Host "Tesseract: Installed but version check failed" -ForegroundColor Yellow
    }
} else {
    Write-Host "Tesseract: Not found in PATH" -ForegroundColor Red
}

if (Test-Command "pdftoppm") {
    Write-Host "Poppler: Available" -ForegroundColor Green
} else {
    Write-Host "Poppler: Not found in PATH" -ForegroundColor Red
}

try {
    python -c "import pytesseract; print('pytesseract: Available')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "pytesseract: Available" -ForegroundColor Green
    } else {
        Write-Host "pytesseract: Not available" -ForegroundColor Red
    }
} catch {
    Write-Host "pytesseract: Not available" -ForegroundColor Red
}

try {
    python -c "import pdf2image; print('pdf2image: Available')" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "pdf2image: Available" -ForegroundColor Green
    } else {
        Write-Host "pdf2image: Not available" -ForegroundColor Red
    }
} catch {
    Write-Host "pdf2image: Not available" -ForegroundColor Red
}

Write-Host "`nIf any components show as 'Not found' or 'Not available', please restart your terminal and try again." -ForegroundColor Yellow
