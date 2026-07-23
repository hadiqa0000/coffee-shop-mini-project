import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine

# Database Connection
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

# 1. Ingest Data
dfshops = pd.read_sql_query("SELECT * FROM CoffeeShop;", engine)
dfproducts = pd.read_sql_query("SELECT * FROM Product;", engine) 
dfemployee = pd.read_sql_query("SELECT * FROM Employee;", engine)
dforders = pd.read_sql_query("SELECT * FROM Orders;", engine)
dforderitem = pd.read_sql_query("SELECT * FROM OrderItem;", engine)
dfpayment = pd.read_sql_query("SELECT * FROM Payment;", engine)


dforders["ordered_at"] = pd.to_datetime(dforders["ordered_at"])
dfemployee["employee_dob"] = pd.to_datetime(dfemployee["employee_dob"])
dfemployee["employee_hire_date"] = pd.to_datetime(
    dfemployee["employee_hire_date"]
)


print("--- MISSING VALUES PER TABLE ---")
print("Employees:\n", dfemployee.isnull().sum()[dfemployee.isnull().sum() > 0])
print("Shops:\n", dfshops.isnull().sum()[dfshops.isnull().sum() > 0])
print("Products:\n", dfproducts.isnull().sum()[dfproducts.isnull().sum() > 0])
print("Orders:\n", dforders.isnull().sum()[dforders.isnull().sum() > 0])
print(
    "OrderItems:\n", dforderitem.isnull().sum()[dforderitem.isnull().sum() > 0]
)
print("Payments:\n", dfpayment.isnull().sum()[dfpayment.isnull().sum() > 0])

dforders["year"] = dforders["ordered_at"].dt.year
yearly_revenue = dforders.groupby("year")["order_total"].sum().reset_index()

print("\nYearly Revenue Trajectory:")
print(yearly_revenue.to_string(index=False))
