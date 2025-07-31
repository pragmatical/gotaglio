import time

print("Testing individual imports...")

start = time.perf_counter()
import openai
print(f"openai: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import numpy
print(f"numpy: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import scipy
print(f"scipy: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import azure.ai.inference
print(f"azure.ai.inference: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import jinja2
print(f"jinja2: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import rich
print(f"rich: {time.perf_counter() - start:.3f}s")

start = time.perf_counter()
import tiktoken
print(f"tiktoken: {time.perf_counter() - start:.3f}s")

print("\nNow testing gotaglio...")
start = time.perf_counter()
import gotaglio
print(f"gotaglio: {time.perf_counter() - start:.3f}s")
