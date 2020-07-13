# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def detect_technical_cues(asset_metadata):
    black_frames = []
    end_credits = []
    for segment in asset_metadata["technicalCueDetection"]["Segments"]:
        if segment["TechnicalCueSegment"]["Type"] == "BlackFrames":
            black_frames.append(float(segment["StartTimestampMillis"]) / 1000.0)
        elif segment["TechnicalCueSegment"]["Type"] == "EndCredits":
            end_credits.append(float(segment["StartTimestampMillis"]) / 1000.0)
    return (black_frames, end_credits)

def detect_shots(asset_metadata):
    shots = []
    for segment in asset_metadata["shotDetection"]["Segments"]:
        if segment["Type"] == "SHOT":
            shots.append(float(segment["StartTimestampMillis"]) / 1000.0)
    return shots
