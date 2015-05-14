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

import sys

sys.path.append("..")
from hackathon.database.models import Hackathon, User, UserHackathonRel, AdminHackathonRel
from hackathon.database import db_adapter
from hackathon.functions import get_now
from hackathon.enum import RGStatus
from hackathon.hackathon_response import *
from hackathon.enum import ADMIN_ROLE_TYPE
from sqlalchemy import or_
from hackathon.constants import HTTP_HEADER
from flask import request, g
import json
from hackathon.constants import HACKATHON_BASIC_INFO
import imghdr
from hackathon.functions import get_config, safe_get_config
from hackathon.azureformation.fileService import create_container_in_storage, upload_file_to_azure
import uuid
import time


class HackathonManager():
    def __init__(self, db):
        self.db = db

    def get_hackathon_by_name_or_id(self, hack_id=None, name=None):
        if hack_id is None:
            return self.get_hackathon_by_name(name)
        return self.get_hackathon_by_id(hack_id)

    def get_hackathon_by_name(self, name):
        return self.db.find_first_object_by(Hackathon, name=name)

    def get_hackathon_by_id(self, hackathon_id):
        return self.db.find_first_object_by(Hackathon, id=hackathon_id)

    def get_hackathon_stat(self, hackathon):
        reg_list = hackathon.registers.filter(UserHackathonRel.deleted != 1,
                                              UserHackathonRel.status.in_([RGStatus.AUTO_PASSED,
                                                                           RGStatus.AUDIT_PASSED])).all()

        reg_count = len(reg_list)
        stat = {
            "total": reg_count,
            "hid": hackathon.id,
            "online": 0,
            "offline": reg_count
        }

        if reg_count > 0:
            user_id_list = [r.user_id for r in reg_list]
            user_id_online = self.db.count(User, (User.id.in_(user_id_list) & (User.online == 1)))
            stat["online"] = user_id_online
            stat["offline"] = reg_count - user_id_online

        return stat

    def get_hackathon_list(self, user_id=None, status=None):
        status_cond = Hackathon.status == status if status is not None else Hackathon.status > -1
        user_cond = or_(UserHackathonRel.user_id == user_id, UserHackathonRel.user_id == None)

        if user_id is None:
            return [r.dic() for r in self.db.find_all_objects(Hackathon, status_cond)]

        hackathon_with_user_list = self.db.session.query(Hackathon, UserHackathonRel). \
            outerjoin(UserHackathonRel, UserHackathonRel.user_id == user_id) \
            .filter(UserHackathonRel.deleted != 1, status_cond, user_cond) \
            .all()

        def to_dict(hackathon, register):
            dic = hackathon.dic()
            if register is not None:
                dic["registration"] = register.dic()

            return dic

        return map(lambda (hack, reg): to_dict(hack, reg), hackathon_with_user_list)


    def get_user_hackathon_list(self, user_id):
        user_hack_list = self.db.session.query(Hackathon, UserHackathonRel) \
            .outerjoin(UserHackathonRel, UserHackathonRel.user_id == user_id) \
            .filter(UserHackathonRel.deleted != 1, UserHackathonRel.user_id == user_id).all()

        return [h.dic() for h in user_hack_list]

    def get_permitted_hackathon_list_by_admin_user_id(self, user_id):
        hackathon_ids = self.get_permitted_hackathon_ids_by_admin_user_id(user_id)
        if -1 in hackathon_ids:
            hackathon_list = db_adapter.find_all_objects(Hackathon)
        else:
            hackathon_list = db_adapter.find_all_objects(Hackathon, Hackathon.id.in_(hackathon_ids))

        return map(lambda u: u.dic(), hackathon_list)

    def get_permitted_hackathon_ids_by_admin_user_id(self, user_id):
        # get AdminUserHackathonRels from query withn filter by email
        admin_user_hackathon_rels = self.db.find_all_objects_by(AdminHackathonRel, user_id=user_id)

        # get hackathon_ids_from AdminUserHackathonRels details
        hackathon_ids = map(lambda x: x.hackathon_id, admin_user_hackathon_rels)

        return list(set(hackathon_ids))


    # check the admin authority on hackathon
    def __validate_admin_privilege(self, user_id, hackathon_id):
        hack_ids = self.get_permitted_hackathon_ids_by_admin_user_id(user_id)
        return -1 in hack_ids or hackathon_id in hack_ids

    def validate_admin_privilege(self):
        return self.__validate_admin_privilege(g.user.id, g.hackathon.id)

    def validate_hackathon_name(self):
        if HTTP_HEADER.HACKATHON_NAME in request.headers:
            try:
                hackathon_name = request.headers[HTTP_HEADER.HACKATHON_NAME]
                hackathon = hack_manager.get_hackathon_by_name(hackathon_name)
                if hackathon is None:
                    log.debug("cannot find hackathon by name %s" % hackathon_name)
                    return False
                else:
                    g.hackathon = hackathon
                    return True
            except Exception:
                log.debug("hackathon_name invalid")
                return False
        else:
            log.debug("hackathon_name not found in headers")
            return False

    def is_auto_approve(self, hackathon):
        try:
            basic_info = json.loads(hackathon.basic_info)
            return basic_info[HACKATHON_BASIC_INFO.AUTO_APPROVE] == 1
        except Exception as e:
            log.error(e)
            log.warn("cannot load auto_approve from basic info for hackathon %d, will return False" % hackathon.id)
            return False

    def is_recycle_enabled(self, hackathon):
        try:
            basic_info = json.loads(hackathon.basic_info)
            return basic_info[HACKATHON_BASIC_INFO.RECYCLE_ENABLED] == 1
        except Exception as e:
            log.error(e)
            log.warn("cannot load recycle_enabled from basic info for hackathon %d, will return False" % hackathon.id)
            return False


    def create_new_hackathon(self, args):
        log.debug("create_or_update_hackathon: %r" % args)
        if "name" not in args:
            return bad_request("hackathon name already exist")
        hackathon = self.get_hackathon_by_name(args['name'])
        try:
            if hackathon is None:
                log.debug("add a new hackathon:" + str(args))
                args['update_time'] = get_now()
                args['create_time'] = get_now()
                args["creator_id"] = g.user.id
                new_hack = self.db.add_object_kwargs(Hackathon, **args)  # insert into hackathon
                try:
                    ahl = AdminHackathonRel(user_id=g.user.id,
                                            role_type=ADMIN_ROLE_TYPE.ADMIN,
                                            hackathon_id=new_hack.id,
                                            status=1,
                                            remarks='creator',
                                            create_time=get_now())
                    self.db.add_object(ahl)
                except Exception as ex:
                    # TODO: send out a email to remind administrator to deal with this problems
                    log.error(ex)
                    return internal_server_error("fail to insert a recorde into admin_hackathon_rel")

                return new_hack.id

        except Exception as  e:
            log.error(e)
            return internal_server_error("fail to create hackathon")

    def update_hackathon(self, args):
        log.debug("create_or_update_hackathon: %r" % args)
        if "name" not in args or "id" not in args:
            return bad_request("name or id are both required when update a hackathon")

        hackathon = self.db.find_first_object(Hackathon, Hackathon.name == args['name'])

        if hackathon.id != args['id']:
            return bad_request("name and id are not matched in hackathon")

        try:
            update_items = dict(dict(args).viewitems() - hackathon.dic().viewitems())

            if "basic_info" in update_items:
                args['basic_info'] = json.dumps(args['basic_info'])
            if "extra_info" in update_items:
                args['extra_info'] = json.dumps(args['extra_info'] if "extra_info" in args else {})

            update_items['update_time'] = get_now()
            update_items.pop('creator_id')
            update_items.pop('create_time')
            update_items.pop('id')
            log.debug("update a exist hackathon :" + str(args))
            result = self.db.update_object(hackathon, **update_items)
            return ok("update hackathon succeed")

        except Exception as  e:
            log.error(e)
            return internal_server_error("fail to update hackathon")


    def upload_images_validate(self):

        # check storage account
        if get_config("storage.account_name") is None or get_config("storage.account_key") is None:
            return internal_server_error("storage accout  does not initialised")

        #check size
        if request.content_length > len(request.files) * get_config("storage.size_limit_byte"):
            return bad_request("more than the file size limited")

        # check each file type
        for file_name in request.files:
            if imghdr.what(request.files.get(file_name)) is None:
                return bad_request("only images can be uploaded")

    def upload_files(self):

        self.upload_images_validate()

        image_container_name = safe_get_config("storage.image_container", "images")
        # create a public container
        create_container_in_storage(image_container_name, 'container')

        images = []
        for file_name in request.files:
            file = request.files.get(file_name)

            # refresh file_name = hack_name + uuid(10) + time + suffix
            real_name = g.hackathon.name + "/" + \
                        str(uuid.uuid1())[0:9] + \
                        time.strftime("%Y%m%d%H%M%S") + "." + \
                        imghdr.what(request.files.get(file_name))

            log.debug("upload image file : " + real_name )
            url = upload_file_to_azure(file, image_container_name, real_name)

            if url is not None:
                image = {}
                image['name'] = file_name
                image['url'] = url
                # frontUI components needed return values
                image['type'] = 'image'
                image['size'] = '1024'
                image['thumbnailUrl'] = url
                image['deleteUrl'] = '/api/file?key=' + file_name

                images.append(image)
            else:
                log.error("upload file raised an exception")
                return internal_server_error("upload file raised an exception")

        return images


hack_manager = HackathonManager(db_adapter)


def is_auto_approve(hackathon):
    return hack_manager.is_auto_approve(hackathon)


def is_recycle_enabled(hackathon):
    return hack_manager.is_recycle_enabled(hackathon)


Hackathon.is_auto_approve = is_auto_approve
Hackathon.is_recycle_enabled = is_recycle_enabled

