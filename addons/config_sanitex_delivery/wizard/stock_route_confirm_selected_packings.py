# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError

class StockRoutePackingConfirmSelected(models.TransientModel):
    _name = 'stock.route.packing.confirm_selected.osv'
    _description = 'Confirm Selected Packings' 

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_packings(self):
        route_obj = self.env['stock.route']
        route = route_obj.browse(self._get_route())
        res = []
        for packing in route.packing_for_client_ids:
            if packing.state == 'draft':
                res.append(packing.id)
            
        return res

    packing_ids = fields.Many2many(
        'stock.packing', 'stock_packing_confirm_osv_rel',
        'osv_id', 'packing_id', 'Packings to Confirm', default=_get_packings
    )
    parent_route_id = fields.Many2one(
        'stock.route', 'Route to Transfer from', default=_get_route
    )

    @api.multi
    def confirm(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        if not self.packing_ids:
            raise UserError(
                _('You have to select at least one packing')
            )
        for packing in self.packing_ids.filtered(lambda pack_rec: pack_rec.state == 'draft'):
            packing.action_done()
            if commit:
                self.env.cr.commit()
        return {'type':'ir.actions.act_window_close'}