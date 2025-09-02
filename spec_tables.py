from bs4 import BeautifulSoup
import pandas as pd

def extract_all_tables(html_file):
    """
    Extracts ALL tables from an HTML file and returns them as a list of DataFrames.
    Handles:
    - Tables with <thead> headers
    - Tables where the first row is headers
    - Tables with rowspan/colspan (flattened by repeating values)
    """
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    tables = []
    for table in soup.find_all("table"):
        # --- Extract headers ---
        headers = []
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        else:
            first_row = table.find("tr")
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all("th")]

        # --- Extract rows with rowspan/colspan handling ---
        rows = []
        occupied = {}  # (row_idx, col_idx) -> value for rowspans
        trs = table.find_all("tr")
        start_idx = 1 if headers else 0

        for r_idx, tr in enumerate(trs[start_idx:], start=0):
            row = []
            col_idx = 0
            for cell in tr.find_all(["td", "th"]):
                # Fill cells already occupied by rowspan from previous rows
                while (r_idx, col_idx) in occupied:
                    row.append(occupied[(r_idx, col_idx)])
                    col_idx += 1

                value = cell.get_text(" ", strip=True)
                rowspan = int(cell.get("rowspan", 1))
                colspan = int(cell.get("colspan", 1))

                # Add value multiple times for colspan
                for j in range(colspan):
                    row.append(value)
                

                # Track rowspan/colspan
                for i in range(rowspan):
                    for j in range(colspan):
                        if i == 0 and j == 0:
                            continue  # skip the top-left cell
                        occupied[(r_idx + i, col_idx + j)] = value

                # Move col_idx forward by colspan
                col_idx += colspan

            # Fill any remaining occupied cells at the end
            while (r_idx, col_idx) in occupied:
                row.append(occupied[(r_idx, col_idx)])
                col_idx += 1

            rows.append(row)

        # Fix mismatched header/data lengths
        if headers and rows and len(headers) != len(rows[0]):
            headers = [f"Col{i+1}" for i in range(len(rows[0]))]

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=headers if headers else None)
        tables.append(df)

    return tables
