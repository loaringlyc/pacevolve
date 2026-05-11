#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${TASK_DIR}"

pwd

/home/loring/miniconda3/condabin/conda run -n pacevolve-kb bash -lc '
set -euo pipefail
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.9}"

if command -v ncu >/dev/null 2>&1; then
  NCU_BIN="$(command -v ncu)"
elif [ -x /usr/local/cuda/bin/ncu ]; then
  NCU_BIN="/usr/local/cuda/bin/ncu"
else
  echo "ERROR: ncu was not found. Install Nsight Compute or add ncu to PATH." >&2
  exit 127
fi

"$NCU_BIN" \
  --target-processes all \
  --kernel-name-base demangled \
  --kernel-name regex:matmul_tiled_kernel \
  --launch-skip 3 \
  --launch-count 1 \
  --section SpeedOfLight \
  --section MemoryWorkloadAnalysis \
  --section LaunchStats \
  --section Occupancy \
  --section SchedulerStats \
  --section WarpStateStats \
  python eval/eval_auto_evo.py \
    --baseline_path eval/baseline/Matmul_with_large_K_dimension.py \
    --kernel_path eval/kernels/Matmul_with_large_K_dimension/kernel.py \
    --baseline_time 0.411 \
    --build_dir eval/kernels/Matmul_with_large_K_dimension
'
