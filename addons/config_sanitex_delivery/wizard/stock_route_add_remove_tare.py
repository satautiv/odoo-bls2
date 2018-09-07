# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class StockRouteAddRemoveTare(models.TransientModel):
    _name = 'stock.route.add_remove.tare.osv'
    _description = 'Add tare to route or remove tare from route'

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
        line_obj = self.env['stock.route.add_remove.tare.line.osv']
        line_ids = []
        if context.get('active_ids', False):
            route = route_obj.browse(context['active_ids'][0])
            warehouse = route.warehouse_id

            ctx = context.copy()
            ctx['route_id'] = context['active_ids'][0]
            for product in sorted(warehouse.product_ids, key=lambda prod: prod.default_code):  # warehouse.product_ids:
                qty_in_route = sum(
                    route.move_ids.filtered(lambda move_record: move_record.product_id == product).mapped(
                        'product_uom_qty'))
                minus_qty_in_route = sum(
                    route.return_move_ids.filtered(lambda move_record: move_record.product_id == product).mapped(
                        'product_uom_qty'))
                already_qty = qty_in_route - minus_qty_in_route
                if already_qty < 0:
                    already_qty = 0
                line_vals = {
                    'product_id': product.id,
                    'product_code': product.default_code,
                    'already_in_route_qty': already_qty,
                    'qty': already_qty
                }
                line_ids.append(line_obj.create(line_vals).id)
        return line_ids

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_get_wh)
    parent_route_id = fields.Many2one('stock.route', 'Parent route', default=_get_route)
    line_ids = fields.One2many('stock.route.add_remove.tare.line.osv', 'osv_id', 'Lines', default=_get_lines)
    drivers_ids = fields.Many2many('stock.location', 'driv_osv_sel_dr_rels', 'osv_id', 'd_id', 'Drivers')
    transfer_picking_ids = fields.Many2many('stock.picking', 'tare_add_wiz_picking_rel', 'picking_id', 'osv_id', 'Transfers', readonly=True)
    return_picking_ids = fields.Many2many('stock.picking', 'tare_remove_wiz_picking_rel', 'picking_id', 'osv_id', 'Returns', readonly=True)

    @api.multi
    def select(self):
        route_env = self.env['stock.route']
        negative_lines = self.line_ids.filtered(lambda rec_line: rec_line.qty < 0)
        if negative_lines:
            raise UserError(
                _('Tare quantity can\'t be negative. Bad lines with tare - %s') % negative_lines.mapped('product_code')
            )
        if not self.line_ids:
            UserError(_('You need at least one line to be filled in'))

        positive_lines = self.env['stock.route.add_remove.tare.line.osv'].search([
            ('osv_id','=',self.id),
            ('difference_qty','>',0)
        ])
        positive_lines.create_picking('to_driver')

        negative_lines = self.env['stock.route.add_remove.tare.line.osv'].search([
            ('osv_id','=',self.id),
            ('difference_qty','<',0)
        ])
        negative_lines.create_picking('from_driver')

        for picking in self.transfer_picking_ids | self.return_picking_ids:
            route_env.with_context(create_invoice_document_for_picking=True).confirm_picking(picking.id)
            picking.send_tare_qty_info()
        # self.parent_route_id.update_packings() # Kaip dėl nesusigeneravusių ruošinių
        self.parent_route_id.update_tare_number()
        self.parent_route_id.update_return_tare_number()
        self.parent_route_id.update_act_status()
        self.parent_route_id.update_weight() # kaip dėl atspausdinto svorio
        return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def create_picking(self, picking_type, owner):
        pick_env = self.env['stock.picking']
        type_env = self.env['stock.picking.type']
        picking_vals = {
            'related_route_id': self.parent_route_id.id,
            'owner_id': owner.id
        }
        if picking_type == 'to_driver':
            if self.env.user.company_id.do_use_new_numbering_method():
                picking_name = pick_env.get_picking_name(
                    'route_transfer_to_driver', self.parent_route_id.warehouse_id, owner
                )
            else:
                picking_name = pick_env.get_pick_name(self.parent_route_id.warehouse_id.id, picking_type='driver')
            picking_vals.update({
                'location_id': self.parent_route_id.get_source_location(),
                'location_dest_id': self.parent_route_id.get_driver(),
                'transfer_to_driver_picking_for_route_id': self.parent_route_id.id,
                'name': picking_name
            })
            if self.parent_route_id.warehouse_id.int_type_id:
                picking_vals['picking_type_id'] = self.parent_route_id.warehouse_id.int_type_id.id
            else:
                stype = type_env.search([
                    ('code', '=', 'internal')
                ], limit=1)
                picking_vals['picking_type_id'] = stype.id
        else:
            picking_vals.update({
                'location_id': self.parent_route_id.get_driver(),
                'location_dest_id': self.parent_route_id.get_return_location(self.parent_route_id.type),
                'return_from_driver_picking_for_route_id': self.parent_route_id.id,
                'name': self.parent_route_id.get_return_picking_name()
            })

            if self.parent_route_id.type in ['out', 'mixed']:
                picking_vals['picking_type_id'] = self.parent_route_id.warehouse_id.int_type_id.id
            elif self.parent_route_id.type == 'internal':
                picking_vals['picking_type_id'] = self.parent_route_id.destination_warehouse_id.int_type_id.id

        picking = pick_env.create(picking_vals)
        if picking_type == 'to_driver':
            self.write({'transfer_picking_ids': [(4, picking.id)]})
        else:
            self.write({'return_picking_ids': [(4, picking.id)]})
        return picking

    @api.multi
    def get_picking(self, picking_type, owner):
        if picking_type == 'to_driver':
            picking = self.transfer_picking_ids.filtered(lambda pick_rec: pick_rec.owner_id == owner)
        else:
            picking = self.return_picking_ids.filtered(lambda pick_rec: pick_rec.owner_id == owner)
        if not picking:
            picking = self.create_picking(picking_type, owner)
        return picking

class StockRouteAddRemoveTareLine(models.TransientModel):
    _name = 'stock.route.add_remove.tare.line.osv'
    _description = 'Add tare to route or remove tare from route(Line)'

    osv_id = fields.Many2one('stock.route.add_remove.tare.osv', 'Osv')
    product_id = fields.Many2one(
        'product.product', 'Product', readonly=True
    )
    rem_qty_by_driver = fields.Integer(
        'Primary Debt by Driver', readonly=True
    )
    product_code = fields.Char('Product Code', size=128, readonly=True)
    already_in_route_qty = fields.Integer('Already In Route Quantity', readonly=True)
    qty = fields.Integer('New Quantity')
    difference_qty = fields.Integer('Difference', readonly=True)
    final_qty = fields.Integer('Final Drivers Debt', readonly=True)

    _order = 'product_code'

    @api.onchange('qty')
    def on_change_quantity(self):
        # if self.qty < 0:
        #     warning = {
        #         'title': _('Value Error !'),
        #         'message': _("Quantity can't be negative")
        #     }
        #     self.qty = self.already_in_route_qty
        #     return {'warning': warning}
        # else:
        self.difference_qty = self.qty - self.already_in_route_qty

    @api.multi
    def create_picking(self, picking_type):
        move_env = self.env['stock.move']

        for line in self:
            picking = line.osv_id.get_picking(picking_type, line.product_id.owner_id)
            move_vals = {'product_id': line.product_id.id}

            temp_move = move_env.new(move_vals)
            temp_move.onchange_product_id()
            move_vals.update(temp_move._convert_to_write(temp_move._cache))

            move_vals['picking_id'] = picking.id
            if picking_type == 'to_driver':
                move_vals['route_id'] = line.osv_id.parent_route_id.id
            else:
                move_vals['return_for_route_id'] = line.osv_id.parent_route_id.id
            # move_vals['product_qty'] = line.qty
            move_vals['product_uom_qty'] = abs(line.difference_qty)
            move_vals['product_uos_qty'] = abs(line.difference_qty)
            move_vals['location_id'] = picking.location_id.id
            move_vals['location_dest_id'] = picking.location_dest_id.id
            move_vals['related_route_id'] = line.osv_id.parent_route_id.id
            move_vals['tare_movement'] = True
            move_env.create(move_vals)
