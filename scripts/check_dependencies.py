#!/usr/bin/env python3
"""
PDFX-Bench Dependency Checker
Checks for required dependencies and provides installation guidance.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class DependencyChecker:
    def __init__(self):
        self.results = {
            'tesseract': {'available': False, 'version': None, 'path': None},
            'poppler': {'available': False, 'version': None, 'path': None},
            'pytesseract': {'available': False, 'version': None},
            'pdf2image': {'available': False, 'version': None}
        }
    
    def check_tesseract(self):
        """Check if Tesseract OCR is available."""
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            try:
                result = subprocess.run(['tesseract', '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_line = result.stderr.split('\n')[0] if result.stderr else result.stdout.split('\n')[0]
                    self.results['tesseract'] = {
                        'available': True,
                        'version': version_line.strip(),
                        'path': tesseract_path
                    }
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
        
        self.results['tesseract'] = {'available': False, 'version': None, 'path': None}
        return False
    
    def check_poppler(self):
        """Check if Poppler utilities are available."""
        pdftoppm_path = shutil.which('pdftoppm')
        if pdftoppm_path:
            try:
                result = subprocess.run(['pdftoppm', '-h'], 
                                      capture_output=True, text=True, timeout=10)
                # pdftoppm returns non-zero for -h, but that's expected
                if 'pdftoppm' in result.stderr or 'pdftoppm' in result.stdout:
                    self.results['poppler'] = {
                        'available': True,
                        'version': 'Available',
                        'path': pdftoppm_path
                    }
                    return True
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
                pass
        
        self.results['poppler'] = {'available': False, 'version': None, 'path': None}
        return False
    
    def check_pytesseract(self):
        """Check if pytesseract Python package is available."""
        try:
            import pytesseract
            version = getattr(pytesseract, '__version__', 'Unknown version')
            self.results['pytesseract'] = {
                'available': True,
                'version': version
            }
            return True
        except ImportError:
            self.results['pytesseract'] = {'available': False, 'version': None}
            return False
    
    def check_pdf2image(self):
        """Check if pdf2image Python package is available."""
        try:
            import pdf2image
            version = getattr(pdf2image, '__version__', 'Unknown version')
            self.results['pdf2image'] = {
                'available': True,
                'version': version
            }
            return True
        except ImportError:
            self.results['pdf2image'] = {'available': False, 'version': None}
            return False
    
    def check_all(self):
        """Check all dependencies."""
        print("Checking PDFX-Bench OCR dependencies...")
        print("=" * 40)
        
        # Check system dependencies
        tesseract_ok = self.check_tesseract()
        poppler_ok = self.check_poppler()
        
        # Check Python dependencies
        pytesseract_ok = self.check_pytesseract()
        pdf2image_ok = self.check_pdf2image()
        
        # Print results
        self.print_results()
        
        # Return overall status
        return all([tesseract_ok, poppler_ok, pytesseract_ok, pdf2image_ok])
    
    def print_results(self):
        """Print dependency check results."""
        print("\nDependency Status:")
        print("-" * 20)
        
        for dep_name, dep_info in self.results.items():
            status = "✓" if dep_info['available'] else "✗"
            print(f"{status} {dep_name.ljust(12)}: ", end="")
            
            if dep_info['available']:
                version = dep_info.get('version', 'Available')
                path = dep_info.get('path', '')
                if path:
                    print(f"{version} ({path})")
                else:
                    print(f"{version}")
            else:
                print("Not found")
        
        print()
        
        # Provide installation guidance
        missing_deps = [name for name, info in self.results.items() if not info['available']]
        
        if missing_deps:
            print("Missing Dependencies:")
            print("-" * 20)
            
            if 'tesseract' in missing_deps:
                print("• Tesseract OCR: Required for OCR functionality")
            if 'poppler' in missing_deps:
                print("• Poppler: Required for PDF to image conversion")
            if 'pytesseract' in missing_deps:
                print("• pytesseract: Python wrapper for Tesseract")
            if 'pdf2image' in missing_deps:
                print("• pdf2image: Python library for PDF to image conversion")
            
            print("\nInstallation Options:")
            print("-" * 20)
            print("1. Automated setup (Windows):")
            print("   powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1")
            print()
            print("2. Manual installation:")
            print("   - Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   - Poppler: https://github.com/oschwartz10612/poppler-windows/releases")
            print("   - Python packages: pip install pytesseract pdf2image")
        else:
            print("All dependencies are available!")
    
    def get_availability_status(self):
        """Get availability status for web interface."""
        return {
            'tesseract_available': self.results['tesseract']['available'] and
                                 self.results['pytesseract']['available'] and
                                 self.results['pdf2image']['available'],
            'poppler_available': self.results['poppler']['available'] and
                               self.results['pdf2image']['available'],
            'details': self.results
        }


def main():
    """Main function for command line usage."""
    checker = DependencyChecker()
    all_available = checker.check_all()
    
    if all_available:
        print("All OCR dependencies are properly installed!")
        sys.exit(0)
    else:
        print("Some dependencies are missing. Please install them to use OCR functionality.")
        sys.exit(1)


if __name__ == "__main__":
    main()
