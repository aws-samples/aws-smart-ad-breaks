# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import time
import uuid
import boto3

workflow_name = os.environ["WORKFLOW_NAME"]
workflow_function = os.environ["WorkflowEndpoint"]
dataplane_bucket = os.environ["DATAPLANE_BUCKET"]

lambda_client = boto3.client('lambda')
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    print(event)
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key = event['Records'][0]['s3']['object']['key']

    # Copy object to Dataplane bucket
    s3_client.copy_object(
        Bucket=dataplane_bucket,
        CopySource={
            'Bucket': bucket_name,
            'Key': object_key
        },
        Key=object_key,
    )

    # Workflow input body
    body = {
        "Name": workflow_name,
        "Input":{
            "Media":{
                "Video":{
                    "S3Bucket": dataplane_bucket,
                    "S3Key": object_key
                }
            }
        }
    }

    # Lambda request (with Chalice/API Gateway attributes)
    request = {
        "resource": "/workflow/execution",
        "path": "/workflow/execution",
        "httpMethod": "POST",
        "headers": {
            'Content-Type': 'application/json'
        },
        "multiValueHeaders": {},
        "queryStringParameters": {},
        "multiValueQueryStringParameters": {},
        "pathParameters": {},
        "stageVariables": {},
        "requestContext": {
            'resourcePath': "/workflow/execution",
            'requestTime': time.time(),
            'httpMethod': 'POST',
            'requestId': 'lambda_' + str(uuid.uuid4()).split('-')[-1],
        },
        "body": json.dumps(body),
        "isBase64Encoded": False
    }

    # Invoke Workflow lambda function
    response = lambda_client.invoke(
        FunctionName=workflow_function,
        InvocationType='RequestResponse',
        LogType='None',
        Payload=bytes(json.dumps(request), encoding='utf-8')
    )
    print(response)
    print(json.loads(response['Payload'].read()))
