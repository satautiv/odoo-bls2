# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields, _
# from openerp.exceptions import UserError
import time

from .stock import utc_str_to_local_str

from datetime import datetime
import pytz
from pytz import timezone

import uuid

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
#     despatch_advice_id = fields.Many2one('despatch.advice', "Despatch Advice")
#     container_line_ids = fields.One2many(
#         'account.invoice.container.line', 'sale_order_id', "Container Lines"
#     )
    one_time_partner_id = fields.Many2one('transportation.order.partner', "One Time Partner")
    location_id = fields.Many2one('stock.location', "Location")
    owner_partner_id = fields.Many2one('res.partner', "Owner Partner")
    lines_count = fields.Integer("Number of Lines")
    despatch_advice_ids = fields.One2many('despatch.advice', 'sale_order_id', "Despatch Advice")
    linked_with_despatch = fields.Boolean("Linked With Dispatch", default=False)
    
#     @api.multi
#     def get_invoices(self):
#         invoices = super(SaleOrder, self).get_invoices()
#         
#         return invoices

#     @api.multi
#     def get_total_weight(self):
#         weight = 0.0
#         for sale in self:
#             if sale.container_line_ids:
#                 for container_line in sale.container_line_ids:
#                     weight += container_line.product_id.weight or 0.0
#             else:
#                 weight += super(SaleOrder, self).get_total_weight()
# #             if sale.transportation_order_id and sale.transportation_order_line_ids:
# #                 for to_line in sale.transportation_order_line_ids:
# #                     weight += to_line.product_id.weight or 0.0
# #             else:    
# #                 for line in sale.order_line:
# #                     weight += line.total_weight
# #                     
# #                 # kai užduotis susikuria iš siuntos ji neturi eilučių, bet turi conteinerius
# #                 if not sale.order_line and sale.container_ids:
# #                     for container in sale.container_ids:
# #                         weight += container.weight
#         return weight
    
    @api.multi
    def link_with_despatch(self):
        despatch_env = self.env['despatch.advice']
        for sale in self:
            despatches = despatch_env.search([
                ('id_bls_shipment','=',sale.name)
            ])
            if despatches:
                despatches.link_with_sale_order(sale_order_id=sale.id)
                
        return True
    
    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
#         res.link_with_despatch()
        
#             res.write({'linked_with_despatch': True})
            
#         lines_count = len(res.order_line)
#         if lines_count:
#             res.write({'lines_count': lines_count})
        
        return res
    
    @api.multi
    def recalc_state(self):
        for sale in self:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    sale_order_line
                WHERE order_id = %s
                    AND picked_qty < product_uom_qty
                LIMIT 1
            ''', (sale.id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                state = 'being_collected'
            else:
                state = 'need_invoice'
#             sale.write({'state': state})
        self._cr.execute('''
                UPDATE
                    sale_order
                SET
                    state = %s
                WHERE id = %s
            ''', (state, sale.id))

        return True
        
    @api.multi
    def calc_picked_qty_from_despatch(self):
        for sale in self:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    despatch_advice
                WHERE sale_order_id = %s
            ''', (sale.id,))
            sql_res = self._cr.fetchall()
            despatch_advice_ids = [i[0] for i in sql_res]
            if despatch_advice_ids:
                self._cr.execute('''
                        SELECT
                            id, product_id
                        FROM
                            sale_order_line
                        WHERE order_id = %s
                    ''', (sale.id,))
                sale_order_line_tuples = self._cr.fetchall()
    #             sale_order_line_ids = [i[0] for i in sql_res]
                for sale_order_line_tuple in sale_order_line_tuples:
                    sale_order_line_id = sale_order_line_tuple[0]
                    product_id = sale_order_line_tuple[1]
                    
                    self._cr.execute('''
                        SELECT
                            id, qty
                        FROM
                            account_invoice_container_line
                        WHERE product_id = %s
                            AND despatch_advice_id in %s
                    ''', (product_id, tuple(despatch_advice_ids)))
                    container_line_tuples = self._cr.fetchall()
                    container_line_ids = []
                    picked_qty = 0.0
                    for container_line_tuple in container_line_tuples:
                        container_line_ids.append(container_line_tuple[0])
                        picked_qty += container_line_tuple[1] or 0.0

                    if container_line_ids:
                        self._cr.execute('''
                            UPDATE
                                account_invoice_container_line
                            SET
                                sale_order_line_id = %s
                            WHERE id in %s
                        ''', (sale_order_line_id, tuple(container_line_ids)))
                        
                        
                        self._cr.execute('''
                            SELECT
                                tol.invoice_group_index, tol.waybill_group_index
                            FROM
                                transportation_order_line AS tol
                            LEFT JOIN
                                account_invoice_container_line AS aicl ON (
                                    aicl.order_line_id = tol.id
                                )
                            WHERE
                                aicl.id = %s
                            LIMIT 1
                        ''', (container_line_ids[0],))
                        invoice_group_index, waybill_group_index = self._cr.fetchone()
                        
                        
                        self._cr.execute('''
                            UPDATE
                                sale_order_line
                            SET
                                picked_qty = %s,
                                invoice_group_index = %s,
                                waybill_group_index = %s
                            WHERE id = %s
                        ''', (
                            picked_qty, invoice_group_index or None,
                            waybill_group_index or None, sale_order_line_id
                        ))
        
#         container_line_env = self.env['account.invoice.container.line']
#         for sale in self:
#             despatch_ids = sale.despatch_advice_ids.ids
#             for sale_line in sale.order_line:
#                 sale_line_product_code = sale_line.product_code
#                 container_lines = container_line_env.search([
#                     ('despatch_advice_id','in',despatch_ids),
#                     ('product_code','=',sale_line_product_code)
#                 ])
#                 container_line_ids_vals = []
#                 picked_qty = 0.0
#                 for conatiner_line in container_lines:
#                     container_line_ids_vals.append((4,conatiner_line.id))
#                     picked_qty += conatiner_line.qty or 0.0
#                 if container_line_ids_vals or picked_qty:
#                     sale_line.write({
#                         'container_line_ids': container_line_ids_vals,
#                         'picked_qty': picked_qty,
#                     })
#                     
            sale.recalc_state()       
        return True


#     @api.multi
#     def do_invoice(self):
#         invoice_env = self.env['account.invoice']
#         transportation_order_doc_env = self.env['transportation.order.document']
#         container_line_env = self.env['account.invoice.container.line']
#         
#         created_invoices = self.env['account.invoice']
#         container_lines = self.env['account.invoice.container.line']
#         
#         invalid_sale_names = []
#         for sale in self:
#             if sale.state != 'need_invoice':
#                 invalid_sale_names.append(sale.name)
#                 continue    #neverta testi ir krautis konteinerio eiluciu, nes vistiek operacija nebus vykdoma
#             
#             
# #             container_lines += sale.container_line_ids
#             container_lines += container_line_env.search([
#                 ('sale_order_line_id','in', sale.order_line.ids),
#             ])
#                  
#         if invalid_sale_names:
#             raise UserError(
#                 _('Selected orders can not be invoiced because it is not fully picked.\nPlease check these tasks: %s') % (
#                     ', '.join(invalid_sale_names)
#                 )
#             )
#             

#         for container_line in container_lines:
#             transportation_order_docs = transportation_order_doc_env.search([
#                 ('transportation_order_id','=',container_line.order_id.id)
#             ])
# #             order = container_line.order_id
#             order_line = container_line.order_line_id
#             sale_order_line = container_line.sale_order_line_id
#             sale_order = sale_order_line.order_id
#             payment_term = order_line.payment_term
#             payment_term_date = order_line.payment_term_date
#             
#             for transportation_order_doc in transportation_order_docs: #gali reiketi israsineti bent kelis dokumentus
#                 category = transportation_order_doc.document_type
#                 if category == 'invoice':
#                     merge_code = order_line.invoice_group_index
#                 elif category == 'waybill':
#                     merge_code = order_line.waybill_group_index
#                 else:
#                     merge_code = False
#                     
#                 given_document_no = transportation_order_doc.document_no
# 
#                 invoice = created_invoices.filtered(lambda inv:\
#                     inv.category == category\
#                     and (merge_code and inv.merge_code == merge_code or not merge_code)\
#                     and (given_document_no and inv.name == given_document_no or not given_document_no)\
#                     and inv.owner_id == sale_order.owner_id\
#                     #REZERVUOTA VIETA PARTNER OWNERIUI, JEI PATYS KURSIM UZDUOTIS
#                     and inv.posid == sale_order.posid\
#                     and (payment_term and inv.payment_term == payment_term or not payment_term)\
#                     and (payment_term_date and inv.payment_term_date == payment_term_date or not payment_term_date)                                    
#                 )
#                 
#                 if not invoice:
#                     inv_vals = invoice_env.default_get(invoice_env._fields)
#                     inv_vals.update({
#                         'partner_shipping_id': sale_order.partner_shipping_id.id,
#                         'partner_id': sale_order.partner_id.id,
#                         'owner_id': sale_order.owner_id.id,
#                         #REZERVUOTA VIETA PARTNER OWNERIUI, JEI PATYS KURSIM UZDUOTIS
#                         'type': 'out_invoice',
#                         'category': category,
# #                         'state': 'close',
# #                         'name': name,
#                         'date_invoice': time.strftime('%Y-%m-%d'),
#                         'payment_term_date': payment_term_date,
#                         'payment_term': payment_term,
# #                         'document_tax_id': payment_term.get('document_tax_id', False),
# #                         'document_form_id': other_vals.get('document_form_id', False), 
#                         'merge_code': merge_code,
#                         'posid': sale_order.posid,   
#                     })
#                     
#                     if given_document_no:
#                         inv_vals['name'] = given_document_no
#                         

#                     invoice = invoice_env.create(inv_vals)
#                     created_invoices += invoice
#                                                                                      
#         return True


    @api.multi
    def do_invoice(self, allow_splitting=False):
        if not self:
            return {}
        
        self.do_out_despatch_linked_with_despatch()
        
#         transportation_order_doc_env = self.env['transportation.order.document']
#         container_line_env = self.env['account.invoice.container.line']
        invoice_env = self.env['account.invoice']
        invoice_line_env = self.env['account.invoice.line']
        product_env = self.env['product.product']
        do_invoice_result_wiz_env = self.env['do.invoice.result.wizard']
        doc_type_env = self.env['document.type']
        warehouse_env = self.env['stock.warehouse']
        owner_env = self.env['product.owner']
        inv_tax_env = self.env['account.invoice.tax']
        
        created_invoices = self.env['account.invoice']
        created_invoice_lines = self.env['account.invoice.line']
        
        inv_line_ctx = self._context or {}
        inv_line_ctx['skip_weight_calculation'] = True
        inv_line_ctx['skip_sale_order_check'] = True
        inv_line_ctx['tracking_disable'] = True
        inv_line_ctx['recompute'] = False
        
        user = self.env.user
        
        warehouse_id = user.get_main_warehouse_id()
        
#         if not warehouse_id:
#             raise UserError(
#                 _('Please select warehouse you are working in')
#             )
            
        warehouse = warehouse_env.browse(warehouse_id)

        document_package_no = user.convert_datetime_to_user_tz(time.strftime("%Y-%m-%d %H:%M:%S"))
        
        package_context = self._context or {}
        package_context['doc_package_no'] = document_package_no
        package_context['recompute'] = False
        
        msg = ''

        self._cr.execute('''
            SELECT
                aicl.id
            FROM
                account_invoice_container_line AS aicl
            LEFT JOIN
                invoice_line_container_line_rel AS ilclr ON (
                    ilclr.container_line_id = aicl.id
                )
            JOIN
                sale_order_line AS sol ON (
                    aicl.sale_order_line_id = sol.id
                )
            WHERE ilclr.container_line_id is NULL
                AND sol.order_id in %s
                AND aicl.order_id is not null
                AND aicl.order_line_id is not null
            ORDER BY
                aicl.id
        ''', (tuple(self.ids),))
        
        sql_res = self._cr.fetchall()
        container_line_ids = [i[0] for i in sql_res if i[0]] 
        
        if not container_line_ids:
            msg = _("There are not any related uninvoiced despatch lines to get invoice data. (It's already invoiced or customer order is missing).")
        
        fully_collected_by_merge_code = {}
        fully_collected_by_doc_no = {}
        
        tasks_which_can_not_be_invoiced = []
        merge_codes_and_tasks_which_can_not_be_invoiced = {}
        doc_numbers_and_tasks_which_can_not_be_invoiced = {}
        
        for container_line_id in container_line_ids:
            
#             container_line_read = container_line_env.browse(container_line_id).read([
#                 'order_id', 'sale_order_line_id', 'order_line_id', 
#                 'product_id', 'qty', 'despatch_advice_id',
#                 'product_code'
#             ])[0]
            
            
            self._cr.execute('''
                SELECT
                    order_id, sale_order_line_id, order_line_id,
                    product_id, qty, product_code, container_id,
                    expiry_date
                FROM
                    account_invoice_container_line
                WHERE id = %s
            ''', (container_line_id,))
#             sale_order_name = self._cr.fetchone()[0]

            order_id, sale_order_line_id, order_line_id,\
            product_id, qty, product_code, container_id,\
            container_line_exp_date = self._cr.fetchone()
            
#             order_line_id = container_line_read['order_line_id'][0]
#             sale_order_line_id = container_line_read['sale_order_line_id'][0]
            
         
#             package_prod = False
#             self._cr.execute('''
#                 SELECT
#                     type_of_product
#                 FROM
#                     product_product
#                 WHERE id = %s
#                 )
#                 LIMIT 1
#             ''', (container_line_read['product_id'][0],))
#             prod_type = self._cr.fetchone()[0]
#             if prod_type in ('package', 'deposit_package'):
#                 package_prod = True
            

#             order_id = container_line_read['order_id'] and container_line_read['order_id'][0] or False
            if not order_id:
#                 raise UserError(
#                     _("Container line with ID %s wasn't linked to any transportation order line") % (container_line_id,)
#                 )
                msg += _("Despatch line with ID %s wasn't linked to any transportation order line.\n") % (container_line_id,)
                continue
            
#             self._cr.execute('''
#                 SELECT
#                     saleo.name
#                 FROM
#                     sale_order as saleo
#                 LEFT JOIN sale_order_line as sol ON (
#                     sol.order_id = saleo.id
#                 )
#                 WHERE sol.id = %s
#             ''', (sale_order_line_id,))
#             sale_order_name = self._cr.fetchone()[0]
            
            
            # Driveriu ir carrieriu info
            carrier_id = False
            driver_id = False
            driver_name = False
            self._cr.execute('''
                SELECT
                    saleo.route_template_id, saleo.name
                FROM
                    sale_order as saleo
                LEFT JOIN sale_order_line as sol ON (
                    sol.order_id = saleo.id
                )
                WHERE sol.id = %s
            ''', (sale_order_line_id,))
            route_template_id, sale_order_name = self._cr.fetchone()
            if route_template_id:
                self._cr.execute('''
                    SELECT
                        driver 
                    FROM
                        stock_route_template
                    WHERE id = %s
                ''', (route_template_id,))
                driver_name = self._cr.fetchone()[0] or False
            
            if driver_name:
                self._cr.execute('''
                    SELECT
                        id, owner_id 
                    FROM
                        stock_location
                    WHERE name = %s
                    LIMIT 1
                ''', (driver_name,))
                sql_res = self._cr.fetchone()
                if sql_res:
                    driver_id, carrier_id = sql_res
                    

            driver_info_vals = {
                'carrier_id': carrier_id,
                'driver_id': driver_id,
                'driver_name': driver_name,
            }

#             transportation_order_docs = transportation_order_doc_env.search([
#                 ('transportation_order_id','=',order_id)
#             ])
#             
            self._cr.execute('''
                SELECT
                    document_type, document_no,
                    sending_type, document_form_id,
                    print_copies, delivery_conditions,
                    group_by_transport_unit, group_by_prod_params
                FROM
                    transportation_order_document
                WHERE transportation_order_id = %s
            ''', (order_id,))
#             sql_res = self._cr.fetchall()
#             transportation_order_doc_ids = [i[0] for i in sql_res if i]
            transportation_order_doc_tuples = self._cr.fetchall()
            
            #Reikiamos info is orderio istraukimas
            self._cr.execute('''
                SELECT
                    buyer_id, one_time_buyer_id, delivery_address_id, 
                    owner_id, posid_code, note, seller_id, despatch_address_id,
                    delivery_terms
                FROM
                    transportation_order
                WHERE id = %s
                LIMIT 1
            ''', (order_id,))
            sql_res = self._cr.fetchone()
            
            partner_id = sql_res[0] or False
            one_time_partner_id = sql_res[1] or False
            owner_id = sql_res[3] or False
            posid = sql_res[4] or False
            partner_address_id = sql_res[2] or partner_id
            delivery_terms = sql_res[8] or "bls"
            
            transportation_order_inv_vals = {
                'partner_id': partner_id,
                'one_time_partner_id': one_time_partner_id,
                'partner_shipping_id': sql_res[2] or False,
#                 'owner_id': owner_id,
                'posid': posid,
                'comment': sql_res[5] or "",
                'seller_partner_id': sql_res[6] or False,
                'despatch_address_id': sql_res[7] or False,
                'delivery_terms': delivery_terms,
            }
            
            if one_time_partner_id:
                self._cr.execute('''
                    SELECT
                        ref, name, address
                    FROM
                        transportation_order_partner
                    WHERE id = %s
                    LIMIT 1
                ''', (one_time_partner_id,))
                sql_res = self._cr.fetchone()
                
                transportation_order_inv_vals.update({
                    'partner_ref': sql_res[0] or False,
                    'partner_name': sql_res[1] or False,
                    'partner_address': sql_res[2] or False,
                })
            else:
                self._cr.execute('''
                    SELECT
                        supplier_code, ref, name, street
                    FROM
                        res_partner
                    WHERE id = %s
                    LIMIT 1
                ''', (partner_id,))
                sql_res = self._cr.fetchone()
                
                transportation_order_inv_vals.update({
                    'supplier_code': sql_res[0] or False,
                    'partner_ref': sql_res[1] or False,
                    'partner_name': sql_res[2] or False,
                })

                self._cr.execute('''
                    SELECT
                        street
                    FROM
                        res_partner
                    WHERE id = %s
                    LIMIT 1
                ''', (partner_address_id,))
                sql_res = self._cr.fetchone()

                transportation_order_inv_vals.update({
                    'partner_address': sql_res[0] or False,
                })

            self._cr.execute('''
                SELECT
                    payment_term, payment_term_date 
                FROM
                    transportation_order_line
                WHERE id = %s
                LIMIT 1
            ''', (order_line_id,))
            sql_res = self._cr.fetchone()
            transportation_order_inv_vals['payment_term'] = sql_res[0] or False
            transportation_order_inv_vals['payment_term_date'] = sql_res[1] or False

            #Transportation Order Line'o duomenys eilutes formavimui
            self._cr.execute('''
                SELECT
                    unit_price, uom_id, discount, tax_id 
                FROM
                    transportation_order_line
                WHERE id = %s
                LIMIT 1
            ''', (order_line_id,))
            sql_res = self._cr.fetchone()
            order_line_inv_line_vals = {
                'price_unit': sql_res[0],
                'uom_id': sql_res[1],
                'discount': sql_res[2],
                'invoice_line_tax_ids': sql_res[3] and [(4,sql_res[3])] or [],
            }
            
#             product_id = container_line_read['product_id'][0]
            prod_read = product_env.browse(product_id).read(['name','type_of_product', 'default_code'])[0]
            prod_name = prod_read['name']
            product_code = prod_read['default_code']
            
#             if not owner_id:
            self._cr.execute('''
                SELECT
                    saleo.owner_id, saleo.route_id
                FROM
                    sale_order as saleo
                LEFT JOIN sale_order_line as sol ON (
                    sol.order_id = saleo.id
                )
                WHERE sol.id = %s
                LIMIT 1
            ''', (sale_order_line_id,))
            sale_owner_id, route_id = self._cr.fetchone()
            if not owner_id:
                owner_id = sale_owner_id
            transportation_order_inv_vals['owner_id'] = owner_id
            
            
            if route_id:
                self._cr.execute('''
                    SELECT
                        date
                    FROM
                        stock_route
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (route_id,))
                sql_res = self._cr.fetchone()
                route_date = sql_res and sql_res[0] and False
            else:
                route_date = False
                
                
                
#             product_code = container_line_read['product_code']
#             merge_products = prod_read['type_of_product'] in ['package']

            if not transportation_order_doc_tuples:
                msg += _("Task %s does not have information what kind of document is required.\n") % (sale_order_name)
                continue
            
            self._cr.execute('''
                 SELECT
                     lot_id
                 FROM
                     container_line_lot_rel
                 WHERE container_line_id = %s
                 LIMIT 1
             ''', (container_line_id,))
            sql_res = self._cr.fetchone()
            lot_id = sql_res and sql_res[0] or False
            
            
            sibling_doc_ids = []
            
            for transportation_order_doc_tuple in transportation_order_doc_tuples:
                category, given_document_no, sending_type,\
                document_form_id, print_copies, delivery_conditions,\
                group_by_transport_unit, group_by_prod_params = transportation_order_doc_tuple
                    

                if not (group_by_transport_unit and group_by_prod_params):
                    exp_group = False
                elif group_by_prod_params and not group_by_transport_unit:
                    exp_group = 'lot'
                else:
                    exp_group = 'container'
            
                
                if category == 'invoice':
                    self._cr.execute('''
                        SELECT
                            invoice_group_index
                        FROM
                            transportation_order_line
                        WHERE id = %s
                        LIMIT 1
                    ''', (order_line_id,))
                    merge_code = self._cr.fetchone()[0]
                    document_type_code = 'document.invoice'
#                     merge_code = order_line.invoice_group_index
                elif category == 'waybill':
                    self._cr.execute('''
                        SELECT
                            waybill_group_index
                        FROM
                            transportation_order_line
                        WHERE id = %s
                        LIMIT 1
                    ''', (order_line_id,))
                    merge_code = self._cr.fetchone()[0]
                    document_type_code = 'document.waybill'
#                     merge_code = order_line.waybill_group_index
                else:
#                     raise UserError(
#                         _("Unknown document type %s") % (category,)
#                     )
                    msg += _("Task %s line ask for unknow document type %s.\n") % (sale_order_name, category,)
                    continue

                if not merge_code or merge_code == '-':
                    if not allow_splitting:
                        self._cr.execute('''
                            SELECT
                                sol.product_code, saleo.name
                            FROM
                                sale_order_line as sol
                            JOIN sale_order as saleo ON (
                                sol.order_id = saleo.id
                            )    
                            WHERE sol.id = %s
                            AND (sol.product_uom_qty - sol.qty_invoiced) > sol.picked_qty
                        ''', (sale_order_line_id,))
                        sql_res = self._cr.fetchall()
                        
                        if sql_res:
                            tasks_which_can_not_be_invoiced.append(sale_order_name)
    #                         msg += _("Task %s lines group which has to be invoiced together is not fully picked.\n") % (sale_order_name,)
                            continue
                    
                else:    
                    if merge_code not in fully_collected_by_merge_code.keys():
                        self._cr.execute('''
                            SELECT
                                sol.product_code, saleo.name
                            FROM
                                sale_order_line as sol
                            JOIN sale_order as saleo ON (
                                sol.order_id = saleo.id
                            )    
                            JOIN account_invoice_container_line as cl ON (
                                cl.sale_order_line_id = sol.id
                            )
                             
                            JOIN transportation_order_line as tol ON (
                                cl.order_line_id = tol.id
                            )    
                            WHERE (sol.product_uom_qty - sol.qty_invoiced) > sol.picked_qty
                            AND (
                                    tol.invoice_group_index = %s 
                                    OR tol.waybill_group_index = %s
                                )
                        ''', (merge_code, merge_code,))
                        sql_res = self._cr.fetchall()
                        fully_collected_by_merge_code[merge_code] = not sql_res and True or False
                        
                    if not fully_collected_by_merge_code[merge_code]\
                        and not allow_splitting\
                    :
                        if merge_code not in merge_codes_and_tasks_which_can_not_be_invoiced.keys():
                            merge_codes_and_tasks_which_can_not_be_invoiced[merge_code] = [sale_order_name,]
                        elif sale_order_name not in merge_codes_and_tasks_which_can_not_be_invoiced[merge_code]:
                            merge_codes_and_tasks_which_can_not_be_invoiced[merge_code].append(sale_order_name)
                        continue
                        
#                     elif not fully_collected_by_merge_code[merge_code]:
#                         continue
#                     
#                         
#                     if not fully_collected_by_merge_code[merge_code]\
#                         and not allow_splitting\
#                     :
#                         msg += _("Task %s lines group which has to be invoiced together is not fully picked.\n") % (sale_order_name,)
#                         continue
# #                     merge_codes_and_tasks_which_can_not_be_invoiced
                    
                
#                 given_document_no = transportation_order_doc.document_no or False
                
                if given_document_no:
                    if given_document_no not in fully_collected_by_doc_no.keys():
                        self._cr.execute('''
                            SELECT
                                sol.id
                            FROM
                                sale_order_line as sol
                            LEFT JOIN sale_order as saleo ON (
                                sol.order_id = saleo.id
                            )    
                            LEFT JOIN account_invoice_container_line as cl ON (
                                cl.sale_order_line_id = sol.id
                            )
                             
                            LEFT JOIN transportation_order as transo ON (
                                cl.order_id = transo.id
                            )    
                            LEFT JOIN transportation_order_document as tod ON (
                                tod.transportation_order_id = transo.id
                            )
                            WHERE cl.id <> %s
                                AND tod.document_no = %s
                                AND (sol.product_uom_qty - sol.qty_invoiced) > sol.picked_qty
                            LIMIT 1
                        ''', (container_line_id, given_document_no,))
                        sql_res = self._cr.fetchone()

                        if sql_res:
                            fully_collected_by_doc_no[given_document_no] = False
                        else:
                            fully_collected_by_doc_no[given_document_no] = True
                    
                    if not fully_collected_by_doc_no[given_document_no]:
#                         raise UserError(
#                             _("Transportation task %s can not be invoiced, because there are other task lines which has to be invoiced with the same given document number %s") % (sale_order_name, given_document_no)
#                         )
#                         msg += _("Transportation task %s can not be invoiced, because there are other task lines which has to be invoiced with the same given document number %s. \n") % (sale_order_name, given_document_no)
#                         continue
                        if given_document_no not in doc_numbers_and_tasks_which_can_not_be_invoiced.keys():
                            doc_numbers_and_tasks_which_can_not_be_invoiced[given_document_no] = [sale_order_name]
                        elif sale_order_name not in doc_numbers_and_tasks_which_can_not_be_invoiced[given_document_no]:
                            merge_codes_and_tasks_which_can_not_be_invoiced[given_document_no].append(sale_order_name)
                        continue
                  
                invoice = created_invoices.filtered(lambda inv:\
                    inv.category == category\
                    and (
                        (given_document_no and inv.name == given_document_no)\
                        or (not given_document_no and inv.merge_code == merge_code)
                    )\
                    and inv.partner_ref == transportation_order_inv_vals['partner_ref']\
                    and inv.owner_id.id == owner_id\
                    and inv.posid == posid                            
                )

                if not invoice:
#                     self._cr.execute('''
#                         SELECT
#                             count(id)
#                         FROM
#                             account_invoice_line   
#                         WHERE 
#                             invoice_id = %s
#                     ''', (invoice.id,))
#                     line_number = self._cr.fetchone()[0] + 1  
#                 else:
#                     line_number = 1
                    self._cr.execute('''
                        SELECT
                            da.owner_partner_id, da.estimated_delivery_period_id
                        FROM
                            despatch_advice AS da
                        JOIN
                            account_invoice_container_line AS aicl ON (
                                aicl.despatch_advice_id = da.id
                            )
                        WHERE aicl.id = %s
                        LIMIT 1
                    ''', (container_line_id,))
                    owner_partner_id, estimated_delivery_period_id = self._cr.fetchone()
                    
                    
                    if estimated_delivery_period_id:
                        self._cr.execute('''
                            SELECT
                                end_date
                            FROM
                                date_time_period
                            WHERE
                                id = %s
                            LIMIT 1
                        ''', (estimated_delivery_period_id,))
                        sql_res = self._cr.fetchone()
                        estimated_delivery_date = sql_res and sql_res[0] or False
                    else:
                        estimated_delivery_date = False
                    
                    inv_vals = invoice_env.default_get(invoice_env._fields)
                    
                    inv_vals.update({
#                         'partner_shipping_id': sale_order.partner_shipping_id.id,
#                         'partner_id': sale_order.partner_id.id,
#                         'owner_id': sale_order.owner_id.id,
                        'type': 'out_invoice',
                        'category': category,
#                         'state': 'close',
#                         'name': name,
#                         'date_invoice': time.strftime('%Y-%m-%d'),
#                         'payment_term_date': payment_term_date,
#                         'payment_term': payment_term,
#                         'document_tax_id': payment_term.get('document_tax_id', False),
#                         'document_form_id': other_vals.get('document_form_id', False), 
                        'merge_code': merge_code,
#                         'posid': sale_order.posid,
                        'sending_type': sending_type,
                        'document_form_id': document_form_id,
                        'print_copies': print_copies,
                        'delivery_conditions': delivery_conditions,
                        'generated_in_atlas': True,
                        'document_package_no': document_package_no,
                        'owner_partner_id': owner_partner_id,
                        'document_create_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'time_invoice': utc_str_to_local_str(date_format='%H:%M'),
                        'estimated_delivery_date': estimated_delivery_date,
                        'id_external': uuid.uuid1(),
                    })
                    inv_vals.update(transportation_order_inv_vals)
                    inv_vals.update(driver_info_vals)
                      
                    if given_document_no:
                        inv_vals['name'] = given_document_no
                        inv_vals['name_generated_in_atlas'] = False
                    else:
                        owner = owner_env.browse(owner_id)
                        inv_vals['name'] = doc_type_env.get_next_number_by_code(
                            document_type_code, warehouse=warehouse, owner=owner
                        )
                        inv_vals['name_generated_in_atlas'] = True
                        
                    if category == 'invoice':
#                         if delivery_terms == 'client' or (estimated_delivery_date and estimated_delivery_date < time.strftime('%Y-%m-%d')):
                        if route_date:
                            inv_vals['date_invoice'] = route_date
                        elif estimated_delivery_date and estimated_delivery_date > time.strftime('%Y-%m-%d'):
                            inv_vals['date_invoice'] = estimated_delivery_date
                        else:
                            inv_vals['date_invoice'] = time.strftime('%Y-%m-%d') 
                    else:
                        inv_vals['date_invoice'] = time.strftime('%Y-%m-%d')          
   
#                     invoice = invoice_env.with_context(tracking_disable=True, recompute=False).create(inv_vals)
                    invoice_id = invoice_env.with_context(tracking_disable=True, recompute=False)._create(inv_vals)
                    sibling_doc_ids.append(invoice_id)
                    invoice = invoice_env.browse(invoice_id)

                    created_invoices += invoice

#                 inv_line = created_invoice_lines.filtered(lambda inv_line:\
#                     inv_line.invoice_id == invoice\
#                     and (
#                         (merge_products and inv_line.product_code == product_code)\
#                         or inv_line.transportation_order_line_id.id == order_line_id
#                     )                                
#                 )
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         account_invoice_line
#                     WHERE invoice_id = %s
#                     
#                     LIMIT 1
#                 ''', (invoice.id,))
                inv_line_qry_where_part = "WHERE invoice_id = %s" % (invoice.id)
#                 if merge_products:
#                     inv_line_qry_where_part += " AND (product_id = '%s' OR transportation_order_line_id = %s)" % (
#                         product_id, order_line_id
#                     )
#                 else:
                inv_line_qry_where_part += " AND transportation_order_line_id = %s" % (order_line_id, )

                
                if lot_id and exp_group == 'lot':
                    inv_line_qry_where_part += " AND lot_id = %s" % (lot_id, )
                     
                    self._cr.execute('''
                        SELECT
                            expiry_date
                        FROM
                            stock_production_lot
                        WHERE
                            id = %s
                        LIMIT 1
                    ''', (lot_id,))
                    sql_res = self._cr.fetchone()
                    exp_date = sql_res and sql_res[0] or False
                     
                elif container_id and exp_group == 'container':
                    inv_line_qry_where_part += " AND container_id = %s" % (container_id, )
                    exp_date = container_line_exp_date or False
                else:
                    exp_date = False
                     
                if exp_date:
                    inv_line_qry_where_part +=" AND exp_date = %s" % (exp_date, )
                

                inv_line_qry = """
                    SELECT
                        id
                    FROM
                        account_invoice_line
                    %s
                    LIMIT 1
                """ % (inv_line_qry_where_part,)
                
                self._cr.execute(inv_line_qry)

                sql_res = self._cr.fetchone()
                inv_line_id = sql_res and sql_res[0] or False
                if inv_line_id:
                    inv_line = invoice_line_env.browse(inv_line_id)
                else:
                    inv_line = False

                if not inv_line:  
                    inv_line_vals = invoice_line_env.default_get(invoice_line_env._fields)

                    inv_line_vals.update({
                        'invoice_id': invoice.id,
                        'product_id': product_id,
    #                     'uom_id': container_line_read['uom_id'][0],
                        'quantity': qty or 0.0,
                        'name': prod_name,
                        'transportation_order_line_id': order_line_id,
                        'sale_order_line_ids': [(4, sale_order_line_id)],
                        'product_code': product_code,
                        'lot_id': exp_group == 'lot' and lot_id or False,
                        'container_id': exp_group == 'container' and container_id or False,
                        'exp_date': exp_date,
                        'category': category,
#                         'line_number': line_number,
                    })
                    inv_line_vals.update(order_line_inv_line_vals)
#                     t2 = time.time()
#                     inv_line = invoice_line_env.with_context(inv_line_ctx).create(inv_line_vals)
#                     print ("-Viena eilute creatina: %.5f" % (time.time() - t2))

                    inv_line_id = invoice_line_env.with_context(inv_line_ctx)._create(inv_line_vals)
                    inv_line = invoice_line_env.browse(inv_line_id)

                    created_invoice_lines += inv_line

                else:
                    inv_line_read = inv_line.read(['quantity'])[0]
                    inv_line.with_context(inv_line_ctx).write({
                        'quantity': qty + inv_line_read['quantity'],
                    })
                    
                
                self._cr.execute('''
                    UPDATE sale_order_line
                    SET qty_invoiced = qty_invoiced + %s
                    WHERE id = %s
                ''', (qty, sale_order_line_id))
#                 self._cr.execute('''
#                     UPDATE account_invoice_container_line
#                     SET invoice_line_id = %s
#                     WHERE id = %s
#                 ''', (inv_line.id, container_line_id))
#                 self._cr.execute('''
#                     UPDATE invoice_line_container_line_rel
#                     SET invoice_line_id = %s
#                     WHERE container_line_id = %s
#                 ''', (inv_line.id, container_line_id))
                self._cr.execute('''
                    INSERT INTO invoice_line_container_line_rel
                    (invoice_line_id, container_line_id)
                    VALUES
                    (%s, %s)
                ''', (inv_line.id, container_line_id))
      
            if len(sibling_doc_ids) > 1:
                for inv_id in sibling_doc_ids:
                    siblings = set(sibling_doc_ids) - {inv_id}
                    for sibling_id in siblings:
                        self._cr.execute('''
                            INSERT INTO invoice_sibling_invoice_rel
                            (invoice_id, invoice_sibling_id)
                            VALUES
                            (%s, %s)
                        ''', (inv_id, sibling_id))
                
        for invoice in created_invoices:
#             invoice._onchange_invoice_line_ids()
            taxes_grouped = invoice.get_taxes_values()
            for tax_vals in taxes_grouped.values():
                tax_vals['invoice_id'] = invoice.id
                inv_tax_env.with_context(recompute=False)._create(tax_vals)
        
        
        if tasks_which_can_not_be_invoiced:
            tasks_which_can_not_be_invoiced = list(set(tasks_which_can_not_be_invoiced))
            for task_which_can_not_be_invoiced in tasks_which_can_not_be_invoiced:
                msg += _("Task %s lines are not fully picked.\n") % (task_which_can_not_be_invoiced,)
        for merge_code in merge_codes_and_tasks_which_can_not_be_invoiced:
            if len(merge_codes_and_tasks_which_can_not_be_invoiced[merge_code]) == 1:
                msg += _("Task %s was skipped because it has merge code %s ant not all lines are fully picked with this code.\n") % (
                    merge_codes_and_tasks_which_can_not_be_invoiced[merge_code][0], merge_code
                )
            else:
                msg += _("Tasks %s were skipped because they have merge code %s ant not all lines are fully picked with this code.\n") % (
                    ', '.join(merge_codes_and_tasks_which_can_not_be_invoiced[merge_code]), merge_code
                )
        for document_no in doc_numbers_and_tasks_which_can_not_be_invoiced:
            if len(doc_numbers_and_tasks_which_can_not_be_invoiced[document_no]) == 1:
                msg += _("Task %s was skipped because it has given document number %s ant not all lines are fully picked with this number.\n") % (
                    doc_numbers_and_tasks_which_can_not_be_invoiced[document_no][0], document_no
                )
            else:
                msg += _("Tasks %s were skipped because they gave given document number %s ant not all lines are fully picked with this number.\n") % (
                    ', '.join(doc_numbers_and_tasks_which_can_not_be_invoiced[document_no]), document_no
                )        
             
        
        created_invoices.set_version()
        created_invoice_lines.set_version()
        created_invoices.update_full_name()
        
        created_invoices.set_line_numbers()
        created_invoices.update_sale_orders()
        created_invoice_lines.update_total_weight_with_sql()
#         created_invoice_lines.recompute_prices()
        created_invoices.recompute_document_totals()
        created_invoices.update_line_count()
        
        self._cr.commit()
        
#         created_invoices.create_stock_pickings()
        created_invoices.actions_after_document_generate() #Kiti veiksmai po dokumentu sukurimo. Greiciausiai vykdomi kitam threade
        
        do_invoice_result_wiz = do_invoice_result_wiz_env.with_context(package_context).create({
            'msg': msg,
            'created_invoice_ids': [(4, created_inv.id) for created_inv in created_invoices]
        })
        
        form_view = self.env.ref('config_bls_stock.view_do_invoice_result_wizard', False)[0]
        
        return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'do.invoice.result.wizard',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'res_id': do_invoice_result_wiz.id,
                'views': [(form_view.id,'form')],
                'context': package_context,
            }
        
    @api.multi
    def do_out_despatch_linked_with_despatch(self):
        doc_type_env = self.env['document.type']
        warehouse_env = self.env['stock.warehouse']
        owner_env = self.env['product.owner']
        despatch_env = self.env['despatch.advice']
        doc_type_env = self.env['document.type']
        created_out_despatch_ids = []
        
        user = self.env.user
        warehouse_id = user.get_main_warehouse_id()
        warehouse = warehouse_env.browse(warehouse_id)
        
        self._cr.execute('''
            SELECT
                partner_id
            FROM
                res_company    
            WHERE 
                id = %s
            LIMIT 1
        ''', (user.company_id.id,))
        company_partner_id, = self._cr.fetchone()
        
        for sale in self:
            self._cr.execute('''
                SELECT
                    linked_with_despatch, partner_id, route_template_id,
                    partner_shipping_id, owner_id, route_id
                FROM
                    sale_order    
                WHERE 
                    id = %s
                LIMIT 1
            ''', (sale.id,))
            linked_with_despatch, partner_id, route_template_id,\
            partner_shipping_id, owner_id, route_id = self._cr.fetchone()
            
            if not linked_with_despatch:
                continue
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    account_invoice_container_line    
                WHERE 
                    sale_order_line_id in (
                        SELECT
                            id
                        FROM
                            sale_order_line
                        WHERE
                            order_id = %s
                    )
            ''', (sale.id,))
            
            container_line_ids = [i[0] for i in self._cr.fetchall()]
            if not container_line_ids:
                continue
            
            self._cr.execute('''
                SELECT
                    seller_id, despatch_supplier_id
                FROM
                    despatch_advice    
                WHERE 
                    id in (
                        SELECT despatch_advice_id
                        FROM account_invoice_container_line
                        WHERE id = %s
                    )
            ''', (container_line_ids[0],))
            seller_id, despatch_supplier_id = self._cr.fetchone()
            
            if not despatch_supplier_id:
                despatch_supplier_id = company_partner_id
                
                
            driver_id = False
            license_plate = False
            trailer = False
            if route_id:
                self._cr.execute('''
                    SELECT
                        source_location_id, location_id,
                        license_plate, trailer
                    FROM
                        stock_route    
                    WHERE 
                        id = %s
                    LIMIT 1
                ''', (route_id,))
                source_location_id, driver_id,\
                license_plate, trailer = self._cr.fetchone()
            else:
                self._cr.execute('''
                    SELECT
                        driver
                    FROM
                        stock_route_template   
                    WHERE 
                        id = %s
                    LIMIT 1
                ''', (route_template_id,))
                driver_name, = self._cr.fetchone()
                
                if driver_name:
                    self._cr.execute('''
                        SELECT
                            id, license_plate, trailer
                        FROM
                            stock_location   
                        WHERE
                            driver = true
                        AND
                            name = %s
                        LIMIT 1
                    ''', (driver_name,))
                    sql_res = self._cr.fetchone()
                    if sql_res:
                        driver_id, license_plate, trailer = sql_res
                    
                warehouse_id = user.get_main_warehouse_id()
                
                self._cr.execute('''
                    SELECT
                        wh_output_stock_loc_id
                    FROM
                        stock_warehouse  
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (warehouse_id,))
                sql_res = self._cr.fetchone()
                source_location_id = sql_res and sql_res[0] or False    
            
            out_despatch_id = False
            if created_out_despatch_ids:
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        despatch_advice    
                    WHERE 
                        id in %s
                    AND
                        owner_id = %s
                    AND
                        buyer_id = %s
                    AND
                        delivery_address_id = %s
                    AND
                        (route_id = %s OR route_template_id = %s)
                    AND
                        seller_id = %s
                    LIMIT 1
                ''', (
                    tuple(created_out_despatch_ids), owner_id or False,
                    partner_id or False, partner_shipping_id, route_id or -1, #Kvailas sprendimas su -1, bet veiks. Man nereiia, kad suieskotu visu sal be route. Jie route nera, tada reikia klaiutis template'u
                    route_template_id or False, seller_id or False
                ))
                sql_res = self._cr.fetchone()
                out_despatch_id = sql_res and sql_res[0] or False
            if not out_despatch_id:
                owner = owner_id and owner_env.browse(owner_id) or False
                
                name = doc_type_env.get_next_number_by_code(
                    'out.despatch', warehouse=warehouse, owner=owner
                )
                
                
                if driver_id:
                    self._cr.execute('''
                        SELECT
                            owner_id
                        FROM
                            stock_location    
                        WHERE 
                            id = %s
                        LIMIT 1
                    ''', (driver_id,))
                    sql_res = self._cr.fetchone()
                    carrier_id = sql_res and sql_res[0] or False
                else:
                    carrier_id = False
                
                out_despatch_vals = {
                    'despatch_type': 'out_sale',
                    'name': name,
                    'warehouse_id': warehouse_id,
                    'location_id': source_location_id,
                    'id_version': datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone('Europe/Vilnius')).timestamp(),
                    'route_id': route_id,
                    'truck_reg_plate': license_plate or "",
                    'trailer_reg_plate': trailer or "",
#                     'issue_datetime': route_datetime,

                    'issue_datetime': user.get_today_datetime(),
                    'carrier_id': carrier_id,
                    'owner_id': owner_id,
                    'buyer_id': partner_id,
                    'receiver_id': partner_id,
#                     'one_time_buyer_id': one_time_buyer_id,
                    'delivery_address_id': partner_shipping_id,
                    'seller_id': seller_id,
                    'despatch_supplier_id': despatch_supplier_id,
                    'id_external': uuid.uuid1(),
                }
                out_despatch_id = despatch_env._create(out_despatch_vals)
                created_out_despatch_ids.append(out_despatch_id)
                
            self._cr.execute('''
                UPDATE
                    account_invoice_container_line
                SET
                    out_despatch_id = %s
                WHERE 
                    id in %s
            ''', (out_despatch_id, tuple(container_line_ids),))
            
        if self.env.user.company_id.save_test_ubs_to_disk:
            despatch_env.browse(created_out_despatch_ids).form_and_save_to_disk()
            
        return True
    
    @api.multi
    def do_out_movement_despatch(self):
        despatch_env = self.env['despatch.advice']
        container_line_env = self.env['account.invoice.container.line']
        doc_type_env = self.env['document.type']
        owner_env = self.env['product.owner']
        warehouse_env = self.env['stock.warehouse']
        
        created_out_despatch_ids = []
#         created_lines_ids = []
        
        self._cr.execute('''
            SELECT
                partner_id
            FROM
                res_company    
            WHERE 
                id = %s
            LIMIT 1
        ''', (self.env.user.company_id.id,))
        despatch_supplier_id, = self._cr.fetchone()
        
        for sale in self:
            self._cr.execute('''
                SELECT
                    internal_movement_id, partner_id,
                    partner_shipping_id, owner_id, route_id
                FROM
                    sale_order    
                WHERE 
                    id = %s
                LIMIT 1
            ''', (sale.id,))
            internal_movement_id, partner_id,\
            partner_shipping_id, owner_id, route_id = self._cr.fetchone()
            
            if not internal_movement_id:
                continue
            
            self._cr.execute('''
                SELECT
                    operation_id
                FROM
                    internal_operation_movement    
                WHERE 
                    id = %s
                LIMIT 1
            ''', (internal_movement_id,))
            operation_id = self._cr.fetchone()
            
            if not operation_id:
                continue

            self._cr.execute('''
                SELECT
                    id, transportation_order_no
                FROM
                    stock_picking    
                WHERE 
                    picking_from_warehouse_for_internal_order_id = %s
                AND
                    owner_id = %s
                LIMIT 1
            ''', (operation_id, owner_id))
            picking_id, id_order = self._cr.fetchone()
            
            
            self._cr.execute('''
                SELECT
                    iopm.warehouse_to_id, iop.location_to_id,
                    iop.warehouse_id, iop.location_from_id
                FROM
                    internal_operation AS iop
                JOIN
                    internal_operation_movement AS iopm ON (
                        iopm.operation_id = iop.id
                    )  
                WHERE 
                    iopm.id = %s
                LIMIT 1
            ''', (internal_movement_id,))
            dest_warehouse_id, dest_location_id,\
            src_warehouse_id, src_location_id = self._cr.fetchone()
            
            if route_id:
                self._cr.execute('''
                    SELECT
                        source_location_id, location_id,
                        license_plate, trailer, departure_time,
                        warehouse_id
                    FROM
                        stock_route    
                    WHERE 
                        id = %s
                    LIMIT 1
                ''', (route_id,))
                source_location_id, driver_id,\
                license_plate, trailer, route_datetime,\
                warehouse_id = self._cr.fetchone()
            else:
                source_location_id = src_location_id or False
                driver_id = False
                license_plate = ""
                trailer = ""
                route_datetime = False
                warehouse_id = src_warehouse_id
            
            warehouse = warehouse_env.browse(warehouse_id)
            
            out_despatch_id = False
            if created_out_despatch_ids:
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        despatch_advice    
                    WHERE 
                        id in %s
                    AND
                        owner_id = %s
                    AND
                        buyer_id = %s
                    AND
                        delivery_address_id = %s
                    AND
                        route_id = %s
                    AND
                        dest_warehouse_id = %s
                    AND
                        dest_location_id = %s
                    LIMIT 1
                ''', (
                    tuple(created_out_despatch_ids), owner_id or False,
                    partner_id or False, partner_shipping_id, route_id or None,
                    dest_warehouse_id or False, dest_location_id or False,
                ))
                sql_res = self._cr.fetchone()
                out_despatch_id = sql_res and sql_res[0] or False
            if not out_despatch_id:
                owner = owner_id and owner_env.browse(owner_id) or False
                
                name = doc_type_env.get_next_number_by_code(
                    'out.despatch', warehouse=warehouse, owner=owner
                )
                
                if driver_id:
                    self._cr.execute('''
                        SELECT
                            owner_id
                        FROM
                            stock_location    
                        WHERE 
                            id = %s
                        LIMIT 1
                    ''', (driver_id,))
                    sql_res = self._cr.fetchone()
                    carrier_id = sql_res and sql_res[0] or False
                else:
                    carrier_id = False
                
                out_despatch_vals = {
                    'despatch_type': 'out_atlas_wh',
                    'name': name,
                    'warehouse_id': warehouse_id,
                    'location_id': source_location_id,
                    'id_version': datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone('Europe/Vilnius')).timestamp(),
                    'route_id': route_id,
                    'truck_reg_plate': license_plate or "",
                    'trailer_reg_plate': trailer or "",
                    'issue_datetime': route_datetime,
                    'carrier_id': carrier_id,
                    'owner_id': owner_id,
                    'buyer_id': partner_id,
                    'receiver_id': partner_id,
#                     'one_time_buyer_id': one_time_buyer_id,
                    'delivery_address_id': partner_shipping_id,
                    'despatch_supplier_id': despatch_supplier_id,
                    'dest_warehouse_id': dest_warehouse_id,
                    'dest_location_id': dest_location_id,
                    'id_external': uuid.uuid1(),
                }
                out_despatch_id = despatch_env._create(out_despatch_vals)
                created_out_despatch_ids.append(out_despatch_id)
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    sale_order_line    
                WHERE 
                    order_id = %s
            ''', (sale.id,))
            
            sale_line_ids = [i[0] for i in self._cr.fetchall()]
            
            for sale_line_id in sale_line_ids:
                self._cr.execute('''
                    SELECT
                        product_uom_qty, product_uom,
                        product_code, product_id
                    FROM
                        sale_order_line    
                    WHERE 
                        id = %s
                    LIMIT 1
                ''', (sale_line_id,))
                qty, uom_id, product_code, product_id = self._cr.fetchone()
                
                
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        stock_move   
                    WHERE 
                        picking_id = %s
                    AND
                        invoice_line_id = (
                            SELECT
                                id
                            FROM
                                account_invoice_line
                            WHERE
                                automatically_created_sale_line_id = %s
                            LIMIT 1
                        )
                    LIMIT 1
                ''', (picking_id, sale_line_id))
                move_id, = self._cr.fetchone()
                
#                 line_id = False
#                 if created_lines_ids:
#                     self._cr.execute('''
#                         SELECT
#                             id, qty
#                         FROM
#                             account_invoice_container_line    
#                         WHERE 
#                             id in %s
#                         AND
#                             product_id = %s
#                         AND 
#                             out_despatch_id = %s
#                         AND
#                             id_order = %s
#                         LIMIT 1
#                     ''', (tuple(created_lines_ids),product_id, out_despatch_id))
#                     sql_res = self._cr.fetchone()
#                     if sql_res:
#                         line_id, line_qty = sql_res
#                 
#                 if line_id:
#                     self._cr.execute('''
#                         UPDATE
#                             account_invoice_container_line 
#                         SET
#                             qty = %s
#                         WHERE 
#                             id = %s
#                     ''', (line_qty + qty, line_id,))
#                 else:
                line_vals = {
                    'qty': qty,
                    'uom_id': uom_id,
                    'product_code': product_code,
                    'product_id': product_id,
                    'out_despatch_id': out_despatch_id,
                    'id_order': id_order,
                    'id_order_line': str(move_id),
                }
#                 created_lines_ids.append(container_line_env._create(line_vals))
                container_line_env._create(line_vals)
            
        return True
    
    
    #Lygtais nebenaudojamas
    @api.multi
    def do_out_despatch(self):
        self._cr.execute('''
            SELECT
                id
            FROM
                sale_order    
            WHERE 
                id in %s
            AND
                linked_with_despatch = true
            LIMIT 1
        ''', (tuple(self.ids),))
        linked_with_despatch_sale_ids = [i[0] for i in self._cr.fetchall()]
        
        self._cr.execute('''
            SELECT
                id
            FROM
                sale_order    
            WHERE 
                id in %s
            AND
                internal_movement_id IS NOT NULL
            LIMIT 1
        ''', (tuple(self.ids),))
        movement_sale_ids = [i[0] for i in self._cr.fetchall()]
        
        self.browse(linked_with_despatch_sale_ids).do_out_despatch_linked_with_despatch()
        self.browse(movement_sale_ids).do_out_movement_despatch()
        
        return True
        
    @api.multi
    def try_set_invoiced_state(self):
        for sale in self:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    sale_order_line    
                WHERE 
                    order_id = %s
                    AND product_uom_qty > qty_invoiced
                LIMIT 1
            ''', (sale.id,))
            sql_res = self._cr.fetchone()
            if not sql_res:
                self._cr.execute('''
                    UPDATE
                        sale_order
                    SET
                        state = 'invoiced'
                    WHERE 
                        id = %s
                ''', (sale.id,))
        return True
    
    @api.multi
    def actions_after_creating_task(self):
        res = super(SaleOrder, self).actions_after_creating_task()
        self.link_with_despatch()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    container_line_ids = fields.One2many(
        'account.invoice.container.line', 'sale_order_line_id', "Container Lines"
    )
    invoice_group_index = fields.Char("Invoice Group Index", index=True)
    waybill_group_index = fields.Char("Waybill Group Index", index=True)
    
    @api.multi
    def write(self, vals):
        if 'qty_invoiced' not in vals.keys():
            vals['qty_invoiced'] = 0.0
        return super(SaleOrderLine, self).write(vals)