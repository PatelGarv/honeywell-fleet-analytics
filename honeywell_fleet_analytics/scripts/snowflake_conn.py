import snowflake.connector
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

def get_snowflake_connection():
    conn = snowflake.connector.connect(
        user='GARV101',
        password=os.getenv("SNOWFLAKE_PASSWORD"),  
        account=os.getenv("SNOWFLAKE_ACCOUNT"),             
        warehouse='HONEYWELL_WH',
        database='HONEYWELL_FLEET',
        schema='DBT_GARV'
    )
    return conn

def query_to_df(sql):
    conn = get_snowflake_connection()
    df = pd.read_sql(sql, conn)
    conn.close()
    return df
