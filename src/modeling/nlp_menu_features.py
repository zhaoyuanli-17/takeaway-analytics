import pandas as pd
import numpy as np
from pathlib import Path

# -------- Paths --------
IN_PATH = Path("data/clean/menu_items.csv")
OUT_DIR = Path("data/derived")

# -------- Keyword rules --------
KEYWORDS = {
    "spicy": ["spicy", "chilli", "chili", "hot"],
    "noodles": ["noodle", "ramen", "udon"],
    "rice": ["rice"],
    "fried": ["fried", "crispy", "tempura"],
    "soup": ["soup", "broth"],
    "vegan": ["vegan", "vegetarian", "tofu", "plant"]
}

def flag_keywords(text: str, keywords: list) -> int:
    if pd.isna(text):
        return 0
    t = text.lower()
    return int(any(k in t for k in keywords))

def main():
    if not IN_PATH.exists():
        raise FileNotFoundError(f"Missing {IN_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_PATH, encoding="latin1")


    # ---- basic cleaning ----
    df["restaurant"] = df["restaurant"].astype(str).str.strip()
    df["item_name"] = df["item_name"].astype(str).str.strip()
    if "tags" not in df.columns:
       df["tags"] = ""
    else:
       df["tags"] = df["tags"].astype(str)


    text_col = (df["item_name"] + " " + df["tags"]).str.lower()

    # ---- item-level NLP features ----
    for label, keys in KEYWORDS.items():
        df[label] = text_col.apply(lambda x: flag_keywords(x, keys))

    df["item_price"] = pd.to_numeric(df.get("price"), errors="coerce")

    menu_features = df[
        ["restaurant", "item_name", "item_price"]
        + list(KEYWORDS.keys())
    ].copy()

    # ---- restaurant-level profile ----
    agg_rules = {k: "mean" for k in KEYWORDS.keys()}
    agg_rules["item_price"] = "mean"

    restaurant_profile = (
        menu_features
        .groupby("restaurant", as_index=False)
        .agg(agg_rules)
        .rename(columns={
            "item_price": "avg_item_price",
            **{k: f"{k}_ratio" for k in KEYWORDS.keys()}
        })
    )

    # ---- save ----
    menu_features.to_csv(OUT_DIR / "menu_features.csv", index=False)
    restaurant_profile.to_csv(OUT_DIR / "restaurant_profile.csv", index=False)

    print("✅ NLP Step F done.")
    print(" - Saved: data/derived/menu_features.csv")
    print(" - Saved: data/derived/restaurant_profile.csv")

if __name__ == "__main__":
    main()
