# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError

import time

class StockRouteTransferOrders(models.TransientModel):
    _name = 'stock.route.transfer_orders.osv'
    _description = 'Transfer Orders to another Route' 

    @api.model
    def _get_orders(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'])
            return route.sale_ids.mapped('id')
        return context.get('order_ids', [])

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]
    
    order_ids = fields.Many2many(
        'sale.order', 'sale_order_route_transfer_osv_rel',
        'sale_id', 'osv_id', 'Orders to Transfer', default=_get_orders
    )
    route_id = fields.Many2one(
        'stock.route', 'Route to Transfer for', required=True, ondelete='cascade'
    )
    domain_order_ids = fields.Many2many(
        'sale.order', 'sale_order_route_transfer_domain_osv_rel',
        'osv_id', 'sale_id', 'Orders to Transfer(Domain)'
    )
    parent_route_id = fields.Many2one(
        'stock.route', 'Route to Transfer from', default=_get_route
    )
    today = fields.Date('Today', default=lambda self: time.strftime('%Y-%m-%d'))

    @api.multi
    def transfer(self):
        context = self.env.context or {}
        ctx_skip = context.copy()
        ctx_skip['skip_packing_remove'] = True

        if context.get('active_ids', False):
            if not self.order_ids:
                raise UserError(
                    _('You have to select at least one order')
                )
            if self.route_id.state != 'draft':
                raise UserError(
                    _('Selected route has to be in draft state')
                )
            self.order_ids.with_context(ctx_skip).write({'route_id': self.route_id.id})
            self.order_ids.transfer_sales_packing(self.route_id.id)
            self.parent_route_id.remove_not_needed_packings()
        return {'type':'ir.actions.act_window_close'}