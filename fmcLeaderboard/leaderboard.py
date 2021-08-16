import requests
import json
from datetime import datetime, timedelta
import boto3

URL = 'https://spreadsheets.google.com/feeds/list/1qHYA46hxx9mVzmVzEhguGWEwWoJ6jUmfGtMbzHlgEcU/1/public/values?alt=json'
PATH = 'racingCollective/duro/gb/21.json'

SCRATCHED = {
    1: ['George Bramwell', 'Charlie Holden', 'Liam Yates', 'Ben Rickaby'],
    2: [],
    3: [],
    4: [],
}


def lambda_wrapper(event, lambda_context):
    update_table()


def update_table(write_local=False):
    stage_times = pullData(URL)
    results, offsets = calculateResults(stage_times)
    to_s3(PATH, results)
    if write_local:
        with open('results.json', 'w') as f:
            f.write(results)
        with open('offsets.json', 'w') as f:
            f.write(offsets)


def calculateResults(stageTimes):
    results = []
    offsets = {}
    group2name = {'1': 'Solo', '2': 'Pair'}
    for r in stageTimes['feed']['entry']:
        riderName = r['gsx$name']['$t']
        res = {'Rider': riderName,
               'Group': group2name[r['gsx$groupid']['$t']]}
        off = {}
        totalTime = timedelta(0)
        totalStopped = timedelta(0)
        for s in range(1, 5):
            if riderName in SCRATCHED[s]:
                res['S{}'.format(s)] = 'DNF'
                res['CP{}'.format(s)] = 'DNF'
                s += 1
                break
            startKey = 'gsx$s{}-starttime'.format(s)
            stopKey = 'gsx$s{}-stoptime'.format(s)
            if r[startKey]['$t'] and r[stopKey]['$t']:
                startTime = datetime.strptime(r[startKey]['$t'], '%d-%m-%Y %H:%M:%S')
                stopTime = datetime.strptime(r[stopKey]['$t'], '%d-%m-%Y %H:%M:%S')
                stageTime = (stopTime - startTime)
                totalTime = totalTime + stageTime
                res['S{}'.format(s)] = format_timedelta(stageTime)
                res['CP{}'.format(s)] = format_timedelta(totalTime, 3)
            else:
                break
        for sx in range(s, 5):
            res['S{}'.format(sx)] = ''
            res['CP{}'.format(sx)] = ''
        for s in range(2, 5):
            stopKey = 'gsx$s{}-stoptime'.format(s - 1)
            startKey = 'gsx$s{}-starttime'.format(s)
            if r[startKey]['$t'] and r[stopKey]['$t']:
                stopTime = datetime.strptime(r[stopKey]['$t'], '%d-%m-%Y %H:%M:%S')
                startTime = datetime.strptime(r[startKey]['$t'], '%d-%m-%Y %H:%M:%S')
                totalStopped = totalStopped + (startTime - stopTime)
                off['S{}'.format(s)] = totalStopped.days * 24 + totalStopped.seconds / 60 / 60
            else:
                break
        results.append(res)
        offsets[r['gsx$name']['$t']] = off
    results.sort(key=lambda x: x['Rider'])
    return json.dumps({'data': results}), json.dumps(offsets)


def format_timedelta(td, zeros=2):
    from datetime import timedelta
    if not isinstance(td, timedelta):
        return td
    if td.days > 30:
        return 'DNF'
    hours = (td.days * 24) + (td.seconds // 3600)
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    format_string = '{:0' + str(zeros) + '}H {:02d}M'  # {:02d}S'
    return format_string.format(hours, minutes, seconds)

def pullData(url):
    from time import sleep
    for attempt in range(11):
        try:
            return requests.get(url).json()
        except Exception:
            sleep(2**attempt//2)
    raise EnvironmentError()

def to_s3(path, body):
    s3 = boto3.resource('s3')
    s3.Object('bikerid.es', path).put(Body=body, ContentType='application/json')
