"""
Tests for equivalence between OLD (PB_scripts/core/) and NEW (scalable_proportional_pb/) implementations.

These tests verify that both implementations produce identical results, which is
critical for validating the refactoring that replaces the OLD algorithms with
wrappers around the NEW canonical implementation.
"""

import pytest
from fractions import Fraction
from pathlib import Path
import sys

# Add paths for both implementations
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "PB_scripts"))

# NEW implementation imports
from scalable_proportional_pb import (
    parse_pabulib_file,
    ees_with_outcome,
    add_opt_cardinal,
    add_opt_uniform,
)
from scalable_proportional_pb.ees import cardinal_utility as new_cardinal_utility, cost_utility as new_cost_utility
from scalable_proportional_pb.types import Election, Project

# OLD implementation imports (uses pabutools)
try:
    from pabutools.election import parse_pabulib
    from core.ees import (
        exact_method_of_equal_shares,
        exact_method_of_equal_shares_approval,
        exact_method_of_equal_shares_cost,
    )
    from core.add_opt import add_opt_approval, add_opt_cost
    from core.utils import profile_preprocessing, cardinal_utility, cost_utility
    PABUTOOLS_AVAILABLE = True
except ImportError:
    PABUTOOLS_AVAILABLE = False


# Test instance directory
TEST_INSTANCES_DIR = Path(__file__).parent.parent.parent / "ees_vs_mes_test_instances"


def get_test_instance_paths():
    """Get all .pb files from test instances directory."""
    if not TEST_INSTANCES_DIR.exists():
        return []
    return sorted(TEST_INSTANCES_DIR.glob("instance_*.pb"))


@pytest.fixture
def simple_election_data():
    """Simple election data for creating test instances."""
    return {
        "projects": {"A": 10, "B": 10, "C": 20},
        "votes": [
            ["A", "C"],      # Voter 0
            ["A", "B"],      # Voter 1
            ["B", "C"],      # Voter 2
            ["C"],           # Voter 3
        ],
        "budget": 40,
    }


def make_new_election(data: dict) -> Election:
    """Create a NEW API Election from dict data."""
    projects = {
        pid: Project(id=pid, cost=Fraction(cost))
        for pid, cost in data["projects"].items()
    }
    voters = list(range(len(data["votes"])))
    approvals = {i: set(data["votes"][i]) for i in voters}
    return Election(
        projects=projects,
        voters=voters,
        approvals=approvals,
        budget=Fraction(data["budget"]),
    )


@pytest.mark.skipif(not PABUTOOLS_AVAILABLE, reason="pabutools not installed")
class TestEESEquivalence:
    """Test equivalence of EES implementations."""

    def test_basic_election_approval(self, simple_election_data):
        """Test that basic election gives same results with approval utility."""
        # Create NEW election
        new_election = make_new_election(simple_election_data)
        new_outcome = ees_with_outcome(new_election, new_cardinal_utility)

        # For OLD, we need a pabutools instance - create a temp .pb file
        import tempfile
        pb_content = """META
key;value
budget;40
num_projects;3
num_votes;4
vote_type;approval
PROJECTS
project_id;cost;name
A;10;A
B;10;B
C;20;C
VOTES
voter_id;vote
1;A,C
2;A,B
3;B,C
4;C
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pb', delete=False) as f:
            f.write(pb_content)
            temp_path = f.name

        try:
            # Run OLD implementation
            instance, profile = parse_pabulib(temp_path)
            old_result = exact_method_of_equal_shares(
                instance, profile, utility_function=cardinal_utility
            )
            old_funded, old_payments, old_shares, old_cost = old_result

            # Compare selected projects
            old_selected = {p.name for p in old_funded.keys()}
            assert old_selected == new_outcome.selected, \
                f"Selected projects differ: OLD={old_selected}, NEW={new_outcome.selected}"

            # Compare total cost
            assert abs(old_cost - float(new_outcome.total_cost)) < 1e-10, \
                f"Total cost differs: OLD={old_cost}, NEW={float(new_outcome.total_cost)}"

            # Compare selection order
            old_order = [p.name for p in old_funded.keys()]
            new_order = [pid for pid, _ in new_outcome.selection_order]
            assert old_order == new_order, \
                f"Selection order differs: OLD={old_order}, NEW={new_order}"

        finally:
            import os
            os.unlink(temp_path)

    def test_basic_election_cost_utility(self, simple_election_data):
        """Test that basic election gives same results with cost utility."""
        new_election = make_new_election(simple_election_data)
        new_outcome = ees_with_outcome(new_election, new_cost_utility)

        import tempfile
        pb_content = """META
key;value
budget;40
num_projects;3
num_votes;4
vote_type;approval
PROJECTS
project_id;cost;name
A;10;A
B;10;B
C;20;C
VOTES
voter_id;vote
1;A,C
2;A,B
3;B,C
4;C
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pb', delete=False) as f:
            f.write(pb_content)
            temp_path = f.name

        try:
            instance, profile = parse_pabulib(temp_path)
            old_result = exact_method_of_equal_shares_cost(instance, profile)
            old_funded, old_payments, old_shares, old_cost = old_result

            old_selected = {p.name for p in old_funded.keys()}
            assert old_selected == new_outcome.selected, \
                f"Selected projects differ: OLD={old_selected}, NEW={new_outcome.selected}"

            assert abs(old_cost - float(new_outcome.total_cost)) < 1e-10, \
                f"Total cost differs: OLD={old_cost}, NEW={float(new_outcome.total_cost)}"

        finally:
            import os
            os.unlink(temp_path)

    @pytest.mark.parametrize("pb_file", get_test_instance_paths())
    def test_ees_on_test_instances(self, pb_file):
        """Test EES equivalence on all test instances."""
        # Run NEW implementation
        new_election = parse_pabulib_file(str(pb_file))
        new_outcome = ees_with_outcome(new_election, new_cardinal_utility)

        # Run OLD implementation
        instance, profile = parse_pabulib(str(pb_file))
        old_result = exact_method_of_equal_shares(
            instance, profile, utility_function=cardinal_utility
        )
        old_funded, old_payments, old_shares, old_cost = old_result

        # Compare selected projects
        old_selected = {p.name for p in old_funded.keys()}
        assert old_selected == new_outcome.selected, \
            f"[{pb_file.name}] Selected projects differ: OLD={old_selected}, NEW={new_outcome.selected}"

        # Compare total cost
        assert abs(old_cost - float(new_outcome.total_cost)) < 1e-10, \
            f"[{pb_file.name}] Total cost differs: OLD={old_cost}, NEW={float(new_outcome.total_cost)}"

        # Compare selection order
        old_order = [p.name for p in old_funded.keys()]
        new_order = [pid for pid, _ in new_outcome.selection_order]
        assert old_order == new_order, \
            f"[{pb_file.name}] Selection order differs: OLD={old_order}, NEW={new_order}"


@pytest.mark.skipif(not PABUTOOLS_AVAILABLE, reason="pabutools not installed")
class TestPaymentEquivalence:
    """Test that payment allocations are equivalent."""

    def test_payment_amounts_match(self, simple_election_data):
        """Test that individual voter payments match between implementations."""
        new_election = make_new_election(simple_election_data)
        new_outcome = ees_with_outcome(new_election, new_cardinal_utility)

        import tempfile
        pb_content = """META
key;value
budget;40
num_projects;3
num_votes;4
vote_type;approval
PROJECTS
project_id;cost;name
A;10;A
B;10;B
C;20;C
VOTES
voter_id;vote
1;A,C
2;A,B
3;B,C
4;C
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pb', delete=False) as f:
            f.write(pb_content)
            temp_path = f.name

        try:
            instance, profile = parse_pabulib(temp_path)
            old_result = exact_method_of_equal_shares(
                instance, profile, utility_function=cardinal_utility
            )
            old_funded, old_payments, old_shares, old_cost = old_result

            # Build mapping: OLD uses (voter_name, project_object) -> amount
            # NEW uses (voter_idx, project_id) -> Fraction
            # OLD voter names are 1-indexed (from profile_preprocessing)

            preprocessed = profile_preprocessing(profile)
            voter_name_to_idx = {v['name']: i for i, v in enumerate(preprocessed)}

            for (voter_name, project), old_amount in old_payments.items():
                if old_amount == 0:
                    continue
                voter_idx = voter_name_to_idx[voter_name]
                project_id = project.name
                new_amount = new_outcome.payment(voter_idx, project_id)

                assert abs(old_amount - float(new_amount)) < 1e-10, \
                    f"Payment differs for voter {voter_name}({voter_idx}), project {project_id}: " \
                    f"OLD={old_amount}, NEW={float(new_amount)}"

        finally:
            import os
            os.unlink(temp_path)

    def test_leftover_budgets_match(self, simple_election_data):
        """Test that remaining voter budgets match."""
        new_election = make_new_election(simple_election_data)
        new_outcome = ees_with_outcome(new_election, new_cardinal_utility)

        import tempfile
        pb_content = """META
key;value
budget;40
num_projects;3
num_votes;4
vote_type;approval
PROJECTS
project_id;cost;name
A;10;A
B;10;B
C;20;C
VOTES
voter_id;vote
1;A,C
2;A,B
3;B,C
4;C
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pb', delete=False) as f:
            f.write(pb_content)
            temp_path = f.name

        try:
            instance, profile = parse_pabulib(temp_path)
            old_result = exact_method_of_equal_shares(
                instance, profile, utility_function=cardinal_utility
            )
            old_funded, old_payments, old_shares, old_cost = old_result

            preprocessed = profile_preprocessing(profile)
            voter_name_to_idx = {v['name']: i for i, v in enumerate(preprocessed)}

            for voter_name, old_leftover in old_shares.items():
                voter_idx = voter_name_to_idx[voter_name]
                new_leftover = new_outcome.leftover_budgets.get(voter_idx, Fraction(0))

                assert abs(old_leftover - float(new_leftover)) < 1e-10, \
                    f"Leftover budget differs for voter {voter_name}({voter_idx}): " \
                    f"OLD={old_leftover}, NEW={float(new_leftover)}"

        finally:
            import os
            os.unlink(temp_path)


class TestNewImplementationOnly:
    """Tests that verify NEW implementation produces expected results (no OLD dependency)."""

    @pytest.mark.parametrize("pb_file", get_test_instance_paths())
    def test_new_implementation_runs(self, pb_file):
        """Verify NEW implementation runs without error on all test instances."""
        election = parse_pabulib_file(str(pb_file))
        outcome = ees_with_outcome(election, new_cardinal_utility)

        # Basic sanity checks
        assert outcome.selected is not None
        assert outcome.total_cost >= 0
        assert outcome.total_cost <= election.budget

        # All selected projects should have payments summing to their cost
        for pid in outcome.selected:
            total_payments = sum(
                outcome.payments.get((v, pid), Fraction(0))
                for v in election.voters
            )
            assert total_payments == election.projects[pid].cost, \
                f"[{pb_file.name}] Project {pid} payments don't sum to cost"

    def test_tie_breaking_determinism(self):
        """Test that tie-breaking is deterministic (larger project ID wins)."""
        # Create election with projects that should tie
        election = Election(
            projects={
                "A": Project(id="A", cost=Fraction(10)),
                "B": Project(id="B", cost=Fraction(10)),
            },
            voters=[0, 1],
            approvals={
                0: {"A", "B"},
                1: {"A", "B"},
            },
            budget=Fraction(20),
        )

        outcome = ees_with_outcome(election, new_cardinal_utility)

        # With equal BpB, larger project ID ("B" > "A") should be selected first
        assert outcome.selection_order[0][0] == "B", \
            f"Expected 'B' to be selected first (larger ID), got {outcome.selection_order[0][0]}"

    def test_fraction_precision(self):
        """Test that Fraction arithmetic preserves precision."""
        # Create election where float would lose precision
        election = Election(
            projects={
                "P": Project(id="P", cost=Fraction(1, 3)),  # 0.333... infinite decimal
            },
            voters=[0, 1, 2],
            approvals={
                0: {"P"},
                1: {"P"},
                2: {"P"},
            },
            budget=Fraction(1, 3),
        )

        outcome = ees_with_outcome(election, new_cardinal_utility)

        # Each voter should pay exactly 1/9
        expected_payment = Fraction(1, 9)
        for v in [0, 1, 2]:
            actual = outcome.payment(v, "P")
            assert actual == expected_payment, \
                f"Voter {v} payment should be exactly {expected_payment}, got {actual}"


# Expected outcomes for test instances (from ees_vs_mes_test_instances README)
EXPECTED_OUTCOMES = {
    "instance_01_basic_difference.pb": {"A", "B"},  # EES selects A and B
    "instance_03_cascading_poverty.pb": {"A"},      # EES selects only A
    "instance_07_rich_poor_divide.pb": {"B"},       # EES selects only B
    "instance_09_asymmetric_costs.pb": {"B", "C"},  # EES selects B and C
    # Add more expected outcomes as they are documented
}


class TestExpectedOutcomes:
    """Test that implementations match documented expected outcomes."""

    @pytest.mark.parametrize("filename,expected_selected", EXPECTED_OUTCOMES.items())
    def test_expected_selected_projects(self, filename, expected_selected):
        """Test NEW implementation matches expected outcomes."""
        pb_path = TEST_INSTANCES_DIR / filename
        if not pb_path.exists():
            pytest.skip(f"Test file {filename} not found")

        election = parse_pabulib_file(str(pb_path))
        outcome = ees_with_outcome(election, new_cardinal_utility)

        assert outcome.selected == expected_selected, \
            f"[{filename}] Expected {expected_selected}, got {outcome.selected}"
