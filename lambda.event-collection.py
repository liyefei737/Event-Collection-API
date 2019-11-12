from boto3.dynamodb.conditions import Key, Attr
from botocore.vendored import requests
from datetime import datetime, timedelta
import boto3
import json

GEOIP_API_ENDPOINT = ''

dynamodb = boto3.resource('dynamodb')

event_table = dynamodb.Table('event_tab')


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err['message'] if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def handle_post(event):
    request_body = json.loads(event['body']) if event['body'] is not None else {}

    # check required fields
    if 'ip' not in request_body or 'name' not in request_body:
        return respond(err={'message': 'Missing required fields. Required fields: ip, name. '})

    ip = request_body['ip']
    name = request_body['name']

    # make a call to geoip api
    r = requests.get(GEOIP_API_ENDPOINT, params={'ip': ip})

    if r.status_code != 200:
        return respond(err={'message': 'geoip api call was unsuccessful. Please try again later. '})

    geoip_api_result = r.json()

    utc_date_time = datetime.utcnow()
    # e.g. '2019-11-13'
    created_date = utc_date_time.strftime("%Y-%m-%d")
    # e.g. '02:58:39.625411'
    created_time = utc_date_time.strftime("%H:%M:%S.%f")

    # convert location information(e.g. longitude 73.223 ) from type decimal to type string
    location = {k: str(v) for k, v in geoip_api_result['location'].items()}

    item = {
        'created_date': created_date,
        'created_time': created_time,
        'ip': ip,
        'name': name,
        'city': geoip_api_result['city'],
        'country': geoip_api_result['country']['name'],
        'location': location
    }

    if 'additional_info' in request_body:
        item['additional_info'] = request_body['additional_info']

    # write this event to db
    event_table.put_item(Item=item)

    return respond(None, res={'body': "success"})


def handle_get(event):
    query_params = event['queryStringParameters'] if event['queryStringParameters'] is not None else {}
    # retrieve parameters, set to None if a parameter is not given
    start_date_time = query_params.get('startDateTime', None)
    end_date_time = query_params.get('endDateTime', None)
    city = query_params.get('city', None)
    country = query_params.get('country', None)

    # do a time range query if both start and end time are given
    # except users to provide datetime information in this format 2019-11-11T02:44:44
    if start_date_time and end_date_time:
        start_date, start_time = start_date_time.split('T')
        end_date, end_time = end_date_time.split('T')
        date_delta = datetime.strptime(end_date, "%Y-%m-%d").date() - datetime.strptime(start_date, "%Y-%m-%d").date()

        # end datetime is before start datetime
        if date_delta.days < 0:
            return respond(err={'message': 'ending time is before starting time.'})

        # same day time range
        if date_delta.days == 0:
            time_delta = datetime.strptime(end_time, '%H:%M:%S') - datetime.strptime(start_time, '%H:%M:%S')

            # end datetime is before start datetime
            if time_delta.seconds < 0:
                return respond(err={'message': 'ending time is before starting time.'})

            response = event_table.query(
                KeyConditionExpression=Key('created_date').eq(start_date) & Key('created_time').between(start_time,
                                                                                                        end_time))
            return respond(None, res=response)
        # multi day range
        else:
            # get events greater than or equal to start_time on start_date
            response = event_table.query(
                KeyConditionExpression=Key('created_date').eq(start_date) & Key('created_time').gte(start_time))

            # get events in between the start date and end date. could have none
            sd = datetime.strptime(start_date, "%Y-%m-%d").date()
            for i in range(1, date_delta.days):
                day = sd + timedelta(days=i)
                r = event_table.query(KeyConditionExpression=Key('created_date').eq(day.strftime("%Y-%m-%d")))
                response['Items'].extend(r['Items'])

            # get events less than or equal to end_time on end_date
            response_end_day = event_table.query(
                KeyConditionExpression=Key('created_date').eq(end_date) & Key('created_time').lte(end_time))
            response['Items'].extend(response_end_day['Items'])

            return respond(None, res=response)
    else:
        # query either on city index or country index
        if city:
            # process 2 cases: only city given and both city and country given from the query strings
            if country:
                response = event_table.query(IndexName='city-index', KeyConditionExpression=Key('city').eq(city),
                                             FilterExpression=Attr('country').eq(country))
            else:
                response = event_table.query(IndexName='city-index', KeyConditionExpression=Key('city').eq(city))

            return respond(None, res=response)

        elif country:
            # process 1 case when only country is given from the query string
            response = event_table.query(IndexName='country-index', KeyConditionExpression=Key('country').eq(country))
            return respond(None, res=response)

        else:
            # no query string given, return all items in the table
            return respond(None, res=event_table.scan())


def handler(event, context):
    operation = event['httpMethod']

    if operation == 'GET':
        return handle_get(event)
    elif operation == 'POST':
        return handle_post(event)
