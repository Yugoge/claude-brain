#!/usr/bin/env python3
"""
FSRS (Free Spaced Repetition Scheduler) Algorithm Implementation

Based on research by Jarrett Ye and open-spaced-repetition community.

Key Concepts:
- Difficulty (D): How hard the concept is for this user (0-10)
- Stability (S): How well it's been retained (days)
- Retrievability (R): Current memory strength (0-1)

Formula:
next_interval = S * log(desired_retention) / log(0.9)
(When desired_retention = 0.9, this simplifies to: next_interval = S)
"""

import math
from typing import Dict, Tuple
from datetime import datetime, timedelta
import json


class FSRSAlgorithm:
    """FSRS spaced repetition algorithm."""

    def __init__(self, parameters: Dict = None):
        """
        Initialize FSRS with parameters.

        Parameters (default pre-trained values):
        - w: Weight vector [w0, w1, w2, ..., w17] (18 parameters)
        - desired_retention: Target retention rate (default: 0.9)
        - maximum_interval: Max days between reviews (default: 36500)
        """
        self.w = parameters.get("w") if parameters else self.default_parameters()
        self.desired_retention = parameters.get("desired_retention", 0.9) if parameters else 0.9
        self.maximum_interval = parameters.get("maximum_interval", 36500) if parameters else 36500

    @staticmethod
    def default_parameters() -> list:
        """
        Default pre-trained FSRS parameters.

        Trained on 10,000+ review dataset.
        Provides good performance before personalization.
        """
        return [
            0.4072, 1.1829, 3.1262, 15.4722,  # w0-w3: Initial stability
            7.2102, 0.5316, 1.0651, 0.0234,   # w4-w7: Difficulty factors
            1.616, 0.1544, 1.0826, 1.9813,    # w8-w11: Stability increase
            0.0953, 0.2975, 2.2042, 0.2407,   # w12-w15: Difficulty adjustment
            2.9466, 0.5034                     # w16-w17: Forgetting factors
        ]

    def initial_difficulty(self, rating: int) -> float:
        """
        Calculate initial difficulty based on first review rating.

        Args:
            rating: User rating (1=Again, 2=Hard, 3=Good, 4=Easy)

        Returns:
            Difficulty (0-10 scale)
        """
        if rating == 1:  # Again
            return self.w[4]
        elif rating == 2:  # Hard
            return self.w[5]
        elif rating == 3:  # Good
            return self.w[6]
        else:  # Easy (rating == 4)
            return self.w[7]

    def initial_stability(self, rating: int) -> float:
        """
        Calculate initial stability based on first review rating.

        Args:
            rating: User rating (1-4)

        Returns:
            Stability (days)
        """
        return max(self.w[rating - 1], 0.1)  # w0-w3 correspond to ratings 1-4

    def next_difficulty(self, difficulty: float, rating: int) -> float:
        """
        Calculate next difficulty after review.

        Args:
            difficulty: Current difficulty (0-10)
            rating: User rating (1-4)

        Returns:
            New difficulty (0-10)
        """
        delta_d = rating - 3  # Offset from "Good" rating
        difficulty_adjustment = self.w[15] * delta_d

        next_d = difficulty + difficulty_adjustment
        return max(1, min(10, next_d))  # Clamp to [1, 10]

    def next_stability(
        self,
        difficulty: float,
        stability: float,
        retrievability: float,
        rating: int
    ) -> float:
        """
        Calculate next stability after review.

        Args:
            difficulty: Current difficulty (0-10)
            stability: Current stability (days)
            retrievability: Current retrievability (0-1)
            rating: User rating (1-4)

        Returns:
            New stability (days)
        """
        if rating == 1:  # Again (forgot)
            # Forgotten: Reset stability
            # Formula: S' = w11 * D^(-w12) * ((S+1)^w13 - 1) * e^(w14*(1-R))
            new_stability = (
                self.w[11] *
                (difficulty ** -self.w[12]) *
                ((stability + 1) ** self.w[13] - 1) *  # Fixed: added - 1
                math.exp(self.w[14] * (1 - retrievability))
            )
            # Cap at old stability: forgetting cannot increase stability
            new_stability = min(new_stability, stability)
        else:  # Remembered (Hard, Good, Easy)
            # Remembered: Increase stability
            # Calculate base multiplier
            hard_penalty = self.w[15] if rating == 2 else 0
            easy_bonus = self.w[16] if rating == 4 else 0

            # Stability increase factor
            si = (
                math.exp(self.w[8]) *
                (11 - difficulty) *
                (stability ** -self.w[9]) *
                (math.exp(self.w[10] * (1 - retrievability)) - 1)
            )

            new_stability = stability * (1 + si - hard_penalty + easy_bonus)

        return max(0.1, min(new_stability, self.maximum_interval))

    def calculate_retrievability(self, elapsed_days: int, stability: float) -> float:
        """
        Calculate current retrievability based on time elapsed.

        Uses forgetting curve: R = exp(ln(0.9) * elapsed / stability)

        Args:
            elapsed_days: Days since last review
            stability: Current stability

        Returns:
            Retrievability (0-1)
        """
        return math.exp(math.log(0.9) * elapsed_days / stability)

    def calculate_interval(self, stability: float) -> int:
        """
        Calculate next review interval.

        Formula (FSRS official): interval = S * log(DR) / log(0.9)
        Where DR is desired_retention (default 0.9)

        When DR = 0.9, this simplifies to interval = S
        (because log(0.9)/log(0.9) = 1)

        Source: https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm

        Args:
            stability: Current stability (days)

        Returns:
            Days until next review
        """
        # Official FSRS formula
        interval = stability * math.log(self.desired_retention) / math.log(0.9)
        return max(1, min(int(round(interval)), self.maximum_interval))

    def review(
        self,
        current_state: Dict,
        rating: int,
        review_date: datetime = None
    ) -> Dict:
        """
        Process a review and calculate next state.

        Args:
            current_state: {
                "difficulty": float,
                "stability": float,
                "last_review": str (ISO date),
                "review_count": int
            }
            rating: User rating (1=Again, 2=Hard, 3=Good, 4=Easy)
            review_date: Date of review (default: now)

        Returns:
            New state (JSON-safe with string dates): {
                "difficulty": float,
                "stability": float,
                "retrievability": float,
                "interval": int,
                "next_review": str (ISO date),
                "review_count": int,
                "last_review": str (ISO date)
            }
        """
        if review_date is None:
            review_date = datetime.now()

        # First review (new concept)
        if current_state.get("review_count", 0) == 0:
            difficulty = self.initial_difficulty(rating)
            stability = self.initial_stability(rating)
            retrievability = 1.0
        else:
            # Calculate elapsed time
            # Handle both datetime objects and ISO strings
            last_review = current_state["last_review"]
            if isinstance(last_review, str):
                last_review = datetime.fromisoformat(last_review.replace('Z', '+00:00'))
                # Convert to naive datetime (remove timezone info)
                if last_review.tzinfo is not None:
                    last_review = last_review.replace(tzinfo=None)
            elapsed = (review_date - last_review).days
            elapsed = max(0, elapsed)

            # Calculate current retrievability
            retrievability = self.calculate_retrievability(
                elapsed,
                current_state["stability"]
            )

            # Update difficulty and stability
            difficulty = self.next_difficulty(current_state["difficulty"], rating)
            stability = self.next_stability(
                current_state["difficulty"],
                current_state["stability"],
                retrievability,
                rating
            )

        # Calculate next interval
        interval = self.calculate_interval(stability)
        next_review = review_date + timedelta(days=interval)

        # Always return JSON-safe string dates
        return {
            "difficulty": round(difficulty, 4),
            "stability": round(stability, 4),
            "retrievability": round(retrievability, 4),
            "interval": interval,
            "next_review": next_review.strftime('%Y-%m-%d'),
            "review_count": current_state.get("review_count", 0) + 1,
            "last_review": review_date.strftime('%Y-%m-%d')
        }

    def predict_retention(self, state: Dict, days_ahead: int) -> float:
        """
        Predict retention rate N days in the future.

        Args:
            state: Current FSRS state
            days_ahead: Days to predict

        Returns:
            Predicted retention (0-1)
        """
        return self.calculate_retrievability(days_ahead, state["stability"])
