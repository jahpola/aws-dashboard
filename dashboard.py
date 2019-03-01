#!/usr/bin/env python3
# pylint: disable=C0301,C0111

"""
A script for rendering AWS dashboards to be viewed without logging in.
"""

import base64
import datetime
import json
import logging
import sys
import os

import boto3
from botocore.exceptions import ClientError

__author__ = "Markus Koskinen&Jyrki Ahpola"
__license__ = "BSD"

www_bucket = os.getenv('www_bucket', 'jahp-foobar')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def store_to_s3(data,www_bucket):
    try:
        s3 = boto3.resource('s3')
        content = s3.Object(www_bucket,"index.html")
        content.put(Body=data,ContentType='text/html')
    except ClientError as e:
        logging.error("Writing to S3 failed: %s", e)
        raise Exception

def syntax(execname):
    print("Syntax: %s [dashboard_name]" % execname)
    sys.exit(1)

def auth():
    """ TODO: This not quite how it should be done. """
    try:
        api = boto3.client('cloudwatch')
    except ClientError as e:
        logging.error("Client error: %s", e)
        raise Exception
    else:
        return api

def get_dashboard_images(dashboard_name="all", encode_base64=True):
    """ Returns a list of base64 encoded PNGs of dashboard metrics. """
    cloudwatch_api = auth()

    dashboard_list = [d['DashboardName'] for d in cloudwatch_api.list_dashboards()['DashboardEntries']]

    logger.info("Dashboards available: %s Rendering: %s", dashboard_list, dashboard_name)

    if dashboard_name != "all" and dashboard_name in dashboard_list:
        dashboard_list = [dashboard_name]

    dashboard_widget_properties = {}
    dashboard_images = {}

    logger.debug("Dashboards available: %s ", dashboard_list)

    for dashboard in dashboard_list:
        dashboard_widget_properties[dashboard] = [dp['properties'] for dp in json.loads(cloudwatch_api.get_dashboard(DashboardName=dashboard)['DashboardBody'])['widgets'] if 'metrics' in dp['properties']]
        dashboard_images[dashboard] = []

        for dashboard_widget_property in dashboard_widget_properties[dashboard]:
            logger.debug(json.dumps(dashboard_widget_property))

            dashboard_image = cloudwatch_api.get_metric_widget_image(MetricWidget=json.dumps(dashboard_widget_property))['MetricWidgetImage']

            if encode_base64:
                dashboard_image = base64.b64encode(dashboard_image).decode('utf-8')

            dashboard_images[dashboard].append(dashboard_image)

    result = [item for sublist in dashboard_images.values() for item in sublist]
    logger.info("Result size: %d ", len(result))

    return result

def main(event, context):
    """ Outputs a HTML page to stdout with inline base64 encoded PNG dashboards. """
    dashboard_name = "all"

    result = "<html>\n"

    start_time = datetime.datetime.now()
    result += "<!-- Generation started: " + start_time.isoformat() + " -->\n"

    for image in get_dashboard_images(dashboard_name=dashboard_name):
        result += "  <img src='data:image/png;base64," + str(image) + "' />\n"

    end_time = datetime.datetime.now()
    result += "<!-- Generation ended: " + end_time.isoformat() + " -->\n"
    result += "</html>\n"
    
    logger.info("Completed. Start time: %s Runtime: %s ", start_time, str(end_time-start_time))

    store_to_s3(result,www_bucket)
    
    response = {
        "statusCode": 200,
        "body": "Foo"
    }
    
    return response
