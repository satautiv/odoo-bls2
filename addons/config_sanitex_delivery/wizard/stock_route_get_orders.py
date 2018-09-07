# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError

class StockRouteGetOrders(models.TransientModel):
    _name = 'stock.route.get_orders.osv'
    _description = 'Transfer Orders to another Route' 

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]
    
    order_ids = fields.Many2many(
        'sale.order', 'sale_order_route_get_osv_rel',
        'sale_id', 'osv_id', 'Orders to Transfer'
    )
    route_id = fields.Many2one(
        'stock.route', 'Route to Transfer from', required=True, ondelete='cascade'
    )
    domain_order_ids = fields.Many2many(
        'sale.order', 'sale_order_route_get_domain_osv_rel',
        'osv_id', 'sale_id', 'Orders to Transfer(Domain)'
    )
    parent_route_id = fields.Many2one(
        'stock.route', 'Route to Transfer for', default=_get_route
    )
    stage2 = fields.Boolean('Stage2', default=False)

    @api.multi
    def next(self):
        context = self.env.context or {}
        if context.get('active_ids', False):
            if not self.route_id.sale_ids:
                raise UserError(
                    _('Selected route doesn\'t have any orders')
                )
            self.write({
                'domain_order_ids': [(6, 0, self.route_id.sale_ids.mapped('id'))],
                'stage2': True
            })
            
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.get_orders.osv',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': self.id,
        }

    @api.multi
    def get(self):
        context = self.env.context or {}
        ctx = context.copy()
        ctx['skip_packing_remove'] = True
        if self.parent_route_id and self.route_id:

            if not self.order_ids:
                raise UserError(
                    _('You have to select at least one order')
                )
            if self.parent_route_id.state != 'draft':
                raise UserError(
                    _('Route has to be in \'draft\' state')
                )
            if self.route_id.state != 'draft':
                raise UserError(
                    _('Selected route has to be in \'draft\' state')
                )

            self.order_ids.with_context(ctx).write({'route_id': self.parent_route_id.id})
            self.order_ids.transfer_sales_packing(self.parent_route_id.id)
            self.route_id.remove_not_needed_packings()
        return {'type':'ir.actions.act_window_close'}