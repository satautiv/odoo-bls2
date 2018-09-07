# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError

class StockRouteSelectOrders(models.TransientModel):
    _name = 'stock.route.select_orders.osv'
    _description = 'Select Orders for Route' 

    @api.model
    def _get_type(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            return route_obj.browse(context['active_ids'][0]).type
        return ''

    @api.model
    def _get_wh(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            return route_obj.browse(context['active_ids'][0]).warehouse_id.id
        return False

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]


    order_ids = fields.Many2many(
        'sale.order', 'sale_order_route_select_osv_rel',
        'sale_id', 'osv_id', 'Orders'
    )
    type =  fields.Selection([
        ('internal', 'Internal'),
        ('out', 'Out'),
        ('mixed', 'Mixed')
    ], 'Type', default=_get_type)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_get_wh)
    parent_route_id = fields.Many2one('stock.route', 'Route', readonly=True, default=_get_route)


    @api.multi
    def select(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            if route.state != 'draft':
                raise UserError(
                    _('Route has to be in \'draft\' state')
                )
                
            if not self.order_ids:
                raise UserError(
                    _('You have to select at least one order')
                )
            self.order_ids.write({'route_id': route.id})
            self.order_ids.change_route(route)
        return {'type':'ir.actions.act_window_close'}