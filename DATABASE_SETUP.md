# Database Setup Guide

## PostgreSQL Architecture

The system uses the following PostgreSQL structure:

```
Database: postgres
  └── Schema: team_faiber_force
      ├── Table: dispatch_history_10k
      └── Table: technicians_10k
```

## Configuration

### 1. Environment Variables

Create a `.env` file from the template:

```bash
cp env.example .env
```

### 2. Edit `.env` File

```bash
# Database Configuration
DB_HOST=localhost              # Your PostgreSQL host
DB_PORT=5432                   # PostgreSQL port (default: 5432)
DB_NAME=postgres               # Database name
DB_SCHEMA=team_faiber_force    # Schema containing the tables
DB_USER=postgres               # Your database username
DB_PASSWORD=your_password      # Your database password
```

### Key Points:

- **DB_NAME** should be `postgres` (the database name)
- **DB_SCHEMA** should be `team_faiber_force` (the schema containing your tables)
- The system automatically references tables as `team_faiber_force.dispatch_history_10k` and `team_faiber_force.technicians_10k`

## How It Works

### 1. Connection

The system connects to the database using `psycopg2` with these parameters:

```python
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'postgres',                    # Main database
    'user': 'postgres',
    'password': 'your_password',
    'options': '-c search_path=team_faiber_force'  # Schema search path
}
```

### 2. Schema Qualification

All SQL queries explicitly qualify table names with the schema:

```sql
SELECT * FROM team_faiber_force.dispatch_history_10k dh
LEFT JOIN team_faiber_force.technicians_10k t
  ON dh.assigned_technician_id = t.technician_id
```

This ensures:
- ✓ No ambiguity about which schema to use
- ✓ Works even if default search_path differs
- ✓ Explicit and clear table references

## Required Database Schema

### Table: team_faiber_force.dispatch_history_10k

Required columns:
- `id` - Dispatch identifier
- `ticket_type` - Type of service ticket
- `order_type` - Order classification
- `priority` - Priority level
- `required_skill` - Skill required for the job
- `assigned_technician_id` - ID of assigned technician
- `customer_latitude` - Customer location latitude
- `customer_longitude` - Customer location longitude
- `duration_min` - Expected duration in minutes
- `actual_duration` - Actual time taken in minutes
- `productive_dispatch` - Binary success indicator (0/1 or boolean)
- `dispatch_time` - When dispatch was created
- `completion_time` - When dispatch was completed

### Table: team_faiber_force.technicians_10k

Required columns:
- `technician_id` - Technician identifier
- `technician_skill` - Technician's primary skill
- `skill_level` - Skill proficiency level
- `latitude` - Technician's location latitude
- `longitude` - Technician's location longitude

## Testing Connection

Test your database configuration:

```bash
python test_connection.py
```

**Expected Output:**
```
======================================================================
DATABASE CONNECTION TEST
======================================================================
Database: postgres
Schema: team_faiber_force
======================================================================

[1/4] Testing database connection...
   ✓ Connection successful

[2/4] Checking if required tables exist...
   ✓ dispatch_history_10k table found
     Columns: id, ticket_type, order_type, priority, ...
   ✓ technicians_10k table found
     Columns: technician_id, technician_skill, latitude, ...

[3/4] Checking sample data...
   ✓ dispatch_history_10k has 3 sample records
   ✓ technicians_10k has 3 sample records

[4/4] Testing data join query...
   ✓ Successfully fetched XXXX joined records

======================================================================
✓ ALL TESTS PASSED - Database is ready!
======================================================================
```

## Common Issues and Solutions

### Issue 1: Schema Not Found

**Error:** `schema "team_faiber_force" does not exist`

**Solution:**
```sql
-- Check existing schemas
SELECT schema_name FROM information_schema.schemata;

-- Create schema if needed
CREATE SCHEMA team_faiber_force;

-- Grant permissions
GRANT USAGE ON SCHEMA team_faiber_force TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA team_faiber_force TO postgres;
```

### Issue 2: Tables Not Found

**Error:** `relation "team_faiber_force.dispatch_history_10k" does not exist`

**Solution:**
```sql
-- Check if tables exist in schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'team_faiber_force';

-- If tables are in different schema, move them
ALTER TABLE your_schema.dispatch_history_10k 
  SET SCHEMA team_faiber_force;

ALTER TABLE your_schema.technicians_10k 
  SET SCHEMA team_faiber_force;
```

### Issue 3: Permission Denied

**Error:** `permission denied for schema team_faiber_force`

**Solution:**
```sql
-- Grant schema access
GRANT USAGE ON SCHEMA team_faiber_force TO your_username;

-- Grant table access
GRANT SELECT ON ALL TABLES IN SCHEMA team_faiber_force TO your_username;

-- For future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA team_faiber_force
  GRANT SELECT ON TABLES TO your_username;
```

### Issue 4: Wrong Database

**Error:** `database "team_faiber_force" does not exist`

**Solution:**
Update your `.env` file:
```bash
# WRONG - trying to connect to database named "team_faiber_force"
DB_NAME=team_faiber_force

# CORRECT - connect to "postgres" database, use "team_faiber_force" schema
DB_NAME=postgres
DB_SCHEMA=team_faiber_force
```

## Verifying Schema Structure

Run these SQL queries to verify your setup:

```sql
-- 1. Check database
SELECT current_database();

-- 2. Check schema exists
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name = 'team_faiber_force';

-- 3. Check tables in schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'team_faiber_force';

-- 4. Check table columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'team_faiber_force' 
  AND table_name = 'dispatch_history_10k';

-- 5. Check data exists
SELECT COUNT(*) FROM team_faiber_force.dispatch_history_10k;
SELECT COUNT(*) FROM team_faiber_force.technicians_10k;
```

## Migration from Previous Setup

If you were using the old configuration (database = team_faiber_force), update your `.env`:

**Before:**
```bash
DB_NAME=team_faiber_force
# No DB_SCHEMA
```

**After:**
```bash
DB_NAME=postgres
DB_SCHEMA=team_faiber_force
```

Then restart your application or rerun training:

```bash
python train_model.py
```

## Alternative: Using psql

Connect directly using psql to verify:

```bash
# Connect to postgres database
psql -h localhost -U postgres -d postgres

# Once connected, list schemas
\dn

# Set schema search path
SET search_path TO team_faiber_force;

# List tables
\dt

# View table structure
\d dispatch_history_10k
\d technicians_10k

# Query data
SELECT COUNT(*) FROM dispatch_history_10k;
SELECT COUNT(*) FROM technicians_10k;
```

## Summary

✓ **Database**: `postgres`  
✓ **Schema**: `team_faiber_force`  
✓ **Tables**: `dispatch_history_10k`, `technicians_10k`  
✓ **Connection**: Uses schema-qualified table names  
✓ **Configuration**: Set in `.env` file  

This setup ensures proper schema isolation and explicit table references!

