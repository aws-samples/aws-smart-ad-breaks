# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import math

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError
from MediaInsightsEngineLambdaHelper import DataPlane

from fade import detect_fades
from silence import detect_silences
from segment import detect_technical_cues, detect_shots

REKOGNITION_OPERATORS = {
    "celebrityRecognition",
    "faceDetection",
    "labelDetection",
    "contentModeration",
    "technicalCueDetection",
    "shotDetection"
}
SCORE_ADJUSTMENTS = {
    "Silence": 0.7,
    "FadeIn": 0.6,
    "FadeOut": 0.6,
    "BlackFrame": 0.8,
    "ShotChange": 0.7,
    "EndCredits": 1.0
}

context_interval = int(os.environ["CONTEXT_INTERVAL_IN_SECONDS"])
min_confidence = int(os.environ["CONTEXT_MIN_CONFIDENCE"])

dataplane = DataPlane()

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    operator_object = MediaInsightsOperationHelper(event)
    # Get media metadata from input event
    try:
        workflow_id = operator_object.workflow_execution_id
        asset_id = operator_object.asset_id
        frames_bucket = operator_object.input["Media"]["Frames"]["S3Bucket"]
        frames_key = operator_object.input["Media"]["Frames"]["S3Key"]
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
        fade_ins, fade_outs = detect_fades(frames_bucket, frames_key)
        black_frames, end_credits = detect_technical_cues(asset_metadata)
        shots = detect_shots(asset_metadata)
        reasons_timestamps = {
            "Silence": silences,
            "FadeIn": fade_ins,
            "FadeOut": fade_outs,
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
        slots = __calculate_scores(slots, media_info, asset_metadata)
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

def __calculate_scores(slots, media_info, asset_metadata):
    # Sorting by slot time
    slots.sort(key=__get_slot_time)

    min_slot_interval = 0.50
    block_ratio = 0.25

    consolidated = []
    prev_slot = {}

    # Getting video duration
    total_duration = float(media_info["DurationMillis"]) / 1000.0

    for slot in slots:
        # Adjusting base slot score
        slot["Score"] = slot["Score"] * SCORE_ADJUSTMENTS[slot["Reasons"][0]]

        # Score adjustment: distance from beginning
        if slot["Timestamp"] / total_duration < block_ratio:
            slot["Score"] = slot["Score"] * math.pow(
                slot["Timestamp"] / total_duration, 0.30)

        if "Timestamp" in prev_slot:
            dist_from_prev = slot["Timestamp"] - prev_slot["Timestamp"]
            # Consolidating with previous slot if distance < min_slot_interval
            if dist_from_prev < min_slot_interval:
                print("Consolidating slots: {}\n{}".format(prev_slot, slot))

                prev_slot["Timestamp"] = slot["Timestamp"]
                if slot["Reasons"][0] not in prev_slot["Reasons"]:
                    prev_slot["Reasons"].append(slot["Reasons"][0])
                prev_slot["Score"] = __disjunction(prev_slot["Score"], slot["Score"])
                continue
            # Score adjustment: distance between slots
            elif dist_from_prev / total_duration < block_ratio:
                if slot["Score"] < prev_slot["Score"]:
                    slot["Score"] = slot["Score"] * math.pow(
                        dist_from_prev / total_duration, 0.05)
                else:
                    prev_slot["Score"] = prev_slot["Score"] * math.pow(
                        dist_from_prev / total_duration, 0.05)

        # Score adjustment: labels before and after
        slot["Context"] = __get_context_metadata(slot["Timestamp"], asset_metadata)
        pre_labels = set(label["Name"] for label in slot["Context"]["Labels"]["Before"])
        post_labels = set(label["Name"] for label in slot["Context"]["Labels"]["After"])
        similarity = len(pre_labels.intersection(post_labels)) / len(pre_labels.union(post_labels))
        slot["Score"] = __disjunction(slot["Score"], math.pow(1.0 - similarity, 4.0))

        consolidated.append(slot)
        prev_slot = slot

    return consolidated

def __disjunction(x, y):
    return 1.0 - ((1.0 - x) * (1.0 - y))

def __get_slot_time(slot):
    return slot["Timestamp"]

def __get_context_metadata(slot_timestamp, asset_metadata):
    rek_operator_keys = {
        "celebrityRecognition": ["Celebrities", "Celebrity"],
        "faceDetection": ["Faces", "Face"],
        "labelDetection": ["Labels", "Label"],
        "contentModeration": ["ModerationLabels", "ModerationLabel"]
    }
    context = {}
    for operator in rek_operator_keys:
        list_key = rek_operator_keys[operator][0]
        before = {}
        after = {}
        for result in asset_metadata[operator][list_key]:
            result_timestamp = result["Timestamp"] / 1000.0
            item_key = rek_operator_keys[operator][1]
            if slot_timestamp - context_interval <= result_timestamp <= slot_timestamp:
                for label in __labels_from_result(result, item_key):
                    if label["Name"] in before: 
                        if before[label["Name"]]["Confidence"] < label["Confidence"]:
                            before[label["Name"]] = label
                    else:
                        before[label["Name"]] = label
            elif slot_timestamp <= result_timestamp <= slot_timestamp + context_interval:
                for label in __labels_from_result(result, item_key):
                    if label["Name"] in after:
                        if after[label["Name"]]["Confidence"] < label["Confidence"]:
                            after[label["Name"]] = label
                    else:
                        after[label["Name"]] = label
            elif result_timestamp > slot_timestamp + context_interval:
                break
        context[list_key] = {
            "Before": list(before.values()),
            "After": list(after.values())
        }
    return context

def __labels_from_result(result, item_key):
    labels = []
    if "Emotions" in result[item_key]:
        for emotion in result[item_key]["Emotions"]:
            if float(emotion["Confidence"]) >= min_confidence:
                labels.append({"Name": emotion["Type"], "Confidence": emotion["Confidence"]})
    else:
        if float(result[item_key]["Confidence"]) >= min_confidence:
            labels.append({"Name": result[item_key]["Name"], "Confidence": result[item_key]["Confidence"]})
    return labels