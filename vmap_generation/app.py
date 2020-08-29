# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
import datetime
import random
import boto3

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError
from MediaInsightsEngineLambdaHelper import DataPlane

from vmap_xml.vmap import VMAP
from vast_xml.vast import VAST

ADS_FILE = 'ads.json'

top_slots_qty = int(os.environ['TOP_SLOTS_QTY'])

s3 = boto3.client('s3')
dataplane = DataPlane()

# Reading ads from JSON file
with open(ADS_FILE) as json_file:
    ads = json.load(json_file)['ads']

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
        # Select slots with highest scores
        slots["slots"].sort(key=lambda slot: slot["Score"])
        top_slots = slots["slots"][-top_slots_qty:]
        # Generate VMAP and add object
        key = 'private/assets/{}/vmap/ad_breaks.vmap'.format(asset_id)
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

def __write_vmap(slots, bucket, key):
    vmap = VMAP()
    i = 1
    for slot in slots:
        # Merging labels from before and after the slot into a single list
        before_labels = [label['Name'] for label in slot['Context']['Labels']['Before']]
        after_labels = [label['Name'] for label in slot['Context']['Labels']['After']]
        labels = before_labels + list(set(after_labels) - set(before_labels))
        # Adding ad break to VMAP file
        ad_break = vmap.attachAdBreak({
            'timeOffset': __format_timedelta(datetime.timedelta(seconds=float(slot['Timestamp']))),
            'breakType': 'linear',
            'breakId': 'midroll-{}'.format(i)
        })
        # Adding VAST ad source 
        vast = VAST()
        ad_break.attachAdSource(
            'midroll-{}-ad-1'.format(i),
            'false',
            'true',
            'VASTAdData',
            vast)
        ad = vast.attachAd({
            'id': str(i),
            'structure': 'inline',
            'AdSystem': {'name': '2.0'},
            'AdTitle': 'midroll-{}-ad-1'.format(i)
        })
        ad.attachImpression({})
        creative = ad.attachCreative('Linear', {
            'Duration' : '00:00:15'
        })
        # Setting media file URL referencing the ad server, passing labels as parameters
        creative.attachMediaFile(__select_ad(labels), {
            'id': 'midroll-{}-ad-1'.format(i),
            'type': 'video/mp4',
            'delivery': 'progressive',
            'width': '1920',
            'height': '1080'
        })
        i += 1
    # Converting VMAP content to XML
    vmap_content = vmap.xml()
    print(vmap_content)
    # Putting VMAP file into dataplane bucket
    s3.put_object(
        Body=bytes(vmap_content),
        Bucket=bucket,
        Key=key
    )

def __format_timedelta(delta):
    hours, rem = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    milliseconds = int(delta.microseconds / 1000)
    return '{:02d}:{:02d}:{:02d}.{:03d}'.format(hours, minutes, seconds, milliseconds)

def __select_ad(labels):
    print('labels: {}'.format(labels))
    # Searching ads to find the one with most similar labels
    top_similarity = -1.0
    top_ad = None
    slot_labels = set(labels)
    random.shuffle(ads) # Shuffle to return a random ad in case none has similarity
    for ad in ads:
        print('ad: {}'.format(ad))
        ad_labels = set(ad['labels'])
        similarity = len(slot_labels.intersection(ad_labels)) / len(slot_labels.union(ad_labels))
        if similarity > top_similarity:
            top_similarity = similarity
            top_ad = ad
    print('top_ad: {}'.format(top_ad))
    print('top_similarity: {}'.format(top_similarity))
    # Return URL to selected ad video file
    return top_ad['url']
