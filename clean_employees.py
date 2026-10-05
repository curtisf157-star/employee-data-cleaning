import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

INPUT  = BASE_DIR / "Messy_Employee_dataset.csv"
OUTPUT = BASE_DIR / "employees_clean.csv"
REPORT = BASE_DIR / "cleaning_report.json"

# ------------------------------------------------------------
# 1. Load CSV
# ------------------------------------------------------------
df = pd.read_csv(
    INPUT,
    na_values=["N/A", "NA", "NULL", "", " "],
    keep_default_na=True
)

# Remove exact duplicate rows, if any
df = df.drop_duplicates()

# ------------------------------------------------------------
# 2. Strip whitespace from text columns
# ------------------------------------------------------------
for col in df.select_dtypes(include=["object", "string"]).columns:
    df[col] = df[col].astype("string").str.strip()

# ------------------------------------------------------------
# 3. Standardize text values
# ------------------------------------------------------------
df["Employee_ID"] = df["Employee_ID"].str.upper()
df["First_Name"] = df["First_Name"].str.title()
df["Last_Name"] = df["Last_Name"].str.title()
df["Status"] = df["Status"].str.title()
df["Performance_Score"] = df["Performance_Score"].str.title()
df["Email"] = df["Email"].str.lower()

# ------------------------------------------------------------
# 4. Split Department_Region into Department and Region
# Example: "Cloud Tech-New York" -> Department="Cloud Tech", Region="New York"
# ------------------------------------------------------------
dept_region = df["Department_Region"].str.split("-", n=1, expand=True)
df["Department"] = dept_region[0].str.strip()
df["Region"] = dept_region[1].str.strip()
df = df.drop(columns=["Department_Region"])

# ------------------------------------------------------------
# 5. Convert Join_Date to datetime
# ------------------------------------------------------------
df["Join_Date"] = pd.to_datetime(
    df["Join_Date"],
    errors="coerce",
    format="%m/%d/%Y"
)

# ------------------------------------------------------------
# 6. Convert Age and Salary to numeric
# ------------------------------------------------------------
df["Age"] = pd.to_numeric(df["Age"], errors="coerce")

df["Salary"] = (
    df["Salary"]
    .astype("string")
    .str.replace(",", "", regex=False)
)
df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")

# Flag missing values before imputation
df["Age_Was_Missing"] = df["Age"].isna()
df["Salary_Was_Missing"] = df["Salary"].isna()

# Optional: fill missing Age with median Age by Department
df["Age"] = df.groupby("Department")["Age"].transform(
    lambda s: s.fillna(s.median())
)
df["Age"] = df["Age"].fillna(df["Age"].median()).round().astype("Int64")

# Optional: fill missing Salary instead of leaving it missing
# df["Salary"] = df.groupby("Department")["Salary"].transform(
#     lambda s: s.fillna(s.median())
# )
# df["Salary"] = df["Salary"].fillna(df["Salary"].median())

# ------------------------------------------------------------
# 7. Clean Phone
# Negative phone numbers appear in the file.
# This keeps digits only: -1651623197 -> 1651623197
# ------------------------------------------------------------
df["Phone"] = (
    df["Phone"]
    .astype("string")
    .str.replace(r"\D", "", regex=True)
)

# ------------------------------------------------------------
# 8. Convert Remote_Work to boolean
# ------------------------------------------------------------
df["Remote_Work"] = (
    df["Remote_Work"]
    .astype("string")
    .str.upper()
    .map({"TRUE": True, "FALSE": False})
    .astype("boolean")
)

# ------------------------------------------------------------
# 9. Validate emails
# ------------------------------------------------------------
email_re = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
df["Email_Valid"] = df["Email"].str.match(email_re, na=False)

# Optional data quality rules
# df.loc[(df["Age"] < 18) | (df["Age"] > 65), "Age"] = pd.NA
# df.loc[df["Salary"] < 0, "Salary"] = pd.NA

# ------------------------------------------------------------
# 10. Reorder columns
# ------------------------------------------------------------
cols = [
    "Employee_ID",
    "First_Name",
    "Last_Name",
    "Age",
    "Age_Was_Missing",
    "Department",
    "Region",
    "Status",
    "Join_Date",
    "Salary",
    "Salary_Was_Missing",
    "Email",
    "Email_Valid",
    "Phone",
    "Performance_Score",
    "Remote_Work",
]

df = df[[c for c in cols if c in df.columns]]

# ------------------------------------------------------------
# 11. Create cleaning report
# ------------------------------------------------------------
report = {
    "rows": len(df),
    "columns": list(df.columns),
    "missing_values": df.isna().sum().to_dict(),
    "duplicate_employee_ids": int(df["Employee_ID"].duplicated().sum()),
    "exact_duplicate_rows": int(df.duplicated().sum()),
    "invalid_emails": int((~df["Email_Valid"]).sum()),
    "departments": sorted(df["Department"].dropna().unique().tolist()),
    "regions": sorted(df["Region"].dropna().unique().tolist()),
    "statuses": sorted(df["Status"].dropna().unique().tolist()),
    "performance_scores": sorted(
        df["Performance_Score"].dropna().unique().tolist()
    ),
}

REPORT.write_text(
    json.dumps(report, indent=2, default=str),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 12. Save cleaned file
# ------------------------------------------------------------
df.to_csv(OUTPUT, index=False)

print(f"Cleaned file saved to: {OUTPUT}")
print(f"Report saved to: {REPORT}")
print(json.dumps(report, indent=2, default=str))