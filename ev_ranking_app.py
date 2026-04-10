import streamlit as st
import pandas as pd

st.set_page_config(page_title="EV Worth-It Ranker", layout="wide")

st.title("EV Worth-It Ranker")
st.write("Enter electric vehicle data, choose your priorities, and rank EVs from most worth it to least worth it.")

st.markdown("### How scoring works")
st.write(
    "Higher is better for: range, efficiency, charging, safety, cargo, acceleration, warranty, and your personal rating. "
    "Lower is better for: price."
)

# ---------------------------
# Default EV data
# ---------------------------
default_data = pd.DataFrame([
    {
        "Model": "BYD Dolphin",
        "Price_IDR": 425000000,
        "Range_km": 410,
        "Efficiency_km_per_kWh": 6.2,
        "DC_Charge_kW": 60,
        "Safety_10": 8,
        "Cargo_L": 345,
        "Acceleration_0_100_sec": 10.9,
        "Warranty_Years": 8,
        "Personal_Rating_10": 7,
        "Notes": "Affordable city EV"
    },
    {
        "Model": "Wuling BinguoEV",
        "Price_IDR": 370000000,
        "Range_km": 410,
        "Efficiency_km_per_kWh": 5.8,
        "DC_Charge_kW": 50,
        "Safety_10": 7,
        "Cargo_L": 310,
        "Acceleration_0_100_sec": 12.0,
        "Warranty_Years": 8,
        "Personal_Rating_10": 7,
        "Notes": "Cute styling, city use"
    },
    {
        "Model": "Hyundai Ioniq 5",
        "Price_IDR": 800000000,
        "Range_km": 451,
        "Efficiency_km_per_kWh": 5.0,
        "DC_Charge_kW": 220,
        "Safety_10": 9,
        "Cargo_L": 527,
        "Acceleration_0_100_sec": 7.4,
        "Warranty_Years": 8,
        "Personal_Rating_10": 9,
        "Notes": "Premium feel and very fast charging"
    }
])

# ---------------------------
# Sidebar weights
# ---------------------------
st.sidebar.header("Your priorities")
price_weight = st.sidebar.slider("Price importance", 0, 30, 20)
range_weight = st.sidebar.slider("Range importance", 0, 30, 20)
eff_weight = st.sidebar.slider("Efficiency importance", 0, 20, 10)
charge_weight = st.sidebar.slider("Charging speed importance", 0, 20, 10)
safety_weight = st.sidebar.slider("Safety importance", 0, 20, 10)
cargo_weight = st.sidebar.slider("Cargo importance", 0, 20, 5)
accel_weight = st.sidebar.slider("Acceleration importance", 0, 20, 5)
warranty_weight = st.sidebar.slider("Warranty importance", 0, 20, 5)
personal_weight = st.sidebar.slider("Personal feeling importance", 0, 20, 15)

weights = {
    "Price_IDR": price_weight,
    "Range_km": range_weight,
    "Efficiency_km_per_kWh": eff_weight,
    "DC_Charge_kW": charge_weight,
    "Safety_10": safety_weight,
    "Cargo_L": cargo_weight,
    "Acceleration_0_100_sec": accel_weight,
    "Warranty_Years": warranty_weight,
    "Personal_Rating_10": personal_weight,
}

# ---------------------------
# Data entry
# ---------------------------
st.markdown("### EV data input")
st.write("You can edit the sample rows, add your own EVs, or delete rows.")

df = st.data_editor(
    default_data,
    num_rows="dynamic",
    use_container_width=True,
    key="ev_editor"
)

# ---------------------------
# Filters
# ---------------------------
st.markdown("### Filters")
col1, col2 = st.columns(2)
with col1:
    max_budget = st.number_input("Maximum budget (IDR)", min_value=0, value=1000000000, step=10000000)
with col2:
    min_range = st.number_input("Minimum range (km)", min_value=0, value=0, step=10)

filtered_df = df.copy()
filtered_df = filtered_df[filtered_df["Price_IDR"] <= max_budget]
filtered_df = filtered_df[filtered_df["Range_km"] >= min_range]

# ---------------------------
# Scoring helpers
# ---------------------------
def normalize_series(series, higher_is_better=True):
    series = pd.to_numeric(series, errors="coerce")
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val):
        return pd.Series([0] * len(series), index=series.index)

    if max_val == min_val:
        return pd.Series([10] * len(series), index=series.index)

    if higher_is_better:
        return 10 * (series - min_val) / (max_val - min_val)
    else:
        return 10 * (max_val - series) / (max_val - min_val)


def calculate_scores(data):
    scored = data.copy()

    scored["Score_Price"] = normalize_series(scored["Price_IDR"], higher_is_better=False)
    scored["Score_Range"] = normalize_series(scored["Range_km"], higher_is_better=True)
    scored["Score_Efficiency"] = normalize_series(scored["Efficiency_km_per_kWh"], higher_is_better=True)
    scored["Score_Charging"] = normalize_series(scored["DC_Charge_kW"], higher_is_better=True)
    scored["Score_Safety"] = normalize_series(scored["Safety_10"], higher_is_better=True)
    scored["Score_Cargo"] = normalize_series(scored["Cargo_L"], higher_is_better=True)
    scored["Score_Acceleration"] = normalize_series(scored["Acceleration_0_100_sec"], higher_is_better=False)
    scored["Score_Warranty"] = normalize_series(scored["Warranty_Years"], higher_is_better=True)
    scored["Score_Personal"] = normalize_series(scored["Personal_Rating_10"], higher_is_better=True)

    total_weight = sum(weights.values())
    if total_weight == 0:
        scored["Final_Score"] = 0
        return scored

    scored["Final_Score"] = (
        scored["Score_Price"] * weights["Price_IDR"] +
        scored["Score_Range"] * weights["Range_km"] +
        scored["Score_Efficiency"] * weights["Efficiency_km_per_kWh"] +
        scored["Score_Charging"] * weights["DC_Charge_kW"] +
        scored["Score_Safety"] * weights["Safety_10"] +
        scored["Score_Cargo"] * weights["Cargo_L"] +
        scored["Score_Acceleration"] * weights["Acceleration_0_100_sec"] +
        scored["Score_Warranty"] * weights["Warranty_Years"] +
        scored["Score_Personal"] * weights["Personal_Rating_10"]
    ) / total_weight

    scored = scored.sort_values("Final_Score", ascending=False).reset_index(drop=True)
    scored.index = scored.index + 1
    return scored

# ---------------------------
# Output
# ---------------------------
st.markdown("### Ranking")
if filtered_df.empty:
    st.warning("No EVs match your filters.")
else:
    result = calculate_scores(filtered_df)

    st.dataframe(
        result[[
            "Model", "Price_IDR", "Range_km", "Efficiency_km_per_kWh", "DC_Charge_kW",
            "Safety_10", "Cargo_L", "Acceleration_0_100_sec", "Warranty_Years",
            "Personal_Rating_10", "Final_Score", "Notes"
        ]],
        use_container_width=True
    )

    st.markdown("### Top pick")
    top = result.iloc[0]
    st.success(
        f"Best match right now: {top['Model']} | Final Score: {top['Final_Score']:.2f}/10"
    )

    st.markdown("### Why this ranking makes sense")
    for idx, row in result.iterrows():
        st.write(
            f"**#{idx} {row['Model']}** — Score {row['Final_Score']:.2f}/10 | "
            f"Price: IDR {row['Price_IDR']:,} | Range: {row['Range_km']} km | "
            f"Charging: {row['DC_Charge_kW']} kW | Personal rating: {row['Personal_Rating_10']}/10"
        )

st.markdown("---")
st.caption("Next upgrade ideas: charging time calculation, battery size, AC charging speed, brand resale score, maintenance estimate, and comparison charts.")
