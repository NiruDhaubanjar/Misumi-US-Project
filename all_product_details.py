import os
import time
import random
import requests
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import SB
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from openpyxl import Workbook
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.styles import Border, Side
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlparse
import os
import base64

def download_spec_html_files(spec_html, base_folder, base_url="https://us.misumi-ec.com/"):
    """
    Downloads spec HTML and all images/PDFs linked inside it.
    Updates the HTML to point to local copies.
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    import os

    spec_folder = os.path.join(base_folder, "Product_Specification")
    os.makedirs(spec_folder, exist_ok=True)

    soup = BeautifulSoup(spec_html, "html.parser")

    # Function to sanitize filenames
    def sanitize_filename(url):
        parsed = urlparse(url)
        name = os.path.basename(parsed.path)
        if not name:
            name = "file"
        return "".join(c for c in name if c.isalnum() or c in ('_', '-', '.'))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
    }

    # Download all images
    for idx, img in enumerate(soup.find_all("img")):
        src = img.get("src")
        if not src:
            continue
        full_url = urljoin(base_url, src)
        try:
            response = requests.get(full_url, headers=headers, timeout=30)
            response.raise_for_status()
            content = response.content

            # Determine extension
            ext = os.path.splitext(full_url)[1]
            if not ext:
                content_type = response.headers.get("Content-Type", "")
                if "image/jpeg" in content_type:
                    ext = ".jpg"
                elif "image/png" in content_type:
                    ext = ".png"
                elif "image/gif" in content_type:
                    ext = ".gif"
                else:
                    ext = ".jpg"

            local_name = f"img_{idx}{ext}"
            local_path = os.path.join(spec_folder, local_name)
            with open(local_path, "wb") as f:
                f.write(content)

            img['src'] = local_name
        except Exception as e:
            print(f"Failed to download image {full_url}: {e}")

    # Download PDFs or other linked files
    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href']
        if href.lower().endswith(".pdf"):
            full_url = urljoin(base_url, href)
            try:
                response = requests.get(full_url, headers=headers, timeout=30)
                response.raise_for_status()
                content = response.content
                local_name = sanitize_filename(full_url)
                local_path = os.path.join(spec_folder, local_name)
                with open(local_path, "wb") as f:
                    f.write(content)
                a_tag['href'] = local_name
            except Exception as e:
                print(f"Failed to download PDF {full_url}: {e}")

    # Save updated spec HTML
    spec_html_path = os.path.join(spec_folder, "spec.html")
    with open(spec_html_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"Specification HTML and all linked files saved in: {spec_folder}")
    return spec_html_path


def capture_tables_from_website(driver,base_folder, xpath="//div[contains(@id,'Tab_wysiwyg_area_1_contents')] | //div[contains(@id,'Tab_wysiwyg_area_0_contents')]"):

    output_folder = os.path.join(base_folder, "Product_Specification")
    os.makedirs(output_folder, exist_ok=True)

    container_div = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )

    # Find all tables inside the container div
    tables = container_div.find_elements(By.TAG_NAME, "table")

    if not tables:
        print("No tables found in the specified div.")
        return None

    # Create HTML report
    html_content = "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Table Screenshots</title></head><body>"
    html_content += "<h1>Tables from Website</h1>"

    for idx, table in enumerate(tables):
        # Scroll table into view with offset to avoid fixed header overlap
        driver.execute_script("""
            var table = arguments[0];
            var headerHeight = arguments[1];
            var rect = table.getBoundingClientRect();
            window.scrollBy(0, rect.top - headerHeight);
        """, table, 300)

        # Get full table height
        table_height = driver.execute_script("return arguments[0].scrollHeight", table)

        # Temporarily expand table height
        driver.execute_script("arguments[0].style.height = arguments[0].scrollHeight + 'px';", table)

        # Screenshot the full table
        screenshot_path = os.path.join(output_folder, f"table_{idx}.png")
        table.screenshot(screenshot_path)

        # Reset table height
        driver.execute_script("arguments[0].style.height = '';", table)

        # Embed screenshot as Base64
        with open(screenshot_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")

        html_content += f"<h2>Table {idx}</h2>"
        html_content += f"<img src='data:image/png;base64,{encoded_image}' alt='Table {idx}'/><br><br>"

    html_content += "</body></html>"

    # Save HTML report
    html_file_path = os.path.join(output_folder, "all_tables.html")
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"All table screenshots taken from website and saved in: {html_file_path}")
    return html_file_path


def scroll_to_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)


def wait_for_element(driver, selector, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
    )


def get_text_safe(driver, selector, scroll=False):
    try:
        elem = driver.find_element(By.CSS_SELECTOR, selector)
        if scroll:
            scroll_to_view(driver, elem)
        return elem.text.strip()
    except:
        return ""
    
def save_html(content, filename, subfolder="scraped_html"):
    os.makedirs(subfolder, exist_ok=True)
    filepath = os.path.join(subfolder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def fix_image_src_to_absolute(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            if src.startswith("//"):
                img['src'] = "https:" + src
            elif src.startswith("/"):
                img['src'] = urljoin(base_url, src)
    return str(soup)

def extract_product_info(url, max_retries=3):
    """
    Visit the product URL, extract breadcrumb folder structure,
    and collect all part numbers.
    """
    with SB(uc=True, incognito=True, maximize=True, locale_code="en",
            skip_js_waits=True, headless=False) as driver:

        driver.get(url)
        time.sleep(random.uniform(2.5, 3.5))

        # Handle pop-up if present
        try:
            pop_up = driver.find_element(
                By.XPATH,
                "//a[contains(@class,'m-btn--sitewideNotice VN_opacity m-notice__button_acceptPrivacyPolicy')]"
            )
            pop_up.click()
            time.sleep(3)
        except NoSuchElementException:
            pass

        # Extract breadcrumb and create nested folder structure
        try:
            breadcrumb_element = driver.find_element(By.XPATH, "//div[contains(@class,'l-breadcrumbWrap')]")
            breadcrumb_text = breadcrumb_element.text.strip()
            folders = [part.strip().replace("/", "-").replace(" ", "_")
                       for part in breadcrumb_text.split(">")]
            folder_path = os.path.join(*folders)
        except NoSuchElementException:
            folder_path = "default_products"

        os.makedirs(folder_path, exist_ok=True)
        print(f"Saving files to folder: {folder_path}")
        data = {} 
        try: 
            spec_html_elem = driver.find_element(By.XPATH, "//div[contains(@id,'Tab_wysiwyg_area_1_contents')] | //div[contains(@id,'Tab_wysiwyg_area_0_contents')] ")
            raw_spec_html = spec_html_elem.get_attribute("outerHTML") 
            spec_html_path = download_spec_html_files(raw_spec_html, folder_path) 
            data['spec_html'] = spec_html_path 
            table_html_path =capture_tables_from_website(driver,folder_path) 
            data['spec_html'] += table_html_path 
        except: 
            data['spec_html'] = ""

        try:
            part_numbers_tab = driver.find_element(By.ID, "codeList")
            scroll_to_view(driver, part_numbers_tab)
            driver.execute_script("arguments[0].click();", part_numbers_tab)
            time.sleep(2)
        except Exception as e:
            print("Failed to click 'Part Numbers' tab via JS:", e)

        # Collect all part numbers
        all_rows = []

        while True:
            table_ele = driver.find_elements(By.XPATH, "//table[contains(@class,'m-codeTable')]")[0]
            table_body_element = table_ele.find_element(By.XPATH, ".//tbody")
            row_elems = table_body_element.find_elements(By.XPATH, ".//tr")

            for row in row_elems:
                row_data = [cell.text for cell in row.find_elements(By.TAG_NAME, "td")]
                all_rows.append(row_data)

            # Check for next page
            next_buttons = driver.find_elements(
                By.XPATH,
                "//li[contains(@class, 'arrow') and @id='detail_codeList_pager_upper_right']/a"
                " | //li[contains(@class, 'arrow')]//a[contains(@id, '-next')]"
            )

            if next_buttons and next_buttons[0].is_enabled():
                next_buttons[0].click()
                WebDriverWait(driver, 10).until(EC.staleness_of(table_body_element))
            else:
                break

        part_numbers = [row[0] for row in all_rows if row]
        print("Collected Part Numbers:", part_numbers)

    return part_numbers, folder_path

def process_part_numbers(part_number, folder_path):
    """
    Iterate through part numbers, search each, scrape details,
    and save them as HTML in the folder_path.
    """
    max_retries = 5
    data = {}

    for attempt in range(1, max_retries + 1):
        try:
            with SB(uc=True, incognito=True, maximize=True, locale_code="en",
                    skip_js_waits=True, headless=True) as driver:

                driver.get("https://us.misumi-ec.com/")
                time.sleep(5)

                # --- Search by part number --- #
                input_box = driver.find_element(By.XPATH, "//input[contains(@id,'keyword_input')]")
                input_box.click()
                input_box.clear()
                input_box.send_keys(part_number)
                time.sleep(3)

                search_click = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//p[contains(@class,'mc-keyword-suggest-preview__configureNow')]"
                    " | //span[contains(@class,'mc-keyword-suggest-preview__partNumberPartNumber')]"
                ))
            )
                search_click.click()
                time.sleep(5)

                # --- Click part numbers tab (if available) --- #
                try:
                    part_numbers_tab = driver.find_element(By.ID, "codeList")
                    scroll_to_view(driver, part_numbers_tab)
                    driver.execute_script("arguments[0].click();", part_numbers_tab)
                    time.sleep(2)
                except Exception:
                    pass

                # --- Scraping Product Info --- #
                try:
                    h1_elem = wait_for_element(driver, "h1.m-h1.m-adaptive-product__title")
                    scroll_to_view(driver, h1_elem)
                    data['title'] = h1_elem.get_attribute("outerHTML")
                except:
                    data['title'] = "Not Found"

                try:
                    sub_title = wait_for_element(driver, "h2.m-adaptive-product__subtitle")
                    data['subtitle'] = sub_title.get_attribute("outerHTML")
                except:
                    data['subtitle'] = "Not Found"

                data['part_number'] = part_number

                try:
                    product_details = driver.find_element(By.XPATH, "//p[contains(@class,'mc-text catch_copy')]")
                    data['product_details'] = product_details.get_attribute("outerHTML")
                except:
                    data['product_details'] = "Not Found"

                try:
                    price_elements = driver.find_elements(
                        By.XPATH,
                        "//ul[contains(@class,'m-adaptive-cartBox__list')]"
                        " | //table[contains(@class,'m-table')]"
                    )
                    price_html_list = [elem.get_attribute("outerHTML") for elem in price_elements]
                    filtered_html_list = [html for html in price_html_list if "quantity" in html.lower() and "$" in html]
                    data['price_html'] = "\n".join(filtered_html_list) if filtered_html_list else "Price Not Found"
                except:
                    data['price_html'] = "Price Not Found"

                try:
                    spec_table = driver.find_element(By.XPATH, "//table[contains(@class,'m-listTable m-listTable--adaptive')]")
                    data['spec_table'] = spec_table.get_attribute("outerHTML")
                except:
                    data['spec_table'] = ""
                    product_tables = driver.find_elements(By.XPATH, "//table[contains(@class,'m-codeTable')]")
                    for table in product_tables:
                        try:
                            tbody = table.find_element(By.TAG_NAME, "tbody")
                            rows = tbody.find_elements(By.TAG_NAME, "tr")
                            if len(rows) > 0:
                                data['spec_table'] += table.get_attribute("outerHTML")
                        except:
                            continue
                    try:
                        alterations_div = driver.find_element(By.XPATH, "//div[@id='alterations']")
                        try:
                            unwanted = alterations_div.find_element(By.CLASS_NAME, "l-adaptive-more-information-base")
                            driver.execute_script("arguments[0].parentNode.removeChild(arguments[0]);", unwanted)
                        except:
                            pass
                        data['spec_table'] += alterations_div.get_attribute("outerHTML")
                    except:
                        print("No alterations div found.")

                # --- Save HTML --- #
                html_content = f"""
                <html>
                <head><meta charset="UTF-8"></head>
                <body>
                    <h1>{data['title']}</h1>
                    <h2>{data['subtitle']}</h2>
                    <p>Part Number: {data['part_number']}</p>
                    <p>Product Details: {data['product_details']}</p>
                    <p>Price: {data['price_html']}</p>
                    <p>Specification Table: {data['spec_table']}</p>
                </body>
                </html>
                """

                safe_filename = "".join(c for c in data['part_number'] if c.isalnum() or c in ('_', '-'))
                file_path = os.path.join(folder_path, f"{safe_filename}.html")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

                print(f"✅ Saved: {file_path}")
                return folder_path  # success → exit

        except Exception as e:
            print(f"[Attempt {attempt}] Search failed for {part_number}: {e}")
            # Browser is auto-quit here by `with SB(...)`
            if attempt == max_retries:
                print(f"❌ Skipping {part_number} after {max_retries} failed attempts.")
                return None