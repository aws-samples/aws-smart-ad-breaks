# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
import cfnresponse

def lambda_handler(event, context):
    print('event: {}'.format(event))
    mediatailor = boto3.client('mediatailor')
    config_name = event['ResourceProperties']['ConfigurationName']
    content_url = event['ResourceProperties']['VideoContentSource']
    ads_url = event['ResourceProperties']['AdDecisionServer']
    slate_ad = ''
    if 'SlateAd' in event['ResourceProperties']:
        slate_ad = event['ResourceProperties']['SlateAd']
    cdn_content_prefix = ''
    if 'CDNContentSegmentPrefix' in event['ResourceProperties']:
        cdn_content_prefix = event['ResourceProperties']['CDNContentSegmentPrefix']
    cdn_ad_prefix = ''
    if 'CDNAdSegmentPrefix' in event['ResourceProperties']:
        cdn_ad_prefix = event['ResourceProperties']['CDNAdSegmentPrefix']
    response = {}
    status = cfnresponse.SUCCESS
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
        try:
            if cdn_content_prefix != '' or cdn_ad_prefix != '':
                res = mediatailor.put_playback_configuration(
                    Name=config_name,
                    VideoContentSourceUrl=content_url,
                    AdDecisionServerUrl=ads_url,
                    SlateAdUrl=slate_ad,  # ok even if this is empty
                    CdnConfiguration={
                        'AdSegmentUrlPrefix': cdn_ad_prefix,
                        'ContentSegmentUrlPrefix': cdn_content_prefix
                    }
                )
            else:
                res = mediatailor.put_playback_configuration(
                    Name=config_name,
                    VideoContentSourceUrl=content_url,
                    AdDecisionServerUrl=ads_url,
                    SlateAdUrl=slate_ad,  # ok even if this is empty
                )
            print('res: {}'.format(res))
            hls_prefix = urlparse(res['HlsConfiguration']['ManifestEndpointPrefix'])
            hls_domain = hls_prefix.netloc
            hls_path = hls_prefix.path
            response = {
                'SessionInitializationPrefix': res['SessionInitializationEndpointPrefix'],
                'HLSPlaybackDomain': hls_domain,
                'HLSPlaybackPath': hls_path,
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
                Name=config_name
            )
        except ClientError as error:
            print('Exception: %s' % error)
            status = cfnresponse.FAILED
            response = {'Exception': str(error)}
    print('response: {}'.format(response))
    cfnresponse.send(event, context, status, response)