# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError
 
class StockRouteSelectProduct(models.TransientModel):
    _name = 'stock.route.select_product.osv'
    _description = 'Select Product for Route' 

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

    @api.model
    def _get_lines(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        line_obj = self.env['stock.route.select_product.line.osv']
        line_ids = []
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            warehouse = route.warehouse_id

            ctx = context.copy()
            ctx['route_id'] = context['active_ids'][0]
            for product in sorted(warehouse.product_ids, key=lambda prod: prod.default_code): #warehouse.product_ids:
                qty_in_route = sum(route.move_ids.filtered(lambda move_record: move_record.product_id == product).mapped('product_uom_qty'))
                line_vals = {
                    'product_id': product.id,
                    'qty': qty_in_route
                }
                temp_line = line_obj.new(line_vals)
                temp_line.with_context(ctx).on_change_product_id()
                line_vals.update(temp_line._convert_to_write(temp_line._cache))
                line_ids.append(line_obj.create(line_vals).id)
        return line_ids

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_get_wh)
    parent_route_id = fields.Many2one('stock.route', 'Parent route', default=_get_route)
    line_ids = fields.One2many('stock.route.select_product.line.osv', 'osv_id', 'Lines', default=_get_lines)
    drivers_ids = fields.Many2many('stock.location', 'driv_osv_sel_dr_rels', 'osv_id', 'd_id', 'Drivers')

    @api.multi
    def select(self):
        context = self.env.context or {}
        
        pick_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        route_obj = self.env['stock.route']
        type_obj = self.env['stock.picking.type']

        if not self.line_ids:
            UserError(_('You need at least one line to be filled in'))

        if context.get('active_ids', False):
            pick_vals = {}
            route = route_obj.browse(context['active_ids'][0])
            if route.state != 'draft':
                raise UserError(_('Route has to be in \'draft\' state'))
            
            loc_id = route.get_source_location()
            loc_dest_id = route.get_driver()

            for line in self.line_ids:

                #pakeitimas dėl to kad nebūtų viename važtaraštyje kelių skirtingų ownerių.

                owner = line.product_id.owner_id
                owner_picking = route.picking_ids.filtered(lambda picking_rec: picking_rec.owner_id == owner)
                if not owner_picking:
                    if line.qty <= 0.0:
                        continue
                    pick_vals.update(pick_obj.default_get(pick_obj._fields))

                    if route.warehouse_id.int_type_id:
                        pick_vals['picking_type_id'] = route.warehouse_id.int_type_id.id
                    else:
                        stype = type_obj.search([
                            ('code','=','internal')
                        ], limit=1)
                        pick_vals['picking_type_id'] = stype.id

                    pick_vals['location_id'] = loc_id
                    pick_vals['location_dest_id'] = loc_dest_id
                    pick_vals['owner_id'] = owner.id
                    pick_vals['transfer_to_driver_picking_for_route_id'] = route.id
                    pick_vals['related_route_id'] = route.id

                    if self.env.user.company_id.do_use_new_numbering_method():
                        pick_vals['name'] = pick_obj.get_picking_name('route_transfer_to_driver', route.warehouse_id, owner)
                    else:
                        pick_vals['name'] = pick_obj.get_pick_name(route.warehouse_id.id, picking_type='driver')
                    picking = pick_obj.create(pick_vals)
                    # route.write({
                    #     'picking_number': pick_vals['name']
                    # })
                else:
                    picking = owner_picking


                move_vals = {}
                move = move_obj.search([
                    ('product_id','=',line.product_id.id),
                    ('picking_id','=',picking.id)
                ], limit=1)
                if not move:
                    if line.qty <= 0:
                        continue
                    move_vals.update(move_obj.default_get(move_obj._fields))
                    move_vals['product_id'] = line.product_id.id

                    temp_move = move_obj.new(move_vals)
                    temp_move.onchange_product_id()
                    move_vals.update(temp_move._convert_to_write(temp_move._cache))
    
                    move_vals['picking_id'] = picking.id
                    move_vals['route_id'] = route.id
                    # move_vals['product_qty'] = line.qty
                    move_vals['product_uom_qty'] = line.qty
                    move_vals['product_uos_qty'] = line.qty
                    move_vals['location_id'] = loc_id
                    move_vals['location_dest_id'] = loc_dest_id
                    move_vals['related_route_id'] = route.id
                    move_vals['tare_movement'] = True
                    move_obj.create(move_vals)
                else:
                    # move_vals['product_qty'] = line.qty + move.product_qty
                    if line.qty < 0:
                        continue
                    elif line.qty == 0.0:
                        move.unlink()
                    else:
                        move_vals['product_uom_qty'] = line.qty# + move.product_uom_qty
                        move_vals['product_uos_qty'] = line.qty# + move.product_uos_qty
                        move.write(move_vals)

            route.write({'products_picked': True})
            route.update_packings()
            route.update_tare_number()
            route.update_act_status()
            route.update_weight()
        return {'type':'ir.actions.act_window_close'}


class StockRouteSelectProdutLine(models.TransientModel):
    _name = 'stock.route.select_product.line.osv'
    _description = 'Select Product for Route(Line)'

    osv_id = fields.Many2one('stock.route.select_product.osv', 'Osv')
    product_id = fields.Many2one(
        'product.product', 'Product', readonly=True
    )
    rem_qty_by_driver = fields.Integer(
        'Primary Debt by Driver', readonly=True
    )
    product_code = fields.Char('Product Code', size=128, readonly=True)
    qty = fields.Integer('Quantity')
    final_qty = fields.Integer('Final Drivers Debt', readonly=True)
    # already_in_route_qty = fields.Integer('Route Quantity', readonly=True, default=0)

    _order = 'product_code'

    @api.onchange('qty')
    def on_change_quantity(self):
        final_qty = 0
        if self.rem_qty_by_driver:
            final_qty += self.rem_qty_by_driver
        if self.qty:
            final_qty += self.qty
        self.final_qty = final_qty

    @api.onchange('product_id')
    def on_change_product_id(self):
        context = self.env.context or {}
        route = self.osv_id and self.osv_id.route_id or \
            context.get('route_id', False) and self.env['stock.route'].browse(context['route_id']) or False
        if self.product_id and route:
            prod = self.product_id
            loc_qty = 0.0
            if route.location_id:
                loc_qty = route.location_id.get_drivers_debt(prod.id)
            self.rem_qty_by_driver = loc_qty
            self.product_code = prod.default_code or ''
            self.on_change_quantity()


        #     self.final_qty = self.on_change_quantity(
        #         cr, uid, ids, res['value']['rem_qty_by_driver'], qty, context=context
        #     ).get('value', {}).get('final_qty', 0.0)
        #
        # return res