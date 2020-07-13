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

from adbreak import AdBreak
from lxml import etree

class VMAP(object):
    def __init__(self, settings={}, version="1.0"):
        self.adBreaks = []
        self.version = version

    def attachAdBreak(self, settings={}):
        adBreak = AdBreak(settings)
        self.adBreaks.append(adBreak)
        return adBreak

    def xml(self):
        element = etree.Element('{http://www.iab.net/videosuite/vmap}VMAP', version=self.version, nsmap={
            "vmap": "http://www.iab.net/videosuite/vmap"
        })
        for adBreak in self.adBreaks:
            _type = adBreak.adSource["type"]
            adBreakElement = etree.SubElement(element, "{http://www.iab.net/videosuite/vmap}AdBreak",
                                              **adBreak.attributes)
            adSourceElement = etree.SubElement(adBreakElement, "{http://www.iab.net/videosuite/vmap}AdSource",
                                               {'id': adBreak.adSource['_id'],
                                                'allowMultipleAds': adBreak.adSource['allow_mutiple_ads'],
                                                'followRedirects': adBreak.adSource['follow_redirects']})
            adTypedElement = etree.SubElement(adSourceElement,
                                              "{{http://www.iab.net/videosuite/vmap}}{type}".format(type=_type),
                                              **adBreak.adSource["attributes"])
            if _type == "VASTAdData":
                adTypedElement.append(etree.fromstring(adBreak.adSource["source"]))
            elif _type == 'AdTagURI':
                adTypedElement.text = etree.CDATA(adBreak.adSource["source"])
            elif _type == 'CustomAdData':
                adTypedElement.append(etree.CDATA(etree.fromstring(adBreak.adSource["source"])))

            if len(adBreak.trackingEvents) > 0:
                trackigEventsElem = etree.SubElement(adBreakElement, "{http://www.iab.net/videosuite/vmap}TrackingEvents")
            for event in adBreak.trackingEvents:
                trackingElem = etree.SubElement(trackigEventsElem, "{http://www.iab.net/videosuite/vmap}Tracking",
                                                **{"event": event.event})
                trackingElem.text = etree.CDATA(event.url)

        return etree.tostring(element, pretty_print=False)
