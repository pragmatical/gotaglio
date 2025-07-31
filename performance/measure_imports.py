#!/usr/bin/env python3
"""
Script to measure import times for gotaglio and its dependencies
"""
import time
import sys

def time_import(module_name, description=None):
    """Time how long it takes to import a module"""
    if description is None:
        description = module_name
    
    print(f"Importing {description}...", end=" ", flush=True)
    start_time = time.perf_counter()
    
    try:
        __import__(module_name)
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"{duration:.3f}s")
        return duration
    except ImportError as e:
        print(f"FAILED: {e}")
        return 0

def main():
    print("Measuring import times for gotaglio dependencies...")
    print("=" * 60)
    
    total_time = 0
    
    # Test heavy dependencies first
    total_time += time_import("openai", "OpenAI library")
    total_time += time_import("azure.ai.inference", "Azure AI Inference")
    total_time += time_import("azure.core.credentials", "Azure Core")
    total_time += time_import("numpy", "NumPy")
    total_time += time_import("scipy", "SciPy")
    total_time += time_import("jinja2", "Jinja2")
    total_time += time_import("rich", "Rich")
    total_time += time_import("tiktoken", "tiktoken")
    total_time += time_import("gitpython", "GitPython")
    total_time += time_import("nest_asyncio", "nest_asyncio")
    total_time += time_import("glom", "glom")
    total_time += time_import("pyparsing", "pyparsing")
    
    print("-" * 60)
    print(f"Dependencies total: {total_time:.3f}s")
    print("-" * 60)
    
    # Now test gotaglio itself
    gotaglio_time = time_import("gotaglio", "gotaglio library")
    
    print("=" * 60)
    print(f"Dependencies: {total_time:.3f}s")
    print(f"Gotaglio:     {gotaglio_time:.3f}s")
    print(f"TOTAL:        {total_time + gotaglio_time:.3f}s")

if __name__ == "__main__":
    main()
