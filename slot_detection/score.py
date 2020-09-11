# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import math

SCORE_ADJUSTMENTS = {
    "Silence": 0.7,
    "BlackFrame": 0.8,
    "ShotChange": 0.7,
    "EndCredits": 1.0
}

context_interval = int(os.environ["CONTEXT_INTERVAL_IN_SECONDS"])
min_confidence = int(os.environ["CONTEXT_MIN_CONFIDENCE"])

def calculate_scores(slots, media_info, asset_metadata):
    # Sorting by slot time
    slots.sort(key=lambda slot: slot["Timestamp"])

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
        if pre_labels or post_labels:
            distance = 1.0 - (len(pre_labels.intersection(post_labels)) / len(pre_labels.union(post_labels)))
            slot["Score"] = __disjunction(slot["Score"], math.pow(distance, 4.0))

        consolidated.append(slot)
        prev_slot = slot

    return consolidated

def __disjunction(x, y):
    return 1.0 - ((1.0 - x) * (1.0 - y))

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