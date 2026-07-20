import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns


DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
dfshops = pd.read_sql_query("SELECT * FROM CoffeeShop;", engine)
dfproducts = pd.read_sql_query("SELECT * FROM Products;", engine)
dfemployee = pd.read_sql_query("SELECT * FROM Employee;", egine)
dforders = pd.read_sql_query("SELECT * FROM Orders", engine)
dforderitem = pd.read_sql_query("SELECT * FROM OrderItem", engine)
dfpayment = pd.read_sql_query("SELECT * FROM Payment", engine)
 
 
dforders['ordered_at']= pd.to_datetime(dforders['ordered_at']
dfemployee['employee_dob']= pd.to_datetime(dforders['employee_dob']
dfemployee['employee_hire_date']= pd.to_datetime(dforders['employee_hire_date']
print(dfemployees.isnull().sum()[df_employees.isnull().sum() > 0])
print(dfshops.isnull().sum()[dfshops.isnull().sum() > 0])
print(dfproducts.isnull().sum()[dfproducts.isnull().sum() > 0])
print(dforders.isnull().sum()[dforders.isnull().sum() > 0])

print(dforderitem.isnull().sum()[dforderitem.isnull().sum() > 0])
print(dfpayment.isnull().sum()[dfpayment.isnull().sum() > 0])

dforders['year'] = dforders['ordered_at'].dt.year
yearly_revenue = dforders.groupby('year')['order_total'].sum().reset_index()
print("\nYearly Revenue Trajectory :")
print(yearly_revenue.to_string(index=False))

