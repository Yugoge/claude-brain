#!/usr/bin/env python3
"""
FSRS parameter personalization engine.

Uses maximum likelihood estimation to optimize parameters
based on user's review history (30+ reviews required).
"""

import numpy as np
from scipy.optimize import minimize
from typing import List, Dict, Tuple
import json
from datetime import datetime
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(__file__))

from fsrs_algorithm import FSRSAlgorithm


class FSRSOptimizer:
    """Optimize FSRS parameters for individual user."""

    def __init__(self, review_history: List[Dict]):
        """
        Initialize optimizer with review history.

        Args:
            review_history: List of reviews [{
                "concept": str,
                "rating": int (1-4),
                "elapsed_days": int,
                "difficulty": float,
                "stability": float
            }]
        """
        self.history = review_history
        self.default_params = FSRSAlgorithm.default_parameters()

    def loss_function(self, w: np.ndarray) -> float:
        """
        Calculate loss (negative log-likelihood).

        Lower loss = better fit to user's review history.

        Args:
            w: FSRS weight vector

        Returns:
            Loss value
        """
        fsrs = FSRSAlgorithm({"w": w.tolist()})
        total_loss = 0.0

        for review in self.history:
            # Predict retention
            predicted_retention = fsrs.calculate_retrievability(
                review["elapsed_days"],
                review["stability"]
            )

            # Actual result (1 = remembered, 0 = forgot)
            actual = 1 if review["rating"] > 1 else 0

            # Log-likelihood
            if actual == 1:
                loss = -np.log(predicted_retention + 1e-10)
            else:
                loss = -np.log(1 - predicted_retention + 1e-10)

            total_loss += loss

        return total_loss

    def optimize(self, max_iterations: int = 500) -> Dict:
        """
        Optimize parameters using gradient descent.

        Args:
            max_iterations: Maximum optimization iterations

        Returns:
            Optimized parameters: {
                "w": list,
                "loss": float,
                "improvement": float
            }
        """
        # Start from default parameters
        initial_w = np.array(self.default_params)

        # Baseline loss
        baseline_loss = self.loss_function(initial_w)

        # Optimize
        result = minimize(
            self.loss_function,
            initial_w,
            method='L-BFGS-B',
            options={'maxiter': max_iterations}
        )

        optimized_w = result.x
        optimized_loss = result.fun
        improvement = (baseline_loss - optimized_loss) / baseline_loss if baseline_loss > 0 else 0

        return {
            "w": optimized_w.tolist(),
            "loss": float(optimized_loss),
            "baseline_loss": float(baseline_loss),
            "improvement": float(improvement),
            "success": bool(result.success)
        }

    def should_optimize(self) -> Tuple[bool, str]:
        """
        Check if optimization is recommended.

        Requires:
        - At least 30 reviews
        - At least 10 "Again" (forgot) ratings
        - At least 3 different concepts

        Returns:
            (should_optimize, reason)
        """
        if len(self.history) < 30:
            return False, f"Need 30+ reviews (have {len(self.history)})"

        forgot_count = sum(1 for r in self.history if r["rating"] == 1)
        if forgot_count < 10:
            return False, f"Need 10+ forgot events (have {forgot_count})"

        unique_concepts = len(set(r["concept"] for r in self.history))
        if unique_concepts < 3:
            return False, f"Need 3+ concepts (have {unique_concepts})"

        return True, "Ready for optimization"


def run_optimization(user_id: str = "default") -> Dict:
    """
    Run optimization for user if criteria met.

    Args:
        user_id: User identifier

    Returns:
        Optimization results or error
    """
    # Load review history from .review/history.json
    history_file = ".review/history.json"
    if not os.path.exists(history_file):
        return {
            "optimized": False,
            "reason": "No review history found"
        }

    with open(history_file) as f:
        history_data = json.load(f)

    # Extract reviews from sessions
    user_history = []
    if "sessions" in history_data:
        for session in history_data["sessions"]:
            if session.get("session_type") == "review":
                for review in session.get("reviews", []):
                    # Convert to optimizer format
                    if "fsrs_state" in review:
                        user_history.append({
                            "concept": review.get("concept_name", "unknown"),
                            "rating": review.get("rating", 3),
                            "elapsed_days": review.get("elapsed_days", 0),
                            "difficulty": review.get("fsrs_state", {}).get("difficulty", 5.0),
                            "stability": review.get("fsrs_state", {}).get("stability", 1.0)
                        })

    if not user_history:
        return {
            "optimized": False,
            "reason": "No FSRS reviews found in history"
        }

    optimizer = FSRSOptimizer(user_history)
    should_run, reason = optimizer.should_optimize()

    if not should_run:
        return {
            "optimized": False,
            "reason": reason
        }

    # Run optimization
    result = optimizer.optimize()

    if result["success"]:
        # Save optimized parameters
        params_file = f".review/fsrs-params-{user_id}.json"
        with open(params_file, "w") as f:
            json.dump({
                "w": result["w"],
                "optimized_at": datetime.now().isoformat(),
                "review_count": len(user_history),
                "improvement": result["improvement"]
            }, f, indent=2)

        return {
            "optimized": True,
            "improvement": result["improvement"],
            "params_file": params_file,
            "review_count": len(user_history)
        }
    else:
        return {
            "optimized": False,
            "reason": "Optimization failed to converge"
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimize FSRS parameters for user")
    parser.add_argument("--user-id", default="default", help="User ID")
    args = parser.parse_args()

    result = run_optimization(args.user_id)

    print("=" * 50)
    print("FSRS Parameter Optimization")
    print("=" * 50)

    if result["optimized"]:
        print(f"✅ Optimization successful!")
        print(f"   Improvement: {result['improvement']*100:.1f}%")
        print(f"   Review count: {result['review_count']}")
        print(f"   Params saved to: {result['params_file']}")
    else:
        print(f"❌ Optimization not performed")
        print(f"   Reason: {result['reason']}")
