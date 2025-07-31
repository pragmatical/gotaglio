#!/usr/bin/env python3
"""
Test script to measure gotaglio import time in isolation
"""
import time
import sys

def test_clean_import():
    """Test importing gotaglio in a fresh Python process"""
    print("Testing gotaglio import time in isolation...")
    
    start_time = time.perf_counter()
    import gotaglio
    end_time = time.perf_counter()
    
    duration = end_time - start_time
    print(f"Gotaglio import time: {duration:.3f}s")
    
    # Test that we can access the main function without triggering heavy imports
    start_time = time.perf_counter()
    main_func = gotaglio.main
    end_time = time.perf_counter()
    
    access_time = end_time - start_time
    print(f"Accessing main function: {access_time:.3f}s")
    
    return duration

if __name__ == "__main__":
    test_clean_import()
