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
import asyncio


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
                items = []
                url = 'https://api.bol.com/retailer/'
                if os.environ['expiry'] == str(0):
                        dic = {'isSuccess':False,'details':'Please try after login','status_code':400}
                        return HttpResponse(json.dumps(dic))
                if token != None:
                        auth = "Bearer "+os.environ['token']
                        # headers={'Accept':'application/vnd.retailer.v3+json','Authorization':auth}
                        # payload = {'maxCapacity':'7','timeToLive':'1','timeUnit':'MINUTES','page':3}
                        if request.method == 'GET':
                                myDict = dict(request.GET)
                                if 'category' in myDict:
                                        category=request.GET['category']
                                        # r= requests.get(url,headers=headers,params=payload)
                                        # print("none",r.text)
                                        url = url+category
                                        result=[]
                                        one_method = asyncio.run(recurse_all(auth,url,category,result,page = 1,method='FBR'))
                                        sec_method = asyncio.run(recurse_all(auth,url,category,result=[None],page = 1,method='FBB'))
                                        items.append(one_method)
                                        items.append(sec_method)
                                        # data = json.loads(items)
                                        # result = auxy_list(data,category)
                                        result = auxy_list(items[0][0],category)
                                        result = result+auxy_list(items[1][0],category)
                                        iter_items = asyncio.run(all_items(auth,url,category,result))
                                        # print("items:::",reponse)
                                        dic = {'response':result,'status_code':200,'data':iter_items}
                                        return HttpResponse(json.dumps(dic))
                                else:
                                        dic = {'isSuccess':False,'details':'Please provide category','status_code':401}
                                        return HttpResponse(json.dumps(dic))


async def recurse_all(auth,url,category,result=[],page=1,method='FBR'):

                result = []
                headers={'Accept':'application/vnd.retailer.v3+json','Authorization':auth}
                payload = {'maxCapacity':'7','timeToLive':'1','timeUnit':'MINUTES','page':page,'fulfilment-method':method}        
                r= requests.get(url,headers=headers,params=payload)
                d = json.loads(r.text)
                if d:
                        result.append(json.loads(r.text))
                        page+=1
                        if page%7 == 0:
                                await asyncio.sleep(60)
                        recurse_all(auth,url,category,result,page,method)  
                        return result   
                else:
                        return result



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


def auxy_list(data,category):
        result = []
        if data and category:
                eav = data[category]
                if category == 'shipments':
                        for i in range(0,len(eav)):
                                result.append(eav[i]['shipmentId'])
                        return result
                elif category == 'orders':
                        for i in range(0,len(eav)):
                                result.append(eav[i]['orederId'])
                        return result
                elif category == 'returns':
                        for i in range(0,len(eav)):
                                result.append(eav[i]['rmaId'])
                        return result
        else:
                return None


def store_shipments(data,category):
        if data and category == 'shipments':
                ins = Shipments(shipmentId=data['shipmentId'],category=category,shipmentDate=data['shipmentDate'],
                        shipmentItems=data['shipmentItems'],transportId=data['transport']['transportId'])
                ins.save()

def store_items(ids,data,category):
        count=0
        if category == 'shipments':
                for i in data:
                        ins = Items(id=ids[count],data=data[count],status='shipment')
                        ins.save()
                        count+=1
        elif category == 'orders':
                for i in data:
                        ins = Items(id=ids[count],data=data[count],status='open')
                        ins.save()
        else:
                for i in data:
                        ins = Items(id=ids[count],data=data[count],status='returned')
                        ins.save()
                


async def all_items(auth,uri,category,ids):
                result = []
                count=0
                headers={'Accept':'application/vnd.retailer.v3+json','Authorization':auth}
                payload = {'maxCapacity':'7','timeToLive':'1','timeUnit':'MINUTES'} 
                for i in ids:
                        if  count%6 == 0 and count != 0 :
                                # time.sleep(60) 
                                await asyncio.sleep(60)                           
                        else:
                                urs = uri+'/'+str(i)
                                r= requests.get(urs,headers=headers,params=payload)
                                result.append(json.loads(r.text))
                                count+=1
                return result



@refresh_token
@csrf_exempt
def store_in_sync(request):
        if request.method == 'GET':
                myDict = dict(request.GET)
                if 'category' in myDict:           
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
                else:
                        dic = {'isSuccess':False,'details':'Please provide category','status_code':401}
                        return HttpResponse(json.dumps(dic))                        

@refresh_token
@csrf_exempt
def sync_all(request):
        if request.method == 'GET':
                myDict = dict(request.GET)
                if 'category' in myDict:           
                        category = request.GET['category']
                        url = 'http://localhost:8000/getShipments'
                        payload = {'category':category}
                        r = requests.get(url,params=payload)
                        r_dir = dict(json.loads(r.text))
                        if 'isSuccess' in r_dir:
                                return HttpResponse(r.text)
                        else:
                                jobs = group(process.s(item) for item in r_dir['response'])
                                result = jobs.apply_async()
                                print("yedu:",result.join())         
                                store_items(result.join(),r_dir['data'],category)
                                dic = {'isSuccess':True,'details':'Data stored successfully','sync_items':result.join(),'status_code':200}
                                return HttpResponse(json.dumps(dic))                       
                else:
                        dic = {'isSuccess':False,'details':'Please provide category','status_code':401}
                        return HttpResponse(json.dumps(dic))    

