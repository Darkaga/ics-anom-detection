# =============================================================================
# Phase 3/4: GPU-Accelerated ML Pipeline with RAPIDS cuML
# =============================================================================
# Uses NVIDIA RAPIDS for GPU-accelerated feature extraction and ML training

FROM rapidsai/base:25.10-cuda13-py3.11

LABEL maintainer="ICS Anomaly Detection"
LABEL description="GPU-accelerated ML pipeline for ICS anomaly detection"
LABEL phase="3-4-ml"

USER root

# Install additional dependencies
RUN apt-get update && apt-get install -y \
    vim \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python packages
RUN pip install --no-cache-dir \
    matplotlib \
    seaborn \
    tqdm \
    pyarrow

# Create working directories
RUN mkdir -p /workspace/data/zeek \
             /workspace/data/features \
             /workspace/data/models \
             /workspace/scripts \
             /workspace/notebooks

# Copy scripts
COPY scripts/extract_features.py /workspace/scripts/
COPY scripts/train_model.py /workspace/scripts/
RUN chmod +x /workspace/scripts/*.py

# Set working directory
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
