import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns


DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
 shops = pd.read_sql_query("SELECT * FROM CoffeeShop;", engine)
 products = pd.read_sql_query("SELECT * FROM Products;", engine)
