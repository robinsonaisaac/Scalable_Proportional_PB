"""
Run Exact Equal Shares with completion (cost/uniform utilities, exhaustive, heuristic).

Uses ADD-OPT-SKIP and continues until all projects are selected.
"""

import pandas as pd
from pathlib import Path
import os
import sys

# Use canonical implementation directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scalable_proportional_pb import parse_pabulib_file, ees_with_outcome, greedy_project_change_uniform
from scalable_proportional_pb.ees import cost_utility
from scalable_proportional_pb.gpc_uniform import compute_L_lists
from core.cli import setup_results_dir, save_results


def add_opt_skip_uniform(election, outcome):
    """
    ADD-OPT-SKIP for uniform utilities: only consider unselected projects.

    Returns minimum d > 0, or None if infinity.
    """
    # Precompute L lists
    L_lists = compute_L_lists(election, outcome, cost_utility)

    d = None  # None means infinity

    for p_id in election.projects:
        if p_id not in outcome.selected:
            gpc_d = greedy_project_change_uniform(election, outcome, p_id, cost_utility, L_lists)
            if gpc_d is not None and gpc_d > 0:
                if d is None or gpc_d < d:
                    d = gpc_d

    return d


def exact_method_of_equal_shares_with_completion_cost_exhaustive_heuristic(pabulib_file: str):
    """
    Run EES with budget completion using ADD-OPT-SKIP heuristic (exhaustive, cost utilities).

    Continues until all projects are selected, tracking monotonicity violations.
    """
    election = parse_pabulib_file(pabulib_file)
    actual_budget = election.budget
    n = election.n
    number_total_projects = election.m

    # Initial EES run with cost utility
    outcome = ees_with_outcome(election, cost_utility)

    most_efficient_selected = set(outcome.selected)
    budget_increase_count = 0
    budget_increase_list = []
    efficiency_tracker = float(outcome.spending_efficiency(actual_budget))
    monotonic_violation = 0
    exceeded_non_exhaustive_case = 0

    prev_outcome = outcome
    current_budget = election.budget
    final_efficiency = 0

    while True:
        # Compute minimum budget increase (heuristic: skip selected projects)
        d = add_opt_skip_uniform(election.with_budget(current_budget), outcome)

        if d is None:  # Infinity - no more changes possible
            break

        budget_increase_count += 1
        current_budget = current_budget + n * d

        # Run EES with increased budget
        outcome = ees_with_outcome(election.with_budget(current_budget), cost_utility)

        if outcome.total_cost > actual_budget:
            exceeded_non_exhaustive_case = 1
        else:
            budget_increase_list.append(float(d))
            prev_outcome = outcome

            efficiency_candidate = float(outcome.spending_efficiency(actual_budget))
            if efficiency_candidate > efficiency_tracker:
                if exceeded_non_exhaustive_case:
                    monotonic_violation = 1
                efficiency_tracker = efficiency_candidate
                most_efficient_selected = set(outcome.selected)

        if len(outcome.selected) == number_total_projects:
            final_efficiency = float(prev_outcome.spending_efficiency(actual_budget))
            break

    data = {
        'most_efficient_project_set': [list(most_efficient_selected)],
        'highest_efficiency_attained': [efficiency_tracker],
        'final_project_set': [list(prev_outcome.selected)],
        'final_efficiency': [final_efficiency],
        'budget_increase_count': [budget_increase_count],
        'len_budget_increase_list': [len(budget_increase_list)],
        'max_budget_increase': [max(budget_increase_list)] if budget_increase_list else [0],
        'min_budget_increase': [min(budget_increase_list)] if budget_increase_list else [0],
        'avg_budget_increase': [sum(budget_increase_list)/len(budget_increase_list)] if budget_increase_list else [0],
        'monotonic_violation': [monotonic_violation]
    }

    return pd.DataFrame(data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_cost_equal_shares_exhaustive_heuristic.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    input_path = Path(file_path).resolve()
    results_dir = setup_results_dir("exact_equal_shares/cost/exhaustive_heuristic")

    try:
        output_filename = f"{input_path.stem}.csv"
        output_path = results_dir / output_filename

        print(f"Processing file: {input_path}")
        print(f"Results will be saved to: {output_path}")

        output_df = exact_method_of_equal_shares_with_completion_cost_exhaustive_heuristic(str(input_path))
        save_results(output_df, results_dir, output_filename)

    except Exception as e:
        print(f"Error during execution: {str(e)}")
        sys.exit(1)
