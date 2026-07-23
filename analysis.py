import os
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sqlalchemy import create_engine, text

# Set visual theme
sns.set_theme(style="whitegrid")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"

# Database connection
db_user = os.getenv("DB_USER", "postgres")
db_password = os.getenv("DB_PASSWORD", "")
DATABASE_URL = f"postgresql://{db_user}:{db_password}@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

print("Fetching raw tables from PostgreSQL...")

# Wrap SQL queries in text() to support older SQLAlchemy versions
dfshops = pd.read_sql_query(text("SELECT * FROM CoffeeShop;"), engine)
dfproducts = pd.read_sql_query(text("SELECT * FROM Product;"), engine)
dfemployee = pd.read_sql_query(text("SELECT * FROM Employee;"), engine)
dforders = pd.read_sql_query(text("SELECT * FROM Orders;"), engine)
dforderitem = pd.read_sql_query(text("SELECT * FROM OrderItem;"), engine)
dfpayment = pd.read_sql_query(text("SELECT * FROM Payment;"), engine)

# Date conversions
dforders["ordered_at"] = pd.to_datetime(dforders["ordered_at"])
dfemployee["employee_dob"] = pd.to_datetime(dfemployee["employee_dob"])
dfemployee["employee_hire_date"] = pd.to_datetime(
    dfemployee["employee_hire_date"]
)

# Missing values check
print("\n--- MISSING VALUES PER TABLE ---")
print("Employees:\n", dfemployee.isnull().sum()[dfemployee.isnull().sum() > 0])
print("Shops:\n", dfshops.isnull().sum()[dfshops.isnull().sum() > 0])
print("Products:\n", dfproducts.isnull().sum()[dfproducts.isnull().sum() > 0])
print("Orders:\n", dforders.isnull().sum()[dforders.isnull().sum() > 0])
print(
    "OrderItems:\n", dforderitem.isnull().sum()[dforderitem.isnull().sum() > 0]
)
print("Payments:\n", dfpayment.isnull().sum()[dfpayment.isnull().sum() > 0])

# Yearly revenue
dforders["year"] = dforders["ordered_at"].dt.year
yearly_revenue = dforders.groupby("year")["order_total"].sum().reset_index()
print("\nYearly Revenue Trajectory:")
print(yearly_revenue.to_string(index=False))

# -------------------------------------------------------------------
# VISUALIZATION 1: Peak Hourly Sales
# -------------------------------------------------------------------
print("\nGenerating Peak Hourly Analysis...")
hourly_query = text("""
    SELECT 
        EXTRACT(HOUR FROM ordered_at) AS hour_of_day,
        COUNT(order_id) AS total_orders,
        ROUND(SUM(order_total)::numeric, 2) AS total_revenue
    FROM Orders
    WHERE order_status = 'served'
    GROUP BY hour_of_day
    ORDER BY hour_of_day ASC;
""")

df_hourly = pd.read_sql(hourly_query, con=engine)

fig, ax1 = plt.subplots(figsize=(10, 5))
color = "tab:blue"
ax1.set_xlabel("Hour of Day (24h Clock)", fontsize=12)
ax1.set_ylabel("Total Revenue ($)", color=color, fontsize=12)
ax1.plot(
    df_hourly["hour_of_day"],
    df_hourly["total_revenue"],
    color=color,
    marker="o",
    linewidth=2,
)
ax1.tick_params(axis="y", labelcolor=color)

ax2 = ax1.twinx()
color = "tab:gray"
ax2.set_ylabel("Order Count", color=color, fontsize=12)
ax2.bar(
    df_hourly["hour_of_day"],
    df_hourly["total_orders"],
    alpha=0.3,
    color=color,
    width=0.4,
)
ax2.tick_params(axis="y", labelcolor=color)

plt.title(
    "Peak Hourly Traffic & Revenue Analysis (2.29M Orders Dataset)",
    fontsize=14,
    pad=15,
)
fig.tight_layout()
plt.savefig("peak_hourly_traffic.png", dpi=300)
plt.close()
print("✓ Saved: peak_hourly_traffic.png")

# -------------------------------------------------------------------
# VISUALIZATION 2: Location Revenue
# -------------------------------------------------------------------
print("Generating Location Revenue Comparison...")
shop_query = text("""
    SELECT 
        cs.shop_name,
        COUNT(o.order_id) AS total_orders,
        ROUND(SUM(o.order_total)::numeric, 2) AS total_revenue
    FROM CoffeeShop cs
    JOIN Orders o ON cs.shop_id = o.shop_id
    WHERE o.order_status = 'served'
    GROUP BY cs.shop_id, cs.shop_name
    ORDER BY total_revenue DESC;
""")

df_shops = pd.read_sql(shop_query, con=engine)

plt.figure(figsize=(10, 5))
b# With this:
barplot = sns.barplot(
    data=df_shops,
    x="shop_name",
    y="total_revenue",
    hue="shop_name",
    palette="viridis",
    legend=False,
)
plt.title("Total Revenue Comparison Across Multi-Tenant Shops", fontsize=14)
plt.xlabel("Coffee Shop Location", fontsize=12)
plt.ylabel("Total Revenue ($)", fontsize=12)
plt.xticks(rotation=15)

for p in barplot.patches:
    barplot.annotate(
        f"${p.get_height():,.2f}",
        (p.get_x() + p.get_width() / 2.0, p.get_height()),
        ha="center",
        va="center",
        xytext=(0, 8),
        textcoords="offset points",
        fontsize=10,
    )

plt.tight_layout()
plt.savefig("shop_revenue_comparison.png", dpi=300)
plt.close()
print("✓ Saved: shop_revenue_comparison.png")

print(
    "\nAll data extraction, sanity checks, and chart exports completed successfully!"
)
