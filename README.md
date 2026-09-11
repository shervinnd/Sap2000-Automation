# SAP2000 Automation

Python tooling to drive **SAP2000** on Windows through the COM API.

What it does:

- open an existing `.sdb` model
- run analysis
- run steel design (default code: `AISC360-16`)
- export analysis log / design summary ratios to Excel
- optimize member sections with a **genetic algorithm** to reduce structural weight

> Requires Windows + a licensed SAP2000 installation. The COM bridge will not work on macOS/Linux.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

Optional:

```powershell
$env:SAP2000_EXE = "C:\Program Files\Computers and Structures\SAP2000 24\SAP2000.exe"
```

Put your `.sdb` files under `models/` (gitignored).

## Usage

### Analysis / design

```bash
sap2000-auto analyze models\modelFixed.sdb -o outputs
sap2000-auto design models\modelFixed.sdb -o outputs --code AISC360-16
```

### Genetic weight optimization

1. Copy `configs/optimize.example.json`
2. Set `section_pool` to section property names that already exist in the model
3. Set `member_groups` (frames that must share one section).  
   If you leave `member_groups` empty, groups are auto-built from the current section assignments.
4. Run:

```bash
sap2000-auto optimize models\modelFixed.sdb -c configs\optimize.example.json -o outputs --save-model models\modelFixed_opt.sdb
```

Fitness is:

- minimize total steel weight
- if max design ratio > `ratio_limit`, apply a large penalty

Outputs:

- `outputs/ga_history.csv`
- `outputs/ga_best_assignment.json`

### Python API

```python
from sap2000_automation.config import AppConfig
from sap2000_automation.optimize import load_optimize_config, run_weight_optimization

config = AppConfig.from_env(model_path=r"models\modelFixed.sdb", output_dir="outputs")
problem = load_optimize_config("configs/optimize.example.json")
result = run_weight_optimization(config, problem)
print(result.best_sections, result.total_weight, result.max_ratio)
```

## Layout

```text
src/sap2000_automation/
  client.py
  analysis.py
  design.py
  genetic.py
  optimize.py
  cli.py
configs/optimize.example.json
models/
outputs/
notebooks/
tests/
```

## Notes

- Section names in `section_pool` must already exist as frame properties in SAP2000.
- Keep model/analysis binaries out of git.
- GA unit tests run without SAP2000; full optimize needs a local SAP install.

## License

MIT — see [LICENSE](LICENSE).
