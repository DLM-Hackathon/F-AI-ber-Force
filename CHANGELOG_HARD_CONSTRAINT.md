# Calendar Availability: Hard Constraint Implementation

## Summary
Updated the Dispatch Optimization Engine to enforce **calendar availability as a HARD CONSTRAINT** that can never be bypassed.

## Changes Made

### 1. **Modified `check_availability()` method** (`optimize_dispatches.py`)
- Now returns 4 values: `(is_available, warnings, calendar_entry, has_calendar_entry)`
- Added `has_calendar_entry` boolean to track if technician has `Available = 1` in calendar
- Added "(HARD CONSTRAINT)" tag to warning messages for unavailable technicians

### 2. **Modified `assign_dispatch()` method** (`optimize_dispatches.py`)
- Added early exit: `if not has_calendar_entry: continue`
- Technicians without calendar entries (Available=0) are now **skipped entirely**
- Even at fallback level 6 (forced assignment), calendar availability is respected
- Updated fallback level 6 message to clarify "all soft constraints relaxed"

### 3. **Enhanced error reporting** (`optimize_dispatches.py`)
- When a dispatch can't be assigned, system now reports:
  - "No technicians available on [date]" if calendar has no entries for that date
  - "No technicians meet constraints" if technicians exist but don't meet other constraints

### 4. **Updated documentation** (`OPTIMIZER_GUIDE.md`)
- Added new section: **"HARD CONSTRAINTS (Never Bypassed)"**
- Clearly documented that calendar availability is never relaxed
- Reorganized constraints into "Hard" vs "Soft" categories
- Updated fallback strategy section to clarify this constraint

## Technical Details

### What "Available = 1" Means
- Technicians have entries in `technician_calendar_10k` table
- Each entry has a date and `Available` field (1 = available, 0 = unavailable)
- During data loading, optimizer only loads calendar entries where `Available = 1`
- If a technician has no entry in the loaded calendar for a date, they cannot be assigned

### Constraint Hierarchy
1. **HARD**: Calendar Availability (`Available = 1`) - **NEVER BYPASSED**
2. **Soft**: Time buffers, concurrent appointments, overtime, workload limits - Can be relaxed through fallback

## Expected Impact

### Before This Change
- 75 dispatches (12.5%) were assigned to technicians marked as unavailable
- Warnings showed "Technician not available on this date"
- These assignments violated calendar constraints

### After This Change
- **Zero dispatches** will be assigned to technicians with `Available = 0`
- Some dispatches may become **unassignable** if no technicians are available
- System will report which dispatches couldn't be assigned and why

## Testing

To verify the changes:

```bash
# Run the optimizer
python optimize_dispatches.py

# Check for availability warnings
python -c "import pandas as pd; df = pd.read_csv('optimization_warnings.csv'); print(df[df['warning'].str.contains('HARD CONSTRAINT', case=False)])"

# Should return empty or very minimal results
```

## Fallback Behavior

If a dispatch date has **no available technicians**:
- System will try all 6 fallback levels
- All will fail (no candidates to evaluate)
- Dispatch will remain **unassigned**
- Error message: "No technicians available on [date]"

## Recommendations

If many dispatches become unassignable:
1. **Review technician calendar data** - ensure adequate coverage
2. **Add more technicians** - increase Available=1 entries for needed dates
3. **Reschedule dispatches** - move to dates with better availability
4. **Adjust shift schedules** - make more technicians available on high-demand dates

---

**Created**: November 19, 2025  
**Status**: ✅ Implemented and Documented



