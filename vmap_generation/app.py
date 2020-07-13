# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import datetime
import random
import boto3

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError
from MediaInsightsEngineLambdaHelper import DataPlane

from vmap import VMAP

AD_FILES = [
    'AD-caribbean-5.mp4',
    'AD-carracing-5.mp4',
    'AD-perfume-5.mp4',
    'AD-polarbear-5.mp4',
    'AD-robots-5.mp4',
    'AD-skiing-5.mp4',
    'AD-sports-5.mp4']

ads_cf_url = os.environ['ADS_CF_URL']
top_slots_qty = int(os.environ['TOP_SLOTS_QTY'])

s3 = boto3.client('s3')
dataplane = DataPlane()

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    operator_object = MediaInsightsOperationHelper(event)
    # Get media metadata from input event
    try:
        asset_id = operator_object.asset_id
        bucket = operator_object.input["Media"]["Video"]["S3Bucket"]
    except Exception as exception:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            VmapGenerationError="Missing a required metadata key {e}".format(e=exception))
        raise MasExecutionError(operator_object.return_output_object())
    # Get slots metadata from dataplane
    try:
        slots = {}
        params = {"asset_id": asset_id, "operator_name": "slotDetection"}
        while True:
            resp = dataplane.retrieve_asset_metadata(**params)
            if "operator" in resp and resp["operator"] == "slotDetection":
                __update_and_merge_lists(slots, resp["results"])
            if "cursor" not in resp:
                break
            params["cursor"] = resp["cursor"]
        print("slots: {}".format(slots))
    except Exception as exception:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            VmapGenerationError="Unable to retrieve metadata for asset {}: {}".format(asset_id, exception))
        raise MasExecutionError(operator_object.return_output_object())
    try:
        # Generate VMAP and add object
        key = 'private/assets/{}/vmap/ad_breaks.vmap'.format(asset_id)
        slots["slots"].sort(key=__get_slot_score)
        top_slots = slots["slots"][-top_slots_qty:]
        __write_vmap(top_slots, bucket, key)
        operator_object.add_media_object("VMAP", bucket, key)
        # Set workflow status complete
        operator_object.update_workflow_status("Complete")
        return operator_object.return_output_object()
    except Exception as exception:
        print("Exception:\n", exception)
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(VmapGenerationError=exception)
        raise MasExecutionError(operator_object.return_output_object())

def __update_and_merge_lists(dict1, dict2):
    for key in dict2:
        if key in dict1:
            if type(dict1[key]) is list and type(dict2[key]) is list:
                dict1[key].extend(dict2[key])
            elif type(dict1[key]) is dict and type(dict1[key]) is dict:
                __update_and_merge_lists(dict1[key], dict2[key])
            else:
                dict1[key] = dict2[key]
        else:
            dict1[key] = dict2[key]

def __get_slot_score(slot):
    return slot["Score"]

def __write_vmap(slots, bucket, key):
    vmap = VMAP()
    i = 1
    for slot in slots:
        ad_break = vmap.attachAdBreak({
            'timeOffset': __format_timedelta(datetime.timedelta(seconds=float(slot['Timestamp']))),
            'breakType': 'linear',
            'breakId': 'midroll-{}'.format(i)
        })
        ad_break.attachAdSource('midroll-{}-ad-1'.format(i), 'false', 'true', 'VASTAdData',
            '<VAST version="3.0"><Ad><InLine><AdSystem>2.0</AdSystem><AdTitle>midroll-{}-ad-1</AdTitle><Impression/><Creatives><Creative><Linear><Duration>00:00:05</Duration><MediaFiles><MediaFile delivery="progressive" type="video/mp4" width="1920" height="1080"><![CDATA[{}ads/{}]]></MediaFile></MediaFiles></Linear></Creative></Creatives></InLine></Ad></VAST>'.format(
                i,
                ads_cf_url,
                random.choice(AD_FILES)))
        i += 1

    vmap_content = '<?xml version="1.0" encoding="UTF-8"?>{}'.format(vmap.xml().decode('utf-8'))
    print(vmap_content)

    __write_to_s3(vmap_content, bucket, key)

def __format_timedelta(delta):
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    milliseconds = int(delta.microseconds / 1000)
    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(hours, minutes, seconds, milliseconds)

def __write_to_s3(content, bucket, key):
    s3.put_object(
        Body=bytes(content.encode('UTF-8')),
        Bucket=bucket,
        Key=key
    )
