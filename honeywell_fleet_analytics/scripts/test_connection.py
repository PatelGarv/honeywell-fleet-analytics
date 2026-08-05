import sys
sys.path.append('../scripts')
from snowflake_conn import query_to_df

# Test connection
df = query_to_df("SELECT CURRENT_USER(), CURRENT_DATABASE(), CURRENT_SCHEMA()")
print(df)
