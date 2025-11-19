# Database Configuration Changes

## What Changed

Updated the system to properly work with PostgreSQL schemas.

### Previous (Incorrect) Configuration:
```
Database: team_faiber_force  ❌ (was trying to connect to a database with this name)
Tables: dispatch_history_10k, technicians_10k
```

### New (Correct) Configuration:
```
Database: postgres  ✅
Schema: team_faiber_force  ✅
Tables: team_faiber_force.dispatch_history_10k  ✅
        team_faiber_force.technicians_10k  ✅
```

## Files Modified

### 1. `config.py`
- Changed `DB_NAME` default from `'team_faiber_force'` to `'postgres'`
- Added `'options'` parameter to set search_path to the schema
- Added support for `DB_SCHEMA` environment variable

**Before:**
```python
DB_CONFIG = {
    'database': os.getenv('DB_NAME', 'team_faiber_force'),
}
```

**After:**
```python
DB_CONFIG = {
    'database': os.getenv('DB_NAME', 'postgres'),
    'options': f"-c search_path={os.getenv('DB_SCHEMA', 'team_faiber_force')}"
}
```

### 2. `data_loader.py`
- Added `import os` at the top
- Updated all SQL queries to use schema-qualified table names
- `dispatch_history_10k` → `{schema}.dispatch_history_10k`
- `technicians_10k` → `{schema}.technicians_10k`

**Updated Methods:**
- `fetch_dispatch_data()` - Main data query with schema prefix
- `get_table_info()` - Added `table_schema` filter
- `get_sample_data()` - Added schema prefix to table names

**Example Query Change:**
```sql
-- Before
FROM dispatch_history_10k dh
LEFT JOIN technicians_10k t

-- After
FROM team_faiber_force.dispatch_history_10k dh
LEFT JOIN team_faiber_force.technicians_10k t
```

### 3. `env.example`
Added `DB_SCHEMA` variable:

**Before:**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=team_faiber_force
DB_USER=postgres
DB_PASSWORD=your_password_here
```

**After:**
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres              # Changed
DB_SCHEMA=team_faiber_force   # New
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 4. `test_connection.py`
- Added display of database and schema being used
- Shows configuration before running tests

**New Output:**
```
======================================================================
DATABASE CONNECTION TEST
======================================================================
Database: postgres
Schema: team_faiber_force
======================================================================
```

### 5. `DATABASE_SETUP.md` (New File)
- Comprehensive guide to database configuration
- Troubleshooting for common schema issues
- SQL queries to verify setup

## What You Need to Do

### Step 1: Update Your `.env` File

If you have an existing `.env` file, update it:

```bash
# Change this line
DB_NAME=team_faiber_force

# To these lines
DB_NAME=postgres
DB_SCHEMA=team_faiber_force
```

Or create a new `.env` from the updated template:

```bash
cp env.example .env
# Then edit .env with your credentials
```

### Step 2: Test the Connection

```bash
python test_connection.py
```

This will verify:
- ✓ Connection to `postgres` database works
- ✓ Schema `team_faiber_force` exists
- ✓ Tables exist in the schema
- ✓ Data can be queried with schema qualification

### Step 3: Retrain Models (if needed)

Once connection test passes:

```bash
python train_model.py
```

## Benefits of This Change

✅ **Correct PostgreSQL Usage**
- Follows PostgreSQL best practices
- Uses schema to organize tables
- Allows multiple schemas in same database

✅ **Explicit Table References**
- No ambiguity about which tables to use
- Works regardless of search_path settings
- Clear and maintainable SQL queries

✅ **Flexible Configuration**
- Can easily change schema name
- Can use different schemas for dev/prod
- Environment variable driven

## Troubleshooting

### If you get "schema does not exist"

```sql
-- Create the schema
CREATE SCHEMA team_faiber_force;
```

### If you get "relation does not exist"

Verify tables are in the correct schema:

```sql
-- List all tables in schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'team_faiber_force';
```

### If tables are in different schema

Move them to the correct schema:

```sql
ALTER TABLE old_schema.dispatch_history_10k 
  SET SCHEMA team_faiber_force;

ALTER TABLE old_schema.technicians_10k 
  SET SCHEMA team_faiber_force;
```

## Quick Reference

| Setting | Value |
|---------|-------|
| Database Name | `postgres` |
| Schema Name | `team_faiber_force` |
| Table 1 | `team_faiber_force.dispatch_history_10k` |
| Table 2 | `team_faiber_force.technicians_10k` |
| Environment Variable | `DB_SCHEMA=team_faiber_force` |

## Verification

Run these commands to verify your setup:

```bash
# 1. Test connection
python test_connection.py

# 2. If successful, train models
python train_model.py

# 3. Make a test prediction
python predict.py \
    --ticket-type "Installation" \
    --order-type "Standard" \
    --priority "High" \
    --required-skill "Fiber" \
    --technician-skill "Fiber" \
    --distance 25.5 \
    --expected-duration 60
```

---

**All changes are backward compatible through environment variables!** 

If your database structure is different, just update the `.env` file accordingly.

