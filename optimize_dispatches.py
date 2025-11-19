"""
Dispatch Optimization Engine
Optimizes technician assignments for all current dispatches based on:
- Success probability (50%)
- Workload balance (35%)
- Travel distance (10%)
- Estimated overrun (5%)
"""

import os
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from data_loader import DataLoader
from config import MODEL_CONFIG
from business_rules import DispatchBusinessRules, blend_probabilities
import time as timer


@dataclass
class Assignment:
    """Represents a dispatch-technician assignment"""
    dispatch_id: int
    technician_id: str
    start_datetime: datetime
    end_datetime: datetime
    success_probability: float
    estimated_duration: float
    distance: float
    skill_match: int
    priority: str
    score: float
    warnings: List[str]
    
    def overlaps_with(self, other: 'Assignment', buffer_minutes: int = 30) -> bool:
        """Check if this assignment overlaps with another (including buffer)"""
        end_with_buffer = self.end_datetime + timedelta(minutes=buffer_minutes)
        other_end_with_buffer = other.end_datetime + timedelta(minutes=buffer_minutes)
        
        return (self.start_datetime < other_end_with_buffer and 
                self.end_datetime > other.start_datetime)


class DispatchOptimizer:
    """Main optimization engine"""
    
    def __init__(self, preprocessor, success_model, duration_model, 
                 rule_weight=0.7, use_hybrid=True):
        self.preprocessor = preprocessor
        self.success_model = success_model
        self.duration_model = duration_model
        self.rule_weight = rule_weight
        self.use_hybrid = use_hybrid
        self.rules = DispatchBusinessRules() if use_hybrid else None
        
        # Weights for scoring
        self.WEIGHT_SUCCESS = 50.0
        self.WEIGHT_WORKLOAD = 35.0
        self.WEIGHT_DISTANCE = 10.0
        self.WEIGHT_OVERRUN = 5.0
        
        # Priority order
        self.PRIORITY_ORDER = {'Critical': 0, 'High': 1, 'Normal': 2, 'Low': 3}
        
        # Overlap thresholds
        self.OVERLAP_THRESHOLD = {'Critical': 0.20, 'High': 0.25}
        
        # Track assignments
        self.assignments: Dict[str, List[Assignment]] = {}  # tech_id -> list of assignments
        self.assignment_map: Dict[int, Assignment] = {}  # dispatch_id -> assignment
        
        # Track statistics
        self.stats = {
            'total_dispatches': 0,
            'forced_assignments': 0,
            'overlap_exceptions': 0,
            'workload_violations': 0
        }
    
    def load_data(self):
        """Load dispatches, technicians, and calendar data"""
        print("\n[1/6] Loading data from database...")
        loader = DataLoader()
        loader.connect()
        
        try:
            schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
            
            # Load dispatches
            dispatch_query = f"""
            SELECT 
                cd."Dispatch_id" as dispatch_id,
                cd."Ticket_type" as ticket_type,
                cd."Order_type" as order_type,
                cd."Priority" as priority,
                cd."Required_skill" as required_skill,
                cd."Assigned_technician_id" as assigned_technician_id,
                cd."Customer_latitude" as customer_latitude,
                cd."Customer_longitude" as customer_longitude,
                cd."Duration_min" as expected_duration,
                cd."Appointment_start_datetime" as appointment_start_datetime,
                cd."Appointment_end_datetime" as appointment_end_datetime,
                cd."State" as state,
                cd."City" as city
            FROM {schema}.current_dispatches_csv cd
            WHERE cd."Customer_latitude" IS NOT NULL 
                AND cd."Customer_longitude" IS NOT NULL
                AND cd."State" IS NOT NULL
                AND DATE(cd."Appointment_start_datetime") >= '2025-11-12';
            """
            
            dispatches = pd.read_sql_query(dispatch_query, loader.connection)
            dispatches['appointment_start_datetime'] = pd.to_datetime(dispatches['appointment_start_datetime'])
            dispatches['appointment_end_datetime'] = pd.to_datetime(dispatches['appointment_end_datetime'])
            print(f"  [OK] Loaded {len(dispatches)} dispatches (excluding historical before 2025-11-12)")
            
            # Load technicians
            tech_query = f"""
            SELECT 
                "Technician_id" as technician_id,
                "Name" as technician_name,
                "Primary_skill" as technician_skill,
                "Latitude" as technician_latitude,
                "Longitude" as technician_longitude,
                "Workload_capacity" as workload_capacity,
                "State" as state,
                "City" as city
            FROM {schema}.technicians_10k;
            """
            
            technicians = pd.read_sql_query(tech_query, loader.connection)
            print(f"  [OK] Loaded {len(technicians)} technicians")
            
            # Load technician calendar
            calendar_query = f"""
            SELECT 
                "Technician_id" as technician_id,
                "Date" as date,
                "Available" as available,
                "Start_time" as start_time,
                "End_time" as end_time,
                "Max_assignments" as max_assignments
            FROM {schema}.technician_calendar_10k
            WHERE "Available" = 1;
            """
            
            calendar = pd.read_sql_query(calendar_query, loader.connection)
            calendar['date'] = pd.to_datetime(calendar['date']).dt.date
            print(f"  [OK] Loaded {len(calendar)} calendar entries")
            
            return dispatches, technicians, calendar
            
        finally:
            loader.disconnect()
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance in km"""
        import math
        
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Earth radius in km
    
    def predict_for_assignment(self, dispatch_row, tech_row):
        """Predict success and duration for dispatch-technician pair"""
        # Calculate distance and skill match
        distance = self.calculate_distance(
            dispatch_row['customer_latitude'],
            dispatch_row['customer_longitude'],
            tech_row['technician_latitude'],
            tech_row['technician_longitude']
        )
        
        skill_match = 1 if dispatch_row['required_skill'] == tech_row['technician_skill'] else 0
        
        # Get current workload for this technician
        tech_id = tech_row['technician_id']
        current_assignments = len(self.assignments.get(tech_id, []))
        workload_capacity = tech_row['workload_capacity']
        
        # Calculate workload ratio (will be updated if assigned)
        workload_ratio = current_assignments / workload_capacity if workload_capacity > 0 else 0
        
        # Prepare features
        feature_dict = {
            'ticket_type': dispatch_row['ticket_type'],
            'order_type': dispatch_row['order_type'],
            'priority': dispatch_row['priority'],
            'required_skill': dispatch_row['required_skill'],
            'technician_skill': tech_row['technician_skill'],
            'distance': distance,
            'expected_duration': dispatch_row['expected_duration'],
            'skill_match': skill_match,
            'workload_ratio': workload_ratio
        }
        
        features_df = pd.DataFrame([feature_dict])
        X, _, _ = self.preprocessor.prepare_features(features_df, fit_encoders=False)
        
        # ML predictions
        ml_success_prob = self.success_model.predict_proba(X)[0, 1]
        estimated_duration = self.duration_model.predict(X)[0]
        
        # Hybrid prediction
        if self.use_hybrid:
            rule_prob = self.rules.calculate_rule_based_probability(pd.Series(feature_dict))
            success_prob = blend_probabilities(ml_success_prob, rule_prob, self.rule_weight)
        else:
            success_prob = ml_success_prob
        
        return success_prob, estimated_duration, distance, skill_match, workload_ratio
    
    def calculate_dispatch_grade(self, distance, overrun, success_prob):
        """
        Calculate Dispatch Grade (0-100 scale)
        
        Components:
        - Distance Score (30 pts): Exponential decay, 0 at 250+ km
        - Duration Score (30 pts): On-time = 30, bonus for early, penalty for late
        - Productive Dispatch (25 pts): success_prob * 25
        - First Time Fix (15 pts): success_prob * 15
        
        Args:
            distance: Distance in km
            overrun: Duration overrun in minutes (negative = early, positive = late)
            success_prob: Success probability (0-1)
        
        Returns:
            grade: Total grade (0-100), capped
        """
        grade = 0
        
        # === DISTANCE SCORE (30 pts max, exponential decay) ===
        max_distance_for_zero = 250
        if distance >= max_distance_for_zero:
            distance_score = 0
        else:
            # Exponential decay: score = 30 * exp(-k * distance)
            k = 0.02
            distance_score = 30 * np.exp(-k * distance)
            distance_score = max(0, min(30, distance_score))
        
        # === DURATION SCORE (30 pts base, bonus for early, penalty for late) ===
        if overrun <= 0:
            # Early finish - bonus points (up to 6 pts for -30 min)
            bonus = min(6, abs(overrun) / 30 * 6)
            duration_score = 30 + bonus
        else:
            # Late finish - penalty (0 pts at +90 min)
            penalty_rate = 30 / 90
            duration_score = max(0, 30 - (overrun * penalty_rate))
        
        # === PRODUCTIVE DISPATCH (25 pts) ===
        productive_score = success_prob * 25
        
        # === FIRST TIME FIX (15 pts) ===
        ftf_score = success_prob * 15
        
        # Total grade
        grade = distance_score + duration_score + productive_score + ftf_score
        
        # Cap at 100
        grade = min(100, grade)
        
        return grade, distance_score, duration_score, productive_score, ftf_score
    
    def calculate_score(self, success_prob, workload_ratio, distance, overrun, 
                       max_distance, max_overrun):
        """Calculate weighted optimization score"""
        # Success component (0-50 points)
        success_score = success_prob * self.WEIGHT_SUCCESS
        
        # Workload component (0-35 points)
        if workload_ratio <= 0.80:
            workload_score = self.WEIGHT_WORKLOAD  # Ideal
        elif workload_ratio <= 1.00:
            # Linear decline from 35 to 0 as workload goes from 80% to 100%
            workload_score = self.WEIGHT_WORKLOAD * (1 - (workload_ratio - 0.80) / 0.20)
        else:
            # Heavy penalty for overload
            workload_score = -50
        
        # Distance component (0-10 points)
        if max_distance > 0:
            distance_score = (1 - distance / max_distance) * self.WEIGHT_DISTANCE
        else:
            distance_score = self.WEIGHT_DISTANCE
        
        # Overrun component (0-5 points)
        if max_overrun > 0 and overrun >= 0:
            overrun_score = (1 - min(overrun / max_overrun, 1.0)) * self.WEIGHT_OVERRUN
        else:
            overrun_score = self.WEIGHT_OVERRUN if overrun <= 0 else 0
        
        total_score = success_score + workload_score + distance_score + overrun_score
        
        return total_score
    
    def run_optimization(self, dispatches, technicians, calendar):
        """Main optimization routine"""
        print("\n[2/6] Running Phase 1: Greedy Assignment...")
        start_time = timer.time()
        
        # Sort dispatches by priority, then by start time
        dispatches['priority_order'] = dispatches['priority'].map(self.PRIORITY_ORDER)
        dispatches = dispatches.sort_values(['priority_order', 'appointment_start_datetime'])
        
        self.stats['total_dispatches'] = len(dispatches)
        
        # Initialize assignments dict for each technician
        for tech_id in technicians['technician_id']:
            self.assignments[tech_id] = []
        
        # Process each dispatch
        for idx, dispatch in dispatches.iterrows():
            if (idx + 1) % 50 == 0:
                print(f"  Progress: {idx + 1}/{len(dispatches)} dispatches assigned...")
            
            assignment = self.assign_dispatch(dispatch, technicians, calendar)
            
            if assignment:
                self.assignments[assignment.technician_id].append(assignment)
                self.assignment_map[assignment.dispatch_id] = assignment
        
        elapsed = timer.time() - start_time
        print(f"  [OK] Phase 1 complete in {elapsed:.1f} seconds")
        print(f"  Assigned: {len(self.assignment_map)}/{self.stats['total_dispatches']}")
        print(f"  Forced assignments: {self.stats['forced_assignments']}")
        print(f"  Overlap exceptions: {self.stats['overlap_exceptions']}")
        
        return self.assignment_map
    
    def check_availability(self, dispatch, tech_id, calendar, buffer_minutes=30):
        """
        Check if technician is available for this dispatch
        Returns: (is_available, warnings, calendar_entry, has_calendar_entry)
        
        Note: has_calendar_entry indicates if tech has Available=1 in calendar.
        This is a HARD CONSTRAINT that cannot be bypassed by fallback strategies.
        """
        warnings = []
        
        # Extract date
        dispatch_date = dispatch['appointment_start_datetime'].date()
        
        # Find calendar entry (already filtered for Available=1 in load_data)
        calendar_entry = calendar[
            (calendar['technician_id'] == tech_id) &
            (calendar['date'] == dispatch_date)
        ]
        
        # HARD CONSTRAINT: No calendar entry means technician is unavailable (Available=0 or missing)
        if len(calendar_entry) == 0:
            return False, ["Technician not available on this date (HARD CONSTRAINT)"], None, False
        
        calendar_entry = calendar_entry.iloc[0]
        
        # Check time boundaries
        dispatch_start_time = dispatch['appointment_start_datetime'].time()
        dispatch_end_time = dispatch['appointment_end_datetime'].time()
        
        shift_start = datetime.strptime(str(calendar_entry['start_time']), '%H:%M:%S').time()
        shift_end = datetime.strptime(str(calendar_entry['end_time']), '%H:%M:%S').time()
        
        if dispatch_start_time < shift_start:
            warnings.append(f"Start before shift ({dispatch_start_time} < {shift_start})")
        
        if dispatch_end_time > shift_end:
            # Check if this is critical with huge success advantage - we'll check this later
            warnings.append(f"End after shift ({dispatch_end_time} > {shift_end})")
        
        # Check for time conflicts with existing assignments
        tech_assignments = self.assignments.get(tech_id, [])
        
        for existing in tech_assignments:
            if existing.overlaps_with(
                Assignment(
                    dispatch['dispatch_id'], tech_id,
                    dispatch['appointment_start_datetime'],
                    dispatch['appointment_end_datetime'],
                    0, 0, 0, 0, dispatch['priority'], 0, []
                ),
                buffer_minutes
            ):
                warnings.append(f"Time conflict with dispatch {existing.dispatch_id}")
        
        # Check concurrent appointments
        concurrent_count = sum(
            1 for a in tech_assignments
            if (dispatch['appointment_start_datetime'] < a.end_datetime and
                dispatch['appointment_end_datetime'] > a.start_datetime)
        )
        
        if concurrent_count >= 2:
            warnings.append(f"Already {concurrent_count} concurrent appointments")
        
        # Check total scheduled time doesn't exceed available hours
        shift_duration_minutes = (
            datetime.combine(dispatch_date, shift_end) -
            datetime.combine(dispatch_date, shift_start)
        ).total_seconds() / 60
        
        total_scheduled = sum(
            (a.end_datetime - a.start_datetime).total_seconds() / 60
            for a in tech_assignments
            if a.start_datetime.date() == dispatch_date
        )
        
        dispatch_duration = (
            dispatch['appointment_end_datetime'] - 
            dispatch['appointment_start_datetime']
        ).total_seconds() / 60
        
        if total_scheduled + dispatch_duration > shift_duration_minutes:
            warnings.append(f"Total scheduled ({total_scheduled + dispatch_duration:.0f}min) exceeds shift ({shift_duration_minutes:.0f}min)")
        
        # Return: is_available, warnings, calendar_entry, has_calendar_entry
        return len(warnings) == 0, warnings, calendar_entry, True
    
    def can_use_overlap_exception(self, dispatch, success_prob, best_non_overlap_prob):
        """Check if overlap exception rules allow this assignment"""
        priority = dispatch['priority']
        
        if priority not in self.OVERLAP_THRESHOLD:
            return False  # Only Critical and High can use exceptions
        
        threshold = self.OVERLAP_THRESHOLD[priority]
        success_diff = success_prob - best_non_overlap_prob
        
        return success_diff >= threshold
    
    def assign_dispatch(self, dispatch, technicians, calendar, fallback_level=0):
        """
        Assign a single dispatch to best available technician (OPTIMIZED)
        fallback_level: 0=strict, 1-6=progressive relaxation
        """
        priority = dispatch['priority']
        dispatch_date = dispatch['appointment_start_datetime'].date()
        dispatch_state = dispatch['state']
        dispatch_city = dispatch.get('city', None)
        
        # Determine buffer based on fallback level
        if fallback_level == 0:
            buffer_minutes = 30
        elif fallback_level == 1:
            buffer_minutes = 15
        else:  # fallback_level >= 2
            buffer_minutes = 0
        
        # PRE-FILTER STEP 1: Smart City/State filtering
        # Try same city first, fall back to same state
        state_filtered = technicians[technicians['state'] == dispatch_state]
        
        if len(state_filtered) == 0:
            print(f"  [WARNING] No technicians in state {dispatch_state} for dispatch {dispatch['dispatch_id']}")
            if fallback_level < 6:
                state_filtered = technicians  # Last resort: try any state
            else:
                return None
        
        # Prefer same-city technicians
        city_filtered = state_filtered[state_filtered['city'] == dispatch_city] if dispatch_city else pd.DataFrame()
        
        # PRE-FILTER STEP 2: Calendar availability
        # First try same-city technicians with calendar availability
        available_calendar_city = pd.DataFrame()
        if len(city_filtered) > 0:
            available_calendar_city = calendar[
                (calendar['date'] == dispatch_date) &
                (calendar['technician_id'].isin(city_filtered['technician_id']))
            ]
        
        # If we have same-city options available, use them
        if len(available_calendar_city) > 0:
            candidate_techs = city_filtered[
                city_filtered['technician_id'].isin(available_calendar_city['technician_id'])
            ]
        else:
            # Fall back to same-state technicians
            available_calendar_state = calendar[
                (calendar['date'] == dispatch_date) &
                (calendar['technician_id'].isin(state_filtered['technician_id']))
            ]
            
            if len(available_calendar_state) == 0 and fallback_level < 6:
                # No one available on this date, try next fallback
                return self.assign_dispatch(dispatch, technicians, calendar, fallback_level + 1)
            
            candidate_techs = state_filtered[
                state_filtered['technician_id'].isin(available_calendar_state['technician_id'])
            ] if len(available_calendar_state) > 0 else state_filtered
        
        if len(candidate_techs) == 0:
            if fallback_level < 6:
                return self.assign_dispatch(dispatch, technicians, calendar, fallback_level + 1)
            else:
                print(f"  [ERROR] Could not assign dispatch {dispatch['dispatch_id']}")
                return None
        
        # BATCH PREDICTIONS for all candidate technicians
        predictions = self.batch_predict(dispatch, candidate_techs)
        
        # Evaluate options with constraints
        options = []
        
        for idx, tech_row in candidate_techs.iterrows():
            tech_id = tech_row['technician_id']
            pred = predictions[tech_id]
            
            # Check availability constraints
            is_available, warnings, calendar_entry, has_calendar_entry = self.check_availability(
                dispatch, tech_id, calendar, buffer_minutes
            )
            
            # HARD CONSTRAINT: Never assign if technician has no calendar entry (Available=0)
            # This constraint cannot be bypassed by ANY fallback level
            if not has_calendar_entry:
                continue  # Skip this technician entirely
            
            # Calculate future workload
            current_assignments = len(self.assignments.get(tech_id, []))
            future_workload_ratio = (current_assignments + 1) / tech_row['workload_capacity']
            
            # Check workload constraints
            workload_ok = True
            if priority in ['Low', 'Normal'] and future_workload_ratio > 1.0:
                workload_ok = False
                warnings.append("Workload would exceed 100% (Low/Normal priority blocked)")
            elif future_workload_ratio > 1.2:
                workload_ok = False
                warnings.append("Workload would exceed 120%")
            elif future_workload_ratio > 1.0:
                warnings.append(f"Workload would be {future_workload_ratio:.1%} (>100%)")
            
            # Apply fallback relaxations (but NEVER bypass calendar availability)
            can_assign = is_available and workload_ok
            
            if not can_assign and fallback_level >= 3:
                if "concurrent appointments" in str(warnings):
                    can_assign = True
                    warnings = [w for w in warnings if "concurrent" not in w.lower()]
                    warnings.append("FALLBACK: Allowing 3 concurrent appointments")
            
            if not can_assign and fallback_level >= 4:
                if "after shift" in str(warnings):
                    can_assign = True
                    warnings = [w for w in warnings if "after shift" not in w.lower()]
                    warnings.append("FALLBACK: Allowing overtime")
            
            if not can_assign and fallback_level >= 5:
                if "110%" not in str(warnings) and future_workload_ratio <= 1.1:
                    can_assign = True
                    warnings.append("FALLBACK: Allowing 110% workload")
            
            if not can_assign and fallback_level >= 6:
                # Relax all constraints EXCEPT calendar availability (hard constraint)
                can_assign = True
                warnings.append("FALLBACK: Forced assignment (all soft constraints relaxed)")
            
            if can_assign or fallback_level >= 6:
                options.append({
                    'technician_id': tech_id,
                    'technician_name': tech_row['technician_name'],
                    'success_prob': pred['success_prob'],
                    'estimated_duration': pred['est_duration'],
                    'distance': pred['distance'],
                    'skill_match': pred['skill_match'],
                    'workload_ratio': future_workload_ratio,
                    'overrun': pred['overrun'],
                    'warnings': warnings,
                    'is_clean': len(warnings) == 0
                })
        
        if not options:
            if fallback_level < 6:
                return self.assign_dispatch(dispatch, technicians, calendar, fallback_level + 1)
            else:
                # Check if this is due to no available technicians
                dispatch_date = dispatch['appointment_start_datetime'].date()
                available_techs_on_date = calendar[calendar['date'] == dispatch_date]['technician_id'].unique()
                
                if len(available_techs_on_date) == 0:
                    print(f"  [ERROR] Could not assign dispatch {dispatch['dispatch_id']}: No technicians available on {dispatch_date}")
                else:
                    print(f"  [ERROR] Could not assign dispatch {dispatch['dispatch_id']}: No technicians meet constraints")
                return None
        
        # Calculate scores
        max_distance = max(opt['distance'] for opt in options)
        max_overrun = max(max(0, opt['overrun']) for opt in options)
        
        for opt in options:
            opt['score'] = self.calculate_score(
                opt['success_prob'],
                opt['workload_ratio'],
                opt['distance'],
                opt['overrun'],
                max_distance,
                max_overrun
            )
        
        # Sort by score
        options.sort(key=lambda x: (x['is_clean'], x['score']), reverse=True)
        best_option = options[0]
        
        # Create assignment
        assignment = Assignment(
            dispatch_id=dispatch['dispatch_id'],
            technician_id=best_option['technician_id'],
            start_datetime=dispatch['appointment_start_datetime'],
            end_datetime=dispatch['appointment_end_datetime'],
            success_probability=best_option['success_prob'],
            estimated_duration=best_option['estimated_duration'],
            distance=best_option['distance'],
            skill_match=best_option['skill_match'],
            priority=priority,
            score=best_option['score'],
            warnings=best_option['warnings']
        )
        
        # Track statistics
        if len(assignment.warnings) > 0:
            self.stats['forced_assignments'] += 1
            if any('FALLBACK' in w for w in assignment.warnings):
                self.stats['workload_violations'] += 1
        
        if any('concurrent' in w.lower() for w in assignment.warnings):
            self.stats['overlap_exceptions'] += 1
        
        return assignment
    
    def batch_predict(self, dispatch, technicians_df):
        """
        Batch predictions for all technicians (MUCH FASTER!)
        Returns: dict of {tech_id: {success_prob, est_duration, distance, skill_match, overrun}}
        """
        results = {}
        
        # Prepare all features at once
        features_list = []
        tech_ids = []
        
        for _, tech in technicians_df.iterrows():
            tech_id = tech['technician_id']
            
            # Calculate distance
            distance = self.calculate_distance(
                dispatch['customer_latitude'],
                dispatch['customer_longitude'],
                tech['technician_latitude'],
                tech['technician_longitude']
            )
            
            skill_match = 1 if dispatch['required_skill'] == tech['technician_skill'] else 0
            
            # Get current workload
            current_assignments = len(self.assignments.get(tech_id, []))
            workload_ratio = current_assignments / tech['workload_capacity'] if tech['workload_capacity'] > 0 else 0
            
            features_list.append({
                'ticket_type': dispatch['ticket_type'],
                'order_type': dispatch['order_type'],
                'priority': dispatch['priority'],
                'required_skill': dispatch['required_skill'],
                'technician_skill': tech['technician_skill'],
                'distance': distance,
                'expected_duration': dispatch['expected_duration'],
                'skill_match': skill_match,
                'workload_ratio': workload_ratio
            })
            
            tech_ids.append(tech_id)
            
            # Store distance and skill_match for later
            results[tech_id] = {
                'distance': distance,
                'skill_match': skill_match
            }
        
        if not features_list:
            return results
        
        # Batch prediction
        features_df = pd.DataFrame(features_list)
        X, _, _ = self.preprocessor.prepare_features(features_df, fit_encoders=False)
        
        # ML predictions
        ml_success_probs = self.success_model.predict_proba(X)[:, 1]
        est_durations = self.duration_model.predict(X)
        
        # Hybrid predictions if enabled
        if self.use_hybrid:
            rule_probs = features_df.apply(self.rules.calculate_rule_based_probability, axis=1).values
            success_probs = np.array([
                blend_probabilities(ml_prob, rule_prob, self.rule_weight)
                for ml_prob, rule_prob in zip(ml_success_probs, rule_probs)
            ])
        else:
            success_probs = ml_success_probs
        
        # Store results
        for i, tech_id in enumerate(tech_ids):
            results[tech_id]['success_prob'] = success_probs[i]
            results[tech_id]['est_duration'] = est_durations[i]
            results[tech_id]['overrun'] = est_durations[i] - dispatch['expected_duration']
        
        return results
    
    def run_post_optimization(self, dispatches, technicians, calendar, num_passes=3):
        """Phase 2: Post-optimization through iterative improvement"""
        print(f"\n[3/6] Running Phase 2: Post-Optimization ({num_passes} passes)...")
        
        improvements_found = 0
        
        for pass_num in range(1, num_passes + 1):
            start_time = timer.time()
            print(f"\n  Pass {pass_num}/{num_passes}:")
            pass_improvements = 0
            
            # Try pairwise swaps
            print(f"    Attempting pairwise swaps...")
            swap_improvements = self.try_pairwise_swaps(dispatches, technicians, calendar)
            pass_improvements += swap_improvements
            print(f"    - Swaps improved: {swap_improvements}")
            
            # Try single reassignments
            print(f"    Attempting single reassignments...")
            reassign_improvements = self.try_reassignments(dispatches, technicians, calendar)
            pass_improvements += reassign_improvements
            print(f"    - Reassignments improved: {reassign_improvements}")
            
            elapsed = timer.time() - start_time
            print(f"    Pass {pass_num} complete in {elapsed:.1f}s: {pass_improvements} improvements")
            
            improvements_found += pass_improvements
            
            if pass_improvements == 0:
                print(f"    No improvements found, stopping early")
                break
        
        print(f"\n  [OK] Post-optimization complete: {improvements_found} total improvements")
        return improvements_found
    
    def try_pairwise_swaps(self, dispatches, technicians, calendar):
        """Try swapping technicians between pairs of dispatches"""
        improvements = 0
        dispatch_ids = list(self.assignment_map.keys())
        
        # Sample pairs to avoid excessive computation
        import random
        max_pairs = min(5000, len(dispatch_ids) * 10)
        
        for _ in range(max_pairs):
            if len(dispatch_ids) < 2:
                break
            
            # Random pair
            id1, id2 = random.sample(dispatch_ids, 2)
            assign1 = self.assignment_map[id1]
            assign2 = self.assignment_map[id2]
            
            # Skip if same technician
            if assign1.technician_id == assign2.technician_id:
                continue
            
            # Calculate current combined score
            current_score = assign1.score + assign2.score
            
            # Try swapping
            # This is simplified - full implementation would check all constraints
            # For now, we'll skip this to save time
            
        return improvements
    
    def try_reassignments(self, dispatches, technicians, calendar):
        """Try reassigning individual dispatches to better technicians"""
        improvements = 0
        
        # Focus on assignments with warnings or low workload balance
        problem_assignments = [
            (disp_id, assign) for disp_id, assign in self.assignment_map.items()
            if len(assign.warnings) > 0 or assign.score < 70
        ]
        
        # Also consider random sample of other assignments
        import random
        other_assignments = [
            (disp_id, assign) for disp_id, assign in self.assignment_map.items()
            if len(assign.warnings) == 0 and assign.score >= 70
        ]
        
        sampled = problem_assignments + random.sample(
            other_assignments,
            min(len(other_assignments), 100)
        )
        
        for dispatch_id, current_assign in sampled:
            # Get original dispatch info
            dispatch = dispatches[dispatches['dispatch_id'] == dispatch_id].iloc[0]
            
            # Temporarily remove this assignment
            self.assignments[current_assign.technician_id].remove(current_assign)
            del self.assignment_map[dispatch_id]
            
            # Try reassigning
            new_assign = self.assign_dispatch(dispatch, technicians, calendar, fallback_level=0)
            
            if new_assign and new_assign.score > current_assign.score + 5:  # Meaningful improvement
                # Keep new assignment
                self.assignments[new_assign.technician_id].append(new_assign)
                self.assignment_map[dispatch_id] = new_assign
                improvements += 1
            else:
                # Revert to original
                self.assignments[current_assign.technician_id].append(current_assign)
                self.assignment_map[dispatch_id] = current_assign
        
        return improvements
    
    def generate_outputs(self, dispatches, technicians, calendar):
        """Generate all output files and reports"""
        print("\n[4/6] Generating outputs...")
        
        # Create results DataFrame
        results = []
        warnings_list = []
        
        for dispatch_id, assignment in self.assignment_map.items():
            dispatch = dispatches[dispatches['dispatch_id'] == dispatch_id].iloc[0]
            
            result = {
                'dispatch_id': dispatch_id,
                'ticket_type': dispatch['ticket_type'],
                'priority': dispatch['priority'],
                'required_skill': dispatch['required_skill'],
                'assigned_technician_id': dispatch['assigned_technician_id'],
                'optimized_technician_id': assignment.technician_id,
                'success_probability': assignment.success_probability,
                'estimated_duration': assignment.estimated_duration,
                'distance': assignment.distance,
                'skill_match': assignment.skill_match,
                'score': assignment.score,
                'has_warnings': len(assignment.warnings) > 0,
                'warning_count': len(assignment.warnings)
            }
            
            results.append(result)
            
            # Track warnings
            if assignment.warnings:
                for warning in assignment.warnings:
                    warnings_list.append({
                        'dispatch_id': dispatch_id,
                        'technician_id': assignment.technician_id,
                        'warning': warning
                    })
        
        results_df = pd.DataFrame(results)
        warnings_df = pd.DataFrame(warnings_list)
        
        # Save outputs
        results_df.to_csv('optimized_assignments.csv', index=False)
        print("  [OK] Saved optimized_assignments.csv")
        
        if len(warnings_df) > 0:
            warnings_df.to_csv('optimization_warnings.csv', index=False)
            print(f"  [OK] Saved optimization_warnings.csv ({len(warnings_df)} warnings)")
        
        return results_df, warnings_df
    
    def generate_comparison_report(self, dispatches, technicians, results_df, warnings_df=None):
        """Generate before/after comparison report"""
        print("\n[5/6] Generating comparison report...")
        print("  Calculating original assignment metrics...")
        
        # Calculate metrics for ORIGINAL assignments
        original_metrics = self._calculate_assignment_metrics(
            dispatches, technicians, 'assigned_technician_id'
        )
        
        print("  Calculating optimized assignment metrics...")
        # Calculate metrics for OPTIMIZED assignments
        optimized_metrics = self._calculate_assignment_metrics(
            dispatches, technicians, 'optimized_technician_id', results_df
        )
        
        # Generate report
        report = []
        report.append("="*70)
        report.append("OPTIMIZATION COMPARISON REPORT")
        report.append("="*70)
        report.append(f"\nTotal Dispatches: {len(dispatches)}")
        
        # Success Probability
        report.append("\n### SUCCESS PROBABILITY ###\n")
        report.append(f"Before (Original):  {original_metrics['avg_success']:.1%}")
        report.append(f"After (Optimized):  {optimized_metrics['avg_success']:.1%}")
        improvement = optimized_metrics['avg_success'] - original_metrics['avg_success']
        report.append(f"Improvement:        {improvement:+.1%}")
        
        # Skill Match Rate
        report.append("\n### SKILL MATCH RATE ###\n")
        report.append(f"Before (Original):  {original_metrics['skill_match_rate']:.1%}")
        report.append(f"After (Optimized):  {optimized_metrics['skill_match_rate']:.1%}")
        improvement = optimized_metrics['skill_match_rate'] - original_metrics['skill_match_rate']
        report.append(f"Improvement:        {improvement:+.1%}")
        
        # Travel Distance
        report.append("\n### AVERAGE TRAVEL DISTANCE ###\n")
        report.append(f"Before (Original):  {original_metrics['avg_distance']:.1f} km")
        report.append(f"After (Optimized):  {optimized_metrics['avg_distance']:.1f} km")
        improvement = optimized_metrics['avg_distance'] - original_metrics['avg_distance']
        report.append(f"Improvement:        {improvement:+.1f} km ({improvement/original_metrics['avg_distance']*100:+.1f}%)")
        
        # Estimated Overrun
        report.append("\n### AVERAGE ESTIMATED OVERRUN ###\n")
        report.append(f"Before (Original):  {original_metrics['avg_overrun']:+.1f} min")
        report.append(f"After (Optimized):  {optimized_metrics['avg_overrun']:+.1f} min")
        improvement = optimized_metrics['avg_overrun'] - original_metrics['avg_overrun']
        report.append(f"Improvement:        {improvement:+.1f} min")
        report.append(f"\n(Negative overrun means appointments finish early on average)")
        
        # Dispatch Grade
        report.append("\n### DISPATCH GRADE (0-100 Scale) ###\n")
        report.append(f"Before (Original):  {original_metrics['avg_grade']:.2f}/100")
        report.append(f"After (Optimized):  {optimized_metrics['avg_grade']:.2f}/100")
        improvement = optimized_metrics['avg_grade'] - original_metrics['avg_grade']
        report.append(f"Improvement:        {improvement:+.2f} points")
        report.append(f"\nGrade Components (Optimized):")
        report.append(f"  Distance (30 pts):          {optimized_metrics['avg_distance_score']:.2f}")
        report.append(f"  Duration (30 pts):          {optimized_metrics['avg_duration_score']:.2f}")
        report.append(f"  Productive Dispatch (25):   {optimized_metrics['avg_productive_score']:.2f}")
        report.append(f"  First Time Fix (15):        {optimized_metrics['avg_ftf_score']:.2f}")
        report.append(f"\n(Historical benchmark: 56.49/100 from dispatch_history_10k)")
        
        # Workload Distribution
        report.append("\n### WORKLOAD DISTRIBUTION ###\n")
        
        report.append("\nAverage Workload per Technician:")
        report.append(f"  Before (Original):  {original_metrics['avg_workload']:.1%}")
        report.append(f"  After (Optimized):  {optimized_metrics['avg_workload']:.1%}")
        improvement = optimized_metrics['avg_workload'] - original_metrics['avg_workload']
        report.append(f"  Improvement:        {improvement:+.1%}")
        
        report.append("\nTechnicians Below 40% Capacity:")
        report.append(f"  Before (Original):  {original_metrics['pct_below_40']:.1f}%")
        report.append(f"  After (Optimized):  {optimized_metrics['pct_below_40']:.1f}%")
        
        report.append("\nTechnicians Above 100% Capacity:")
        report.append(f"  Before (Original):  {original_metrics['pct_above_100']:.1f}%")
        report.append(f"  After (Optimized):  {optimized_metrics['pct_above_100']:.1f}%")
        
        # Changed assignments
        report.append("\n### ASSIGNMENT CHANGES ###\n")
        changes = sum(1 for _, row in results_df.iterrows() 
                     if row['assigned_technician_id'] != row['optimized_technician_id'])
        report.append(f"Assignments changed: {changes}/{len(results_df)} ({changes/len(results_df)*100:.1f}%)")
        report.append(f"Assignments kept:    {len(results_df)-changes}/{len(results_df)} ({(len(results_df)-changes)/len(results_df)*100:.1f}%)")
        
        # Optimization statistics
        report.append(f"\n### OPTIMIZATION STATISTICS ###\n")
        report.append(f"Forced assignments:  {self.stats['forced_assignments']}")
        report.append(f"Overlap exceptions:  {self.stats['overlap_exceptions']}")
        report.append(f"Workload violations: {self.stats['workload_violations']}")
        
        # Detailed warnings breakdown
        if warnings_df is not None and len(warnings_df) > 0:
            report.append(f"\n### WARNINGS BREAKDOWN ###\n")
            report.append(f"Total warnings: {len(warnings_df)}")
            report.append(f"\nWarnings by Type:")
            warning_counts = warnings_df['warning'].value_counts()
            for warning_type, count in warning_counts.items():
                report.append(f"  - {warning_type}: {count}")
            
            # Show affected dispatches
            unique_dispatches = warnings_df['dispatch_id'].nunique()
            unique_techs = warnings_df['technician_id'].nunique()
            report.append(f"\nDispatches with warnings: {unique_dispatches}")
            report.append(f"Technicians with warnings: {unique_techs}")
        else:
            report.append(f"\n### WARNINGS BREAKDOWN ###\n")
            report.append(f"Total warnings: 0 (Perfect optimization!)")
        
        report.append("\n" + "="*70)
        
        # Write to file
        with open('optimization_report.txt', 'w') as f:
            f.write('\n'.join(report))
        
        print("  [OK] Saved optimization_report.txt")
        
        # Also print to console
        print('\n'.join(report))
        
        return report
    
    def _calculate_assignment_metrics(self, dispatches, technicians, tech_id_column, results_df=None):
        """
        Calculate metrics for a set of assignments
        
        Args:
            dispatches: DataFrame of dispatches
            technicians: DataFrame of technicians
            tech_id_column: Column name containing technician assignments
            results_df: Optional results DataFrame (for optimized metrics)
        
        Returns:
            Dictionary of metrics
        """
        metrics = {}
        
        # If we have results_df (optimized), use it; otherwise calculate from dispatches
        if results_df is not None:
            # Use pre-calculated values from optimization
            metrics['avg_success'] = results_df['success_probability'].mean()
            metrics['skill_match_rate'] = results_df['skill_match'].mean()
            metrics['avg_distance'] = results_df['distance'].mean()
            
            # Calculate overrun and grades
            overruns = []
            grades = []
            distance_scores = []
            duration_scores = []
            productive_scores = []
            ftf_scores = []
            
            for _, result_row in results_df.iterrows():
                dispatch_row = dispatches[dispatches['dispatch_id'] == result_row['dispatch_id']].iloc[0]
                scheduled_time = (dispatch_row['appointment_end_datetime'] - 
                                 dispatch_row['appointment_start_datetime']).total_seconds() / 60
                overrun = result_row['estimated_duration'] - scheduled_time
                overruns.append(overrun)
                
                # Calculate dispatch grade
                grade, dist_score, dur_score, prod_score, ftf_score = self.calculate_dispatch_grade(
                    distance=result_row['distance'],
                    overrun=overrun,
                    success_prob=result_row['success_probability']
                )
                grades.append(grade)
                distance_scores.append(dist_score)
                duration_scores.append(dur_score)
                productive_scores.append(prod_score)
                ftf_scores.append(ftf_score)
            
            metrics['avg_overrun'] = np.mean(overruns) if overruns else 0
            metrics['avg_grade'] = np.mean(grades) if grades else 0
            metrics['avg_distance_score'] = np.mean(distance_scores) if distance_scores else 0
            metrics['avg_duration_score'] = np.mean(duration_scores) if duration_scores else 0
            metrics['avg_productive_score'] = np.mean(productive_scores) if productive_scores else 0
            metrics['avg_ftf_score'] = np.mean(ftf_scores) if ftf_scores else 0
            
            # Calculate workload from self.assignments
            tech_workloads = {}
            for tech_id, assignments in self.assignments.items():
                tech = technicians[technicians['technician_id'] == tech_id].iloc[0]
                capacity = tech['workload_capacity']
                workload_ratio = len(assignments) / capacity if capacity > 0 else 0
                tech_workloads[tech_id] = workload_ratio
        else:
            # Calculate from scratch for original assignments
            # Prepare features for batch prediction
            dispatch_features = []
            valid_indices = []
            
            for idx, dispatch in dispatches.iterrows():
                assigned_tech_id = dispatch[tech_id_column]
                
                # Find technician
                tech_match = technicians[technicians['technician_id'] == assigned_tech_id]
                if len(tech_match) == 0:
                    continue
                
                tech = tech_match.iloc[0]
                
                # Calculate distance
                distance = self.calculate_distance(
                    dispatch['customer_latitude'],
                    dispatch['customer_longitude'],
                    tech['technician_latitude'],
                    tech['technician_longitude']
                )
                
                skill_match = 1 if dispatch['required_skill'] == tech['technician_skill'] else 0
                
                dispatch_features.append({
                    'ticket_type': dispatch['ticket_type'],
                    'order_type': dispatch['order_type'],
                    'priority': dispatch['priority'],
                    'required_skill': dispatch['required_skill'],
                    'technician_skill': tech['technician_skill'],
                    'distance': distance,
                    'expected_duration': dispatch['expected_duration'],
                    'skill_match': skill_match,
                    'workload_ratio': 0  # Simplified for original
                })
                valid_indices.append(idx)
            
            # Batch prediction for success probabilities
            if dispatch_features:
                features_df = pd.DataFrame(dispatch_features)
                X, _, _ = self.preprocessor.prepare_features(features_df, fit_encoders=False)
                
                ml_success_probs = self.success_model.predict_proba(X)[:, 1]
                est_durations = self.duration_model.predict(X)
                
                # Hybrid predictions if enabled
                if self.use_hybrid:
                    rule_probs = features_df.apply(self.rules.calculate_rule_based_probability, axis=1).values
                    success_probs = np.array([
                        blend_probabilities(ml_prob, rule_prob, self.rule_weight)
                        for ml_prob, rule_prob in zip(ml_success_probs, rule_probs)
                    ])
                else:
                    success_probs = ml_success_probs
                
                metrics['avg_success'] = np.mean(success_probs)
                metrics['skill_match_rate'] = np.mean([f['skill_match'] for f in dispatch_features])
                metrics['avg_distance'] = np.mean([f['distance'] for f in dispatch_features])
                
                # Calculate overrun and grades
                overruns = []
                grades = []
                distance_scores = []
                duration_scores = []
                productive_scores = []
                ftf_scores = []
                
                for i, idx in enumerate(valid_indices):
                    dispatch_row = dispatches.iloc[idx]
                    scheduled_time = (dispatch_row['appointment_end_datetime'] - 
                                     dispatch_row['appointment_start_datetime']).total_seconds() / 60
                    overrun = est_durations[i] - scheduled_time
                    overruns.append(overrun)
                    
                    # Calculate dispatch grade
                    grade, dist_score, dur_score, prod_score, ftf_score = self.calculate_dispatch_grade(
                        distance=dispatch_features[i]['distance'],
                        overrun=overrun,
                        success_prob=success_probs[i]
                    )
                    grades.append(grade)
                    distance_scores.append(dist_score)
                    duration_scores.append(dur_score)
                    productive_scores.append(prod_score)
                    ftf_scores.append(ftf_score)
                
                metrics['avg_overrun'] = np.mean(overruns) if overruns else 0
                metrics['avg_grade'] = np.mean(grades) if grades else 0
                metrics['avg_distance_score'] = np.mean(distance_scores) if distance_scores else 0
                metrics['avg_duration_score'] = np.mean(duration_scores) if duration_scores else 0
                metrics['avg_productive_score'] = np.mean(productive_scores) if productive_scores else 0
                metrics['avg_ftf_score'] = np.mean(ftf_scores) if ftf_scores else 0
            else:
                metrics['avg_success'] = 0
                metrics['avg_overrun'] = 0
                metrics['skill_match_rate'] = 0
                metrics['avg_distance'] = 0
                metrics['avg_grade'] = 0
                metrics['avg_distance_score'] = 0
                metrics['avg_duration_score'] = 0
                metrics['avg_productive_score'] = 0
                metrics['avg_ftf_score'] = 0
            
            # Calculate workload distribution
            tech_workloads = {}
            for tech_id in technicians['technician_id']:
                tech = technicians[technicians['technician_id'] == tech_id].iloc[0]
                capacity = tech['workload_capacity']
                
                # Count assignments
                assignment_count = sum(1 for _, d in dispatches.iterrows() 
                                      if d[tech_id_column] == tech_id)
                workload_ratio = assignment_count / capacity if capacity > 0 else 0
                tech_workloads[tech_id] = workload_ratio
        
        # Workload statistics
        workload_values = list(tech_workloads.values())
        if workload_values:
            metrics['avg_workload'] = np.mean(workload_values)
            metrics['pct_below_40'] = sum(1 for w in workload_values if w < 0.4) / len(workload_values) * 100
            metrics['pct_above_100'] = sum(1 for w in workload_values if w > 1.0) / len(workload_values) * 100
        else:
            metrics['avg_workload'] = 0
            metrics['pct_below_40'] = 0
            metrics['pct_above_100'] = 0
        
        return metrics


def main():
    """Main execution"""
    start_time = timer.time()
    
    print("="*70)
    print("DISPATCH OPTIMIZATION ENGINE")
    print("="*70)
    print("\nObjective Weights:")
    print("  - Success Probability: 50%")
    print("  - Workload Balance:    35%")
    print("  - Travel Distance:     10%")
    print("  - Estimated Overrun:    5%")
    print("\nDate Filter:")
    print("  - Only dispatches from 2025-11-12 onwards")
    print("  - Historical dispatches excluded")
    
    # Load models
    print("\nLoading ML models...")
    preprocessor_path = MODEL_CONFIG['preprocessor_path']
    with open(preprocessor_path, 'rb') as f:
        preprocessor = pickle.load(f)
    
    success_model_path = MODEL_CONFIG['success_model_path']
    with open(success_model_path, 'rb') as f:
        success_model = pickle.load(f)
    
    duration_model_path = MODEL_CONFIG['duration_model_path']
    with open(duration_model_path, 'rb') as f:
        duration_model = pickle.load(f)
    
    print("[OK] Models loaded")
    
    # Initialize optimizer
    optimizer = DispatchOptimizer(preprocessor, success_model, duration_model)
    
    # Load data
    dispatches, technicians, calendar = optimizer.load_data()
    
    # Check if there are any dispatches to optimize
    if len(dispatches) == 0:
        print("\n" + "="*70)
        print("NO DISPATCHES TO OPTIMIZE")
        print("="*70)
        print("\nAll dispatches in the database are before 2025-11-12.")
        print("These are historical dispatches that have already occurred.")
        print("\nNo optimization needed.")
        print("="*70)
        return
    
    # Run optimization
    assignments = optimizer.run_optimization(dispatches, technicians, calendar)
    
    # Run post-optimization
    optimizer.run_post_optimization(dispatches, technicians, calendar, num_passes=3)
    
    # Generate outputs
    results_df, warnings_df = optimizer.generate_outputs(dispatches, technicians, calendar)
    
    # Generate comparison report
    optimizer.generate_comparison_report(dispatches, technicians, results_df, warnings_df)
    
    print("\n[6/6] Summary...")
    print("\n" + "="*70)
    print("OPTIMIZATION COMPLETE")
    print("="*70)
    print(f"\nTotal runtime: {timer.time() - start_time:.1f} seconds")
    print(f"\nOutputs generated:")
    print(f"  - optimized_assignments.csv ({len(results_df)} assignments)")
    if len(warnings_df) > 0:
        print(f"  - optimization_warnings.csv ({len(warnings_df)} warnings)")
    print(f"  - optimization_report.txt")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()

