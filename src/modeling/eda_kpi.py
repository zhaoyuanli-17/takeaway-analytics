import pandas as pd
import numpy as np
from pathlib import Path

FACT_PATH = Path("data/derived/fact_orders.csv")
OUT_DIR = Path("data/derived")
REPORTS_DIR = Path("reports")

def main():
    if not FACT_PATH.exists():
        raise FileNotFoundError(f"Cannot find {FACT_PATH}. Please run your star schema script first.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(FACT_PATH)

    # --- parse datetime safely ---
    if "ordered_time" not in df.columns:
        raise ValueError("fact_orders.csv must contain 'ordered_time'.")

    df["ordered_time"] = pd.to_datetime(df["ordered_time"], errors="coerce")

    # --- must-have numeric cols (fill if missing) ---
    for c in ["total_paid", "delivery_minutes", "fees_ratio", "total_fees"]:
        if c not in df.columns:
            df[c] = np.nan

    # --- derive time features from ordered_time (no dependency on order_hour/order_weekday columns) ---
    df["order_date"] = df["ordered_time"].dt.date
    df["order_month"] = df["ordered_time"].dt.to_period("M").astype(str)
    df["order_hour"] = df["ordered_time"].dt.hour
    df["order_weekday"] = df["ordered_time"].dt.weekday  # 0=Mon
    df["is_late_night"] = df["order_hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(int)

    # if is_weekend missing or has NaN, recompute
    if "is_weekend" not in df.columns:
        df["is_weekend"] = (df["order_weekday"] >= 5).astype(int)
    else:
        df["is_weekend"] = pd.to_numeric(df["is_weekend"], errors="coerce")
        df.loc[df["is_weekend"].isna(), "is_weekend"] = (df.loc[df["is_weekend"].isna(), "order_weekday"] >= 5).astype(int)

    # --- Daily KPI ---
    kpi_daily = (
        df.groupby("order_date", dropna=True)
          .agg(
              orders_cnt=("order_id", "nunique") if "order_id" in df.columns else ("ordered_time", "count"),
              total_spend=("total_paid", "sum"),
              aov=("total_paid", "mean"),
              median_delivery=("delivery_minutes", "median"),
              p90_delivery=("delivery_minutes", lambda x: np.nanpercentile(x.dropna(), 90) if x.dropna().shape[0] else np.nan),
              avg_fees_ratio=("fees_ratio", "mean"),
              late_night_share=("is_late_night", "mean"),
              weekend_share=("is_weekend", "mean"),
          )
          .reset_index()
          .rename(columns={"order_date": "date"})
    )

    # --- Monthly KPI ---
    kpi_monthly = (
        df.groupby("order_month", dropna=True)
          .agg(
              orders_cnt=("order_id", "nunique") if "order_id" in df.columns else ("ordered_time", "count"),
              total_spend=("total_paid", "sum"),
              aov=("total_paid", "mean"),
              median_delivery=("delivery_minutes", "median"),
              avg_fees_ratio=("fees_ratio", "mean"),
          )
          .reset_index()
          .rename(columns={"order_month": "month"})
    )

    # --- Save KPIs ---
    kpi_daily.to_csv(OUT_DIR / "kpi_orders_daily.csv", index=False)
    kpi_monthly.to_csv(OUT_DIR / "kpi_orders_monthly.csv", index=False)

    # --- Basic insights text (8-12 bullets) ---
    # Keep it simple and robust to missing values
    total_orders = int(df["order_id"].nunique()) if "order_id" in df.columns else int(df.shape[0])
    total_spend = float(np.nan_to_num(df["total_paid"]).sum())
    aov = float(np.nanmean(df["total_paid"])) if df["total_paid"].notna().any() else np.nan
    median_delivery = float(np.nanmedian(df["delivery_minutes"])) if df["delivery_minutes"].notna().any() else np.nan
    avg_fees_ratio = float(np.nanmean(df["fees_ratio"])) if df["fees_ratio"].notna().any() else np.nan
    late_night_share = float(df["is_late_night"].mean()) if df["is_late_night"].notna().any() else np.nan
    weekend_share = float(df["is_weekend"].mean()) if df["is_weekend"].notna().any() else np.nan

    # Top restaurant (by orders) if restaurant_id exists
    top_restaurant_line = ""
    if "restaurant_id" in df.columns:
        top_rest = df.groupby("restaurant_id").size().sort_values(ascending=False).head(1)
        if len(top_rest):
            rid = int(top_rest.index[0])
            cnt = int(top_rest.iloc[0])
            top_restaurant_line = f"- Top restaurant_id by orders: restaurant_id={rid} ({cnt} orders)"

    insights = [
        f"- Total orders: {total_orders}",
        f"- Total spend: {total_spend:.2f}",
        f"- Average order value (AOV): {aov:.2f}" if not np.isnan(aov) else "- Average order value (AOV): n/a",
        f"- Median delivery minutes: {median_delivery:.1f}" if not np.isnan(median_delivery) else "- Median delivery minutes: n/a",
        f"- Average fees ratio: {avg_fees_ratio:.2%}" if not np.isnan(avg_fees_ratio) else "- Average fees ratio: n/a",
        f"- Late-night order share (22:00–05:00): {late_night_share:.2%}" if not np.isnan(late_night_share) else "- Late-night order share: n/a",
        f"- Weekend order share: {weekend_share:.2%}" if not np.isnan(weekend_share) else "- Weekend order share: n/a",
    ]
    if top_restaurant_line:
        insights.append(top_restaurant_line)

    # Add platform split if platform_id exists
    if "platform_id" in df.columns:
        plat = df.groupby("platform_id").agg(orders=("order_id","nunique") if "order_id" in df.columns else ("ordered_time","count"),
                                             spend=("total_paid","sum")).reset_index()
        plat = plat.sort_values("orders", ascending=False)
        insights.append(f"- Platform split (platform_id): {plat.to_dict(orient='records')}")

    report_path = REPORTS_DIR / "insights_summary.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Insights Summary (Step D)\n\n")
        f.write("\n".join(insights))
        f.write("\n")

    print("✅ Step D done.")
    print(f" - Saved: {OUT_DIR / 'kpi_orders_daily.csv'}")
    print(f" - Saved: {OUT_DIR / 'kpi_orders_monthly.csv'}")
    print(f" - Saved: {report_path}")

if __name__ == "__main__":
    main()
