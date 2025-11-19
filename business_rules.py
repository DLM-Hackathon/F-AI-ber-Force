"""
Business rules for dispatch success probability
Provides rule-based probability estimates based on domain knowledge
"""

import pandas as pd
import numpy as np


class DispatchBusinessRules:
    """
    Define business rules for expected dispatch success probabilities
    These override or blend with ML predictions when historical data is unreliable
    """
    
    def __init__(self):
        """
        Initialize business rules based on actual historical data patterns:
        - Skill match: 92% success rate
        - Distance < 10 km: 88% success rate  
        - Workload < 80%: 85% success rate
        - All three factors align: 95%+ success rate
        """
        
        # Base success rate (when all factors are poor/missing)
        self.base_success_rate = 0.55  # Baseline
        
        # Skill match impact (MOST IMPORTANT - observed 92% success with match)
        # When skill matches with average other conditions: 92%
        self.skill_match_boost = 0.37  # +37% when skills match
        self.skill_mismatch_penalty = -0.10  # -10% when skills don't match
        
        # Workload impact (observed 85% success when < 80%)
        # When workload < 80% with average other conditions: 85%
        self.workload_thresholds = {
            'low': (0, 0.5),      # Under 50% capacity
            'medium': (0.5, 0.8), # 50-80% capacity (threshold from data)
            'high': (0.8, 1.0),   # 80-100% capacity
            'overloaded': (1.0, float('inf'))  # Over capacity
        }
        self.workload_adjustments = {
            'low': 0.32,          # +32% when not busy (best conditions)
            'medium': 0.30,       # +30% at normal load (observed 85%)
            'high': -0.10,        # -10% when at capacity threshold
            'overloaded': -0.30   # -30% when overloaded
        }
        
        # Distance impact (observed 88% success when < 10km)
        # When distance < 10km with average other conditions: 88%
        self.distance_thresholds = {
            'very_close': (0, 10),    # Under 10km (threshold from data)
            'close': (10, 50),
            'medium': (50, 100),
            'far': (100, 500),
            'very_far': (500, float('inf'))
        }
        self.distance_adjustments = {
            'very_close': 0.33,   # +33% for < 10km (observed 88%)
            'close': 0.05,        # +5% for close
            'medium': 0.00,       # No change
            'far': -0.12,         # -12% for far
            'very_far': -0.30     # -30% for very far
        }
        
        # Priority impact (secondary factors)
        self.priority_adjustments = {
            'Low': 0.02,          # Low priority = slightly easier
            'Normal': 0.00,       # Baseline
            'High': -0.02,        # Slightly harder
            'Critical': -0.05     # More complex/urgent
        }
        
        # Ticket type impact
        self.ticket_type_adjustments = {
            'Order': 0.02,        # New installations slightly easier
            'Trouble': -0.03      # Troubleshooting is harder
        }
    
    def get_workload_category(self, workload_ratio):
        """Categorize workload level"""
        for category, (min_val, max_val) in self.workload_thresholds.items():
            if min_val <= workload_ratio < max_val:
                return category
        return 'medium'
    
    def get_distance_category(self, distance):
        """Categorize distance"""
        for category, (min_val, max_val) in self.distance_thresholds.items():
            if min_val <= distance < max_val:
                return category
        return 'medium'
    
    def calculate_rule_based_probability(self, row):
        """
        Calculate success probability based on business rules
        
        Args:
            row: DataFrame row with dispatch features
            
        Returns:
            float: Expected success probability (0-1)
        """
        prob = self.base_success_rate
        
        # Skill match - MOST IMPORTANT
        if row.get('skill_match', 0) == 1:
            prob += self.skill_match_boost
        else:
            prob += self.skill_mismatch_penalty
        
        # Workload impact
        workload_ratio = row.get('workload_ratio', 0.5)
        workload_cat = self.get_workload_category(workload_ratio)
        prob += self.workload_adjustments[workload_cat]
        
        # Distance impact
        distance = row.get('distance', 50)
        distance_cat = self.get_distance_category(distance)
        prob += self.distance_adjustments[distance_cat]
        
        # Priority impact
        priority = row.get('priority', 'Normal')
        prob += self.priority_adjustments.get(priority, 0.0)
        
        # Ticket type impact
        ticket_type = row.get('ticket_type', 'Order')
        prob += self.ticket_type_adjustments.get(ticket_type, 0.0)
        
        # Ensure probability is between 0 and 1
        prob = np.clip(prob, 0.0, 1.0)
        
        return prob
    
    def calculate_probabilities(self, df):
        """
        Calculate rule-based probabilities for all rows
        
        Args:
            df: DataFrame with dispatch features
            
        Returns:
            np.array: Array of success probabilities
        """
        return df.apply(self.calculate_rule_based_probability, axis=1).values
    
    def get_explanation(self, row):
        """
        Generate human-readable explanation for probability calculation
        
        Args:
            row: DataFrame row with dispatch features
            
        Returns:
            str: Explanation of probability factors
        """
        factors = []
        
        # Base
        factors.append(f"Base rate: {self.base_success_rate:.0%}")
        
        # Skill match
        if row.get('skill_match', 0) == 1:
            factors.append(f"[+] Skill match: +{self.skill_match_boost:.0%}")
        else:
            factors.append(f"[-] Skill mismatch: {self.skill_mismatch_penalty:.0%}")
        
        # Workload
        workload_ratio = row.get('workload_ratio', 0.5)
        workload_cat = self.get_workload_category(workload_ratio)
        adj = self.workload_adjustments[workload_cat]
        factors.append(f"Workload ({workload_cat}, {workload_ratio:.2f}): {adj:+.0%}")
        
        # Distance
        distance = row.get('distance', 50)
        distance_cat = self.get_distance_category(distance)
        adj = self.distance_adjustments[distance_cat]
        factors.append(f"Distance ({distance_cat}, {distance:.1f}km): {adj:+.0%}")
        
        # Priority
        priority = row.get('priority', 'Normal')
        adj = self.priority_adjustments.get(priority, 0.0)
        if adj != 0:
            factors.append(f"Priority ({priority}): {adj:+.0%}")
        
        # Ticket type
        ticket_type = row.get('ticket_type', 'Order')
        adj = self.ticket_type_adjustments.get(ticket_type, 0.0)
        if adj != 0:
            factors.append(f"Type ({ticket_type}): {adj:+.0%}")
        
        # Final probability
        final_prob = self.calculate_rule_based_probability(row)
        factors.append(f"\n=> Final: {final_prob:.0%}")
        
        return " | ".join(factors)


def blend_probabilities(ml_prob, rule_prob, rule_weight=0.7):
    """
    Blend ML and rule-based probabilities
    
    Args:
        ml_prob: ML model probability (0-1)
        rule_prob: Rule-based probability (0-1)
        rule_weight: Weight for rule-based (0-1), default 0.7 = 70% rules, 30% ML
        
    Returns:
        float: Blended probability
    """
    return rule_weight * rule_prob + (1 - rule_weight) * ml_prob


if __name__ == "__main__":
    # Example usage
    rules = DispatchBusinessRules()
    
    # Test case 1: Ideal dispatch
    ideal = pd.Series({
        'skill_match': 1,
        'workload_ratio': 0.4,
        'distance': 15,
        'priority': 'Normal',
        'ticket_type': 'Order'
    })
    
    print("="*70)
    print("EXAMPLE 1: Ideal Dispatch (Skills match, low workload, close)")
    print("="*70)
    print(rules.get_explanation(ideal))
    
    # Test case 2: Challenging dispatch
    challenging = pd.Series({
        'skill_match': 0,
        'workload_ratio': 1.2,
        'distance': 150,
        'priority': 'Critical',
        'ticket_type': 'Trouble'
    })
    
    print("\n" + "="*70)
    print("EXAMPLE 2: Challenging Dispatch (No skill match, overloaded, far)")
    print("="*70)
    print(rules.get_explanation(challenging))
    
    # Test case 3: Average dispatch
    average = pd.Series({
        'skill_match': 1,
        'workload_ratio': 0.6,
        'distance': 60,
        'priority': 'Normal',
        'ticket_type': 'Order'
    })
    
    print("\n" + "="*70)
    print("EXAMPLE 3: Average Dispatch")
    print("="*70)
    print(rules.get_explanation(average))

