# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

###############################################################################
# PURPOSE:
#   This operator uses MediaConvert to do four things:
#     1) transcode video into an HLS playlist to be used with MediaTailor
#     2) transcode video into an MP4 format supported by Rekognition
#     3) extract audio track from video (with loudness analysis)
#   The transcode MP4 video is a "proxy encode" and is used by Rekognition
#   operators instead of the original video uploaded by a user.
#
# OUTPUT:
#   Audio will be saved to the following path:
#       "s3://" + $DATAPLANE_BUCKET + "/private/assets/"" + asset_id + "/workflows/" + workflow_id + "/"
#
###############################################################################

import os
import boto3

from MediaInsightsEngineLambdaHelper import MediaInsightsOperationHelper
from MediaInsightsEngineLambdaHelper import MasExecutionError

region = os.environ['AWS_REGION']
mediaconvert_role = os.environ['MEDIA_CONVERT_ROLE_ARN']

mediaconvert = boto3.client("mediaconvert", region_name=region)

def lambda_handler(event, context):
    print("We got the following event:\n", event)
    operator_object = MediaInsightsOperationHelper(event)

    try:
        workflow_id = str(operator_object.workflow_execution_id)
        asset_id = operator_object.asset_id
        bucket = operator_object.input["Media"]["Video"]["S3Bucket"]
        key = operator_object.input["Media"]["Video"]["S3Key"]
    except KeyError as e:
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(VideoTranscodingError="Missing a required metadata key {e}".format(e=e))
        raise MasExecutionError(operator_object.return_output_object())

    file_input = "s3://" + bucket + "/" + key
    hls_destination = "s3://" + bucket + "/private/assets/" + asset_id + "/hls/playlist"
    proxy_destination = "s3://" + bucket + "/private/assets/" + asset_id + "/proxy/" + asset_id
    audio_destination = "s3://" + bucket + "/private/assets/" + asset_id + "/audio/" + asset_id

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

    try:
        response = customer_mediaconvert.create_job(
            Role=mediaconvert_role,
            Settings={
                "OutputGroups": [
                    {
                        "Name": "Apple HLS",
                        "Outputs": [
                            {
                                "Preset": "System-Avc_16x9_1080p_29_97fps_8500kbps",
                                "NameModifier": "_hls"
                            }
                        ],
                        "OutputGroupSettings": {
                            "Type": "HLS_GROUP_SETTINGS",
                            "HlsGroupSettings": {
                                "ManifestDurationFormat": "INTEGER",
                                "SegmentLength": 1,
                                "TimedMetadataId3Period": 10,
                                "CaptionLanguageSetting": "OMIT",
                                "TimedMetadataId3Frame": "PRIV",
                                "CodecSpecification": "RFC_4281",
                                "OutputSelection": "MANIFESTS_AND_SEGMENTS",
                                "ProgramDateTimePeriod": 600,
                                "MinSegmentLength": 0,
                                "MinFinalSegmentLength": 0,
                                "DirectoryStructure": "SINGLE_DIRECTORY",
                                "ProgramDateTime": "EXCLUDE",
                                "SegmentControl": "SEGMENTED_FILES",
                                "ManifestCompression": "NONE",
                                "ClientCache": "ENABLED",
                                "StreamInfResolution": "INCLUDE",
                                "Destination": hls_destination
                            }
                        }
                    },
                    {
                        "CustomName": "Proxy",
                        "Name": "File Group",
                        "Outputs": [
                            {
                                "VideoDescription": {
                                    "ScalingBehavior": "DEFAULT",
                                    "TimecodeInsertion": "DISABLED",
                                    "AntiAlias": "ENABLED",
                                    "Sharpness": 50,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "InterlaceMode": "PROGRESSIVE",
                                            "NumberReferenceFrames": 3,
                                            "Syntax": "DEFAULT",
                                            "Softness": 0,
                                            "GopClosedCadence": 1,
                                            "GopSize": 90,
                                            "Slices": 1,
                                            "GopBReference": "DISABLED",
                                            "SlowPal": "DISABLED",
                                            "SpatialAdaptiveQuantization": "ENABLED",
                                            "TemporalAdaptiveQuantization": "ENABLED",
                                            "FlickerAdaptiveQuantization": "DISABLED",
                                            "EntropyEncoding": "CABAC",
                                            "Bitrate": 5000000,
                                            "FramerateControl": "SPECIFIED",
                                            "RateControlMode": "CBR",
                                            "CodecProfile": "MAIN",
                                            "Telecine": "NONE",
                                            "MinIInterval": 0,
                                            "AdaptiveQuantization": "HIGH",
                                            "CodecLevel": "AUTO",
                                            "FieldEncoding": "PAFF",
                                            "SceneChangeDetect": "ENABLED",
                                            "QualityTuningLevel": "SINGLE_PASS",
                                            "FramerateConversionAlgorithm": "DUPLICATE_DROP",
                                            "UnregisteredSeiTimecode": "DISABLED",
                                            "GopSizeUnits": "FRAMES",
                                            "ParControl": "SPECIFIED",
                                            "NumberBFramesBetweenReferenceFrames": 2,
                                            "RepeatPps": "DISABLED",
                                            "FramerateNumerator": 30,
                                            "FramerateDenominator": 1,
                                            "ParNumerator": 1,
                                            "ParDenominator": 1
                                        }
                                    },
                                    "AfdSignaling": "NONE",
                                    "DropFrameTimecode": "ENABLED",
                                    "RespondToAfd": "NONE",
                                    "ColorMetadata": "INSERT"
                                },
                                "AudioDescriptions": [
                                    {
                                        "AudioTypeControl": "FOLLOW_INPUT",
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "AudioDescriptionBroadcasterMix": "NORMAL",
                                                "RateControlMode": "CBR",
                                                "CodecProfile": "LC",
                                                "CodingMode": "CODING_MODE_2_0",
                                                "RawFormat": "NONE",
                                                "SampleRate": 48000,
                                                "Specification": "MPEG4",
                                                "Bitrate": 64000
                                            }
                                        },
                                        "LanguageCodeControl": "FOLLOW_INPUT",
                                        "AudioSourceName": "Audio Selector 1"
                                    }
                                ],
                                "ContainerSettings": {
                                    "Container": "MP4",
                                    "Mp4Settings": {
                                        "CslgAtom": "INCLUDE",
                                        "FreeSpaceBox": "EXCLUDE",
                                        "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                                    }
                                },
                                "Extension": "mp4",
                                "NameModifier": "_proxy"
                            }
                        ],
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {
                                "Destination": proxy_destination
                            }
                        }
                    },
                    {
                        "CustomName": "Audio",
                        "Name": "File Group",
                        "Outputs": [
                            {
                                "ContainerSettings": {
                                    "Container": "MP4",
                                    "Mp4Settings": {
                                        "CslgAtom": "INCLUDE",
                                        "CttsVersion": 0,
                                        "FreeSpaceBox": "EXCLUDE",
                                        "MoovPlacement": "PROGRESSIVE_DOWNLOAD"
                                    }
                                },
                                "AudioDescriptions": [
                                    {
                                        "AudioTypeControl": "FOLLOW_INPUT",
                                        "AudioSourceName": "Audio Selector 1",
                                        "AudioNormalizationSettings": {
                                            "Algorithm": "ITU_BS_1770_2",
                                            "AlgorithmControl": "MEASURE_ONLY",
                                            "LoudnessLogging": "LOG",
                                            "PeakCalculation": "NONE"
                                        },
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "AudioDescriptionBroadcasterMix": "NORMAL",
                                                "Bitrate": 96000,
                                                "RateControlMode": "CBR",
                                                "CodecProfile": "LC",
                                                "CodingMode": "CODING_MODE_2_0",
                                                "RawFormat": "NONE",
                                                "SampleRate": 48000,
                                                "Specification": "MPEG4"
                                            }
                                        },
                                        "LanguageCodeControl": "FOLLOW_INPUT"
                                    }
                                ],
                                "Extension": "mp4",
                                "NameModifier": "_audio"
                            }
                        ],
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {
                                "Destination": audio_destination
                            }
                        }
                    }
                ],
                "Inputs": [{
                    "AudioSelectors": {
                        "Audio Selector 1": {
                            "Offset": 0,
                            "DefaultSelection": "DEFAULT",
                            "ProgramSelection": 1
                        }
                    },
                    "VideoSelector": {
                        "ColorSpace": "FOLLOW",
                        "Rotate": "DEGREE_0",
                        "AlphaBehavior": "DISCARD"
                    },
                    "FilterEnable": "AUTO",
                    "PsiControl": "USE_PSI",
                    "FilterStrength": 0,
                    "DeblockFilter": "DISABLED",
                    "DenoiseFilter": "DISABLED",
                    "TimecodeSource": "EMBEDDED",
                    "FileInput": file_input
                }]
            }
        )
    # TODO: Add support for boto client error handling
    except Exception as e:
        print("Exception:\n", e)
        operator_object.update_workflow_status("Error")
        operator_object.add_workflow_metadata(VideoTranscodingError=str(e))
        raise MasExecutionError(operator_object.return_output_object())
    else:
        job_id = response['Job']['Id']
        operator_object.update_workflow_status("Executing")
        operator_object.add_workflow_metadata(VideoTranscodingJobId=job_id, VideoTranscodingInputFile=file_input, AssetId=asset_id, WorkflowExecutionId=workflow_id)
        return operator_object.return_output_object()