from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# Create the Celery application instance
app = Celery('crm')

# Load configuration from Django settings, using a namespace 'CELERY'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks in all registered Django app configs
app.autodiscover_tasks()