# Spike 1e: which GPU does a Kaggle notebook get? Push with: kaggle kernels push -p spikes/kaggle_gpu
import subprocess
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"], capture_output=True, text=True).stdout)
