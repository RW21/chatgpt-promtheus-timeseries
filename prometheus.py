import requests
from dataclasses import dataclass

PROMETHEUS = 'http://192.168.193.179:9090'

def get_metric_and_metadata(job: str):
    params = {
        'match[]': f'{{__name__=~".+", job="{job}"}}'
    }

    # Get labels
    response = requests.get(PROMETHEUS + '/api/v1/label/__name__/values', params=params)
    labels = set(response.json()['data'])

    # Get metadata
    response = requests.get(PROMETHEUS + '/api/v1/metadata')
    metadata = response.json()['data']

    # label: help_string
    res = {label: v[0]['help'] for label, v in metadata.items() if label in labels}

    return res
        


def get_all_jobs():
    response = requests.get(PROMETHEUS + '/api/v1/label/job/values')
    jobs = response.json()['data']
    return jobs



def get_all_label_pairs(metric_name: str, label_name: str) -> list:
    # Get all series for a particular metric
    response = requests.get(PROMETHEUS + '/api/v1/series', params={
        'match[]': f'{{__name__="{metric_name}"}}',
    })

    # Check the status code
    if response.status_code != 200:
        print(f"Request failed with status {response.status_code}")
        return None

    # Parse the JSON response
    data = response.json()['data']
    
    # Extract unique label pairs for the specific label name
    label_pairs = set()
    for series in data:
        if label_name in series:
            label_pairs.add(series[label_name])

    return list(label_pairs)

def get_all_labels(metric_name: str):
    response = requests.get(PROMETHEUS + '/api/v1/series', params={
        'match[]': f'{{__name__="{metric_name}"}}',
    })

    if response.status_code != 200:
        print(f"Request failed with status {response.status_code}")
        return None

    data = response.json()['data']
    
    labels = set()
    for series in data:
        labels.update(series.keys())

    labels.discard('__name__')
    labels.discard('job')

    return list(labels)


@dataclass
class PrometheusSummary:
    mean: float
    min: float
    max: float
    num_samples: int
    stddev: float
    quantiles: dict[str, float]
    variance: float
    total_increase: float
    rate_of_change: float


def get_summary_of_data(start: float, end: float, label: str, job: str) -> PrometheusSummary:
    query_time = {
        'start': start,
        'end': end,
        'step': '1000000',  # You might want to adjust this based on your typical scrape interval
    }

    # Query the raw data for this label and job
    response = requests.get(PROMETHEUS + '/api/v1/query_range', params={
        'query': f'{label}{{job="{job}"}}',
        **query_time,
    })

    print(response.json())
    return

    values = [float(v[1]) for v in response.json()['data']['result'][0]['values']]

    # Calculate statistics
    mean = requests.get(PROMETHEUS + '/api/v1/query', params={
        'query': f'avg_over_time({label}{{job="{job}"}}[{end - start}s])',
        'time': end,
    }).json()['data']['result'][0]['value'][1]
    min_val = min(values)
    max_val = max(values)
    num_samples = len(values)
    stddev = requests.get(PROMETHEUS + '/api/v1/query', params={
        'query': f'stddev_over_time({label}{{job="{job}"}}[{end - start}s])',
        'time': end,
    }).json()['data']['result'][0]['value'][1]

    variance = requests.get(PROMETHEUS + '/api/v1/query', params={
        'query': f'stdvar_over_time({label}{{job="{job}"}}[{end - start}s])',
        'time': end,
    }).json()['data']['result'][0]['value'][1]

    quantiles = {
        '0.5': requests.get(PROMETHEUS + '/api/v1/query', params={
            'query': f'quantile_over_time(0.5, {label}{{job="{job}"}}[{end - start}s])',
            'time': end,
        }).json()['data']['result'][0]['value'][1],
        '0.9': requests.get(PROMETHEUS + '/api/v1/query', params={
            'query': f'quantile_over_time(0.9, {label}{{job="{job}"}}[{end - start}s])',
            'time': end,
        }).json()['data']['result'][0]['value'][1],
    }

    total_increase = requests.get(PROMETHEUS + '/api/v1/query', params={
        'query': f'increase({label}{{job="{job}"}}[{end - start}s])',
        'time': end,
    }).json()['data']['result'][0]['value'][1]
    
    rate_of_change = requests.get(PROMETHEUS + '/api/v1/query', params={
        'query': f'rate({label}{{job="{job}"}}[{end - start}s])',
        'time': end,
    }).json()['data']['result'][0]['value'][1]

    res = PrometheusSummary(mean=mean, min=min_val, max=max_val, num_samples=num_samples, 
                             stddev=stddev, variance=variance, quantiles=quantiles, 
                             total_increase=total_increase, rate_of_change=rate_of_change)

    print(res)
    return res

