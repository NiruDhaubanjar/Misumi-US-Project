from bs4 import BeautifulSoup
import pandas as pd

def extract_spec_table(soup):
    """
    Extracts key/value pairs from supported spec tables.
    Handles:
    - m-listTable (vertical key/value)
    - m-codeTable (horizontal header/value row)
    """
    # Case 1: m-listTable (key/value format)
    table = soup.find("table", class_="m-listTable m-listTable--adaptive")
    if table:
        row_data = []
        for tr in table.find_all("tr"):
            ths = tr.find_all("th")
            tds = tr.find_all("td")

            for i in range(min(len(ths), len(tds))):
                key = ths[i].get_text(strip=True)
                value = tds[i].get_text(strip=True)
                row_data.extend([key, value])  # alternating key/value

        return row_data

    # Case 2: m-codeTable (horizontal header/value rows, all rows)
    tables = soup.find_all("table", {"class": lambda c: c and "m-codeTable" in c})
    if len(tables) >= 2:
        table = tables[1]   # take the 2nd one
        headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]

        row_data = []
        for row in table.find("tbody").find_all("tr"):
            values = [td.get_text(strip=True) for td in row.find_all("td")]
            for h, v in zip(headers, values):
                row_data.extend([h, v])
        return row_data

    return []

def extract_spec_table_from_html(html_file):
    """
    Reads an HTML file and returns the specification table data
    as a horizontal row.
    """
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    return extract_spec_table(soup)


def extract_alteration_specs(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    # Find the main alteration <ul>
    alteration_ul = soup.find("ul", class_="l-adaptive-navfilterOption", 
                              attrs={"data-spec":"alteration-spec-ul"})
    if not alteration_ul:
        return pd.DataFrame()  # no specs found

    data = []

    # Loop over all <li> blocks
    for li in alteration_ul.find_all("li", class_="m-adaptive-spec-block"):
        # Key: h4 text
        h4 = li.find("h4", class_="m-adaptive-spec-block__title")
        if h4:
            key = h4.get_text(" ", strip=True)
        else:
            key = None

        # Value: try to get input value(s) if present, otherwise empty
        value_div = li.find("div", attrs={"data-spec-filter":"box"})
        value = ""
        if value_div:
            # Try to get all <input> values
            inputs = value_div.find_all("input")
            if inputs:
                input_values = [inp.get("value", "").strip() for inp in inputs if inp.get("value", "").strip()]
                if input_values:
                    value = ", ".join(input_values)
                else:
                    # fallback: get range info
                    ranges = value_div.find_all("span", class_="m-inputText__range")
                    value = ", ".join([r.get_text(strip=True) for r in ranges])
            else:
                # fallback: get all <li class="is-specItem"> inside
                li_items = value_div.find_all("li", class_="is-specItem")
                value = ", ".join([lii.get_text(strip=True) for lii in li_items])

        data.append({"Spec Name": key, "Value": value})

    df = pd.DataFrame(data)
    return df
