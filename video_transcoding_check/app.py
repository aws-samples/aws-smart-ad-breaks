# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# PURPOSE:
#   Adds HLS, proxy encode and audio outputs from MediaConvert to
#   workflow metadata so downstream operators can use them as inputs.
###############################################################################

import os
import boto3

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError

region = os.environ["AWS_REGION"]
mediaconvert = boto3.client("mediaconvert", region_name=region)

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    operator_object = MediaInsightsOperationHelper(event)

    # Get MediaConvert job id
    try:
        workflow_id = operator_object.workflow_execution_id
        job_id = operator_object.metadata["VideoTranscodingJobId"]
        input_file = operator_object.metadata["VideoTranscodingInputFile"]
    except KeyError as e:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(VideoTranscodingError="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(operator_object.return_output_object())
    # Get asset id
    try:
        asset_id = operator_object.asset_id
    except KeyError as e:
        print("No asset_id in this workflow")
        asset_id = ''

    # Get mediaconvert endpoint from cache if available
    if ("MEDIACONVERT_ENDPOINT" in os.environ):
        mediaconvert_endpoint = os.environ["MEDIACONVERT_ENDPOINT"]
        customer_mediaconvert = boto3.client("mediaconvert", region_name=region, endpoint_url=mediaconvert_endpoint)
    else:
        try:
            response = mediaconvert.describe_endpoints()
        except Exception as e:
            print("Exception:\n", e)
            operator_object.update_workflow_status("Error")
            operator_object.add_workflow_metadata(VideoTranscodingError=str(e))
            raise MasExecutionError(operator_object.return_output_object())
        else:
            mediaconvert_endpoint = response["Endpoints"][0]["Url"]
            # Cache the mediaconvert endpoint in order to avoid getting throttled on
            # the DescribeEndpoints API.
            os.environ["MEDIACONVERT_ENDPOINT"] = mediaconvert_endpoint
            customer_mediaconvert = boto3.client("mediaconvert", region_name=region, endpoint_url=mediaconvert_endpoint)

    # Get MediaConvert job results
    try:
        response = customer_mediaconvert.get_job(Id=job_id)
    except Exception as e:
        print("Exception:\n", e)
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(VideoTranscodingError=e, VideoTranscodingJobId=job_id)
        raise MasExecutionError(operator_object.return_output_object())
    else:
        if response["Job"]["Status"] == 'IN_PROGRESS' or response["Job"]["Status"] == 'PROGRESSING':
            operator_object.update_workflow_status("Executing")
            operator_object.add_workflow_metadata(VideoTranscodingJobId=job_id,
                                                  VideoTranscodingInputFile=input_file,
                                                  AssetId=asset_id,
                                                  WorkflowExecutionId=workflow_id)
            return operator_object.return_output_object()
        elif response["Job"]["Status"] == 'COMPLETE':
            # Get HLS object
            hls_output_uri = response["Job"]["Settings"]["OutputGroups"][0]["OutputGroupSettings"]["HlsGroupSettings"]["Destination"]
            hls_bucket = hls_output_uri.split("/")[2]
            hls_path = "/".join(hls_output_uri.split("/")[3:])
            hls_key = hls_path + ".m3u8"
            operator_object.add_media_object("HLS", hls_bucket, hls_key)
            # Get proxy object
            proxy_output_uri = response["Job"]["Settings"]["OutputGroups"][1]["OutputGroupSettings"]["FileGroupSettings"]["Destination"]
            proxy_extension = response["Job"]["Settings"]["OutputGroups"][1]["Outputs"][0]["Extension"]
            proxy_modifier = response["Job"]["Settings"]["OutputGroups"][1]["Outputs"][0]["NameModifier"]
            proxy_bucket = proxy_output_uri.split("/")[2]
            proxy_path = "/".join(proxy_output_uri.split("/")[3:])
            proxy_key = proxy_path + proxy_modifier + "." + proxy_extension
            operator_object.add_media_object("ProxyEncode", proxy_bucket, proxy_key)
            # Get audio object
            audio_output_uri = response["Job"]["Settings"]["OutputGroups"][2]["OutputGroupSettings"]["FileGroupSettings"]["Destination"]
            audio_extension = response["Job"]["Settings"]["OutputGroups"][2]["Outputs"][0]["Extension"]
            audio_modifier = response["Job"]["Settings"]["OutputGroups"][2]["Outputs"][0]["NameModifier"]
            audio_bucket = audio_output_uri.split("/")[2]
            audio_path = "/".join(audio_output_uri.split("/")[3:])
            audio_key = audio_path + audio_modifier + "." + audio_extension
            loudness_key = audio_path + audio_modifier + "_loudness.csv"
            operator_object.add_media_object("Audio", audio_bucket, audio_key)
            operator_object.add_media_object("Loudness", audio_bucket, loudness_key)
            # Set workflow status complete
            operator_object.add_workflow_metadata(VideoTranscodingJobId=job_id)
            operator_object.update_workflow_status("Complete")
            return operator_object.return_output_object()
        else:
            operator_object.update_workflow_status("Error")
            operator_object.add_workflow_metadata(
                VideoTranscodingError="Unhandled exception, unable to get status from mediaconvert: {response}".format(response=response), 
                VideoTranscodingJobId=job_id)
            raise MasExecutionError(operator_object.return_output_object())