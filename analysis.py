import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns


DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
 dfshops = pd.read_sql_query("SELECT * FROM CoffeeShop;", engine)
 dfproducts = pd.read_sql_query("SELECT * FROM Products;", engine)
 dfemployees = pd.read_sql_query("SELECT * FROM Emolployee;", egine)
 dforders = pd.read_sql_query("SELECT * FROM Orders", engine)
 dforderitem = pd.read_sql_query("SELECT * FROM OrderItem", engine)
 dfpayment = pd.read_sql_query("SELECT * FROM Payment", engine)
