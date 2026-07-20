#!/bin/bash
# Qwen2.5-VL-7B-AWQ, TP=2 across both 3060 Tis, cross-NUMA NCCL socket transport.
# DENSE video frame sampling so the VLM WATCHES THE FULL VIDEO (not ~4 stills):
#   mm-processor-kwargs fps=12 -> ~25 frames from a 2s clip; max_pixels capped so the
#   frames fit the context window (12288).
pkill -9 -f "vllm serve" 2>/dev/null; pkill -9 -f "micromamba run" 2>/dev/null; pkill -9 -f EngineCore 2>/dev/null
sleep 6
export MAMBA_ROOT_PREFIX=$HOME/.mamba
CUDA_DIR=$HOME/.mamba/envs/vllm/lib/python3.12/site-packages/nvidia/cu13
GXX=$HOME/.mamba/envs/vllm/bin/x86_64-conda-linux-gnu-g++
exec $HOME/bin/micromamba run -n vllm env \
  CUDA_VISIBLE_DEVICES=0,1 CUDA_HOME=$CUDA_DIR NVCC_PREPEND_FLAGS="-ccbin $GXX" \
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True VLLM_USE_FLASHINFER_SAMPLER=0 VLLM_ATTENTION_BACKEND=FLASH_ATTN \
  NCCL_P2P_DISABLE=1 NCCL_SHM_DISABLE=1 NCCL_IB_DISABLE=1 NCCL_NET=Socket NCCL_SOCKET_IFNAME=lo \
  VLLM_WORKER_MULTIPROC_METHOD=spawn \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct-AWQ \
  --tensor-parallel-size 2 --max-model-len 12288 --gpu-memory-utilization 0.70 --enforce-eager \
  --port 8001 --limit-mm-per-prompt.image 60 --limit-mm-per-prompt.video 1
