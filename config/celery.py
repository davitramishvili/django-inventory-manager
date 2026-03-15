import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('inventory_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # Every night at midnight: summarise that day's sales
    'calculate-daily-summary-midnight': {
        'task': 'apps.reports.tasks.calculate_daily_summary',
        'schedule': crontab(hour=0, minute=0),
    },
    # Every morning at 8am: flag items below reorder level
    'check-low-stock-8am': {
        'task': 'apps.reports.tasks.check_low_stock',
        'schedule': crontab(hour=8, minute=0),
    },
}
