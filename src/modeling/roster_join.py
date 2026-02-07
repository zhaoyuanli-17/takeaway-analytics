import pandas as pd
import numpy as np
from pathlib import Path

FACT_PATH = Path("data/derived/fact_orders.csv")
ROSTER_PATH = Path("data/clean/roster.csv")  
OUT_DIR = Path("data/derived")
REPORTS_DIR = Path("reports")


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names:
    - strip leading/trailing spaces
    - lower
    - replace spaces with underscore
    """
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df


def parse_time_token(t):
    """
    Parse time tokens like:
    '7am', '3pm', '11pm', '07:30', '15:00', '7 am', '07:00 AM'
    Returns a datetime.time or NaT.
    """
    if pd.isna(t):
        return pd.NaT
    s = str(t).strip().lower()
    if s in ["", "nan", "none"]:
        return pd.NaT

    # normalize common variants
    s = s.replace(".", "")
    s = s.replace(" a m", "am").replace(" p m", "pm")
    s = s.replace(" a.m", "am").replace(" p.m", "pm")
    s = s.replace("am", " am").replace("pm", " pm").strip()  # helps parser sometimes

    # try parse directly
    for candidate in [s, "2000-01-01 " + s]:
        try:
            dt = pd.to_datetime(candidate, errors="raise")
            return dt.time()
        except Exception:
            continue

    return pd.NaT


def pick_roster_columns(r: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure we end up with canonical columns:
    date, shift_start, shift_end, shift_type, hours

    Your file may include:
    shift_start.1, shift_end.1, shift_type.1
    We'll prefer base names; fallback to *.1 if needed.
    """
    r = r.copy()

    def pick(base: str):
        if base in r.columns:
            return base
        alt = base + ".1"
        if alt in r.columns:
            return alt
        return None

    date_col = "date" if "date" in r.columns else None
    start_col = pick("shift_start")
    end_col = pick("shift_end")
    type_col = pick("shift_type")
    hours_col = "hours" if "hours" in r.columns else None

    missing = [x for x in [date_col, start_col, end_col, type_col] if x is None]
    if missing:
        raise ValueError(
            "Roster missing required columns after normalization. "
            f"Found columns: {list(r.columns)}"
        )

    out = pd.DataFrame({
        "date": r[date_col],
        "shift_start": r[start_col],
        "shift_end": r[end_col],
        "shift_type": r[type_col],
    })

    if hours_col is not None:
        out["hours"] = r[hours_col]
    else:
        out["hours"] = np.nan

    return out


def build_shift_datetimes(roster: pd.DataFrame) -> pd.DataFrame:
    """
    Build shift_start_dt and shift_end_dt from date + shift_start/shift_end strings.
    Night shift crosses midnight: if end <= start, add +1 day to end.
    Day off: keep datetimes NaT.
    """
    r = roster.copy()

    # date
   
    r["date"] = pd.to_datetime(r["date"], errors="coerce", dayfirst=True).dt.date

    # shift_type canonical
    r["shift_type"] = (
        r["shift_type"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # parse times
    r["shift_start_time"] = r["shift_start"].apply(parse_time_token)
    r["shift_end_time"] = r["shift_end"].apply(parse_time_token)

    base_date = pd.to_datetime(r["date"], errors="coerce")
    r["shift_start_dt"] = pd.NaT
    r["shift_end_dt"] = pd.NaT

    is_workday = r["shift_type"].ne("day off")
    has_times = r["shift_start_time"].notna() & r["shift_end_time"].notna()
    mask = is_workday & has_times & base_date.notna()

    # create datetime by adding HH:MM:SS to date
    # (time -> string -> timedelta)
    r.loc[mask, "shift_start_dt"] = base_date[mask] + pd.to_timedelta(r.loc[mask, "shift_start_time"].astype(str))
    r.loc[mask, "shift_end_dt"] = base_date[mask] + pd.to_timedelta(r.loc[mask, "shift_end_time"].astype(str))

    # cross-midnight
    cross = mask & (r["shift_end_dt"] <= r["shift_start_dt"])
    r.loc[cross, "shift_end_dt"] = r.loc[cross, "shift_end_dt"] + pd.Timedelta(days=1)

    # work hours
    r["work_hours"] = pd.to_numeric(r["hours"], errors="coerce")
    calc = mask & r["work_hours"].isna()
    r.loc[calc, "work_hours"] = (
        (r.loc[calc, "shift_end_dt"] - r.loc[calc, "shift_start_dt"])
        .dt.total_seconds() / 3600
    )

    keep = ["date", "shift_type", "shift_start_dt", "shift_end_dt", "work_hours"]
    r = r[keep].dropna(subset=["date"]).drop_duplicates()

    return r


def join_orders_to_roster(orders: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """
    Join rules:
    - Workday: ordered_time within [shift_start_dt, shift_end_dt] on same date
    - Day off: match only by order_date == date
    """
    o = orders.copy()
    if "ordered_time" not in o.columns:
        raise ValueError("fact_orders.csv must contain 'ordered_time'.")

    o["ordered_time"] = pd.to_datetime(o["ordered_time"], errors="coerce")
    o = o[o["ordered_time"].notna()].copy()
    o["order_date"] = o["ordered_time"].dt.date

    # split roster
    r_work = roster[roster["shift_type"].ne("day off")].copy()
    r_off = roster[roster["shift_type"].eq("day off")].copy()

    # workday: merge on date then filter by window
    tmp = o.merge(r_work, left_on="order_date", right_on="date", how="left")

    in_window = (
        tmp["shift_start_dt"].notna() &
        tmp["shift_end_dt"].notna() &
        (tmp["ordered_time"] >= tmp["shift_start_dt"]) &
        (tmp["ordered_time"] <= tmp["shift_end_dt"])
    )
    matched_work = tmp[in_window].copy()

    # if multiple matches, choose closest shift_start
    matched_work["gap_to_start_min"] = (matched_work["ordered_time"] - matched_work["shift_start_dt"]).dt.total_seconds() / 60
    if "order_id" in matched_work.columns:
        matched_work = matched_work.sort_values(["order_id", "gap_to_start_min"]).drop_duplicates("order_id")

    # day off: date-only merge
    off_join = o.merge(r_off, left_on="order_date", right_on="date", how="left")

    # combine: prefer work match, else day off, else empty
    if "order_id" in o.columns:
        combined = o.merge(
            matched_work[["order_id", "shift_type", "shift_start_dt", "shift_end_dt", "work_hours"]],
            on="order_id", how="left"
        )

        combined = combined.merge(
            off_join[["order_id", "shift_type", "shift_start_dt", "shift_end_dt", "work_hours"]],
            on="order_id", how="left", suffixes=("", "_off")
        )

        combined["shift_type"] = combined["shift_type"].fillna(combined["shift_type_off"])
        combined["shift_start_dt"] = combined["shift_start_dt"].fillna(combined["shift_start_dt_off"])
        combined["shift_end_dt"] = combined["shift_end_dt"].fillna(combined["shift_end_dt_off"])
        combined["work_hours"] = combined["work_hours"].fillna(combined["work_hours_off"])
        combined = combined.drop(columns=[c for c in combined.columns if c.endswith("_off")])

    else:
        # fallback (shouldn't happen in your fact table)
        combined = o.copy()
        combined["shift_type"] = np.nan
        combined["shift_start_dt"] = pd.NaT
        combined["shift_end_dt"] = pd.NaT
        combined["work_hours"] = np.nan

    # derived fields
    combined["is_workday"] = combined["shift_type"].fillna("unknown").ne("day off").astype(int)

    combined["mins_after_shift_end"] = np.where(
        combined["shift_end_dt"].notna(),
        (combined["ordered_time"] - combined["shift_end_dt"]).dt.total_seconds() / 60,
        np.nan
    )
    combined["is_after_shift"] = np.where(
        combined["mins_after_shift_end"].notna(),
        (combined["mins_after_shift_end"] >= 0).astype(int),
        np.nan
    )

    return combined


def write_insights(enriched: pd.DataFrame, path: Path):
    df = enriched.copy()
    df["total_paid"] = pd.to_numeric(df.get("total_paid"), errors="coerce")
    df["delivery_minutes"] = pd.to_numeric(df.get("delivery_minutes"), errors="coerce")

    total_orders = df["order_id"].nunique() if "order_id" in df.columns else len(df)
    share_workday = df["is_workday"].mean() if "is_workday" in df.columns else np.nan

    after = df[df["mins_after_shift_end"].notna()].copy()
    after_pos = after[after["mins_after_shift_end"] >= 0].copy()

    def fmt(x, p=2):
        return "n/a" if pd.isna(x) else f"{x:.{p}f}"

    lines = []
    lines.append("# Work Roster Insights (Step E)\n")
    lines.append(f"- Total orders in enriched dataset: {total_orders}")
    lines.append(f"- Share of orders on workdays (shift_type != day off): {share_workday:.2%}" if pd.notna(share_workday) else "- Share of workdays: n/a")

    if len(after_pos) > 0:
        lines.append(f"- Orders placed after shift end (count): {len(after_pos)}")
        lines.append(f"- Median minutes after shift end: {fmt(after_pos['mins_after_shift_end'].median(), 1)}")
        lines.append(f"- P90 minutes after shift end: {fmt(np.nanpercentile(after_pos['mins_after_shift_end'], 90), 1)}")
    else:
        lines.append("- After-shift analysis: not enough matched records to compute.")

    if "shift_type" in df.columns:
        by_shift = (
            df.groupby("shift_type")
              .agg(
                  orders=("order_id", "nunique") if "order_id" in df.columns else ("ordered_time","count"),
                  avg_spend=("total_paid", "mean"),
                  median_delivery=("delivery_minutes", "median"),
              )
              .reset_index()
              .sort_values("orders", ascending=False)
        )
        lines.append("\n## Summary by shift_type\n")
    for _, row in by_shift.iterrows():
     lines.append(
        f"- {row['shift_type']}: "
        f"{int(row['orders'])} orders, "
        f"avg spend {row['avg_spend']:.2f}, "
        f"median delivery {row['median_delivery']:.1f} mins"
    )


    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


# -----------------------------
# main
# -----------------------------
def main():
    if not FACT_PATH.exists():
        raise FileNotFoundError(f"Missing {FACT_PATH}. Run star schema first.")
    if not ROSTER_PATH.exists():
        raise FileNotFoundError(f"Missing {ROSTER_PATH}. Put roster.csv under data/clean/roster.csv")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    orders = pd.read_csv(FACT_PATH)

    roster_raw = pd.read_csv(ROSTER_PATH)

    roster_raw.columns = roster_raw.columns.astype(str).str.strip()
    roster_raw.columns = roster_raw.columns.str.lower()

    roster_raw = normalize_cols(roster_raw)

    # Drop Excel junk cols
    roster_raw = roster_raw.loc[:, [c for c in roster_raw.columns if not c.startswith("unnamed")]]

    roster_base = pick_roster_columns(roster_raw)

    roster = build_shift_datetimes(roster_base)
    enriched = join_orders_to_roster(orders, roster)

    out_path = OUT_DIR / "orders_enriched_roster.csv"
    enriched.to_csv(out_path, index=False)

    report_path = REPORTS_DIR / "work_roster_insights.md"
    write_insights(enriched, report_path)

    print("✅ Step E done.")
    print(f" - Saved: {out_path}")
    print(f" - Saved: {report_path}")


if __name__ == "__main__":
    main()
