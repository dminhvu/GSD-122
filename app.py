import io

import pandas as pd
import streamlit as st

# Set app title
st.set_page_config(page_title="GSD-122: Bakery Republic")
st.title("GSD-122: Bakery Republic")


def process_file(file):
    # Determine file type and read accordingly
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file, skip_blank_lines=True)
    elif file.name.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(file, skip_blank_lines=True)
    else:
        st.error("Unsupported file format. Please upload a CSV or Excel file.")
        return None

    # Check if the dataframe is empty
    if df.empty:
        st.error("The uploaded file is empty.")
        return None

    # Skip header rows until we find the actual header row with "Name"
    header_row_index = None
    for i, row in df.iterrows():
        # Check if this row contains "Name" in the first column
        if isinstance(row.iloc[0], str) and row.iloc[0] == "Name":
            header_row_index = i
            break

    if header_row_index is None:
        st.error("Could not find the header row with 'Name' in the file.")
        return None

    # Reset the dataframe to use the identified header row
    # Get the header row
    header = df.iloc[header_row_index]
    # Get the data rows (everything after the header)
    data = df.iloc[header_row_index + 1 :]
    # Create a new dataframe with the correct header
    df = pd.DataFrame(data.values, columns=header)

    # Rename columns to match the expected output format
    column_mapping = {
        "Name": "Debtor Reference",
        "Transaction type": "Transaction Type",
        "No.": "Document Number",
        "Date": "Document Date",
        "Open balance": "Document Balance",
    }
    df = df.rename(columns=column_mapping)

    # Process the data according to requirements

    # 0. Remove rows where at least one field is empty
    df = df.dropna(how="any")

    # 0.1. Ignore rows from "TOTAL" and below
    total_row_index = df[df["Debtor Reference"] == "TOTAL"].index
    if not total_row_index.empty:
        df = df.iloc[: total_row_index[0]]

    # 1. Remove rows with "Open balance" = 0
    # First clean the Document Balance column
    df["Document Balance"] = (
        df["Document Balance"].astype(str).str.replace(",", "").str.replace('"', "")
    )
    # Then filter out zero values
    df = df[df["Document Balance"].astype(float) != 0]

    # 2. Remove redundant apostrophes from Document Number
    df["Document Number"] = df["Document Number"].str.replace("'", "")

    # 3. Convert Transaction Type values
    transaction_type_mapping = {"Invoice": "INV", "Credit Note": "CRD"}
    df["Transaction Type"] = df["Transaction Type"].map(
        lambda x: transaction_type_mapping.get(x, x)
    )

    # 4. Format Document Date as dd/mm/yyyy
    def format_date(date_str):
        try:
            # Try to parse the date
            date_obj = pd.to_datetime(date_str, dayfirst=True)
            # Format as dd/mm/yyyy
            return date_obj.strftime("%d/%m/%Y")
        except Exception:
            # Return original if parsing fails
            return date_str

    df["Document Date"] = df["Document Date"].apply(format_date)

    # 5. Format Document Balance to have 2 decimal places and make negative if Transaction Type is CRD
    def format_balance(balance_str, transaction_type):
        # Remove quotes and commas (already done above)
        try:
            balance_value = float(balance_str)
            return f"{balance_value:.2f}"
        except Exception:
            return balance_str

    df["Document Balance"] = df.apply(
        lambda row: format_balance(row["Document Balance"], row["Transaction Type"]),
        axis=1,
    )

    # 5.1. Set Transaction Type to CRD if Open Balance is negative
    df["Transaction Type"] = df.apply(
        lambda row: "CRD" if float(row["Document Balance"]) < 0 else "INV",
        axis=1,
    )

    # 6. Reorder columns
    result_df = df[
        [
            "Debtor Reference",
            "Transaction Type",
            "Document Number",
            "Document Date",
            "Document Balance",
        ]
    ]

    # 7. Reset the index
    result_df = result_df.reset_index(drop=True)

    return result_df


def get_csv_download_link(df):
    # Generate CSV file for download
    csv = df.to_csv(index=False)
    csv_bytes = csv.encode()
    buffer = io.BytesIO(csv_bytes)
    return buffer


# File uploader
st.write("Upload your Excel or CSV file:")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    # Process the file
    processed_df = process_file(uploaded_file)

    if processed_df is not None:
        # Display the processed data
        st.write("Processed Data:")
        st.dataframe(processed_df)

        # Download button
        csv_buffer = get_csv_download_link(processed_df)
        st.download_button(
            label="Download Processed File",
            data=csv_buffer,
            file_name="processed_data.csv",
            mime="text/csv",
        )
