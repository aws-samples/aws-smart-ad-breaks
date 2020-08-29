# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError
from MediaInsightsEngineLambdaHelper import DataPlane

from silence import detect_silences
from segment import detect_technical_cues, detect_shots
from score import calculate_scores

REKOGNITION_OPERATORS = {
    "celebrityRecognition",
    "faceDetection",
    "labelDetection",
    "contentModeration",
    "technicalCueDetection",
    "shotDetection"
}

dataplane = DataPlane()

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    operator_object = MediaInsightsOperationHelper(event)
    # Get media metadata from input event
    try:
        workflow_id = operator_object.workflow_execution_id
        asset_id = operator_object.asset_id
        loudness_bucket = operator_object.input["Media"]["Loudness"]["S3Bucket"]
        loudness_key = operator_object.input["Media"]["Loudness"]["S3Key"]
    except Exception as exception:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            SlotDetectionError="Missing a required metadata key {e}".format(e=exception))
        raise MasExecutionError(operator_object.return_output_object())
    # Get asset metadata from dataplane
    try:
        asset_metadata = __get_asset_metadata(asset_id)
    except Exception as exception:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            SlotDetectionError="Unable to retrieve metadata for asset {}: {}".format(asset_id, exception))
        raise MasExecutionError(operator_object.return_output_object())
    try:
        # Get detected reasons' timestamps from media and asset metadata
        silences = detect_silences(loudness_bucket, loudness_key)
        black_frames, end_credits = detect_technical_cues(asset_metadata)
        shots = detect_shots(asset_metadata)
        reasons_timestamps = {
            "Silence": silences,
            "BlackFrame": black_frames,
            "ShotChange": shots,
            "EndCredits": end_credits
        }
        media_info = asset_metadata["shotDetection"]["VideoMetadata"][0]
        # Create slots from reasons' timestamps
        print("reasons_timestamps: {}".format(reasons_timestamps))
        slots = []
        for reason in reasons_timestamps:
            for timestamp in reasons_timestamps[reason]:
                slots.append({
                    "Timestamp": float(timestamp),
                    "Score": 1.0,
                    "Reasons": [reason]
                })
        print("slots: {}".format(slots))
        # Consolidate slots and calculate scores
        slots = calculate_scores(slots, media_info, asset_metadata)
        print("scored_slots: {}".format(slots))
    except Exception as exception:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(SlotDetectionError=str(exception))
        raise MasExecutionError(operator_object.return_output_object())

    operator_object.add_workflow_metadata(
        AssetId=asset_id,
        WorkflowExecutionId=workflow_id)
    operator_object.update_workflow_status("Complete")

    metadata_upload = dataplane.store_asset_metadata(
        asset_id=asset_id,
        operator_name=operator_object.name,
        workflow_id=workflow_id,
        results={"slots": slots}
    )
    print("metadata_upload: {}".format(metadata_upload))
    if metadata_upload["Status"] == "Success":
        print("Uploaded metadata for asset: {asset}".format(asset=asset_id))
    elif metadata_upload["Status"] == "Failed":
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            SlotDetectionError="Unable to upload metadata for asset {}: {}".format(asset_id, metadata_upload))
        raise MasExecutionError(operator_object.return_output_object())
    else:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(
            SlotDetectionError="Unable to upload metadata for asset {}: {}".format(asset_id, metadata_upload))
        raise MasExecutionError(operator_object.return_output_object())

    return operator_object.return_output_object()

def __get_asset_metadata(asset_id):
    asset_metadata = {operator: {} for operator in REKOGNITION_OPERATORS}
    params = {"asset_id": asset_id}
    while True:
        response = dataplane.retrieve_asset_metadata(**params)
        if "operator" in response and response["operator"] in REKOGNITION_OPERATORS:
            __update_and_merge_lists(asset_metadata[response["operator"]], response["results"])
        if "cursor" not in response:
            break
        params["cursor"] = response["cursor"]
    return asset_metadata

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