import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IN_PATH = PROJECT_ROOT / "data" / "derived" / "orders_finance_context.csv"
OUT_DIR = PROJECT_ROOT / "data" / "derived" / "kpi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def summarize(df, group_col, value_col):
    return (df.groupby(group_col)[value_col]
              .agg(orders="count", mean="mean", median="median", sum="sum")
              .reset_index()
            )

def main():
    df = pd.read_csv(IN_PATH)

    # Focus on valid amounts
    df["total_paid"] = pd.to_numeric(df["total_paid"], errors="coerce")
    df["food_cost"] = pd.to_numeric(df["food_cost"], errors="coerce")

    # 1) Payday vs non-payday
    payday_total = summarize(df, "is_payday", "total_paid")
    payday_food  = summarize(df, "is_payday", "food_cost")

    # 2) Days since payday (0-6)
    cycle_total = summarize(df, "days_since_payday", "total_paid")
    cycle_food  = summarize(df, "days_since_payday", "food_cost")

    # 3) Near rent due vs not (27-30 vs others)
    near_rent_total = summarize(df, "is_near_rent_due", "total_paid")
    near_rent_food  = summarize(df, "is_near_rent_due", "food_cost")

    # 4) Day of month trend (看看月末是否最低)
    dom_total = summarize(df, "day_of_month", "total_paid")
    dom_food  = summarize(df, "day_of_month", "food_cost")

    payday_total.to_csv(OUT_DIR / "kpi_payday_total_paid.csv", index=False)
    payday_food.to_csv(OUT_DIR / "kpi_payday_food_cost.csv", index=False)
    cycle_total.to_csv(OUT_DIR / "kpi_paycycle_total_paid.csv", index=False)
    cycle_food.to_csv(OUT_DIR / "kpi_paycycle_food_cost.csv", index=False)
    near_rent_total.to_csv(OUT_DIR / "kpi_near_rent_total_paid.csv", index=False)
    near_rent_food.to_csv(OUT_DIR / "kpi_near_rent_food_cost.csv", index=False)
    dom_total.to_csv(OUT_DIR / "kpi_day_of_month_total_paid.csv", index=False)
    dom_food.to_csv(OUT_DIR / "kpi_day_of_month_food_cost.csv", index=False)

    print("\n=== Payday vs Non-payday (total_paid) ===")
    print(payday_total)
    print("\n=== Payday vs Non-payday (food_cost) ===")
    print(payday_food)

    print("\n=== Near rent due (27-30) vs Others (total_paid) ===")
    print(near_rent_total)
    print("\n=== Day of month trend (total_paid) top/bottom ===")
    print(dom_total.sort_values("mean").head(5))
    print(dom_total.sort_values("mean").tail(5))

if __name__ == "__main__":
    main()
