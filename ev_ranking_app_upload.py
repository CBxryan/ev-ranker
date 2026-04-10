
import streamlit as st
import pandas as pd

st.set_page_config(page_title="EV Worth-It Ranker", layout="wide")

st.title("EV Worth-It Ranker")
st.write("Upload a CSV of EVs sold or announced in Indonesia, adjust your priorities, and rank them from most worth it to least worth it.")

REQUIRED_COLUMNS = [
    "Brand","Model","Status","Segment","Price_IDR","Range_km","Battery_kWh","DC_Charge_kW",
    "AC_Charge_kW","Power_hp","Torque_Nm","Seats","Length_mm","Width_mm","Height_mm",
    "Wheelbase_mm","Ground_Clearance_mm","Warranty_Years","Source_URL","Notes"
]

DEFAULT_ROWS = [
    {
        "Brand": "BYD", "Model": "Seal", "Status": "On sale", "Segment": "Sedan",
        "Price_IDR": 639000000, "Range_km": 650, "Battery_kWh": 82.56, "DC_Charge_kW": None,
        "AC_Charge_kW": None, "Power_hp": None, "Torque_Nm": 670, "Seats": 5,
        "Length_mm": None, "Width_mm": None, "Height_mm": None, "Wheelbase_mm": None,
        "Ground_Clearance_mm": None, "Warranty_Years": None, "Source_URL": "https://www.byd.com/id/pricelist",
        "Notes": "Example row"
    },
    {
        "Brand": "Hyundai", "Model": "KONA Electric", "Status": "On sale", "Segment": "SUV",
        "Price_IDR": 565300000, "Range_km": 600, "Battery_kWh": None, "DC_Charge_kW": None,
        "AC_Charge_kW": None, "Power_hp": None, "Torque_Nm": None, "Seats": 5,
        "Length_mm": None, "Width_mm": None, "Height_mm": None, "Wheelbase_mm": None,
        "Ground_Clearance_mm": None, "Warranty_Years": None, "Source_URL": "https://www.hyundai.com/id/id/find-a-car/all-new-kona-electric/highlights",
        "Notes": "Example row"
    },
    {
        "Brand": "NETA", "Model": "V-II", "Status": "On sale", "Segment": "Small SUV",
        "Price_IDR": 299000000, "Range_km": None, "Battery_kWh": None, "DC_Charge_kW": None,
        "AC_Charge_kW": None, "Power_hp": None, "Torque_Nm": None, "Seats": 5,
        "Length_mm": None, "Width_mm": None, "Height_mm": None, "Wheelbase_mm": None,
        "Ground_Clearance_mm": None, "Warranty_Years": None, "Source_URL": "https://neta.co.id/en/price-list",
        "Notes": "Example row"
    },
]
default_df = pd.DataFrame(DEFAULT_ROWS)
for col in REQUIRED_COLUMNS:
    if col not in default_df.columns:
        default_df[col] = None
default_df = default_df[REQUIRED_COLUMNS]

st.sidebar.header("1) Data source")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    df = df[REQUIRED_COLUMNS]
    st.sidebar.success("CSV loaded.")
else:
    df = default_df.copy()
    st.sidebar.info("No CSV uploaded. Using example rows.")

sample_csv = df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download current table as CSV", data=sample_csv, file_name="ev_data_export.csv", mime="text/csv")

st.sidebar.header("2) Priorities")
weights = {
    "Price_IDR": st.sidebar.slider("Price importance", 0, 30, 20),
    "Range_km": st.sidebar.slider("Range importance", 0, 30, 20),
    "Battery_kWh": st.sidebar.slider("Battery size importance", 0, 20, 10),
    "DC_Charge_kW": st.sidebar.slider("DC charging speed importance", 0, 20, 10),
    "Seats": st.sidebar.slider("Seat count importance", 0, 10, 4),
    "Ground_Clearance_mm": st.sidebar.slider("Ground clearance importance", 0, 10, 3),
    "Warranty_Years": st.sidebar.slider("Warranty importance", 0, 20, 8),
}

st.markdown("### Data editor")
st.write("You can still edit the uploaded rows directly in the app.")
df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

st.markdown("### Filters")
col1, col2, col3 = st.columns(3)
with col1:
    status_filter = st.multiselect("Status", sorted([s for s in df["Status"].dropna().unique()]), default=list(sorted([s for s in df["Status"].dropna().unique()])))
with col2:
    max_budget = st.number_input("Max budget (IDR)", min_value=0, value=10000000000, step=10000000)
with col3:
    min_range = st.number_input("Minimum range (km)", min_value=0, value=0, step=10)

filtered = df.copy()
if status_filter:
    filtered = filtered[filtered["Status"].isin(status_filter)]
filtered["Price_IDR"] = pd.to_numeric(filtered["Price_IDR"], errors="coerce")
filtered["Range_km"] = pd.to_numeric(filtered["Range_km"], errors="coerce")
filtered = filtered[(filtered["Price_IDR"].isna()) | (filtered["Price_IDR"] <= max_budget)]
filtered = filtered[(filtered["Range_km"].isna()) | (filtered["Range_km"] >= min_range)]

def normalize_series(series, higher_is_better=True):
    series = pd.to_numeric(series, errors="coerce")
    valid = series.dropna()
    if len(valid) == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    min_val = valid.min()
    max_val = valid.max()
    if max_val == min_val:
        return pd.Series([10.0 if not pd.isna(v) else 0.0 for v in series], index=series.index)
    if higher_is_better:
        scored = 10 * (series - min_val) / (max_val - min_val)
    else:
        scored = 10 * (max_val - series) / (max_val - min_val)
    return scored.fillna(0.0)

def calculate_scores(data):
    scored = data.copy()
    scored["Score_Price"] = normalize_series(scored["Price_IDR"], higher_is_better=False)
    scored["Score_Range"] = normalize_series(scored["Range_km"], higher_is_better=True)
    scored["Score_Battery"] = normalize_series(scored["Battery_kWh"], higher_is_better=True)
    scored["Score_DC"] = normalize_series(scored["DC_Charge_kW"], higher_is_better=True)
    scored["Score_Seats"] = normalize_series(scored["Seats"], higher_is_better=True)
    scored["Score_GC"] = normalize_series(scored["Ground_Clearance_mm"], higher_is_better=True)
    scored["Score_Warranty"] = normalize_series(scored["Warranty_Years"], higher_is_better=True)

    total_weight = sum(weights.values())
    if total_weight == 0:
        scored["Final_Score"] = 0
    else:
        scored["Final_Score"] = (
            scored["Score_Price"] * weights["Price_IDR"] +
            scored["Score_Range"] * weights["Range_km"] +
            scored["Score_Battery"] * weights["Battery_kWh"] +
            scored["Score_DC"] * weights["DC_Charge_kW"] +
            scored["Score_Seats"] * weights["Seats"] +
            scored["Score_GC"] * weights["Ground_Clearance_mm"] +
            scored["Score_Warranty"] * weights["Warranty_Years"]
        ) / total_weight

    scored = scored.sort_values("Final_Score", ascending=False, na_position="last").reset_index(drop=True)
    scored.index = scored.index + 1
    return scored

st.markdown("### Ranking")
if filtered.empty:
    st.warning("No EVs match your filters.")
else:
    result = calculate_scores(filtered)
    st.dataframe(
        result[[
            "Brand","Model","Status","Segment","Price_IDR","Range_km","Battery_kWh","DC_Charge_kW",
            "Seats","Ground_Clearance_mm","Warranty_Years","Final_Score","Notes","Source_URL"
        ]],
        use_container_width=True
    )

    st.markdown("### Top pick")
    top = result.iloc[0]
    st.success(f"Best match right now: {top['Brand']} {top['Model']} — score {top['Final_Score']:.2f}/10")

    st.markdown("### Quick compare")
    st.write("Rows with a lot of missing specs are still shown, but missing values score as 0 until you fill them in.")

st.markdown("---")
st.caption("Tip: upload the Indonesia EV CSV, edit any missing specs, then re-download the cleaned file.")
