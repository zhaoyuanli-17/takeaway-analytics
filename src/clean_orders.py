import re
import pandas as pd
import numpy as np
from pathlib import Path

RAW_DIR = Path("data/raw")
OUT_CLEAN = Path("data/clean/orders_clean.csv")
OUT_QC = Path("reports/data_quality_report.md")

RAW_FILES = [
    "deliveroo.csv","hungry panda.csv"
]

def normalize_colnames(cols):
    return [str(c).strip().lower().replace(" ", "_") for c in cols]

def try_parse_datetime(series):
    s = series.astype(str).str.strip()
    s = s.str.replace("：", ":", regex=False)   
    s = s.str.replace(";", ":", regex=False)   
    s = s.str.replace(r"[^0-9:/\-\s]", ":", regex=True)
    s = s.str.replace(r":+", ":", regex=True)
    s = s.str.replace(r"(\d{2}/\d{2}/\d{4})(\d{1,2}:\d{1,2})", r"\1 \2", regex=True)

    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def to_numeric(series):
    return pd.to_numeric(series, errors="coerce")

def main():
    frames = []

    for f in RAW_FILES:
        path = RAW_DIR / f
        if not path.exists():
            raise FileNotFoundError(f"Missing raw file: {path}")

        df = pd.read_csv(path)
        df = df.dropna(axis=1, how="all")
        df.columns = normalize_colnames(df.columns)

        if "platform" not in df.columns:
            df["platform"] = f.replace(".csv", "")

        frames.append(df)

    raw = pd.concat(frames, ignore_index=True)

    for col in ["ordered_time", "delivered_time"]:
        if col in raw.columns:
            raw[col] = try_parse_datetime(raw[col])
            # --- Cross-field checks: ordered_time vs delivered_time ---
    if "ordered_time" in raw.columns and "delivered_time" in raw.columns:
     raw["delivery_before_order"] = raw["delivered_time"] < raw["ordered_time"]

     raw["year_diff"] = raw["delivered_time"].dt.year - raw["ordered_time"].dt.year
     raw["year_mismatch"] = raw["year_diff"] != 0

     raw["delivery_time_bad"] = (
        raw["delivery_before_order"].fillna(False)
        | (raw["year_diff"].abs() >= 2).fillna(False)
    )

     raw.loc[raw["delivery_time_bad"], "delivered_time"] = pd.NaT
    # --- Data-driven check: delivery duration outliers (quantile-based) ---
    # --- Data-driven check: delivery duration outliers (quantile-based) ---
    if "ordered_time" in raw.columns and "delivered_time" in raw.columns:
     raw["delivery_minutes"] = (raw["delivered_time"] - raw["ordered_time"]).dt.total_seconds() / 60

     cap = raw["delivery_minutes"].quantile(0.995)
     raw["delivery_minutes_outlier"] = (raw["delivery_minutes"] < 0) | (raw["delivery_minutes"] > cap)

     raw.loc[raw["delivery_minutes_outlier"].fillna(False), "delivered_time"] = pd.NaT




    for col in ["food_cost", "delivery_fee", "service_fee", "total_paid"]:
        if col in raw.columns:
            raw[col] = to_numeric(raw[col])

    raw["order_date"] = raw["ordered_time"].dt.date
    raw["order_hour"] = raw["ordered_time"].dt.hour
    raw["order_weekday"] = raw["ordered_time"].dt.day_name()

    OUT_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    OUT_QC.parent.mkdir(parents=True, exist_ok=True)

    
    for c in ["ordered_time", "delivered_time"]:
      if c in raw.columns:
        raw[c] = raw[c].dt.strftime("%d/%m/%Y %H:%M")

    
    raw.to_csv(OUT_CLEAN, index=False)

    qc = raw.isna().mean().sort_values(ascending=False)
    report = "# Data Quality Report\n\n"
    report += f"Rows: {len(raw)}\n\n"
    report += "Missing rate by column:\n"
    for k, v in qc.items():
        report += f"- {k}: {v:.1%}\n"

    OUT_QC.write_text(report, encoding="utf-8")

    print("✅ Data cleaning completed")
    print("Saved:", OUT_CLEAN)
    print("Report:", OUT_QC)

if __name__ == "__main__":
    main()
