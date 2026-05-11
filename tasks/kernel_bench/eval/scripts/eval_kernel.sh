cd ../..
pwd

# conda run -n pacevolve-kb bash -lc '
# python eval/eval_auto_evo.py \
#   --baseline_path eval/baseline/LayerNorm.py \
#   --kernel_path   multi_island_generated_kernels/kernel_16.py \
#   --baseline_time 5.68 \
#   --build_dir     eval/kernels/LayerNorm
# '

# conda run -n pacevolve-kb bash -lc '
# python eval/eval_auto_evo.py \
#   --baseline_path eval/baseline/Conv3d_Max_LogSumExp_ReLU.py \
#   --kernel_path   artifacts/Conv3d_Max_LogSumExp_ReLU/kernel.py \
#   --baseline_time 1.12 \
#   --build_dir     eval/kernels/Conv3d_Max_LogSumExp_ReLU
# '

conda run -n pacevolve-kb bash -lc '
python eval/eval_auto_evo.py \
  --baseline_path eval/baseline/Matmul_with_large_K_dimension.py \
  --kernel_path   artifacts/Matmul_with_large_K_dimension/kernel_best.py \
  --baseline_time 0.411 \
  --build_dir     eval/kernels/Matmul_with_large_K_dimension
'