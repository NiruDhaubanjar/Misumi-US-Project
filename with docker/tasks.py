import redis
from celery import group,chain,chord
from scraper import extract_subcategory_urls
from celery_worker import celery_app
from all_product_details import extract_product_info,process_part_numbers
from selenium.common.exceptions import NoSuchElementException, TimeoutException
# Redis client for storing sublinks
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
# BATCH_SIZE = 5

# # --- Task 1: Scrape sublinks and store in Redis ---
# @celery_app.task(bind=True)
# def scrape_sublinks_task(self, url):
#     sublinks = extract_subcategory_urls(url)
#     job_id = self.request.id

#     if sublinks:
#         redis_key = f"sublinks:{job_id}"
#         redis_client.delete(redis_key)
#         for link in sublinks:
#             redis_client.rpush(redis_key, link)

#         # Trigger batch scheduling asynchronously
#         schedule_batches_task.apply_async(args=[job_id])

#     return {"job_id": job_id, "count": len(sublinks)}


# # --- Task 2: Schedule batches ---
# @celery_app.task(bind=True)
# def schedule_batches_task(self, job_id):
#     redis_key = f"sublinks:{job_id}"
#     total_links = redis_client.llen(redis_key)

#     # Split into batches and create a task for each batch
#     for i in range(0, total_links, BATCH_SIZE):
#         batch = redis_client.lrange(redis_key, i, i + BATCH_SIZE - 1)
#         process_batch_task.apply_async(args=[batch])

#     return {"job_id": job_id, "total_links": total_links, "batch_size": BATCH_SIZE}


# # --- Task 3: Process a single batch ---
# @celery_app.task(bind=True)
# def process_batch_task(self, batch):
#     # Launch a group of tasks to process all links in this batch concurrently
#     group(scrape_details_task.s(link) for link in batch).apply_async()
#     return {"batch_count": len(batch)}


# # --- Task 4: Scrape details for a single link ---
# @celery_app.task(bind=True)
# def scrape_details_task(self, link):
#     folder_path = extract_product_info(link)
#     return {"link": link, "details": folder_path}


# @celery_app.task(bind=True)
# def scrape_sublinks_task(self, url):
#     job_id = self.request.id
#     sublinks = extract_subcategory_urls(url)

#     redis_key = f"sublinks:{job_id}"
#     redis_client.delete(redis_key)
#     for link in sublinks:
#         redis_client.rpush(redis_key, link)

#     # Schedule product page processing as a Celery task
#     process_all_product_pages_task.apply_async(args=[job_id])

#     return {"job_id": job_id, "count": len(sublinks)}


# @celery_app.task(bind=True)
# def process_all_product_pages_task(self, job_id):
#     """
#     Sequentially process product pages.
#     For each product page, process all its part numbers in parallel.
#     """
#     redis_key_links = f"sublinks:{job_id}"
#     links = redis_client.lrange(redis_key_links, 0, -1)

#     for url in links:
#         try:
#             part_numbers, folder_path = extract_product_info(url)

#             # Push part numbers to Redis
#             redis_key_pn = f"part_numbers:{job_id}"
#             redis_client.delete(redis_key_pn)
#             for pn in part_numbers:
#                 redis_client.rpush(redis_key_pn, f"{pn}|{folder_path}")

#             # Step: process all part numbers in parallel
#             part_number_list = redis_client.lrange(redis_key_pn, 0, -1)
#             job_group = group(process_part_number_task.s(job_id) for _ in part_number_list)
#             job_group.apply_async()

#         except Exception as e:
#             print(f"Error processing product page {url}: {e}")


# @celery_app.task(bind=True)
# def process_part_number_task(self, job_id):
#     """
#     Process a single part number from Redis
#     """
#     redis_key = f"part_numbers:{job_id}"
#     item = redis_client.lpop(redis_key)

#     if not item:
#         return {"job_id": job_id, "status": "no more part numbers"}

#     part_number, folder_path = item.split("|", 1)
#     file_path = process_part_numbers(part_number, folder_path)

#     return {"job_id": job_id, "part_number": part_number, "file_path": file_path}



@celery_app.task(bind=True)
def scrape_sublinks_task(self, url):
    """
    Scrape subcategory URLs and schedule processing product pages
    """
    job_id = self.request.id
    sublinks = extract_subcategory_urls(url)

    redis_key = f"sublinks:{job_id}"
    redis_client.delete(redis_key)
    for link in sublinks:
        redis_client.rpush(redis_key, link)

    # Start processing product pages sequentially
    process_all_product_pages_task.apply_async(args=[None,job_id])

    return {"job_id": job_id, "count": len(sublinks)}

@celery_app.task(bind=True)
def process_all_product_pages_task(self,results, job_id):
    redis_key_links = f"sublinks:{job_id}"
    links = redis_client.lrange(redis_key_links, 0, -1)

    if not links:
        return {"job_id": job_id, "status": "all links processed"}

    # Pop the first link to process
    url = links[0]
    if isinstance(url, bytes):
        url = url.decode("utf-8")
    redis_client.ltrim(redis_key_links, 1, -1)  # remove first element

    try:
        part_numbers, folder_path = extract_product_info(url)
        job_group = group(process_part_number_task.s(job_id, pn, folder_path) for pn in part_numbers)
        chord(job_group)(process_all_product_pages_task.s(job_id))
    except Exception as e:
        print(f"Error processing product page {url}: {e}")
        process_all_product_pages_task.apply_async(args=[None,job_id])




@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_part_number_task(self, job_id, part_number, folder_path):
    """
    Process a single part number with retry on Selenium failures.
    """
    try:
        file_path = process_part_numbers(part_number, folder_path)
        return {"job_id": job_id, "part_number": part_number, "file_path": file_path}
    except (NoSuchElementException, TimeoutException) as e:
        # Retry for Selenium-specific exceptions
        try:
            print(f"Retrying part number {part_number} due to error: {e}")
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            return {"job_id": job_id, "part_number": part_number, "error": str(e)}
    except Exception as e:
        # Other exceptions are returned without retry
        return {"job_id": job_id, "part_number": part_number, "error": str(e)}
