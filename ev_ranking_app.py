import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="EV Worth-It Ranker", layout="wide")

REQUIRED_COLUMNS = [
    "Brand", "Model", "Status", "Segment", "Price_IDR", "Range_km", "Battery_kWh", "DC_Charge_kW",
    "AC_Charge_kW", "Power_hp", "Torque_Nm", "Seats", "Length_mm", "Width_mm", "Height_mm",
    "Wheelbase_mm", "Ground_Clearance_mm", "Warranty_Years", "Personal_Rating_10", "Source_URL", "Notes"
]

DEFAULT_ROWS = [
    {
        "Brand": "BYD", "Model": "Dolphin", "Status": "On sale", "Segment": "Hatchback",
        "Price_IDR": 425000000, "Range_km": 410, "Battery_kWh": 44.9, "DC_Charge_kW": 60,
        "AC_Charge_kW": 7, "Power_hp": 94, "Torque_Nm": 180, "Seats": 5,
        "Length_mm": 4290, "Width_mm": 1770, "Height_mm": 1570, "Wheelbase_mm": 2700,
        "Ground_Clearance_mm": 130, "Warranty_Years": 8, "Personal_Rating_10": 7,
        "Source_URL": "", "Notes": "Starter row; replace with your own verified data."
    },
    {
        "Brand": "Wuling", "Model": "Cloud EV", "Status": "On sale", "Segment": "Hatchback",
        "Price_IDR": 398000000, "Range_km": 460, "Battery_kWh": 50.6, "DC_Charge_kW": 50,
        "AC_Charge_kW": 6.6, "Power_hp": 134, "Torque_Nm": 200, "Seats": 5,
        "Length_mm": 4295, "Width_mm": 1850, "Height_mm": 1652, "Wheelbase_mm": 2700,
        "Ground_Clearance_mm": 150, "Warranty_Years": 8, "Personal_Rating_10": 7,
        "Source_URL": "", "Notes": "Starter row; replace with your own verified data."
    },
]

NUMERIC_COLUMNS = [
    "Price_IDR", "Range_km", "Battery_kWh", "DC_Charge_kW", "AC_Charge_kW", "Power_hp", "Torque_Nm",
    "Seats", "Length_mm", "Width_mm", "Height_mm", "Wheelbase_mm", "Ground_Clearance_mm",
    "Warranty_Years", "Personal_Rating_10"
]

st.title("EV Worth-It Ranker")
st.write("Persistent version backed by Google Sheets. Edit the table, press save, and your data stays there.")


@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[REQUIRED_COLUMNS]
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_sheet() -> pd.DataFrame:
    conn = get_connection()
    df = conn.read(worksheet=st.secrets["connections"]["gsheets"]["worksheet"], ttl=0)
    if df is None or df.empty:
        return clean_dataframe(pd.DataFrame(DEFAULT_ROWS))
    return clean_dataframe(df)


def save_sheet(df: pd.DataFrame) -> None:
    conn = get_connection()
    conn.update(
        worksheet=st.secrets["connections"]["gsheets"]["worksheet"],
        data=clean_dataframe(df),
    )


def normalize_series(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce")
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val):
        return pd.Series([0] * len(series), index=series.index)
    if max_val == min_val:
        return pd.Series([10] * len(series), index=series.index)

    if higher_is_better:
        return 10 * (series - min_val) / (max_val - min_val)
    return 10 * (max_val - series) / (max_val - min_val)


def calculate_scores(data: pd.DataFrame, weights: dict) -> pd.DataFrame:
    scored = data.copy()
    scored["Score_Price"] = normalize_series(scored["Price_IDR"], higher_is_better=False)
    scored["Score_Range"] = normalize_series(scored["Range_km"], higher_is_better=True)
    scored["Score_Battery"] = normalize_series(scored["Battery_kWh"], higher_is_better=True)
    scored["Score_DC"] = normalize_series(scored["DC_Charge_kW"], higher_is_better=True)
    scored["Score_AC"] = normalize_series(scored["AC_Charge_kW"], higher_is_better=True)
    scored["Score_Power"] = normalize_series(scored["Power_hp"], higher_is_better=True)
    scored["Score_Torque"] = normalize_series(scored["Torque_Nm"], higher_is_better=True)
    scored["Score_Warranty"] = normalize_series(scored["Warranty_Years"], higher_is_better=True)
    scored["Score_Personal"] = normalize_series(scored["Personal_Rating_10"], higher_is_better=True)

    total_weight = sum(weights.values())
    if total_weight == 0:
        scored["Final_Score"] = 0
        return scored

    scored["Final_Score"] = (
        scored["Score_Price"] * weights["Price_IDR"]
        + scored["Score_Range"] * weights["Range_km"]
        + scored["Score_Battery"] * weights["Battery_kWh"]
        + scored["Score_DC"] * weights["DC_Charge_kW"]
        + scored["Score_AC"] * weights["AC_Charge_kW"]
        + scored["Score_Power"] * weights["Power_hp"]
        + scored["Score_Torque"] * weights["Torque_Nm"]
        + scored["Score_Warranty"] * weights["Warranty_Years"]
        + scored["Score_Personal"] * weights["Personal_Rating_10"]
    ) / total_weight

    scored = scored.sort_values("Final_Score", ascending=False).reset_index(drop=True)
    scored.index = scored.index + 1
    return scored


if "sheet_df" not in st.session_state:
    st.session_state.sheet_df = load_sheet()

st.sidebar.header("Your priorities")
weights = {
    "Price_IDR": st.sidebar.slider("Price importance", 0, 30, 20),
    "Range_km": st.sidebar.slider("Range importance", 0, 30, 20),
    "Battery_kWh": st.sidebar.slider("Battery size importance", 0, 20, 6),
    "DC_Charge_kW": st.sidebar.slider("DC charging importance", 0, 20, 10),
    "AC_Charge_kW": st.sidebar.slider("AC charging importance", 0, 20, 4),
    "Power_hp": st.sidebar.slider("Power importance", 0, 20, 8),
    "Torque_Nm": st.sidebar.slider("Torque importance", 0, 20, 6),
    "Warranty_Years": st.sidebar.slider("Warranty importance", 0, 20, 8),
    "Personal_Rating_10": st.sidebar.slider("Personal feeling importance", 0, 20, 15),
}

st.markdown("### EV database")
st.caption("Edits are local until you press Save changes to Google Sheets.")

edited_df = st.data_editor(
    st.session_state.sheet_df,
    num_rows="dynamic",
    use_container_width=True,
    key="ev_editor",
)

col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    if st.button("Reload from Google Sheets", use_container_width=True):
        st.session_state.sheet_df = load_sheet()
        st.rerun()
with col_b:
    if st.button("Save changes to Google Sheets", type="primary", use_container_width=True):
        try:
            save_sheet(edited_df)
            st.session_state.sheet_df = clean_dataframe(edited_df)
            st.success("Saved to Google Sheets.")
        except Exception as e:
            st.error(f"Save failed: {e}")
with col_c:
    st.write("")

st.markdown("### Filters")
f1, f2, f3 = st.columns(3)
with f1:
    max_budget = st.number_input("Maximum budget (IDR)", min_value=0, value=1500000000, step=10000000)
with f2:
    min_range = st.number_input("Minimum range (km)", min_value=0, value=0, step=10)
with f3:
    status_filter = st.multiselect(
        "Status",
        options=sorted([x for x in edited_df["Status"].dropna().unique().tolist() if str(x).strip()]),
        default=sorted([x for x in edited_df["Status"].dropna().unique().tolist() if str(x).strip()]),
    )

filtered_df = clean_dataframe(edited_df)
filtered_df = filtered_df[filtered_df["Price_IDR"].fillna(0) <= max_budget]
filtered_df = filtered_df[filtered_df["Range_km"].fillna(0) >= min_range]
if status_filter:
    filtered_df = filtered_df[filtered_df["Status"].isin(status_filter)]

st.markdown("### Ranking")
if filtered_df.empty:
    st.warning("No EVs match your current filters.")
else:
    result = calculate_scores(filtered_df, weights)
    st.dataframe(
        result[[
            "Brand", "Model", "Status", "Price_IDR", "Range_km", "Battery_kWh", "DC_Charge_kW",
            "AC_Charge_kW", "Power_hp", "Torque_Nm", "Warranty_Years", "Personal_Rating_10",
            "Final_Score", "Notes"
        ]],
        use_container_width=True,
    )

    top = result.iloc[0]
    st.success(f"Top pick: {top['Brand']} {top['Model']} — {top['Final_Score']:.2f}/10")

st.markdown("---")
st.markdown("### Setup notes")
st.code(
    """[connections.gsheets]\nspreadsheet = \"YOUR_GOOGLE_SHEET_URL\"\nworksheet = \"EVs\"\n\n[gcp_service_account]\ntype = \"service_account\"\nproject_id = \"...\"\nprivate_key_id = \"...\"\nprivate_key = \"-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n\"\nclient_email = \"...\"\nclient_id = \"...\"\nauth_uri = \"https://accounts.google.com/o/oauth2/auth\"\ntoken_uri = \"https://oauth2.googleapis.com/token\"\nauth_provider_x509_cert_url = \"https://www.googleapis.com/oauth2/v1/certs\"\nclient_x509_cert_url = \"...\"\nuniverse_domain = \"googleapis.com\"""",
    language="toml",
)
