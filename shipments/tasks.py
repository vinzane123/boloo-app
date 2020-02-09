import string
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from celery import shared_task
import datetime
import json
import re
import requests
import os
import time
from .auto_refresh import *
from shipments.views import *



# normal-sync

@shared_task
def sync_items(category):
    payload = {'category': category}
    r = requests.get('http://localhost:8000/getShipments',params=payload)
    return r.text

# scaled-sync

@shared_task
def process(item):
    return item
    

