#!/bin/bash
cd /home/guillaume/NeuroTuxLayer/services/vision
# Enable PyTorch memory optimization
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
/home/guillaume/NeuroTuxLayer/myenv/bin/python service.py

