# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

from datetime import datetime, timedelta

class InternalOperationReason(models.Model):
    _name = 'internal.operation.reason'
    _description = 'Reason for Internal Operation'

    name = fields.Char('Name', size=256, required=True, translate=True)
    code = fields.Char('Code', size=256)

class InternalOperation(models.Model):
    _name = 'internal.operation'
    _description = 'Internal Operation'

    _order = 'date desc'

    @api.model
    def _get_warehouse(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        return user.get_default_warehouse()

    @api.model
    def _get_operation_types(self):
        context = self.env.context or {}
        if context.get('internal_operation_object', False):
            try:
                types = self.env[context['internal_operation_object']]._get_operation_types()
                return types
            except:
                raise
                pass
        return [
            ('to_warehouse', _('To Warehouse')),
            ('from_warehouse', _('From Warehouse'))
        ]

    @api.model
    def _get_operation_states(self):
        return [
            ('draft',_('Draft')),
            ('done',_('Done'))
        ]

    @api.model
    def _get_location(self, location_type):
        warehouse = self.env['stock.warehouse'].browse(self._get_warehouse())
        if location_type == 'from':
            return warehouse.wh_output_stock_loc_id and warehouse.wh_output_stock_loc_id.id or False
        elif location_type == 'to':
            return warehouse.wh_return_stock_loc_id and warehouse.wh_return_stock_loc_id.id or False
        return False

    @api.model
    def _get_from_location(self):
        return self._get_location('from')

    @api.model
    def _get_to_location(self):
        return self._get_location('to')

    name = fields.Char('Document No.', size=256)
    line_ids = fields.One2many('internal.operation.line', 'operation_id', 'Lines', auto_join=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', default=_get_warehouse, readonly=True)
    location_from_id = fields.Many2one('stock.location', 'Location From', default=_get_from_location)
    location_to_id = fields.Many2one('stock.location', 'Location To', default=_get_to_location)
    operation_type = fields.Selection(_get_operation_types, 'Operation Type', required=True)
    state = fields.Selection(_get_operation_states, 'State', readonly=True, default='draft')
    lines_filled_in = fields.Boolean('Lines Filled In', default=False)
    picking_to_warehouse_ids = fields.One2many(
        'stock.picking', 'picking_to_warehouse_for_internal_order_id', 'Transfers to Warehouse', readonly=True
    )
    picking_from_warehouse_ids = fields.One2many(
        'stock.picking', 'picking_from_warehouse_for_internal_order_id', 'Transfers from Warehouse', readonly=True
    )
    owner_codes = fields.Char('Own.', size=32, readonly=True)
    owner_ids = fields.Many2many('product.owner', 'internal_operation_owner_rel', 'operation_id', 'owner_id', 'Owners', readonly=True)
    status_name = fields.Char('Status', size=64, readonly=True)
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    user_confirm_id = fields.Many2one('res.users', 'Confirmed By', readonly=True,
        help='User who confirmed this document.'
    )


    @api.model
    def _get_all_operation_types(self):
        return [
            ('adjustment',_('Adjustment')),
            ('driver',_('Driver')),
            ('client',_('Client')),
            ('warehouse_movement',_('Movement in Warehouse')),
            ('atlas_movement',_('Movement in Atlas')),
            ('bls_movement',_('Movement in BLS'))
        ]

    @api.model
    def cron_unlink_old_draft_operations(self, hours=1):
        # Ištrinami juodraštinės vidinės operacijos kurios
        # yra senesnės nei 1 valanda. Tam kad nesimėtytų nereikalingi objektai.

        _logger.info('Removing draft corrections older than %s hours' % str(hours))
        time_domain = datetime.now() - timedelta(hours=hours)
        operations = self.search([
            ('state','=','draft'),
            ('create_date','<',time_domain.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        _logger.info('Found %s operations to delete' % str(len(operations)))
        operations.with_context(allow_to_unlink_operation=True).unlink()

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_unlink_operation', False):
            for operation in self:
                if operation.state == 'done':
                    raise UserError(_('You can\'t delete internal operation (%s)') % operation.name)
        return super(InternalOperation, self).unlink()

    @api.multi
    def check_operation(self, child_operation):
        if not self.line_ids.filtered(lambda line_rec: line_rec.quantity > 0):
            raise UserError(
                _('There should be at least one line with quantity greater than zero filled in(Opertaion: %s, ID: %s)') % (
                    self.name, str(self.id)
                )
            )
        negative_lines = self.line_ids.filtered(lambda line_rec: line_rec.quantity < 0)
        if negative_lines:
            raise UserError(_('Quantity of a line can\'t be lower than zero(Line: %s, ID: %s)') % (
                negative_lines[0].product_code, str(negative_lines[0].id)
            )
        )

    @api.multi
    def action_done(self, operation, send_tare_qty_info=True):
        context = self.env.context or {}
        route_env = self.env['stock.route']
        self.check_operation(operation)
        self.line_ids.fill_code_if_empty()
        self.line_ids.filtered(lambda line_record: line_record.quantity != 0.0).create_moves(operation)
        pickings = self.picking_to_warehouse_ids | self.picking_from_warehouse_ids
        for picking in pickings:
            route_env.with_context(
                create_invoice_document_for_picking=context.get('create_invoice_document_for_picking', True)
            ).confirm_picking(picking.id)
            if send_tare_qty_info:
                picking.send_tare_qty_info()

        vals = {
            'state': 'done',
            'name': ', '.join(pickings.mapped('name')),
            'user_confirm_id': self.env.uid,
        }
        all_owners = pickings.mapped('owner_id')
        vals['owner_codes'] = ', '.join(all_owners.mapped('owner_code'))
        if len(all_owners) > 1:
            vals['owner_ids'] = [(6, 0, list(all_owners._ids))]
        elif all_owners:
            vals['owner_id'] = all_owners.id
        if self.operation_type == 'to_warehouse':
            status = self.location_to_id or self.warehouse_id.wh_return_stock_loc_id
        else:
            status = self.location_from_id or self.warehouse_id.wh_output_stock_loc_id
        vals['status_name'] = status.name or ''

        self.write(vals)


    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate an internal operation.'))

    @api.multi
    def action_done_and_print(self):
        print_action = self.env.ref('config_sanitex_delivery.action_print_report_from_object_osv').read()[0]
        if print_action['context']:
            print_action['context'] = print_action['context'][:-1] + ', \'for_confirmation\':True}'
        return print_action

    @api.onchange('warehouse_id', 'operation_type')
    def on_change_warehouse(self):
        if self.warehouse_id:
            self.location_from_id = self.warehouse_id.wh_output_stock_loc_id and \
                                            self.return_to_warehouse_id.wh_output_stock_loc_id.id or False
            self.location_to_id = self.warehouse_id.wh_return_stock_loc_id and \
                                            self.return_to_warehouse_id.wh_return_stock_loc_id.id or False
        else:
            self.location_from_id = False
            self.location_to_id = False

    @api.model
    def get_debt(self, operation, product):
        return 0.0

    @api.multi
    def action_generate_lines(self, operation):
        line_env = self.env['internal.operation.line']
        products = operation.get_products()
        for product in products:
            line_vals = {
                'product_id': product[0],
                'product_code': product[2],
                'debt': product[1],
                'operation_id': self.id,
            }
            line_vals = operation.update_line_values(line_vals)
            line_env.create(line_vals)
        self.write({'lines_filled_in': True})

    @api.multi
    def name_get(self):
        res = []
        for operation in self:
            name = operation.name or _('New')
            res.append((operation.id, name))
        return res

    @api.multi
    def get_records_to_print(self, report):
        pickings = self.env['stock.picking']
        for operation in self:
            pickings |= operation.picking_to_warehouse_ids
            pickings |= operation.picking_from_warehouse_ids
        return pickings


    @api.model
    def get_search_domain(self, args):
        context = self._context or {}
        if context.get('search_operation_by_warehouse', False):
            user = self.env['res.users'].browse(self.env.uid)
            if not user.default_warehouse_id:
                raise UserError(_('To open Internal Operations you need to select warehouse'))
            available_wh_id = user.default_warehouse_id.id
            if ('warehouse_id','=',available_wh_id) not in args:
                args.append(('warehouse_id','=',available_wh_id))

class InternalOperationClient(models.Model):
    _name = 'internal.operation.client'
    _description = 'Internal Operation for Clients'
    _inherits = {'internal.operation': 'operation_id'}

    _order = 'date desc'

    operation_id = fields.Many2one('internal.operation', 'Internal Operation',
        auto_join=True, index=True, ondelete='cascade', required=True
    )
    partner_id = fields.Many2one('res.partner', 'Client', domain=[('is_company','=',True)])
    partner_address_id = fields.Many2one('res.partner', 'Posid', required=True)
    client_name = fields.Char('Client Name', size=128, readonly=True)
    posid = fields.Char('POSID', size=32, readonly=True)


    @api.multi
    def unlink(self):
        self.mapped('operation_id').unlink()
        return super(InternalOperationClient, self).unlink()

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.env['internal.operation'].get_search_domain(args)
        return super(InternalOperationClient, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def name_get(self):
        res = []
        for operation in self:
            name = operation.name or _('New')
            res.append((operation.id, name))
        return res

    @api.model
    def _get_operation_types(self):
        return [
            ('to_warehouse', _('Return tere from client')),
            ('from_warehouse', _('Transfer tare to client'))
        ]

    @api.multi
    def action_generate_lines(self):
        for operation in self:
            operation.operation_id.action_generate_lines(operation)

    @api.multi
    def update_line_values(self, line_vals):
        return line_vals

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate an internal operation.'))

    @api.onchange('partner_address_id')
    def on_change_posid_id(self):
        if self.partner_address_id:
            if not self.partner_id or (self.partner_id and self.partner_id != self.partner_address_id.parent_id):
                self.partner_id = self.partner_address_id.parent_id
            self.posid = self.partner_address_id.possid_code
            self.client_name = self.partner_id.name
        else:
            self.posid = ''
            self.client_name = ''

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        if not self.partner_id:
            self.partner_address_id = False
            self.on_change_posid_id()
        elif self.partner_address_id:
            if self.partner_address_id.parent_id != self.partner_id:
                self.partner_address_id = False
                self.on_change_posid_id()

    @api.model
    def get_debt(self, operation, product):
        debt = 0.0
        if operation:
            if operation._name != self._name:
                operation = self.search([('operation_id','=',operation.id)], limit=1)
            posid = operation.partner_address_id
        else:
            context = self.env.context or {}
            posid = self.env['res.partner'].browse(context.get('posid_id', []))
        if posid:
            debt = posid.get_debt(product.id)
        return debt

    @api.multi
    def get_products(self):
        products = []
        if self.operation_type == 'to_warehouse':
            products = self.partner_address_id.get_products_with_debt()
        elif self.operation_type == 'from_warehouse':
            products_read = self.warehouse_id.product_ids.read(['default_code'])
            products = [(product_read['id'], 0, product_read['default_code']) for product_read in products_read]
        return products

    @api.multi
    def action_done_and_print(self):
        res = self.operation_id.action_done_and_print()
        return res

    @api.multi
    def action_done(self):
        for operation in self:
            operation.operation_id.action_done(operation)

    @api.multi
    def update_location_vals(self, vals):
        if self.operation_type == 'to_warehouse':
            vals['location_id'] = self.env['stock.route'].get_client_location()
            vals['location_dest_id'] = self.location_to_id and self.location_to_id.id or self.warehouse_id.wh_return_stock_loc_id.id
        else:
            vals['location_id'] = self.location_from_id and self.location_from_id.id or self.warehouse_id.wh_output_stock_loc_id.id
            vals['location_dest_id'] = self.env['stock.route'].get_client_location()
        return vals

    @api.multi
    def update_picking_vals(self, vals):
        type_env = self.env['stock.picking.type']
        vals = self.update_location_vals(vals)
        if self.operation_type == 'to_warehouse':
            stock_type = 'incoming'
        else:
            stock_type = 'outgoing'

        type_record = type_env.search([
            ('code','=',stock_type),
            ('warehouse_id','=',self.warehouse_id.id)
        ], limit=1)
        vals['picking_type_id'] = type_record.id
        vals['operation_type'] = 'client'
        return vals

    @api.multi
    def update_move_vals(self, vals):
        vals = self.update_location_vals(vals)
        vals['address_id'] = self.partner_address_id.id
        vals['tare_movement'] = True
        return vals

    @api.multi
    def get_records_to_print(self, report):
        to_print = self.mapped('operation_id').get_records_to_print(report)
        return to_print

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(InternalOperationClient, self)._export_rows(fields)
        return res

    @api.multi
    def do_not_print_reports(self, reports=None):
        if reports is None:
            reports = [
                'config_sanitex_delivery.client_packing_from_picking', # Taros perdavimo-grąžinimo aktas klientui (vidinė op.)
            ]
        elif isinstance(reports, str):
            reports = [reports]

        report_env = self.env['ir.actions.report']

        for report_name in reports:
            for record in self.get_records_to_print(report_name): # in self.mapped('picking_to_driver_ids') + self.mapped('picking_to_warehouse_ids'):
                report_env.do_not_print_report(record, report_name)

    @api.model
    def get_document_type(self):
        return 'internal_transfer_to_client'

    @api.model
    def get_document_type2(self):
        return 'client_packing'


class InternalOperationLine(models.Model):
    _name = 'internal.operation.line'
    _description = 'Internal Operation Line'

    _order = 'product_code'

    operation_id = fields.Many2one('internal.operation', 'Internal Operation',
        index=True, ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_code = fields.Char('Tare Code', size=64, readonly=True)
    debt = fields.Float('Debt', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    quantity = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'),)

    @api.model
    def create(self, vals):
        if vals.get('product_id', False) and not vals.get('product_code', ''):
            product = self.env['product.product'].browse(vals['product_id'])
            if not product.default_code:
                raise UserError(_('Product %s does not have code') % product.name)
            vals['product_code'] = product.default_code
        return super(InternalOperationLine, self).create(vals)

    @api.model
    def write(self, vals):
        if vals.get('product_id', False) and not vals.get('product_code', ''):
            product = self.env['product.product'].browse(vals['product_id'])
            if not product.default_code:
                raise UserError(_('Product %s does not have code') % product.name)
            vals['product_code'] = product.default_code
        return super(InternalOperationLine, self).write(vals)

    @api.onchange('product_id')
    def on_change_product_id(self):
        if not self.product_id:
            self.debt = 0.0
            self.product_code = ''
        else:
            context = self.env.context or {}
            self.debt = self.env[context.get(
                'internal_operation_object', 'internal.operation'
            )].get_debt(self.operation_id, self.product_id)

            self.product_code = self.product_id.default_code

    @api.multi
    def create_picking(self, child_operation):
        pick_env = self.env['stock.picking']
        if self.env.user.company_id.do_use_new_numbering_method():
            pick_name = child_operation.name or pick_env.get_picking_name(
                child_operation.get_document_type(), self.operation_id.warehouse_id, self.product_id.owner_id
            )
        else:
            pick_name = child_operation.name or pick_env.get_pick_name(self.operation_id.warehouse_id.id, child_operation.get_document_type2())
        picking_vals = {
            'name': pick_name,
            'date': self.operation_id.date,
            'owner_id': self.product_id.owner_id.id,
            'picking_type_id': self.operation_id.warehouse_id.int_type_id.id
        }
        if self.operation_id.operation_type == 'to_warehouse':
            picking_vals['picking_to_warehouse_for_internal_order_id'] = self.operation_id.id
            if self.operation_id.name and self.operation_id.picking_to_warehouse_ids:
                picking_vals['name'] += str(len(self.operation_id.picking_to_warehouse_ids)+1)
        else:
            picking_vals['picking_from_warehouse_for_internal_order_id'] = self.operation_id.id
            if self.operation_id.name and self.operation_id.picking_from_warehouse_ids:
                picking_vals['name'] += str(len(self.operation_id.picking_from_warehouse_ids)+1)
        picking_vals = child_operation.update_picking_vals(picking_vals)
        return pick_env.create(picking_vals)

    @api.multi
    def get_picking(self, child_operation):
        owner = self.product_id.owner_id
        if self.operation_id.operation_type == 'to_warehouse':
            pickings = self.operation_id.picking_to_warehouse_ids
        else:
            pickings = self.operation_id.picking_from_warehouse_ids
        picking = pickings.filtered(lambda pick_rec: pick_rec.owner_id.id == owner.id)
        if not picking:
            picking = self.create_picking(child_operation)
        return picking

    @api.multi
    def create_moves(self, child_operation):
        move_env = self.env['stock.move']
        for line in self:
            picking = line.get_picking(child_operation)
            move_vals = {
                'product_id': line.product_id.id,
                'picking_id': picking.id,
            }
            temp_move = move_env.new(move_vals)
            temp_move.onchange_product_id()
            move_vals.update(temp_move._convert_to_write(temp_move._cache))
            move_vals.update({
                'product_code': line.product_id.default_code or '',
                'product_uom_qty': abs(line.quantity),
                'product_uos_qty': abs(line.quantity),
                'date': line.operation_id.date,
            })
            move_vals = child_operation.update_move_vals(move_vals)
            move_env.create(move_vals)

    @api.multi
    def fill_code_if_empty(self):
        for line in self:
            if not line.product_code and line.product_id:
                line.write({'product_code': line.product_id.default_code})

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate an internal operation.'))


class InternalOperationAdjustment(models.Model):
    _name = 'internal.operation.adjustment'
    _description = 'Internal Operation for Stock Adjustment'
    _inherits = {'internal.operation': 'operation_id'}


    operation_id = fields.Many2one('internal.operation', 'Internal Operation',
        auto_join=True, index=True, ondelete='cascade', required=True
    )
    reason_id = fields.Many2one('internal.operation.reason', 'Reason for Operation')

    @api.model
    def _get_operation_types(self):
        return [
            ('to_warehouse', _('Addition')),
            ('from_warehouse', _('Write Off'))
        ]

    @api.model
    def get_debt(self, operation, product):
        context = self.env.context or {}
        debt = 0.0
        location = False
        location_name = ''
        operation_type = operation and operation.operation_type or context.get('operation', '')
        if operation_type == 'to_warehouse':
            location = operation.location_to_id
            location_name = 'location_to_id'
        elif operation_type == 'from_warehouse':
            location = operation.location_from_id
            location_name = 'location_from_id'


        if operation and location:
            debt = self.env['sanitex.product.location.stock'].get_quantity(
                product_id=product.id, location_id=location.id
            )
        else:
            if location_name and context.get(location_name, False):
                debt = self.env['sanitex.product.location.stock'].get_quantity(
                    product_id=product.id, location_id=context[location_name]
                )
        return debt

    @api.onchange('location_from_id')
    def on_change_location_from(self):
        for line in self.line_ids:
            if line.product_id:
                line.debt = self.get_debt(self, line.product_id)

    @api.multi
    def action_done(self):
        for operation in self:
            operation.operation_id.action_done(operation, send_tare_qty_info=False)


    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.env['internal.operation'].get_search_domain(args)
        return super(InternalOperationAdjustment, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def get_document_type(self):
        return 'product_adjustment'

    @api.model
    def get_document_type2(self):
        return 'product_adjustment'

    @api.multi
    def update_location_vals(self, vals):
        if self.operation_type == 'to_warehouse':
            vals['location_id'] = self.env['stock.picking'].get_positive_adjustment_location().id
            vals['location_dest_id'] = self.location_to_id and self.location_to_id.id or self.warehouse_id.wh_return_stock_loc_id.id
        else:
            vals['location_id'] = self.location_from_id and self.location_from_id.id or self.warehouse_id.wh_output_stock_loc_id.id
            vals['location_dest_id'] = self.env['stock.picking'].get_negative_adjustment_location().id
        return vals

    @api.multi
    def update_move_vals(self, vals):
        vals = self.update_location_vals(vals)
        return vals

    @api.multi
    def update_picking_vals(self, vals):
        self.update_location_vals(vals)
        vals['operation_type'] = 'adjustment'
        return vals


class InternalOperationMovement(models.Model):
    _name = 'internal.operation.movement'
    _description = 'Internal Operation for Stock Movement'
    _inherits = {'internal.operation': 'operation_id'}

    _rec_name = 'operation_id'

    operation_id = fields.Many2one('internal.operation', 'Internal Operation',
        auto_join=True, index=True, ondelete='cascade', required=True
    )
    warehouse_to_id = fields.Many2one('stock.warehouse', 'Destination Warehouse')
    dos_location_posid_id = fields.Many2one('res.partner', 'DOS Posid', domain=[('dos_location','=',True)])
    movement_type = fields.Selection([
        ('atlas_warehouse', 'Atlas Warehouse Transfer'),
        ('dos_warehouse', 'DOS Warehouse Transfer'),
    ], 'Movement Type', required=True, default='atlas_warehouse')

    @api.onchange('movement_type')
    def onchange_movement_type(self):
        if self.movement_type and self.movement_type == 'dos_warehouse':
            self.location_to_id = self.env['stock.location'].get_dos_location().id
        else:
            self.location_to_id = False

    @api.multi
    def check_values(self):
        for operation in self:
            if operation.location_from_id == operation.location_to_id:
                raise UserError(_('Source and destination statuses has to be different.'))

    @api.model
    def _get_operation_types(self):
        return [
            ('to_warehouse', _('')),
            ('from_warehouse', _('Movement'))
        ]

    @api.model
    def default_get(self, fields):
        res = super(InternalOperationMovement, self).default_get(fields)
        res['operation_type'] = 'from_warehouse'
        res['location_to_id'] = False
        return res

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate an internal operation.'))

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.env['internal.operation'].get_search_domain(args)
        return super(InternalOperationMovement, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def action_done_and_print(self):
        print_action = self.env.ref('config_sanitex_delivery.action_print_report_from_object_osv').read()[0]
        if print_action['context']:
            print_action['context'] = print_action['context'][:-1] + ', \'for_confirmation\':True}'
        return print_action

    @api.multi
    def get_records_to_print(self, report):
        to_print = self.mapped('operation_id').get_records_to_print(report)
        return to_print

    @api.multi
    def action_done(self):
        for operation in self:
            operation.operation_id.action_done(operation, send_tare_qty_info=False)
            # operation.operation_id.with_context(
            #     create_invoice_document_for_picking=False
            # ).action_done(operation, send_tare_qty_info=False)
            if operation.location_from_id.get_location_warehouse_id() == operation.location_to_id.get_location_warehouse_id():
                # Automatiškai gaunamas dokumentas jeigu produktus perkeliami tarp to pačio sandėlio statusų(vietų).
                (self.picking_to_warehouse_ids + self.picking_from_warehouse_ids).action_receive()
            if operation.location_from_id.get_location_warehouse_id() != operation.location_to_id.get_location_warehouse_id():
                # and operation.movement_type == 'atlas_warehouse' \
                # Jeigu kuriamias perkėlimas tarp dviejų skirtingų Atlas sandėlių tada turi susikurti
                # transportavimo užduotis(sale.order), kurią bus galima įdęti į maršrutą. Užduotis sukurs
                # iš dokumentų(account.invoice), kurie susikūrė iš važtaraščio(stock.picking),
                # kurie susikūrė patvirtinus šį movementą.
                pickings = self.env['stock.picking'].search([
                    '|',('picking_to_warehouse_for_internal_order_id','=',operation.operation_id.id),
                    ('picking_from_warehouse_for_internal_order_id','=',operation.operation_id.id),
                ])
                invoices = pickings.mapped('invoice_id')
                if operation.movement_type == 'atlas_warehouse':
                    company_partner = self.env.user.company_id.bls_owner_partner_id
                    invoices.write({
                        'partner_ref': company_partner.ref or '',
                        'partner_name': company_partner.name or '',
                        'partner_address': operation.location_to_id.load_address or '',
                        'partner_shipping_id': company_partner.id or False,
                        'partner_invoice_id': company_partner.id or False,
                        'partner_id': company_partner.id or False,
                        'posid': '',
                    })
                tasks = invoices.create_sale()
                tasks.write({'internal_movement_id': operation.id})
            # TODO: išsiaiškinti ar reikia užduoties perkeliant į dos sandėlį


    @api.multi
    def update_picking_vals(self, vals):
        self.update_location_vals(vals)
        if self.warehouse_to_id == self.warehouse_id:
            vals['operation_type'] = 'warehouse_movement'
        elif self.movement_type == 'dos_warehouse':
            vals['operation_type'] = 'bls_movement'
        else:
            vals['operation_type'] = 'atlas_movement'

        return vals

    @api.model
    def get_debt(self, operation, product):
        debt = 0.0
        if operation and operation.location_from_id:
            debt = self.env['sanitex.product.location.stock'].get_quantity(
                product_id=product.id, location_id=operation.location_from_id.id
            )
        else:
            context = self.env.context or {}
            if context.get('location_from_id', False):
                debt = self.env['sanitex.product.location.stock'].get_quantity(
                    product_id=product.id, location_id=context['location_from_id']
                )
        return debt

    @api.onchange('location_from_id')
    def on_change_location_from(self):
        for line in self.line_ids:
            if line.product_id:
                line.debt = self.get_debt(self, line.product_id)

    @api.onchange('location_to_id')
    def on_change_location_to(self):
        if self.location_to_id:
            self.warehouse_to_id = self.location_to_id.get_location_warehouse_id()

    @api.onchange('warehouse_to_id')
    def on_change_warehouse_to(self):
        if self.warehouse_to_id and self.location_to_id:
            if self.location_to_id.get_location_warehouse_id() != self.warehouse_to_id:
                self.location_to_id = False
        elif self.warehouse_to_id and not self.location_to_id:
            self.location_to_id = self.warehouse_to_id.wh_return_stock_loc_id.id

    @api.model
    def get_document_type(self):
        return 'product_movement'

    @api.model
    def get_document_type2(self):
        return 'product_movement'

    @api.multi
    def update_location_vals(self, vals):
        vals['location_id'] = self.location_from_id and self.location_from_id.id or False
        if self.warehouse_to_id != self.warehouse_id and self.movement_type == 'atlas_warehouse':
            vals['location_dest_id'] = self.warehouse_to_id.get_intermediate_location().id
        elif self.movement_type == 'atlas_warehouse':
            vals['location_dest_id'] = self.location_to_id and self.location_to_id.id or False
        else:
            vals['location_dest_id'] = self.env['stock.location'].get_dos_location().id
        return vals

    @api.multi
    def update_move_vals(self, vals):
        vals = self.update_location_vals(vals)
        if self.movement_type == 'dos_warehouse':
            vals['address_id'] = self.dos_location_posid_id.id

        return vals

    @api.multi
    def do_not_print_reports(self, reports=None):
        return

    @api.model
    def create(self, vals):
        operation = super(InternalOperationMovement, self).create(vals)
        operation.check_values()
        return operation

    @api.multi
    def write(self, vals):
        result = super(InternalOperationMovement, self).write(vals)
        self.check_values()
        return result