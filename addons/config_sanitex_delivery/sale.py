# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Afcheck_related_routesfero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, _, tools, SUPERUSER_ID
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

import datetime
import time
import traceback
import json
import math
import logging

from .stock import utc_str_to_local_str

_logger = logging.getLogger(__name__)

ROUTE_OPERATOR_GROUP_XML_ID = 'config_sanitex_delivery.stock_route_operator_group'

class TransportType(models.Model):
    _name = 'transport.type'
    _description = 'Transport Type'
    
    name = fields.Char('Name', size=64, required=True)
    code = fields.Char('Code', size=64, required=True)

    @api.model
    def create_if_not_exists(self, code):
        ttype = self.search([
            ('code', '=', code)
        ], limit=1)
        return ttype or self.create({
            'code': code,
            'name': code,
        })

class SaleOrder(models.Model):
    _inherit = "sale.order"
    _order = "date_order desc"

    @api.multi
    def _get_sale_orders_from_partner(self):
        sale_order_obj = self.env['sale.order']
        return sale_order_obj.search([
            ('partner_shipping_id','in',self.mapped('id'))
        ])

    @api.one
    def _get_invoice_count(self):
        # Suskaičiuoja kiek sąskaitų faktūrų turi užduotis.
        # Naudojama kad parodytį skaičių ant mygtuko

        self.sani_invoice_count = len(self.get_invoices())
    
    @api.model
    def _get_transportation_task_states(self):
        return [
            ('blank',_('Blank')),
            ('being_collected',_('Being Collected')),
            ('need_invoice',_('Fully Picked')),
            ('invoiced',_('Invoiced')),
            ('cancel',_('Canceled')),
        ]

    route_id = fields.Many2one('stock.route', 'Route',
        readonly=True, track_visibility='onchange',
    )
    collection_no = fields.Char('Collection No', size=64, track_visibility='onchange')
    route_type = fields.Char('Route Type', size=64, track_visibility='onchange')
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by',
        track_visibility='onchange', readobly=True
    )
    selection_sheet = fields.Char('Selection Sheet', size=512,
        track_visibility='onchange', readonly=True
    )
    cash = fields.Boolean('Cash', readonly=True,
        track_visibility='onchange'
    )
    cash_amount = fields.Float('Cash Amount', track_visibility='onchange', digts=(16, 2))
    alcohol = fields.Boolean('Alcohol', readonly=True, track_visibility='onchange')
    tobacco = fields.Boolean('Tobacco', track_visibility='onchange')
    invoice_line_ids = fields.Many2many(
        'account.invoice.line', 'sale_order_acc_inv_line_rel',
        'inv_line_id', 'sale_id', 'Invoice Lines',
        track_visibility='onchange'
    )
    comment = fields.Text('Comment', track_visibility='onchange')
    delivered_goods_time = fields.Char('Delivered Goods time', size=128,
        track_visibility='onchange'
    )
    delivering_goods_by_routing_program = fields.Char('Delivering Goods by Routing Program',
        track_visibility='onchange', size=256
    )
    delivery_number = fields.Char('Delivery Number', size=256, track_visibility='onchange')
    transport_types = fields.Char('Transport Types', size=256, track_visibility='onchange')
    vip_customer = fields.Boolean('VIP Customer', track_visibility='onchange')
    owner_id = fields.Many2one('product.owner', 'Owner', track_visibility='onchange')
    order_type = fields.Selection([
        ('order', 'Order'),
        ('instruction', 'Instruction')
    ], 'Order Type', track_visibility='onchange')
    delivery_type = fields.Selection([
        ('delivery', 'Delivery'),
        ('collection', 'Collection')
    ], 'Delivery Type', track_visibility='onchange')
    packing_id = fields.Many2one('stock.packing', 'Packing',
        track_visibility='onchange', readonly=True, index=True
    )
    external_sale_order_id = fields.Char('External ID', readonly=True,
        track_visibility='onchange', size=64
    )
    direction = fields.Char('Direction', size=256, track_visibility='onchange')
    name = fields.Char('Collection Sheet Number', size=128, track_visibility='onchange', copy=True)
    partner_invoice_id = fields.Many2one('res.partner', 'Invoice Address',
        readonly=True, required=False,
        states={'blank': [('readonly', False)]},
        help="Invoice address for current sales order.",
        track_visibility='onchange'
    )
    partner_shipping_id = fields.Many2one('res.partner', 'Delivery Address',
        readonly=True, required=False,
        states={'blank': [('readonly', False)]},
        help="Delivery address for current sales order.",
        track_visibility='onchange'
    )
    warehouse_id = fields.Many2one('stock.warehouse',
       'Order Picking Warehouse', required=True,
       track_visibility='onchange'
    )
    customer_region = fields.Char('Customer Region', size=256,
        track_visibility='onchange'
    )
    customer_loading_type = fields.Char('Customer Loading Type', size=256,
        track_visibility='onchange'
    )
    shipping_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Order Shipping Warehouse',
        track_visibility='onchange'
    )
    picking_location_id = fields.Many2one(
        'stock.location', 'Order Picking Location',
        track_visibility = 'onchange'

    )
    posid = fields.Char('POSID', size=128, readonly=True)
    shipping_date = fields.Date('Delivery Date', track_visibility = 'onchange')
    sani_invoice_count = fields.Integer(string="Invoice Count", readonly=True, compute='_get_invoice_count')
    transport_type_id = fields.Many2one('transport.type', 'Transport Group', track_visibility='onchange')
    document_type = fields.Selection([
        ('invoice','Invoice'),
        ('picking','Picking'),
        ('loading_sheet','Loading Sheet'),
        ('four_document_system','Four Document System')
    ], 'Document Type', track_visibility='onchange')
    not_combine_documents = fields.Boolean('Do Not Combine Documents', default=False, track_visibility='onchange')
    invoice_number = fields.Char(
        'Document Number', digits=256,
        readonly=True, track_visibility='onchange'
    )
    text_on_invoice = fields.Text('Text on Invoice', track_visibility='onchange')
    license_text = fields.Text('License Text', track_visibility='onchange')
    license_type = fields.Char('License Type', track_visibility='onchange')
    license_date = fields.Date('License Date', track_visibility='onchange')
    divide_vat = fields.Boolean('Divide VAT', track_visibility='onchange')
    urgent_order = fields.Boolean('Urgent Order', track_visibility='onchange')
    no_delivery = fields.Boolean(
        'No Delivery', default=False, track_visibility='onchange',
        help='Client will take products directly from the warehouse'
    )
    delivery_by_agent = fields.Boolean('Delivery by Agent', track_visibility='onchange')
    discount = fields.Float('Discount for Invoice', digits=(16, 2))
    client_type = fields.Selection([
        ('R','Retail'),
        ('W','Wholesale'),
        ('E','Export')
    ], 'Client Type', track_visibility='onchange')
    gate_id = fields.Many2one('stock.gate', 'Gate', track_visibility='onchange')
    container_ids = fields.Many2many(
        'account.invoice.container', 'sale_order_container_rel', 'sale_id', 
        'cont_id', 'Containers', track_visibility='onchange'
    )
    state = fields.Selection(
        _get_transportation_task_states, 'State', readonly=True, default='blank',
        track_visibility='onchange'
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True, 
        states={'blank': [('readonly', False)]}, required=False,
        change_default=True, index=True, track_visibility='always'
    )
    validity_date = fields.Date(
        string='Expiration Date', readonly=True, 
        states={'blank': [('readonly', False)]},
        track_visibility='onchange'
    )
    partner_name = fields.Char('Partner Name', size=128, readonly=True)
    has_out_route = fields.Boolean('Has Out Route', readonly=True, default=False)
    total_weight = fields.Float('Total Weight', digits=dp.get_precision('Stock Weight'), readonly=True, track_visibility='onchange')
    
    route_number = fields.Char('Route Number', size=64, readonly=True, track_visibility='onchange')
    driver_id = fields.Many2one('stock.location', 'Driver', readonly=True, track_visibility='onchange')
    license_plate = fields.Char('License Plate', size=16, readonly=True)
    driver_name = fields.Char('Driver Name', size=128, readonly=True)
    route_number_id = fields.Many2one('stock.route.number', 'Route Number', readonly=True, track_visibility='onchange', index=True)
    
    shipping_warehouse_route_released = fields.Boolean('Shipping Warehouse Route Released', redonly=True, default=False)
    pallet_qty = fields.Integer('Pallet Quantity', readonly=True, track_visibility='onchange')
    route_state_received = fields.Boolean('Received', readonly=False, default=False, track_visibility='onchange')
    show = fields.Boolean('Show', readonly=True, default=True)
    not_received = fields.Boolean('Not Received', readonly=False, default=False, track_visibility='onchange')
    sequence = fields.Integer('Sequence', readonly=True)
    received_by = fields.Char('Received By', size=128, readonly=True, track_visibility='onchange')
    release_date = fields.Date('Release Date', track_visibility='onchange')
    order_number_by_route = fields.Char('Order Number in Route', size=32, readonly=True, track_visibility='onchange')
    order_number_by_route_int = fields.Integer('Order Number in Route', readonly=True, default=0)
    transportation_order_id = fields.Many2one(
        'transportation.order', 'Transportation Order', track_visibility='onchange', index=True
    )
    transportation_order_line_ids = fields.One2many(
        'transportation.order.line', 'sale_id', "Transportation Order Lines", readonly=True
    )
    related_package_id = fields.Many2one('stock.package', 'Package', readonly=True,
        help='This is the package this transportation task was created from', track_visibility='onchange'
    )
    order_package_type = fields.Selection([
        ('package','Package'),
        ('order','Order')
    ], 'Task Type', help='Shows if this task created from order or from package', track_visibility='onchange')
    warehouse_next_to_id = fields.Many2one('stock.warehouse', 'Warehouse To', readonly=True, track_visibility='onchange')
    boolean_for_intermediate_wizard = fields.Boolean('Include')
    task_copied_from_task_id = fields.Many2one('sale.order', 'Copied From', readonly=True, copy=False)
    previous_task_received = fields.Boolean('Previous Task Received', readonly=True, default=False)
    internal_task_number = fields.Char('Internal No', readonly=True, size=64, track_visibility='onchange')
    task_at = fields.Char('Task At', size=64, help='This field shows where this task is at the moment', readonly=True)
    can_be_picked_up = fields.Boolean('Can Be Picked Up', readonly=True,
        help='Is marked when you can put this task into a route. And is not marked when this task have not reached picking warehouse'
    )
    extend_start = fields.Datetime('Extend Start', readonly=True)
    extend_end = fields.Datetime('Extend End', readonly=True)
    extend_duration = fields.Integer('Extend Duration in Seconds', readonly=True)
    route_template_id = fields.Many2one('stock.route.template', 'Route Template', readonly=True, index=True)
    route_id_str = fields.Char('Route ID', size=32, readonly=True)
    receive_fixed = fields.Boolean('Receive Fixed', readonly=True, default=False)
    has_related_document = fields.Boolean('Has Related Document', readonly=True,
        help='True if one of sale.order.line has related account.invoice.line', default=False
    )
    # related_document_indication = fields.Char('Doc. In?', readonly=True, size=4, default='-')
    related_document_indication = fields.Selection([
        ('yes','Yes'),
        ('-','-')
    ], 'Doc. In?', readonly=True, default='-')
    changes_in_route_formation = fields.Char('Changes When Route Was Created', size=256, readonly=True)
    changes_when_received = fields.Char('Changes When Task Was Received', size=256, readonly=True)
    import_timestamp = fields.Integer('Import Timestamp', readonly=True, help='Taken from import values', default=0)
    rounded_total_weight = fields.Integer('Total Weight', digits=(16,0), readonly=True, default=0)
    added_manually = fields.Boolean('Added Manually', deafult=False, readonly=True,
        help='Is checked when task is put into route template manually.(Using wizard)'
    )
    original_route_number_id = fields.Many2one('stock.route.number', 'Original Route Number', readonly=True, index=True,
        help='Filled in with route number received from integration. Even after route number is changed via wizard.'
    )
    replanned = fields.Boolean('Replanned', readonly=True, default=False, help='True if this task has been replanned.')
    processed_with_despatch = fields.Boolean('Processed with DA', default=False,
        help='Check True if this Task is related to dispatch advise. This is done to avoid overriding confirmed quantities.'
    )
    after_replan = fields.Boolean('After Replan', readonly=True, default=False)
    internal_movement_id = fields.Many2one('internal.operation.movement', 'Movement', readonly=True,
        help='Shows internal movement whitch generated this task.'
    )
    placeholder_for_route_template = fields.Boolean('Placeholder for Route Template', readonly=True, default=False)

    @api.multi
    def get_cash_amount_from_invoices(self):
        # Susumuoja visų susijusių sąskaitų faktūrų grynųjų pinigų reikšmes

        invoices = self.get_invoices()
        return sum(invoices.mapped('cash_amount'))

    @api.multi
    def update_cash_amount(self):
        # Kai pardavimas ir sąskaita faktūra būna užsiųsti atskirai, gali būti,
        # kad grynųjų pinigų suma buvo atsiųsti tik prie sąskaitos faktūros,
        # o ne prie pardavimo.

        for task in self:
            task_cash_amount = task.get_cash_amount_from_invoices()
            cash = False
            if task_cash_amount > 0.0:
                cash = True
            task.write({
                'cash_amount': task_cash_amount,
                'cash': cash
            })

    @api.multi
    def cancel_action_if_none_is_confirmed(self):
        tasks_to_cancel = self.env['sale.order']
        for task in self:
            confirmed_lines = self.env['sale.order.line'].search([
                ('picked_qty_filled_in','=',True),
                ('picked_qty','>',0.0),
                ('order_id','=',task.id)
            ], limit=1)
            not_confirmed_lines = self.env['sale.order.line'].search([
                ('picked_qty_filled_in','=',False),
                ('order_id','=',task.id)
            ], limit=1)
            if not confirmed_lines and not not_confirmed_lines:
                tasks_to_cancel += task
        tasks_to_cancel and tasks_to_cancel.cancel_transportation_task()

    @api.multi
    def action_cancel_transportation_task(self):
        self.write({
            'state': 'cancel'
        })


    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(SaleOrder, self)._export_rows(fields)
        return res

    @api.multi
    def to_dict_for_rest_integration(self):
        context = self.env.context or {}
        list_of_task_dict = []
        invoices = self.get_invoices()
        task_dict = {
            'tasktype': self.order_package_type == 'package' and 'Shipment' or 'Invoice', # Neaišku kokie kiti tipai
            'ownerid': self.owner_id and self.owner_id.product_owner_external_id or '',
            'posid': self.posid or '',
            'invoicetype': '1', # Neaišku kas per tipas iš kur imt
            'documenttype': 'Invoice',
            'orderno': self.name or '',
            'istobaco': int(self.tobacco),
            'isalco': int(self.alcohol),
            'documentdate': self.shipping_date, # Neaišku kurią datą perduoti
            'boxcount': 0, #ar čia paleičių kiekis ar dėžių? kaip
        }
        if context.get('rest_version', 1) > 1:
            task_dict.update({
                # 'orderId': '',#užsipildys invoice
                'carrierId': self.route_id and self.route_id.location_id and self.route_id.location_id.owner_id \
                    and self.route_id.location_id.owner_id.external_customer_id or '',
                'orderNo': self.name or '',
                # 'orderExternalNo': '',#užsipildys invoice
                'noteForDriver': self.comment or '',
                'deleted': False,
                # 'orderSum': '',#užsipildys invoice
                'orderDate': self.shipping_date or '',
                'ownerId': self.owner_id and self.owner_id.product_owner_external_id or '',
                # 'supplierId': '',#Negaunam
                # 'originPlaceId': '',#Negaunam
                'destinationPlaceId': self.posid or '',
                'ownerInfo': self.owner_id and self.owner_id.owner_to_dict_for_rest() or {},
                'containers': [],
                'placeInfo': self.partner_shipping_id and self.partner_shipping_id.posid_to_dict_for_rest_integration() or {},
                'supplierInfo': {}
            })
            for container in self.container_ids:
                container_dict = container.container_to_dict_for_res_integration()
                container_dict['routeId'] = self.route_id and str(self.route_id.id) or ''
                container_dict['carrierId'] = task_dict.get('carrierId', '')
                task_dict['containers'].append(container_dict)

        for invoice in invoices:
            invoice_dict = invoice.to_dict_for_rest_integration()
            task_dict_to_list = task_dict.copy()
            task_dict_to_list.update(invoice_dict)
            list_of_task_dict.append(task_dict_to_list)
        return list_of_task_dict

    @api.model
    def _needaction_domain_get(self):
        # Užklotas kad grąžintų tuščią domainą, nes kitu atveju grąžindavo [('message_needaction', '=', True)]
        # Tiksliai neaišku kokia viso to prasmė, bet kolkas užklotą, kad greičiau veiktų programa
        return []

    @api.multi
    def update_task_location(self, receiver_wh=None):
        # Prie užduočių pažymi kuriame sandėlyje yra užduotis. Svarbu kad pažymėtu
        # prie kiekvienos užduoties visoje grandinėje, nes visa grandinė yra kaip viena užduotis
        # tai reikia kad prie antros ar trečios grandinės grandies matytųsi, kad
        # užduotis vis dar yra pirmame sandėlyje.

        updated_tasks = self.env['sale.order']
        for task in self:
            if task in updated_tasks:
                continue
            if receiver_wh:
                all_tasks = task.get_all_chain()
                for all_task in all_tasks:
                    can_be_picked_up = False
                    if all_task.warehouse_id.code == receiver_wh:
                        can_be_picked_up = True
                    self.env.cr.execute('''
                        UPDATE
                            sale_order
                        SET
                            task_at = %s,
                            can_be_picked_up = %s
                        WHERE
                            id = %s
                    ''', (receiver_wh, can_be_picked_up, all_task.id))
                # all_tasks.sudo().write({'task_at': receiver_wh})
                updated_tasks += all_tasks
            else:
                all_tasks = task.get_all_chain()
                received_tasks = all_tasks.filtered('received_by')
                if received_tasks:
                    last_received = max(received_tasks, key=lambda task_record: task_record.sequence)
                    all_tasks.sudo().write({'task_at': last_received.received_by})


    @api.multi
    def update_task_receive_status(self):
        # Ar užduotis yra gauta ar ne priklauso nuo konteinerių. 
        # Ši funkcija pagal susijusias konteinerio būsenos eilute stock.route.container
        # pasižiūri ar visi užduoties konteineriai gauti ar ne ir pagal juos nustato pačios
        # užduoties gavimo būsena(gauta/negauta). Taip pat pasižiūri ar visi vienos
        # užduoties konteineriai gauti to pačio sandėlio, jeigu ne tada užduotis skeliama
        # į dvi(arba daugiau - priklauso nuo gavėjų skaičiaus) užduotis. 
        
#         rcl_env = self.env['stock.route.container']
        context = self.env.context or {}
        ctx_allow_copy = context.copy()
        ctx_allow_copy['allow_to_copy_sale'] = True
        ctx_allow_delete = context.copy()
        ctx_allow_delete['allow_to_delete_sale_with_route'] = True

        ctx_allow_copy['recompute'] = False
        ctx_allow_copy['skip_weight_calculation'] = True
        ctx_allow_copy['skip_task_line_recount'] = True
        ctx_allow_copy['skip_missing_links'] = True
        ctx_allow_copy['skip_missing_link_search'] = True
        ctx_allow_copy['skip_template_calculation'] = True
        ctx_allow_copy['skip_translations'] = True
        ctx_allow_copy['tracking_disable'] = True
        for sale in self:
            if not sale.route_id:
                continue
            if sale.route_state_received:
                continue
            
            sale_warehouse_to = sale.shipping_warehouse_id
            containers = sale.container_ids
            lines = sale.route_id.container_line_ids.filtered(
                lambda line_record: line_record.container_id in containers
            )
            #dėl testavimo
            if len(lines) != len(containers):
                raise UserError(_('Route containers does not match Sale containers'))
            
            containers_received_by_others = lines.filtered(
                lambda line_record: line_record.state == 'received' \
                    and line_record.warehouse_id != sale_warehouse_to
            )
            sale_container_lines = lines - containers_received_by_others
            no_delete = False
            if containers_received_by_others:
                other_warehouses = containers_received_by_others.mapped('warehouse_id')
#                 if lines == containers_received_by_others:
#                     # visa užduotis buvo gauta kituose sandėliuose
#                     if len(other_warehouses) == 1:
#                         sale.write({'shipping_warehouse_id': other_warehouses[0].id})
#                     else:   
                for other_warehouse in other_warehouses:
                    conteiners_to_warehouse_ids = containers_received_by_others.filtered(
                        lambda line_rec: line_rec.warehouse_id == other_warehouse
                    ).mapped('container_id').mapped('id')
                    if not sale.not_received:
                        sale.write({'container_ids': [
                            (3, conteiners_to_warehouse_id) for conteiners_to_warehouse_id in conteiners_to_warehouse_ids
                        ]})
                    already_existing_sales = sale.route_id.sale_ids.filtered(
                        lambda record_sale: record_sale.task_copied_from_task_id \
                            and record_sale.task_copied_from_task_id.id == sale.id
                    )
                    if already_existing_sales and not sale.not_received:
                        if len(already_existing_sales) > 1:
                            raise UserError('Per daug kopijų')
                        already_existing_sales.write({'container_ids': [
                            (4, conteiners_to_warehouse_id) for conteiners_to_warehouse_id in conteiners_to_warehouse_ids
                        ]})
                        already_existing_sales.update_task_receive_status()
                    else:

                        if not sale.container_ids and not sale.not_received:
                            sale_vals = {
                                'container_ids': [(
                                    6, 0, conteiners_to_warehouse_ids
                                )],
                                'shipping_warehouse_id': other_warehouse.id,
                                'changes_when_received': (sale.shipping_warehouse_id and sale.shipping_warehouse_id.code or '*') \
                                    + '--->' + other_warehouse.code,
                                'shipping_warehouse_route_released': False,
                                'route_state_received': True,
                                'not_received': False,
                                'intermediate_id': False,
                                'show': False,
                                'received_by': other_warehouse.code,
                                'task_at': other_warehouse.code,
                            }
                            sale.write(sale_vals)
                            sale.extend_chain()
                            sale.receive()
                        else:
                            default = {
                                'shipping_warehouse_route_released': False,
                                'route_state_received': False,
                                'not_received': False,
                                'intermediate_id': False,
                                'show': True,
                                'shipping_warehouse_id': other_warehouse.id,
                                'task_copied_from_task_id': sale.id,
                                'container_ids': [(
                                    6, 0, conteiners_to_warehouse_ids
                                )]
                            }
                            if sale.not_received:
                                del default['shipping_warehouse_id']
                                default['route_id'] = False
                                self.search([
                                    ('transportation_order_id','=',sale.transportation_order_id.id),
                                    ('id','!=',sale.id),
                                    ('sequence','>',sale.sequence),
                                    ('replanned','=',False),
                                ]).sudo().with_context(ctx_allow_delete).unlink()
                            new_task = sale.with_context(ctx_allow_copy).copy(default)
                            if sale.not_received:
                                sale.write({
                                    'received_by': sale.warehouse_id.code,
                                    'sequence': 0
                                })
                            new_task.create_transportation_order_for_sale()
                            new_task.update_task_receive_status()
                            if new_task.route_id.state == 'released':
                                new_task.extend_chain()
                                no_delete = True
            
            if not sale.container_ids:
                # vadinasi visi konteineriai buvo gauti ne tikslo sandėlyyje,
                # o kažkuriuose kituose
                sale.cancel_transportation_task(no_delete)
            if set(sale_container_lines.mapped('state')) == {'received'}:
                #gauti užduotį
                sale.receive()
            elif set(sale_container_lines.mapped('state')) == {'not_received'}:
                # patikrina ar negavo būtent tas sandėlys, kuris turėjo gauti
                if sale_container_lines.mapped('warehouse_id') == sale.shipping_warehouse_id:
                #negauti užduoties
                    sale.not_receive()
    
    @api.multi
    def cancel_transportation_task(self, no_delete=False):
        # Transportavimo užduotis atšaukiama (pavyzdžiui, kai visus jos konteinerius
        # priima kiti sandėliai ir tiems konteiniariams susikuria naujos transportavimo užduotys.
        # Atšaukiama užduotis lieka be konteinerių, bet dėl istorijos norima ją palikti prie maršruto).
        # Ištrinami ir sekantys grandinės užduotys.
        
        context = self.env.context or {}
        ctx = context.copy()
        ctx['allow_to_delete_sale_with_route'] = True
        for task in self:
            if not no_delete:
                self.search([
                    ('transportation_order_id','=',task.transportation_order_id.id),
                    ('id','!=',task.id),
                    ('sequence','>',task.sequence),
                    ('replanned','=',False),
                ]).sudo().with_context(ctx).unlink()
            task.action_cancel_transportation_task()
    
    @api.multi
    def get_vals_for_transportation_order(self):
        # Iš transportavimo užduoties gaunamos reikšmės 
        # naujam transportavimo užsakymui
        
        vals = {
            'name': self.name or ('SOID: ' + str(self.id)),
            'state': 'blank',
            'warehouse_id': self.warehouse_id.id,
            'partner_id': self.partner_id.id,
            'posid_partner_id': self.partner_shipping_id.id,
            'location_id': self.picking_location_id.id,
            'transport_type_id': self.transport_type_id.id
        }
        return vals
    
    @api.multi
    def create_transportation_order_for_sale(self):
        # Sukuriamas transportavimo užsakymas transportavimo užduočiai.
        # Ateityje transportavimo užsakymai turėtų susikurti prieš susikuriant
        # transportavimo užduotims, tačiau kol tas funkcionalumas dar nesuprogramuotas
        # bus naudojama ši funkcija, nes transportavimo užsakymas yra reikalingas surišti
        # transportavimo užduotis į grandinę
        
        to_env = self.env['transportation.order']
        for sale in self:
            if sale.transportation_order_id:
                continue
            order_vals = sale.get_vals_for_transportation_order()
            order = to_env.create(order_vals)
            sale.write({'transportation_order_id': order.id})
    
    @api.multi
    def get_vals_for_container(self):
        vals = {
            'state': 'in_terminal',
            'id_external': self.external_sale_order_id,
            'container_no': self.name,
            'weight': self.total_weight,
#             'sale_id': self.id
            'owner_id': self.owner_id and self.owner_id.id or False,
            'delivery_date': self.shipping_date,
            'buyer_id': self.partner_id.id,
            'buyer_address_id': self.partner_shipping_id.id,
            'picking_warehouse_id': self.warehouse_id.id,
            'buyer_posid': self.partner_shipping_id.possid_code or '',
        }
        
        return vals
    
    @api.multi
    def create_container_for_sale(self):
        # Sukuriamas konteineris pardavimui, jei pardavimas neturi 
        # nei vieno konteinerio. Kolkas naudojamas tol kol realūs konteineriai
        # nebus priskirinėjami pardavimams
        
        cont_env = self.env['account.invoice.container']
        for sale in self:
            if sale.container_ids:
                continue
            if sale.related_package_id and sale.related_package_id.container_ids:
                sale.write({'container_ids': [(6, 0, sale.related_package_id.container_ids.ids)]})
                continue
            container_vals = sale.get_vals_for_container()
            container = cont_env.create(container_vals)
            sale.write({'container_ids': [(6, 0, [container.id])]})
    
    @api.multi
    def get_all_chain(self):
        # Grąžina pasirinktos užduoties visą grandinę.
        # Grandinė ieškoma pagal susijusį transportavimo užsakymą
        
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        if not self.transportation_order_id:
            return self
        return self.with_context(ctx).search([
            ('transportation_order_id','=',self.transportation_order_id.id)
        ])
    
    def remove_from_system(self):
        ctx = (self.env.context or {}).copy()
        ctx['allow_to_delete_sale_with_route'] = True
        ctx['allow_to_delete_not_draft'] = True
        ctx['recompute'] = False
        self.sudo().with_context(ctx).unlink()


    @api.multi
    def can_delete_transportation_task(self, date_until=None, date_field=None):
        if date_field is None:
            user = self.env['res.users'].browse(self.env.uid)
            company = user.company_id
            date_field = company.get_date_field_for_removing_object(self._name)

        if date_until is None:
            user = self.env['res.users'].browse(self.env.uid)
            company = user.company_id
            days_after = company.delete_transportation_tasks_after
            today = datetime.datetime.now()
            date_until = (today - datetime.timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')        
        if not getattr(self, date_field) < date_until:
            return False
        return True
            
    
    @api.model
    def cron_delete_old_transportation_tasks(self):
        # Klausimai:
        # Pagal kuria data
        # Kokios busenos
        # ar galima trinti grandine dalimis
        # ar galima trinti uzduotis jeigu marsrutas neuzdarytas arba marsrutas dar netrinamas
        
        
        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_transportation_tasks_after

        date_field = company.get_date_field_for_removing_object(self._name)
        _logger.info('Removing old Transportation Tasks (%s days old) using date field \'%s\'' % (str(days_after), date_field))

        today = datetime.datetime.now()
        date_until = today - datetime.timedelta(days=days_after)
        tasks = self.search([
            (date_field,'<',date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Transportation Tasks: found %s records' % str(len(tasks)))

        if log:
            all_task_count = float(len(tasks))
            i = 0
            last_log = 0
        ids_to_unlink = tasks.mapped('id')
        for task_ids in [ids_to_unlink[ii:ii+50] for ii in range(0, len(ids_to_unlink), 50)]:
            try:
                self.browse(task_ids).remove_from_system()
                self.env.cr.commit()
                if log:
                    i += len(task_ids)
                    if last_log < int((i / all_task_count)*100):
                        last_log = int((i / all_task_count)*100)
                        _logger.info('Transportation task delete progress: %s / %s' % (str(i), str(int(all_task_count))))
            except Exception as e:
                err_note = 'Failed to delete  transportation task(ID: %s): %s \n\n' % (str(task_ids), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
        
    
    @api.multi
    def action_receive_not_received(self):
        # ši funkcija kviečiama negautiems užsakymams
        # priklausomai nuo naudotojo kuris spaudžia mygtuką
        # užduotis tampa gauta arba pasilieka atšaukta(dėl istorijos),
        # bet susikuria nauja užduoties kopija, kuri jau neturi jokio gavimo statuso
        
        user = self.env['res.users'].browse(self.env.uid)
        user_warehouse = user.default_warehouse_id
        context = self.env.context or {}
        ctx_allow_copy = context.copy()
        ctx_allow_copy['allow_to_copy_sale'] = True
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        ctx['allow_to_delete_sale_with_route'] = True
        self = self.with_context(ctx)
        for sale in self:
            if not sale.not_received or sale.sequence == 0:
                continue
            if sale.shipping_warehouse_id.id == user_warehouse.id:
                sale.receive()
            elif sale.warehouse_id.id == user_warehouse.id:
                self.search([
                    ('transportation_order_id','=',sale.transportation_order_id.id),
                    ('id','!=',sale.id),
                    ('sequence','>',sale.sequence),
                    ('replanned','=',False),
                ]).sudo().with_context(ctx).unlink()
                vals = {
                    'show': False,
                    'received_by': user_warehouse.code,
                    'sequence': 0
                }
                
                default = {
                    'route_id': False,
                    'container_ids': False,
                    'shipping_warehouse_route_released': False,
                    'route_state_received': False,
                    'not_received': False,
                    'intermediate_id': False,
                    'show': True,
                    'previous_task_received': False,
                    'shipping_warehouse_id': False
                }
                sale.with_context(ctx_allow_copy).copy(default)
                sale.write(vals)
            else:
                UserError(_('Something Wrong'))
            
        
    @api.multi
    def route_released(self):
        # ši funkcija kviečiama tiems transportavimo užsakymams, 
        # kurių maršrutas yra išleidžiamas.
        for sale in self:
            if not sale.previous_task_received and sale.sequence > 1:
                previous_sale = self.search([
                    ('transportation_order_id','=',sale.transportation_order_id.id),
                    ('shipping_warehouse_id','=',sale.warehouse_id.id),
                    ('route_state_received','=',False),
                    ('replanned','=',False),
                    ('id','!=',sale.id),
                    ('sequence','=',sale.sequence-1),
                ])
                if previous_sale:
                    raise UserError(_('Order %s which traveling from %s to %s are still not received') % (
                        previous_sale.name, previous_sale.warehouse_id.name, previous_sale.shipping_warehouse_id.name
                    ))
            # Tikrinama ar visi konteineriai kuriuos norima išleisti į maršruta yra terminale.
            if sale.delivery_type == 'delivery' and sale.related_package_id \
                and sale.container_ids.filtered(
                    lambda container_record: container_record.state != 'in_terminal'
            ):
                containers_not_in_terminal = sale.container_ids.filtered(
                    lambda container_record: container_record.state != 'in_terminal'
                )
                packages = containers_not_in_terminal.mapped('package_id')
                for package in packages:
                    if not sale.route_id.sale_ids.filtered(lambda sale_record: 
                        sale_record.related_package_id \
                        and sale_record.related_package_id == package \
                        and sale_record.delivery_type == 'collection'
                    ):
                        bad_containers = containers_not_in_terminal.filtered(lambda container_record: container_record.package_id == package)
                        raise UserError(_('You can\'t release route (%s, ID: %s) because it has containers(%s, ID:%s, task: %s) wich are not in terminal yet.') % (
                            sale.route_id.receiver or '', str(sale.route_id.id), bad_containers[0].container_no, str(bad_containers[0].id), sale.name
                        ))
        # self.write({'release_date': time.strftime('%Y-%m-%d')})
        self.env.cr.execute('''UPDATE sale_order set release_date = %s where id in %s''',(time.strftime('%Y-%m-%d'), tuple(self.mapped('id'))))
    
    @api.multi
    def read(self, fields=None, load='_classic_read'):

        context = self.env.context or {}
        if context.get('check_for_replanned_tasks', False):
            if 'name' in fields and ('replanned' not in fields or 'after_replan' not in fields):
                fields.append('replanned')
                fields.append('after_replan')
        res = super(SaleOrder, self).read(fields=fields, load=load)
        if 'order_number_by_route' in fields or fields is None:
            manual_translation = _('MANUAL')
            for sale in res:
                if sale.get('order_number_by_route', '') == 'MANUAL':
                    sale['order_number_by_route'] = manual_translation
        if not context.get('read_all_task', False):
            # padaryta dėl to kad jeigu išsiuntimo sandėlis toks pat kaip atrinkimo, tada nerodytų
            # išsiuntimo sandėlio, nes užduotis keliauja pas klientus
            for sale in res:
                if 'warehouse_id' in sale.keys() and 'shipping_warehouse_id' in sale.keys() and sale['warehouse_id'] == sale['shipping_warehouse_id']:
                    sale['shipping_warehouse_id'] = False
        if context.get('check_for_replanned_tasks', False):
            for sale in res:
                if (sale.get('replanned', False) or sale.get('after_replan', False)) and 'name' in fields:
                    sale['name'] = _('(R)') + '' + sale['name']
        return res
    
    @api.multi
    def action_open_all_chain(self):
        # atidaroma visa transportavimo užduočių grandinė, kuriai priklauso pardavimas
        # grandinė atsekama pagal išorinį pardavimo id (external_sale_order_id),
        # kuris yra vienodas visiems vienos grandinės transporto užsakymams

        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        open_sale_ids = self.get_all_chain().mapped('id')
    
    
        tree_view = self.env.ref('config_sanitex_delivery.view_sale_order_route_sequence_order_tree')
        form_view = self.env.ref('config_sanitex_delivery.view_sale_order_route_bls_form')
        return {
            'name': _('Transportation Task Chain: %s') % self.name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id,'tree'),(form_view.id,'form')],
            'context': ctx,
            'nodestroy': True,
            'domain': [
                ('id','in',open_sale_ids)
            ]
        }
    
    @api.multi
    def extend_chain(self, warehouses=[]):
        # pratesia transportavimo užduočių eilę nurodytais sandėliais

        if not warehouses:
            return self.check_transport_task_chain()
        for sale in self:
            extend_sale = sale
            extend_sale.write({'shipping_warehouse_id': warehouses[0]})
            for warehouse_id in warehouses[1:]:
                extend_sale = extend_sale.check_transport_task_chain()
                extend_sale.write({'shipping_warehouse_id': warehouse_id})
                
    
    # @api.multi
    # def continue_chain(self, shipping_warehouse_id, warehouse_id=None):
    #     # Transportavimo užduočiai pakeičia tikslo sandėlį į naują.
    #     # Nauja transportavimo užduotis turėtų susikurti automatiškai
    #     # kai write'as iškvies check_transport_task_chain
    #     # NEBENAUDOJAMA
    #     if warehouse_id:
    #         sale = self.continue_chain(warehouse_id)
    #     else:
    #         sale = self[0]
    #     if sale.shipping_warehouse_id and sale.shipping_warehouse_id.id == shipping_warehouse_id:
    #         return sale
    #     sale.write({'shipping_warehouse_id': shipping_warehouse_id})
    #     return self.search([
    #         ('external_sale_order_id','=',sale.external_sale_order_id),
    #         ('shipping_warehouse_id','=',shipping_warehouse_id),
    #         ('warehouse_id','=',shipping_warehouse_id)
    #     ])
    
    @api.multi
    def check_transport_task_chain(self):
        # patikrina ar transportavimo užduotis yra paskutinė grandinėje, 
        # t.y. ar atrinkimo ir išvežimo sandėliai sutampa. Jeigu ne tada
        # sukuria naują transportavimo užduotį užbaigti grandinę, t.y. 
        # kur atrinkimo sandėlys sutampa su siuntimo sandėliu
        
        context = self.env.context or {}
        ctx_allow_copy = context.copy()
        ctx_allow_copy['allow_to_copy_sale'] = True
        ctx_allow_copy['recompute'] = False
        ctx_allow_copy['skip_weight_calculation'] = True
        ctx_allow_copy['skip_task_line_recount'] = True
        ctx_allow_copy['skip_missing_links'] = True
        ctx_allow_copy['skip_missing_link_search'] = True
        ctx_allow_copy['skip_template_calculation'] = True
        ctx_allow_copy['skip_translations'] = True
        ctx_allow_copy['tracking_disable'] = True
        ctx_allow_delete = context.copy()
        ctx_allow_delete['allow_to_delete_sale_with_route'] = True
        new_sale = False
        ids = self.mapped('id')
        # self.invalidate_cache()
        # self.env['sale.order.line'].invalidate_cache()
        # self.env.clear()
        # for sale in self:
        for sale_id in ids:
            sale = self.browse(sale_id)
            start_time = datetime.datetime.now()
            if not sale.shipping_warehouse_id:
                sale.write({'shipping_warehouse_id': sale.warehouse_id.id})
                continue
            if sale.warehouse_id.id == sale.shipping_warehouse_id.id:
                continue
            next_sales = self.search([
                ('transportation_order_id','=',sale.transportation_order_id.id),
                ('shipping_warehouse_id','=',sale.shipping_warehouse_id.id),
                ('replanned','=',False),
                ('warehouse_id','=',sale.shipping_warehouse_id.id),
                ('sequence','=',sale.sequence+1)
            ])
            if not next_sales:
                self.search([
                    ('transportation_order_id','=',sale.transportation_order_id.id),
                    ('id','!=',sale.id),
                    ('route_state_received','=',False),
                    ('sequence','>',sale.sequence),
                    ('replanned','=',False),
                ]).with_context(ctx_allow_delete).sudo().unlink()
                default = {
                    'shipping_warehouse_id': sale.warehouse_next_to_id  \
                        and sale.warehouse_next_to_id.id != sale.shipping_warehouse_id.id \
                        and sale.warehouse_next_to_id.id or sale.shipping_warehouse_id.id,
                    'warehouse_id': sale.shipping_warehouse_id.id,
#                     'related_route_ids': [(6, 0, [])],
                    'route_id': False,
#                     'first_route_id': False,
#                     'last_route_id': False,
#                     'to_release_route_id': False,
#                     'container_ids': False,
                    'shipping_warehouse_route_released': False,
                    'route_state_received': False,
                    'intermediate_id': False,
#                     'has_route': False,
                    'show': True,
                    'sequence': sale.sequence + 1,
                    'previous_task_received': False,
#                     'shipping_warehouse_id': False,
                    'name': sale.name,
                    'can_be_picked_up': False,
                    'date_order': sale.date_order
                }
                if new_sale:
                    new_sale += sale.sudo().with_context(ctx_allow_copy).copy(default=default)
                else:
                    new_sale = sale.sudo().with_context(ctx_allow_copy).copy(default=default)
            else:
                next_sales[0].write({'show': True})
            end_time = datetime.datetime.now()
            self.env.cr.execute('''
                UPDATE
                    sale_order
                SET
                    extend_start = %s,
                    extend_end = %s,
                    extend_duration = %s,
                    receive_fixed = False
                WHERE
                    id = %s
                ''', (start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'),
                      (end_time - start_time).seconds, sale.id
            ))
            if context.get('commit_after_each_task_extention', False):
                self.env.cr.commit()
        new_sale and new_sale.mapped('route_number_id').create_route_template()
        return new_sale
    
    @api.multi
    def action_receive_wizard(self):
        # iš sąrašo vaizdo kviečiamas mygtukas
        self.receive()
#         return {
#             "type": "ir.actions.no_destroy",
#         }
        return {
            "type": "reload",
        }
    
    @api.multi    
    def action_not_receive_wizard(self):
        # iš sąrašo vaizdo kviečiamas mygtukas
        self.not_receive()
        return {
            "type": "reload",
        }
    
    @api.multi
    def receive(self):
        # pažymima prie pardavimo kad jis yra gautas
        wh_code = self.env['res.users'].browse(self.env.uid).default_warehouse_id.code
        # vals = {
        #     'route_state_received': True,
        #     'not_received': False,
        #     'show': False,
        #     'received_by': wh_code
        # }
                    
        for sale in self:
            # next_sales = self.search([
            #     ('transportation_order_id','=',sale.transportation_order_id.id),
            #     ('sequence','=',sale.sequence+1),
            #     ('show','=',False)
            # ])
            # if next_sales:
            self.env.cr.execute('''
                UPDATE
                    sale_order
                SET
                    previous_task_received = %s,
                    show = %s
                WHERE
                    transportation_order_id = %s
                    AND sequence = %s
                    AND replanned = False
            ''', (True, True, sale.transportation_order_id.id, sale.sequence+1))
                # next_sales.write({'show': True, 'previous_task_received': True})
        self.env.cr.execute('''
            UPDATE
                sale_order
            SET
                route_state_received = %s,
                not_received = %s,
                show = %s,
                received_by = %s
            WHERE
                id in %s
        ''', (True, False, False, wh_code, tuple(self.mapped('id'))))
        self.update_task_location(wh_code)
        self.mapped('route_id').update_received_warehouse_ids_text()
        # self.write(vals)
        
#         user = self.env['res.users'].browse(self.env.uid)
#         if user.default_warehouse_id:
#             print 'kk'
#             vals['received_by'] = user.default_warehouse_id.code            
#             for sale in self:
#                 if sale.shipping_warehouse_id.id != user.default_warehouse_id.id:
#                     # Jeigu gavo ne tas sandėlis kuri turėjo gauti
#                     #TODO: Išsiaiškinti koks tikslo sandėlis tokiu atveju turi būti
#                     sale.write({'shipping_warehouse_id': user.default_warehouse_id.id})
#                     sale.check_transport_task_chain()
#                 else:
#                     print 'search next'
#                     # Pažiūri ar grandinėje yra sekančių nematomų užduočių ir padaro jas mantomas
#                     next_sales = self.search([
#                         ('transportation_order_id','=',sale.transportation_order_id.id),
#                         ('sequence','=',sale.sequence+1),
#                         ('show','=',False)
#                     ])
#                     print 'next_sales', next_sales, [
#                         ('transportation_order_id','=',sale.transportation_order_id.id),
#                         ('sequence','=',sale.sequence+1),
#                         ('show','=',False)
#                     ]
#                     if next_sales:
#                         next_sales.write({'show': True})
#             self.write(vals)
#         else:
#             raise UserError(_('You have no warehouse selected'))
        
    @api.multi
    def not_receive(self):
        # pažymima prie pardavimo kad jis yra negautas
        
        vals = {
            'route_state_received': False, 
            'not_received': True,
            'show': True
        }
        
        # sekančias užduotis padaro nematomas ir išima iš maršrutų jeigu jau būna priskirti
        for sale in self:
            next_sales = self.search([
                ('transportation_order_id','=',sale.transportation_order_id.id),
                ('sequence','>',sale.sequence),
                ('replanned','=',False)
            ])
            next_sales.write({
                'show': False,
                'route_id': False
            })
        self.write(vals)

    @api.model
    def cron_fix_received_tasks(self):
        _logger.info('Fixing Receive status')
        tasks_to_fix = self.with_context(search_by_user_sale=False).search([
            ('route_state_received','=',True),
            ('receive_fixed','=',False)
        ])
        _logger.info('Fixing Receive status. Found %s tasks to check.' % str(len(tasks_to_fix)))
        fixed = 0

        for task_to_fix in tasks_to_fix:
            task = self.with_context(search_by_user_sale=False).search([
                ('transportation_order_id','=',task_to_fix.transportation_order_id.id),
                ('sequence','=',task_to_fix.sequence + 1),
                ('replanned','=',False)
            ])
            if task:
                try:
                    if not task.previous_task_received:
                        task.write({'previous_task_received': True, 'show': True})
                        fixed += 1
                    task_to_fix.write({'receive_fixed': True})
                except:
                    _logger.info('Fixing Receive status. Error: %s' % str(task_to_fix.transportation_order_id))
        _logger.info('Fixing Receive status. Finished. Tasks needed to be fixed: %s' % str(fixed))

    @api.multi
    def update_shipping_warehouse_route_released(self):
        # užpildo pardavimams varnelę pagal kurią operatoriam filtruoja pardavimus
        # ir atrenka tokius kurie atkeliauja į operatoriaus sandėlį
        # (t.y atrenka pardavimus kurie priskirti vidiniams maršrutams kurių tikslo sandėlys yra 
        # operatoriaus numatytas sandėlys ir tas maršrutas yra išleistas)

        #LYGTAIS NEBENAUDOJAMA

        # for sale in self:
        #     if sale.shipping_warehouse_id:
        #         if sale.route_id and sale.route_id.type in ['internal', 'mixed'] \
        #             and sale.route_id.state in ['released', 'closed'] \
        #         :
        #             sale.write({'shipping_warehouse_route_released': True})
        #         else:
        #             sale.write({'shipping_warehouse_route_released': False})
        return False
    
    @api.multi
    def group_sales_by_warehouses(self):
        # sugrupuoja pardavimus pagal atrinkimo ir siuntimo sandėlius
        # grąžinamas rezultatas: {
        #     (atrinkimo_sandėlio_id1, siuntimo_sandėlio_id2): recordlist[pardavimo objektas1, pardavimo objektas2...],
        #     (atrinkimo_sandėlio_id1, siuntimo_sandėlio_id3): recordlist[pardavimo objektas3, pardavimo objektas4...]
        # }
        
        grouped_sales = {}
        for sale in self:
            picking_warehouse_id = sale.warehouse_id and sale.warehouse_id.id or False
            shipping_warehouse_id = sale.shipping_warehouse_id and sale.shipping_warehouse_id.id or False
            key = (picking_warehouse_id, shipping_warehouse_id)
            if key not in grouped_sales.keys():
                grouped_sales[key] = sale
            else:
                grouped_sales[key] += sale
        return grouped_sales

    # @api.multi
    # def update_weight_after_invoice(self):
    #     tasks_to_update = self.filtered('has_related_document')
    #     sql = '''
    #         UPDATE
    #             sale_order_line
    #         SET
    #             total_weight = picked_qty
    #
    #     '''

    @api.multi
    def update_weight_and_pallete_with_sql(self):
        sql = '''
            UPDATE
                sale_order so
            SET
                total_weight = (select SUM(total_weight) from sale_order_line where order_id = so.id),
                pallet_qty = (select SUM(pallet_qty) from sale_order_line where order_id = so.id),
                rounded_total_weight = (select SUM(total_weight) from sale_order_line where order_id = so.id)
            WHERE 
                so.id in %s
        '''
        self.env.cr.execute(sql, (tuple(self.ids),))

    @api.multi
    def update_weight_with_sql(self):
        if self:
            upd_weight_sql = '''
                UPDATE
                    sale_order so
                SET
                    total_weight = (select SUM(total_weight) from sale_order_line where order_id = so.id)
                WHERE 
                    so.id in %s
                    AND so.order_package_type = 'order'
            '''
            upd_weight_where = (self._ids,)
            self.env.cr.execute(upd_weight_sql, upd_weight_where)
            upd_weight_sql = '''
                UPDATE
                    sale_order so
                SET
                    total_weight = (
                        SELECT 
                            SUM(aic.weight) 
                        FROM 
                            account_invoice_container aic, 
                            sale_order_container_rel rel 
                        WHERE 
                            rel.sale_id = so.id
                            AND rel.cont_id = aic.id
                    )
                WHERE 
                    so.id in %s
                    AND so.order_package_type = 'package'
            '''
            upd_weight_where = (self._ids,)
            self.env.cr.execute(upd_weight_sql, upd_weight_where)
            upd_weight_sql = '''
                UPDATE
                    sale_order so
                SET
                    rounded_total_weight = round(total_weight)
                WHERE 
                    so.id in %s
            '''
            upd_weight_where = (self._ids,)
            self.env.cr.execute(upd_weight_sql, upd_weight_where)
            self.invalidate_cache(fnames=['total_weight'], ids=list(self._ids))

    @api.multi
    def update_weight(self):
        context = self.env.context or {}
        if context.get('skip_weight_calculation', False):
            return
        for sale in self:
            weight = sale.get_total_weight()
            pallet_qty = sale.get_total_pallet()
            if sale.total_weight != weight or sale.pallet_qty != pallet_qty:
                sale.write({
                    'total_weight': weight,
                    'pallet_qty': pallet_qty,
                    'rounded_total_weight': int(round(sale.rounded_total_weight,0)),
                })
        self.mapped('route_id').update_weight()
    
    @api.multi
    def get_total_pallet(self):
        # suskaičiuoja suminį pardavimų palečių skaičių
        
        quantity = 0
        for sale in self:
            for line in sale.order_line:
                quantity += line.pallet_qty
        return quantity

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_task_copied_from_task_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_task_copied_from_task_id_index ON sale_order (task_copied_from_task_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_external_id_index ON sale_order (external_sale_order_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_intermediate_id_index ON sale_order (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_route_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_route_id_index ON sale_order (route_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_related_package_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_related_package_id_index ON sale_order (related_package_id)')
        cr.execute("""
            SELECT 
                count(*) 
            FROM 
                information_schema.constraint_table_usage 
            WHERE 
                table_name = 'sale_order'
                and constraint_name = 'sale_order_name_uniq'
        """)
        res = cr.fetchone()
        if res[0] > 0:
            cr.execute("""
                ALTER TABLE 
                    sale_order
                DROP CONSTRAINT 
                    sale_order_name_uniq
            """)
    
    # def __init__(self, pool, cr):
    #     cr.execute("""
    #         SELECT
    #             count(*)
    #         FROM
    #             information_schema.constraint_table_usage
    #         WHERE
    #             table_name = 'sale_order'
    #             and constraint_name = 'sale_order_name_uniq'
    #     """)
    #     res = cr.fetchone()
    #     if res[0] > 0:
    #         cr.execute("""
    #             ALTER TABLE
    #                 sale_order
    #             DROP CONSTRAINT
    #                 sale_order_name_uniq
    #         """)
    #     return super(SaleOrder, self).__init__(pool, cr)

    @api.multi
    def copy(self, default=None):
        context = self.env.context or {}
        if context.get('allow_to_copy_sale'):
            return super(SaleOrder, self).copy(default=default)
        raise UserError(_('You cannot duplicate a sale.'))
    
    @api.multi
    def get_invoices(self):
        # Paduodama tik viena užduotis. Grąžina susijusias sąskaitas faktūras
        
        invoices = self.env['account.invoice']
        for line in self.order_line:
            for invoice_line in line.invoice_line_ids:
                if invoice_line.invoice_id not in invoices and invoice_line.invoice_id.state != 'cancel':
                    invoices += invoice_line.invoice_id
                    
        if self.transportation_order_id and self.transportation_order_id.invoice_ids:
            for invoice in self.transportation_order_id.invoice_ids:
                if invoice.state == 'close' and not invoice.parent_invoice_id:
                    invoices += invoice
#             invoices += self.transportation_order_id.invoice_ids
        if self.order_package_type == 'package' and self.related_package_id:
            invoices |= invoices.search([
                ('delivery_type','=',self.delivery_type),
                ('stock_package_id','=',self.related_package_id.id)
            ])
        return invoices
        
    @api.multi
    def get_total_weight(self):
        weight = 0.0
        for sale in self:
            if sale.transportation_order_id and sale.transportation_order_line_ids:
                for to_line in sale.transportation_order_line_ids:
                    weight += to_line.product_id.weight or 0.0
            else:
                for line in sale.order_line:
                    weight += line.total_weight
                    
                # kai užduotis susikuria iš siuntos ji neturi eilučių, bet turi conteinerius
                if not sale.order_line and sale.container_ids:
                    for container in sale.container_ids:
                        weight += container.weight
        return weight

    @api.multi
    def compute_invoice_number_sql(self):
        if self:
            task_upd_sql = '''
                UPDATE
                    sale_order so
                SET 
                    related_document_indication = %s,
                    has_related_document = True,
                    invoice_number = (
                        SELECT 
                            string_agg(distinct(ai.all_document_numbers), ', ')
                        FROM
                            sale_order so2
                            JOIN sale_order_line sol on (sol.order_id = so2.id)
                            JOIN invoice_line_so_line_rel rel on (rel.order_line_id = sol.id)
                            JOIN account_invoice_line ail on (ail.id = rel.invoice_line_id)
                            JOIN account_invoice ai on (ail.invoice_id=ai.id)
                        WHERE
                            so2.id = so.id    
                    )
                WHERE
                    so.id in %s
            '''
            task_upd_where = ('yes', self._ids)
            self.env.cr.execute(task_upd_sql, task_upd_where)

            ln_get_sql = '''
                SELECT
                    id
                FROM 
                    sale_order_line
                WHERE
                    order_id in %s
            '''
            ln_get_where = (self._ids,)
            self.env.cr.execute(ln_get_sql, ln_get_where)
            sol_ids = [sol_id[0] for sol_id in self.env.cr.fetchall()]
            lines = self.env['sale.order.line'].browse(sol_ids)
            self.invalidate_cache(ids=list(self._ids))
            lines.invalidate_cache(ids=list(lines._ids))
            lines.update_weight_with_sql()

    
    @api.multi
    def compute_invoice_number(self):
        for sale in self:
            invoices = []
            for line in sale.order_line:
                for invoice_line in line.invoice_line_ids:
                    inv_names = [invoice_line.invoice_id.name or '']
                    inv_names += [invoice_line.invoice_id.nkro_number or '']
                    inv_names += [invoice_line.invoice_id.nsad_number or '']
                    for inv_name in inv_names:
                        if inv_name and inv_name not in invoices:
                            invoices.append(inv_name)
            if invoices:
                sale.write({
                    'invoice_number': ', '.join(invoices),
                    'has_related_document': True,
                    'related_document_indication': 'yes'
                })
                sale.order_line.update_weight()
        return True
                
    @api.multi
    def transfer_sales_packing(self, to_route_id):
        route_obj = self.env['stock.route']
        
        for sale in self:
            if sale.packing_id:
                if sale.packing_id.state == 'done':
                    raise UserError(_('You can\'t transfer sale because its packing(%s, ID: %s) is already done') % (
                        sale.packing_id.number, str(sale.packing_id.id))
                    )
                all_orders_of_posid_removed_from_route = True
                for order in sale.packing_id.route_id.sale_ids:
                    if order.partner_shipping_id and sale.partner_shipping_id\
                        and order.partner_shipping_id.id == sale.partner_shipping_id.id\
                    :
                        all_orders_of_posid_removed_from_route = False
                        break
                if all_orders_of_posid_removed_from_route:
                    sale.packing_id.write({
                        'route_id': to_route_id
                    })
                else:
                    route_obj.browse(to_route_id).generate_product_act_new([sale.id])
        return True    
    
#     def update_args(self, cr, uid, args, context=None):
#         #nebenaudojama
#         if context is None:
#             context = {}
#         if context.get('args_updated', False):
#             return True
#         else:
#             context['args_updated'] = True
#         route_obj = self.env('stock.route')
#         if context.get('just_not_assigned', False):
#             if context.get('route_id', False):
#                 route = route_obj.browse(cr, uid, context['route_id'], context=context)
#                 if route.type == 'out':
#                     cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             sale_order
#                         WHERE
#                             id not in (SELECT
#                                     sorr.order_id
#                                 FROM
#                                     sale_order_routes_relation sorr
#                                     join stock_route sr on (sr.id = sorr.route_id)
#                                 WHERE
#                                     sorr.route_id is not null
#                                     AND sr.type = '%s'
#                             )
#                     ''' % route.type)
#                     res = cr.fetchall()
#                     ord_ids = [res_one[0] for res_one in res]
#                     args.append(('id','in',ord_ids))
#                 else:
#                     cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             sale_order
#                         WHERE
#                             id not in (SELECT
#                                     sorr.order_id
#                                 FROM
#                                     sale_order_routes_relation sorr
#                                     join stock_route sr on (sr.id = sorr.route_id)
#                                 WHERE
#                                     sorr.route_id is not null
#                                     AND sr.state != 'draft'
#                             )
#                     ''')
#                     res = cr.fetchall()
#                     ord_ids = [res_one[0] for res_one in res]
#                     args.append(('id','in',ord_ids))
#
#                     # pašalinta, nes neaišku su kuriuo sandėliu tikrinti
# #         if context.get('route_id', False):
# #             route = route_obj.browse(cr, uid, context['route_id'], context=context)
# #             if route.type == 'out':
# #                 args.append(('warehouse_id','=',route.warehouse_id.id))
#         return True

    @api.model
    def _get_ids(self):
        context = self.env.context or {}
        ids = []
        route_obj = self.env['stock.route']
        if context.get('just_not_assigned', False):
            if context.get('route_id', False):
                route = route_obj.browse(context['route_id'])
                if route.type == 'out':
                    self.env.cr.execute('''select id from sale_order where id not in (select order_id from sale_order_routes_relation sorr join stock_route sr on (sr.id = sorr.route_id) where sr.type = 'out' or sr.type is null)''')
                    res = self.env.cr.fetchall()
                    ids = [res_one[0] for res_one in res]
                else:
                    self.env.cr.execute('''select id from sale_order where id not in (select order_id from sale_order_routes_relation sorr join stock_route sr on (sr.id = sorr.route_id) where sr.state = 'draft' or sr.state is null)''')
                    res = self.env.cr.fetchall()
                    ids = [res_one[0] for res_one in res]
        return ids

    @api.model
    def get_first_sale_order_by_external_id(self, external_id):
        return self.search([
            ('external_sale_order_id','=',external_id),
            ('replanned','=',False)
        ], order='id', limit=1)

    @api.multi
    def check_if_can_close_route(self):
        if self:
            check_sql = '''
                SELECT
                    r.name,
                    s.name,
                    w.name
                FROM
                    sale_order s
                    LEFT JOIN stock_route r on (r.id=s.route_id)
                    LEFT JOIN stock_warehouse w on (w.id=s.shipping_warehouse_id)
                WHERE
                    s.id in %s
                    AND s.state != 'cancel'
                    AND s.warehouse_id != s.shipping_warehouse_id
                    AND s.route_state_received = False
                    AND s.not_received = False
            '''
            check_where = (tuple(self._ids),)
            self.env.cr.execute(check_sql, check_where)
            result = self.env.cr.fetchall()
            if result:
                raise UserError(_('You can\'t close route %s. Because task %s witch is going to %s is neither received or not received.') % (
                    result[0][0], result[0][1], result[0][2]
                ))

    @api.multi
    def check_as_replanned(self):
        # Pažymime užduotį ir jos vėlesnius žingsnius kaip perplanuotus
        for task in self:
            task.get_all_chain().write({'replanned': True, 'show': False, 'after_replan': False})
        self.mapped('container_ids').write({'state': 'in_terminal'})


    @api.multi
    def copy_sale_for_replanning(self, additional_vals=None):
        # kartais būna kad užduotis Atlase yra įdėta į maršrutą ir išsiųsta,
        # bet vairuotojas iš tikro užduoties neišvežė. todėl po kelių dienų
        # tą pačią užduotį gali integraciją atsiųsti jau kitame maršruto ruošinyje,
        # tokiu atveju senos užduoties nekeičiame, o ją nukopijuojame ir toliau dirbame su koipja.

        if additional_vals is None:
            additional_vals = {}
        if not self or (self.route_number_id and additional_vals.get('route_number_id', False) == self.route_number_id.id):
            return self
        context = self.env.context or {}
        ctx_allow_copy = context.copy()
        ctx_allow_copy['allow_to_copy_sale'] = True
        ctx_allow_copy['recompute'] = False
        ctx_allow_copy['skip_weight_calculation'] = True
        ctx_allow_copy['skip_task_line_recount'] = True
        ctx_allow_copy['skip_missing_links'] = True
        ctx_allow_copy['skip_missing_link_search'] = True
        ctx_allow_copy['skip_template_calculation'] = True
        ctx_allow_copy['skip_translations'] = True
        ctx_allow_copy['tracking_disable'] = True

        default_vals = additional_vals.copy()
        default_vals.update({
            'route_id': False,
            'shipping_warehouse_route_released': False,
            'route_state_received': False,
            'intermediate_id': False,
            'show': True,
            'replanned': False,
            'name': self.name,
            'can_be_picked_up': False,
            'date_order': self.date_order,
            'after_replan': True
        })
        self.check_as_replanned()
        return self.with_context(ctx_allow_copy).copy(default_vals)

    @api.model
    def get_user_domain(self, args=None):
        # funkcija kuri sukuria sale.order paieškos domeną
        # atsižvelgiant į conteksto reikšmę
        if args is None:
            args = []
        if self.env.uid == SUPERUSER_ID and False:
            return []
        
        context = self.env.context or {}
        domain = []

        if context.get('search_by_user_sale', False):
            usr_env = self.env['res.users']
            user = usr_env.browse(self.env.uid)
            if user.default_warehouse_id or user.default_region_id:
                # domain.append(('warehouse_id','=',user.default_warehouse_id.id))
                domain.append(('warehouse_id','in',user.get_current_warehouses().mapped('id')))
                domain.append(('route_id','=',False))
                domain.append(('show','=',True))
                domain.append(('route_state_received','=',False))
                domain.append(('state','!=','cancel'))
        elif context.get('search_by_user_not_received_sale', False):
            usr_env = self.env['res.users']
            user = usr_env.browse(self.env.uid)
            if user.default_warehouse_id or user.default_route_id:
                domain.append(('route_state_received','=',False))
                domain.append(('not_received','=',True))
                domain.append(('show','=',True))
                domain.append('|')
                domain.append(('warehouse_id','=',user.default_warehouse_id.id))
                domain.append(('shipping_warehouse_id','=',user.default_warehouse_id.id))
        if context.get('search_for_template_view', False):
            for arg in args:
                if len(arg) == 3 and arg[0] == 'route_template_id' and arg[2]:
                    usr_env = self.env['res.users']
                    user = usr_env.browse(self.env.uid)
                    if user.default_warehouse_id or user.default_region_id:
                        # [('route_state_received','=',False),('sequence','=',)]
                        # domain.append('|')
                        # domain.append(('warehouse_id','in',user.get_current_warehouses().mapped('id')))
                        # domain.append(('shipping_warehouse_id','in',user.get_current_warehouses().mapped('id')))
                        for tmpl_id in arg[2]:
                            warehouse_ids = user.get_current_warehouses().mapped('id')
                            self.env.cr.execute('''
                                SELECT
                                    id, name
                                FROM
                                    sale_order
                                WHERE
                                    route_template_id = %s
                                    AND warehouse_id in %s
                                    AND warehouse_id = shipping_warehouse_id
                                    AND previous_task_received = True
                            ''', (tmpl_id, tuple(warehouse_ids),))
                            results = self.env.cr.fetchall()
                            ids = []
                            names = []
                            for res in results:
                                ids.append(res[0])
                                names.append(res[1])
                            if names:
                                self.env.cr.execute('''
                                    SELECT
                                        max(id)
                                    FROM
                                        sale_order
                                    WHERE
                                        route_template_id = %s
                                        AND (shipping_warehouse_id in %s
                                            OR warehouse_id in %s)
                                        AND previous_task_received = True
                                        AND name not in %s
                                    GROUP BY
                                        name
                                ''', (tmpl_id, tuple(warehouse_ids), tuple(warehouse_ids), tuple(names),))
                            else:
                                self.env.cr.execute('''
                                    SELECT
                                        max(id)
                                    FROM
                                        sale_order
                                    WHERE
                                        route_template_id = %s
                                        AND (shipping_warehouse_id in %s
                                            OR warehouse_id in %s)
                                        AND previous_task_received = True
                                    GROUP BY
                                        name
                                ''', (tmpl_id, tuple(warehouse_ids), tuple(warehouse_ids),))

                            results = self.env.cr.fetchall()
                            for res in results:
                                ids.append(res[0])
                            domain.append(('id','in',ids))
                    break
#                 
#                 domain.append('|')
#                 domain.append('&')
#                 domain.append(('warehouse_id','=',user.default_warehouse_id.id))
#                 domain.append('&')
#                 domain.append(('has_route','=',False))
#                 domain.append(('show','=',True))
#                 domain.append('&')
#                 domain.append(('shipping_warehouse_id','=',user.default_warehouse_id.id))
#                 domain.append(('shipping_warehouse_route_released','=',True))
        return domain

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        context = self.env.context or {}
        ctx = context.copy()
        if context.get('search_for_template_view', False) and order is None:
            order = 'order_number_by_route_int'
#         if context.get('just_not_assigned', False):
#             args.append(('has_out_route','=',False))
        args += self.get_user_domain(args)
        return super(SaleOrder, self.with_context(ctx))._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(SaleOrder, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )
        return res
#     
#     def check_all_internal_routes(self, cr, uid, ids, context=None):
#         for id in ids:
#             all = True
#             sale = self.browse(cr, uid, id, context=context)
#             has_out_route = False
# #             has_route = False
# #             for route in sale.related_route_ids:
#             if sale.route_id:
# #                 has_route = True
#                 if sale.route_id.type == 'internal' and sale.route_id.state == 'draft':
#                      all = False
#                      break
#                 elif sale.route_id.type == 'out':
#                     has_out_route = True
#             self.write(cr, SUPERUSER_ID, [id], {
# #                 'all_internal_routes_are_done': all,
#                 'has_out_route': has_out_route,
# #                 'has_route': has_route
#             }, context=context)
#         return True
    
#     def remove_route_drom_sale_order(self, cr, uid, id, route_id, context=None):
#         #nebenaudojama
#         seq_obj = self.env('sale.order.route_sequence')
#         route_obj = self.env('stock.route')
#         seq_ids = seq_obj.search(cr, uid, [
#             ('sale_order_id','=',id),
#             ('route_id','=',route_id)
#         ], context=context)
#         if seq_ids:
#             last_id = seq_obj.get_last_route_id(cr, uid, id, context=context)
#             first_id = seq_obj.get_first_route_id(cr, uid, id, context=context)
#             if route_id not in [last_id, first_id]:
#                 route = route_obj.browse(cr, uid, route_id, context=context)
#                 sale = self.browse(cr, uid, id, context=context)
#                 raise osv.except_osv(
#                     _('Error'),
#                     _('You can\'t remove route(%s, ID: %s) from sale(%s, ID: %s)') % (
#                         route.receiver, str(route_id), sale.name, str(sale.id)
#                     )
#                 )
#         return True
    
#     def put_routes_in_order(self, cr, uid, id, context=None):
#         #nebenaudojama
#         if context is None:
#             context = {}
#         seq_obj = self.env('sale.order.route_sequence')
#         sale = self.browse(cr, uid, id, context=context)
#         all_related_routes = sale.related_route_ids
#         first = False
#         last = False
#         routes_in_order = []
#         if all_related_routes:
#             current_route = all_related_routes[0]
#             for route in all_related_routes:
#                 if route.type == 'out':
#                     current_route = route
# 
#             first = current_route
#             last = current_route
#             routes_in_order.append(current_route)
#             route_count = len(all_related_routes)
#             routes_checked = 0
#             added = False
#             while routes_checked < route_count or added:
#                 routes_checked = 0
#                 added = False
#                 for route in all_related_routes:
#                     routes_checked += 1
#                     if route not in routes_in_order:
#                         if last.type == 'out':
#                             if first.warehouse_id.id == route.destination_warehouse_id.id:
#                                 first = route
#                                 routes_in_order.insert(0, route)
#                                 added = True
#                                 break
#                         else:
#                             if first.warehouse_id.id == route.destination_warehouse_id.id:
#                                 first = route
#                                 routes_in_order.insert(0, route)
#                                 added = True
#                                 break
#                             elif last.destination_warehouse_id.id == route.warehouse_id.id:
#                                 last = route
#                                 routes_in_order.append(route)
#                                 added = True
#                                 break
#             if len(all_related_routes) != len(routes_in_order):
#                 if context.get('removeall_if_bad', False):
#                     self.write(cr, uid, [sale.id], {
#                         'related_route_ids': [(6, 0, [])]
#                     }, context=context)
#                 raise osv.except_osv(
#                     _('Error'),
#                     _('Order\'s (%s, ID: %s) related routes (\n%s\n) can\'t be put in order, when new ones (\n%s\n) are added') %(
#                         sale.name, str(sale.id), '\n'.join([(route.receiver or route.route_name or 'ID: ' + str(route.id)) + ': ' + route.warehouse_id.name + ' --> ' + (route.destination_warehouse_id and route.destination_warehouse_id.name or 'Clients') for route in routes_in_order]),
#                         '\n'.join([(route.receiver or route.route_name or 'ID: ' + str(route.id)) + ': ' + route.warehouse_id.name + ' --> ' + (route.destination_warehouse_id and route.destination_warehouse_id.name or 'Clients') for route in all_related_routes if route not in routes_in_order]),
#                     )
#                 )
#             
#             for route in routes_in_order:
#                 if route.state == 'draft':
#                     for route_desc in list(reversed(routes_in_order)):
#                         if route_desc.state != 'draft':
#                             if routes_in_order.index(route) < routes_in_order.index(route_desc):
#                                 raise osv.except_osv(
#                                     _('Error'),
#                                     _('After this operation order\'s (%s, ID: %s) related routes (\n%s) will have released route not in order') %(
#                                         sale.name, str(sale.id), '\n'.join([(route.receiver or route.route_name or 'ID: ' + str(route.id)) + ': ' + route.warehouse_id.name + ' --> ' + (route.destination_warehouse_id and route.destination_warehouse_id.name or 'Clients') + ' ' + ROUTE_STATES[route.state] for route in routes_in_order]),
#                                     )
#                                 )
#             seq_ids = seq_obj.search(cr, uid, [
#                 ('sale_order_id','=',id),
#             ], context=context)
#             if seq_ids:
#                 seq_obj.unlink(cr, uid, seq_ids, context=context)
#             seq = 1
#             for route in routes_in_order:
#                 seq_obj.create(cr, uid, {
#                     'sale_order_id': id,
#                     'route_id': route.id,
#                     'sequence': seq
#                 }, context=context)
#                 seq += 1
#         return True
    
#     def check_routes_states(self, cr, uid, ids, context=None):
#         # nebenaudojama
#         for id in ids:
#             sale = self.browse(cr, uid, id, context=context)
#             routes_in_order = [seq.route_id for seq in sale.route_sequence_ids]
#             for route in routes_in_order:
#                 if route.state == 'draft':
#                     for route_desc in list(reversed(routes_in_order)):
#                         if route_desc.state != 'draft':
#                             if routes_in_order.index(route) < routes_in_order.index(route_desc):
#                                 raise osv.except_osv(
#                                     _('Error'),
#                                     _('After this operation order\'s (%s, ID: %s) related routes (\n%s\n) will have released route not in order') %(
#                                         sale.name, str(sale.id), '\n'.join([(route.receiver or route.name or '') + ': ' + route.warehouse_id.name + ' --> ' + (route.destination_warehouse_id and route.destination_warehouse_id.name or 'Clients') + ' (' + ROUTE_STATES[route.state] + ')' for route in routes_in_order]),
#                                     )
#                                 )
#         return True
    
#     def add_route_to_sale_order(self, cr, uid, id, route_id, context=None):
#         route_obj = self.env('stock.route')
#         seq_obj = self.env('sale.order.route_sequence')
#         sale = self.browse(cr, uid, id, context=context)
#         route_to_add = route_obj.browse(cr, uid, route_id, context=context)
#         if not sale.route_sequence_ids:
#             seq_obj.create(cr, uid, {
#                 'sale_order_id': id,
#                 'route_id': route_id,
#                 'sequence': 1
#             }, context=context)
#         else:
#             last_id = seq_obj.get_last_route_id(cr, uid, id, context=context)
#             last = route_obj.browse(cr, uid, last_id, context=context)
#             first_id = seq_obj.get_first_route_id(cr, uid, id, context=context)
#             first = route_obj.browse(cr, uid, first_id, context=context)
#             first_sequence = seq_obj.get_sequence(cr, uid, first_id, id, context=context) - 1
#             last_sequence = seq_obj.get_sequence(cr, uid, last_id, id, context=context) + 1
#             if first.type == 'out':
#                 if route_to_add.type == 'out':
#                     raise osv.except_osv(
#                         _('Error'),
#                         _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because order already has %s type route assigned to it') % (
#                             route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id), _('Distributive (DST)')
#                         )
#                     )
#                 if first.state != 'draft':
#                     raise osv.except_osv(
#                         _('Error'),
#                         _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because first route of that order already released or finished') % (
#                             route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                         )
#                     )
#                 if first.warehouse_id.id != route_to_add.destination_warehouse_id.id:
#                     raise osv.except_osv(
#                         _('Error'),
#                         _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because routes\' destination and source warehouses doesn\'t match') % (
#                             route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                         )
#                     )
#                 seq_obj.create(cr, uid, {
#                     'sale_order_id': id,
#                     'route_id': route_id,
#                     'sequence': first_sequence
#                 }, context=context)
#                 
#                 
#             elif first.type == 'internal':
#                 if last.type == 'out':
#                     if route_to_add.type == 'out':
#                         raise osv.except_osv(
#                             _('Error'),
#                             _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because order already has %s type route assigned to it') % (
#                                 route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id), _('Distributive (DST)')
#                             )
#                         )
#                     if first.state != 'draft':
#                         raise osv.except_osv(
#                             _('Error'),
#                             _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because first route of that order already released or finished') % (
#                                 route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                             )
#                         )
#                     if first.warehouse_id.id != route_to_add.destination_warehouse_id.id:
#                         raise osv.except_osv(
#                             _('Error'),
#                             _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because routes\' destination and source warehouses doesn\'t match') % (
#                                 route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                             )
#                         )
#                     seq_obj.create(cr, uid, {
#                         'sale_order_id': id,
#                         'route_id': route_id,
#                         'sequence': first_sequence
#                     }, context=context)
#                 elif last.type == 'internal':
#                     if route_to_add.type == 'out':
#                         if last.destination_warehouse_id.id != route_to_add.warehouse_id.id:
#                             raise osv.except_osv(
#                                 _('Error'),
#                                 _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because routes\' destination and source warehouses doesn\'t match') % (
#                                     route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                                 )
#                             )
#                         seq_obj.create(cr, uid, {
#                             'sale_order_id': id,
#                             'route_id': route_id,
#                             'sequence': last_sequence
#                         }, context=context)
#                     elif last.destination_warehouse_id.id == route_to_add.warehouse_id.id:
#                         seq_obj.create(cr, uid, {
#                             'sale_order_id': id,
#                             'route_id': route_id,
#                             'sequence': last_sequence
#                         }, context=context)
#                     elif first.warehouse_id.id == route_to_add.destination_warehouse_id.id:
#                         if first.state != 'draft':
#                             raise osv.except_osv(
#                                 _('Error'),
#                                 _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because first route of that order already released or finished') % (
#                                     route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                                 )
#                             )
#                         seq_obj.create(cr, uid, {
#                             'sale_order_id': id,
#                             'route_id': route_id,
#                             'sequence': last_sequence
#                         }, context=context)
#                     else:
#                         raise osv.except_osv(
#                             _('Error'),
#                             _('You can\'t add route(%s, ID:%s) to order(%s, ID: %s), because routes\' destination and source warehouses doesn\'t match') % (
#                                 route_to_add.receiver, str(route_to_add.id), sale.name, str(sale.id)
#                             )
#                         )
#         return True
        
#     def remove_old_routes(self, cr, uid, id, route_not_to_remove_id, context=None):
#         #nebenaudojama
#         sale = self.browse(cr, uid, id, context=context)
#         for route in sale.related_route_ids:
#             if route.id == route_not_to_remove_id:
#                 continue
#             if route.type == 'out':
#                 self.write(cr, uid, [sale.id], {
#                     'related_route_ids': [(3, route.id)]
#                 }, context=context)
#         return True
    
#     def check_related_routes(self, cr, uid, ids, context=None):
#         #nebenaudojama
#         if context is None:
#             context = {}
#         for id in ids:
#             type_out = False
# #             type_int = False
#             sale = self.browse(cr, uid, id, context=context)
#             for route in sale.related_route_ids:
#                 if route.type == 'out':
#                     if type_out:
#                         if context.get('removeall_if_bad', False):
#                             self.write(cr, uid, [sale.id], {
#                                 'related_route_ids': [(6, 0, [])]
#                             }, context=context)
#                         raise osv.except_osv(
#                             _('Error'),
#                             _('Sale (%s, ID: %s) has more than one \'out\' type routes') %(
#                                 sale.name, str(sale.id)
#                             )
#                         )
#                     else:
#                         type_out = True
# #                 elif route.type == 'internal':
# #                     if type_int:
# #                         raise osv.except_osv(
# #                             _('Error'),
# #                             _('Sale (%s, ID: %s) has more than one \'internal\' type routes') %(
# #                                 sale.name, str(sale.id)
# #                             )
# #                         )
# #                     else:
# #                         type_int = True
# #                 ordered_route_ids = self.get_routes_by_sale_in_order(cr, uid, id, context=context)
#         return True
    
#     def check_warehouses(self, cr, uid, ids, context=None):
#         route_obj = self.env('stock.route')
#         for id in ids:
#             sale = self.browse(cr, uid, id, context=context)
#             for route in sale.related_route_ids:
#                 if route.type == 'out' and route.warehouse_id and sale.shipping_warehouse_id \
#                     and route.warehouse_id.id != sale.shipping_warehouse_id.id \
#                 :
#                     UserError(_('Warehouse of sale order (%s, ID: %s) doesn\'t match warehouse of route (%s, ID: %s)') % (
#                         sale.name, str(sale.id), route_obj.name_get(cr, uid, [route.id], context=context) \
#                             and route_obj.name_get(cr, uid, [route.id], context=context)[0] \
#                             and route_obj.name_get(cr, uid, [route.id], context=context)[0][1] \
#                             or route.name, str(route.id)
#                     ))
#         return True
    
    @api.multi
    def open_invoices(self):
        invoices = []
        for sale in self:
            invoices += sale.get_invoices()

        form_view = self.env['ir.model.data'].xmlid_to_object('config_sanitex_delivery.view_account_invoice_bls_documents_form')[0]
        tree_view = self.env['ir.model.data'].xmlid_to_object('config_sanitex_delivery.view_account_invoice_bls_documents_tree')[0]
        return {
            'name': _('Invoices of sale: %s') % ', '.join([sale.name for sale in self]),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id,'tree'),(form_view.id,'form')],
            'domain': [
                ('id','in',[invoice.id for invoice in invoices])
            ]
        }
    
#     def check_route_order(self, cr, uid, ids, context=None):
#         nebenaudojama            
#         if context is None:
#             context = {}
#         seq_obj = self.env('sale.order.route_sequence')
#         if context.get('do_not_check_route_order', False):
#             return True
#         for id in ids:
#             added_ids = seq_obj.get_added_routes(cr, uid, id, context=context)
#             removed_ids = seq_obj.get_removed_routes(cr, uid, id, context=context)
#             if added_ids and removed_ids or len(added_ids) > 1 or len(removed_ids) > 1:
#                 self.put_routes_in_order(cr, uid, id, context=context)
#             elif added_ids:
#                 self.add_route_to_sale_order(cr, uid, id, added_ids[0], context=context)
#             elif removed_ids:
#                 self.remove_route_drom_sale_order(cr, uid, id, removed_ids[0], context=context)
# #             self.check_warehouses(cr, uid, [ids], context=context)
#         return True

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        ctx = context.copy()
        ctx['delete_sale'] = True
        ctx['force_sale_unlink'] = True
        usr_obj = self.env['res.users']
        if usr_obj.browse(self.env.uid).is_user_in_group_xml(ROUTE_OPERATOR_GROUP_XML_ID) and self.env.uid != SUPERUSER_ID:
            raise UserError(_('You can\'t delete orders because you belong to group %s') % _('Route / Operator'))
        
        if not context.get('allow_to_delete_sale_with_route', False):
            if context.get('remove_task_from_route', False):
                self.write({'route_id': False})
                return True
            else:
                for sale in self:
                    if sale.route_id:
                        raise UserError(_('Sale order (%s, ID: %s) can\'t be deleted because it is assigned to a route (%s, ID: %s)') %(
                                sale.name, str(sale.id), sale.route_id.name, str(sale.route_id.id)
                            )
                        )
        # self.invalidate_cache(['state'], self.mapped('id'))
        return super(SaleOrder, self.with_context(ctx)).unlink()

    @api.multi
    def check_for_missing_links(self):
        context = self.env.context or {}
        ctx = context.copy()
        ctx['links_checked'] = True
        link_obj = self.env['stock.route.integration.intermediate.missing_links']
        if not context.get('links_checked', False):
            for sale in self:
                sale_read = sale.read(['external_sale_order_id'])[0]
                if sale_read.get('external_sale_order_id', False):
                    link_obj.with_context(ctx).check_for_missing_links(self._name, sale_read['external_sale_order_id'])
        return True
    
            
    @api.model
    def update_vals(self, vals):
        if 'total_weight' in vals.keys():
            vals['rounded_total_weight'] = int(round(vals['total_weight']))
        if 'partner_id' in vals.keys():
            if vals['partner_id']:
                vals['partner_name'] = self.env['res.partner'].browse(vals['partner_id']).name or ''
            else:
                vals['partner_name'] = ''
        if 'partner_shipping_id' in vals.keys():
            if vals['partner_shipping_id']:
                vals['posid'] = self.env['res.partner'].browse(vals['partner_shipping_id']).possid_code or ''
            else:
                vals['posid'] = ''
        if 'route_number_id' in vals.keys():
            if vals['route_number_id']:
                route_number = self.env['stock.route.number'].browse(vals['route_number_id'])
                route_number.create_route_template()
                vals['route_number'] = route_number.name
                template = self.env['stock.route.template'].search([('route_no_id','=',route_number.id)], limit=1)
                if not template:
                    route_number.create_route_template()
                    template = self.env['stock.route.template'].search([('route_no_id','=',route_number.id)], limit=1)
                vals['route_template_id'] = template.id
            else:
                vals['route_number'] = ''
                vals['route_template_id'] = False
        elif 'route_template_id' in vals.keys():
            if not vals['route_template_id']:
                vals['route_number'] = ''
                vals['route_template_id'] = False
                vals['order_number_by_route'] = ''
                vals['shipping_warehouse_id'] = False
                vals['route_number_id'] = False

        if vals.get('warehouse_id') and 'task_at' not in vals.keys():
            vals['task_at'] = self.env['stock.warehouse'].browse(vals['warehouse_id']).code
            vals['can_be_picked_up'] = True
        if 'route_id' in vals.keys():
            if vals.get('route_id', False):
                vals['route_id_str'] = str(vals['route_id'])
            else:
                vals['route_id_str'] = ''
        if 'order_number_by_route' in vals.keys():
            try:
                vals['order_number_by_route_int'] = int(vals['order_number_by_route'])
            except:
                pass

    @api.multi
    def update_next_warehouse(self, wh_id):
        if wh_id:
            for task in self:
                if not task.warehouse_next_to_id:
                    task.write({'warehouse_next_to_id': wh_id})

    @api.multi
    def change_route(self, new_route=None):
        # Kai užduotis būna įdėta į maršrutą, kuriame neturėjo būti, tada
        # reikia nuo užduoties nutrinti tam tikras reikšmes

        task_vals = {
            'route_number_id': False
        }

        if new_route and new_route.location_id:
            task_vals['driver_id'] = new_route.location_id.id
            task_vals['license_plate'] = new_route.location_id.license_plate
            task_vals['driver_name'] = new_route.location_id.name
        task_vals['added_manually'] = True
        task_vals['order_number_by_route'] = 'MANUAL'
        task_vals['order_number_by_route_int'] = 999
        task_vals['delivering_goods_by_routing_program'] = ''
        self.write(task_vals)

    @api.multi
    def write(self, vals):
        route_no_env = self.env['stock.route.number']
        route_tmpl_env = self.env['stock.route.template']
        context = self.env.context or {}

        self.update_vals(vals)
        route_numbers = route_no_env.browse()
        templates_to_remove = route_tmpl_env.browse([])
        if 'route_template_id' in vals.keys():
            new_template = route_tmpl_env.browse(vals['route_template_id'] or [])
            templates_to_remove = self.mapped('route_template_id') - new_template


        if 'partner_id' in vals or 'partner_shipping_id' in vals:
            for sale in self:
                if sale.route_id:
                    for packing in sale.route_id.packing_for_client_ids:
                        if packing.partner_id.id == sale.partner_id.id\
                            or packing.address_id.id == sale.partner_shipping_id.id\
                        :
                            raise UserError(_('You can\'t change client or client shipping address in sale order (%s, ID: %s), because related route(%s, ID: %s) has generated client packings for this order') % (
                                    sale.name, str(sale.id), sale.route_id.name, str(sale.route_id.id)
                                )
                            )
                            
        if context.get('do_not_allow_to_change_route', False) and 'route_id' in vals.keys():
            tasks_in_routes = self.filtered('route_id')
            if tasks_in_routes:
                task_in_routes = tasks_in_routes[0]
                raise UserError(_('Task(%s, ID: %s) already in route(%s, ID: %s)') % (
                    task_in_routes.name, str(task_in_routes.id), task_in_routes.route_id.name,
                    str(task_in_routes.route_id.id)
                ))
            
        old_routes = False
        if 'route_id' in vals.keys():
            old_routes = self.mapped('route_id')

        res = super(SaleOrder, self).write(vals)
        if context.get('check_for_links', False):
            self.check_for_missing_links()

        if 'shipping_warehouse_id' in vals.keys():
            self.update_next_warehouse(vals['shipping_warehouse_id'])
            self.mapped('route_number_id').create_route_template()

        if 'shipping_warehouse_id' in vals.keys() or 'route_id' in vals.keys():
            self.update_shipping_warehouse_route_released()
            routes = self.mapped('route_id')
            routes.update_route_type()
            
        if 'shipping_warehouse_id' in vals.keys() or 'warehouse_id' in vals.keys() \
            or 'route_state_received' in vals.keys() \
        :
            self.mapped('route_id').update_shipping_warehouse_id_filter()
            self.mapped('route_id').update_picking_warehouse_id_filter()

        if 'route_id' in vals.keys():
            self.check_for_missing_links()
            if old_routes:
                routes = old_routes
            else:
                routes = self.mapped('route_id')
            routes.remove_not_needed_packings()
            routes.update_counts()
            routes.update_weight()
            routes.update_shipping_warehouse_id_filter()
            routes.update_picking_warehouse_id_filter()
            routes.update_route_type()
            routes.update_containers()
            routes.update_related_documents()
            self.update_related_packages()
        if vals.get('route_state_received', False) or vals.get('not_received', False):
            self.mapped('route_id').update_received_warehouse_ids_text()
        if vals.get('sequence', -1) == 0:
            if old_routes:
                routes = old_routes
            else:
                routes = self.mapped('route_id')
            routes.close_route_if_needed()

        if 'received_by' in vals.keys():
            self.update_task_location(vals['received_by'])

        # if 'task_at' in vals.keys():
        #     if vals['task_at']:
        #         for task in self:
        #             if vals['task_at'] == task.warehouse_id.code:
        #                 task.write({'can_be_picked_up': True})
        #             else:
        #                 task.write({'can_be_picked_up': False})
        #     else:
        #         vals['can_be_picked_up'] = False

        if vals.get('route_number_id', False):
            self.mapped('route_number_id').create_route_template()
            self.filtered(lambda task_rec: not task_rec.original_route_number_id).write({
                'original_route_number_id': vals['route_number_id']
            })
            self.update_document_template_info()


        if 'shipping_warehouse_id' in vals.keys():
            route_numbers += self.mapped('route_number_id')
            route_numbers.create_route_template()
            if not vals['shipping_warehouse_id']:
                for task in self:
                    task.write({'shipping_warehouse_id': task.warehouse_id.id})
        if vals.get('has_related_document', False):
            self.mapped('order_line').update_weight()
        templates_to_remove.remove_if_empty()
        return res

    @api.multi
    def actions_after_creating_task(self):
        return

    @api.multi
    def remove_from_route(self):
        self.write({'route_id_str': ''})

    @api.model
    def show_print_button(self, ids, context):
        return False

    @api.multi
    def compute_route_number(self):
        # Kolkas nenaudojama
        # Užduotyje yra laukas route_no_client_no, kuris turi rodyti maršruto numerį ir kliento numerį maršrute
        # "maršruto numeris (kliento numeris maršrute)". Ši funkcija užpildo tą lauką

        for task in self:
            value = ''
            if task.route_number:
                value = task.route_number
                if task.order_number_by_route:
                    value += ' (%s)' % task.order_number_by_route
            if task.route_no_client_no != value:
                task.write({'route_no_client_no': value})

    @api.multi
    def update_related_packages(self):
        # Atnaujina siuntas pagal susijusias užduotis. pavyzdžiui: 
        # Jei užduotis priskirta prie maršruto tai prie siuntos turi užsidėti tas maršrutas.
        
        for task in self.filtered(lambda task_record: task_record.delivery_type == 'collection'):
            if task.route_id:
                task.related_package_id.write({'collection_route_id': task.route_id.id})
            else:
                task.related_package_id.write({'collection_route_id': False})

    @api.model
    def check_sale_vals(self, sale_vals):
        if not sale_vals.get('partner_id', False) and not sale_vals.get('placeholder_for_route_template', False):
            raise UserError(_('Sale has to have \'%s\' filled') % _('Client'))
        return True

    @api.multi
    def update_document_template_info(self):
        # Dokumentas turi turėti maršruto ruošinio informaciją. Dokumentas
        # susijęs su maršruto ruošiniu per susijusią transportavimo užduotį.
        if self:
            template_info_sql = '''
                UPDATE
                    account_invoice ai
                SET 
                    route_template_number = so.route_number || ' (' || so.order_number_by_route || ')',
                    driver_name = srt.driver
                FROM
                    sale_order so,
                    sale_order_line sol,
                    account_invoice_line ail,
                    invoice_line_so_line_rel ilslr,
                    stock_route_template srt
                WHERE
                    so.id in %s
                    AND sol.order_id = so.id
                    AND sol.id = ilslr.order_line_id
                    AND ilslr.invoice_line_id = ail.id
                    AND ai.id = ail.invoice_id
                    AND so.route_number is not null
                    AND so.route_number != ''
                    AND srt.id = so.route_template_id
            '''
            template_info_where = (self._ids,)
            self.env.cr.execute(template_info_sql, template_info_where)


    @api.multi
    def recount_lines_numbers(self):
        # Transportavimo užskyme eilutės turi būti numeruojamos: 1, 2, 3 ...
        # Ši funkcija perskaičiuoja eilučių numeravimą jeigu viena būna pašalinta arba yra pridedama nauja

        context = self.env.context or {}
        if context.get('skip_task_line_recount', False):
            return False

        line_env = self.env['sale.order.line']
        for task in self:
            self.env.cr.execute('''
                SELECT
                    id,
                    line_no
                FROM
                    sale_order_line
                WHERE
                    order_id = %s
                ORDER BY
                    sequence, line_no, id
            ''' % str(task.id))
            lines = self.env.cr.fetchall()
            new_lines = []
            for line in lines:
                new_lines.append((line[0], lines.index(line)+1))
            lines_to_change = set(new_lines).difference(set(lines))
            for line_to_change in list(lines_to_change):
                line_env.browse(line_to_change[0]).write({'line_no': line_to_change[1]})

    @api.model
    def cron_fix_route_template_for_task(self):
        _logger.info('Fixing Templates in Tasks')
        template_env = self.env['stock.route.template']
        bad_tasks = self.search([
            ('route_template_id','=',False),
            ('route_id','=',False),
            ('route_number_id','!=',False),
            ('create_date','>','2018-01-15 00:00:00')
        ])
        _logger.info('Found %s bad tasks' % str(len(bad_tasks)))
        for bad_task in bad_tasks:
            template = template_env.search([('route_no_id','=',bad_task.route_number_id.id)], limit=1)
            if template:
                bad_task.write({'route_template_id': template.id})
        _logger.info('Fixing bad tasks done')

    @api.model
    def create_sale(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self.env.context or {}
        commit = not context.get('no_commit', False)

        ctx = context.copy()
        ctx['check_for_links'] = True
        ctx['recompute'] = False

        sale = self.search([
            ('external_sale_order_id','=',vals['external_sale_order_id']),
            ('replanned','=',False)
        ], order='id', limit=1)
        if sale:
            import_timestamp = sale.read(['import_timestamp'])[0]['import_timestamp']
            if import_timestamp > vals['import_timestamp']:
                return sale
            sale_vals = {}
            sale_vals.update(vals)
            if 'name' in sale_vals:
                del sale_vals['name']
            if 'date_order' in sale_vals:
                del sale_vals['date_order']
            interm_obj.remove_same_values(sale, sale_vals)
            if sale_vals:
                sale_vals['intermediate_id'] = context.get('intermediate_id', False)
                sale.with_context(ctx).write(sale_vals)
                if 'updated_sale_ids' in context:
                    context['updated_sale_ids'].append((vals['external_sale_order_id'], sale.id))
            context['sale_message'].append(_('Sale was successfully updated'))
        else:
            sale_vals = self.default_get(self._fields)
            sale_vals.update(vals)
            sale_vals['user_id'] = 1
            sale_vals['pricelist_id'] = self.env['product.pricelist'].search([], limit=1).id
            sale_vals['intermediate_id'] = context.get('intermediate_id', False)
            sale_vals['state'] = 'blank'
            sale_vals['show'] = True
            sale_vals['replanned'] = False
            sale_vals['processed_with_despatch'] = False
            sale_vals['sequence'] = 1
            sale_vals['order_package_type'] = sale_vals.get('order_package_type', 'order')
            sale_vals['previous_task_received'] = True
            self.check_sale_vals(sale_vals)
            sale = self.with_context(recompute=False).create(sale_vals)
            if 'created_sale_ids' in context:
                context['created_sale_ids'].append((sale_vals['external_sale_order_id'], sale.id))
            context['sale_message'].append(_('Sale was successfully created'))
        if commit:
            self.env.cr.commit()
        return sale

    @api.multi
    def remove_placeholder_duplicate(self):
        # Kai sukuriamas užsakymas, patikrinama ar jam nebuvo sukurtas šabloninio užsakymas.
        # Jei buvo, tada tas šabloninis būna ištrintas.
        if self:
            search_sql = '''
                SELECT
                    id
                FROM
                    sale_order
                WHERE
                    external_sale_order_id in %s
                    AND placeholder_for_route_template = True
                    AND id not in %s
                    AND route_id is null
            '''
            search_where = (tuple(self.mapped('name')),tuple(self.ids))
            self.env.cr.execute(search_sql, search_where)
            ids = self.env.cr.fetchall()
            route_number_ids = []
            if ids:
                tasks_to_delete = self.browse([id[0] for id in ids])
                for task_to_delete in tasks_to_delete:
                    _logger.info('Deleted placeholder tasks: ID - %s, Name - %s, template_id - %s' % (
                        str(task_to_delete.id), task_to_delete.name, str(task_to_delete.route_template_id)
                    ))
                    if task_to_delete.route_number_id:
                        route_number_ids.append(task_to_delete.route_number_id.id)
                tasks_to_delete.unlink()
            return route_number_ids

    @api.model
    def create(self, vals):
        link_obj = self.env['stock.route.integration.intermediate.missing_links']
        link_env2 = self.env['stock.route.integration.missing_links.new']
        route_obj = self.env['stock.route']
        context = self.env.context or {}

        if 'sequence' not in vals.keys():
            vals['sequence'] = 1
        self.update_vals(vals)
        if 'warehouse_id' in vals.keys() and 'shipping_warehouse_id' not in vals.keys():
            vals['shipping_warehouse_id'] = vals['warehouse_id']
        sale = super(SaleOrder, self).create(vals)
        if vals.get('external_sale_order_id', False) and not context.get('skip_missing_links', False):
            link_obj.check_for_missing_links(self._name, vals['external_sale_order_id'])
            link_env2.check_for_missing_links(vals['external_sale_order_id'], 'task_creation_from_package')
            link_env2.check_for_missing_links(vals['external_sale_order_id'], 'task_update_from_route')
        if vals.get('route_id', False):
            route = route_obj.browse(vals['route_id'])
            route.update_route_type()
            route.update_containers()
        sale.update_weight()
        if 'received_by' in vals.keys():
            sale.update_task_location(vals['received_by'])
        if vals.get('route_number_id', False) and not context.get('skip_template_calculation', False):
            sale.route_number_id.create_route_template()
        route_number_ids = sale.remove_placeholder_duplicate()
        if route_number_ids:
            sale.write({'route_number_id': route_number_ids[0]})
        return sale

    @api.multi
    def get_picking_warehouse_id_filter(self):
        return self.get_field_id_filter('warehouse_id')

    @api.multi
    def get_shipping_warehouse_id_filter(self):
        return self.get_field_id_filter('shipping_warehouse_id')

    @api.multi
    def get_field_id_filter(self, field_name):
        obj_filter = ''
        sales_objects = self.mapped(field_name)
        if sales_objects:
            object_ids = list(set(sales_objects.mapped('id')))
            obj_filter = 'id'.join([str(obj_id) for obj_id in object_ids])
            obj_filter = 'id' + obj_filter + 'id'
        return obj_filter

    @api.model
    def CreateOrder(self, list_of_sale_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_sale_values(list_of_sale_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'CreateOrder',
                'received_information': str(json.dumps(list_of_sale_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'CreateOrder',
            'received_values': str(json.dumps(list_of_sale_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def check_imported_sale_values(self, list_of_sale_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        required_values = [
            'external_customer_id',
            'document_name',
            'external_buyer_address_id',
            'external_sale_order_id', 
#             'warehouse_id', 'delivery_type', 
            'order_type', 
            'owner_id',
            
        ]
        inter_obj.check_import_values(list_of_sale_vals, required_values, result)
        if result:
            return result
        required_line_values = [
            'external_product_id', 'product_name', 'product_code',
            'external_sale_order_line_id', 'sale_order_line_qty',
            'sale_order_line_uom'
        ]
        selection_values = {
            'order_type': ['order', 'instruction'],
            'delivery_type': ['delivery', 'collection'],
            'document_type': ['invoice', 'picking']
        }
        i = 0
        for sale_dict in list_of_sale_vals:
            i = i + 1
            index = str(i)
#             if sale_dict.get('cash', False) and sale_dict.get('cash_amount', 0.0) <= 0.0:
#                 msg = _('\'Cash\' is marked in order.') + ' ' +  _('You have to fill in value: %s') % 'cash_amount'
#                 if index in result.keys():
#                     result[index].append(msg)
#                 else:
#                     result[index] = [msg]
            
            if sale_dict.get('order_type', '') == 'instruction' and not sale_dict.get('comment', ''):
                msg = _('\'Order Type\' is \'instruction\'.') + ' ' +  _('You have to fill in value: %s') % 'comment'
                if index in result.keys():
                    result[index] += '\n' + msg
                else:
                    result[index] = [msg]
                
            if sale_dict.get('order_type', '') == 'order' and not sale_dict.get('order_lines', []):
                msg = _('\'Order Type\' is \'order\'.') + ' ' +  _('You have to fill in value: %s') % 'order_lines' + '. ' + _('At least one line')
                if index in result.keys():
                    result[index].append(msg)
                else:
                    result[index] = [msg]
            this_required_line_values = required_line_values[:]
            if sale_dict.get('document_type', '') == 'invoice':
                this_required_line_values.append('sale_order_line_amount_wth_tax')
            line_results = {}
            inter_obj.check_import_values(
                sale_dict.get('order_lines', []),
                this_required_line_values, line_results, prefix=_('Order Line')
            )
            if line_results:
                if index in result.keys():
                    result[index].append(line_results)
                else:
                    result[index] = [line_results]
            for selection_key in selection_values.keys():
                if selection_key in sale_dict.keys():
                    selection_result = inter_obj.check_selection_values(
                        selection_key, sale_dict[selection_key],
                        selection_values[selection_key]
                    )
                    if selection_result:
                        if index in result.keys():
                            result[index].append(selection_result)
                        else:
                            result[index] = [selection_result]
        return result
    
    @api.multi
    def get_type_for_route(self):
        # pagal pasirinktus pardavimus nustatoma kokio tipo
        # turėtų būti maršrutas
        usr_env = self.env['res.users']
        user = usr_env.browse(self.env.uid)

        if user.default_region_id and not user.default_warehouse_id:
            return self.get_type_for_route_by_region()
        else:
            return self.get_type_for_route_by_warehouse()

    @api.multi
    def get_type_for_route_by_warehouse(self):
        route_type_set = set()
        for task in self:
            if task.warehouse_id == task.shipping_warehouse_id:
                route_type_set.add('out')
            else:
                route_type_set.add('internal')
            if len(route_type_set) > 1:
                break
        if not len(route_type_set):
            return 'out'
        elif len(route_type_set) > 1:
            return 'mixed'
        else:
            return route_type_set.pop()

    @api.multi
    def get_type_for_route_by_region(self):
        route_type_set = set()
        for task in self:
            if task.warehouse_id.region_id == task.shipping_warehouse_id.region_id:
                route_type_set.add('out')
            else:
                route_type_set.add('internal')
            if len(route_type_set) > 1:
                break
        if len(route_type_set) > 1:
            return 'mixed'
        else:
            return route_type_set.pop()

        # route_type = 'mixed'
        # dest_warehouses = self.mapped('shipping_warehouse_id')
        # print('dest_warehouses', dest_warehouses)
        #
        # if len(dest_warehouses) > 1:
        #     route_type = 'mixed'
        # if len(dest_warehouses) == 1:
        #     if self[0].warehouse_id.id == dest_warehouses[0].id:
        #         route_type = 'out'
        #     else:
        #         route_type = 'internal'
        # return route_type

    @api.multi
    def change_sales_for_createing_route_from_region(self):
        usr_env = self.env['res.users']
        user = usr_env.browse(self.env.uid)
        if user.default_region_id:
            region_main_warehouse = user.default_region_id.get_main_location().get_location_warehouse_id()
            for task in self.filtered(lambda task_rec:
                task_rec.warehouse_id != region_main_warehouse
                or task_rec.shipping_warehouse_id != region_main_warehouse
            ):
                changes = task.warehouse_id.code + ' --> ' + region_main_warehouse.code + ' | ' \
                    + task.shipping_warehouse_id.code + ' --> ' + region_main_warehouse.code
                new_vals = {
                    'warehouse_id': region_main_warehouse.id,
                    'shipping_warehouse_id': region_main_warehouse.id,
                    'changes_in_route_formation': changes
                }
                task.write(new_vals)


    @api.multi
    def action_create_route_confirm(self):
        sales_without_documents = self - self.filtered('has_related_document')
        if sales_without_documents:
            if sales_without_documents == self:
                raise UserError(_('None of selected task have a document.'))
            message_to_show =  _('There are %s tasks(%s) without documents. These task will not be included into created route') % (
                str(len(sales_without_documents)), ', '.join(sales_without_documents.mapped('name'))
            )
            context = self.env.context or {}
            ctx = context.copy()
            ctx['active_ids'] = self.filtered('has_related_document').mapped('id')
            ctx['action_model'] = self._name
            ctx['action_function'] = 'create_route'
            ctx['warning'] = message_to_show
            
            form_view = self.env.ref('config_sanitex_delivery.object_action_warning_osv_form', False)[0]
            
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'object.confirm.action.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'nodestroy': True,
                'views': [(form_view.id,'form')],
            }
        else:
            return self.create_route()


    @api.multi
    def create_route(self):
        # pažymėtiems pardavimams sukuriamas maršrutas ir
        # visi pardavimai priskiriami tam maršrutui
        
        route_env = self.env['stock.route']
        usr_env = self.env['res.users']
        
        context = self.env.context
        ctx = context.copy()
        ctx['tracking_disable'] = True
        
        self = self.with_context(ctx)
        
        user = usr_env.browse(self.env.uid)
        if self:
            sales = self.filtered('has_related_document')
            route_type = sales.get_type_for_route()

            route_vals = {}
            route_vals['type'] = route_type
            route_vals['date'] = utc_str_to_local_str()[:10]
            route_vals['region_id'] = False
            route_numbers = [no for no in sales.mapped('route_number') if isinstance(no, str)]
            if route_numbers and route_type == 'out':
                route_vals['receiver'] = ', '.join(list(set(route_numbers)))
            if user.default_warehouse_id:
                wh = user.default_warehouse_id
            else:
                warehouses = sales.mapped('warehouse_id')
                if user.default_region_id:
                    wh = user.default_region_id.get_main_location().get_location_warehouse_id()
                    route_vals['region_id'] = user.default_region_id.id
                else:
                    wh = warehouses[0]
            route_vals['warehouse_id'] = wh.id
            if route_type == 'out' and not user.default_warehouse_id and user.default_region_id:
                sales.change_sales_for_createing_route_from_region()

            route_vals['source_location_id'] = wh.wh_output_stock_loc_id and wh.wh_output_stock_loc_id.id or False
            if route_type == 'internal':
                sh_warehouses = sales.mapped('shipping_warehouse_id')
                if sh_warehouses:
                    route_vals['destination_warehouse_id'] = sh_warehouses[0].id
                    route_vals['receiver'] = sh_warehouses[0].name
                    route_vals['return_location_id'] = sh_warehouses[0].wh_return_stock_loc_id and sh_warehouses[0].wh_return_stock_loc_id.id or False

            else:
                route_vals['return_location_id'] = wh.wh_return_stock_loc_id and wh.wh_return_stock_loc_id.id
            if user.default_region_id and not user.default_warehouse_id:
                route_vals['return_location_id'] = user.default_region_id.get_main_location().id
            if route_type == 'out' and len(sales) == 1 and sales.mapped('driver_id'):
                route_vals['location_id'] = sales.mapped('driver_id')[0].id
            if len(sales.mapped('driver_id')) == 1 and route_type == 'out':
                driver = sales.mapped('driver_id')
                route_vals['location_id'] = driver.id
                route_vals['license_plate'] = driver.license_plate
                route_vals['trailer'] = driver.trailer

            route = route_env.create(route_vals)
            sales.write({'route_id': route.id})
            
            if route.type != 'internal':
                route.generate_product_act_new()
            
            form_view = self.env.ref('config_sanitex_delivery.view_stock_routes_form', False)[0]
            view = self.env.ref('config_sanitex_delivery.view_stock_routes_tree', False)[0]
            domain = [('id','=',route.id)]
            return {
                'name': _('Created Route'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'stock.route',
                'views': [(form_view.id,'form'),(view.id,'tree')],
                'type': 'ir.actions.act_window',
                'res_id': route.id,
                'domain': domain,
                'context': {'search_by_user_sale': False, 'remove_task_from_route': True, 'hide_print_button': True}
            }
        
        return {'type': 'ir.actions.act_window_close'}
    
    
#Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi galimi marsrutu numeriai
    def get_avail_route_numbers(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []
        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
#                 normalized_domain.append(domain_ele[0])
                normalized_domain += domain_ele
            else:
                continue
            
        if action_domain:
            normalized_domain += action_domain

        normalized_domain += self.with_context(context).get_user_domain()
        
        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(route_number) FROM sale_order %s ORDER BY route_number' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        route_numbers = []
        
        for el in res:
            if el[0]:
                route_numbers.append(el[0])
        
        return route_numbers
    
#Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi galimi savininkai
    def get_avail_owners(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []
        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
#                 normalized_domain.append(domain_ele[0])
                normalized_domain += domain_ele
            else:
                continue
            
        if action_domain:
            normalized_domain += action_domain
        
        normalized_domain += self.with_context(context).get_user_domain()
        
        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(owner_id) FROM sale_order %s ORDER BY owner_id' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        owners = []
        
        for owner_id_tuple in res:
            if owner_id_tuple[0]:
                owner_id = owner_id_tuple[0]
                self.env.cr.execute('SELECT owner_code,name FROM product_owner WHERE id = %s' % owner_id)
                owner_code_sql_res = self.env.cr.fetchone()
                
                owner_code, owner_name = owner_code_sql_res
                if owner_name:
                    owner_str = "%s - %s" % (owner_code, owner_name)
                else:
                    owner_str = owner_code
                
                if (owner_code, owner_str) not in owners:
                    owners.append((owner_code, owner_str))
        
        owners = sorted(owners, key=lambda tup: tup[1])
        return owners
    
    #Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinamos skirtingos galimos pristatymo datos
    def get_avail_dates(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []
        
        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
#                 normalized_domain.append(domain_ele[0])
                normalized_domain += domain_ele
            else:
                continue
            
        if action_domain:
            normalized_domain += action_domain

        normalized_domain += self.with_context(context).get_user_domain()

        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(shipping_date) FROM sale_order %s ORDER BY shipping_date DESC' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        dates = [tpl[0] for tpl in res]
        return dates
    
    #Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi isvezimo sandeliai
    def get_avail_shipping_warehouses(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []       

        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
                normalized_domain += domain_ele
            else:
                continue
            
        if action_domain:
            normalized_domain += action_domain
            
        normalized_domain += self.with_context(context).get_user_domain()

        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(shipping_warehouse_id) FROM sale_order %s' % where_str
        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        
        shipping_warehouses = []
        
        for shipping_warehouse_id_tuple in res:
            if shipping_warehouse_id_tuple[0]:
                shipping_warehouse_id = shipping_warehouse_id_tuple[0]
                self.env.cr.execute('SELECT name FROM stock_warehouse WHERE id = %s' % shipping_warehouse_id)
                shipping_warehouse_sql_res = self.env.cr.fetchone()
#                 
                shipping_warehouses.append((shipping_warehouse_id, shipping_warehouse_sql_res[0]))
        
        shipping_warehouses = sorted(shipping_warehouses, key=lambda tup: tup[1])
        return shipping_warehouses
    
    @api.multi
    def set_being_collected_state(self):
        self.write({'state': 'being_collected'})
        return True
        
    @api.multi
    def set_need_invoice_state(self):
        self.write({'state': 'need_invoice'})
        return True
    
    @api.multi
    def set_invoiced_state(self):
        self.write({'state': 'invoiced'})
        return True
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.model
    def _get_transportation_states(self):
        sale_env = self.env['sale.order']
        return sale_env._get_transportation_states()

    external_sale_order_line_id = fields.Char(
        'External ID', size=64, readonly=True
    )
    uom = fields.Char('UOM', size=64)
    product_code = fields.Char('Product Code', readonly=True, size=128)
    product_uom_qty = fields.Float(
        'Quantity', digits=(16, 2), required=True
    )
    product_uos_qty = fields.Float(
        'UoS Quantity', digits=(16, 2), required=False
    )
    # temp_product_uom_qty = fields.Float(
    #     'Temp Quantity', digits=(16, 2), readonly=True
    # )
    invoice_line_ids = fields.Many2many(
        'account.invoice.line', 'invoice_line_so_line_rel',
        'order_line_id', 'invoice_line_id', 'Invoice Lines'
    )
    min_weight = fields.Float('Min. Weight', digits=dp.get_precision('Stock Weight'))
    max_weight = fields.Float('Max Weight', digits=dp.get_precision('Stock Weight'))
    optional_qty = fields.Integer('Optional Qty')
    valid_to = fields.Datetime('Valid To')
    pack_uom_id = fields.Many2one('product.uom', 'Pack UOM')
    min_valid_from = fields.Date('No worse than')
    min_valid_to = fields.Date('No better than')
    picked_qty = fields.Float('Confirmed Quantity', digits=(16,3))
    picked_qty_filled_in = fields.Boolean('Picked Quantity Filled', readonly=True, default=False)
    picked_qty_str = fields.Char('Confirmed Quantity', readonly=True, size=16, default='')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    documetn_type = fields.Selection([
        ('invoice','Invoice'),
        ('picking','Picking'),
        ('loading_sheet','Loading Sheet')
    ], 'Document Type')
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    serial_id = fields.Many2one('product.stock.serial', 'Searial')
    payment_term = fields.Integer('Payment Term (in Days)')
    order_number = fields.Char('Order Number', size=64)
    min_exp_date = fields.Date('Minimum Expiration Date')
    max_exp_date = fields.Date('Maximum Expiration Date')
    state = fields.Selection(
        _get_transportation_states, related='order_id.state', string='Order Status',
        readonly=True, copy=False, store=True, default='blank'
    )
    total_weight = fields.Float('Total Weight', digits=dp.get_precision('Stock Weight'), readonly=True)
    line_no = fields.Integer('No.', readonly=True)
    product_uom_name = fields.Char('UoM', size=32, readonly=True,
        help='Filled in from integration. Used in reports'
    )
    pallet_qty = fields.Integer('Pallete Quantity', readonly=True)
    has_related_document = fields.Boolean('Has Related Document', readonly=True, default=False)
#     _sql_constraints = [
#         # Jau gali būti kelios eilutės su tokiu pačiu išoriniu ID
#         ('external_sale_order_line_id', 'unique (external_sale_order_line_id)', 'External ID of sale line has to be unique')
#     ]
    
    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('sale_order_line_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX sale_order_line_external_id_index ON sale_order_line (external_sale_order_line_id)')

    
#     def __init__(self, pool, cr):
#         cr.execute("""
#             SELECT 
#                 count(*)
#             FROM 
#                 INFORMATION_SCHEMA.COLUMNS 
#             WHERE 
#                 table_name = 'sale_order_line' 
#                 AND column_name = 'temp_product_uom_qty'
#         """)
#         res = cr.fetchone()
#         if res and res[0] > 0:
#             cr.execute("""
#                 UPDATE 
#                     sale_order_line 
#                 SET 
#                     product_uom_qty = temp_product_uom_qty
#                 WHERE 
#                     product_uom_qty = 0
#                     AND temp_product_uom_qty <> 0
#             """)
#         
#         cr.execute("""
#             SELECT 
#                 column_name
#             FROM 
#                 INFORMATION_SCHEMA.COLUMNS 
#             WHERE 
#                 table_name = 'sale_order_line' 
#                 AND column_name like 'product_uom_qty_moved%'
#             ORDER BY
#                 ordinal_position
#         """)
#         res = cr.fetchall()
#         if res:
#             for column in res:
#                 if column:
#                     try:
#                         cr.execute("""
#                             ALTER TABLE 
#                                 sale_order_line
#                             DROP COLUMN 
#                                 %s
#                         """ %column[0])
#                         cr.commit()
#                     except:
#                         cr.rollback()
#                         pass
#         return super(sale_order_line, self).__init__(pool, cr)
    
    
    @api.multi
    def get_total_pallet_quantity(self):
        # Suskaičiuoja kiek palečių reikia eilutėms
        # Skaičiuoja pagal prie produkto nurodytus parametrus, kiekį dėžėje. dėžių kiekį paletėje
        # ir pagal eilutės kiekį. Atsižvelgia ir į produkto svorio tipą
        
        quantity = 0
        for line in self:
            if line.product_id.product_type == 'unit':
                line_quantity_in_units = line.product_uom_qty
            else:
                line_quantity_in_units = line.product_uom_qty / (line.product_id.average_weight or 1.0)
                
            packages = math.ceil(line_quantity_in_units / float(line.product_id.big_package_size or 1))
            pallets = math.ceil(packages / float(line.product_id.packages_per_pallet or 1))
            quantity += pallets
        return quantity

    @api.multi
    def update_pallet_quantity(self):
        tasks = self.env['sale.order']
        for line in self:
            qty = line.get_total_pallet_quantity()
            if line.pallet_qty != qty:
                line.write({'pallet_qty': qty})
                tasks += line.order_id
        if tasks:
            tasks.update_weight()

    @api.multi
    def update_weight_with_sql(self):
        if self:
            weight_sql = '''
                UPDATE
                    sale_order_line sol
                SET
                    total_weight = (
                        CASE
                            WHEN 
                                pp.product_type in ('fixed', 'variable')
                                AND so.has_related_document = True
                            THEN 
                                sol.picked_qty
                            WHEN 
                                pp.product_type in ('fixed', 'variable')
                                AND (so.has_related_document = False
                                        OR so.has_related_document is null
                                )
                            THEN 
                                sol.product_uom_qty
                            WHEN 
                                pp.product_type in ('unit')
                                AND so.has_related_document = True
                            THEN 
                                sol.picked_qty * pp.weight
                            WHEN 
                                pp.product_type in ('unit')
                                AND (so.has_related_document = False
                                        OR so.has_related_document is null
                                )
                            THEN 
                                sol.product_uom_qty * pp.weight
                        END
                )
                FROM
                    product_product pp,
                    sale_order so
                WHERE
                    so.id = sol.order_id
                    AND pp.id = sol.product_id
                    AND sol.id in %s
                RETURNING 
                    order_id
            '''
            weight_where = (self._ids,)
            self.env.cr.execute(weight_sql, weight_where)
            order_ids = [ord_id[0] for ord_id in self.env.cr.fetchall()]
            self.env['sale.order'].browse(list(set(order_ids))).update_weight_with_sql()
            self.invalidate_cache(fnames=['total_weight'], ids=list(self._ids))


    @api.multi
    def update_weight(self):
        tasks = self.env['sale.order']
        for line in self:
            weight = line.get_total_weight()
            if line.total_weight != weight:
                line.write({'total_weight': weight})
                tasks += line.order_id
        if tasks:
            tasks.update_weight()
    
    @api.multi
    def get_total_weight(self):
        weight = 0.0
        for line in self:
            if line.product_id:
                if line.order_id.has_related_document:
                    # weight += line.product_id.weight * line.picked_qty
                    weight += line.product_id.get_weight(qty=line.picked_qty)
                else:
                    # weight += line.product_id.weight * line.product_uom_qty
                    weight += line.product_id.get_weight(qty=line.product_uom_qty)
        return weight

    @api.model
    def check_sale_line_vals(self, sale_line_vals):
        if not sale_line_vals.get('product_id', False):
            raise UserError(_('Sale line has to have \'%s\' filled') % _('Product'))
        if not sale_line_vals.get('product_uom_qty', False):
            sale_line_vals['product_uom_qty'] = 0
        if not sale_line_vals.get('price_unit', False):
            sale_line_vals['price_unit'] = 0.0
            
        return True

    @api.model
    def create_sale_line(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self.env.context or {}
        commit = not context.get('no_commit', False)

        line = self.search([
            ('external_sale_order_line_id','=',vals['external_sale_order_line_id'])
        ], order='id', limit=1)
        if line and interm_obj.do_not_update_vals('sale.order.line') and 'picked_qty' not in vals.keys():
            return line
        sale_line_vals = {}
        sale_line_vals.update(vals)
        if line:
            interm_obj.remove_same_values(line, sale_line_vals)
            if sale_line_vals:
                line.write(sale_line_vals)
        else:
            sale_line_vals = self.default_get(self._fields)
            sale_line_vals.update(vals)
            self.check_sale_line_vals(sale_line_vals)
            line = self.with_context(recompute=False).create(sale_line_vals)
        if commit:
            self.env.cr.commit()
        return line

    @api.model
    def update_vals(self, vals):
        context = self.env.context or {}
        if 'picked_qty' in vals.keys() and not context.get('allow_to_copy_sale', False):
            vals['picked_qty_filled_in'] = True
            try:
                if int(vals['picked_qty']) == round(vals['picked_qty'], 3):
                    vals['picked_qty_str'] = str(int(vals['picked_qty']))
                else:
                    vals['picked_qty_str'] = str(vals['picked_qty']).replace('.', ',')
            except:
                vals['picked_qty_str'] = str(vals['picked_qty'])

    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        prod_obj = self.env['product.product']
        if vals.get('product_id', False):
            product = prod_obj.browse(vals['product_id'])
            vals['product_code'] = product.get_product_code()
        # if 'product_uom_qty' in vals.keys():
        #     vals['temp_product_uom_qty'] = vals['product_uom_qty']
        res = super(SaleOrderLine, self).write(vals)
        if {'order_id', 'product_id', 'product_uom_qty'}.intersection(set(vals.keys())):
            self.update_weight()
            self.update_pallet_quantity()

        if ('order_id' in vals.keys() or 'sequence' in vals.keys()) and 'line_no' not in vals.keys():
            self.mapped('order_id').recount_lines_numbers()
        if 'invoice_line_ids' in vals.keys():
            self.mapped('order_id').update_cash_amount()
        if 'picked_qty' in vals.keys():
            self.update_weight()
        return res

    @api.model
    def create(self, vals):
        context = self.env.context or {}
        link_obj = self.env['stock.route.integration.intermediate.missing_links']
        prod_obj = self.env['product.product']
        self.update_vals(vals)
        if vals.get('product_id', False) and not vals.get('product_code', False):
            product = prod_obj.browse(vals['product_id'])
            vals['product_code'] = product.get_product_code()
        # if 'product_uom_qty' in vals.keys():
        #     vals['temp_product_uom_qty'] = vals['product_uom_qty']
        line = super(SaleOrderLine, self.with_context(recompute=False)).create(vals)
        if line.sequence != line.line_no:
            line.write({'sequence': line.line_no})
        if vals.get('external_sale_order_line_id', False) and not context.get('skip_missing_link_search', False):
            link_obj.check_for_missing_links(self._name, vals['external_sale_order_line_id'])
        line.update_weight()
        line.update_pallet_quantity()
        if ('order_id' in vals.keys() or 'sequence' in vals.keys()) and 'line_no' not in vals.keys():
            line.order_id and line.order_id.recount_lines_numbers()

        return line

    @api.multi
    def unlink(self):
        tasks_to_recount = self.env['sale.order']
        for line in self:
            if line.order_id:
                tasks_to_recount += line.order_id
        res = super(SaleOrderLine, self).unlink()
        if tasks_to_recount:
            tasks_to_recount.recount_lines_numbers()
        return res

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        do = False
        if 'picked_qty_str' in fields:
            fields.append('has_related_document')
            do = True
        if not fields:
            do = True
        res = super(SaleOrderLine, self).read(fields=fields, load=load)
        if do:
            for line in res:
                if line['picked_qty_str'] and line['picked_qty_str'] != '0' and not line['has_related_document']:
                    line['picked_qty_str'] = ''
        return res

# class sale_order_route_sequence(osv.Model):
#     #nebenaudojama
#     _name = 'sale.order.route_sequence'
#     _description = 'Route Sequence'
#     
#     _columns = {
#         'sale_order_id': fields.many2one('sale.order', 'Sale', readonly=True),
#         'route_id': fields.many2one('stock.route', 'Route', readonly=True),
#         'sequence': fields.integer('Sequence', readonly=True),
#         'name': fields.char('Name', size=256, readonly=True),
#     }
#     
#     _sql_constraints = [
#         ('external_sale_order_route_id', 'unique (sale_order_id, route_id)', 'Sequence object for route in sale already exists'),
#         ('external_sale_order_sequence', 'unique (sale_order_id, sequence)', 'Sequence for route in sale already exists'),
#     ]
#     
#     _order = 'sequence'
#     
#     def check_connection(self, cr, uid, from_id, to_id, context=None):
#         from_rec = self.browse(cr, uid, from_id, context=context)
#         to_rec = self.browse(cr, uid, to_id, context=context)
#         if from_rec.sale_id.id != to_rec.sale_id.id:
#             return False
#         if from_rec.route_id.warehouse_destination_id.id != to_rec.route_id.warehouse_id.id:
#             return False
#         
#         return True
#         
#     def get_first_route_id(self, cr, uid, sale_id, context=None):
#         ids = self.search(cr, uid, [
#             ('sale_order_id','=',sale_id)
#         ], order='sequence', context=context)
#         return ids and self.browse(
#             cr, uid, ids[0], context=context
#         ).route_id.id or False
#         
#     def get_last_route_id(self, cr, uid, sale_id, context=None):
#         ids = self.search(cr, uid, [
#             ('sale_order_id','=',sale_id)
#         ], order='sequence desc', context=context)
#         return ids and self.browse(
#             cr, uid, ids[0], context=context
#         ).route_id.id or False
#     
#     def get_added_routes(self, cr, uid, sale_id, context=None):
#         so_obj = self.env('sale.order')
#         sale = so_obj.browse(cr, uid, sale_id, context=context)
#         route_w_seq_ids = set([seq.route_id.id for seq in sale.route_sequence_ids])
#         route_wo_seq_ids = set([route.id for route in sale.related_route_ids])
#         return list(route_wo_seq_ids - route_w_seq_ids)
#     
#     def get_removed_routes(self, cr, uid, sale_id, context=None):
#         so_obj = self.env('sale.order')
#         sale = so_obj.browse(cr, uid, sale_id, context=context)
#         route_w_seq_ids = set([seq.route_id.id for seq in sale.route_sequence_ids])
#         route_wo_seq_ids = set([route.id for route in sale.related_route_ids])
#         return list(route_w_seq_ids - route_wo_seq_ids)
#     
#     def get_sequence(self, cr, uid, route_id, sale_id, context=None):
#         ids = self.search(cr, uid, [
#             ('sale_order_id','=',sale_id),
#             ('route_id','=',route_id)
#         ], context=context)
#         if ids:
#             return self.browse(cr, uid, ids[0], context=context).sequence
#         return False
#     
#     def create(self, cr, uid, vals, context=None):
#         if vals.get('route_id', False):
#             vals['name'] = self.env('stock.route').get_route_info(
#                 cr, uid, vals['route_id'], context=context
#             )
#         id = super(sale_order_route_sequence, self).create(
#             cr, uid, vals, context=context
#         )
#         return id
# sale_order_route_sequence()