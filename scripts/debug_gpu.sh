#!/bin/bash
# Debug script to check GPU and RAPIDS
echo "=== GPU Information ==="
nvidia-smi

echo -e "\n=== RAPIDS Version ==="
python3 -c "import cudf; print(f'cuDF version: {cudf.__version__}')"

echo -e "\n=== Available GPU Memory ==="
python3 << 'PYTHON'
import cupy as cp
mempool = cp.get_default_memory_pool()
print(f"Free memory: {mempool.free_bytes() / 1024**3:.2f} GB")
print(f"Total memory: {mempool.total_bytes() / 1024**3:.2f} GB")
PYTHON

echo -e "\n=== Test Simple cuDF Operation ==="
python3 << 'PYTHON'
import cudf
import cupy as cp
print("Creating small test dataframe...")
df = cudf.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(f"Success! Shape: {df.shape}")
print(df)
PYTHON
