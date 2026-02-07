import pandas as pd
import numpy as np
from pathlib import Path

IN_PATH = Path("data/derived/orders_roster_nlp.csv")
OUT_PATH = Path("data/derived/orders_roster_nlp_fixed.csv")

def parse_dt(s):
    # 兼容各种乱格式
    return pd.to_datetime(s, errors="coerce")

def build_shift_datetimes(order_dt: pd.Series, shift_type: pd.Series):
    """
    shift_type expects values like:
    'morning shift', 'evenning shift', 'evening shift', 'night shift', 'day off', 'Unknown'
    """
    # 统一命名
    st = shift_type.fillna("Unknown").str.lower().str.strip()
    st = st.replace({"evenning shift": "evening shift"})  # 你数据里拼写错了

    order_date = order_dt.dt.normalize()  # 当天 00:00

    # 默认 Unknown/day off -> NaT
    shift_start = pd.Series(pd.NaT, index=order_dt.index)
    shift_end = pd.Series(pd.NaT, index=order_dt.index)

    # morning 07-15
    m = st.eq("morning shift")
    shift_start.loc[m] = order_date.loc[m] + pd.Timedelta(hours=7)
    shift_end.loc[m] = order_date.loc[m] + pd.Timedelta(hours=15)

    # evening 15-23
    e = st.eq("evening shift")
    shift_start.loc[e] = order_date.loc[e] + pd.Timedelta(hours=15)
    shift_end.loc[e] = order_date.loc[e] + pd.Timedelta(hours=23)

    # night 23-07 next day
    n = st.eq("night shift")
    shift_start.loc[n] = order_date.loc[n] + pd.Timedelta(hours=23)
    shift_end.loc[n] = order_date.loc[n] + pd.Timedelta(days=1, hours=7)

    return shift_start, shift_end, st

def main():
    df = pd.read_csv(IN_PATH)

    # 1) 找到订单时间列
    time_col = None
    for c in ["ordered_time", "order_time"]:
        if c in df.columns:
            time_col = c
            break
    if time_col is None:
        raise ValueError("Cannot find ordered_time / order_time in the file.")

    df[time_col] = parse_dt(df[time_col])

    if "shift_type" not in df.columns:
        raise ValueError("Cannot find shift_type column in the file.")

    # 2) 生成 shift start/end datetime
    shift_start_dt, shift_end_dt, st_norm = build_shift_datetimes(df[time_col], df["shift_type"])

    df["shift_type_norm"] = st_norm
    df["shift_start_dt"] = shift_start_dt
    df["shift_end_dt"] = shift_end_dt

    # 3) 计算 mins_after_shift_end & is_after_shift（只对有 shift_end 的行）
    df["mins_after_shift_end_fixed"] = (
        (df[time_col] - df["shift_end_dt"]).dt.total_seconds() / 60
    )

    df["is_after_shift_fixed"] = np.where(
        df["shift_end_dt"].notna() & (df["mins_after_shift_end_fixed"] >= 0),
        1, 0
    )

    # 4) 也给一个 “距 shift start” 的特征（更稳，常用于行为分析）
    df["mins_from_shift_start_fixed"] = (
        (df[time_col] - df["shift_start_dt"]).dt.total_seconds() / 60
    )

    # 5) 简单质量检查输出（你跑完看 print）
    print("✅ Fixed shift timing created.")
    print("Non-null shift_end_dt:", int(df["shift_end_dt"].notna().sum()))
    print("is_after_shift_fixed=1:", int((df["is_after_shift_fixed"] == 1).sum()))

    df.to_csv(OUT_PATH, index=False)
    print("🎯 Output:", OUT_PATH.as_posix())

if __name__ == "__main__":
    main()
