# PACEvolve: Enabling Long-Horizon Progress-Aware Consistent Evolution

## Table of Contents
1. [About the Project](#about-the-project)
2. [Prerequisites](#prerequisites)
3. [Installation & Usage](#installation--usage)
4. [Support & Contribution](#support--contribution)
5. [License](#license)

---

## About the Project

This repo contains implementation for the [PACEvolve](https://arxiv.org/pdf/2601.10657) paper.

---

## Prerequisites

Before installing `PACEvolve` you need:

* **Python 3.9** or later
* We support OpenAI / Anthropic / Google Gemini APIs. You should have at least one API key available, more installation instructions can be found below.
* **Git**

The project relies on specific directory structures to locate tasks and configurations. Ensure your project root contains:
* `workflows/` (where this script resides)
* `tasks/` (containing task definitions and their respective environment installation requirements)

---

## Installation & Usage

### 1. Installation

Create the conda environment and install PACEvolve:

```bash
conda create -n pacevolve-kb python=3.10 -y
conda activate pacevolve-kb

git clone https://github.com/loaringlyc/pacevolve.git
cd pacevolve
git checkout 22798d9f30c00e12e71225cd1cb1325c48f133ad

pip install -U pip setuptools wheel
pip install -r requirements.txt
```

Install KernelBench v0 and copy the required files into PACEvolve:

```bash
cd ..
git clone --depth 1 --branch v0 https://github.com/ScalingIntelligence/KernelBench.git
cd KernelBench
git checkout 6500bbc8cf102520d7a8f09be34ee6d5db1c29b0
cd ..

rsync -a KernelBench/src/ pacevolve/tasks/kernel_bench/src/
rsync -a KernelBench/KernelBench/ pacevolve/tasks/kernel_bench/KernelBench/

pip install -r KernelBench/requirements.txt
cd pacevolve/tasks/kernel_bench
pip install -e .


---

### 2. Setup API Keys & Dependencies

You must configure the API keys and install the necessary packages for the models you intend to use. We currently support Google Gemini, OpenAI, and Anthropic.

**1. Set your API Keys**
Export the environment variables for the providers you plan to use:

```bash
export DEEPSEEK_API_KEY="<your-api-key>"

# Install all supported clients
pip install openai 
```

Each task contains a config.yaml file in the config subdirectory, you can change the backbone llm by changing the llm section in the config file.


### 3. Evaluating One Kernel
Before running evolutionary search, verify the KernelBench evaluator directly.
This example evaluates the generated Softmax kernel against the PyTorch
baseline:

```bash
cd pacevolve/tasks/kernel_bench

conda run -n pacevolve-kb bash -lc '
python eval/eval_auto_evo.py \
  --baseline_path eval/baseline/Softmax.py \
  --kernel_path   eval/kernels/Softmax/kernel.py \
  --baseline_time 0.008750 \
  --build_dir     eval/kernels/Softmax
'
```

### 4. Running Your First Experiment
To run the evolutionary process, execute the script with a specific task_id. This assumes you have a task configuration file located at ../tasks/<task_id>/config/.

```bash
python run_experiment.py --task_id kernel_bench --run_id 10
```

Run the parallel pipeline with four workers:

```bash
cd pacevolve/workflows
python run_experiment.py \
  --task_id kernel_bench \
  --run_id 10 \
  --parallel \
  --num_workers 4
```

---

## Support & Contribution
### Documentation
Transcript Logs: Detailed logs of the LLM's thought process and code generation are saved to the transcripts defined in your YAML config.
Controller Logs: Technical execution logs are saved to controller_verbose_*.log.

If you need help, please open an issue in the repository!

---

## License

**Open-source project**

You are free to copy, modify, and distribute `PACEvolve` with attribution under the terms of the **Apache 2.0 license**. See the `LICENSE` file for details.

---

This is not an officially supported Google product. This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security).

This project is intended for demonstration purposes only. It is not intended for use in a production environment.
