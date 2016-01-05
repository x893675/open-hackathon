# -*- coding: utf-8 -*-
"""
Copyright (c) Microsoft Open Technologies (Shanghai) Co. Ltd.  All rights reserved.

The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

__author__ = "rapidhere"

from azure.servicemanagement.servicemanagementservice import ServiceManagementService
from azure.common import AzureHttpError, AzureMissingResourceHttpError

from service_adapter import ServiceAdapter
from constants import ASYNC_OP_RESULT


class CloudServiceAdapter(ServiceAdapter):
    """A thin wrapper on ServiceManagementServie class

    wrap up some interface to work with Azure Cloud Service

    NOTE: the deployment must be done on a cloud service in Azure,
    so we won't split a signle deployment adapter, instead, we do it in CloudServiceAdapter
    """

    def __init__(self, subscription_id, cert_url, *args, **kwargs):
        super(CloudServiceAdapter, self).__init__(
            ServiceManagementService(subscription_id, cert_url, *args, **kwargs))

    def cloud_service_exists(self, name):
        """Link to azure and check whether specific cloud service exist in specific azure subscription

        :type name: string|unicode
        :param name: the name of the coloud service

        :rtype: boolean
        :return:
        """
        try:
            props = self.service.get_hosted_service_properties(name)
        except AzureMissingResourceHttpError:
            return False
        except Exception as e:
            self.log.error(e)
            raise e

        return props is not None

    def create_cloud_service(self, name, label, location, **extra):
        """the sync version of ServiceManagementService.create_hosted_service

        for full list of arguments, please refr to ServiceManagementService.create_hosted_service

        :rtype: boolean
        :return: True on success
        """
        # DON'T DO ERROR CHECK AS azureformation.cloudService did
        # Micrsoft has checked the error up in server side
        # you don't have to do it again
        try:
            req = self.service.create_hosted_service(
                service_name=name,
                label=label,
                location=location,
                **extra)
        except AzureHttpError as e:
            self.log.debug("create cloud service %s failed: %s" % (name, e.message))
            return False

        self.log.debug("service cloud %s, creation in progress" % name)
        res = self.service.wait_for_operation_status(
            req.request_id,
            progress_callback=None,
            success_callback=None,
            failure_callback=None)

        if res and res.status == ASYNC_OP_RESULT.SUCCEEDED:
            self.log.debug("service cloud %s, creation done" % name)
            return True
        else:
            self.log.debug("service cloud %s, creation failed" % name)
            return False

    def update_cloud_service(self):
        # TODO
        raise NotImplementedError

    def delete_cloud_service(self):
        # TODO
        raise NotImplementedError
