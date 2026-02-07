import pandas as pd
from pathlib import Path

# ----------------------------
# Config
# ----------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
IN_PATH = PROJECT_ROOT / "data" / "derived" / "orders_enriched_roster.csv"
OUT_PATH = PROJECT_ROOT / "data" / "derived" / "orders_finance_context.csv"

def add_finance_features(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure order_date exists
    if "order_date" not in df.columns:
        # fallback: derive from ordered_time
        df["order_date"] = pd.to_datetime(df["ordered_time"], errors="coerce").dt.date

    # Parse order_date as datetime (date-level)
    df["order_date_dt"] = pd.to_datetime(df["order_date"], errors="coerce")

    # --- Payday features (every Friday) ---
    # pandas weekday: Monday=0 ... Sunday=6, Friday=4
    df["weekday"] = df["order_date_dt"].dt.weekday
    df["is_payday"] = (df["weekday"] == 4).astype(int)

    # days_since_payday: 0 on Friday, 1 on Saturday, ... 6 on Thursday
    # This assumes weekly payday cycle.
    df["days_since_payday"] = (df["weekday"] - 4) % 7

    # --- Rent features (rent due on 30th) ---
    df["day_of_month"] = df["order_date_dt"].dt.day

    df["is_rent_due"] = (df["day_of_month"] == 30).astype(int)

    # days_to_rent_due: 0 on 30th, positive before 30th
    # For months without 30 days (e.g., Feb), this will still compute but you can filter later.
    df["days_to_rent_due"] = 30 - df["day_of_month"]

    # month_end bucket: last ~4 days before rent due (27-30)
    df["is_near_rent_due"] = df["day_of_month"].isin([27, 28, 29, 30]).astype(int)

    return df

def main():
    df = pd.read_csv(IN_PATH)

    # Safety: make sure key money fields are numeric
    for c in ["total_paid", "food_cost", "delivery_fee", "service_fee"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df2 = add_finance_features(df)
    df2.to_csv(OUT_PATH, index=False)
    print(f"Saved: {OUT_PATH}")
    print(df2[["order_date", "weekday", "is_payday", "days_since_payday",
               "day_of_month", "is_rent_due", "days_to_rent_due", "is_near_rent_due"]].head(10))

if __name__ == "__main__":
    main()
