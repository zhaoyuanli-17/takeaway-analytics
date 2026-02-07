import pandas as pd
from pathlib import Path

ROSTER_ENRICHED_PATH = Path("data/derived/orders_enriched_roster.csv")
DIM_RESTAURANT_PATH = Path("data/derived/dim_restaurant.csv")
REST_PROFILE_PATH = Path("data/derived/restaurant_profile.csv")

OUT_DIR = Path("data/derived")

def main():
    roster = pd.read_csv(ROSTER_ENRICHED_PATH)
    dim_rest = pd.read_csv(DIM_RESTAURANT_PATH)
    rest_prof = pd.read_csv(REST_PROFILE_PATH)

    # 防止列名有空格（你之前 roster 就出现过）
    roster.columns = [c.strip() for c in roster.columns]
    dim_rest.columns = [c.strip() for c in dim_rest.columns]
    rest_prof.columns = [c.strip() for c in rest_prof.columns]

    # 必要列检查
    if not {"restaurant_id", "restaurant"}.issubset(dim_rest.columns):
        raise ValueError(f"dim_restaurant must have restaurant_id + restaurant. Found: {list(dim_rest.columns)}")
    if "restaurant" not in rest_prof.columns:
        raise ValueError(f"restaurant_profile must have restaurant column. Found: {list(rest_prof.columns)}")
    if "is_workday" not in roster.columns:
        raise ValueError(f"orders_enriched_roster must have is_workday. Found: {list(roster.columns)}")

    # restaurant_id -> restaurant name
    out = roster.merge(dim_rest[["restaurant_id", "restaurant"]], on="restaurant_id", how="left")

    # join NLP restaurant profile
    out = out.merge(rest_prof, on="restaurant", how="left")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = OUT_DIR / "orders_roster_nlp.csv"
    out.to_csv(out_path, index=False)

    # KPI：workday vs non-workday 的口味均值（ratio 列）
    ratio_cols = [c for c in rest_prof.columns if c.endswith("_ratio")]
    kpi = (
        out.groupby("is_workday")[ratio_cols]
           .mean(numeric_only=True)
           .reset_index()
    )
    kpi_path = OUT_DIR / "kpi_workday_foodprefs.csv"
    kpi.to_csv(kpi_path, index=False)

    print("✅ Step F (join roster + NLP) done.")
    print(f" - Saved: {out_path}")
    print(f" - Saved: {kpi_path}")
    print("\nPreview kpi_workday_foodprefs:")
    print(kpi)

if __name__ == "__main__":
    main()
