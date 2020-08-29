# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import tempfile
import boto3

s3 = boto3.client("s3")

def detect_silences(loudness_bucket, loudness_key):
    start_threshold = float(os.environ['START_THRESHOLD_IN_SECONDS'])
    # silent audio has loudness lower than threshold
    silent_threshold = float(os.environ['SILENT_THRESHOLD'])
    silences = []
    with tempfile.TemporaryFile() as tmp:
        s3.download_fileobj(loudness_bucket, loudness_key, tmp)
        tmp.seek(0)
        is_silent = False
        for line in tmp.readlines()[1:]:
            line = line.decode('utf-8')
            short_term_loudness = float(line.split(',')[3])
            if short_term_loudness < silent_threshold:
                if not is_silent:
                    second = float(line.split(',')[0])
                    if second > start_threshold:
                        silences.append(second)
                        is_silent = True
            else:
                is_silent = False
    return silences