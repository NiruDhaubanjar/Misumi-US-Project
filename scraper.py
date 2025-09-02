import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumbase import SB


def scroll_to_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)


def accept_popup(driver):
    """Handle cookie/privacy popup if present"""
    try:
        pop_up = driver.find_element(
            By.XPATH,
            "//a[contains(@class,'acceptPrivacyPolicy') or contains(text(),'Accept')]"
        )
        pop_up.click()
        time.sleep(2)
    except:
        pass


def extract_products(driver, final_urls):
    """Extract product URLs from current listing page with pagination"""
    while True:
        try:
            product_links = driver.find_elements(
                By.XPATH, "//ul[@class='m-listAreaUnit--spec is-listview']//li//p[@class='mc-name']//a"
            )
            for link in product_links:
                product_url = link.get_attribute("href")
                if product_url and product_url not in final_urls:
                    final_urls.append(product_url)
                    print(f"Product URL: {product_url}")
        except Exception as e:
            print(f"⚠ Error fetching product links: {e}")
            break

        # Handle pagination
        try:
            next_button = driver.find_element(
                By.XPATH, "//li[@class='arrow']//a[contains(@id, '-next')]"
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            driver.execute_script("arguments[0].click();", next_button)

            WebDriverWait(driver, 5).until(EC.staleness_of(next_button))
            WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//ul[@class='m-listAreaUnit--spec is-listview']//li//p[@class='mc-name']//a")
                )
            )
        except Exception:
            return final_urls


def traverse_category(driver, current_url, final_urls, visited_urls):
    """Recursive traversal of categories"""
    if current_url in visited_urls:
        return
    visited_urls.add(current_url)
    print(f"Visiting: {current_url}")

    driver.get(current_url)
    time.sleep(3)
    accept_popup(driver)

    # Check for subcategories
    sub_categories = driver.find_elements(
        By.XPATH, "//ul[contains(@class,'m-categoryList')]//a"
    )
    sub_urls = [s.get_attribute("href") for s in sub_categories if s.get_attribute("href")]

    if sub_urls:
        for sub_url in sub_urls:
            traverse_category(driver, sub_url, final_urls, visited_urls)
    else:
        # Check if single product page
        try:
            product_title = driver.find_element(
                By.XPATH, "//h1[contains(@class,'m-adaptive-product__title')]"
            ).text.strip()
            final_urls.append(current_url)
            print(f"Single Product: {product_title} → {current_url}")
            return 
        except Exception:
            pass

        # Try brand filter
        try:
            brand_select = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//li[@class='is-brandItem']"))
            )
            scroll_to_view(driver, brand_select)
            driver.execute_script("arguments[0].click();", brand_select)
        except Exception:
            pass

        # Switch to list view
        try:
            view_to_list = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@class='mc-list']"))
            )
            scroll_to_view(driver, view_to_list)
            driver.execute_script("arguments[0].click();", view_to_list) 
        except Exception:
            pass

        # Extract product URLs
        extract_products(driver, final_urls)


def extract_subcategory_urls(start_url):
    final_urls = []
    visited_urls = set()

    with SB(uc=True, incognito=True, maximize=True, locale_code="en", skip_js_waits=True, headless=True) as driver:
        traverse_category(driver, start_url, final_urls, visited_urls)

    return final_urls