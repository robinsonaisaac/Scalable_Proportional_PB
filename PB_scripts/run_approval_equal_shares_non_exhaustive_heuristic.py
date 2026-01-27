"""
Run Exact Equal Shares with completion (approval utilities, non-exhaustive, heuristic).

Uses ADD-OPT-SKIP (skips already-selected projects) to find minimum budget increases.
"""

import pandas as pd
from pathlib import Path
import os
import sys

# Use canonical implementation directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scalable_proportional_pb import parse_pabulib_file, ees_with_outcome, greedy_project_change_cardinal
from scalable_proportional_pb.ees import cardinal_utility
from core.cli import setup_results_dir, save_results


def add_opt_skip_cardinal(election, outcome):
    """
    ADD-OPT-SKIP: only consider unselected projects.

    Returns minimum d > 0, or None if infinity.
    """
    d = None  # None means infinity

    for p_id in election.projects:
        if p_id not in outcome.selected:
            gpc_d = greedy_project_change_cardinal(election, outcome, p_id)
            if gpc_d is not None and gpc_d > 0:
                if d is None or gpc_d < d:
                    d = gpc_d

    return d


def exact_method_of_equal_shares_with_completion_approval_heuristic(pabulib_file: str):
    """
    Run EES with budget completion using ADD-OPT-SKIP heuristic (non-exhaustive).

    Stops when total cost exceeds initial budget.
    """
    election = parse_pabulib_file(pabulib_file)
    actual_budget = election.budget
    n = election.n

    # Initial EES run
    outcome = ees_with_outcome(election, cardinal_utility)

    most_efficient_selected = set(outcome.selected)
    budget_increase_count = 0
    budget_increase_list = []
    efficiency_tracker = float(outcome.spending_efficiency(actual_budget))

    prev_outcome = outcome
    current_budget = election.budget

    while True:
        # Compute minimum budget increase (heuristic: skip selected projects)
        d = add_opt_skip_cardinal(election.with_budget(current_budget), outcome)

        if d is None:  # Infinity - no more changes possible
            break

        budget_increase_count += 1
        current_budget = current_budget + n * d

        # Run EES with increased budget
        outcome = ees_with_outcome(election.with_budget(current_budget), cardinal_utility)

        if outcome.total_cost > actual_budget:
            break

        budget_increase_list.append(float(d))
        prev_outcome = outcome

        efficiency_candidate = float(outcome.spending_efficiency(actual_budget))
        if efficiency_candidate > efficiency_tracker:
            efficiency_tracker = efficiency_candidate
            most_efficient_selected = set(outcome.selected)

    final_efficiency = float(prev_outcome.spending_efficiency(actual_budget))

    data = {
        'most_efficient_project_set': [list(most_efficient_selected)],
        'highest_efficiency_attained': [efficiency_tracker],
        'final_project_set': [list(prev_outcome.selected)],
        'final_efficiency': [final_efficiency],
        'budget_increase_count': [budget_increase_count],
        'len_budget_increase_list': [len(budget_increase_list)],
        'max_budget_increase': [max(budget_increase_list)] if budget_increase_list else [0],
        'min_budget_increase': [min(budget_increase_list)] if budget_increase_list else [0],
        'avg_budget_increase': [sum(budget_increase_list)/len(budget_increase_list)] if budget_increase_list else [0]
    }

    return pd.DataFrame(data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_approval_equal_shares_non_exhaustive_heuristic.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    input_path = Path(file_path).resolve()
    results_dir = setup_results_dir("exact_equal_shares/approval/non_exhaustive_heuristic")

    try:
        output_filename = f"{input_path.stem}.csv"
        output_path = results_dir / output_filename

        print(f"Processing file: {input_path}")
        print(f"Results will be saved to: {output_path}")

        output_df = exact_method_of_equal_shares_with_completion_approval_heuristic(str(input_path))
        save_results(output_df, results_dir, output_filename)

    except Exception as e:
        print(f"Error during execution: {str(e)}")
        sys.exit(1)
