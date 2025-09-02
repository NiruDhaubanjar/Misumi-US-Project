def extract_title(soup):
    # Try multiple options
    title_tag = soup.find("h1", class_="m-h1 m-adaptive-product__title") \
        or soup.find("h1", class_="product-title") \
        or soup.find("h1")
    return {"key": "title", "value": title_tag.get_text(strip=True) if title_tag else ""}

def extract_subtitle(soup):
    subtitle_tag = soup.find("h2", class_="m-adaptive-product__subtitle") \
        or soup.find("h2", class_="product-subtitle") \
        or soup.find("h2")
    return {"key": "subtitle", "value": subtitle_tag.get_text(strip=True) if subtitle_tag else ""}

def extract_part_number(soup):
    tag = soup.find(lambda t: t.name in ["p", "span", "div"] and "Part Number:" in t.get_text())
    return {"key": "part_number", "value": tag.get_text(strip=True).replace("Part Number:", "").strip() if tag else ""}

def extract_description(soup):
    """
    Extracts the product description from <p class="mc-text catch_copy">
    Returns an empty string if not found.
    """
    desc_tag = soup.find("p", class_="mc-text catch_copy")
    return {"key": "description", "value": desc_tag.get_text(strip=True) if desc_tag else ""}

def extract_volume_discount_table(soup):
    """
    Extracts Quantity, Price, and Ship Date from a proper Volume Discount table.
    Returns a list of dicts, or [] if no valid table found.
    """
    # Try finding by known summary/class first
    table = soup.find("table", class_="m-table", summary="Volume Discount")

    # Fallback: look for tables that explicitly have Quantity/Price/Ship Date headers
    if not table:
        for candidate in soup.find_all("table"):
            headers = [th.get_text(strip=True).lower() for th in candidate.find_all("th")]
            if any("quantity" in h for h in headers) and \
               any("price" in h for h in headers) and \
               any("ship" in h for h in headers):
                table = candidate
                break

    if not table:
        return [] 

    rows = table.find_all("tr")
    data = []

    # Skip header row
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 3:
            data.append({
                "Quantity": cols[0].get_text(strip=True),
                "Price": cols[1].get_text(strip=True),
                "Ship Date": cols[2].get_text(strip=True)
            })

    return data





