import pandas as pd
import numpy as np
from pathlib import Path

IN_PATH = Path("data/clean/orders_clean.csv")
OUT_DIR = Path("data/derived")

def parse_dt(s):
    return pd.to_datetime(s, errors="coerce", dayfirst=True)

def standardize_platform(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.strip()
         .str.lower()
         .replace({
             "deliveroo": "Deliveroo",
             "hungry panda": "HungryPanda",
             "hungrypanda": "HungryPanda",
         })
    )

def standardize_restaurant(df: pd.DataFrame) -> pd.Series:
    """
    Create ONE canonical restaurant column for modeling.
    Preference order:
    restaurant_name_std > restaurant_name > restaurant
    """
    src_col = None
    for c in ["restaurant_name_std", "restaurant_name", "restaurant"]:
        if c in df.columns:
            src_col = c
            break

    if src_col is None:
        out = pd.Series([np.nan] * len(df), index=df.index)
    else:
        out = df[src_col]

    out = out.astype(str).str.strip()
    out.loc[out.isin(["", "nan", "None"])] = np.nan
    out = out.fillna("Unknown")
    return out

def main():
    df = pd.read_csv(IN_PATH)

    # Re-parse datetime
    if "ordered_time" in df.columns:
        df["ordered_time"] = parse_dt(df["ordered_time"])
    if "delivered_time" in df.columns:
        df["delivered_time"] = parse_dt(df["delivered_time"])

    # Delivery minutes
    if "delivery_minutes" not in df.columns and {"ordered_time", "delivered_time"}.issubset(df.columns):
        df["delivery_minutes"] = (df["delivered_time"] - df["ordered_time"]).dt.total_seconds() / 60

    # Fee features
    fee_cols = [c for c in ["delivery_fee", "service_fee"] if c in df.columns]
    if "total_paid" in df.columns and fee_cols:
        df["total_fees"] = df[fee_cols].sum(axis=1)
        df["fees_ratio"] = np.where(df["total_paid"] > 0, df["total_fees"] / df["total_paid"], np.nan)
    else:
        df["total_fees"] = np.nan
        df["fees_ratio"] = np.nan

    # Weekend flag
    if "ordered_time" in df.columns:
        df["is_weekend"] = (df["ordered_time"].dt.weekday >= 5).astype(int)

    # Normalize platform
    if "platform" in df.columns:
        df["platform"] = standardize_platform(df["platform"])
    else:
        df["platform"] = "Unknown"

    # Canonical restaurant (ONE column)
    df["restaurant"] = standardize_restaurant(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # -------- dim_platform --------
    dim_platform = df[["platform"]].drop_duplicates().reset_index(drop=True)
    dim_platform["platform_id"] = range(1, len(dim_platform) + 1)

    # -------- dim_date (exclude NaT) --------
    if "ordered_time" in df.columns:
        dim_date = (
            df.loc[df["ordered_time"].notna(), "ordered_time"]
              .dt.date
              .drop_duplicates()
              .reset_index(drop=True)
              .to_frame(name="date")
        )
        dim_date["date_id"] = range(1, len(dim_date) + 1)
        dt = pd.to_datetime(dim_date["date"])
        dim_date["year"] = dt.dt.year
        dim_date["month"] = dt.dt.month
        dim_date["weekday"] = dt.dt.weekday
        dim_date["is_weekend"] = (dim_date["weekday"] >= 5).astype(int)
    else:
        dim_date = pd.DataFrame(columns=["date","date_id","year","month","weekday","is_weekend"])

    # -------- dim_restaurant (no blanks, includes Unknown if needed) --------
    dim_restaurant = df[["restaurant"]].drop_duplicates().reset_index(drop=True)
    dim_restaurant["restaurant_id"] = range(1, len(dim_restaurant) + 1)

    # -------- fact_orders --------
    fact = df.copy()

    fact = fact.merge(dim_platform, on="platform", how="left")

    if "ordered_time" in fact.columns:
        fact["date"] = fact["ordered_time"].dt.date
        fact = fact.merge(dim_date[["date_id", "date"]], on="date", how="left")
    else:
        fact["date_id"] = np.nan

    fact = fact.merge(dim_restaurant, on="restaurant", how="left")

    if "order_id" not in fact.columns:
        fact["order_id"] = (
            pd.util.hash_pandas_object(fact.fillna(""), index=False)
              .astype("int64")
              .astype(str)
        )

    keep_cols = [
        "order_id", "platform_id", "restaurant_id", "date_id",
        "ordered_time", "delivered_time",
        "order_date", "order_hour", "order_weekday",
        "food_cost", "delivery_fee", "service_fee", "total_paid",
        "delivery_minutes", "total_fees", "fees_ratio",
        "delivery_time_bad", "delivery_minutes_outlier",
        "is_weekend"
    ]
    keep_cols = [c for c in keep_cols if c in fact.columns]
    fact_orders = fact[keep_cols].copy()

    # -------- Save --------
    # 提醒：如果 Excel/PowerBI 正在打开这些文件，会 Permission denied
    dim_platform.to_csv(OUT_DIR / "dim_platform.csv", index=False)
    dim_date.to_csv(OUT_DIR / "dim_date.csv", index=False)
    dim_restaurant.to_csv(OUT_DIR / "dim_restaurant.csv", index=False)
    fact_orders.to_csv(OUT_DIR / "fact_orders.csv", index=False)

    print("✅ Star schema saved to data/derived")

if __name__ == "__main__":
    main()
