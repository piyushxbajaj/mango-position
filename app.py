import streamlit as st
import pandas as pd
from datetime import datetime
import csv
from openpyxl import load_workbook
from io import BytesIO, StringIO

st.title("Net Position Processor & Comparator")

# Upload the two required files
uploaded_excel = st.file_uploader("Upload NetPosition Excel File (.xlsx)", type=["xlsx"])
uploaded_db = st.file_uploader("Upload Comparison CSV File (.csv)", type=["csv"])

if uploaded_excel is not None and uploaded_db is not None:
    # --- FIRST ROW REMOVE CODE ---
    # Read the uploaded Excel file into openpyxl
    excel_bytes = uploaded_excel.read()
    workbook = load_workbook(filename=BytesIO(excel_bytes))
    sheet = workbook.active
    sheet.delete_rows(1)
    output_excel_io = BytesIO()
    workbook.save(output_excel_io)
    st.success("First row removed from Excel file.")

    # --- CONVERT EXCEL TO CSV ---
    output_excel_io.seek(0)
    df_excel = pd.read_excel(output_excel_io)
    csv_buffer = StringIO()
    df_excel.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    df = pd.read_csv(StringIO(csv_buffer.getvalue()))

    # --- GENERATE FORMATTED NAMES ---
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
            raise ValueError("Invalid date format: {}. Expected format is DD-MM-YYYY.".format(exp_date))
        if call_put == "FF":
            suffix = "FUT"
            formatted_strike = ""
        else:
            suffix = call_put
            formatted_strike = str(int(float(strike))) if float(strike).is_integer() else str(float(strike))
        return "{ticker}{year}{month}{strike}{suffix}".format(
            ticker=ticker, year=exp_year, month=exp_month, strike=formatted_strike, suffix=suffix
        )

    df["Formatted Name with Qty"] = df.apply(
        lambda row: "{},{}".format(generate_name(row), int(row["Net Qty"])), axis=1
    )

    # --- SAVE FORMATTED CSV ---
    formatted_output = "formatted_names_with_qty.csv"
    formatted_csv_io = StringIO()
    df.to_csv(formatted_csv_io, columns=["Formatted Name with Qty"], index=False, quoting=csv.QUOTE_NONE, escapechar=" ")
    st.success("Formatted names with quantities generated.")

    # --- CLEAN CSV FILE CODE ---
    formatted_csv_io.seek(0)
    input_csv_io = StringIO(formatted_csv_io.getvalue())
    cleaned_csv_io = StringIO()
    reader = csv.reader(input_csv_io)
    writer = csv.writer(cleaned_csv_io)
    next(reader, None)
    for row in reader:
        cleaned_row = [cell.strip() for cell in row]
        writer.writerow(cleaned_row)
    st.success("Extra spaces removed from CSV.")

    # --- COMPARE INSTRUMENTS AND QUANTITY CODE ---
    def read_file(file_str):
        data = {}
        for line in file_str.splitlines():
            instrument, position = line.strip().split(',')
            data[instrument.strip()] = int(position.strip())
        return data

    # p1_data comes from the cleaned CSV output
    cleaned_csv_io.seek(0)
    p1_data = read_file(cleaned_csv_io.getvalue())

    # p2_data comes from the uploaded comparison CSV file
    db_bytes = uploaded_db.read()
    db_str = db_bytes.decode("utf-8")
    p2_data = read_file(db_str)

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
        st.subheader("Differences Found:")
        diff_list = [{"Instrument": instr, "OMSFile pos": positions[0], "DB pos": positions[1]} 
                    for instr, positions in differences.items()]
        diff_df = pd.DataFrame(diff_list)
        st.table(diff_df)
    else:
        st.subheader("No Differences Found.")

