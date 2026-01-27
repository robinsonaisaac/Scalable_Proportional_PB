"""
Core utilities for Participatory Budgeting experiments.

This package provides utilities for running PB experiments:
- cli: Command-line interface helpers and results handling
- mes: MES/Waterflow wrappers (uses pabutools directly)

Note: EES algorithms are now in the main scalable_proportional_pb package.
Use `from scalable_proportional_pb import ...` for EES functionality.
"""

from .cli import (
    run_experiment,
    save_results,
    setup_results_dir,
    create_argument_parser,
    get_pabulib_files,
    calculate_efficiency,
)

from .mes import (
    run_mes_approval,
    run_mes_cost,
    calculate_efficiency as mes_calculate_efficiency,
    mes_with_budget_increase_exhaustion,
    create_mes_results_df,
)

__all__ = [
    # cli
    "run_experiment",
    "save_results",
    "setup_results_dir",
    "create_argument_parser",
    "get_pabulib_files",
    "calculate_efficiency",
    # mes
    "run_mes_approval",
    "run_mes_cost",
    "mes_calculate_efficiency",
    "mes_with_budget_increase_exhaustion",
    "create_mes_results_df",
]
