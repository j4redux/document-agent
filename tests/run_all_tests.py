#!/usr/bin/env python3
"""Run all document agent tests."""

import os
import sys
import subprocess

def run_test_file(test_file):
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(test_file)
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running {test_file}: {e}")
        return False


def main():
    """Run all tests in the tests directory."""
    print("Document Agent Test Suite")
    print("="*60)
    
    # Get all test files
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [
        os.path.join(tests_dir, f) 
        for f in os.listdir(tests_dir) 
        if f.startswith('test_') and f.endswith('.py')
    ]
    
    # Sort for consistent order
    test_files.sort()
    
    print(f"Found {len(test_files)} test files:")
    for f in test_files:
        print(f"  - {os.path.basename(f)}")
    
    # Run each test
    results = {}
    for test_file in test_files:
        success = run_test_file(test_file)
        results[os.path.basename(test_file)] = success
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for success in results.values() if success)
    failed = len(results) - passed
    
    for test_file, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_file:<30} {status}")
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\nAll tests passed!")
        return 0
    else:
        print(f"\n{failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())