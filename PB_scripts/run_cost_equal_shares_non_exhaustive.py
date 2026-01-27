"""
Run Exact Equal Shares with completion (cost/uniform utilities, non-exhaustive).

Uses ADD-OPT to find minimum budget increases until budget is exhausted.
"""

import pandas as pd
from pathlib import Path
import os
import sys

# Use canonical implementation directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scalable_proportional_pb import parse_pabulib_file, ees_with_outcome, add_opt_uniform
from scalable_proportional_pb.ees import cost_utility
from core.cli import setup_results_dir, save_results


def exact_method_of_equal_shares_with_completion_cost(pabulib_file: str):
    """
    Run EES with budget completion using ADD-OPT (non-exhaustive, cost utilities).

    Stops when total cost exceeds initial budget.
    """
    election = parse_pabulib_file(pabulib_file)
    actual_budget = election.budget
    n = election.n

    # Initial EES run with cost utility
    outcome = ees_with_outcome(election, cost_utility)

    most_efficient_selected = set(outcome.selected)
    budget_increase_count = 0
    budget_increase_list = []
    efficiency_tracker = float(outcome.spending_efficiency(actual_budget))

    prev_outcome = outcome
    current_budget = election.budget

    while True:
        # Compute minimum budget increase
        d = add_opt_uniform(election.with_budget(current_budget), outcome, cost_utility)

        if d is None:  # Infinity - no more changes possible
            break

        budget_increase_count += 1
        current_budget = current_budget + n * d

        # Run EES with increased budget
        outcome = ees_with_outcome(election.with_budget(current_budget), cost_utility)

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
        print("Usage: python run_cost_equal_shares_non_exhaustive.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    input_path = Path(file_path).resolve()
    results_dir = setup_results_dir("exact_equal_shares/cost/non_exhaustive")

    try:
        output_filename = f"{input_path.stem}.csv"
        output_path = results_dir / output_filename

        print(f"Processing file: {input_path}")
        print(f"Results will be saved to: {output_path}")

        output_df = exact_method_of_equal_shares_with_completion_cost(str(input_path))
        save_results(output_df, results_dir, output_filename)

    except Exception as e:
        print(f"Error during execution: {str(e)}")
        sys.exit(1)
