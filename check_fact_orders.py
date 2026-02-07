import pandas as pd

df = pd.read_csv("data/derived/fact_orders.csv")

print("Total rows in fact_orders:", len(df))
print("Non-null ordered_time:", df["ordered_time"].notna().sum())
print("Distinct months (sample):")
print(df["ordered_time"].astype(str).head(10))

print("\nOrders per month (raw count):")
print(
    pd.to_datetime(df["ordered_time"], errors="coerce")
      .dt.to_period("M")
      .value_counts()
      .sort_index()
)
