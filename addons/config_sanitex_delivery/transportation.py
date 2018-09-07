# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo import tools

import logging
import datetime
import traceback

_logger = logging.getLogger(__name__)

class TransportationOrder(models.Model):
    _name = 'transportation.order'
    
    @api.model   
    def _get_default_warehouse(self):
        user_env = self.env['res.users']
        user = user_env.browse(self._uid)
        return user.default_warehouse_id.id or False
    
    @api.model
    def _get_transportation_order_states(self):
        return [
            ('blank','Blank'),
            ('transfered_to_warehouse','Transfered to Warehouse (POOL)'),
            ('being_collected','Being Collected'),
            ('need_invoice','Fully Collected'),
            ('invoiced','Invoiced'),
            ('cancel','Canceled'),
        ]

    name = fields.Char(
        'Order Reference', required=True, copy=False
    )
    owner_id = fields.Many2one("product.owner","Owner")
    partner_id = fields.Many2one('res.partner', "Partner")
    posid_partner_id = fields.Many2one('res.partner', "POSID Partner")
    warehouse_id = fields.Many2one(
        'stock.warehouse', "Warehouse", default=_get_default_warehouse,
        readonly=True
    )
    location_id = fields.Many2one('stock.location', "Location")
    transport_type_id = fields.Many2one('transport.type', 'Transport Group')
    state = fields.Selection(
        _get_transportation_order_states, 'State', readonly=True, default='blank'
    )
    line_ids = fields.One2many('transportation.order.line', 'transportation_order_id', "Lines")
#     invoice_id = fields.Many2one('account.invoice', "Invoice", readonly=True)
    invoice_ids = fields.Many2many(
        'account.invoice', 'transportation_order_invoice_rel', 'transportation_order_id',
        'invoice_id', "Invoice", readonly=True
    )
    no_delivery = fields.Boolean("No Delivery", default=False)
    delivery_by_agent = fields.Boolean("Delivery by Agent", default=False)
    delivery_date = fields.Date('Delivery Date')
    date = fields.Date('Date')
#     mismatch_document = fields.Selection([
#         ('credit', "Credit Document"),
#         ('annul', "Annul Document")
#     ], "Mismatch Invoice", required=True)
    
    @api.multi
    def set_being_collected_state(self):
        self.write({'state': 'being_collected'})
        return True
    
    @api.multi
    def set_need_invoice_state(self):
        self.write({'state': 'need_invoice'})
        return True

    @api.multi
    def remove_from_system(self):
        self.unlink()

    @api.model
    def cron_delete_old_transportation_orders(self):

        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_transportation_orders_after

        date_field = company.get_date_field_for_removing_object(self._name)
        _logger.info('Removing old Transportation Orders (%s days old) using date field \'%s\'' % (
        str(days_after), date_field))

        today = datetime.datetime.now()
        date_until = today - datetime.timedelta(days=days_after)
        orders = self.search([
            (date_field, '<', date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Transportation Orders: found %s records' % str(len(orders)))
        if log:
            all_order_count = float(len(orders))
            i = 0
            last_log = 0
        ids_to_unlink = orders.mapped('id')
        # for order in orders:
        for order_ids in [ids_to_unlink[ii:ii+50] for ii in range(0, len(ids_to_unlink), 50)]:
            try:
                # order.remove_from_system()
                # self.env.cr.commit()
                self.browse(order_ids).remove_from_system()
                self.env.cr.commit()
                if log:
                    i += 1
                    if last_log < int((i / all_order_count)*100):
                        last_log = int((i / all_order_count)*100)
                        _logger.info('Transportation order delete progress: %s / %s' % (str(i), str(int(all_order_count))))
            except Exception as e:
                err_note = 'Failed to delete  Order(ID: %s): %s \n\n' % (str(order_ids), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
    

class TransportationOrderLine(models.Model):
    _name = 'transportation.order.line'
    
    transportation_order_id = fields.Many2one(
        'transportation.order', "Transportation Order", ondelete='cascade', index=True
    )
    product_id = fields.Many2one('product.product', string="Product")
    product_code = fields.Char(string="Product Code", readonly=True)
    uom_id = fields.Many2one('product.uom', string='Product Unit of Measure')
    quantity = fields.Float("Quantity", digits=dp.get_precision('Product Unit of Measure'), readonly=True)
#     exp_date = fields.Date('Expiration Date')
    small_package_qty = fields.Float("Small Package Quantity")
    big_package_qty = fields.Float("Big Package Quantity")
    small_package_size = fields.Float("Small Package Size", readonly=True)
    big_package_size = fields.Float("Big Package Size", readonly=True)
    product_qty = fields.Float(
        "Product Quantity", digits=(12,3), help="Product quantity not in package"
    )
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    serial_id = fields.Many2one('product.stock.serial', 'Serial')
    sale_id = fields.Many2one('sale.order', "Transportation Task", index=True)
    payment_term_days = fields.Integer("Payment Term Days")

    
#     @api.onchange('small_package_qty', 'big_package_qty', 'product_qty')
#     def _onchange_package_or_product_qty(self):
#         self.quantity = ((self.small_package_qty or 0.0) * (self.small_package_size or 0.0)) +\
#         ((self.big_package_qty or 0.0) * (self.big_package_size or 0.0)) + (self.product_qty or 0.0)
        
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
#             self.small_package_size = self.product_id.small_package_size or 0.0
#             self.big_package_size = self.product_id.big_package_size or 0.0
            self.product_code = self.product_id.default_code
#             if self.product_id.uom_id:
#                 self.uom_id = self.product_id.uom_id.id
#         else:    
#             self.small_package_size = 0.0
#             self.big_package_size = 0.0
#         self._onchange_package_or_product_qty()
        
    @api.model
    def get_readonly_fields_vals(self, vals):   
        res = {}
        if vals.get('product_id', False):
            prod_env = self.env['product.product']
            product = prod_env.browse(vals['product_id'])
            res['product_code'] = product.default_code or False
#             res['small_package_size'] = product.small_package_size or 0.0
#             res['big_package_size'] = product.big_package_size or 0.0
        return res
    
#     @api.multi
#     def calc_readonly_fields(self):   
#         for order in self:
#             quantity = ((order.small_package_qty or 0.0) * (order.small_package_size or 0.0)) +\
#                 ((order.big_package_qty or 0.0) * (order.big_package_size or 0.0)) + (order.product_qty or 0.0)
#             order.with_context({'read_only_fields': True}).write({'quantity': quantity})
#         return True


    @api.model
    def create(self, vals):
        vals.update(self.get_readonly_fields_vals(vals))
        res = super(TransportationOrderLine, self).create(vals)  
#         res.calc_readonly_fields()
        return res
    
    @api.multi
    def write(self, vals):
#         context = self._context or {}
#         if not context.get('read_only_fields', False):
#             vals.update(self.get_readonly_fields_vals(vals))
#             res = super(TransportationOrderLine, self).write(vals)
# #             self.calc_readonly_fields()
#         else:
        res = super(TransportationOrderLine, self).write(vals)
        return res 
    
    