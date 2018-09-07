# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class StockRouteReturnPackingFromDriver(models.TransientModel):
    _name = 'stock.route.return_driver_packing.osv'
    _description = 'Return Drivers Packing'

    @api.model
    def _get_message(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            if route.return_picking_created:
                return _('Return picking is already done')
        return ''

    @api.model
    def _get_done(self):
        context = self.env.context or {}
        route_obj = self.env['stock.route']
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            if route.return_picking_created:
                return True
        return False

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_driver(self):
        location_id = False
        route_obj = self.env['stock.route']
        route_id = self._get_route()
        if route_id:
            route = route_obj.browse(route_id)
            if route.location_id:
                location_id = route.location_id.id
        return location_id

    @api.model
    def _get_lines(self):
        context = self.env.context or {}
        ctx = context.copy()
        route_obj = self.env['stock.route']
        line_obj = self.env['stock.route.return_driver_packing.line.osv']
        line_ids = []
        if context.get('active_ids', False):
            route = route_obj.browse(self._get_route())
            ctx['route_id'] = route.id
            for product in route.location_id.get_products():
                line_vals = {
                    'product_id': product[0],
                    'done': False
                }
                temp_line = line_obj.new(line_vals)
                temp_line.with_context(ctx).on_change_product_id()
                line_vals.update(temp_line._convert_to_write(temp_line._cache))
                line_ids.append(line_obj.create(line_vals).id)
            if not line_ids:
                raise UserError(_('Driver %s does not have any tare debts.') % route.location_id.name )
        if not line_ids:
            raise UserError(_('Driver does not have any tare debts.'))
        return line_ids

    parent_route_id = fields.Many2one('stock.route', 'Parent route', default=_get_route)
    line_ids = fields.One2many(
        'stock.route.return_driver_packing.line.osv', 'osv_id', 'Lines', default=_get_lines
    )
    line2_ids = fields.One2many(
        'stock.route.return_driver_packing.line_for_rec.osv', 'osv_id', 'Reconciliation Lines'
    )
    message = fields.Text('Message', readonly=True, default=_get_message)
    done = fields.Boolean('Picking Done', readonly=True, default=_get_done)
    location_id = fields.Many2one('stock.location', 'Driver', default=_get_driver)
    stage = fields.Integer('Stage', readonly=True, default=1)
    product_ids = fields.Many2many('product.product', 'product_return_osv_rel', 'osv_id', 'product_id', 'Products')

    @api.multi
    def return_packing_next(self):
        move_obj = self.env['stock.move']
        prod_obj = self.env['product.product']
        osv_line_2_obj = self.env['stock.route.return_driver_packing.line_for_rec.osv']

        product_ids = []
        used_moves_ids = []
        product_reconciled_ids = []
        lines = {}

        wrong_lines = self.line_ids.filtered(lambda line_rec: line_rec.to_warehouse_qty > line_rec.driver_qty)
        if wrong_lines:
            wrong_line = wrong_lines[0]
            raise UserError(_('You are trying to return %s units of \'%s\' from driver %s. %s has only %s of this tare.') % (
                str(wrong_line.to_warehouse_qty), wrong_line.product_id.get_name_for_error(), self.location_id.name,
                self.location_id.name, str(wrong_line.driver_qty)
            ))

        wrong_qty_lines = self.line_ids.filtered(lambda line_rec: line_rec.to_warehouse_qty < 0.0)
        if wrong_qty_lines:
            wrong_qty_line = wrong_qty_lines[0]
            raise UserError(_('You are trying to return %s units of \'%s\' from driver %s. Negative quantities are not allowed. ') % (
                str(wrong_qty_line.to_warehouse_qty), wrong_qty_line.product_id.get_name_for_error(), self.location_id.name,
            ))

        if self.parent_route_id:
            route_move_ids = self.parent_route_id.move_ids.mapped('id')

            if self.parent_route_id.in_picking_id:
                route_move_ids += [move.id for move in self.parent_route_id.in_picking_id.move_lines if
                                   move.id not in route_move_ids]

            for transfer_picking in self.parent_route_id.transfer_to_route_id:
                for move in transfer_picking.move_lines:
                    if move.id not in route_move_ids:
                        route_move_ids.append(move.id)
            for line in self.line_ids:
                if line.to_warehouse_qty == 0:
                    continue
                lines[line.product_id.id] = line.to_warehouse_qty
            for product_id in lines.keys():
                for route_move_id in route_move_ids:
                    route_move = move_obj.browse(route_move_id)

                    if lines[product_id] == 0:
                        continue
                    if route_move.product_id.id == product_id \
                            and route_move.get_reconciled_to_qty() < route_move.product_uom_qty \
                            :
                        qty = min([lines[product_id], route_move.product_uom_qty - route_move.get_reconciled_to_qty()])
                        vals = {
                            'to_warehouse_qty': qty,
                            'product_id': product_id,
                            'product_code': route_move.product_id.default_code,
                            'osv_id': self.id,
                            'move_id': route_move.id,
                            'invisible': True,
                        }
                        used_moves_ids.append(route_move.id)
                        lines[product_id] += -qty
                        osv_line_2_obj.create(vals)
                        product_reconciled_ids.append(product_id)
                if product_id not in product_ids:
                    product_ids.append(product_id)
        for p_id in product_ids:
            if p_id not in product_reconciled_ids or lines.get(p_id, 0) > 0:
                moves = move_obj.search([
                    ('product_id', '=', p_id),
                    ('location_dest_id', '=', self.parent_route_id.location_id.id),
                    ('open', '=', True),
                    ('id', 'not in', used_moves_ids),
                    ('date','<=',self.parent_route_id.departure_time)
                ], order='date desc')
                moves += move_obj.search([
                    ('product_id', '=', p_id),
                    ('location_dest_id', '=', self.parent_route_id.location_id.id),
                    ('open', '=', True),
                    ('id', 'not in', used_moves_ids),
                    ('date','>',self.parent_route_id.departure_time)
                ], order='date')
                for not_route_move in moves:
                    qty = min([lines[p_id], not_route_move.product_uom_qty - not_route_move.get_reconciled_to_qty()])
                    if qty > 0:
                        vals = {
                            'to_warehouse_qty': qty,
                            'product_id': p_id,
                            'product_code': prod_obj.browse(p_id).default_code,
                            'osv_id': self.id,
                            'invisible': False,
                            'move_id': not_route_move.id,
                        }
                        osv_line_2_obj.create(vals)
                        lines[p_id] -= qty
        self.write({
            'stage': 2,
            'product_ids': [(6, 0, product_ids)]
        })
        self.line_ids.write({'done': True})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.return_driver_packing.osv',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': self.id,
        }

    @api.multi
    def return_packing(self):
        route_obj = self.env['stock.route']
        pick_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        rec_obj = self.env['stock.move.reconcile']

        if self.parent_route_id:
            route = self.parent_route_id
            if route.state != 'released':
                raise UserError(_('Route has to be released'))
            for packing in route.packing_for_client_ids:
                if packing.state == 'draft':
                    raise UserError(_('All client packings has to be done'))
            if not self.line_ids:
                raise UserError(_('You have to fill in at least one line'))
            if route.returned_picking_id and route.returned_picking_id.state == 'done':
                raise UserError(_('Return picking is already done'))

            for line2 in self.line2_ids:
                if line2.to_warehouse_qty > line2.move_id.product_uom_qty - line2.move_id.get_reconciled_to_qty():
                    raise UserError(
                        _(
                            'You can\'t reconcile %s units of product %s to move %s. Because moves unreconciled quantity is %s') % (
                            str(line2.to_warehouse_qty), line2.product_id.name, line2.move_id.make_name(),
                            str(line2.move_id.product_uom_qty - line2.move_id.get_reconciled_to_qty())
                        )
                    )
            for line in self.line_ids:
                to_warehouse_qty = line.to_warehouse_qty
                for line2 in self.line2_ids:
                    if line.product_id.id == line2.product_id.id:
                        to_warehouse_qty = to_warehouse_qty - line2.to_warehouse_qty
                if to_warehouse_qty != 0:
                    raise UserError(
                        _(
                            'Selected return quantity for product %s was %s, but later you selected %s. Quantity has to be the same') % (
                            line.product_id.name, str(line.to_warehouse_qty),
                            str(line.to_warehouse_qty - to_warehouse_qty)
                        )
                    )
            location_id = route.location_id.id
            location_to = route.get_return_location(route.type)
            pick_type_id = False
            if route.type in ['out', 'mixed']:
                pick_type_id = route.warehouse_id.int_type_id.id
            elif route.type == 'internal':
                pick_type_id = route.destination_warehouse_id.int_type_id.id

            # if route.returned_picking_id:
            #     picking_id = route.returned_picking_id.id
            # else:
            #     pick_vals = {}
            #     pick_vals.update(pick_obj.default_get(pick_obj._fields))
            #     pick_vals['name'] = route.get_return_picking_name()
            #     pick_vals['picking_type_id'] = pick_type_id
            #     pick_vals['location_id'] = location_id
            #     pick_vals['location_dest_id'] = location_to
            #     picking = pick_obj.create(pick_vals)
            #     route.write({'returned_picking_id': picking.id})
            #     picking_id = picking.id
            for line in self.line2_ids:
                if line.to_warehouse_qty == 0:
                    continue

                #pakeitimas dėl to kad viename važtaraštye nebūtų skirtingų sąvininkų
                owner = line.product_id.owner_id
                owner_picking = route.returned_picking_ids.filtered(lambda picking_rec: picking_rec.owner_id == owner and picking_rec.state == 'draft')
                if not owner_picking:
                    pick_vals = {}
                    pick_vals.update(pick_obj.default_get(pick_obj._fields))
                    pick_vals['name'] = route.get_return_picking_name(owner=owner)
                    pick_vals['picking_type_id'] = pick_type_id
                    pick_vals['location_id'] = location_id
                    pick_vals['location_dest_id'] = location_to
                    pick_vals['return_from_driver_picking_for_route_id'] = route.id
                    pick_vals['related_route_id'] = route.id
                    pick_vals['owner_id'] = owner.id

                    picking = pick_obj.create(pick_vals)
                    picking_id = picking.id
                else:
                    picking_id = owner_picking.id
                move_vals = {}
                move_vals['product_id'] = line.product_id.id
                move_vals['location_id'] = location_id
                move_vals['location_dest_id'] = location_to
                move_vals['return_for_route_id'] = route.id
                move_vals['related_route_id'] = route.id

                temp_move = move_obj.new(move_vals)
                temp_move.onchange_product_id()
                move_vals.update(temp_move._convert_to_write(temp_move._cache))

                # move_vals['product_qty'] = line.to_warehouse_qty
                move_vals['product_uom_qty'] = line.to_warehouse_qty
                move_vals['product_uos_qty'] = line.to_warehouse_qty
                move_vals['picking_id'] = picking_id
                move_vals['tare_movement'] = True
                move_to = move_obj.create(move_vals)
                rec_obj.reconcile(line.move_id.id, move_to.id, qty=line.to_warehouse_qty)
            for return_picking in route.returned_picking_ids:
                route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(return_picking.id)
                return_picking.send_tare_qty_info()
            route.write({'return_picking_created': True})
            route.update_act_status()
            route.update_return_tare_number()
        return {'type': 'ir.actions.act_window_close'}


class StockRouteReturnPackingFromDriverLineForRec(models.TransientModel):
    _name = 'stock.route.return_driver_packing.line_for_rec.osv'
    _description = 'Return Drivers Packing Reconciliation Line'

    product_id = fields.Many2one(
        'product.product', 'Product'
    )
    to_warehouse_qty = fields.Integer('Return Quantity')
    fixed = fields.Boolean('Fixed', readonly=True)
    product_code = fields.Char('Product Code', size=128, readonly=True)
    move_id = fields.Many2one('stock.move', 'Move')
    invisible = fields.Boolean('Invisible')
    qty_to_reconciliate = fields.Integer('Not Reconciled Quantity', readonly=True)
    osv_id = fields.Many2one('stock.route.return_driver_packing.osv', 'Osv')

    _sql_constraints = [
        ('move_uniq', 'unique(osv_id, move_id)',
         'Move has to be unique per return! Check if you haven\'t selected same moves to reconcile from in several different lines.'),
    ]

    _order = 'product_code'

    @api.onchange('product_id')
    def on_change_product_id(self):
        if self.product_id:
            self.product_code = self.product_id.default_code or ''

    @api.onchange('move_id')
    def on_change_move_id(self):
        if self.move_id:
            self.to_warehouse_qty = self.move_id.product_uom_qty - self.move_id.get_reconciled_to_qty()

    @api.onchange('to_warehouse_qty')
    def on_change_quantity(self):
        if self.to_warehouse_qty > self.move_id.left_qty:
            self.to_warehouse_qty = self.move_id.left_qty


class StockRouteReturnPackingFromDriverLine(models.TransientModel):
    _name = 'stock.route.return_driver_packing.line.osv'
    _description = 'Return Drivers Packing Line'

    product_id = fields.Many2one(
        'product.product', 'Product', readonly=True
    )
    to_warehouse_qty = fields.Integer('Return Quantity')
    driver_qty = fields.Integer('Left Quantity for Driver', readonly=True)
    osv_id = fields.Many2one('stock.route.return_driver_packing.osv', 'Osv')
    final_qty = fields.Integer('Final Drivers Debt', readonly=True)
    product_code = fields.Char('Product Code', size=128, readonly=True)
    done = fields.Boolean('Done')
        
    _order = 'product_code'
        
    @api.model
    def create(self, vals):
        if 'to_warehouse_qty' in vals.keys() and 'driver_qty' in vals.keys():
            temp_line = self.new(vals)
            temp_line.on_change_quantity()
            vals.update(temp_line._convert_to_write(temp_line._cache))
        return super(StockRouteReturnPackingFromDriverLine, self).create(vals)

    @api.onchange('to_warehouse_qty')
    def on_change_quantity(self):
        self.final_qty = 0
        if self.to_warehouse_qty:
            self.final_qty = -1.0 * self.to_warehouse_qty
        if self.driver_qty:
            self.final_qty += self.driver_qty
        # if self.final_qty < 0:
        #     self.to_warehouse_qty = self.driver_qty
        #     self.final_qty = 0

    @api.onchange('product_id')
    def on_change_product_id(self):
        route_obj = self.env['stock.route']
        context = self.env.context or {}

        route_id = self.osv_id and self.osv_id.parent_route_id \
                   and self.osv_id.parent_route_id.id or context.get('route_id', False) or False

        if self.product_id and route_id:
            route = route_obj.browse(route_id)
            loc_qty = 0
            if route.location_id:
                loc_qty = self.product_id.get_product_quantity_with_sql(route.location_id.id)
            self.driver_qty = loc_qty
            self.product_code = self.product_id.default_code or ''
            self.on_change_quantity()