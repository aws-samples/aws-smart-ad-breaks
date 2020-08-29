# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import boto3
from botocore.exceptions import ClientError
import cfnresponse

def lambda_handler(event, context):
    print('event: {}'.format(event))
    s3 = boto3.client('s3')
    bucket = event['ResourceProperties']['BucketName']
    oai = event['ResourceProperties']['OriginAccessIdentity']
    response = {}
    status = cfnresponse.SUCCESS
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        try:
            policy = json.loads(s3.get_bucket_policy(Bucket=bucket)['Policy'])
            statement = {
                "Sid": oai,
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::cloudfront:user/CloudFront Origin Access Identity " + oai
                },
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::" + bucket + "/*"
            }
            policy['Statement'].append(statement)
            s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
            response = {}
        except ClientError as error:
            print('Exception: %s' % error)
            status = cfnresponse.FAILED
            response = {'Exception': str(error)}
    elif event['RequestType'] == 'Delete':
        try:
            policy = json.loads(s3.get_bucket_policy(Bucket=bucket)['Policy'])
            for statement in reversed(policy['Statement']):
                if 'Sid' in statement:
                    if statement['Sid'] == oai:
                        policy['Statement'].remove(statement)
            s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))
            response = {}
        except ClientError as error:
            print('Exception: %s' % error)
            status = cfnresponse.FAILED
            response = {'Exception': str(error)}
    print('response: {}'.format(response))
    cfnresponse.send(event, context, status, response)