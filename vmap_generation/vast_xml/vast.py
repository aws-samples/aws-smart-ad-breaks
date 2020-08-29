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

from vast_xml.ad import Ad
from xml.dom.minidom import Document


class VAST(object):
    def __init__(self, settings={}):
        self.ads = []
        self.version = settings.get("version", "3.0")
        self.VASTErrorURI = settings.get("VASTErrorURI", None)

    def attachAd(self, settings):
        ad = Ad(settings)
        self.ads.append(ad)
        return ad

    def xml(self):
        doc = Document()
        doc.appendChild(self.toElement(doc))
        return doc.toxml('utf-8')

    def toElement(self, doc):
        vastElement = doc.createElement("VAST")
        vastElement.setAttribute("version", self.version)
        if len(self.ads) == 0 and self.VASTErrorURI:
            errorElement = doc.createElement("Error")
            errorElement.appendChild(doc.createCDATASection(self.VASTErrorURI))
            vastElement.appendChild(errorElement)
            return vastElement
        for ad in self.ads:
            adOptions = {"id": ad.id}
            if ad.sequence:
                adOptions["sequence"] = str(ad.sequence)

            adElement = doc.createElement("Ad")
            vastElement.appendChild(adElement)

            inLineElement = doc.createElement("InLine")
            adSystemElement = doc.createElement("AdSystem")
            adSystemElement.appendChild(doc.createTextNode(ad.AdSystem["name"]))
            inLineElement.appendChild(adSystemElement)

            adTitleElement = doc.createElement("AdTitle")
            adTitleElement.appendChild(doc.createTextNode(ad.AdTitle))
            inLineElement.appendChild(adTitleElement)

            descriptionElement = doc.createElement("Description")
            descriptionElement.appendChild(doc.createCDATASection(ad.Description or ""))
            inLineElement.appendChild(descriptionElement)

            for survey in ad.surveys:
                surveyElement = doc.createElement("Survey")
                if survey.type:
                    surveyElement.setAttribute("type", survey.type)
                surveyElement.appendChild(doc.createCDATASection(survey.url))
                inLineElement.appendChild(surveyElement)

            if ad.Error:
                errorElement = doc.createElement("Error")
                errorElement.appendChild(doc.createCDATASection(ad.Error))
                inLineElement.appendChild(errorElement)

            for impression in ad.impressions:
                impressionElement = doc.createElement("Impression")
                if "url" in impression:
                    impressionElement.appendChild(doc.createCDATASection(impression["url"]))
                inLineElement.appendChild(impressionElement)

            creativesElement = doc.createElement("Creatives")
            linearCreatives = [c for c in ad.creatives if c.type == "Linear"]
            nonLinearCreatives = [c for c in ad.creatives if c.type == "NonLinear"]
            companionAdCreatives = [c for c in ad.creatives if c.type == "CompanionAd"]
            for creative in linearCreatives:
                creativeElement = doc.createElement("Creative")
                linearElement = doc.createElement("Linear")
                if creative.skipoffset:
                    linearElement.setAttribute("skipoffset", creative.skipoffset)
                if len(creative.icons) > 0:
                    iconsElement = doc.createElement("Icons")
                    linearElement.appendChild(iconsElement)
                    for icon in creative.icons:
                        iconElement = doc.createElement("Icon")
                        iconsElement.appendChild(iconElement)
                        for key, value in icon.attributes.items():
                            iconElement.setAttribute(key, value)
                        resourceElement = doc.createElement(icon.resource["type"])
                        iconElement.appendChild(resourceElement)
                        resourceElement.appendChild(doc.createCDATASection(icon.resource["uri"]))
                        if "creativeType" in icon.resource:
                            resourceElement.setAttribute("creativeType", icon.resource["creativeType"])                        
                        if icon.click or icon.clickThrough:
                            iconClicksElement = doc.createElement("IconClicks")
                            iconElement.appendChild(iconClicksElement)
                            if icon.clickThrough:
                                iconClickThroughElement = doc.createElement("IconClickThrough")
                                iconClicksElement.appendChild(iconClickThroughElement)
                                iconClickThroughElement.appendChild(doc.createCDATASection(icon.clickThrough))
                            if icon.click:
                                iconClickTrackingElement = doc.createElement("IconClickTracking")
                                iconClicksElement.appendChild(iconClickTrackingElement)
                                iconClickTrackingElement.appendChild(doc.createCDATASection(icon.click))
                        if icon.view:
                            response.IconViewTracking(self.cdata(icon.view))
                durationElement = doc.createElement("Duration")
                durationElement.appendChild(doc.createTextNode(creative.duration))
                linearElement.appendChild(durationElement)
                trackingEventsElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:TrackingEvents")
                linearElement.appendChild(trackingEventsElement)
                for event in creative.trackingEvents:
                    trackingElement = doc.createElementNS("http://www.iab.net/videosuite/vmap", "vmap:Tracking")
                    trackingElement.setAttribute("event", event.event)
                    if event.offset:
                        trackingElement.setAttribute("offset", event.offset)
                    trackingElement.appendChild(doc.createCDATASection(event.url))
                    trackingEventsElement.appendChild(trackingElement)
                if creative.AdParameters:
                    adParametersElement = doc.createElement("AdParameters")
                    adParametersElement.setAttribute("xmlEncoded", creative.AdParameters["xmlEncoded"])
                    adParametersElement.appendChild(doc.createTextNode(creative.AdParameters))
                    linearElement.appendChild(adParametersElement)
                for click in creative.videoClicks:
                    clickElement = doc.createElement(click["type"])
                    clickElement.setAttribute("id", click.get("id", ""))
                    clickElement.appendChild(doc.createCDATASection(click["url"]))
                    nonLinearElement.appendChild(clickElement)
                mediaFilesElement = doc.createElement("MediaFiles")
                for media in creative.mediaFiles:
                    mediaFileElement = doc.createElement("MediaFile")
                    mediaFileElement.appendChild(doc.createCDATASection(media["url"]))
                    for key, value in media["attributes"].items():
                        mediaFileElement.setAttribute(key, value)
                    mediaFilesElement.appendChild(mediaFileElement)
                linearElement.appendChild(mediaFilesElement)
                creativeElement.appendChild(linearElement)
                creativesElement.appendChild(creativeElement)
            
            for creative in nonLinearCreatives:
                creativeElement = doc.createElement("Creative")
                nonLinearAdsElement = doc.createElement("NonLinearAds")
                nonLinearElement = doc.createElement("NonLinear")
                for key, value in creative.attributes.items():
                    nonLinearElement.setAttribute(key, value)
                for resource in creative.resources:
                    resourceElement = doc.createElement(resource["type"])
                    if "creativeType" in resource:
                        resourceElement.setAttribute("creativeType", resource["creativeType"])
                    resourceElement.appendChild(doc.createCDATASection(resource["uri"]))
                    nonLinearElement.appendChild(resourceElement)
                for click in creative.clicks:
                    clickElement = doc.createElement(click["type"])
                    clickElement.appendChild(doc.createCDATASection(click["uri"]))
                    nonLinearElement.appendChild(clickElement)
                if creative.AdParameters:
                    adParametersElement = doc.createElement("AdParameters")
                    adParametersElement.setAttribute("xmlEncoded", creative.AdParameters["xmlEncoded"])
                    adParametersElement.appendChild(doc.createTextNode(creative.AdParameters["data"]))
                    nonLinearElement.appendChild(adParametersElement)
                if creative.nonLinearClickThrough:
                    clickThroughElement = doc.createElement("NonLinearClickThrough")
                    clickThroughElement.appendChild(doc.createCDATASection(creative.nonLinearClickThrough))
                    nonLinearElement.appendChild(clickThroughElement)
                if creative.nonLinearClickTracking:
                    clickTrackingElement = doc.createElement("NonLinearClickTracking")
                    clickTrackingElement.appendChild(doc.createCDATASection(creative.nonLinearClickTracking))
                    nonLinearElement.appendChild(clickTrackingElement)
                nonLinearAdsElement.appendChild(nonLinearElement)
                creativeElement.appendChild(nonLinearAdsElement)
                creativesElement.appendChild(creativeElement)

            if len(companionAdCreatives) > 0:
                companionAdsElement = doc.createElement("CompanionAds")
                for creative in companionAdCreatives:
                    companionElement = doc.createElement("Companion")
                    for key, value in creative.attributes.items():
                        companionElement.setAttribute(key, value)
                        for resource in creative.resources:
                            resourceElement = doc.createElement(resource["type"])
                            if "creativeType" in resource:
                                resourceElement.setAttribute("creativeType", resource["creativeType"])
                            resourceElement.appendChild(doc.createCDATASection(resource["uri"]))
                            companionElement.appendChild(resourceElement)
                            if "adParameters" in resource:
                                adParametersElement = doc.createElement("AdParameters")
                                adParametersElement.setAttribute("xmlEncoded", resource["adParameters"]["xmlEncoded"])
                                adParametersElement.appendChild(doc.createTextNode(resource["adParameters"]["data"]))
                                companionElement.appendChild(adParametersElement)
                        for click in creative.clickThroughs:
                            clickThroughElement = doc.createElement("CompanionClickThrough")
                            clickThroughElement.appendChild(doc.createCDATASection(click))
                            companionElement.appendChild(clickThroughElement)
                        if creative.nonLinearClickTracking:
                            clickTrackingElement = doc.createElement("CompanionClickTracking")
                            clickTrackingElement.appendChild(doc.createCDATASection(creative.nonLinearClickTracking))
                            companionElement.appendChild(clickTrackingElement)
                    companionAdsElement.appendChild(companionElement)
                creativesElement.appendChild(companionAdsElement)

            inLineElement.appendChild(creativesElement)
            adElement.appendChild(inLineElement)
        return vastElement
