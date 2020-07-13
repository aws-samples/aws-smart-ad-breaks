# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import boto3
from botocore.exceptions import ClientError
import cfnresponse

def lambda_handler(event, context):
    print('event: {}'.format(event))
    mediatailor = boto3.client('mediatailor')
    response = {}
    status = cfnresponse.SUCCESS
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        try:
            res = mediatailor.put_playback_configuration(
                Name=event['ResourceProperties']['ConfigurationName'],
                VideoContentSourceUrl=event['ResourceProperties']['VideoContentSource'],
                AdDecisionServerUrl=event['ResourceProperties']['AdDecisionServer']
            )
            print('res: {}'.format(res))
            response = {
                'SessionInitializationPrefix': res['SessionInitializationEndpointPrefix'],
                'HLSPlaybackPrefix': res['HlsConfiguration']['ManifestEndpointPrefix'],
                'DashPlaybackPrefix': res['DashConfiguration']['ManifestEndpointPrefix']
            }
        except ClientError as error:
            print('Exception: %s' % error)
            status = cfnresponse.FAILED
            response = {'Exception': str(error)}
    elif event['RequestType'] == 'Delete':
        try:
            response = mediatailor.delete_playback_configuration(
                Name=event['ResourceProperties']['ConfigurationName']
            )
        except ClientError as error:
            print('Exception: %s' % error)
            status = cfnresponse.FAILED
            response = {'Exception': str(error)}
    print('response: {}'.format(response))
    cfnresponse.send(event, context, status, response)