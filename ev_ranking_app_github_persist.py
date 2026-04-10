import io
import base64
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="EV Worth-It Ranker", layout="wide")

REQUIRED_COLUMNS = [
    "Brand", "Model", "Status", "Segment", "Price_IDR", "Range_km", "Battery_kWh",
    "DC_Charge_kW", "AC_Charge_kW", "Power_hp", "Torque_Nm", "Seats", "Length_mm",
    "Width_mm", "Height_mm", "Wheelbase_mm", "Ground_Clearance_mm", "Warranty_Years",
    "Personal_Rating_10", "Source_URL", "Notes"
]

DEFAULT_ROWS = [{
    "Brand": "BYD", "Model": "Dolphin", "Status": "On sale", "Segment": "Hatchback",
    "Price_IDR": 425000000, "Range_km": 410, "Battery_kWh": 44.9, "DC_Charge_kW": 60,
    "AC_Charge_kW": 7, "Power_hp": 95, "Torque_Nm": 180, "Seats": 5, "Length_mm": 4290,
    "Width_mm": 1770, "Height_mm": 1570, "Wheelbase_mm": 2700, "Ground_Clearance_mm": 130,
    "Warranty_Years": 8, "Personal_Rating_10": 7, "Source_URL": "", "Notes": "Starter example row"
}]

def ensure_columns(df):
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REQUIRED_COLUMNS]

def github_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

def github_get_file(owner, repo, path, branch, token):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.get(url, headers=github_headers(token), params={"ref": branch}, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()

def load_data(owner, repo, path, branch, token):
    file_json = github_get_file(owner, repo, path, branch, token)
    if file_json is None:
        return ensure_columns(pd.DataFrame(DEFAULT_ROWS))
    content = base64.b64decode(file_json["content"]).decode("utf-8")
    return ensure_columns(pd.read_csv(io.StringIO(content)))

def save_data(df, owner, repo, path, branch, token, commit_message):
    existing = github_get_file(owner, repo, path, branch, token)
    sha = existing["sha"] if existing else None
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    payload = {
        "message": commit_message,
        "content": base64.b64encode(csv_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    r = requests.put(url, headers=github_headers(token), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

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
    return 10 * (max_val - series) / (max_val - min_val)

def calculate_scores(data, weights):
    scored = data.copy()
    scored["Score_Price"] = normalize_series(scored["Price_IDR"], False)
    scored["Score_Range"] = normalize_series(scored["Range_km"], True)
    scored["Score_Battery"] = normalize_series(scored["Battery_kWh"], True)
    scored["Score_DC"] = normalize_series(scored["DC_Charge_kW"], True)
    scored["Score_AC"] = normalize_series(scored["AC_Charge_kW"], True)
    scored["Score_Power"] = normalize_series(scored["Power_hp"], True)
    scored["Score_Torque"] = normalize_series(scored["Torque_Nm"], True)
    scored["Score_GC"] = normalize_series(scored["Ground_Clearance_mm"], True)
    scored["Score_Warranty"] = normalize_series(scored["Warranty_Years"], True)
    scored["Score_Personal"] = normalize_series(scored["Personal_Rating_10"], True)

    total_weight = sum(weights.values())
    if total_weight == 0:
        scored["Final_Score"] = 0
        return scored

    scored["Final_Score"] = (
        scored["Score_Price"] * weights["Price_IDR"] +
        scored["Score_Range"] * weights["Range_km"] +
        scored["Score_Battery"] * weights["Battery_kWh"] +
        scored["Score_DC"] * weights["DC_Charge_kW"] +
        scored["Score_AC"] * weights["AC_Charge_kW"] +
        scored["Score_Power"] * weights["Power_hp"] +
        scored["Score_Torque"] * weights["Torque_Nm"] +
        scored["Score_GC"] * weights["Ground_Clearance_mm"] +
        scored["Score_Warranty"] * weights["Warranty_Years"] +
        scored["Score_Personal"] * weights["Personal_Rating_10"]
    ) / total_weight

    scored = scored.sort_values("Final_Score", ascending=False).reset_index(drop=True)
    scored.index = scored.index + 1
    return scored

st.title("EV Worth-It Ranker")
st.write("Persistent version: loads from and saves to a CSV file in your GitHub repository.")

st.sidebar.header("GitHub persistence")
owner = st.sidebar.text_input("GitHub owner", value=st.secrets.get("github_owner", "CBxryan"))
repo = st.sidebar.text_input("Repo", value=st.secrets.get("github_repo", "ev-ranker"))
branch = st.sidebar.text_input("Branch", value=st.secrets.get("github_branch", "main"))
csv_path = st.sidebar.text_input("CSV path in repo", value=st.secrets.get("github_csv_path", "ev_indonesia_dataset.csv"))
token = st.sidebar.text_input("GitHub token", value=st.secrets.get("github_token", ""), type="password")

st.sidebar.header("Ranking weights")
weights = {
    "Price_IDR": st.sidebar.slider("Price", 0, 30, 20),
    "Range_km": st.sidebar.slider("Range", 0, 30, 20),
    "Battery_kWh": st.sidebar.slider("Battery size", 0, 20, 10),
    "DC_Charge_kW": st.sidebar.slider("DC charging", 0, 20, 10),
    "AC_Charge_kW": st.sidebar.slider("AC charging", 0, 20, 5),
    "Power_hp": st.sidebar.slider("Power", 0, 20, 5),
    "Torque_Nm": st.sidebar.slider("Torque", 0, 20, 5),
    "Ground_Clearance_mm": st.sidebar.slider("Ground clearance", 0, 20, 5),
    "Warranty_Years": st.sidebar.slider("Warranty", 0, 20, 5),
    "Personal_Rating_10": st.sidebar.slider("Personal feeling", 0, 20, 15),
}

if not token:
    st.warning("Add a GitHub token in Streamlit secrets or in the sidebar to load and save persistently.")
    df = ensure_columns(pd.DataFrame(DEFAULT_ROWS))
else:
    try:
        df = load_data(owner, repo, csv_path, branch, token)
        st.success(f"Loaded data from {owner}/{repo}:{csv_path}")
    except Exception as e:
        st.error(f"Failed to load from GitHub: {e}")
        df = ensure_columns(pd.DataFrame(DEFAULT_ROWS))

st.markdown("### Edit EV database")
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="ev_editor")

col1, col2, col3 = st.columns(3)
with col1:
    max_budget = st.number_input("Maximum budget (IDR)", min_value=0, value=2000000000, step=10000000)
with col2:
    min_range = st.number_input("Minimum range (km)", min_value=0, value=0, step=10)
with col3:
    status_values = [x for x in edited_df["Status"].astype(str).unique() if x]
    status_filter = st.selectbox("Status filter", ["All"] + sorted(status_values))

filtered = edited_df.copy()
filtered["Price_IDR"] = pd.to_numeric(filtered["Price_IDR"], errors="coerce")
filtered["Range_km"] = pd.to_numeric(filtered["Range_km"], errors="coerce")
filtered = filtered[(filtered["Price_IDR"].fillna(0) <= max_budget) & (filtered["Range_km"].fillna(0) >= min_range)]
if status_filter != "All":
    filtered = filtered[filtered["Status"].astype(str) == status_filter]

st.markdown("### Ranking")
if filtered.empty:
    st.info("No rows match the current filters.")
else:
    result = calculate_scores(filtered, weights)
    st.dataframe(result[[
        "Brand", "Model", "Status", "Segment", "Price_IDR", "Range_km", "Battery_kWh",
        "DC_Charge_kW", "AC_Charge_kW", "Power_hp", "Torque_Nm", "Ground_Clearance_mm",
        "Warranty_Years", "Personal_Rating_10", "Final_Score", "Notes"
    ]], use_container_width=True)
    top = result.iloc[0]
    st.success(f"Top pick: {top['Brand']} {top['Model']} — {top['Final_Score']:.2f}/10")

st.markdown("### Save")
commit_message = st.text_input("Commit message", value="Update EV dataset from Streamlit app")
if st.button("Save changes to GitHub"):
    if not token:
        st.error("GitHub token is required.")
    else:
        try:
            to_save = ensure_columns(pd.DataFrame(edited_df))
            save_data(to_save, owner, repo, csv_path, branch, token, commit_message)
            st.success("Saved to GitHub successfully.")
        except Exception as e:
            st.error(f"Save failed: {e}")

st.markdown("---")
st.caption("Recommended: store github_token in Streamlit Secrets, not directly in the sidebar.")
