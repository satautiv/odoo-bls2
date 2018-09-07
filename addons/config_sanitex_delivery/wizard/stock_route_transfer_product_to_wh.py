# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, _, models
from odoo.exceptions import UserError

import time

class StockRouteTransferProductToWh(models.TransientModel):
    _name = 'stock.route.transfer_product_to_wh.osv'
    _description = 'Transfer Orders to another Route' 

    @api.model
    def _get_orders(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            return route.sale_ids.mapped('id')
        return context.get('order_ids', [])

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_lines(self):
        context = self.env.context or {}
        ctx = context.copy()

        route_obj = self.env['stock.route']
        line_obj = self.env['stock.route.transfer_product_to_wh.line.osv']
        line_ids = []
        if context.get('active_ids', False):
            route = route_obj.browse(self._get_route())
            ctx['route_id'] = route.id
            for product in route.location_id.get_products():
                line_vals = {
                    'product_id': product[0]
                }

                temp_line = line_obj.new(line_vals)
                temp_line.with_context(ctx).on_change_product_id()
                line_vals.update(temp_line._convert_to_write(temp_line._cache))

                line_ids.append(line_obj.create(line_vals).id)
        return line_ids
    

    route_id = fields.Many2one(
        'stock.route', 'Route to Transfer to'
    )
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    line_ids = fields.One2many(
        'stock.route.transfer_product_to_wh.line.osv', 'osv_id', 'Transfer Lines', default=_get_lines
    )
    parent_route_id = fields.Many2one(
        'stock.route', 'Route to Transfer from', default=_get_route
    )
    today = fields.Date('Today', default=lambda self: time.strftime('%Y-%m-%d'))

    @api.onchange('route_id')
    def on_change_route(self):
        if self.route_id:
            self.warehouse_id = False

    @api.onchange('warehouse_id')
    def on_change_wh(self):
        if self.warehouse_id:
            self.route_id = False

    @api.multi
    def transfer(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        pick_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        
        if context.get('active_ids', False):
            route = self.parent_route_id
            
            if not self.line_ids:
                raise UserError(
                    _('You have to select at least one product to transfer')
                )
            if not route.location_id:
                raise UserError(
                    _('Source route doesn\'t have driver')
                )
                
            
            if self.route_id:
                if not self.route_id.location_id:
                    raise UserError(
                        _('Destination route doesn\'t have driver')
                    )
                location_to = self.route_id.location_id.id
                pick_type_id = self.route_id.location_id.get_picking_type('internal')
            else:
                if not self.warehouse_id.wh_return_stock_loc_id:
                    raise UserError(_('Warehouse %s doesn\'t have return location') % self.warehouse_id.name)
                location_to = self.warehouse_id.wh_return_stock_loc_id.id
                pick_type_id = self.warehouse_id.int_type_id.id
                
            picking_id = False
            for existing_picking in route.to_wh_or_route_picking_ids:
                for move in existing_picking.move_lines:
                    if move.location_dest_id.id == location_to:
                        picking_id = existing_picking.id
                        break
                    
            if picking_id:
                route_obj.cancel_picking(picking_id)
            else:
                pick_vals = {}
                pick_vals.update(pick_obj.default_get(pick_obj._fields))
                if self.env.user.company_id.do_use_new_numbering_method():
                    pick_vals['name'] = pick_obj.get_picking_name('route_return_from_driver', self.route_id.warehouse_id)
                else:
                    pick_vals['name'] = route_obj.get_pick_name(self.route_id.warehouse_id.id, 'driver')
                pick_vals['picking_type_id'] = pick_type_id
                pick_vals['transfer_route_id'] = route.id
                pick_vals['location_id'] = route.location_id.id
                pick_vals['location_dest_id'] = location_to
                if self.route_id:
                    pick_vals['transfer_to_route_id'] = self.route_id.id
                picking = pick_obj.create(pick_vals)
                route.write({
                    'to_wh_or_route_picking_id': picking.id
                })
                picking_id = picking.id
            for line in self.line_ids:
                if line.quantity == 0:
                    continue
                move_vals = {}
                move_vals['product_id'] = line.product_id.id
                move_vals['location_id'] = route.location_id.id
                move_vals['location_dest_id'] = location_to

                temp_move = move_obj.new(move_vals)
                temp_move.onchange_product_id()
                move_vals.update(temp_move._convert_to_write(temp_move._cache))

                # move_vals['product_qty'] = line.quantity
                move_vals['product_uom_qty'] = line.quantity
                move_vals['product_uos_qty'] = line.quantity
                move_vals['picking_id'] = picking.id
                move_vals['tare_movement'] = True
                if self.route_id:
                    move_vals['route_id'] = self.route_id.id
                move = move_obj.create(move_vals)
                
                move_from_ids = [m.id for m in self.parent_route_id.move_ids if m.product_id.id == line.product_id.id]
                move_from_ids += [m.id for m in self.parent_route_id.in_picking_id.move_lines if m.product_id.id == line.product_id.id and m.id not in move_from_ids]
                move_from_ids += move_obj.search([
                    ('state','=','done'),
                    ('location_dest_id','=',route.location_id.id),
                    ('product_id','=',line.product_id.id),
                    ('id','not in',move_from_ids)
                ]).mapped('id')
                move_obj.reconciliate_moves(move.id, move_from_ids=move_from_ids)
            route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(picking_id)
        return {'type':'ir.actions.act_window_close'}


class StockRouteTransferProductToWhLine(models.TransientModel):
    _name = 'stock.route.transfer_product_to_wh.line.osv'
    _description = 'Transfer Orders to another Route line'

    osv_id = fields.Many2one('stock.route.transfer_product_to_wh.osv', 'Osv')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    rem_qty_by_driver = fields.Integer(
        'Primary Driver\'s Debt', readonly=True
    )
    quantity = fields.Integer('Quantity')
    product_code = fields.Char('Product Code', size=128, readonly=True)
    final_qty = fields.Integer('Final Driver\'s Debt', readonly=True)

    _order = 'product_code'

    @api.onchange('quantity')
    def on_change_quantity(self):
        if self.rem_qty_by_driver:
            self.final_qty = self.rem_qty_by_driver
        if self.quantity:
            self.final_qty = -1.0 * self.quantity

    @api.onchange('product_id')
    def on_change_product_id(self):
        context = self.env.context or {}
        route_env = self.env['stock.route']
        route_id = self.osv_id and self.osv_id.route_id and self.osv_id.route_id.id or context.get('route_id', False) or False

        if self.product_id and route_id:
            route = route_env.browse(route_id)
            loc_qty = 0.0
            if route.location_id:
                loc_qty = self.product_id.get_product_quantity_with_sql(route.location_id.id)
            self.rem_qty_by_driver = loc_qty
            self.product_code = self.product_id.default_code or ''
            self.on_change_quantity()