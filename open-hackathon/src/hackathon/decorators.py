# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------------
# Copyright (c) Microsoft Open Technologies (Shanghai) Co. Ltd.  All rights reserved.
#
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------------

from user import user_manager
from hackathon_response import *
from hack import hack_manager

"""
user must login when this decorator is enabled (for both user and admin)
"""


def token_required(func):
    def authenticate_and_call(*args, **kwargs):
        if not user_manager.validate_login():
            return unauthorized("login required")
        return func(*args, **kwargs)

    return authenticate_and_call


"""
hackathon_name must be included in header when this decorator is enabled
"""


def hackathon_name_required(func):
    def authenticate_and_call(*args, **kwargs):
        if not hack_manager.validate_hackathon_name():
            return bad_request("hackathon name invalid")
        return func(*args, **kwargs)

    return authenticate_and_call


"""
user must login , hackathon_name must be available, and 'user' has proper admin privilege on this hackathon
"""


def admin_privilege_required(func):
    def authenticate_and_call(*args, **kwargs):
        if not user_manager.validate_login():
            return unauthorized("login required")

        if not hack_manager.validate_hackathon_name():
            return bad_request("hackathon name invalid")

        if not hack_manager.validate_admin_privilege():
            return access_denied("access denied")
        return func(*args, **kwargs)

    return authenticate_and_call
