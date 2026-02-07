import pandas as pd
import numpy as np
from pathlib import Path

FACT_PATH = Path("data/derived/fact_orders.csv")
OUT_DIR = Path("data/derived")
REPORTS_DIR = Path("reports")

def main():
    df = pd.read_csv(FACT_PATH)

    # ---- datetime ----
    df["ordered_time"] = pd.to_datetime(df["ordered_time"], errors="coerce")
    df = df[df["ordered_time"].notna()].copy()

    df["order_date"] = df["ordered_time"].dt.date
    df["order_hour"] = df["ordered_time"].dt.hour
    df["order_week"] = df["ordered_time"].dt.to_period("W").astype(str)

    # ---- frequency ----
    weekly_orders = (
        df.groupby("order_week")["order_id"]
          .nunique()
          .mean()
    )

    dinner_share = df["order_hour"].between(18, 21).mean()
    late_night_share = df["order_hour"].isin([22,23,0,1,2,3,4,5]).mean()

    # ---- repeat purchase & interval ----
    repeat_stats = None
    avg_repurchase_gap = np.nan

    if "restaurant_id" in df.columns:
        df_sorted = df.sort_values(["restaurant_id", "ordered_time"])
        df_sorted["prev_time"] = df_sorted.groupby("restaurant_id")["ordered_time"].shift(1)
        df_sorted["repurchase_gap_days"] = (
            (df_sorted["ordered_time"] - df_sorted["prev_time"])
            .dt.total_seconds() / (3600 * 24)
        )

        repeat_stats = (
            df.groupby("restaurant_id")["order_id"]
              .nunique()
              .reset_index(name="orders_cnt")
              .sort_values("orders_cnt", ascending=False)
        )

        avg_repurchase_gap = df_sorted["repurchase_gap_days"].mean()

    # ---- value for money ----
    if "items_count" in df.columns:
        df["cost_per_item"] = df["food_cost"] / df["items_count"]
    else:
        df["cost_per_item"] = np.nan

    df["mins_per_currency"] = df["delivery_minutes"] / df["total_paid"]

    # ---- summary table ----
    metrics = {
        "avg_orders_per_week": weekly_orders,
        "dinner_share": dinner_share,
        "late_night_share": late_night_share,
        "avg_repurchase_gap_days": avg_repurchase_gap,
        "avg_cost_per_item": df["cost_per_item"].mean(),
        "avg_fees_ratio": df["fees_ratio"].mean(),
        "avg_mins_per_currency": df["mins_per_currency"].mean(),
    }

    metrics_df = pd.DataFrame(
        [{"metric": k, "value": v} for k, v in metrics.items()]
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    metrics_df.to_csv(OUT_DIR / "behavior_metrics.csv", index=False)

    # ---- insights report ----
    lines = [
        "# Behavior Metrics Insights\n",
        f"- Average orders per week: {weekly_orders:.2f}",
        f"- Dinner order share (18–22): {dinner_share:.2%}",
        f"- Late-night order share (22–05): {late_night_share:.2%}",
        f"- Average repurchase gap (days): {avg_repurchase_gap:.1f}" if not np.isnan(avg_repurchase_gap) else "- Repurchase gap: n/a",
        f"- Average cost per item: {df['cost_per_item'].mean():.2f}",
        f"- Average fees ratio: {df['fees_ratio'].mean():.2%}",
        f"- Delivery minutes per currency unit: {df['mins_per_currency'].mean():.2f}",
    ]

    with open(REPORTS_DIR / "behavior_insights.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("✅ Behavior metrics generated.")

if __name__ == "__main__":
    main()
