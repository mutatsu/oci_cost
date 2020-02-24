# Python version 3.8.1
# oci-python-sdk-2.10.5
import oci
import argparse
import datetime
import json
import urllib
import math

def oci_config():
    # https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/index.html
    config = {
        "user": 'ocid1.user.oc1..xxxx',
        "key_file": "~/.oci/oci_api_key.pem",
        "fingerprint": '3c:de:13:ec:39:xxxx',
        "tenancy": 'ocid1.tenancy.oc1..xxxx',
        "region": 'ap-xxxx-x'
    }
    oci.config.validate_config(config)
    return config

def metering_config():
    # https://docs.oracle.com/en/cloud/get-started/subscriptions-cloud/meter/index.html
    config={
        'idcs_uid_pwd':'xxxx',  # https://www.base64encode.org/ idcs_userid:idcs_password
        'idcs_account_id':'cacct-xxxx',
        'idcs_instance_guid':'idcs-xxxx',       
        'endpoint':'https://itra.oraclecloud.com',
        'cost_url':'metering/api/v1/usagecost',
        'service_entitlements_url':'myservices/api/v1/serviceEntitlements'
    }
    return config

def get_root_compartment_id():
    return 'ocid1.tenancy.oc1..xxxx'

# --- set above values

def service_url_string(config):
    url_string = config['endpoint'] + '/itas/' + config['idcs_account_id'] + '/' + config['service_entitlements_url']
    return url_string

def tagged_usagecost_url_string(config):
    url_string = config['endpoint'] + '/' + config['cost_url'] + '/' + config['idcs_account_id'] + '/' + 'tagged'
    return url_string

def list_compartments(config,root_compartment_id):
    client = oci.identity.IdentityClient(config)
    response = client.list_compartments(root_compartment_id)
    compartments=[]
    compartments = response.data
    clist = {}
    for i in compartments:
        if i.name == 'ManagedCompartmentForPaaS':
            continue
        if i.lifecycle_state != 'ACTIVE':
            continue
        clist[i.id] = i.name
    return clist

def get_service_entitlements(config):
    headers = {
        'Authorization': 'Basic ' + config['idcs_uid_pwd'],
        'X-ID-TENANT-NAME': config['idcs_instance_guid']
    }
    url = service_url_string(config)
    request = urllib.request.Request(url=url,data=None,headers=headers)
    with urllib.request.urlopen(request) as response:
            data = response.read()
    services = []
    pdata = json.loads(data.decode('utf-8'))
    for i in pdata['items']:
        services.append(i['serviceDefinition']['name'])
    return services

def set_tagged_usagecost_parameter(start_time_str, end_time_str, compartment_id, service_name, usage_type):
    param = {
        'computeTypeEnabled':'Y',
        #'dataCenter':'',
        'dcAggEnabled':'Y',
        'endTime':'',   # mandatory
        #'resourceName':'',
        'rollupLevel':'RESOURCE',
        #'serviceEntitlementId':'',
        'serviceName':'',
        'startTime':'', # mandatory
        'tags':'',
        'timeZone':'UTC',
        'usageType':'',  # TOTAL, HOURLY or DAILY
    }
    param['startTime'] = start_time_str
    param['endTime'] = end_time_str
    param['serviceName'] = service_name
    #param['tags'] = 'ORCL:OCICompartmentName=' + compartment_id
    param['tags'] = 'ORCL:OCICompartment=' + compartment_id
    param['usageType'] = usage_type
    return param

def get_tagged_usagecost(config, param):
    headers = {
        'Authorization': 'Basic ' + config['idcs_uid_pwd'],
        'X-ID-TENANT-NAME': config['idcs_instance_guid']
    }
    url = tagged_usagecost_url_string(config) + '?' + urllib.parse.urlencode(param,safe=':.=')
    request = urllib.request.Request(url=url,data=None,headers=headers)
    with urllib.request.urlopen(request) as response:
            data = response.read()
    pdata = json.loads(data.decode('utf-8'))
    return pdata['items']

def p_items(compartment_name, items):
    for i in items:
        print(compartment_name, end=",")
        print(i['resourceName'],end=",")
        print(i['currency'],end=",")
        print(i['gsiProductId'],end=",")
        #print(i['startTimeUtc'],end=",")
        #print(i['endTimeUtc'],end=",")
        dt = datetime.datetime.strptime(i['startTimeUtc'] , "%Y-%m-%dT%H:%M:%S.%f")
        print(dt.strftime('%Y-%m-%d'),end=",")
        print(dt.strftime('%H:%M:%S.%f'),end=",")
        dt = datetime.datetime.strptime(i['endTimeUtc'] , "%Y-%m-%dT%H:%M:%S.%f")
        print(dt.strftime('%Y-%m-%d'),end=",")
        print(dt.strftime('%H:%M:%S.%f'),end=",")
        print(i['dataCenterId'],end=",")
        print(i['resourceDisplayName'],end=",")
        for j in i['costs']:
            print(j['computedQuantity'],end=",")
            print(j['computedAmount'],end="\n")

def p_items_header():
        print('compartment_name', end=",")
        print('resource_Name',end=",")
        print('currency',end=",")
        print('product_id',end=",")
        #print('startTimeUtc',end=",")
        #print('endTimeUtc',end=",")
        print('start_date_utc',end=",")
        print('start_time_utc',end=",")
        print('end_date_utc',end=",")
        print('end_time_utc',end=",")
        print('data_center_id',end=",")
        print('resource_display_name',end=",")
        print('computed_quantity',end=",")
        print('computed_Amount',end="\n")

def p_tagged_usagecost(conf, opts, compartments, compartment_id, service_name):
    param = set_tagged_usagecost_parameter(
        opts['start_datetime'].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        opts['end_datetime'].strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        compartment_id,service_name,
        opts['usage_type'])
    items = get_tagged_usagecost(conf,param)
    if len(items) != 0:
        p_items(compartments[compartment_id], items)

def check_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "start_time",
        help="set startTime. ex. 2020-02-01 or 2020-02-01T00:00:00")
    parser.add_argument(
        "end_time",
        help="set endTime. ex. 2020-02-10 or 2020-02-10T23:00:00")
    parser.add_argument(
        "-u","--usage_type",
        default="DAILY",
        help="set usage_type. ex TOTAL, HOURLY or DAILY. default is DAILY")

    args= parser.parse_args()

    opts = {}
    date_str_len = len(args.start_time)
    if date_str_len == 10:
        opts['start_datetime'] = datetime.datetime.strptime(args.start_time , "%Y-%m-%d")
    elif date_str_len == 19:
        opts['start_datetime'] = datetime.datetime.strptime(args.start_time , "%Y-%m-%dT%H:%M:%S")
    else:
        parser.print_help()
        exit(0)

    date_str_len = len(args.end_time)
    if date_str_len == 10:
        opts['end_datetime'] = datetime.datetime.strptime(args.end_time , "%Y-%m-%d")
    elif date_str_len == 19:
        opts['end_datetime'] = datetime.datetime.strptime(args.end_time , "%Y-%m-%dT%H:%M:%S")
    else:
        parser.print_help()
        exit(0)

    if args.usage_type == 'TOTAL' or args.usage_type == 'HOURLY' or args.usage_type == 'DAILY':
        opts['usage_type'] = args.usage_type
    else:
        parser.print_help()
        exit(0)
    
    if opts['start_datetime'] >= opts['end_datetime']:
        print("!! start_time must be past day.")
        parser.print_help()
        exit(0)

    return opts

def main():
    opts = check_args()
    conf = oci_config()
    root_compartment_id = get_root_compartment_id()
    compartments = list_compartments(conf,root_compartment_id)
    compartments[root_compartment_id] = 'root' # Because root may have resources
    #for key in compartments:
    #    print(key)
    #    print(compartments[key])
    
    conf = metering_config()
    #print(service_url_string(conf))
    services = []
    services = get_service_entitlements(conf)
    #for i in services:
    #    print(i)

    #print(tagged_usagecost_url_string(conf))
    sdt_org = opts['start_datetime']
    edt_org = opts['end_datetime']
    p_items_header()
    for compartment_id in compartments:
        #print('-- '+ compartments[compartment_id] + ' --')
        for service_name in services:
            if service_name.find('BAREMETAL') == -1:
                continue
            #print('---- ' + service_name + ' ----')
            if opts['usage_type'] == 'TOTAL':
                p_tagged_usagecost(conf, opts, compartments, compartment_id, service_name)
            if opts['usage_type'] == 'DAILY':
                interval_days = 30
                sdt = sdt_org
                edt = edt_org
                elapsed_date = edt - sdt
                cnt = math.ceil(int(elapsed_date.days) / interval_days)
                tmp_sdt = sdt
                tmp_edt = edt
                for i in range(cnt):
                    tmp_sdt = sdt+datetime.timedelta(days=interval_days*i)
                    tmp_edt = sdt+datetime.timedelta(days=interval_days*(i+1))
                    if tmp_edt > edt:
                        tmp_edt = edt 
                    opts['start_datetime'] = tmp_sdt
                    opts['end_datetime'] = tmp_edt
                    p_tagged_usagecost(conf, opts, compartments, compartment_id, service_name)
            if opts['usage_type'] == 'HOURLY':
                interval_days = 7
                sdt = sdt_org
                edt = edt_org
                elapsed_date = edt - sdt
                cnt = math.ceil(int(elapsed_date.days) / interval_days)
                tmp_sdt = sdt
                tmp_edt = edt
                for i in range(cnt):
                    tmp_sdt = sdt+datetime.timedelta(days=interval_days*i)
                    tmp_edt = sdt+datetime.timedelta(days=interval_days*(i+1))
                    if tmp_edt > edt:
                        tmp_edt = edt 
                    opts['start_datetime'] = tmp_sdt
                    opts['end_datetime'] = tmp_edt
                    p_tagged_usagecost(conf, opts, compartments, compartment_id, service_name)

if __name__ == '__main__':
    main()