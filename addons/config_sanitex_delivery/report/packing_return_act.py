# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

# -*- coding: utf-8 -*-

import time
from odoo import api, models, _
from ..stock import utc_str_to_local_str


class PackingReturnAct(models.AbstractModel):
    _name = 'report.config_sanitex_delivery.packing_return_act'

    @api.model
    def _get_info(self, ids, data):
        route_env = self.env['stock.route']
        res = {}
        routes = route_env.browse(ids)
        for route in routes:
            info = {}
            info['receiver'] = {
                'name': route.location_id and route.location_id.name or '',
                'personal_no': '',
            }
            picking = route.get_return_act_picking()
            info['name'] = picking and picking.name or ''
            info['sender'] = route.get_return_act_owner()
            lines, total = route.get_lines_for_packing_return_act()
            info['lines'] = lines
            carrier_name = route.location_id and route.location_id.owner_id and route.location_id.owner_id.name
            carrier_ref = route.location_id and route.location_id.owner_id and route.location_id.owner_id.ref \
                and (', ' + _('comp. code') + ' ' + route.location_id.owner_id.ref)
            info['carrier'] = carrier_name + carrier_ref
            info['time_now'] = utc_str_to_local_str(picking.date[:-3], date_format='%Y-%m-%d %H:%M')
            info.update(total)
            res[route.id] = info
        return res

    @api.model
    def get_report_values(self, docids, data=None):
        route_env = self.env['stock.route']
        usr_env = self.env['res.users']
        print_log_env = self.env['report.print.log']

        company = usr_env.browse(self.env.uid).company_id
        duplicate = print_log_env.already_printed(
            'stock.route', 'config_sanitex_delivery.packing_return_act', docids
        )
        return {
            'doc_ids': docids,
            'doc_model': route_env,
            'docs': route_env.browse(docids),
            'time': time,
            'duplicate': duplicate,
            'data': data,
            'company': company,
            # 'receiver': _get_receiver,
            'get_info': self._get_info(docids, data),
        }