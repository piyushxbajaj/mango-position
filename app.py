import pandas as pd
from datetime import datetime
import csv
import streamlit as st
from openpyxl import load_workbook

st.title("Position Mismatch Checker")

# Upload files via Streamlit
file1 = st.file_uploader("Upload NetPosition Excel File (xlsx)", type=["xlsx"])
file2 = st.file_uploader("Upload Database CSV File", type=["csv"])

if file1 and file2:
    # Process first file (Remove first row & convert to CSV)
    workbook = load_workbook(file1)
    sheet = workbook.active
    sheet.delete_rows(1)
    
    output_xl_file = "NetPositionToday.xlsx"
    workbook.save(output_xl_file)
    
    st.success("First row removed. Cleaned file saved.")

    # Convert Excel to CSV
    df = pd.read_excel(output_xl_file)
    df.to_csv("NetPosition.csv", index=False)
    
    st.write("Converted Excel to CSV:")
    st.dataframe(df.head())

    # Function to generate formatted name
    def generate_name(row):
        ticker = row["Scrip"]
        exp_date = row["Exp Date"]
        strike = row["STK"]
        call_put = row["Call/Put"]
        try:
            exp_date_obj = datetime.strptime(exp_date, "%d-%m-%Y")
            exp_year = exp_date_obj.strftime("%y")
            exp_month = exp_date_obj.strftime("%b").upper()
        except ValueError:
            return "Invalid Date"

        suffix = "FUT" if call_put == "FF" else call_put
        formatted_strike = str(int(float(strike))) if float(strike).is_integer() else str(float(strike))

        return f"{ticker}{exp_year}{exp_month}{formatted_strike}{suffix}"

    # Generate formatted names
    df["Formatted Name with Qty"] = df.apply(lambda row: f"{generate_name(row)},{int(row['Net Qty'])}", axis=1)
    
    # Save formatted CSV
    formatted_output = "formatted_names_with_qty.csv"
    df.to_csv(formatted_output, columns=["Formatted Name with Qty"], index=False, quoting=csv.QUOTE_NONE)

    st.success("Formatted names generated.")
    st.download_button("Download Formatted CSV", open(formatted_output, "rb"), formatted_output)

    # Clean CSV file (Remove extra spaces)
    cleaned_output = "formatted_name_c1.csv"
    with open(formatted_output, "r") as infile, open(cleaned_output, "w", newline="") as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        next(reader, None)
        for row in reader:
            writer.writerow([cell.strip() for cell in row])

    st.success("Extra spaces removed from CSV.")

    # Compare positions
    def read_file(file):
        data = {}
        with open(file, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    instrument, position = parts
                    data[instrument.strip()] = int(position.strip())
        return data

    # Read second uploaded file for comparison
    p1_data = read_file(cleaned_output)
    p2_data = read_file(file2)

    def compare_positions(p1_data, p2_data):
        differences = {}
        all_instruments = set(p1_data.keys()).union(set(p2_data.keys()))
        for instrument in all_instruments:
            pos1 = p1_data.get(instrument)
            pos2 = p2_data.get(instrument)
            if pos1 is not None and pos2 is not None and pos1 != pos2:
                differences[instrument] = (pos1, pos2)
            elif pos1 is None and pos2 is not None and pos2 != 0:
                differences[instrument] = (None, pos2)
            elif pos1 is not None and pos2 is None and pos1 != 0:
                differences[instrument] = (pos1, None)
        return differences

    differences = compare_positions(p1_data, p2_data)

    if differences:
        st.warning("Differences found!")
        diff_df = pd.DataFrame.from_dict(differences, orient='index', columns=["OMS File Pos", "DB Pos"])
        st.dataframe(diff_df)
    else:
        st.success("No differences found!")

