from celery import Celery

# Celery configuration: Using Redis as both the broker and result backend
celery_app = Celery('scraper', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# Celery settings
celery_app.conf.update(
    task_serializer='json',         
    result_serializer='json',      
    accept_content=['json'],       
    result_backend='redis://redis:6379/0', 
    timezone='UTC',                
    task_track_started=True       
)

celery_app.autodiscover_tasks(['tasks'])

