# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import boto3
import botocore
import cv2
import numpy as np

s3 = boto3.client("s3")

def detect_fades(frames_bucket, frames_key):
    print("detect_fades: " + frames_bucket + "/" + frames_key)
    threshold = float(os.environ["LUMINANCE_THRESHOLD"]) * 100.0
    min_percent = float(os.environ["IMAGE_RATIO_THRESHOLD"])
    max_change_rate = float(os.environ["FRAME_CHANGE_THRESHOLD"])
    frames_per_second = float(os.environ["FRAMES_PER_SECOND"])
    num_rows = 32 # Num. of rows to sum per iteration.
    last_amt = -1 # Number of pixel values above threshold in last frame.
    print("threshold: {}".format(threshold))
    print("min_percent: {}".format(min_percent))
    print("max_change_rate: {}".format(max_change_rate))
    
    i = 0
    fade_ins = []
    fade_outs = []

    while True:
        # Get next frame from video.
        rv, im = __download_frame(frames_bucket, frames_key, i)
        if not rv: # im is a valid image if and only if rv is true
            break

        # Compute # of pixel values and minimum amount to trigger fade.
        num_pixel_vals = float(im.shape[0] * im.shape[1] * im.shape[2])
        min_pixels = int(num_pixel_vals * (1.0 - min_percent))

        # Loop through frame block-by-block, updating current sum.
        frame_amt = 0
        curr_row = 0
        while curr_row < im.shape[0]:
            # Add # of pixel values in current block above the threshold.
            frame_amt += np.sum(
                im[curr_row : curr_row + num_rows, :, :] > threshold)
            if frame_amt > min_pixels: # We can avoid checking the rest of the
                break # frame since we crossed the boundary.
            curr_row += num_rows

        # Initializes in first iteration
        if last_amt < 0:
            last_amt = frame_amt
        # Detect fade in from black.
        if last_amt < min_pixels <= frame_amt:
            change_rate = (frame_amt - last_amt) / num_pixel_vals
            print("change_rate: {}".format(change_rate))
            if (change_rate < max_change_rate):
                print("* Detected fade in at %dms (frame %d)." % (
                    round(i / frames_per_second * 1000.0, 3),
                    i))
                fade_ins.append(round(i / frames_per_second, 3))

        # Detect fade out to black.
        elif frame_amt < min_pixels <= last_amt:
            change_rate = (last_amt - frame_amt) / num_pixel_vals
            print("change_rate: {}".format(change_rate))
            if change_rate < max_change_rate:
                print("* Detected fade out at %dms (frame %d)." % (
                    round(i / frames_per_second * 1000.0, 3),
                    i))
                fade_outs.append(round(i / frames_per_second, 3))

        last_amt = frame_amt # Store current mean to compare in next iteration.
        i += 1

    print("fade_ins: {}".format(fade_ins))
    print("fade_outs: {}".format(fade_outs))
    return (fade_ins, fade_outs)

def __download_frame(bucket, key, i):
    tmp_file = "/tmp/frame.jpg"
    try:
        s3.download_file(
            bucket,
            ".".join(key.split(".")[:-1]) + "." + "{:07d}".format(i) + "." + key.split(".")[-1],
            tmp_file
        )
        return True, cv2.imread(tmp_file)
    except botocore.exceptions.ClientError as error:
        if error.response['ResponseMetadata']['HTTPStatusCode'] in [403, 404]:
            return False, None
        print("error: {}".format(error))
        raise error