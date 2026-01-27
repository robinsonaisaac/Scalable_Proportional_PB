# Scalable Proportional Participatory Budgeting

A high-performance Python implementation of **Exact Equal Shares (EES)** and completion heuristics for proportional participatory budgeting.

> **Paper:** Streamlining Equal Shares
> **Authors:** Sonja Kraiczy, Isaac Robinson, and Edith Elkind
> **arXiv:** [2502.11797](https://arxiv.org/abs/2502.11797)

---

## Features

- **Exact Arithmetic** — Uses Python's `Fraction` class throughout to ensure precise, reproducible results
- **Five Core Algorithms** — Complete implementation of Algorithms 1–5 from the paper
- **Three Completion Heuristics** — ADD-ONE, ADD-OPT, and ADD-OPT-SKIP for budget completion
- **Pabulib Compatible** — Direct support for the standard [Pabulib](http://pabulib.org/) `.pb` file format
- **Deterministic Output** — Lexicographic tie-breaking guarantees reproducible results
- **Minimal Dependencies** — No external dependencies for core functionality

---

## Requirements

- Python 3.11 or higher

---

## Installation

```bash
git clone https://github.com/robinsonaisaac/Scalable_Proportional_PB.git
cd Scalable_Proportional_PB

# Install in development mode
pip install -e ".[dev]"
```

---

## Quick Start

### Unified CLI (PB_scripts/run_pb.py)

The unified CLI provides a single entry point for all participatory budgeting algorithms:

```bash
# Run EES with cardinal (approval) utilities and ADD-OPT completion
python PB_scripts/run_pb.py data.pb -a ees -u cardinal -c add-opt

# Run MES (waterflow) with cost utilities
python PB_scripts/run_pb.py data.pb -a mes -u cost -c none

# Run EES with ADD-OPT-SKIP heuristic in exhaustive mode
python PB_scripts/run_pb.py data.pb -a ees -u cardinal -c add-opt-skip --exhaustive
```

**CLI Options:**
| Option | Values | Description |
|--------|--------|-------------|
| `<input_file>` | `<file.pb>` | Input Pabulib file (required, positional) |
| `-a, --algorithm` | `ees`, `mes` | Algorithm: EES or MES/Waterflow |
| `-u, --utility` | `cardinal`, `cost` | Utility function |
| `-c, --completion` | `none`, `add-one`, `add-opt`, `add-opt-skip` | Completion heuristic |
| `-e, --exhaustive` | flag | Continue until all projects selected |
| `-o, --output` | `<file.csv>` | Custom output path |

**Note:** MES only supports `none` and `add-one` completion methods. ADD-OPT and ADD-OPT-SKIP are EES-specific.

### SLURM Batch Submission

For cluster computing, use the unified submission script:

```bash
# Submit EES jobs with cardinal utilities and ADD-OPT completion
./submission_scripts/submit_pb.sh -a ees -u cardinal -c add-opt -d /path/to/pb/files

# Submit MES jobs with cost utilities in exhaustive mode
./submission_scripts/submit_pb.sh -a mes -u cost -c add-one -e -d /path/to/pb/files

# With custom partition and time limit
./submission_scripts/submit_pb.sh -a ees -u cardinal -c add-opt-skip -d /data -p long -t 02:00:00
```

### Module CLI

You can also use the module directly for EES:

```bash
# Run EES with approval (cardinal) utility
python -m scalable_proportional_pb run --input data.pb --utility approval

# Run EES with cost (uniform) utility
python -m scalable_proportional_pb run --input data.pb --utility cost

# Run with ADD-OPT-SKIP completion (recommended)
python -m scalable_proportional_pb run --input data.pb --completion add-opt-skip

# Run with exhaustive completion (explores all budget levels)
python -m scalable_proportional_pb run --input data.pb --completion add-one --exhaustive
```

### Python API

```python
from scalable_proportional_pb import (
    parse_pabulib_file,
    ees,
    ees_with_outcome,
)
from scalable_proportional_pb.ees import cardinal_utility, cost_utility
from scalable_proportional_pb.completion import (
    add_one_completion,
    add_opt_completion,
    add_opt_skip_completion,
)

# Parse a Pabulib file
election = parse_pabulib_file("data.pb")

# Run basic EES (returns set of selected project IDs)
selected = ees(election, cardinal_utility)
print(f"Selected projects: {selected}")

# Run EES with full outcome details
outcome = ees_with_outcome(election, cardinal_utility)
print(f"Selected: {outcome.selected}")
print(f"Total cost: {outcome.total_cost}")
print(f"Spending efficiency: {float(outcome.spending_efficiency(election.budget)):.2%}")
print(f"Selection order: {outcome.selection_order}")

# Access payment details
for project_id in outcome.selected:
    payers = outcome.project_payers(project_id)
    print(f"Project {project_id}: {len(payers)} payers")

# Run with completion heuristics
outcome = add_opt_skip_completion(election, cardinal_utility, is_cardinal=True)
```

---

## Algorithms

All algorithms are implemented exactly as described in the paper.

| Algorithm | Name | Use Case | Time Complexity |
|-----------|------|----------|-----------------|
| Algorithm 1 | **EES** | Core Equal Shares computation | O(m²n) |
| Algorithm 2 | **GreedyProjectChange** | Stability check for cardinal utilities | O(n) |
| Algorithm 3 | **ADD-OPT** | Optimal budget increment for cardinal | O(mn) |
| Algorithm 4 | **GreedyProjectChange** | Stability check for uniform utilities | O(m + n) |
| Algorithm 5 | **ADD-OPT** | Optimal budget increment for uniform | O(m²n) |

*Where m = number of projects, n = number of voters.*

### Utility Functions

- **Cardinal (Approval):** Each approved project contributes utility 1
- **Uniform (Cost):** Each approved project contributes utility equal to its cost

### Completion Heuristics

Completion heuristics address EES's tendency to underspend by iteratively increasing the virtual budget:

| Heuristic | Description | Recommendation |
|-----------|-------------|----------------|
| **ADD-ONE** | Increases budget by n per iteration | Simple baseline |
| **ADD-OPT** | Computes optimal budget increment | Theoretically optimal |
| **ADD-OPT-SKIP** | Like ADD-OPT but skips already-selected projects | **Recommended** — faster with similar results |

Each heuristic has two variants:
- **Standard:** Stops when outcome exceeds actual budget
- **Exhaustive:** Continues until all projects selected, returns best feasible outcome

---

## Data Types

### `Election`

Represents a participatory budgeting instance E(b) = (N, P, {A_i}, cost, b):

```python
election.projects      # Dict[str, Project] — project ID to Project
election.voters        # List[int] — voter indices (0-indexed)
election.approvals     # Dict[int, Set[str]] — voter to approved project IDs
election.budget        # Fraction — total budget
election.n             # int — number of voters
election.m             # int — number of projects
```

### `EESOutcome`

Contains the full result of running EES:

```python
outcome.selected           # Set[str] — selected project IDs
outcome.total_cost         # Fraction — sum of selected project costs
outcome.selection_order    # List[(project_id, bang_per_buck)] — selection history
outcome.payments           # Dict[(voter, project), Fraction] — payment matrix
outcome.leftover_budgets   # Dict[voter, Fraction] — remaining voter budgets

# Methods
outcome.spending_efficiency(budget)  # Fraction — total_cost / budget
outcome.project_payers(project_id)   # Set[int] — voters who paid for project
outcome.payment(voter, project)      # Fraction — specific payment amount
```

---

## Input Format

The library accepts [Pabulib](http://pabulib.org/) `.pb` files:

```
META
key;value
budget;100000
num_projects;10
num_votes;500
vote_type;approval

PROJECTS
project_id;cost;name
p1;10000;Street Lights
p2;25000;Park Renovation
p3;15000;Bike Lane

VOTES
voter_id;vote
1;p1,p2,p5
2;p2,p3
3;p1,p3,p4
```

---

## Testing

The library includes a comprehensive test suite with unit tests, integration tests, and exhaustive verification:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=scalable_proportional_pb
```

---

## Project Structure

```
Scalable_Proportional_PB/
├── src/scalable_proportional_pb/
│   ├── __init__.py          # Public API exports
│   ├── __main__.py          # Module CLI entry point
│   ├── types.py             # Election, EESOutcome, Project
│   ├── ees.py               # Algorithm 1: Exact Equal Shares
│   ├── gpc_cardinal.py      # Algorithm 2: GreedyProjectChange (cardinal)
│   ├── add_opt_cardinal.py  # Algorithm 3: ADD-OPT (cardinal)
│   ├── gpc_uniform.py       # Algorithm 4: GreedyProjectChange (uniform)
│   ├── add_opt_uniform.py   # Algorithm 5: ADD-OPT (uniform)
│   ├── completion.py        # Completion heuristics
│   └── pabulib_io.py        # Pabulib file I/O
├── PB_scripts/
│   ├── run_pb.py            # Unified CLI for EES and MES
│   └── core/
│       ├── cli.py           # CLI utilities and results handling
│       └── mes.py           # MES/Waterflow wrappers (uses pabutools)
├── submission_scripts/
│   └── submit_pb.sh         # Unified SLURM submission script
├── tests/                   # Test suite
├── results/                 # Output directory for experiment results
├── pyproject.toml           # Package configuration
└── README.md
```

### Results Directory Structure

Results are organized by algorithm, utility, and completion method:

```
results/
├── ees/
│   ├── cardinal/
│   │   ├── none/
│   │   ├── add-one/
│   │   ├── add-opt/
│   │   ├── add-opt-skip/
│   │   └── add-opt_exhaustive/
│   └── cost/
│       └── ...
└── mes/
    ├── cardinal/
    │   ├── none/
    │   └── add-one/
    └── cost/
        └── ...
```

---

## Citation

If you use this software in your research, please cite:

```bibtex
@article{kraiczy2025streamlining,
  title={Streamlining Equal Shares},
  author={Kraiczy, Sonja and Robinson, Isaac and Elkind, Edith},
  journal={arXiv preprint arXiv:2502.11797},
  year={2025}
}
```

---

## License

MIT License
