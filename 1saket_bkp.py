import pandas as pd
from datetime import datetime
import csv

#FIRST ROW REMOVE CODE
from openpyxl import load_workbook
input_xl_file = "NetPosition.xlsx"  # Input Excel file
output_xl_file = "NetPositionToday.xlsx"  # Output Excel file
workbook = load_workbook(input_xl_file)
sheet = workbook.active
sheet.delete_rows(1)
workbook.save(output_xl_file)

print("First row removed. Cleaned file saved to {}".format(output_xl_file))


# Load the xslx file and update the position on csv file then generate ticker name with quantity
file_path = "NetPositionToday.xlsx"  # Replace with the path to your CSV file
read_excel = pd.read_excel(file_path)  # Assuming the file is tab-delimited
read_excel.to_csv("NetPosition.csv",index=None, header = True)
df = pd.read_csv("NetPosition.csv",delimiter=',')

#names_to_check_file = "/home/prod/ContractFiles/fo_ref_contract_master.csv"

# Function to generate the formatted name
def generate_name(row):
    ticker = row["Scrip"]
    exp_date = row["Exp Date"]
    strike = row["STK"]
    call_put = row["Call/Put"]
    # Parse the expiry date
    try:
        exp_date_obj = datetime.strptime(exp_date, "%d-%m-%Y")  # Convert to datetime
        exp_year = exp_date_obj.strftime("%y")  # Extract last two digits of the year
        exp_month = exp_date_obj.strftime("%b").upper()  # Get abbreviated month name (e.g., NOV)
    except ValueError:
        raise ValueError("Invalid date format: {}. Expected format is DD-MM-YYYY.".format(exp_date))

    # Determine the suffix and handle futures (FF)
    if call_put == "FF":
        suffix = "FUT"
        formatted_strike = ""  # No strike price for futures
    else:
        suffix = call_put
        # Format the strike price (keep integer format if no decimals are needed)
        if float(strike).is_integer():
            formatted_strike = str(int(float(strike)))  # Remove decimals
        else:
            formatted_strike = str(float(strike))  # Keep decimals as is

    # Combine to create the desired name
    return "{ticker}{year}{month}{strike}{suffix}".format(
        ticker=ticker,
        year=exp_year,
        month=exp_month,
        strike=formatted_strike,
        suffix=suffix,
    )

# Apply the function to each row in the DataFrame
df["Formatted Name with Qty"] = df.apply(
    lambda row: "{},{}".format(generate_name(row), int(row["Net Qty"])), axis=1
)

# Save the result to a new file without quotes
output_file = "formatted_names_with_qty.csv"
#df.to_csv(output_file, columns=["Formatted Name with Qty"], index=False, quoting=csv.QUOTE_NONE, escapechar=" ")
df.to_csv(output_file, columns=["Formatted Name with Qty"], index=False, quoting=csv.QUOTE_NONE, escapechar=" ")
print("Formatted names with quantities saved to {}".format(output_file))
 
#CLEAN  CSV FILE CODE
input_csv = "./formatted_names_with_qty.csv"  # Input CSV file
output_csv = "formatted_name_c1.csv"  # Output CSV file with spaces removed

# Remove extra spaces from the CSV
with open(input_csv, "r") as infile, open(output_csv, "w", newline="") as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    next(reader, None)

    for row in reader:
        # Strip extra spaces from each cell in the row
        cleaned_row = [cell.strip() for cell in row]
        writer.writerow(cleaned_row)

print("Extra spaces removed. Cleaned file saved to {}".format(output_csv))


# COMPARE INSTRUMENTS AND QUANTITY CODE

def read_file(filename):
    data = {}
    with open(filename, 'r') as file:
        for line in file:
            instrument, position = line.strip().split(',')
            data[instrument.strip()] = int(position.strip())
    return data

def compare_positions(p1_data, p2_data):
    differences = {}
    all_instruments = set(p1_data.keys()).union(set(p2_data.keys()))

    for instrument in all_instruments:
        pos1 = p1_data.get(instrument)
        pos2 = p2_data.get(instrument)
        #if mapping.get(instrument) is not None and pos1 is not None:
        #pos1 = int(pos1/int(mapping.get(instrument)[1]))
        # Check if positions are different
        if pos1 is not None and pos2 is not None and pos1 != pos2:
            differences[instrument] = (pos1, pos2)
        elif pos1 is None and pos2 is not None and pos2 != 0:
            differences[instrument] = (None, pos2)
        elif pos1 is not None and pos2 is None and pos1 != 0:
            differences[instrument] = (pos1, None)
    print(len(differences))
    return differences



p1_data = read_file('formatted_name_c1.csv')
p2_data = read_file('formatted_name_db.csv')


differences = compare_positions(p1_data, p2_data)


if differences:
    print("Differences found:")
    for instrument, positions in differences.items():
        print("Instrument {}\t {}:          \tOMSFile pos= {}, \tDB pos= {}".format(instrument, instrument, positions[0], positions[1]))

else:
    print("No differences found.")

