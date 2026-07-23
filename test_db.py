from sqlalchemy import create_engine
import pandas as pd
engine = create_engine('sqlite:///backend/data.db')
try:
    df = pd.read_sql("SELECT * FROM account LIMIT 1", engine)
    print(df.columns.tolist())
except Exception as e:
    print(e)
