#!/usr/bin/env python3
"""
Test the actual import time that users will experience
"""
import subprocess
import sys

def test_import_in_subprocess():
    """Test import in a fresh subprocess to get accurate timing"""
    
    # Create a minimal test script
    test_script = '''
import time
start = time.perf_counter()
import gotaglio
end = time.perf_counter()
print(f"Import time: {end - start:.3f}s")
'''
    
    # Run in subprocess
    result = subprocess.run([
        sys.executable, '-c', test_script
    ], capture_output=True, text=True, cwd='.')
    
    print("Testing gotaglio import in fresh Python process:")
    print(result.stdout.strip())
    
    if result.stderr:
        print("Errors:", result.stderr.strip())

if __name__ == "__main__":
    test_import_in_subprocess()
