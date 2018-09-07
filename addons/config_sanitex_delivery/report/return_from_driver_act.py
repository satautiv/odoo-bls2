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


class DriverReturnAct(models.AbstractModel):
    _name = 'report.config_sanitex_delivery.driver_return_act'

    @api.model
    def _get_info(self, ids, data):
        picking_env = self.env['stock.picking']
        res = {}
        pickings = picking_env.browse(ids)
        for picking in pickings:
            info = {}
            info['receiver'] = {
                'name': picking.location_dest_id and picking.location_dest_id.name or '',
                'personal_no': '',
            }
            owners = picking.move_lines.mapped('product_id').mapped('owner_id')
            if owners:
                info['sender'] = owners[0].get_owner_dict()
            else:
                info['sender'] = {}
            lines, total = picking.get_lines_for_packing_return_act()
            info['lines'] = lines
            carrier_name = picking.location_id and picking.location_id.owner_id and picking.location_id.owner_id.name or ''
            carrier_ref = picking.location_id and picking.location_id.owner_id and picking.location_id.owner_id.ref \
                and (', ' + _('comp. code') + ' ' + picking.location_id.owner_id.ref) or ''
            info['carrier'] = carrier_name + carrier_ref
            info['route'] = ''
            info['license_plate'] = ''
            info['driver'] = picking.location_id and picking.location_id.name or ''
            info['time_now'] = utc_str_to_local_str(picking.date[:-3], date_format='%Y-%m-%d %H:%M')

            info.update(total)

            res[picking.id] = info
        return res

    @api.model
    def get_report_values(self, docids, data=None):
        picking_env = self.env['stock.picking']
        usr_env = self.env['res.users']
        print_log_env = self.env['report.print.log']

        company = usr_env.browse(self.env.uid).company_id
        duplicate = print_log_env.already_printed(
            'stock.route', 'config_sanitex_delivery.driver_return_act', docids
        )
        return {
            'doc_ids': docids,
            'doc_model': picking_env,
            'docs': picking_env.browse(docids),
            'time': time,
            'duplicate': duplicate,
            'data': data,
            'company': company,
            # 'receiver': _get_receiver,
            'get_info': self._get_info(docids, data),
        }