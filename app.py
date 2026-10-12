
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="Restaurant Demand Analysis",
    page_icon="🍽️",
    layout="wide"
)

st.title("🍽️ Restaurant Demand Analysis")
st.caption("Identify restaurant demand patterns using historical visitor data")

# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    visits = pd.read_csv("air_visit_data.csv")
    stores = pd.read_csv("air_store_info.csv")
    dates = pd.read_csv("date_info.csv")

    visits["visit_date"] = pd.to_datetime(visits["visit_date"])
    dates["calendar_date"] = pd.to_datetime(dates["calendar_date"])

    visits["day_of_week"] = visits["visit_date"].dt.day_name()
    visits["month"] = visits["visit_date"].dt.month
    visits["month_name"] = visits["visit_date"].dt.month_name()
    visits["is_weekend"] = visits["visit_date"].dt.dayofweek >= 5

    visits = visits.merge(
        dates[["calendar_date", "holiday_flg"]],
        left_on="visit_date",
        right_on="calendar_date",
        how="left"
    )

    visits = visits.merge(stores, on="air_store_id", how="left")

    visits["holiday_flg"] = visits["holiday_flg"].fillna(0).astype(int)

    return visits

try:
    visits = load_data()
except FileNotFoundError as e:
    st.error(f"Missing file: {e.filename}")
    st.info(
        "Upload air_visit_data.csv, air_store_info.csv, "
        "and date_info.csv to your GitHub repository."
    )
    st.stop()

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("Dashboard Filters")

min_date = visits["visit_date"].min().date()
max_date = visits["visit_date"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

store_options = sorted(visits["air_store_id"].unique())

selected_stores = st.sidebar.multiselect(
    "Select restaurants",
    options=store_options,
    default=[]
)

filtered = visits.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["visit_date"].dt.date.between(start_date, end_date)
    ]

if selected_stores:
    filtered = filtered[
        filtered["air_store_id"].isin(selected_stores)
    ]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

# ---------------- KEY METRICS ----------------
total_visitors = int(filtered["visitors"].sum())
average_visitors = filtered["visitors"].mean()
restaurant_count = filtered["air_store_id"].nunique()
record_count = len(filtered)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Visitors", f"{total_visitors:,}")
c2.metric("Average Visitors / Record", f"{average_visitors:.2f}")
c3.metric("Restaurants", f"{restaurant_count:,}")
c4.metric("Visitor Records", f"{record_count:,}")

st.divider()

# ---------------- DAILY DEMAND ----------------
st.subheader("1. Daily Demand Trend")

daily = (
    filtered.groupby("visit_date", as_index=False)["visitors"]
    .sum()
)

fig_daily = px.line(
    daily,
    x="visit_date",
    y="visitors",
    markers=True,
    title="Total Restaurant Visitors by Date",
    labels={
        "visit_date": "Date",
        "visitors": "Total Visitors"
    }
)

st.plotly_chart(fig_daily, use_container_width=True)

# ---------------- WEEKLY DEMAND ----------------
left, right = st.columns(2)

day_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

weekly = (
    filtered.groupby("day_of_week", as_index=False)["visitors"]
    .mean()
)

weekly["day_of_week"] = pd.Categorical(
    weekly["day_of_week"],
    categories=day_order,
    ordered=True
)
weekly = weekly.sort_values("day_of_week")

with left:
    st.subheader("2. Demand by Weekday")
    fig_week = px.bar(
        weekly,
        x="day_of_week",
        y="visitors",
        labels={
            "day_of_week": "Day",
            "visitors": "Average Visitors"
        }
    )
    st.plotly_chart(fig_week, use_container_width=True)

# ---------------- WEEKDAY VS WEEKEND ----------------
filtered = filtered.copy()
filtered["day_type"] = filtered["is_weekend"].map(
    {False: "Weekday", True: "Weekend"}
)

weekend = (
    filtered.groupby("day_type", as_index=False)["visitors"]
    .mean()
)

with right:
    st.subheader("3. Weekday vs Weekend")
    fig_weekend = px.bar(
        weekend,
        x="day_type",
        y="visitors",
        color="day_type",
        labels={
            "day_type": "Day Type",
            "visitors": "Average Visitors"
        }
    )
    st.plotly_chart(fig_weekend, use_container_width=True)

# ---------------- MONTHLY DEMAND ----------------
st.subheader("4. Monthly Demand Pattern")

month_order = [
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December"
]

monthly = (
    filtered.groupby(["month", "month_name"], as_index=False)["visitors"]
    .mean()
    .sort_values("month")
)

fig_month = px.line(
    monthly,
    x="month_name",
    y="visitors",
    markers=True,
    category_orders={"month_name": month_order},
    labels={
        "month_name": "Month",
        "visitors": "Average Visitors"
    }
)

st.plotly_chart(fig_month, use_container_width=True)

if not monthly.empty:
    busiest_month = monthly.loc[monthly["visitors"].idxmax(), "month_name"]
    quietest_month = monthly.loc[monthly["visitors"].idxmin(), "month_name"]

    a, b = st.columns(2)
    a.info(f"Highest average demand month: {busiest_month}")
    b.info(f"Lowest average demand month: {quietest_month}")

# ---------------- RESTAURANT COMPARISON ----------------
st.subheader("5. Restaurant Demand Comparison")

restaurant_demand = (
    filtered.groupby("air_store_id", as_index=False)
    .agg(
        average_visitors=("visitors", "mean"),
        total_visitors=("visitors", "sum"),
        recorded_days=("visitors", "count")
    )
)

top_n = st.slider(
    "Number of restaurants to display",
    min_value=5,
    max_value=20,
    value=10
)

top_restaurants = restaurant_demand.nlargest(
    top_n, "average_visitors"
).sort_values("average_visitors")

fig_restaurants = px.bar(
    top_restaurants,
    x="average_visitors",
    y="air_store_id",
    orientation="h",
    hover_data=["total_visitors", "recorded_days"],
    labels={
        "air_store_id": "Restaurant",
        "average_visitors": "Average Visitors"
    }
)

st.plotly_chart(fig_restaurants, use_container_width=True)

st.caption(
    "Restaurants may have different numbers of recorded days. "
    "Compare averages and recorded-day counts when interpreting results."
)

# ---------------- HOLIDAY ANALYSIS ----------------
st.subheader("6. Holiday vs Non-Holiday Demand")

filtered["day_category"] = filtered["holiday_flg"].map(
    {0: "Non-Holiday", 1: "Holiday"}
)

holiday = (
    filtered.groupby("day_category", as_index=False)["visitors"]
    .mean()
)

fig_holiday = px.bar(
    holiday,
    x="day_category",
    y="visitors",
    color="day_category",
    labels={
        "day_category": "Date Type",
        "visitors": "Average Visitors"
    }
)

st.plotly_chart(fig_holiday, use_container_width=True)

# ---------------- HIGH DEMAND RECORDS ----------------
st.subheader("7. Unusually High-Demand Records")

q1 = filtered["visitors"].quantile(0.25)
q3 = filtered["visitors"].quantile(0.75)
iqr = q3 - q1
upper_bound = q3 + 1.5 * iqr

high_demand = filtered[
    filtered["visitors"] > upper_bound
].sort_values("visitors", ascending=False)

st.write(f"High-demand threshold: {upper_bound:.2f} visitors")
st.write(f"Records above threshold: {len(high_demand):,}")

st.dataframe(
    high_demand[
        ["air_store_id", "visit_date", "visitors", "day_of_week"]
    ].head(20),
    use_container_width=True
)

# ---------------- DATA DOWNLOAD ----------------
st.subheader("8. Download Filtered Data")

csv = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download filtered data as CSV",
    data=csv,
    file_name="restaurant_demand_analysis.csv",
    mime="text/csv"
)

st.success("Restaurant Demand Analysis dashboard loaded successfully!")
