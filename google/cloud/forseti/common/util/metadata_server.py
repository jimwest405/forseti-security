# Copyright 2017 The Forseti Security Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Metadata server utilities.

The metadata server is only accessible on GCE.
"""

import httplib
import socket

from google.auth.compute_engine import _metadata
from google.auth.transport import requests

from google.cloud.forseti.common.util import errors
from google.cloud.forseti.common.util import logger

METADATA_SERVER_HOSTNAME = 'metadata.google.internal'
METADATA_SERVER_CONN_TIMEOUT = 2
REQUIRED_METADATA_HEADER = {'Metadata-Flavor': 'Google'}
HTTP_SUCCESS = httplib.OK
HTTP_GET = 'GET'

LOGGER = logger.get_logger(__name__)


def _obtain_http_client(hostname=METADATA_SERVER_HOSTNAME):
    """Get an HTTP client to the GCP metadata server.

    Args:
        hostname (str): A qualified hostname.

    Returns:
        HttpClient: A simple HTTP client to the GCP metadata server.
    """
    return httplib.HTTPConnection(hostname,
                                  timeout=METADATA_SERVER_CONN_TIMEOUT)


def _issue_http_request(method, path, headers):
    """Perform a request on a specified httplib connection object.

    Args:
        method (str): The http request method.
        path (str): The path on the server.
        headers (dict): A key-value pairs of headers.

    Returns:
        httplib.HTTPResponse: The HTTP response object.

    Raises:
        MetadataServerHttpError: When we can't reach the requested host.
    """
    http_client = _obtain_http_client()
    try:
        http_client.request(method, path, headers=headers)
        return http_client.getresponse()
    except (socket.error, httplib.HTTPException) as e:
        LOGGER.error('Error with request: %s', e)
        raise errors.MetadataServerHttpError


# TODO: Should use memoize or similar so that after the first check
# the cached result is always returned, regardless of how often it is
# called.
def can_reach_metadata_server():
    """Determine if we can reach the metadata server.

    Returns:
        bool: True if metadata server can be reached, False otherwise.
    """
    can_reach = _metadata.ping(requests.Request())
    return can_reach


def get_value_for_attribute(attribute):
    """For a given key return the value.

    Args:
        attribute (str): Some metadata key.

    Returns:
        str: The value of the requested key, if key isn't present then None.
    """
    path = '/computeMetadata/v1/instance/attributes/%s' % attribute
    try:
        http_response = _issue_http_request(
            HTTP_GET, path, REQUIRED_METADATA_HEADER)
        return http_response.read()
    except (TypeError, ValueError,
            errors.MetadataServerHttpError) as e:
        LOGGER.error('Unable to read value for attribute key %s '
                     'from metadata server: %s', attribute, e)
        return None


def get_project_id():
    """Get the project id from the metadata server.

    Returns:
        str: The of the project id, on error, returns None.
    """
    path = '/computeMetadata/v1/project/project-id'
    try:
        http_response = _issue_http_request(
            HTTP_GET, path, REQUIRED_METADATA_HEADER)
        return http_response.read()
    except errors.MetadataServerHttpError as e:
        LOGGER.error('Unable to read project id from metadata server: %s', e)
        return None
