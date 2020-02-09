from django.shortcuts import render
from django.core import serializers
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from bol.settings import client_id,client_secret
import datetime
import json
import re
import requests
import os
import time
from shipments.models import *
from .auto_refresh import *
from .tasks import sync_items,process
from celery import group


token = None
os.environ['expiry'] = str(0)
expiry =  0


@csrf_exempt
def token(request):
        if request.method == 'POST':
                url = "https://login.bol.com/token"
                headers={'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
                if request.POST:
                        id = request.POST['client_id']
                        secret = request.POST['client_secret']
                        payload = {'client_id': id, 'client_secret': secret,'grant_type':'client_credentials'}
                        r = requests.post(url, data=payload)
                        respon = json.loads(r.text)
                        os.environ['token'] = respon['access_token']
                        token = respon['access_token']
                        dic =  {"access_token":respon['access_token'],"status_code":r.status_code,
                        "access_token_expiration":time.time()+respon['expires_in']}
                        expiry = time.time()+299
                        os.environ['expiry'] = str(expiry)
                        return HttpResponse(json.dumps(dic))



@refresh_token
@csrf_exempt
def list_items(request):
                url = 'https://api.bol.com/retailer/'
                if os.environ['expiry'] == str(0):
                        dic = {'isSuccess':False,'details':'Please try after login','status_code':400}
                        return HttpResponse(json.dumps(dic))
                if token != None:
                        auth = "Bearer "+os.environ['token']
                        headers={'Accept':'application/vnd.retailer.v3+json','Authorization':auth}
                        if request.method == 'GET':
                                category=request.GET['category']
                                url = url+category
                                r= requests.get(url,headers=headers)
                                return HttpResponse(r.text)

def list_all(category):
                url = 'https://api.bol.com/retailer/'+category
                if os.environ['expiry'] == str(0):
                        dic = {'isSuccess':False,'details':'Please try after login','status_code':400}
                        return dic
                if token != None:
                        auth = "Bearer "+os.environ['token']
                        headers={'Accept':'application/vnd.retailer.v3+json','Authorization':auth}
                        r= requests.get(url,headers=headers)
                        return json.loads(r.text)


def store_shipments(data,category):
        if data and category == 'shipments':
                ins = Shipments(shipmentId=data['shipmentId'],category=category,shipmentDate=data['shipmentDate'],
                        shipmentItems=data['shipmentItems'],transportId=data['transport']['transportId'])
                ins.save()


@refresh_token
@csrf_exempt
def store_in_sync(request):
        if request.method == 'GET':
                category = request.GET['category']
                
                test = list_all(category)
                if 'isSuccess' in dict(test):
                        return HttpResponse(json.dumps(test))

                # res = sync_items.delay(category)
                # data = json.loads(res.get(timeout=1))
                # data={}
                # data['%s' %(category)] = '%s' % ()
                
                else:
                        jobs = group(process.s(item) for item in test[category])
                        result = jobs.apply_async()                       
                        for i in range(0,len(result.join())):
                                store_shipments(result.join()[i],category)
                        return HttpResponse(result.join())                       
                



