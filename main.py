import openai
import json
import prometheus
import datetime
import time

query = "match[]={job='node-exporter'}"


def pick_job(task: str):
    pick_job_message = f"""
    You have access to a Prometheus instance. I will ask you questions about it.
    {task}
    Here is a list of jobs in the prometheus instance: {prometheus.get_all_jobs()}
    Please pick an appropriate job for this task.
    """

    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-0613",
    messages=[{"role": "user", "content": pick_job_message}],
    functions=[
        {
            "name": "get_labels_and_metadata",
            "description": "Get the labels and description for labels for a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "job": {
                        "type": "string",
                        "description": "The job name",
                    },
                },
                "required": ["job"],
            },
        }
    ],
    function_call={'name': 'get_labels_and_metadata'}
    )

    message = response["choices"][0]["message"]

    if not message.get('function_call'):
        raise Exception('No function call found')


    function_args = json.loads(message['function_call']['arguments'])
    job = function_args.get('job')
    return job

def determine_date_range(start, end, depth=0, **kwargs):

    # Retrieve data.

    def summarize(data):
        pass

    pick_job_message = f"""
    You have access to a Prometheus instance. I will ask you questions about it.
    Here is the task I want to solve:
    {kwargs.get('task')}

    Here is a list of labels and descriptions available: {kwargs.get('label')}
    Here are some additional data about this label.
    You may only select a date range within the following range: {start} to {end}

    Your job is to zoom in onto a range of time that may be of interest.
    And then summarize the data in that range according to the task.

    Please note that the resolution of the data is 50 data points.
    """

    def zoom_into_time_range(start, end):
        pass



    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-0613",
    messages=[{"role": "user", "content": pick_job_message}],
    functions=[
        {
            "name": "zoom_into_time_range",
            "description": "Get the labels and description for labels for a job",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "",
                    },
                    "job": {
                        "type": "string",
                        "description": "The job name",
                    },
                },
                "required": ["job"],
            },
        }
    ],
    function_call={'name': 'get_labels_and_metadata'}
    )

    message = response["choices"][0]["message"]

    if not message.get('function_call'):
        raise Exception('No function call found')


    function_args = json.loads(message['function_call']['arguments'])
    job = function_args.get('job')
    return job



def run_conversation(task: str):
    job = pick_job(task)
    print(f'Picked job: {job}')

    labels_metadata = prometheus.get_metric_and_metadata(
            job=job,
        )

    labels_metadata_csv = ''
    for k, v in labels_metadata.items():
        labels_metadata_csv += f'{k},{v}\n'

    # Deal with token limit
    label_metadata_csv_chunks = []
    start = 0
    while start < len(labels_metadata_csv):
        end = start + 15000
        if end > len(labels_metadata_csv):
            end = len(labels_metadata_csv)
        else:
            while end > start and labels_metadata_csv[end] != '\n':
                end -= 1

        # Slice the string from 'start' to 'end'
        chunk = labels_metadata_csv[start:end]
        label_metadata_csv_chunks.append(chunk)

        start = end + 1


    def determine_metrics(labels_metadata):
        select_label_message = f"""
        I have access to a Prometheus instance.
        The task is:
        {task}
        Here is a CSV of metrics and descriptions for it:
        {str(labels_metadata)}
        Please select metrics that may be of interest. (Only choose up to 3.)
        Please return the result in a single line of text with comma separated values.
        Do not return anything else.
        """

        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0613",
        messages=[{"role": "user", "content": select_label_message}],
        )

        res = response["choices"][0]["message"]['content']
        res = res.split(',')
        return res

    labels = []
    for chunk in label_metadata_csv_chunks:
        labels.extend(determine_metrics(chunk))

    for i in range(len(labels)):
        labels[i] = labels[i].strip().replace(' ', '')

    # Clean up the list, prometheus meta labels are not useful
    for l in labels:
        if l not in labels_metadata:
            labels.remove(l)

    # rank the labels
    select_label_message = f"""
    I have access to a Prometheus instance.
    The task is:
    {task}
    We have these labels and descriptions:
    { {l: labels_metadata[l] for l in labels} }
    Please rank the label which may be of interest.
    Please return the result in a single line of text with comma separated values.
    Do not return anything else.
    """

    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-0613",
    messages=[{"role": "user", "content": select_label_message}],
    )

    res = response["choices"][0]["message"]['content']
    print(res)


def get_label_pairs_of_interest(metric, label):
    res = prometheus.get_all_label_pairs(metric, label)
    print(res)
    pass

for label in prometheus.get_all_labels('node_cpu_seconds_total'):
    print(label)
    get_label_pairs_of_interest('node_cpu_seconds_total', label)
    

# run_conversation('When does my CPU usage typically spike? In node exporter')


end_unix = int(time.time())
start = datetime.datetime.now() - datetime.timedelta(weeks=2)
start_unix = int(time.mktime(start.timetuple())) 
print(start_unix, end_unix)

# prometheus.get_summary_of_data(int(start_unix), int(end_unix), label='node_cpu_seconds_total', job='node')
