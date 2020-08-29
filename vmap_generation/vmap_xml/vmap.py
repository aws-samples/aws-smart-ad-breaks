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

from vmap_xml.adbreak import AdBreak
from xml.dom.minidom import Document


class VMAP(object):
    def __init__(self, settings={}, version="1.0"):
        self.adBreaks = []
        self.version = version

    def attachAdBreak(self, settings={}):
        adBreak = AdBreak(settings)
        self.adBreaks.append(adBreak)
        return adBreak

    def xml(self):
        doc = Document()
        doc.appendChild(self.toElement(doc))
        return doc.toxml('utf-8')

    def toElement(self, doc):
        vmapElement = doc.createElementNS('http://www.iab.net/videosuite/vmap', 'vmap:VMAP')
        vmapElement.setAttribute("version", self.version)
        vmapElement.setAttribute("xmlns:vmap", "http://www.iab.net/videosuite/vmap")
        for adBreak in self.adBreaks:
            _type = adBreak.adSource["type"]
            adBreakElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:AdBreak")
            for key, value in adBreak.attributes.items():
                adBreakElement.setAttribute(key, value)
            vmapElement.appendChild(adBreakElement)

            adSourceElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:AdSource")
            adSourceElement.setAttribute("id", adBreak.adSource["_id"])
            adSourceElement.setAttribute("allowMultipleAds", adBreak.adSource["allow_mutiple_ads"])
            adSourceElement.setAttribute("followRedirects", adBreak.adSource["follow_redirects"])
            adBreakElement.appendChild(adSourceElement)
            
            adTypedElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:{type}".format(type=_type))
            for key, value in adBreak.adSource["attributes"].items():
                adTypedElement.setAttribute(key, value)
            adSourceElement.appendChild(adTypedElement)

            if _type == "VASTAdData":
                vastElement = adBreak.adSource["source"].toElement(doc)
                adTypedElement.appendChild(vastElement)
            elif _type == 'AdTagURI':
                adTypedElement.appendChild(doc.createCDATASection(adBreak.adSource["source"]))

            if len(adBreak.trackingEvents) > 0:
                trackingEventsElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:TrackingEvents")
                adBreakElement.appendChild(trackingEventsElement)
            for event in adBreak.trackingEvents:
                trackingElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:Tracking")
                trackingElement.setAttribute("event", event.event)
                trackingElement.appendChild(doc.createCDATASection(event.url))
                trackingEventsElement.appendChild(trackingElement)

        return vmapElement
