#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 Timu Eren <timu.eren@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from vmap_xml.events import TrackingEvent

REQURED_ATTRIBUTES = ("timeOffset", "breakType")
BREAK_TYPES = ("linear", "nonlinear", "display")

class AdBreak(object):
    def __init__(self, settings={}):
        self.attributes = {}
        self.trackingEvents = []
        self.adSource = None
        for _type in REQURED_ATTRIBUTES:
            if _type not in settings.keys():
                raise Exception("Missing attribute '{attr}' on AdBreak".format(attr=_type))

        if settings.get("breakType") not in BREAK_TYPES:
            raise Exception("Invalid breakType value, break type can be only one of them {types}"
                            .format(types=",".join(BREAK_TYPES)))

        self.attributes["timeOffset"] = settings.get("timeOffset")
        self.attributes["breakType"] = settings.get("breakType")

        if settings.get("breakId", None):
            self.attributes["breakId"] = settings.get("breakId")
        if settings.get("repeatAfter", None):
            self.attributes["repeatAfter"] = settings.get("repeatAfter", None)

    def attachAdSource(self, _id, allow_mutiple_ads, follow_redirects, _type,  source, attributes={}):
        if _type != 'VASTAdData' and "templateType" not in attributes:
            raise Exception("templateType required by {type}".format(type=_type))
        source = dict(_id=_id,
                      allow_mutiple_ads=allow_mutiple_ads,
                      follow_redirects=follow_redirects,
                      attributes=attributes,
                      source=source,
                      type=_type
        )
        self.adSource = source

    def attachEvent(self, event, url):
        self.trackingEvents.append(TrackingEvent(event, url))
