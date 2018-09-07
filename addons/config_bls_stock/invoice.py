# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields, _
from odoo.api import Environment
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

# from PIL import Image
import requests
from io import BytesIO
import base64


import datetime
import time


# import json
# import html
# import xml.dom.minidom

import threading
import json
# import traceback

import os
from lxml import etree

from .import_schemas.models.invoice.schemas import InvoiceSchema
from .import_schemas.models.waybill.schemas import WaybillSchema
# from .import_schemas.models.despatch_advice.schemas import DespatchAdviceSchema
inv_schema = InvoiceSchema()
wb_schema = WaybillSchema()
# da_schema = DespatchAdviceSchema()

import logging
_logger = logging.getLogger(__name__)

_XSDS_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'import_schemas', 'xsd'
)


class AccountInvoiceContainerLine(models.Model):
    _inherit = 'account.invoice.container.line'
    _rec_name = 'id_despatch_line'
    
    despatch_advice_id = fields.Many2one('despatch.advice', "Despatch Advice", index=True)
    id_despatch_line = fields.Char("Descpatch Line ID")
#     quantity = fields.Float("Quantity", digits=dp.get_precision('Product Unit of Measure'))
    uom_id = fields.Many2one('product.uom', "UoM")
    id_order = fields.Char("Order ID", readonly=True, index=True)
    id_order_line = fields.Char("Order Line ID", readonly=True, index=True)
    order_id = fields.Many2one('transportation.order', "Order", index=True)
    order_line_id = fields.Many2one('transportation.order.line', "Order Line", index=True)
#     product_code = fields.Char("Product Code")
    seller_product_code = fields.Char("Seller Product Code")
    buyer_product_code = fields.Char("Buyer Product Code")
    manufacturer_product_code = fields.Char("Seller Product Code")
    classification_code = fields.Char("Classification Code")
    
    lot_ids = fields.Many2many(
        'stock.production.lot', 'container_line_lot_rel',
        'container_line_id', 'lot_id', string='Lots'
    )
    certificate_ids = fields.Many2many(
        'product.certificate', 'container_line_certificate_rel',
        'container_line_id', 'certificate_id', string='Certificates'
    )

    ordered_qty = fields.Float("Ordered Quantity", digits=dp.get_precision('Product Unit of Measure'))
#     sale_order_id = fields.Many2one('sale.order', "Transportation Task")
    sale_order_line_id = fields.Many2one('sale.order.line', "Transportation Task Line", index=True)
    
    lots_str = fields.Char("Lots")
    certificates_str = fields.Char("Certificates")
    barcode_str = fields.Char("Barcode")
    

#     id_order_int = fields.Integer("Order ID", readonly=True, index=True)
#     id_order_line_int = fields.Integer("Order Line ID", readonly=True, index=True)
    product_id = fields.Many2one(
        'product.product', 'Product', index=True
    )
    out_despatch_id = fields.Many2one('despatch.advice', "Out Despatch Advice", index=True)
    order_name = fields.Char("Order Name", size=32, index=True) #Toks labiau laikinas sprendimas, kad butu galima testuotis su senais duomenimis, kol dar UUID nebuvo

    @api.model
    def form_vals_from_json(self, line_data):
        uom_env = self.env['product.uom']
        product_env = self.env['product.product']
        lot_env = self.env['stock.production.lot']
        cert_env = self.env['product.certificate']
        container_env = self.env['account.invoice.container']
        barcode_env = self.env['product.barcode']
        
        res_list = []
        
        uom = line_data.get('_ext_attributes', False)\
            and line_data['_ext_attributes'].get('DeliveredQuantity', False)\
            and line_data['_ext_attributes']['DeliveredQuantity']['unitCode'] or ''
        
        if uom:    
            if uom in ['V', 'GAB']:
                uom = 'Unit(s)'
            elif uom == 'K':
                uom = 'kg'
                
            self._cr.execute('''
                    SELECT
                        id
                    FROM
                        product_uom
                    WHERE name = %s
                    LIMIT 1
                ''', (uom,))
            sql_res = self._cr.fetchone()
            uom_id = sql_res and sql_res[0] or False
            if not uom_id:
                uom_id = uom_env.create({
                    'name': uom,
                    'uom_type': 'reference',
                    'category_id': self.env.ref('config_bls_stock.uom_categ_bls', False)[0].id,
                }).id
        else:
            uom_id = False
        
        order_ref_data = line_data.get('OrderLineReference', False)
        order_vals = {}
        if order_ref_data:
            # order_ref_data2 - čia skubus pataisymas, po to kai pakeitė schemas kad OrderLineReference gali būti multi
            # nespėjau išsiaiškint, kas tokiu atveju čia turi keistis.
            
            order_ref_data2 = order_ref_data[0]
            id_order_line = order_ref_data2.get('LineID', False)
            order_name = order_ref_data2.get('OrderReference', False) and order_ref_data2['OrderReference']['ID']
            id_order = order_ref_data2.get('OrderReference', False) and order_ref_data2['OrderReference'].get('UUID', order_name)
            order_vals['id_order_line'] = id_order_line
            order_vals['id_order'] = id_order
            order_vals['order_name'] = order_name
#             try:
#                 id_order_line_int = int(id_order_line)
#             except:
#                 id_order_line_int = False
#             try:
#                 id_order_int = int(id_order)
#             except:
#                 id_order_int = False
#             order_vals['id_order_line_int'] = id_order_line_int
#             order_vals['id_order_int'] = id_order_int
#             if order_vals['id_order']:
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         transportation_order
#                     WHERE id_external = %s
#                     LIMIT 1
#                 ''', (id_order,))
#                 sql_res = self._cr.fetchone()
#                 order_vals['order_id'] = sql_res and sql_res[0] or False
#                 if order_vals['order_id'] and order_vals['id_order_line']:
#                     self._cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             transportation_order_line
#                         WHERE id_line = %s
#                             AND transportation_order_id = %s
#                         LIMIT 1
#                     ''', (id_order_line, order_vals['order_id'],))
#                     sql_res = self._cr.fetchone()
#                     order_vals['order_line_id'] = sql_res and sql_res[0] or False

        item_data = line_data.get('Item', False)
                    
        id_manifacturer = item_data.get('ManufacturersItemIdentification', False)\
            and item_data['ManufacturersItemIdentification']['ID'] or ''
        
#         default_code = item_data.get('StandardItemIdentification', False)\
#             and item_data['StandardItemIdentification']['ID'] or ''
#         
#         id_seller = item_data.get('SellersItemIdentification', False)\
#             and item_data['SellersItemIdentification']['ID'] or ''
#             
#         id_buyer = item_data.get('BuyersItemIdentification', False)\
#             and item_data['BuyersItemIdentification']['ID'] or ''

        barcode = False
        default_code = False
        id_seller = False
        standart_item_identification_data = item_data.get('StandardItemIdentification', False)
        
        if standart_item_identification_data:
            barcode = standart_item_identification_data.get('BarcodeSymbologyID', '')
            default_code = standart_item_identification_data['ID'] or ''
        
        seller_item_data = item_data.get('SellersItemIdentification', False)
        if seller_item_data:
            id_seller = seller_item_data.get('ID', '')
            if not barcode:
                barcode = seller_item_data.get('BarcodeSymbologyID', '')
            if not default_code:
                default_code = id_seller
                
        if not default_code:
            additional_ident_data = item_data.get('AdditionalItemIdentification', False)\
                and item_data.get('AdditionalItemIdentification', False)[0] or False
            if additional_ident_data:
                default_code = additional_ident_data.get('ID', '')
                if not barcode:
                    barcode = additional_ident_data.get('BarcodeSymbologyID', '')

        id_buyer = item_data.get('BuyersItemIdentification', False)\
            and item_data['BuyersItemIdentification']['ID'] or ''
            
        if not default_code:
            raise UserError(
                _('Can not find product code in data: %s') % (item_data)
            )
            
        classification_code = item_data.get('CommodityClassification', False)\
            and item_data['CommodityClassification'][0]['ItemClassificationCode'] or ''
            
#         name = item_data.get('Name', '')
        name = item_data.get('Description', '')
        
        self._cr.execute('''
            SELECT
                id
            FROM
                product_product
            WHERE default_code = %s
            LIMIT 1
        ''', (default_code,))
        sql_res = self._cr.fetchone()
        product_id = sql_res and sql_res[0] or False
        
        if not product_id:
            prod_vals = product_env.default_get(product_env._fields)
            prod_vals['name'] = name
            prod_vals['default_code'] = default_code
            if uom_id:
                prod_vals['uom_id'] = uom_id
                prod_vals['uom_po_id'] = uom_id
            
            product = product_env.create(prod_vals)
            product_id = product.id
            
        if barcode:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    product_barcode
                WHERE barcode = %s
                    AND product_id = %s
                LIMIT 1
            ''', (barcode, product_id))
            sql_res = self._cr.fetchone()
            barcode_id = sql_res and sql_res[0] or False
            
            if not barcode_id:
                barcode_env.create({
                    'barcode': barcode,
                    'product_id': product_id,
            })
        
        expiry_date = False    
        lots_vals = []
        certificates_vals = []
        
        item_instance_data = item_data.get('ItemInstance', False)
        if item_instance_data:
            expiry_date = item_instance_data.get('BestBeforeDate', False)
            min_lot_exp_date = False
            
            
            #*** Kad nereiktu stumdyti kodo, perdaryta taip. pradzioj tiketasi, kad gali buti keli LOT'ai ***
            
#             for lot_data in item_instance_data.get('LotIdentification', False):
            if item_instance_data.get('LotIdentification', False):

                lot_data = item_instance_data.get('LotIdentification', False)
#                 if lot_data and lot_data.get('LotNumberID', False):
                if lot_data.get('LotNumberID', False):
                    lot_number = lot_data['LotNumberID']
                    lot_exp_date = lot_data.get('ExpiryDate', False)
                    
                    if not min_lot_exp_date or min_lot_exp_date > lot_exp_date:
                        min_lot_exp_date = lot_exp_date

                    
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            stock_production_lot
                        WHERE name = %s
                            AND product_id = %s
                        LIMIT 1
                    ''', (lot_number,product_id))
                    sql_res = self._cr.fetchone()
                    lot_id = sql_res and sql_res[0]
                    if not lot_id:
                        lot_id = lot_env.create({
                            'name': lot_number,
                            'product_id': product_id,
                            'expiry_date': lot_exp_date,
                        }).id
                    elif lot_exp_date:
                        self._cr.execute('''
                            UPDATE
                                stock_production_lot
                            SET
                                expiry_date = %s
                            WHERE id = %s
                        ''', (lot_exp_date,lot_id))
                    if lot_id:
                        lots_vals.append((4, lot_id))
        
#             if not expiry_date:
#                 expiry_date = min_lot_exp_date or False
        
        if item_data.get('Certificate', False):

            for certificate_data in item_data['Certificate']:
                id_certificate = certificate_data['ID']
                
                if id_certificate == '-':
                    continue
                
                ref_doc_data = certificate_data.get('DocumentReference', False)
                cert_validity_data = ref_doc_data and ref_doc_data.get('ValidityPeriod', False)
    
                cert_vals = {
                    'type': certificate_data.get('CertificateType', False),
                    'issued_by': certificate_data.get('IssuerParty', False)\
                        and certificate_data['IssuerParty'].get('PartyName', False)\
                        and certificate_data['IssuerParty']['PartyName'].get('Name', False) or "",
                    'issue_date': ref_doc_data and ref_doc_data.get('IssueDate', False) or False,
                    'valid_from': cert_validity_data and cert_validity_data.get('StartDate', False) or False,
                    'valid_to': cert_validity_data and cert_validity_data.get('EndDate', False) or False,
                    'product_id': product_id,
                    'name': id_certificate,
                }
                
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        product_certificate
                    WHERE name = %s
                        AND product_id = %s
                    LIMIT 1
                ''', (id_certificate,product_id))
                sql_res = self._cr.fetchone()
                
                cert_id = sql_res and sql_res[0]
                
                if not cert_id:
#                 if cert_id:
#                     cert = cert_env.browse(cert_id)
#                     cert.write(cert_vals)
#                 else:
                    cert_id = cert_env.create(cert_vals).id
                    
                certificates_vals.append((4, cert_id))
            
        shipment_data = line_data.get('Shipment', {})
        
        total_qty = line_data.get('DeliveredQuantity', 0.0)
        containers_qty = 0.0
        check_qty = True

        for consignment_data in shipment_data.get('Consignment', [False]):
            container_id = False
            if consignment_data:
                id_container = consignment_data.get('ID', False)
                qty = consignment_data.get('ConsignmentQuantity', 0.0)
                containers_qty += qty

                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        account_invoice_container
                    WHERE id_external = %s
                    LIMIT 1
                ''', (id_container,))
                sql_res = self._cr.fetchone()
                if sql_res:
                    container_id = sql_res[0]
                else:
                    container_id = container_env.create({
                        'id_external': id_container,
                        'container_no': id_container,
                    }).id
            else:
                qty = total_qty
                check_qty = False

            res = {
                'id_despatch_line': line_data.get('ID', False),
                'qty': qty,
                'uom_id': uom_id,
                'product_code': default_code,
                'seller_product_code': id_seller,
                'buyer_product_code': id_buyer,
                'manufacturer_product_code': id_manifacturer,
                'classification_code': classification_code,
                'product_id': product_id,
                'expiry_date': expiry_date,
                'lot_ids': lots_vals,
                'certificate_ids': certificates_vals,
                'container_id': container_id,
                'barcode_str': barcode or False,
            }
            res.update(order_vals)
            res_list.append(res)
        
#         if shipment_data.get('Consignment', False):
#             for consignment_data in shipment_data['Consignment']:
#                 id_container = consignment_data.get('ID', False)
#                 if id_container:
#                     self._cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             account_invoice_container
#                         WHERE id_external = %s
#                         LIMIT 1
#                     ''', (id_container,))
#                     sql_res = self._cr.fetchone()
#                     if sql_res:
#                         container_id = sql_res[0]
#                     else:
#                         container_id = container_env.create({
#                             'id_external': id_container,
#                             'container_no': id_container,
#                         }).id
# 
#         res = {
#             'id_despatch_line': line_data.get('ID', False),
#             'qty': line_data.get('DeliveredQuantity', 0.0),
#             'uom_id': uom_id,
#             'product_code': default_code,
#             'seller_product_code': id_seller,
#             'buyer_product_code': id_buyer,
#             'manufacturer_product_code': id_manifacturer,
#             'classification_code': classification_code,
#             'product_id': product_id,
#             'expiry_date': expiry_date,
#             'lot_ids': lots_vals,
#             'certificate_ids': certificates_vals,
#             'container_id': container_id,
#             'barcode_str': barcode or False,
#         }
        
#         res.update(order_vals)
#         return res
        if check_qty and abs(total_qty - containers_qty) > 0.000001:
            raise UserError(
                _('Line with product code %s has wrong quantities. Line declare that quantity is %.6f, but per all containers %.6f quantity found') % (
                    default_code, total_qty, containers_qty
                )
            )

        return res_list
    
    @api.multi
    def link_to_order_and_order_line(self):
        order_env = self.env['transportation.order']
#         despatch_advices = self.env['despatch.advice']
        order_ids = []
        for container_line in self:
#             container_line_read = container_line.read(['id_order', 'id_order_line', 'despatch_advice_id'])[0]
            self._cr.execute('''
                SELECT
                    id_order, id_order_line, order_name
                FROM
                    account_invoice_container_line
                WHERE id = %s
                LIMIT 1
            ''', (container_line.id,))
            id_order, id_order_line, order_name = self._cr.fetchone()
            
            link_vals = {}
            
            if id_order:
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        transportation_order
                    WHERE id_external = %s
                    LIMIT 1
                ''', (id_order,))
                sql_res = self._cr.fetchone()
                if not sql_res:
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            transportation_order
                        WHERE name = %s
                        LIMIT 1
                    ''', (order_name,))
                    sql_res = self._cr.fetchone()
            else:
                continue
            
            order_id = sql_res and sql_res[0] or False
            if order_id:
                link_vals['order_id'] = order_id
                order_ids.append(order_id)
                
                if id_order_line:
                    if '.' not in id_order_line:
                        self._cr.execute('''
                            SELECT
                                id, quantity
                            FROM
                                transportation_order_line
                            WHERE id_line = %s
                                AND transportation_order_id = %s
                            LIMIT 1
                        ''', (id_order_line, order_id,))
                        sql_res = self._cr.fetchone()
                    else:
                        self._cr.execute('''
                            SELECT
                                subline.id, subline.quantity
                            FROM
                                transportation_order_line as subline
                            LEFT JOIN transportation_order_line as mainline on (
                                subline.parent_line_id = mainline.id
                            )
                            WHERE subline.id_line = %s
                                AND mainline.transportation_order_id = %s
                            LIMIT 1
                        ''', (id_order_line, order_id,))
                        sql_res = self._cr.fetchone()
                else:
                    sql_res = False
                    
                if sql_res:
                    link_vals['order_line_id'] = sql_res[0]
                    link_vals['ordered_qty'] = sql_res[1]


#             if id_order:
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         transportation_order
#                     WHERE id_external = %s
#                     LIMIT 1
#                 ''', (id_order,))
#                 sql_res = self._cr.fetchone()
#                 if sql_res and sql_res[0]:
#                     link_vals['order_id'] = sql_res[0]
#                     order_ids.append(sql_res[0])
#                 if link_vals.get('order_id', False) and id_order_line:
#                     if '.' not in id_order_line:
#                         self._cr.execute('''
#                             SELECT
#                                 id, quantity
#                             FROM
#                                 transportation_order_line
#                             WHERE id_line = %s
#                                 AND transportation_order_id = %s
#                             LIMIT 1
#                         ''', (id_order_line, link_vals['order_id'],))
#                         sql_res = self._cr.fetchone()
#                     else:
#                         self._cr.execute('''
#                             SELECT
#                                 subline.id, subline.quantity
#                             FROM
#                                 transportation_order_line as subline
#                             LEFT JOIN transportation_order_line as mainline on (
#                                 subline.parent_line_id = mainline.id
#                             )
#                             WHERE subline.id_line = %s
#                                 AND mainline.transportation_order_id = %s
#                             LIMIT 1
#                         ''', (id_order_line, link_vals['order_id'],))
#                         sql_res = self._cr.fetchone()
#                     
#                     if sql_res:
#                         link_vals['order_line_id'] = sql_res[0]
#                         link_vals['ordered_qty'] = sql_res[1]
                    
            if link_vals:
#                 container_line.write(link_vals)
                sql_set_part_list = []
                for link_vals_field in link_vals.keys():
                    field_val = link_vals[link_vals_field]
                    if type(field_val) == str:
                        field_val = "'" + field_val + "'"
                
                    sql_set_part_list.append("%s = %s" % (link_vals_field, field_val))
                        
                sql_set_part = ", ".join(sql_set_part_list)
                
                sql_sentence = """
                    UPDATE account_invoice_container_line
                    SET """ + sql_set_part + """WHERE id = %s""" % (container_line.id)
                    
                self._cr.execute(sql_sentence)


#                 desp_adv_id_tuple = container_line_read['despatch_advice_id']
#                 despatch_advices += desp_adv_id_tuple and desp_adv_id_tuple[0]
        
        if order_ids:
            order_ids = list(set(order_ids))
            orders = order_env.browse(order_ids)
            orders.update_vals_from_despatch()
#         despatch_advices.create_sale_order()
        return True
    
    @api.multi
    def form_lot_and_certificate_strs(self):
        for conatiner_line in self:
            lot_strs = []
            cert_strs = []
            
            for lot in conatiner_line.lot_ids:
                lot_strs.append(lot.name)
            for cert in conatiner_line.certificate_ids:
                cert_strs.append(cert.name)
                
            conatiner_line.write({
                'lots_str': ', '.join(lot_strs),
                'certificates_str': ', '.join(cert_strs),
            })
        return True
    
    
    @api.model
    def create(self, vals):
        res = super(AccountInvoiceContainerLine, self).create(vals)
#         if not (vals.get('id_order_int', False) or vals.get('id_order_line_int', False)):
#             res.calc_int_identificators()
        
    #------- Po eilutes sukurimo sulinkinamos partijos su sertifikatais
        for cert in res.certificate_ids:
            cert_lot_ids = [l.id for l in cert.lot_ids]
            write_lot_ids = []
            for lot in res.lot_ids:
                if lot.id not in cert_lot_ids:
                    write_lot_ids.append((4,lot.id))
            if write_lot_ids:
                cert.write({
                    'lot_ids': write_lot_ids,
                })
        res.form_lot_and_certificate_strs()
        
        return res
    
#     @api.multi
#     def calc_int_identificators(self):
#         self.ensure_one()
#         
#         self._cr.execute('''
#             SELECT
#                 id_order, id_order_line
#             FROM
#                 account_invoice_container_line
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         id_order, id_order_line = self._cr.fetchone()
#         
#         sql_values_to_set_list = []
#         
#         if id_order and id_order[0] != '0':
#             try:
#                 sql_values_to_set_list.append(
#                     "id_order_int = %s" % (int(id_order))
#                 )
#             except:
#                 pass
#             
#         if id_order_line and id_order_line[0] != '0':
#             try:
#                 sql_values_to_set_list.append(
#                     "id_order_line_int = %s" % (int(id_order_line))
#                 )
#             except:
#                 pass
#             
#         if sql_values_to_set_list:
#             self._cr.execute('''
#                 UPDATE
#                     account_invoice_container_line
#                 SET %s
#                 WHERE id = %s
#             ''' % (', '.join(sql_values_to_set_list), self.id))
#             
#         return True

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
#     @api.model
#     def get_sending_type_selection(self):
#         transp_order_doc_env = self.env['transportation.order.document']
#         return transp_order_doc_env.get_sending_type_selection()
    
    @api.model
    def get_document_lines_order_selection(self):
        return self.env['transportation.order.document'].get_document_lines_order_selection()
    
    @api.model
    def get_delivery_terms_selection(self):
        return self.env['transportation.order'].get_delivery_terms_selection()
    
    merge_code = fields.Char("Merge Code", readonly=True, index=True)
    one_time_partner_id = fields.Many2one('transportation.order.partner', "One Time Partner")
    
#     sending_type = fields.Selection(get_sending_type_selection, "Sending Type")
    document_form_id = fields.Many2one('document.form', "Document Form")
    print_copies = fields.Integer("Print Copies", default=1)
    delivery_conditions = fields.Char("Delivery Conditions")
    generated_in_atlas = fields.Boolean("Generated in ATLAS", default=False)
    seller_partner_id = fields.Many2one('res.partner', "Seller Partner")
    printing_datetime = fields.Datetime("Printing Date/Time")
    carrier_id = fields.Many2one('res.partner', "Carrier")
    driver_id = fields.Many2one('stock.location', "Driver")
    document_package_no = fields.Char("Document Package No.")
    despatch_address_id = fields.Many2one('res.partner', "Despatch Address")
#     customer_despatch_intermediate_id = fields.Many2one(
#         'stock.route.integration.intermediate' ,"Customer Despatch Intermediate", readonly=True
#     )
    owner_partner_id = fields.Many2one('res.partner', "Owner Partner")
    need_after_create_actions = fields.Boolean("After Create Actions are Required", default=False)
    edit_mode = fields.Boolean("Edit Mode", default=False)
    name_generated_in_atlas = fields.Boolean("Name was generated in ATLAS", default=False, readonly=True)
    document_lines_order = fields.Selection(
        get_document_lines_order_selection, "Document Lines Selection", readonly=True
    )
    delivery_terms = fields.Selection(get_delivery_terms_selection, "Delivery Terms")
    estimated_delivery_date = fields.Date("Estimated Delivery Date")
    id_external = fields.Char("External ID", size=64, readonly=True)
    cmr_document_id = fields.Many2one('account.invoice', 'CMR', readonly=True, index=True)
    
    sibling_document_ids = fields.Many2many(
        'account.invoice', 'invoice_sibling_invoice_rel',
        'invoice_id', 'invoice_sibling_id', string='Sibling Documents'
    )
    cmr_status = fields.Selection([
        ('separate','Separate'),
        ('joined','Joined')
    ], 'CMR doc. Type', default='joined')
    out_picking_created = fields.Boolean("Out Picking was Created", default=False)

    @api.multi
    def group_invoices_for_cmr(self):
        # Metodas sugrūpuojantis dokumentus į atskirus CMR.

        grouped_documents = {}
        if self:
            group_sql = '''
                SELECT
                    id,
                    route_number,
                    partner_shipping_id,
                    owner_id,
                    cmr_status
                FROM
                    account_invoice
                WHERE
                    id in %s
            '''
            group_where = (tuple(self.ids),)
            self.env.cr.execute(group_sql, group_where)
            documents = self.env.cr.fetchall()
            for document in documents:
                if document[4] == 'joined':
                    group_key = (document[1], document[2], document[3])
                else:
                    group_key = (document[1], document[2], document[3], document[0])

                if group_key not in grouped_documents:
                    grouped_documents[group_key] = []
                grouped_documents[group_key].append(document[0])
        return [self.env['account.invoice'].browse(doc_ids) for doc_ids in grouped_documents.values()]

    @api.multi
    def create_cmr_documents(self):
        cmr_documents = self.env['account.invoice']
        for grouped_invoices in self.group_invoices_for_cmr():
            cmr_documents += grouped_invoices.create_cmr_document()
        return cmr_documents

    @api.multi
    def get_vals_for_cmr_documents(self):
        route_id = False
        if self:
            cmr_vals_sql = '''
                SELECT
                    ai.owner_id,
                    ai.posid,
                    ai.partner_id,
                    ai.partner_shipping_id,
                    max(srir.route_id)
                FROM
                    account_invoice ai
                    JOIN stock_route_invoice_rel srir on (srir.invoice_id = ai.id)
                WHERE
                    ai.id in %s
                GROUP BY
                    ai.owner_id,
                    ai.posid,
                    ai.partner_id,
                    ai.partner_shipping_id
            '''
            cmr_vals_where = (tuple(self.ids),)
            self.env.cr.execute(cmr_vals_sql, cmr_vals_where)
            result_values = self.env.cr.fetchall()
            if len(result_values) != 1:
                raise UserError('KLAIDA su GRUPAVIMu ' + str(result_values))
            result_values = result_values[0]
            values = {
                'owner_id': result_values[0],
                'state': 'draft',
                'partner_id': result_values[2],
                'posid': result_values[1],
                'partner_shipping_id': result_values[3]
            }
            warehouse = self.env.user.get_current_warehouses()
            values['name'] = self.env.user.company_id.cmr_document_sequence_id.next_by_id()
            values['picking_warehouse_id'] = warehouse.id
            values['document_operation_type'] = 'cmr'
            values['category'] = 'cmr'
            values['document_form_id'] = self.env.ref('config_bls_stock.cmr_document_data').id
            values['sending_type'] = 'paper'
            values['print_copies'] = 1
            values['date_invoice'] = time.strftime('%Y-%m-%d')
            route_id = result_values[4]
        else:
            values = {}
        return values, route_id

    @api.multi
    def create_cmr_document(self):
        cmr_document_vals, route_id = self.get_vals_for_cmr_documents()
        cmr_documents = self.get_all_related_cmr_documents()
        if cmr_documents and len(cmr_documents) == 1 and cmr_documents[0]:
            cmr = self.browse(cmr_documents)
            cmr.write(cmr_document_vals)
            cmr.update_line_count()
            cmr.update_amounts()
            return cmr
        if cmr_documents and len(cmr_documents) == 1 and not cmr_documents[0]:
            cmr = self.create(cmr_document_vals)
            route = self.env['stock.route'].browse(route_id)
            route.write({'invoice_ids': [(4, cmr.id)]})
            self.write({'cmr_document_id': cmr.id})
            route.update_last_route_info_in_documents()
            for line in self.get_lines():
                copied_line = line.copy({
                    'invoice_id': cmr.id,
                    'sale_order_line_ids': [],
                    'external_invoice_line_id': 'cmr_' + (line.external_invoice_line_id or str(line.id))
                })
                copied_line.set_version()
            cmr.update_line_count()
            cmr.update_amounts()

        return cmr

    @api.multi
    def get_all_related_cmr_documents(self):
        cmr_document_ids = []
        if self:
            cmr_sql = '''
                SELECT
                    cmr_document_id
                FROM
                    account_invoice
                WHERE
                    id in %s
                GROUP BY
                    cmr_document_id
            '''
            cmr_where = (tuple(self.ids),)
            self.env.cr.execute(cmr_sql, cmr_where)
            cmr_document_ids = [cmr_document_id[0] for cmr_document_id in self.env.cr.fetchall()]
        return cmr_document_ids

    @api.multi
    def get_documents_to_other_coutries(self):
        # Formuojant CMR reikia atrinkti tik tuos dokumentus, kurie keliauja į kitą šalį.
        # Šis metodas atfiltruoja tokius dokumentus.

        if self:
            codes = self.env.user.company_id.get_country_codes()
            codes.append('')
            filter_sql = '''
                SELECT
                    ai.id
                FROM
                    account_invoice ai
                    JOIN res_partner rp on (rp.id = ai.partner_id)
                    LEFT JOIN res_country rc on (rc.id = rp.country_id) 
                WHERE
                    ai.id in %s
                    AND rc.code not in %s
                    AND rc.code is not null
                    AND ai.category != 'cmr'
            '''
            filter_where = (tuple(self.ids), tuple(codes))
            print(filter_sql%filter_where)
            self.env.cr.execute(filter_sql, filter_where)
            foreign_invoice_ids = [invoice_id[0] for invoice_id in self.env.cr.fetchall()]
            if foreign_invoice_ids:
                return self.browse(foreign_invoice_ids)
        return self.env['account.invoice']
    
    @api.multi
    def create_stock_pickings(self):
        route_env = self.env['stock.route']
        stock_move_env = self.env['stock.move']
        picking_env = self.env['stock.picking']
        
        created_pickings = self.env['stock.picking']
        
        pick_vals = picking_env.default_get(picking_env._fields)
#         warehouse_id = self.env.user.get_default_warehouse()
#         if not warehouse_id:
            
        warehouse_id =  self.env.user.get_main_warehouse_id()
        
#         if not warehouse_id:
#             raise UserError(
#                 _('Please select warehouse you are working in')
#             )
        
        self._cr.execute('''
            SELECT
                id
            FROM
                stock_picking_type
            WHERE code = 'outgoing'
                AND warehouse_id = %s
            LIMIT 1
        ''', (warehouse_id,))
        sql_res = self._cr.fetchone()
        if sql_res:
            type_record_id, = sql_res
        else:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_picking_type
                WHERE code = 'outgoing'
                LIMIT 1
            ''')
            type_record_id, = sql_res
            
#         type_record = stock_picking_type_env.search([
#             ('code','=','outgoing'),
#             ('warehouse_id','=',warehouse_id)
#         ], limit=1)
#         if not type_record:
#             type_record = stock_picking_type_env.search([
#                 ('code','=','outgoing')
#             ], limit=1)
            
        self._cr.execute('''
            SELECT
                asn_location_id
            FROM
                stock_warehouse
            WHERE id = %s
            LIMIT 1
        ''', (warehouse_id,))
        asn_location_id, = self._cr.fetchone()
        if not asn_location_id:
            raise UserError(
                _('Your warehouse does not have filled ASN location field.')
            )
            
        client_location_id = route_env.get_client_location()
        if not client_location_id:
            raise UserError(
                _('Can not find client location.')
            )
        total = len(self)
        i = 0
        created_pickings_counter = 0
        invoice_to_skip_ids = []
        
        for invoice in self:
            i += 1
#             #Laikinas sprendimo būdas, nes kolkas waybill'į išrašinėja visada
#             self._cr.execute('''
#                 SELECT
#                     category
#                 FROM
#                     account_invoice
#                 WHERE
#                     id = %s
#                 LIMIT 1
#             ''', (invoice.id,))
#             categ, = self._cr.fetchone()
#             if categ != 'waybill':
#                 continue
            if invoice.id in invoice_to_skip_ids:
                self._cr.execute('''
                    SELECT
                        name
                    FROM
                        account_invoice
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (invoice.id,))
                inv_name, = self._cr.fetchone()
                
                _logger.info(
                    'Document sibling already has picking, so picking create for document %s is skipped.' % (inv_name, )
                )
                continue
            
            self._cr.execute('''
                SELECT
                    invoice_sibling_id
                FROM
                    invoice_sibling_invoice_rel
                WHERE
                    invoice_id = %s
                ORDER BY
                    invoice_sibling_id
            ''', (invoice.id,))
            sibling_doc_ids = [i[0] for i in self._cr.fetchall()]
            
            invoice_to_skip_ids.append(invoice.id)
            invoice_to_skip_ids += sibling_doc_ids
            
            
            this_picking_vals = pick_vals.copy()
            this_picking_vals.update({
                'location_id': asn_location_id,
                'location_dest_id': client_location_id,
                'invoice_id': invoice.id,
                'picking_type_id': type_record_id,
            })
            
            moves_vals = []
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    account_invoice_line
                WHERE invoice_id = %s
            ''', (invoice.id,))
#             inv_line_ids = [i[0] for i in self._cr.fetchall()]
            for inv_line_id, in self._cr.fetchall():
                self._cr.execute('''
                    SELECT
                        quantity, product_id
                    FROM
                        account_invoice_line
                    WHERE id = %s
                ''', (inv_line_id,))
                qty, product_id = self._cr.fetchone()
                
                
                
                line_vals = {
                    'product_uom_qty': qty,
                    'product_uos_qty': qty,
                    'location_id': asn_location_id,
                    'location_dest_id': client_location_id,
                    'product_id': product_id or False,
                }
                temp_move = stock_move_env.new(line_vals)
                temp_move.onchange_product_id()
                line_vals.update(temp_move._convert_to_write(temp_move._cache))
                stock_move_env.create(line_vals)
                
                moves_vals.append((0,0,line_vals))

            if moves_vals:
                this_picking_vals['move_lines'] = moves_vals
                
            created_pickings += picking_env.with_context(tracking_disable=True, recompute=False).create(this_picking_vals)
            created_pickings_counter += 1
            
            self._cr.commit()
            _logger.info('Created pickings %s / %s' % (str(i), str(int(total))))
            
            
            self._cr.execute('''
                UPDATE
                    account_invoice
                SET
                    out_picking_created = true
                WHERE
                    id in %s
            ''', (tuple(sibling_doc_ids + [invoice.id]),))
            
        created_pickings.with_context(qty_sql_write=True).action_confirm_bls()   
        
        _logger.info('\n Total %s pickings were created!' % (created_pickings_counter))
        
        return created_pickings
    
    @api.multi
    def get_print_document_invoice_type(self):
        self.ensure_one()
#         document_form = self.document_form_id and self.document_form_id.code or False
#         if not document_form:
#             if self.category == 'invoice':
#                 document_form = 'Invoice'
# #             elif self.category == 'picking':
#             else :
#                 document_form = 'SHIPINVOICE'
#         return document_form
        
        self._cr.execute('''
            SELECT
                inv.category, df.code
            FROM
                account_invoice AS inv
            LEFT JOIN 
                document_form AS df ON (
                    inv.document_form_id = df.id
                )
            WHERE inv.id = %s
            LIMIT 1
        ''', (self.id,))
        category, document_form = self._cr.fetchone()
        
        if not document_form:
            if category == 'invoice':
                document_form = 'Invoice'
            else :
                document_form = 'SHIPINVOICE'
                
        return document_form
        

    
    @api.multi
    def get_print_document_invoice_data(self):
        user = self.env.user
        self.ensure_one()
        
        self._cr.execute('''
            SELECT
                name, date_invoice, create_date,
                amount_total, amount_untaxed,
                payment_term_date, document_create_datetime
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        name, date_invoice, create_date, amount_total,\
        amount_untaxed, payment_term_date,\
        document_create_datetime  = self._cr.fetchone()
        
        create_datetime = document_create_datetime or create_date
        if len(create_datetime) > 19:
            create_datetime = create_datetime[:19]
        
        res = {
#             'InvoiceNoSeries': self.document_name_series or "",
            'InvoiceNoSeries': "",
            'InvoiceNo': name or "",
            'Status': "Ok",
            'UniqueId': str(self.id),
            'DocumentDate': date_invoice or "",
            'InvoiceCreateTime': user.convert_datetime_to_user_tz(create_datetime) or "",
            'SumTotal': "%.2f" % (amount_total or 0.0),
            'SumNonTaxed': "%.2f" % (amount_untaxed or 0.0),
            'Currency': "EUR",
#             'PaymentDays': self.payment_term_date or "",
            'PaymentDate': payment_term_date or "",
            'DocType': self.get_print_document_invoice_type()
        }
#         if self.parent_invoice_id and self.parent_invoice_id.category == self.category:
#             if self.parent_invoice_id.annul_document:
#                 parent_name = self.parent_invoice_id.parent_invoice_id.name
#             else:
#                 parent_name = self.parent_invoice_id.name
#             res['ChangedInvNo'] = parent_name
        
#         deposit_sum = 0.0
#         tara_sum = 0.0
#         sum_not_taxed = 0.0
#         
#         for line in self.invoice_line_ids:
#             price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
#             if line.deposit:
#                 deposit_sum += (price * line.quantity) or 0.0
#                 sum_not_taxed += (price * line.quantity) or 0.0
#             elif line.product_id.type_of_product == 'package':
#                 tara_sum += (price * line.quantity) or 0.0
#                 
#             if not line.deposit and not line.invoice_line_tax_ids:
#                 sum_not_taxed += (price * line.quantity) or 0.0
#         
#         res['SumDeposit'] = "%.2f" % deposit_sum
#         res['SumTara'] = "%.2f" % tara_sum
#         res['SumNonTaxed'] = "%.2f" % sum_not_taxed
        
        return res
    
    @api.multi
    def get_print_document_seller_data(self):
        self.ensure_one()
#         seller = self.seller_partner_id
        self._cr.execute('''
            SELECT
                seller_partner_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        seller_id, = self._cr.fetchone()

        if not seller_id:
            return {}
        
        self._cr.execute('''
            SELECT
                name, ref, vat,
                phone, fax, alcohol_license_type,
                alcohol_license_sale_type, alcohol_license_no,
                alcohol_license_date, tobac_license_type,
                tobac_license_sale_type, tobac_license_no,
                tobac_license_date, comment, logo_link
            FROM
                res_partner
            WHERE id = %s
            LIMIT 1
        ''', (seller_id,))
        name, ref, vat,\
        phone, fax, alcohol_license_type,\
        alcohol_license_sale_type, alcohol_license_no,\
        alcohol_license_date, tobac_license_type,\
        tobac_license_sale_type, tobac_license_no,\
        tobac_license_date, comment, logo_link = self._cr.fetchone()
        
        logo_base64 = False
        if logo_link:
            company = self.env.user.company_id
            despatch_api_link = company.despatch_api_link
            if not despatch_api_link.endswith('/'):
                despatch_api_link += "/"
            if despatch_api_link.endswith('/api/')\
                and logo_link.startswith('/api/')\
            :
                despatch_api_link = despatch_api_link[:-5]
                
            logo_link = despatch_api_link + logo_link
            
            image_link_response = requests.get(logo_link)
            item_bytes = BytesIO(image_link_response.content)

            logo_base64 = base64.b64encode(item_bytes.getvalue())
            logo_base64 = logo_base64.decode()
        
        seller = self.env['res.partner'].browse(seller_id)
        
        res = {
            'Name': name or "",
            'RegCode': ref or "",
            'VATCode': vat or "",
#             'LoadAddress': owner.load_address or "",
#             'Registrar': owner.registrar or "",
            'RegAddress': seller.get_address() or "",
            'Phone': phone or "",
#             'LogisticsPhone': owner.logistics_phone or "",
#             'LogisticsEMail': owner.logistics_email or "",
            'Fax': fax or "",
            'AlcLicType': alcohol_license_type or "",
            'AlcLicSaleType': alcohol_license_sale_type or "",
            'AlcLicNr': alcohol_license_no or "",
            'AlcLicDate': alcohol_license_date or "",
            'TobLicType': tobac_license_type or "",
            'TobLicSaleType': tobac_license_sale_type or "",
            'TobLicNr': tobac_license_no or "",
            'TobLicDate': tobac_license_date or "",
            'ExtraText': comment or "",
#             'TextInvoiceEnd': owner.text_invoice_end or "",
            'LogoBase64': logo_base64 or "",
        }
        return res
    
    @api.multi
    def get_print_document_owner_data(self):
        self.ensure_one()
#         owner = self.owner_id

        self._cr.execute('''
            SELECT
                owner_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        owner_id, = self._cr.fetchone()

        if not owner_id:
            return {}
        
        self._cr.execute('''
            SELECT
                name, ref, vat, reg_address
            FROM
                product_owner
            WHERE id = %s
            LIMIT 1
        ''', (owner_id,))
        name, ref, vat, reg_address = self._cr.fetchone()
        
        res = {
            'Name': name or "",
            'RegCode': ref or "",
            'VATCode': vat or "",
            'RegAddress': reg_address or "",
        }
        
        return res
    
    @api.multi
    def get_print_document_bank_acc_data(self):
        self.ensure_one()
        
        self._cr.execute('''
            SELECT
                seller_partner_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        seller_id, = self._cr.fetchone()

        if not seller_id:
            return {}
        
        self._cr.execute('''
            SELECT
                rpb.acc_number, rb.name
            FROM
                res_partner_bank AS rpb
            LEFT JOIN 
                res_bank AS rb ON (
                    rpb.bank_id = rb.id
                )
            WHERE rpb.partner_id = %s
            LIMIT 1
        ''', (seller_id,))
        sql_res = self._cr.fetchone()
        if not sql_res:
            return {}
        
        bank_account, bank_name = sql_res
        
        res = {
            'BankName': bank_name or "",
            'BankAccount': bank_account or "",
        }
        
        return res
    
    @api.multi
    def get_print_document_carrier_data(self):
        self.ensure_one()

#         carrier = self.carrier_id
#         driver = self.driver_id

        self._cr.execute('''
            SELECT
                carrier_id, driver_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        carrier_id, driver_id = self._cr.fetchone()
        
        if carrier_id:
            self._cr.execute('''
                SELECT
                    name, ref, vat, street
                FROM
                    res_partner
                WHERE id = %s
                LIMIT 1
            ''', (carrier_id,))
            carrier_name, carrier_ref, carrier_vat, carrier_street = self._cr.fetchone()
        else:
            carrier_name = False
            carrier_ref = False
            carrier_vat = False
            carrier_street = False
            
        if driver_id:
            self._cr.execute('''
                SELECT
                    name, license_plate
                FROM
                    stock_location
                WHERE id = %s
                LIMIT 1
            ''', (driver_id,))
            driver_name, license_plate = self._cr.fetchone()
        else:
            driver_name = False
            license_plate = False

        res = {
            'Name': carrier_name  or "",
            'RegCode': carrier_ref  or "",
            'VATCode': carrier_vat or "",
            'RegAddress': carrier_street or "",
            'CarNumber': license_plate or "",
            'Driver': driver_name or "",
        }
            
        return res
    
    
    @api.multi
    def get_print_document_client_data(self):
        self.ensure_one()
        res = {}
        
        self._cr.execute('''
            SELECT
                partner_shipping_id, partner_id, one_time_partner_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        partner_shipping_id, partner_id, one_time_partner_id = self._cr.fetchone()
        
        if one_time_partner_id:
            self._cr.execute('''
                SELECT
                    parent_id
                FROM
                    res_partner
                WHERE id = %s
                LIMIT 1
            ''', (partner_shipping_id,))
            partner_id, = self._cr.fetchone()
        
        if not (partner_id or one_time_partner_id):
            return {}
        
        if partner_shipping_id:
            self._cr.execute('''
                SELECT
                    name, possid_code, street
                FROM
                    res_partner
                WHERE id = %s
                LIMIT 1
            ''', (partner_shipping_id,))
            posid_name, posid_code, posid_street = self._cr.fetchone()
        else:
            posid_name = False
            posid_code = False
            posid_street = False
        
        region = False
        bank_name = False
        bank_acc = False
        phone = False
        fax = False
        
        if one_time_partner_id:
            self._cr.execute('''
                SELECT
                    name, ref, vat, address,
                    inidividual_actv_nr, farmer_code,
                    state_id, route, alcohol_license_type,
                    alcohol_license_sale_type, alcohol_license_no,
                    alcohol_license_date, alcohol_license_consume, tobac_license_type,
                    tobac_license_sale_type, tobac_license_no,
                    tobac_license_date, bsn_lic_nr, client_code,
                    posid_name, posid_code
                FROM
                    transportation_order_partner
                WHERE id = %s
                LIMIT 1
            ''', (one_time_partner_id,))
            name, ref, vat, street,\
            inidividual_actv_nr, farmer_code,\
            state_id, route, alcohol_license_type,\
            alcohol_license_sale_type, alcohol_license_no,\
            alcohol_license_date, alcohol_license_consume, tobac_license_type,\
            tobac_license_sale_type, tobac_license_no,\
            tobac_license_date, bsn_lic_nr, client_code,\
            posid_name, posid_code = self._cr.fetchone()
        else:
            self._cr.execute('''
                SELECT
                    name, ref, vat, street,
                    inidividual_actv_nr, farmer_code,
                    phone, fax, state_id, route, alcohol_license_type,
                    alcohol_license_sale_type, alcohol_license_no,
                    alcohol_license_date, alcohol_license_consume, tobac_license_type,
                    tobac_license_sale_type, tobac_license_no,
                    tobac_license_date, bsn_lic_nr, client_code
                FROM
                    res_partner
                WHERE id = %s
                LIMIT 1
            ''', (partner_id,))
            name, ref, vat, street,\
            inidividual_actv_nr, farmer_code,\
            phone, fax, state_id, route, alcohol_license_type,\
            alcohol_license_sale_type, alcohol_license_no,\
            alcohol_license_date, alcohol_license_consume, tobac_license_type,\
            tobac_license_sale_type, tobac_license_no,\
            tobac_license_date, bsn_lic_nr, client_code = self._cr.fetchone()
            
            if state_id:
                self._cr.execute('''
                    SELECT
                        name
                    FROM
                        res_country_state
                    WHERE id = %s
                    LIMIT 1
                ''', (state_id,))
                region, = self._cr.fetchone()
                
            self._cr.execute('''
                SELECT
                    rpb.acc_number, rb.name
                FROM
                    res_partner_bank AS rpb
                LEFT JOIN 
                    res_bank AS rb ON (
                        rpb.bank_id = rb.id
                    )
                WHERE rpb.partner_id = %s
                LIMIT 1
            ''', (partner_id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                bank_acc, bank_name = sql_res
        

        res = {
            'Name': name or "",
            'RegCode': ref or "",
            'VatCode': vat or "",
            'RegAddress': street or "",
            'InidividualActvNr': inidividual_actv_nr or "",
            'FarmerCode': farmer_code or "",
            'InnerCode': not one_time_partner_id and posid_code or "",
            'PosName': posid_name or "",
            'PosCode': posid_code or "",
            'PersonName': not one_time_partner_id and posid_name or "",
            'POSAddress': not one_time_partner_id and posid_street or "",
            'Phone': phone or "",
            'Fax': fax or "",
            'Region': region or "",
            'Route': route or "",
            'BankName': bank_name or "",
            'BankAccount': bank_acc or "",
            'AlcLicType': alcohol_license_type or "",
            'AlcLicSaleType': alcohol_license_sale_type or "",
            'AlcLicNr': alcohol_license_no or "",
            'AlcLicDate': alcohol_license_date or "",
            'AlcLicConsume': alcohol_license_consume or "",
            'TobLicType': tobac_license_type or "",
            'TobLicSaleType': tobac_license_sale_type or "",
            'TobLicNr': tobac_license_no or "",
            'TobLicDate': tobac_license_date or "",
            'BSNLicNr': bsn_lic_nr or "",
            'ClientCode': client_code or "",
        }

#         posid = self.partner_shipping_id 
#         partner = self.partner_id or posid.parent_id.id
#         one_time_partner = self.one_time_partner_id
#         
#         res = {
#             'Name': one_time_partner and one_time_partner.name or partner.name or "",
#             'RegCode': one_time_partner and one_time_partner.ref or partner.ref or "",
#             'VatCode': one_time_partner and one_time_partner.vat or partner.vat or "",
#             'RegAddress': one_time_partner and one_time_partner.address or partner.street or "",
#             'InidividualActvNr': one_time_partner and one_time_partner.inidividual_actv_nr or partner.inidividual_actv_nr or "",
#             'FarmerCode': one_time_partner and one_time_partner.farmer_code or partner.farmer_code or "",
#             'InnerCode': not one_time_partner and posid.possid_code or "",
#             'PosName': one_time_partner and one_time_partner.posid_name or posid.name or "",
#             'PosCode': one_time_partner and one_time_partner.posid_code or posid.possid_code or "",
#             'PersonName': not one_time_partner and posid.name or "",
#             'POSAddress': not one_time_partner and posid.street or "",
# #             'POSAddress2': one_time_partner and one_time_partner.posid_address2 or "",
#             'Phone': not one_time_partner and partner.phone or "",
#             'Fax': not one_time_partner and partner.fax or "",
#             'Region': not one_time_partner and partner.state_id and partner.state_id.name or "",
#             'Route': one_time_partner and one_time_partner.route or partner.route or "",
#             'BankName': one_time_partner and one_time_partner.bank_name or partner.bank_name or "",
#             'BankAccount': one_time_partner and one_time_partner.bank_account or partner.bank_account or "",
#             'AlcLicType': one_time_partner and one_time_partner.alcohol_license_type or partner.alcohol_license_type or "",
#             'AlcLicSaleType': one_time_partner and one_time_partner.alcohol_license_sale_type or partner.alcohol_license_sale_type or "",
#             'AlcLicNr': one_time_partner and one_time_partner.alcohol_license_no or partner.alcohol_license_no or "",
#             'AlcLicDate': one_time_partner and one_time_partner.alcohol_license_date or partner.alcohol_license_date or "",
#             'AlcLicConsume': one_time_partner and one_time_partner.alcohol_license_consume or partner.alcohol_license_consume or "",
#             'TobLicType': one_time_partner and one_time_partner.tobac_license_type or partner.tobac_license_type or "",
#             'TobLicSaleType': one_time_partner and one_time_partner.tobac_license_sale_type or partner.tobac_license_sale_type or "",
#             'TobLicNr': one_time_partner and one_time_partner.tobac_license_no or partner.tobac_license_no or "",
#             'TobLicDate': one_time_partner and one_time_partner.tobac_license_date or partner.tobac_license_date or "",
#             'BSNLicNr': one_time_partner and one_time_partner.bsn_lic_nr or partner.bsn_lic_nr or "",
#             'ClientCode': one_time_partner and one_time_partner.client_code or partner.client_code or "",
# #             'EUText': one_time_partner and one_time_partner.reg_code or partner.ref or "",
#         }

        return res
    
    @api.multi
    def get_print_document_vat_datas(self):
        self.ensure_one()
        tax_env = self.env['account.tax']
        res = []    
        
        tax_vals = self.get_taxes_values()
        for key in tax_vals.keys():
            tax_id = tax_vals[key].get('tax_id', False)
            if tax_id:
                tax = tax_env.browse(tax_vals[key]['tax_id'])
                vals = {
                    'VatTrf': "%.0f" % tax.amount,
                    'SumWOVat': "%.2f" % tax_vals[key].get('base', 0.0),
                    'VATSum': "%.2f" % tax_vals[key].get('amount', 0.0),
                }
                res.append(vals)
        return res
    
    @api.multi
    def get_print_document_line_datas(self):
        self.ensure_one()
        res = []
        line_no = 0
        for line in self.invoice_line_ids.sorted(key=lambda r: r.id):
            line_no += 1
            
            product = line.product_id
            
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(
                price, self.currency_id, line.quantity, product=line.product_id, partner=self.partner_id
            )
            taxes_wt_discount = line.invoice_line_tax_ids.compute_all(
                line.price_unit, self.currency_id, line.quantity, product=line.product_id, partner=self.partner_id
            )
            
            total_discount_amount = taxes_wt_discount['total_included'] - taxes['total_included']
            tax_amount = 0.0
            for tax in taxes['taxes']:
                tax_amount += tax.get('amount', 0.0)
                
#             qty = line.quantity
#             small_package_size = product.small_package_size
#             big_package_size = product.big_package_size
            
            
            vals = {
                'Line_No': str(line_no),
#                 'ProductCode': product,
                'Inf_Prek': product.default_code or "",
                'ProductId': str(product.id),
                'Barcode': product.barcode_ids and len(product.barcode_ids) == 1\
                    and product.barcode_ids[0].barcode or "", #TODO: issiaskinti, kuri deti istikruju
#                 'CodeAtClient': "",
                'ProductDescription': product.name or "",
                'ProductDescriptionEN': product.name_english or "",
                'MeasUnit': line.uom_id and line.uom_id.name or product.uom_id.name,
                'MeasUnitEN': product.uom_english or "",
                'Price': "%.5f" % line.price_unit,
                'PriceVat': "%.5f" % tax_amount,
                'Discount': "%.1f" % line.discount,
#                 'Kd': "",
#                 'Km': "",
#                 'Kv': "",
                'Quantity': "%.3f" % line.quantity,
#                 'QuantityInUnits': "",
                'SumWoVAT': "%.5f" % line.price_subtotal,
                'LineDiscAmt': "%.5f" % total_discount_amount,
                'VatTrf': "%.0f" % (line.invoice_line_tax_ids and line.invoice_line_tax_ids[0].amount or 0.0),
                'Brutto': "%.3f" % product.weight,
#                 'NettoUnit': "",
                'Netto': "%.3f" % product.weight_neto,
#                 'CaseQuantity': "",
                'Tobacco': product.type_of_product == 'tabacco' and "1" or "0",
                'Alco': product.type_of_product == 'alcohol' and "1" or "0",
#                 'RecomendedPrice': "",
#                 'Tara': "",
#                 'TaraProd': "",
#                 'TLIC': "",
#                 'SourceDocumentNo': "",
#                 'SourceDocumentDate': "",
#                 'RSP': "",
#                 'ExcPercentRate': "",
#                 'ExcisableQty': "",
#                 'ExciseMeasureUnit': "",
#                 'ExciseTrf': "",
#                 'ExciseSum': "",
#                 'ExciseGroup': "",
#                 'ExciseGroupName': "",
#                 'MinTaxAmount': "",
#                 'FixedTaxAmount': "",
#                 'ProductKiekd': "",
#                 'ProductKiekm': "",
#                 'Volume': "",
            }
            res.append(vals)
        
        return res

    @api.multi
    def action_update_prices(self):
        # Žaimantas yra padaręs webservisą, kur galima paduoti užsakymo ID
        # eilutės numerį, produkto kodą ir eilutės kiekį. Šis metodas patikrina ar nepasikeitusios kainos
        # ir jeigu jos pasikeitusios sukuriamas naujas dokumentas.

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/plain',
            'Host': 'testing.snx.lt'
        }
        price_change_url = self.env.user.company_id.price_change_url

        if not price_change_url:
            raise UserError(_('You have to fill in price update web service url in company settings.'))
        res = False
        for invoice in self:
            if invoice.owner_id.owner_code != 'SNX':
                raise UserError(
                    _('Only Sanitex documents prices can be recalculated. This document(%s, ID: %s) belong to [%s] %s.') % (
                        invoice.name, str(invoice.id), invoice.owner_id.owner_code, invoice.owner_id.name
                    )
                )
            if invoice.state == 'cancel':
                raise UserError(
                    _('You can\'t update prices for cancelled document(%s, ID: %s).') % (
                        invoice.name, str(invoice.id)
                    )
                )
            if invoice.category != 'invoice':
                raise UserError(
                    _('You can update prices only for invoice type document(%s, ID: %s).') % (
                        invoice.name, str(invoice.id)
                    )
                )
            line_updates = {}
            request_data = {'lines': []}
            for line in invoice.invoice_line_ids:
                line_request_data = {
                    'ordStatId': int(line.get_transportation_order_data().get('name', '0')),
                    'lineNum': int(line.get_transportation_order_data().get('id_line', '0')),
                    'quantity': line.quantity,
                    'inf_Prek': line.product_code
                }
                if not line_request_data['ordStatId'] or not line_request_data['lineNum']:
                    raise UserError(
                        _('Document(%s, ID: %s) line(%s - %s, ID: %s) does not have related transportation order.') % (
                            invoice.name, str(invoice.id), line.product_code, str(line.quantity), str(line.id)
                        )
                    )
                key = (line_request_data['ordStatId'], line_request_data['lineNum'])
                line_updates[key] = {'id': line.id, 'old_price': line.price_unit, 'new_price': line.price_unit}
                line_updates[key].update(line_request_data)
                request_data['lines'].append(line_request_data)

            price_change = requests.post(price_change_url, data=json.dumps(request_data), headers=headers)
            price_change_str = price_change.content
            try:
                price_change_dict = json.loads(price_change_str.decode('utf8'))
            except:
                json_acceptable_string = price_change_str.decode('utf8').replace("'", "\"")
                price_change_dict = json.loads(json_acceptable_string)

            # print('request_data', json.dumps(request_data, indent=2))
            # print('price_change', json.dumps(price_change_dict, indent=2))
            if price_change_dict.get('status', '') != 'OK':
                raise UserError(json.dumps(price_change_dict, indent=2))
            if not price_change_dict.get('lines'):
                raise UserError(json.dumps(price_change_dict, indent=2))

            for result_line in price_change_dict['lines']:
                key = (result_line['ordStatId'], result_line['lineNum'])
                if result_line.get('status', 'ERROR') == 'OK':
                    print(result_line)
                    if line_updates[key]['old_price'] == result_line['price']:
                        del line_updates[key]
                        continue
                    line_updates[key]['new_price'] = result_line['price']
                    line_updates[key].update(result_line)
                else:
                    del line_updates[key]
            if not line_updates:
                raise UserError(_('Prices for document %s was already up to date.') % invoice.name)
            # print_line_updates = {}
            # for key in line_updates:
            #     print_line_updates[str(key)] = line_updates[key]
            # print('naujos kainos', json.dumps(print_line_updates, indent=2))
            invoice_line_change = []
            for key in line_updates:
                invoice_line_change.append([1, line_updates[key]['id'], {'price_unit': line_updates[key]['new_price']}])
            if invoice_line_change:
                # print('invoice', invoice.tax_line_ids)
                invoice.with_context(document_edit=True).write({'invoice_line_ids': invoice_line_change})
                all_invoices = invoice.get_related_invoices()
                # print('all_invoices', all_invoices.mapped('tax_line_ids'), all_invoices.mapped('tax_line_ids').mapped('name'))
                # self.invalidate_cache(fnames=['price_subtotal'], ids=list(self._ids))
                # self.env.add_todo(self._fields['price_subtotal'], self)
                all_invoices.update_amounts()
                res = invoice.document_save_button()
        return res

    @api.multi
    def get_print_document_certif_datas(self):
        self.ensure_one()
        res = []

        self._cr.execute('''
            SELECT
                id
            FROM
                account_invoice_line
            WHERE invoice_id = %s
            ORDER BY id
        ''', (self.id,))
        inv_line_ids_tuples = self._cr.fetchall()
        inv_line_ids = [i[0] for i in inv_line_ids_tuples]
        
        line_no = 0
        
        for inv_line_id in inv_line_ids:
            line_no += 1
            
#             self._cr.execute('''
#                 SELECT
#                     id
#                 FROM
#                     account_invoice_container_line
#                 WHERE invoice_line_id = %s
#             ''', (inv_line_id,))
#             container_line_ids_tuple_list = self._cr.fetchall()
#             #Eilute, gali buti nesusijusi tiesiogiai (Pavayzdziui buvo koreguojamas dokumentas)
#             if not container_line_ids_tuple_list:
            self._cr.execute('''
                SELECT
                    container_line_id
                FROM
                    invoice_line_container_line_rel
                WHERE invoice_line_id = %s
            ''', (inv_line_id,))
            container_line_ids_tuple_list = self._cr.fetchall()
                
            container_line_ids = [i[0] for i in container_line_ids_tuple_list if i and i[0]]
            
            if container_line_ids:       
                self._cr.execute('''
                    SELECT
                        pc.id, pc.name, pc.issue_date,
                        pc.issued_by, pc.valid_to
                    FROM
                        product_certificate AS pc
                    JOIN
                        container_line_certificate_rel AS cc_rel ON (
                            pc.id = cc_rel.certificate_id
                        )
                    JOIN
                        account_invoice_container_line AS aicl ON (
                            aicl.id = container_line_id
                        )
                    WHERE aicl.id in %s
                ''', (tuple(container_line_ids),))
                certificate_vals_tuples = self._cr.fetchall()
                
                
                
                for cert_id, name, issue_date, issued_by, valid_to in certificate_vals_tuples:
                    self._cr.execute('''
                        SELECT
                            distinct(lot.name)
                        FROM
                            stock_production_lot AS lot
                        JOIN
                            certificate_lot_rel AS rel ON (
                                lot.id = rel.lot_id
                            )
                        WHERE 
                            rel.certificate_id = %s 
                    ''', (cert_id,))
                    lots_tuples = self._cr.fetchall()
                    
                    lot_number = ', '.join([i[0] for i in lots_tuples if i and i[0]])
                    
                    vals = {
                        'Line_No': str(line_no),
                        'CertNumber': name or "",
                        'CertIssueDate': issue_date or "",
                        'CertIssuedBy': issued_by or "",
                        'LotNumber': lot_number,
                        'ValidToDate': valid_to or "",
                    }
                    res.append(vals)

#         line_no = 0
#         for inv_line in self.invoice_line_ids.sorted(key=lambda r: r.id):
#             line_no += 1
#             
#             certificates = inv_line.container_line_ids.mapped('certificate_ids')
# 
#             for certificate in certificates:
#                 lot_number = ""
#                 if certificate.lot_ids:
#                     lot_numbers = [lot.name for lot  in certificate.lot_ids if lot.name]
#                     if lot_numbers:
#                         lot_number = ', '.join(lot_numbers)
#                 
#                 
#                 vals = {
#                     'Line_No': str(line_no),
#                     'CertNumber': certificate.name or "",
#                     'CertIssueDate': certificate.issue_date or "",
#                     'CertIssuedBy': certificate.issued_by or "",
#                     'LotNumber': lot_number,
#                     'ValidToDate': certificate.valid_to or "",
#                 }
#                 res.append(vals)
        return res
    

    @api.multi
    def send_document_paper_form(self, printer=False):
        invoice_document_report = self.env.ref('config_bls_stock.report_account_invoice_document_print_form', False)[0]
        for invoice in self:
            invoice_document_report.print_report(invoice, printer=printer, copies=invoice.print_copies)
            self._cr.execute('''
                UPDATE account_invoice
                SET printing_datetime = now()
                WHERE id = %s
            ''', (invoice.id,))

        return True
    
    @api.multi
    def get_id_source_doc(self):
        self.ensure_one()
        self._cr.execute('''
            SELECT
                da.id_source_doc
            FROM
                despatch_advice as da
            JOIN account_invoice_container_line as aicl ON (
                aicl.despatch_advice_id = da.id
            )
            
            JOIN invoice_line_container_line_rel as ilclr ON (
                aicl.id = ilclr.container_line_id
            )
            
            JOIN account_invoice_line as ail ON (
                ail.id = ilclr.invoice_line_id
            )  
            WHERE ail.invoice_id = %s
            LIMIT 1
        ''', (self.id,))
        sql_res = self._cr.fetchone()
        return sql_res and sql_res[0] or "-"
    
    @api.multi
    def get_issue_date_and_time(self):
        self.ensure_one()
        self._cr.execute('''
            SELECT
                document_create_datetime, create_date
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        sql_res = self._cr.fetchone()
        
        create_datetime = sql_res[0] or sql_res[1]
        if len(create_datetime) > 19:
            create_datetime = create_datetime[:19]
            

        tz_date_time = self.env.user.convert_datetime_to_user_tz(create_datetime)
        create_date, create_time = tz_date_time.split(' ')
        
        return (
            datetime.datetime.strptime(
                create_date, "%Y-%m-%d"
            ).date(),
            datetime.datetime.strptime(
                create_time, "%H:%M:%S"
            ).time()
        )
#         return (create_date, create_time)
    
    
    @api.model
    def get_one_time_partner_vals(self, one_time_partner_id):
        self._cr.execute('''
            SELECT
                name, vat, ref, address
            FROM
                transportation_order_partner
            WHERE id = %s
            LIMIT 1
        ''', (one_time_partner_id,))
        name, vat, ref, addr_line = self._cr.fetchone()
        
        
        ident_vals_list = []
        
        if vat:
            ident_vals_list.append({
                "scheme_id": "VAT_CODE",
                "id": vat
            })
            
        if ref:
            ident_vals_list.append({
                "scheme_id": "COMPANY_CODE",
                "id": ref
            })
        
        res = {
            "party_name": {
                "name": name
            },
           "physical_location": {
                "address": {
                    "address_line": [
                        {
                            "line": addr_line
                        }
                    ],
                }
            }
        }
        if ident_vals_list:
            res['party_identification'] = ident_vals_list
        
        return res
    
    @api.multi
    def get_shipment_vals(self):
        partner_env = self.env['res.partner']
        res = {
            "id": "1",
            "delivery": {
                
            }
        }
        
        self.ensure_one()
        self._cr.execute('''
            SELECT
                carrier_id, partner_shipping_id,
                despatch_address_id, driver_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        carrier_id, partner_shipping_id, despatch_address_id, driver_id = self._cr.fetchone()
        
        if carrier_id:
            res["delivery"]["carrier_party"] = partner_env.get_partner_vals(carrier_id)
        if partner_shipping_id:
            res["delivery"]["delivery_location"] = partner_env.get_partner_location_vals(partner_shipping_id)
        if despatch_address_id:
            res["delivery"]["despatch"] = {
                "despatch_location": partner_env.get_partner_location_vals(despatch_address_id)
            }
            
        if driver_id:
            self._cr.execute('''
                SELECT
                    license_plate, trailer
                FROM
                    stock_location
                WHERE id = %s
                LIMIT 1
            ''', (driver_id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                license_plate, trailer = sql_res
                if (license_plate and license_plate not in ('.','-'))\
                    or (trailer and trailer not in ('.','-'))\
                :
                    res['transport_handling_unit'] = {
                        'transport_means' : []
                    }
                    if license_plate and license_plate not in ('.','-'):
                        res['transport_handling_unit']['transport_means'].append(
                            {
                                'road_transport': {
                                    "scheme_id": "TRUCK_NUMBER",
                                    "license_plate_id": license_plate,
                                }
                            }
                        )
                    if trailer and trailer not in ('.','-'):
                        res['transport_handling_unit']['transport_means'].append(
                            {
                                'road_transport': {
                                    "scheme_id": "TRAILER_NUMBER",
                                    "license_plate_id": trailer,
                                }
                            }
                        )
                             
        containers = []
        
        self._cr.execute('''
            SELECT
                distinct(aic.id_external), aic.code
            FROM
                account_invoice_container as aic
            JOIN account_invoice_container_line as aicl ON (
                aicl.container_id = aic.id
            )
            
            JOIN invoice_line_container_line_rel as ilclr ON (
                aicl.id = ilclr.container_line_id
            )
            
            JOIN account_invoice_line as ail ON (
                ilclr.invoice_line_id = ail.id
            )
            WHERE ail.invoice_id = %s
        ''', (self.id,))
        container_tuples = self._cr.fetchall()
        for container_tuple in container_tuples:
            containers.append({
                "id": container_tuple[0],
                "handling_code": container_tuple[1]
            })
        
        if containers:
            res['consignment'] = containers

        return res
    
    @api.multi
    def get_electronical_invoice_vals(self):
        self.ensure_one()
        
        partner_env = self.env['res.partner']
        line_env = self.env['account.invoice.line']

        self._cr.execute('''
            SELECT
                name, comment, partner_id, id_external,
                one_time_partner_id, seller_partner_id,
                carrier_id, partner_shipping_id,
                despatch_address_id, amount_untaxed,
                amount_tax, amount_total, currency_id,
                primary_invoice_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        doc_name, note, buyer_partner_id, id_external,\
        one_time_partner_id, seller_partner_id,\
        carrier_id, partner_shipping_id, despatch_address_id,\
        amount_untaxed,amount_tax, amount_total, currency_id,\
        primary_invoice_id = self._cr.fetchone()
        
        currency = "EUR"
        if currency_id:
            self._cr.execute('''
                SELECT
                    name
                FROM
                    res_currency
                WHERE id = %s
                LIMIT 1
            ''', (currency_id,))
            currency, = self._cr.fetchone()
        
        issue_date, issue_time = self.get_issue_date_and_time() or ("", "")

        id_source = self.get_id_source_doc()

        res = {
            "ubl_extensions": {
                "ubl_extension": [
                    {
                        "extensionreasoncode": "INVOICE",
                        "extension_content": {
                            "settings": {
                                "document_source_id": id_source,
                            }
                        }
                    },
                ]
            },
            "ubl_version_id": "2.1",
            "customization_id": "BLS",
            "id": doc_name,
            "uuid": id_external,
#             "IssueDate": issue_date,
#             "IssueTime": issue_time,
#             "Note": note,
            "document_currency_code": currency,
            "tax_total": {
                "tax_amount": "%.2f" % (amount_tax or 0.0),
                "tax_subtotal": [{
                    "taxable_amount": "%.2f" % (amount_untaxed or 0.0),
                    "tax_amount": "%.2f" % (amount_tax or 0.0),
#                     "_ext_attributes": {
#                         "taxable_amount": {
#                           "currency_id": currency,
#                         },
#                         "tax_amount": {
#                           "currency_id": currency,
#                         },
#                     },
                    "tax_category": {
                        "percent": "%.0f" % (amount_untaxed and round((amount_tax or 0.0/amount_untaxed)*100) or 0.0),
                        "tax_scheme": {
                            "name": "VAT",
                            "tax_type": "VAT"
                        }
                    }
                }],
#                 "_ext_attributes": {
#                     "tax_amount": {
#                       "currency_id": currency,
#                     }
#                 },
            },
            "legal_monetary_total": {
                "tax_exclusive_amount": "%.2f" % (amount_untaxed or 0.0),
                "tax_inclusive_amount": "%.2f" % (amount_total or 0.0),
                "payable_amount": "%.2f" % (amount_total or 0.0),
#                 "_ext_attributes": {
#                     "tax_exclusive_amount": {
#                       "currency_id": currency,
#                     },
#                     "tax_inclusive_amount": {
#                       "currency_id": currency,
#                     },
#                     "payable_amount": {
#                       "currency_id": currency,
#                     },
#                 },
            }
        }
        
        
        additional_doc_refs = []
        self._cr.execute('''
            SELECT
                invoice_sibling_id
            FROM
                invoice_sibling_invoice_rel
            WHERE
                invoice_id = %s
            ORDER BY
                invoice_sibling_id
        ''', (self.id,))
        additional_doc_ids = [i[0] for i in self._cr.fetchall()]
        

        for additional_doc_id in additional_doc_ids:
            self._cr.execute('''
                SELECT
                    name, id_external, category
                FROM
                    account_invoice
                WHERE
                    id = %s
                LIMIT 1
            ''', (additional_doc_id,))
            additional_doc_name, additional_doc_uuid, additional_doc_categ = self._cr.fetchone()
            additional_doc_refs.append({
                'id': additional_doc_name,
                'uuid': additional_doc_uuid,
                'document_type_code': additional_doc_categ == 'invoice' and "Invoice"\
                    or additional_doc_categ == 'waybill' and "Waybill" or ""
            })
        if primary_invoice_id:
            self._cr.execute('''
                SELECT
                    name, id_external, category
                FROM
                    account_invoice
                WHERE
                    id = %s
                LIMIT 1
            ''', (primary_invoice_id,))
            additional_doc_name, additional_doc_uuid, additional_doc_categ = self._cr.fetchone()
            additional_doc_refs.append({
                'id': additional_doc_name,
                'uuid': additional_doc_uuid,
                'document_type_code': additional_doc_categ == 'invoice' and "Invoice"\
                    or additional_doc_categ == 'waybill' and "Waybill" or "",
                'version_id': "1",
            })

        if additional_doc_refs:
            res['additional_document_reference'] = additional_doc_refs
        
        

        if note:
            res['note'] = note
        if issue_date:
            res['issue_date'] = issue_date
        if issue_time:
            res['issue_time'] = issue_time
        buyer_vals = False
        if buyer_partner_id:
            buyer_vals = {"party": partner_env.get_partner_vals(buyer_partner_id)}
        elif one_time_partner_id:
            buyer_vals = {"party": self.get_one_time_partner_vals(one_time_partner_id)}
        if buyer_vals:
            res['accounting_customer_party'] = buyer_vals
            res['buyer_customer_party'] = buyer_vals
            
        if seller_partner_id:
            seller_vals = {"party": partner_env.get_partner_vals(seller_partner_id)}
            
            res['accounting_supplier_party'] = seller_vals
            res['seller_supplier_party'] = seller_vals
        
        if carrier_id or partner_shipping_id or despatch_address_id:
            res['delivery'] = {}
            if carrier_id:
                carrier_vals = partner_env.get_partner_vals(carrier_id)
                res["delivery"]["carrier_party"] = carrier_vals
            if partner_shipping_id:
                res["delivery"]["delivery_location"] = partner_env.get_partner_location_vals(partner_shipping_id)
            if despatch_address_id:
                res["delivery"]["despatch"] = {
                    "despatch_location": partner_env.get_partner_location_vals(despatch_address_id)
                }
              
        line_vals_list = []
        line_counter = 0
        self._cr.execute('''
            SELECT
                id
            FROM
                account_invoice_line
            WHERE invoice_id = %s
        ''', (self.id,))
        inv_line_ids = [i[0] for i in self._cr.fetchall()]
        
        for inv_line_id in inv_line_ids:
            line_counter += 1
            line_vals_list = []

            related_invoice_line_vals = line_env.browse(inv_line_id).get_invoice_line_vals_for_ubl(line_counter)

            if related_invoice_line_vals:
                line_vals_list.append(related_invoice_line_vals)




#             self._cr.execute('''
#                 SELECT
#                     quantity, uom_id, product_id,
#                     transportation_order_line_id,
#                     price_subtotal, price_total,
#                     container_id, exp_date, lot_id
#                 FROM
#                     account_invoice_line
#                 WHERE id = %s
#                 LIMIT 1
#             ''', (inv_line_id,))
#             qty, uom_id, prod_id,\
#             transportation_order_line_id,\
#             line_amount_untaxed, line_amount_total,\
#             container_id, exp_date, lot_id = self._cr.fetchone()
#
#             line_amount_tax = line_amount_total - line_amount_untaxed
#
#             if uom_id:
#                 self._cr.execute('''
#                     SELECT
#                         name
#                     FROM
#                         product_uom
#                     WHERE id = %s
#                     LIMIT 1
#                 ''', (uom_id,))
#                 uom, = self._cr.fetchone()
#             else:
#                 uom = ""
#
#             self._cr.execute('''
#                 SELECT
#                     pt.name, pp.default_code
#                 FROM
#                     product_product AS pp
#                 JOIN product_template AS pt ON (
#                     pp.product_tmpl_id = pt.id
#                 )
#                 WHERE pp.id = %s
#                 LIMIT 1
#             ''', (prod_id,))
#             prod_name, default_code = self._cr.fetchone()
#
#             self._cr.execute('''
#                 SELECT
#                     barcode
#                 FROM
#                     product_barcode
#                 WHERE product_id = %s
#                 ORDER BY create_date DESC
#                 LIMIT 1
#             ''', (prod_id,))
#             sql_res = self._cr.fetchone()
#             if sql_res:
#                 barcode, = sql_res
#             else:
#                 barcode = False
#
#             # ------------------------------------------ Vytautas {--------------------------------------
#
#             # susirandu sale.order eilutes
#             self._cr.execute('''
#                 SELECT
#                     order_line_id
#                 FROM
#                     invoice_line_so_line_rel
#                 WHERE
#                     invoice_line_id = %s
#             ''', (inv_line_id,))
#             sol_ids = [line_id[0] for line_id in self.env.cr.fetchall()] # Tiksriausiai gali būti kelios eilutės
#
#             if sol_ids:
#                 # iš konteinerio eilučių išsitraukiu OUT DESPATCH ID, ir eilutės DESP ID, kolkas limituoju 1
#                 self._cr.execute('''
#                     SELECT
#                         id_despatch_line, out_despatch_id
#                     FROM
#                         account_invoice_container_line
#                     WHERE
#                         sale_order_line_id in %s
#                     LIMIT 1
#                 ''', (tuple(sol_ids),))
#                 id_despatch_line, out_desp_id = self.env.cr.fetchone() # Tiksriausiai gali būti kelios eilutės
#
#                 if out_desp_id:
#                     self._cr.execute('''
#                         SELECT
#                             name, id_external
#                         FROM
#                             despatch_advice
#                         WHERE
#                             id = %s
#                         LIMIT 1
#                     ''', (out_desp_id,))
#                     despatch_name, id_despatch = self._cr.fetchone()
#                 else:
#                     despatch_name = ''
#
#
#
#             # ------------------------------------------} Vytautas --------------------------------------
#
#             line_vals = {
#                 "id": str(line_counter),
#                 "invoiced_quantity": qty,
#                 "line_extension_amount": "%.2f" % (line_amount_untaxed),
# #                 "_ext_attributes": {
# #                     "invoiced_quantity": {
# #                       "unit_code": uom,
# #                     },
# #                     "line_extension_amount": {
# #                       "currency_id": currency,
# #                     },
# #                 },
#
#                 "invoiced_quantity_unit_code": uom,
#
#                 "tax_total": {
#                     "tax_amount": "%.2f" % (line_amount_tax),
# #                     "_ext_attributes": {
# #                         "tax_amount": {
# #                           "currency_id": currency,
# #                         }
# #                     },
#                     "tax_subtotal": [{
#                         "taxable_amount": "%.2f" % (line_amount_untaxed),
#                         "tax_amount": "%.2f" % (line_amount_tax),
# #                         "_ext_attributes": {
# #                             "taxable_amount": {
# #                               "currency_id": currency,
# #                             },
# #                             "tax_amount": {
# #                               "currency_id": currency,
# #                             },
# #                         },
#                         "tax_category": {
#                             "percent": "%.0f" % (line_amount_tax and round((line_amount_tax/line_amount_untaxed)*100) or 0.0),
#                             "tax_scheme": {
#                                 "name": "VAT",
#                                 "tax_type": "VAT"
#                             }
#                         }
#                     }],
#                 },
#                 "price": {
#                     "price_amount": "%.2f" % (line_amount_untaxed),
# #                     "_ext_attributes": {
# #                         "price_amount": {
# #                           "currency_id": currency,
# #                         },
# #                     },
#                 },
#                 "item": {
#                     "description": prod_name,
#                     "additional_item_identification": [
#                         {
#                             "id": default_code,
# #                             "_ext_attributes": {
# #                                 "id": {
# #                                   "scheme_id": "PRODUCT_CODE",
# #                                   "scheme_name": "Product code",
# #                                   "scheme_agency_id": "BLS"
# #                                 }
# #                             },
#                             "scheme_id": "PRODUCT_CODE",
#                             "scheme_name": "Product code",
#                             "scheme_agency_id": "BLS"
#                         }
#                     ]
#                 },
#                 # ------------------------------------------ Vytautas {--------------------------------------
#                 "despatch_line_reference": {
#                     'line_id': id_despatch_line,
#                     'document_reference': {
#                         'id': despatch_name,
#                         'uuid': id_despatch,
#                     }
#                 },
#                 # ------------------------------------------} Vytautas --------------------------------------
#
#             }
#
#             if barcode:
#                 line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode
#
#             if transportation_order_line_id:
#                 self._cr.execute('''
#                     SELECT
#                         ordl.id_line, ord.name
#                     FROM
#                         transportation_order_line AS ordl
#                     JOIN transportation_order AS ord ON (
#                         ordl.transportation_order_id = ord.id
#                     )
#                     WHERE ordl.id = %s
#                     LIMIT 1
#                 ''', (transportation_order_line_id,))
#                 sql_res = self._cr.fetchone()
#                 if not sql_res:
#                     self._cr.execute('''
#                         SELECT
#                             ordl.id_line, ord.name
#                         FROM
#                             transportation_order_line AS ordl
#                         JOIN transportation_order_line AS parent_l ON (
#                             ordl.parent_line_id = parent_l.id
#                         )
#                         JOIN transportation_order AS ord ON (
#                             parent_l.transportation_order_id = ord.id
#                         )
#                         WHERE ordl.id = %s
#                         LIMIT 1
#                     ''', (transportation_order_line_id,))
#                     sql_res = self._cr.fetchone()
#                 if sql_res:
#                     id_ord_line, id_ord = sql_res
#
#                     if id_ord_line:
#                         line_vals['order_line_reference'] = {
#                             'line_id': id_ord_line
#                         }
#                         if id_ord:
#                             line_vals['order_line_reference']['order_reference'] = {"id": id_ord}
#
#             self._cr.execute('''
#                 SELECT
#                     container_line_id
#                 FROM
#                     invoice_line_container_line_rel
#                 WHERE
#                     invoice_line_id = %s
#                 ORDER BY
#                     container_line_id
#                 LIMIT 1
#             ''', (inv_line_id,))
#             sql_res = self._cr.fetchone()
#
#             if sql_res and sql_res[0]:
#                 container_line_id = sql_res[0]
#
#                 self._cr.execute('''
#                     SELECT
#                         id_external, name
#                     FROM
#                         despatch_advice
#                     WHERE
#                         id = (
#                             SELECT out_despatch_id
#                             FROM account_invoice_container_line
#                             WHERE id = %s
#                             LIMIT 1
#                         )
#                     LIMIT 1
#                 ''', (container_line_id,))
#                 sql_res = self._cr.fetchone()
#                 if sql_res:
#                     despatch_uuid, despatch_name = sql_res
#
#                     line_vals['despatch_line_reference'] = {
#                         'line_id': str(container_line_id),
#                         'document_reference': {
#                             'id': despatch_name,
#                             'uuid': despatch_uuid,
#                         }
#                     }
#
#
#
#             lot_exp_date= False
#             if lot_id:
#                 self._cr.execute('''
#                     SELECT
#                         name, expiry_date
#                     FROM
#                         stock_production_lot
#                     WHERE
#                         id = %s
#                     LIMIT 1
#                 ''', (lot_id,))
#                 lot_name, lot_exp_date = self._cr.fetchone()
#                 line_vals["item"]['item_instance'] = {
#                     'lot_identification': {
#                         'lot_number': lot_name,
#                     }
#                 }
#                 if lot_exp_date:
#                     line_vals["item"]['item_instance']['lot_identification']['expiry_date'] = lot_exp_date
#
#             if container_id or (exp_date and not lot_exp_date):
#                 if not line_vals["item"].get('item_instance', False):
#                     line_vals["item"]['item_instance'] = {}
#
#                 if container_id:
#                     self._cr.execute('''
#                         SELECT
#                             container_no
#                         FROM
#                             account_invoice_container
#                         WHERE
#                             id = %s
#                         LIMIT 1
#                     ''', (container_id,))
#                     container_no, = self._cr.fetchone()
#                     if container_no:
#                         line_vals["item"]['item_instance']['additional_item_property'] = [
#                             {
#                                 'name': "ContainerNo",
#                                 'value': container_no,
#                             }
#                         ]
#                 if exp_date and not lot_exp_date:
#                     if not line_vals["item"]['item_instance'].get('additional_item_property', False):
#                         line_vals["item"]['item_instance']['additional_item_property'] = []
#                     line_vals["item"]['item_instance']['additional_item_property'].append({
#                         'name': "ExpirationDate",
#                         'value': exp_date,
#                     })
#
            
            
            # line_vals_list.append(line_vals)

        if line_vals_list:
            res['invoice_line'] = line_vals_list
            
        return res
#         return {"Invoice": res}
    
    @api.multi
    def get_electronical_waybill_vals(self):
        self.ensure_one()
        
        partner_env = self.env['res.partner']
        line_env = self.env['account.invoice.line']
        
        self._cr.execute('''
            SELECT
                name, comment, seller_partner_id,
                carrier_id, id_external, partner_shipping_id,
                despatch_address_id, driver_id, primary_invoice_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        doc_name, note, seller_partner_id, carrier_id, id_external,\
        partner_shipping_id, despatch_address_id, driver_id, primary_invoice_id = self._cr.fetchone()
        
        issue_date, issue_time = self.get_issue_date_and_time() or ("", "")
        
        res = {
            "ubl_extensions": {
                "ubl_extension": [
                    {
                        "extension_reason_code": "WAYBILL",
                        "extension_content": {
                            "settings": {
                                "document_source_id": self.get_id_source_doc(),
                            }
                        }
                    },
                ]
            },
            "ubl_versionid": "2.1",
            "id": doc_name,
            "uuid": id_external,
#             "IssueDate": issue_date,
#             "IssueTime": issue_time,
#             "Note": note,
           
#             "Shipment": {
#                 "ID": "1",
#                 "Delivery": {
#                     
#                 }
#             },
            "shipment": self.get_shipment_vals()
        }
        
        additional_doc_refs = []
        self._cr.execute('''
            SELECT
                invoice_sibling_id
            FROM
                invoice_sibling_invoice_rel
            WHERE
                invoice_id = %s
            ORDER BY
                invoice_sibling_id
        ''', (self.id,))
        additional_doc_ids = [i[0] for i in self._cr.fetchall()]
        

        for additional_doc_id in additional_doc_ids:
            self._cr.execute('''
                SELECT
                    name, id_external, category
                FROM
                    account_invoice
                WHERE
                    id = %s
                LIMIT 1
            ''', (additional_doc_id,))
            additional_doc_name, additional_doc_uuid, additional_doc_categ = self._cr.fetchone()
            additional_doc_refs.append({
                'id': additional_doc_name,
                'uuid': additional_doc_uuid,
                'document_type_code': additional_doc_categ == 'invoice' and "Invoice"\
                    or additional_doc_categ == 'waybill' and "Waybill" or ""
            })
        if primary_invoice_id:
            self._cr.execute('''
                SELECT
                    name, id_external, category
                FROM
                    account_invoice
                WHERE
                    id = %s
                LIMIT 1
            ''', (primary_invoice_id,))
            additional_doc_name, additional_doc_uuid, additional_doc_categ = self._cr.fetchone()
            additional_doc_refs.append({
                'id': additional_doc_name,
                'uuid': additional_doc_uuid,
                'document_type_code': additional_doc_categ == 'invoice' and "Invoice"\
                    or additional_doc_categ == 'waybill' and "Waybill" or "",
                'version_id': "1",
            })

        if additional_doc_refs:
            res['document_reference'] = additional_doc_refs
        
        
        if note:
            res['note'] = note
        if issue_date:
            res['issue_date'] = issue_date
        if issue_time:
            res['issue_time'] = issue_time

        items_vals = []
        self._cr.execute('''
            SELECT
                id
            FROM
                account_invoice_line
            WHERE invoice_id = %s
        ''', (self.id,))
        inv_line_ids = [i[0] for i in self._cr.fetchall()]
        line_counter = 0

        for inv_line_id in inv_line_ids:
            line_counter += 1 
            
            self._cr.execute('''
                SELECT
                    quantity, uom_id, product_id,
                    container_id, exp_date, lot_id
                FROM
                    account_invoice_line
                WHERE id = %s
                LIMIT 1
            ''', (inv_line_id,))
            qty, uom_id, prod_id,\
            container_id, exp_date, lot_id = self._cr.fetchone()
            
            self._cr.execute('''
                SELECT
                    pt.name, pp.default_code
                FROM
                    product_product AS pp
                JOIN product_template AS pt ON (
                    pp.product_tmpl_id = pt.id
                )
                WHERE pp.id = %s
                LIMIT 1
            ''', (prod_id,))
            prod_name, default_code = self._cr.fetchone()
            
            self._cr.execute('''
                SELECT
                    barcode
                FROM
                    product_barcode
                WHERE product_id = %s
                ORDER BY create_date DESC
                LIMIT 1
            ''', (prod_id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                barcode, = sql_res
            else:
                barcode = False
 
            line_vals = {
                "id": str(line_counter),
                "quantity": "%.3f" % (qty),
                "item": {
                    "description": prod_name,
                    "additional_item_identification": [
                        {
                            "id": default_code,
#                             "_ext_attributes": {
#                                 "id": {
#                                   "scheme_id": "PRODUCT_CODE",
#                                   "scheme_name": "Product code",
#                                   "scheme_agency_id": "BLS"
#                                 }
#                             },
                            "scheme_id": "PRODUCT_CODE",
                            "scheme_name": "Product code",
                            "scheme_agency_id": "BLS"
                        }
                    ]
                }
            }

            certificates = []
            self._cr.execute('''
                SELECT
                    distinct(id)
                FROM
                    product_certificate
                WHERE product_id = %s
            ''', (prod_id,))
            certificate_ids = [i[0] for i in self._cr.fetchall()]

            for certificate_id in certificate_ids:
                self._cr.execute('''
                    SELECT
                        name, type, issued_by,
                        issue_date, valid_from, valid_to
                    FROM
                        product_certificate
                    WHERE id = %s
                    LIMIT 1
                ''', (certificate_id,))
                cert_name, cert_type, cert_issued_by,\
                cert_issue_date, cert_valid_from, cert_valid_to = self._cr.fetchone()
                
                cert_vals = {
                    'id': cert_name,
                    'certificate_type': cert_type,
                    'certificate_type_code': cert_type,
                    'issuer_party': {
                        'party_name': {
                            'name': cert_issued_by or '-',
                        }
                    },
#                     'DocumentReference': {
#                         "ID": '.', #????????
#                         "IssueDate": cert_issue_date or "",
#                         "ValidityPeriod": {
#                             "StartDate": cert_valid_from,
#                             "EndDate": cert_valid_to,
#                         }
#                     }
                }
                
                if cert_issue_date or (cert_valid_from and cert_valid_to):
                    cert_vals["document_reference"] = {
                        "id": '.', #????????
                    }
                    if cert_issue_date:
                        cert_issue_date = datetime.datetime.strptime(
                            cert_issue_date, "%Y-%m-%d"
                        ).date()
                        cert_vals["document_reference"]["issue_date"] = cert_issue_date
                    if cert_valid_from and cert_valid_to:
                        cert_vals["document_reference"]["validity_period"] = {
#                             "start_date": cert_valid_from,
#                             "end_date": cert_valid_to,
                            "start_date": datetime.datetime.strptime(
                                cert_valid_from, "%Y-%m-%d"
                            ).date(),
                            "end_date": datetime.datetime.strptime(
                                cert_valid_to, "%Y-%m-%d"
                            ).date(),
                        }
                
                certificates.append(cert_vals)

            if barcode:
                line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode
            if certificates:
                line_vals["item"]["certificate"] = certificates
            
            if uom_id:
                self._cr.execute('''
                    SELECT
                        name
                    FROM
                        product_uom
                    WHERE id = %s
                    LIMIT 1
                ''', (uom_id,))
                uom, = self._cr.fetchone()
#                 line_vals["_ext_attributes"] = {
#                     "Quantity": {
#                       "unitCode": uom,
#                     }
#                 }
                line_vals['quantity_unit_code'] = uom
                
                
            lot_exp_date= False
            if lot_id:
                self._cr.execute('''
                    SELECT
                        name, expiry_date
                    FROM
                        stock_production_lot
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (lot_id,))
                lot_name, lot_exp_date = self._cr.fetchone()
                line_vals["item"]['item_instance'] = {
                    'lot_identification': {
                        'lot_number': lot_name,
                    }
                }
                if lot_exp_date:
                    line_vals["item"]['item_instance']['lot_identification']['expiry_date'] = lot_exp_date
           
            if container_id or (exp_date and not lot_exp_date):
                if not line_vals["item"].get('item_instance', False):
                    line_vals["item"]['item_instance'] = {}
                    
                if container_id:
                    self._cr.execute('''
                        SELECT
                            container_no
                        FROM
                            account_invoice_container
                        WHERE
                            id = %s
                        LIMIT 1
                    ''', (container_id,))
                    container_no, = self._cr.fetchone()
                    if container_no:
                        line_vals["item"]['item_instance']['additional_item_property'] = [
                            {
                                'name': "ContainerNo",
                                'value': container_no,
                            }
                        ]
                if exp_date and not lot_exp_date:
                    if not line_vals["item"]['item_instance'].get('additional_item_property', False):
                        line_vals["item"]['item_instance']['additional_item_property'] = []
                    line_vals["item"]['item_instance']['additional_item_property'].append({
                        'name': "ExpirationDate",
                        'value': exp_date,
                    })

            # ------------------------------------------ Vytautas {--------------------------------------
            # iš waybill eilutės ieškom invoice eilučių

            self._cr.execute('''
                SELECT
                    rel2.invoice_line_id
                FROM
                    invoice_line_so_line_rel rel1,
                    invoice_line_so_line_rel rel2 
                    JOIN account_invoice_line ail on (rel2.invoice_line_id = ail.id)
                    JOIN account_invoice ai on (ai.id=ail.invoice_id)
                WHERE
                    rel1.invoice_line_id = %s
                    AND rel1.order_line_id = rel2.order_line_id
                    AND ai.category = 'invoice'
            ''', (inv_line_id,))
            related_invoice_line_ids = [rel_line_id[0] for rel_line_id in self.env.cr.fetchall()]
            line_no = 0
            for related_invoice_line_id in related_invoice_line_ids:
                line_no += 1
                related_invoice_line_vals = line_env.browse(related_invoice_line_id).get_invoice_line_vals_for_ubl(line_no)

                if related_invoice_line_vals:
                    if 'invoice_line' not in line_vals:
                        line_vals['invoice_line'] = []
                    line_vals['invoice_line'].append(related_invoice_line_vals)

            if not related_invoice_line_ids:
                # Jei sugeneruotas tiktais waybill, bet invoice nėra vistiek reikia suformuoti
                # invoice_line, kad nusisiųstų nuorodos į despatch

                related_fake_invoice_line_vals = line_env.browse(inv_line_id).get_fake_invoice_line_vals_for_ubl(1)

                if 'invoice_line' not in line_vals:
                    line_vals['invoice_line'] = []
                line_vals['invoice_line'].append(related_fake_invoice_line_vals)


            # ------------------------------------------} Vytautas --------------------------------------

            items_vals.append(line_vals)

        if items_vals:
            res['shipment']['goods_item'] = items_vals
        
        
        if seller_partner_id:
            res['consignor_party'] = partner_env.get_partner_vals(seller_partner_id, for_owner=True)
        if carrier_id:
            carrier_vals = partner_env.get_partner_vals(carrier_id)
            res['carrier_party'] = carrier_vals
#             res['Shipment']["Delivery"]["CarrierParty"] = carrier_vals
#         if partner_shipping_id:
#             res['Shipment']["Delivery"]["DeliveryLocation"] = self.get_partner_location_vals(partner_shipping_id)
#         if despatch_address_id:
#             res['Shipment']["Delivery"]["Despatch"] = {
#                 "DespatchLocation": self.get_partner_location_vals(despatch_address_id)
#             }
#         if driver_id:
#             self._cr.execute('''
#                 SELECT
#                     license_plate
#                 FROM
#                     stock_location
#                 WHERE id = %s
#                 LIMIT 1
#             ''', (driver_id,))
#             sql_res = self._cr.fetchone()
#             if sql_res:
#                 license_plate, = sql_res
#                 if license_plate and license_plate not in ('.','-'):
#                     res['Shipment']['TransportHandlingUnit'] = {
#                         'TransportMeans' : [
#                             {
#                                 'RoadTransport': {
#                                     "_ext_attributes": {
#                                         "LicensePlateID": {
#                                           "schemeID": "TRUCK_NUMBER",
#                                         }
#                                     },
#                                     "LicensePlateID": license_plate,
#                                 }
#                             }
#                         ]
#                     }
#                     
#         containers = []
#         
#         self._cr.execute('''
#             SELECT
#                 distinct(aic.id_external), aic.code
#             FROM
#                 account_invoice_container as aic
#             JOIN account_invoice_container_line as aicl ON (
#                 aicl.container_id = aic.id
#             )
#             JOIN account_invoice_line as ail ON (
#                 aicl.invoice_line_id = ail.id
#             )
#             WHERE ail.invoice_id = %s
#         ''', (self.id,))
#         container_tuples = self._cr.fetchall()
#         for container_tuple in container_tuples:
#             containers.append({
#                 "ID": container_tuple[0],
#                 "HandlingCode": container_tuple[1]
#             })
#         
#         if containers:
#             res['Shipment']['Consignment'] = containers
        return res
    
    @api.multi
    def get_invoice_ubl(self, pretty=False):
        self.ensure_one()
        
        electronical_document_vals = self.get_electronical_invoice_vals()

        data_xml = inv_schema.dumps(
            electronical_document_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )

        return data_xml

    @api.multi
    def get_waybill_ubl(self, pretty=False):
        self.ensure_one()
        electronical_document_vals = self.get_electronical_waybill_vals()
        # json_data = json.dumps(electronical_document_vals)
        # schema_data = wb_schema.loads(json_data)
#         data_xml = wb_schema.dumps(
#             schema_data, content_type='application/xml', encoding='utf8', method='xml', xml_declaration=True
#         )
#         if pretty:
#             return xml.dom.minidom.parseString(data_xml).toprettyxml(encoding='utf-8')
        print('electronical_document_vals', electronical_document_vals)
        data_xml = wb_schema.dumps(
            electronical_document_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )

        return data_xml
    
    @api.multi
    def send_document_eletronic_form(self):
        integration_intermediate_env = self.env['stock.route.integration.intermediate']
        for invoice in self:
            invoice_id_str = str(invoice.id)
            
            invoice_read = invoice.read([
                'category'
            ])
            function = invoice_read['category'] == 'invoice' and "SendElectronicDocumentInvoice"\
                or "SendElectronicDocumentWaybill"
             
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_integration_intermediate
                WHERE id_xml = %s
                    AND function = %s
                LIMIT 1
            ''', (invoice_id_str, function))
            sql_res = self._cr.fetchone()
            if sql_res:
                integration_intermediate = integration_intermediate_env.browse(sql_res[0])
            else:
                integration_intermediate = False #Po to pacreatinsiu su visai duomenim, dabar neverta
   
            if function == "SendElectronicDocumentInvoice":
                data_xml = invoice.get_invoice_ubl(pretty=True)
            else:
                data_xml = invoice.get_waybill_ubl(pretty=True)
            
            intermediate_vals = {
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                'function': function,
#                 'received_values': html.unescape(xml.dom.minidom.parseString(data_xml).toprettyxml()),
                'received_values': data_xml,
                'processed': False,
                'id_xml': invoice_id_str,
                'result': '',
#                 'valid_xml': valid_xml
            }
            if integration_intermediate:
                integration_intermediate.write(intermediate_vals)
            else:
                integration_intermediate = integration_intermediate_env.create(intermediate_vals)
                
            self._cr.execute('''
                UPDATE account_invoice
                SET intermediate_id = %s
                WHERE id = %s
            ''', (integration_intermediate.id, invoice.id))
                
        
        return True
    
    @api.multi
    def send_document(self, printer=False, force_print=False):
        if force_print:
            self.send_document_paper_form(printer=printer)
        else:
            paper_form_documents = self.filtered(lambda inv:\
                inv.sending_type in ('paper', 'paper_edi')
            )
            if paper_form_documents:
                paper_form_documents.send_document_paper_form(printer=printer)
            
        #El. dokumentu atrinkimas pasalintas, nes jie formuojasi ir siunciasi pagal timestamp'a, kai Dycode papraso
            
#         self.send_document_eletronic_form()            
#         electronic_form_documents = self.filtered(lambda inv:\
#             inv.sending_type == 'electronical'
#         )
#         if electronic_form_documents:
#             electronic_form_documents.send_document_eletronic_form()     
        
        return True
        
    
    @api.multi
    def get_document_xml(self, language='LT'):
        from xml.dom.minidom import Document

        def create_node_with_val(doc, node_name, val):
            node = doc.createElement(node_name)
            value = doc.createTextNode(val)
            node.appendChild(value) 
            return node
        
        invoice = self

        invoice_data = invoice.get_print_document_invoice_data()
        seller_data = invoice.get_print_document_seller_data()
        owner_data = invoice.get_print_document_owner_data()
        bank_acc_data = invoice.get_print_document_bank_acc_data()
        carrier_data = invoice.get_print_document_carrier_data()
        client_data = invoice.get_print_document_client_data()
        vat_datas = invoice.get_print_document_vat_datas()
        line_datas = invoice.get_print_document_line_datas()  
        certif_datas = invoice.get_print_document_certif_datas()
        
        
        #----- XML FORMAVIMO PRADZIA  ---------
        doc = Document()
        main_tag = doc.createElement("PrintDoc")
        doc.appendChild(main_tag)
        
        main_tag.setAttribute("Type", "REPWIN")
        main_tag.setAttribute("Language", "LT")
        main_tag.setAttribute("Form", invoice.get_print_document_invoice_type())
        # ----------- DATA ---------------
        data_tag = doc.createElement("Data")
        main_tag.appendChild(data_tag)
        
        # ----------- Invoice ---------------
        
        invoice_tag = doc.createElement("Invoice")
        data_tag.appendChild(invoice_tag)
        
        for invoice_data_key in invoice_data.keys():
            invoice_tag.appendChild(create_node_with_val(doc, invoice_data_key, invoice_data[invoice_data_key]))
        
        # ----------- Seller ---------------
        
        seller_tag = doc.createElement("Seller")
        data_tag.appendChild(seller_tag)
        
        for seller_data_key in seller_data.keys():
            seller_tag.appendChild(create_node_with_val(doc, seller_data_key, seller_data[seller_data_key]))
            
        # ----------- Owner ---------------
        
        owner_tag = doc.createElement("Owner")
        data_tag.appendChild(owner_tag)
         
        for owner_data_key in owner_data.keys():
            owner_tag.appendChild(create_node_with_val(doc, owner_data_key, owner_data[owner_data_key]))
         
        # ----------- Seller Bank Account ---------------
         
        bank_acc_tag = doc.createElement("SellerBankAccount")
        data_tag.appendChild(bank_acc_tag)
         
        for bank_acc_data_key in bank_acc_data.keys():
            bank_acc_tag.appendChild(create_node_with_val(doc, bank_acc_data_key, bank_acc_data[bank_acc_data_key]))
         
        # ----------- Carrier ---------------
         
        carrier_tag = doc.createElement("Carrier")
        data_tag.appendChild(carrier_tag)
         
        for carrier_data_key in carrier_data.keys():
            carrier_tag.appendChild(create_node_with_val(doc, carrier_data_key, carrier_data[carrier_data_key]))
             
        # ----------- Client ---------------
         
        client_tag = doc.createElement("Client")
        data_tag.appendChild(client_tag)
         
        for client_data_key in client_data.keys():
            client_tag.appendChild(create_node_with_val(doc, client_data_key, client_data[client_data_key]))
          
        # ----------- VAT Line ---------------
        for vat_data in vat_datas:
            vat_tag = doc.createElement("VatLine")
            data_tag.appendChild(vat_tag)
             
            for vat_data_key in vat_data.keys():
                vat_tag.appendChild(create_node_with_val(doc, vat_data_key, vat_data[vat_data_key]))
                 
        # ----------- Line ---------------
        for line_data in line_datas:
            line_tag = doc.createElement("Line")
            data_tag.appendChild(line_tag)
             
            for line_data_key in line_data.keys():
                line_tag.appendChild(create_node_with_val(doc, line_data_key, line_data[line_data_key]))
                 
        # ----------- LineSertif ---------------
        for certif_data in certif_datas:
            certif_tag = doc.createElement("LineSertif")
            data_tag.appendChild(certif_tag)
             
            for certif_data_key in certif_data.keys():
                certif_tag.appendChild(create_node_with_val(doc, certif_data_key, certif_data[certif_data_key]))

        xml_string = doc.toxml(encoding='utf-8')
        
#             invoice_document_report.print_report(self, record, printer=None, reprint_reason=None, copies=None, data=None):
#             file_path = self.env['printer'].get_report(xml_string, "Dokumentas")
#             printer.linux_print(file_path, copies=(invoice.print_copies or 1))

        return xml_string
    
    @api.multi
    def get_pdf_report(self, report, language='LT'):
        xml = self.get_document_xml(language)
        return self.env['printer'].get_report(xml, report)
    
#     @api.multi
#     def get_customer_despatch_vals(self):
#         self.ensure_one()
#         
#         issue_date, issue_time = self.get_issue_date_and_time() or ("", "")
#         
#         self._cr.execute('''
#             SELECT
#                 owner_partner_id, seller_partner_id, name,
#                 comment, partner_id,
#                 one_time_partner_id, seller_partner_id,
#                 owner_id
#             FROM
#                 account_invoice
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         owner_partner_id, seller_partner_id, name,\
#         note, buyer_partner_id, one_time_partner_id,\
#         seller_partner_id, owner_id = self._cr.fetchone()
#         
#         if owner_partner_id and seller_partner_id and seller_partner_id != owner_partner_id:
#             shipment_type = "InterCompany"
#         else:
#             shipment_type = "TransDepot"
#         
#         res = {
#             "ubl_extensions": {
#                 "ubl_extension": [
#                     {
#                         "extension_reason_code": "DESPATCH_ADVICE",
#                         "extension_content": {
#                             "settings": {
#                                 "document_source_id": self.get_id_source_doc(),
#                                 "shipment_type": shipment_type,
#                             }
#                         }
#                     
#                     }
#                 ]
#             },
#             "ubl_version_id": "2.1",
#             "customization_id": "BLS",
#             "id": name,
# #             "IssueDate": issue_date,
# #             "IssueTime": issue_time,
#             "shipment": self.get_shipment_vals(),
#         }
#         
#         if note:
#            res['note'] = note
#         if issue_date:
#             res['issue_date'] = issue_date
#         if issue_time:
#             res['issue_time'] = issue_time
#            
#         buyer_vals = False
#         if buyer_partner_id:
#             buyer_vals = {"party": self.get_partner_vals(buyer_partner_id)}
#         elif one_time_partner_id:
#             buyer_vals = {"party": self.get_one_time_partner_vals(one_time_partner_id)}
#         if buyer_vals:
#             res['buyer_customer_party'] = buyer_vals
#             res['delivery_customer_party'] = buyer_vals
#             
#         if not seller_partner_id:
#             raise UserError(
#                 _('Seller partner is missing.')
#             )
#             
#         seller_vals = {"party": self.get_partner_vals(seller_partner_id)}
#         res['seller_supplier_party'] = seller_vals
#         res['despatch_supplier_party'] = seller_vals
#             
#         if owner_partner_id:
#             owner_code = False
#             if owner_id:
#                 self._cr.execute('''
#                     SELECT
#                         owner_code
#                     FROM
#                         product_owner
#                     WHERE id = %s
#                     LIMIT 1
#                 ''', (owner_id,))
#                 owner_code, = self._cr.fetchone()
#             
#             res['seller_supplier_party'] = self.get_partner_vals(owner_partner_id, owner_code=owner_code)
#             
#         lines_vals_list = []
#         self._cr.execute('''
#             SELECT
#                 id
#             FROM
#                 account_invoice_line
#             WHERE invoice_id = %s
#         ''', (self.id,))
#         line_counter = 0
#         inv_line_ids_tuple_list = self._cr.fetchall()
#         for invoice_line_id, in inv_line_ids_tuple_list:
# #             line_counter += 1 
#             self._cr.execute('''
#                 SELECT
#                     uom_id, product_id, quantity,
#                     transportation_order_line_id
#                 FROM
#                     account_invoice_line
#                 WHERE id = %s
#                 LIMIT 1
#             ''', (invoice_line_id,))
#             uom_id, prod_id, inv_line_qty,\
#             transportation_order_line_id = self._cr.fetchone()
#             
#             
#             id_ord = False
#             id_ord_line = False
# #             if transportation_order_line_id:
# #                 self._cr.execute('''
# #                     SELECT
# #                         ordl.id_line, ord.name
# #                     FROM
# #                         transportation_order_line AS ordl
# #                     JOIN transportation_order AS ord ON (
# #                         ordl.transportation_order_id = ord.id
# #                     )
# #                     WHERE ordl.id = %s
# #                     LIMIT 1
# #                 ''', (transportation_order_line_id,))
# #                 id_ord_line, id_ord = self._cr.fetchone()
# 
#             if transportation_order_line_id:
#                 self._cr.execute('''
#                     SELECT
#                         ordl.id_line, ord.name
#                     FROM
#                         transportation_order_line AS ordl
#                     JOIN transportation_order AS ord ON (
#                         ordl.transportation_order_id = ord.id
#                     )
#                     WHERE ordl.id = %s
#                     LIMIT 1
#                 ''', (transportation_order_line_id,))
#                 sql_res = self._cr.fetchone()
#                 if not sql_res:
#                     self._cr.execute('''
#                         SELECT
#                             ordl.id_line, ord.name
#                         FROM
#                             transportation_order_line AS ordl
#                         JOIN transportation_order_line AS parent_l ON (
#                             ordl.parent_line_id = parent_l.id
#                         )
#                         JOIN transportation_order AS ord ON (
#                             parent_l.transportation_order_id = ord.id
#                         )
#                         WHERE ordl.id = %s
#                         LIMIT 1
#                     ''', (transportation_order_line_id,))
#                     sql_res = self._cr.fetchone()
#                 if sql_res:
#                     id_ord_line, id_ord = sql_res
#             
#             uom = False    
#             if uom_id:
#                 self._cr.execute('''
#                     SELECT
#                         name
#                     FROM
#                         product_uom
#                     WHERE id = %s
#                     LIMIT 1
#                 ''', (uom_id,))
#                 uom, = self._cr.fetchone()
#                 
#             self._cr.execute('''
#                 SELECT
#                     pt.name, pp.default_code
#                 FROM
#                     product_product AS pp
#                 JOIN product_template AS pt ON (
#                     pp.product_tmpl_id = pt.id
#                 )
#                 WHERE pp.id = %s
#                 LIMIT 1
#             ''', (prod_id,))
#             prod_name, default_code = self._cr.fetchone()
#                 
#             
#             self._cr.execute('''
#                 SELECT
#                     id
#                 FROM
#                     account_invoice_container_line
#                 WHERE invoice_line_id = %s
#             ''', (invoice_line_id,))
#             container_line_ids_tuple_list = self._cr.fetchall()
#             
#             
#             #Eilute, gali buti nesusijusi tiesiogiai (Pavayzdziui buvo koreguojamas dokumentas)
#             if not container_line_ids_tuple_list:
#                 self._cr.execute('''
#                     SELECT
#                         container_line_id
#                     FROM
#                         invoice_line_container_line_rel
#                     WHERE invoice_line_id = %s
#                 ''', (invoice_line_id,))
# 
#                 container_line_ids_tuple_list = self._cr.fetchall()
#               
#             for container_line_id, in container_line_ids_tuple_list:
#                 line_counter += 1
#                 self._cr.execute('''
#                     SELECT
#                         qty, barcode_str
#                     FROM
#                         account_invoice_container_line
#                     WHERE id = %s
#                     LIMIT 1
#                 ''', (container_line_id,))
#                 container_line_qty, barcode_str = self._cr.fetchone()
#                 
#                 if not inv_line_qty:
#                     break
#                 elif container_line_qty <= inv_line_qty:
#                     qty = container_line_qty
#                     inv_line_qty -= container_line_qty
#                 else:
#                     qty = inv_line_qty
#                     inv_line_qty = 0.0
#                 
#   
#                 line_vals = {
#                     "id": str(line_counter),
#                     "delivered_quantity": "%.3f" % (qty),
#                     "item": {
#                         "description": prod_name,
#                         "additional_item_identification": [
#                             {
#                                 "id": default_code,
# #                                 "_ext_attributes": {
# #                                     "id": {
# #                                       "schemeID": "PRODUCT_CODE",
# #                                       "schemeName": "Product code",
# #                                       "scheme_agency_id": "BLS"
# #                                     }
# #                                 },
#                                 "schemeID": "PRODUCT_CODE",
#                                 "schemeName": "Product code",
#                                 "scheme_agency_id": "BLS"
#                             }
#                         ]
#                     }
#                 }
#                 
#                 if barcode_str:
#                     line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode_str
#             
#                 certificates = []
#                 self._cr.execute('''
#                     SELECT
#                         certificate_id
#                     FROM
#                         container_line_certificate_rel
#                     WHERE container_line_id = %s
#                 ''', (container_line_id,))
#                 certificate_ids_tuple_list = self._cr.fetchall()
#                 for certificate_id, in certificate_ids_tuple_list:
#                     self._cr.execute('''
#                         SELECT
#                             name, type, issued_by,
#                             issue_date, valid_from, valid_to
#                         FROM
#                             product_certificate
#                         WHERE id = %s
#                         LIMIT 1
#                     ''', (certificate_id,))
#                     cert_name, cert_type, cert_issued_by,\
#                     cert_issue_date, cert_valid_from, cert_valid_to = self._cr.fetchone()
#                      
#                     cert_vals = {
#                         'id': cert_name,
#                         'certificate_type': cert_type,
#                         'certificate_type_code': cert_type,
#                         'issuer_party': {
#                             'party_name': {
#                                 'name': cert_issued_by or '-',
#                             }
#                         },
#                     }
#                      
#                     if cert_issue_date or (cert_valid_from and cert_valid_to):
#                         cert_vals["document_reference"] = {
#                             "id": '.', #????????
#                         }
# #                         if cert_issue_date:
# #                             cert_vals["document_reference"]["issue_date"] = cert_issue_date
# #                         if cert_valid_from and cert_valid_to:
# #                             cert_vals["document_reference"]["validity_period"] = {
# #                                 "start_date": cert_valid_from,
# #                                 "end_date": cert_valid_to,
# #                             }
# 
#                         if cert_issue_date:
#                             cert_issue_date = datetime.datetime.strptime(
#                                 cert_issue_date, "%Y-%m-%d"
#                             ).date()
#                             cert_vals["document_reference"]["issue_date"] = cert_issue_date
#                         if cert_valid_from and cert_valid_to:
#                             cert_vals["document_reference"]["validity_period"] = {
#     #                             "start_date": cert_valid_from,
#     #                             "end_date": cert_valid_to,
#                                 "start_date": datetime.datetime.strptime(
#                                     cert_valid_from, "%Y-%m-%d"
#                                 ).date(),
#                                 "end_date": datetime.datetime.strptime(
#                                     cert_valid_to, "%Y-%m-%d"
#                                 ).date(),
#                             }                      
#                     certificates.append(cert_vals)
#                     
#                 if certificates:
#                     line_vals["item"]["certificate"] = certificates
#                     
#                     
#                 self._cr.execute('''
#                     SELECT
#                         lot_id
#                     FROM
#                         container_line_lot_rel
#                     WHERE container_line_id = %s
#                     LIMIT 1
#                 ''', (container_line_id,))
#                 sql_res = self._cr.fetchone()
#                 
#                 if sql_res:
# #                 for lot_id, in lot_ids_tuple_list:
#                     lot_id, = sql_res
#                     self._cr.execute('''
#                         SELECT
#                             name, expiry_date
#                         FROM
#                             stock_production_lot
#                         WHERE id = %s
#                         LIMIT 1
#                     ''', (certificate_id,))
#                     lot_cert_name, lot_expiry_date = self._cr.fetchone()
#                     
#                     line_vals["item_instance"] = {
#                         "lot_identification": {
#                             'lot_number_id': lot_cert_name,
# #                             'expiry_date': lot_expiry_date,
#                             'expiry_date': datetime.datetime.strptime(
#                                 lot_expiry_date, "%Y-%m-%d"
#                             )
#                         }
#                     }
#                      
#                 if id_ord_line:
#                     line_vals['order_line_reference'] = {
#                         'line_id': id_ord_line
#                     }
#                     if id_ord:
#                         line_vals['order_line_reference']['order_reference'] = {"id": id_ord}
#                        
#                 lines_vals_list.append(line_vals)
#         
#   
#         if not lines_vals_list:
#             return False
#         res['despatch_line'] = lines_vals_list
#         
#         return res
#     
#     @api.multi
#     def get_customer_despatch_ubl(self, pretty=False):
#         self.ensure_one()
#         customer_despatch_vals = self.get_customer_despatch_vals()
#         if not customer_despatch_vals:
#             return False
# #         json_data = json.dumps(customer_despatch_vals)
# #         if not json_data:
# #             return False
# #         schema_data = da_schema.loads(json_data)
# #         data_xml = da_schema.dumps(
# #             schema_data, content_type='application/xml', encoding='utf8', method='xml', xml_declaration=True
# #         )
# #         if pretty:
# #             return xml.dom.minidom.parseString(data_xml).toprettyxml(encoding='utf-8')
# 
#         data_xml = da_schema.dumps(
#             customer_despatch_vals, content_type='application/xml', encoding='utf8', method='xml',
#             xml_declaration=True, pretty_print=pretty
#         )
# 
#         return data_xml
#     
#     @api.multi
#     def form_customer_despatch(self):
#         integration_intermediate_env = self.env['stock.route.integration.intermediate']
#         
#         for invoice in self:
#             invoice_id_str = str(invoice.id)
#             self._cr.execute('''
#                 SELECT
#                     id
#                 FROM
#                     stock_route_integration_intermediate
#                 WHERE id_xml = %s
#                     AND function = 'SendCustomerDespatchAdvice'
#                 LIMIT 1
#             ''', (invoice_id_str,))
#             sql_res = self._cr.fetchone()
#             if sql_res:
#                 integration_intermediate = integration_intermediate_env.browse(sql_res[0])
#             else:
#                 integration_intermediate = False #Po to pacreatinsiu su visai duomenim, dabar neverta
#                 
# #             customer_despatch_vals = invoice.get_customer_despatch_vals()
# #             json_data = json.dumps(customer_despatch_vals)
# #             schema_data = da_schema.loads(json_data)
# #             data_xml = da_schema.dumps(schema_data, content_type='application/xml')
#             data_xml = invoice.get_customer_despatch_ubl()
#             
#             intermediate_vals = {
#                 'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
#                 'function': 'SendCustomerDespatchAdvice',
#                 'received_values': data_xml,
#                 'processed': False,
#                 'id_xml': invoice_id_str,
#                 'return_results': '',
#             }
#             if integration_intermediate:
#                 integration_intermediate.write(intermediate_vals)
#             else:
#                 integration_intermediate = integration_intermediate_env.create(intermediate_vals)
# 
#             self._cr.execute('''
#                 UPDATE account_invoice
#                 SET customer_despatch_intermediate_id = %s
#                 WHERE id = %s
#             ''', (integration_intermediate.id, invoice.id))
# 
#         return True
    
    @api.multi
    def thread_actions_after_document_generate(self):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            save_test_ubls_to_disk = new_self.env.user.company_id.save_test_ubs_to_disk
            try:
                new_self.create_stock_pickings()
                if save_test_ubls_to_disk:
                    new_self.form_and_save_to_disk()
                new_cr.commit()
            finally:
                new_cr.close()
        return True
    
    
    
    @api.multi
    def actions_after_document_generate(self):
        
        t = threading.Thread(target=self.thread_actions_after_document_generate)
        t.start()
#         self.form_customer_despatch()
#         self.create_stock_pickings()
        
        return True
    
    @api.multi
    def get_doc_edit_config(self):
        self.ensure_one()
        doc_edit_config_env = self.env['account.invoice.edit.config']
        doc_edit_config_id = False
        
        self._cr.execute('''
            SELECT
                powner.document_edit_config_id
            FROM
                product_owner AS powner
            JOIN
                account_invoice AS inv ON (
                    inv.owner_id = powner.id
                )
            WHERE inv.id = %s
                AND powner.document_edit_config_id IS NOT NULL
            LIMIT 1
        ''', (self.id,))
        sql_res = self._cr.fetchone()
        if sql_res:
            doc_edit_config_id = sql_res[0] or False
            
        if not doc_edit_config_id:
            self._cr.execute('''
                SELECT
                    document_edit_config_id
                FROM
                    res_company
                WHERE id = %s
                    AND document_edit_config_id IS NOT NULL
                LIMIT 1
            ''', (self.env.user.company_id.id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                doc_edit_config_id = sql_res[0] or False
                
        if not doc_edit_config_id:
            raise UserError(
                _('Document edit configuration must be filled in the owner info or company configuration.')
            )
            
        return doc_edit_config_env.browse(doc_edit_config_id)
        
    @api.multi
    def check_if_doc_can_be_edited(self):
        self.ensure_one()
         
        doc_edit_config = self.get_doc_edit_config()
        if doc_edit_config.days < 1:
            return True
        self._cr.execute('''
            SELECT
                date_invoice
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        date_invoice, = self._cr.fetchone()
        days = doc_edit_config.days
        if date_invoice:
            if doc_edit_config.type == 'month_day':
                day_str = str(days)
                if len(day_str) > 2:
                    day_str = '31'
                elif len(day_str) == 1:
                    day_str = '0'+day_str
                
#                 if date_invoice[-2:] <= day_str:
#                     target_date = date_invoice[:-2] + day_str
#                 else:
                years = date_invoice[:4]
                month = date_invoice[5:7]
                month_int = int(month) + 1
                if month_int == 13:
                    years = str(int(years)+1)
                    month = "01"
                else:
                    month = str(month_int)
                    if len(month) == 1:
                        month = '0'+ month
                target_date = "%s-%s-%s" % (years, month, day_str)
            else:
                date_invoice_date_time = datetime.datetime.strptime(date_invoice, '%Y-%m-%d')
                date_invoice_date_time += datetime.timedelta(days=days)
                target_date = date_invoice_date_time.strftime('%Y-%m-%d')
                
    #!!! Kodas gali atrodyti nesmaoningai, bet kai lyginame string'us, tai mums jokio skirtumo, jei vasaris tures ir 31 diena
            if time.strftime('%Y-%m-%d') > target_date:
                raise UserError(
                    _('This document can not be edited anymore.')
                )
             
        return True
    
    @api.multi
    def document_edit_button(self):
        self.ensure_one()
        form_view = self.env.ref('config_bls_stock.view_acc_invoice_bls_stock_document_form', False)[0]
#         self.write({'edit_mode': True})

        self._cr.execute('''
            UPDATE account_invoice
            SET edit_mode = true
            WHERE id = %s
        ''', (self.id,))

        context = self._context.copy()
        context['form_view_initial_mode'] = 'edit'
        context['force_detailed_view'] = True
        context['document_edit'] = True
        context['do_not_create_breadcrumb'] = True

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'target': 'self',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id,'form')],
            'res_id': self.id,
            'nodestroy': False,
            'context': context,
        }
        
    @api.multi
    def document_save_button(self):
        self.ensure_one()
        invoice_env = self.env['account.invoice']
#         try:
#             annul_doc = invoice_env.search([('primary_invoice_id','=',self.id)])
#             edited_doc = invoice_env.search([('primary_invoice_id','=',annul_doc.id)])
#             annul_doc.actions_after_document_generate()
#             new_doc.actions_after_document_generate()
#         except:
#             raise

        self._cr.execute('''
            UPDATE account_invoice
            SET edit_mode = false
            WHERE id = %s
        ''', (self.id,))

        context = self._context.copy()
        context['form_view_initial_mode'] = 'readonly'

        form_view = self.env.ref('config_bls_stock.view_acc_invoice_bls_stock_document_form', False)[0]

        annul_doc = invoice_env.search([('primary_invoice_id','=',self.id)])
        if not annul_doc: #Taip nutinka, kai pavyzdziui bando issaugoti nieko nepakeitus
            context['do_not_create_breadcrumb'] = True
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'target': 'self',
                'type': 'ir.actions.act_window',
                'views': [(form_view.id,'form')],
                'res_id': self.id,
                'nodestroy': False,
                'context': context,
            }
        
        edited_doc = invoice_env.search([('primary_invoice_id','=',annul_doc.id)])
#         annul_doc.actions_after_document_generate()
#         edited_doc.actions_after_document_generate()
        (annul_doc + edited_doc).actions_after_document_generate() #geriau paduoti kartu, kad atskiros gijos nesikreiptu i ta pati sequenca
        
        context['do_not_create_breadcrumb'] = False
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'target': 'self',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id,'form')],
            'res_id': edited_doc.id,
            'nodestroy': False,
            'context': context,
        }
        
    @api.multi
    def document_cancel_edit_button(self):
        self.ensure_one()
        self._cr.execute('''
            UPDATE account_invoice
            SET edit_mode = false
            WHERE id = %s
        ''', (self.id,))
        form_view = self.env.ref('config_bls_stock.view_acc_invoice_bls_stock_document_form', False)[0]
        context = self._context.copy()
        context['form_view_initial_mode'] = 'readonly'
        context['do_not_create_breadcrumb'] = True
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'target': 'self',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id,'form')],
            'res_id': self.id,
            'nodestroy': False,
            'context': context,
        }

    @api.multi
    def write(self, vals):
        context = self._context or {}
        if vals and context.get('document_edit', False):
            self.ensure_one()
            vals['edit_mode'] = False
            new_doc = self.with_context(document_edit=False, primary_lines_vals=True).document_edit()
            res = super(AccountInvoice, new_doc.with_context(document_edit=False)).write(vals)
            new_doc.with_context(recompute=False)._onchange_invoice_line_ids()
        else:
            res = super(AccountInvoice, self.with_context(document_edit=False)).write(vals)
        return res
    
    @api.multi
    def document_edit(self):
        self.ensure_one()
        self.check_if_doc_can_be_edited()
        doc_type_env = self.env['document.type']
        warehouse_env = self.env['stock.warehouse']
        owner_env = self.env['product.owner']

        self._cr.execute("""
            SELECT
                name, name_generated_in_atlas, category, owner_id
            FROM
                account_invoice
            WHERE id = %s
            LIMIT 1
        """ , (self.id,))
        name, name_generated_in_atlas, category, owner_id = self._cr.fetchone()
         
        annul_doc = self.with_context(allow_inv_copy=True).copy({
            'state': 'cancel',
            'primary_invoice_id': self.id,
            'invoice_line_ids': [],
            'date_invoice': time.strftime('%Y-%m-%d'),
            'name': name,
            'edit_mode': False,
            'annul_document': True,
            'tax_line_ids': []
        })
        if name_generated_in_atlas:
            user = self.env.user
            warehouse_id = user.get_main_warehouse_id()
#             if not warehouse_id:
#                 raise UserError(
#                     _('Please select warehouse you are working in')
#                 )
            warehouse = warehouse_env.browse(warehouse_id)
            owner = owner_env.browse(owner_id)
            if category == 'invoice':
                document_type_code = 'document.invoice'
            elif category == 'waybill':
                document_type_code = 'document.waybill'
            else:
                document_type_code = False
            
            new_doc_name = doc_type_env.get_next_number_by_code(document_type_code, warehouse, owner)
        else:
            new_doc_name = name

        new_doc = self.with_context(allow_inv_copy=True).copy({
            'primary_invoice_id': annul_doc.id,
            'date_invoice': time.strftime('%Y-%m-%d'),
            'name': new_doc_name,
            'invoice_line_ids': [],
            'need_after_create_actions': True,
            'edit_mode': False,
            'tax_line_ids': []
        })
         
        for inv_line in self.invoice_line_ids:
            container_line_ids = []
            self._cr.execute("""
                SELECT
                    container_line_id
                FROM
                    invoice_line_container_line_rel
                WHERE
                    invoice_line_id = %s
                ORDER BY
                    container_line_id
            """ , (inv_line.id,))
            sql_res = self._cr.fetchall()
            if sql_res:
                container_line_ids = [i[0] for i in sql_res]
             
            self._cr.execute("""
                SELECT
                    quantity
                FROM
                    account_invoice_line
                WHERE id = %s
                LIMIT 1
            """ , (inv_line.id,))
            qty, = self._cr.fetchone()
             
            annul_inv_line = inv_line.copy({
                'invoice_id': annul_doc.id,
                'quantity': -1*qty,
            })
             
            new_inv_line = inv_line.copy({
                'invoice_id': new_doc.id,
                'primary_invoice_line_id': inv_line.id,
            })
             
            for container_line_id in container_line_ids:
                self._cr.execute("""
                    SELECT * FROM invoice_line_container_line_rel
                    WHERE container_line_id = %s AND invoice_line_id = %s
                """, (container_line_id, annul_inv_line.id,))
                if not self._cr.fetchall():
                    self._cr.execute("""
                        INSERT INTO invoice_line_container_line_rel
                            (container_line_id, invoice_line_id)
                        VALUES
                            (%s, %s)
                    """, (container_line_id, annul_inv_line.id,))
                self._cr.execute("""
                    SELECT * FROM invoice_line_container_line_rel
                    WHERE container_line_id = %s AND invoice_line_id = %s
                """, (container_line_id, new_inv_line.id,))
                if not self._cr.fetchall():
                 
                    self._cr.execute("""
                        INSERT INTO invoice_line_container_line_rel
                            (container_line_id, invoice_line_id)
                        VALUES
                            (%s, %s)
                    """, (container_line_id, new_inv_line.id,))
             
        annul_doc._onchange_invoice_line_ids()
        
        self._cr.execute('''
            UPDATE account_invoice
            SET state = 'cancel'
            WHERE id = %s
        ''', (self.id,))
        
        return new_doc
    
    @api.multi
    def document_annul(self):
        annul_invoices = self.env['account.invoice']
        for invoice in self:
            invoice.check_if_doc_can_be_edited()
            self._cr.execute("""
                SELECT
                    name
                FROM
                    account_invoice
                WHERE id = %s
                LIMIT 1
            """ , (invoice.id,))
            name, = self._cr.fetchone()
            annul_doc = invoice.with_context(allow_inv_copy=True).copy({
                'state': 'cancel',
                'primary_invoice_id': invoice.id,
                'invoice_line_ids': [],
                'date_invoice': time.strftime('%Y-%m-%d'),
                'name': name,
                'edit_mode': False,
                'annul_document': True,
            })
            
            for inv_line in invoice.invoice_line_ids:
                container_line_ids = []
                self._cr.execute("""
                    SELECT
                        container_line_id
                    FROM
                        invoice_line_container_line_rel
                    WHERE
                        invoice_line_id = %s
                    ORDER BY
                        container_line_id
                """ , (inv_line.id,))
                sql_res = self._cr.fetchall()
                if sql_res:
                    container_line_ids = [i[0] for i in sql_res]
                 
                self._cr.execute("""
                    SELECT
                        quantity
                    FROM
                        account_invoice_line
                    WHERE id = %s
                    LIMIT 1
                """ , (inv_line.id,))
                qty, = self._cr.fetchone()
                 
                annul_inv_line = inv_line.copy({
                    'invoice_id': annul_doc.id,
                    'quantity': -1*qty,
                })
                 
                for container_line_id in container_line_ids:
                    self._cr.execute("""
                        INSERT INTO invoice_line_container_line_rel
                            (container_line_id, invoice_line_id)
                        VALUES
                            (%s, %s)
                    """, (container_line_id, annul_inv_line.id,))

            annul_doc._onchange_invoice_line_ids()
        
            self._cr.execute('''
                UPDATE account_invoice
                SET state = 'cancel'
                WHERE id = %s
            ''', (invoice.id,))
            
            annul_invoices += annul_doc
            
        return annul_invoices
        
    @api.multi
    def document_annul_button(self):
        self.ensure_one()
        self.document_annul()
        
        form_view = self.env.ref('config_bls_stock.view_acc_invoice_bls_stock_document_form', False)[0]
        context = self._context.copy()
        context['form_view_initial_mode'] = 'readonly'
        context['do_not_create_breadcrumb'] = True
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'target': 'self',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id,'form')],
            'res_id': self.id,
            'nodestroy': False,
            'context': context,
        }
    
    @api.multi
    def form_and_save_to_disk(self):
        intermediate_env = self.env['stock.route.integration.intermediate']
        for invoice in self:
            invoice_read = invoice.read([
                'category', 'name'
            ])[0]
            categ = invoice_read['category']
            inv_name = invoice_read['name']
            if categ == 'invoice':
                doc_ubl_xml = invoice.get_invoice_ubl(pretty=True)
            elif categ == 'waybill':
                doc_ubl_xml = invoice.get_waybill_ubl(pretty=True)
            else:
                doc_ubl_xml = False
            if doc_ubl_xml:
                intermediate_env.xml_save_to_file(doc_ubl_xml, '%s_%s' % (categ, inv_name))
                 
        return True

#------------------ PERKELIAU I STOCK -----------------     
#    
#     @api.multi
#     def thread_ubl_save_to_disk(self):
#         with Environment.manage():
#             new_cr = self.pool.cursor()
#             new_self = self.with_env(self.env(cr=new_cr))
#             try:
#                 for invoice in new_self:
#                     invoice_read = invoice.read([
#                         'category', 'name'
#                     ])[0]
#                     categ = invoice_read['category']
#                     inv_name = invoice_read['name']
#                     if categ == 'invoice':
#                         doc_ubl_xml = invoice.get_invoice_ubl()
#                     elif categ == 'waybill':
#                         doc_ubl_xml = invoice.get_waybill_ubl()
#                     else:
#                         doc_ubl_xml = False
#                     if doc_ubl_xml:
#                         new_self.xml_save_to_file(doc_ubl_xml, file_name = '%s_%s' % (categ, inv_name))
#                         
#                     customer_despatch_ubl_xml = invoice.get_customer_despatch_ubl()
#                     new_self.xml_save_to_file(customer_despatch_ubl_xml, file_name = 'customer_despatch_%s' % (inv_name,))
#                 new_cr.commit()
#             finally:
#                 new_cr.close()
#         return True
#     
#     
#     
#     @api.multi
#     def ubl_save_to_disk_call(self):
#         t = threading.Thread(target=self.thread_ubl_save_to_disk)
#         t.start()
#         return True

#     @api.model
#     def get_ubl_documents_json_vals(self, id_version, ubl_doc):
# #         res = {}
#         res = []
#         start_datetime = datetime.datetime.now()
#         integration_intermediate_env = self.env['stock.route.integration.intermediate']
# 
#         domain = [('id_version','>',id_version), ('generated_in_atlas','=',True)]
#         
#         
#         if ubl_doc == 'invoice':
#             domain += [('category','=',ubl_doc)]
#             # Dabar kazkodel ateina vien tik dokumentai, kurie praso PAPER formos, tad kad butu galima testuotis paduodam visus
# #             domain += [('sending_type','in',('electronical', 'paper_edi'))]
#             function = "SendElectronicDocumentInvoice"
#             method = 'get_invoice_ubl'
#         elif ubl_doc == 'waybill':
#             # Dabar kazkodel ateina vien tik dokumentai, kurie praso PAPER formos, tad kad butu galima testuotis paduodam visus
# #             domain += [('sending_type','in',('electronical', 'paper_edi'))]
#             domain += [('category','=',ubl_doc)]
#             function = "SendElectronicDocumentWaybill"
#             method = 'get_waybill_ubl'
#         elif ubl_doc == 'despatch':
#             function = "SendCustomerDespatchAdvice"
#             method = 'get_customer_despatch_ubl'
#             
#             #TODO: issiaskinti ar tirkai
#             domain += [('category','=','waybill')] #Nes lygtais waybill formuojame visada ir dar kartais papildomai invoice
#         else:
#             function = ""
#             
#         receive_vals = "<ubl_doc> - %s\n<id_version> - %s" % (ubl_doc, id_version)
#         result_vals = ''
#         processed = True
#         trb = ''
#             
#         intermediate = integration_intermediate_env.create({
#             'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
#             'function': function,
#             'received_values': receive_vals,
#             'processed': False
#         })
#         self.env.cr.commit()
#         
#         try:
#             doc_limit = self.env.user.company_id.ubl_export_limit 
#             documents = self.search(domain, limit=doc_limit, order='id_version ASC')
#             for document in documents:
# #                 ubl_xml = getattr(document, method)().decode('utf-8').encode('unicode-escape')
#                 ubl_xml = getattr(document, method)()
#                 if not ubl_xml:
#                     continue
#                 ubl_xml = ubl_xml.decode('utf-8')
#                 
#                 self._cr.execute('''
#                     SELECT
#                         id_version
#                     FROM
#                         account_invoice
#                     WHERE id = %s
#                     LIMIT 1
#                 ''', (document.id,))
#                 id_version, = self._cr.fetchone()
#                 
# #                 xsd_validation_error = self.check_xsd_validity(ubl_xml, ubl_doc)
# #                 if xsd_validation_error:
# #                     print ("\n\n\n xsd_validation_error: ", xsd_validation_error, id_version)
#                 
#                 res.append(
#                     {
#                         'id_version': id_version,
#                         'data': ubl_xml
#                     }
#                 )
# #                 res[id_version] = ubl_xml
# 
# #             result_vals += _('Result: ') + '\n\n' + str(json.dumps(res, indent=2))
#             result_vals += _('Result: ') + '\n\n' + str(json.dumps(res, indent=2))
#             if documents:
#                 if ubl_doc == 'despatch':
#                      self._cr.execute('''
#                         UPDATE account_invoice
#                         SET customer_despatch_intermediate_id = %s
#                         WHERE id in %s
#                     ''', (intermediate.id, tuple(documents.ids)))
#                 else:
#                     self._cr.execute('''
#                         UPDATE account_invoice
#                         SET intermediate_id = %s
#                         WHERE id in %s
#                     ''', (intermediate.id, tuple(documents.ids))) 
#         except Exception as e:
#             err_note = _('Failed to return %s UBLs: %s') % (ubl_doc, tools.ustr(e),)
#             result_vals += err_note
#             processed = False
#             trb += traceback.format_exc() + '\n\n'
#             self.env.cr.rollback()
#         
#         end_datetime = datetime.datetime.now()
#         
#         intermediate.write({
#             'processed': processed,
#             'return_results': result_vals,
#             'traceback_string': trb,
#             'duration': (end_datetime-start_datetime).seconds
#         })
#         self.env.cr.commit()
#         
#         return processed and res or "Error"
    
    @api.model
    def check_xsd_validity(self, xml_data, doc_categ):
        main_xsd_path = os.path.join(_XSDS_PATH, 'maindoc')
        bls_settings_xsd_path = os.path.join(_XSDS_PATH, 'bls', 'BlsSettings-1.0.xsd')
        
        if doc_categ == 'invoice':
            xsd_path = os.path.join(main_xsd_path, 'UBL-Invoice-2.1.xsd')
        elif doc_categ == 'waybill':
            xsd_path = os.path.join(main_xsd_path, 'UBL-Waybill-2.1.xsd')
        elif doc_categ == 'despatch':
            xsd_path = os.path.join(main_xsd_path, 'UBL-DespatchAdvice-2.1.xsd')
        else:
            return False
        
        xsd = etree.parse(xsd_path)
        bls_settings_xsd_part = etree.Element(
            '{http://www.w3.org/2001/XMLSchema}import',
            namespace='bls:document:schema:xsd:Settings-1',
            schemaLocation=bls_settings_xsd_path
        )
        
        
        xsd.getroot().insert(0, bls_settings_xsd_part)
        
        xsd_validator = etree.XMLSchema(xsd)
        
        doc = etree.parse(BytesIO(xml_data.encode('utf8')))
        valid = xsd_validator.validate(doc)
        
        if not valid:
            error_msg = xsd_validator.error_log.filter_from_errors()[0]
        else:
            error_msg = False
        
        return error_msg
    
    @api.multi
    def set_line_numbers(self):
        for invoice in self:
            self._cr.execute("""
                SELECT
                    trod.document_lines_order
                FROM
                    transportation_order_document AS trod
                JOIN
                    transportation_order AS tro ON (
                        trod.transportation_order_id = tro.id
                    )
                JOIN
                    transportation_order_line AS trol ON (
                        trol.transportation_order_id = tro.id
                    )  
                JOIN
                    account_invoice_line AS ail ON (
                        ail.transportation_order_line_id = trol.id
                    )  
                WHERE
                    ail.invoice_id = %s
                ORDER BY
                    tro.id_external DESC, tro.name DESC
                LIMIT 1
            """ , (invoice.id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                line_order_by = sql_res[0] or 'CONTAINER'
            else:
                line_order_by = False
                  
            order_by_part = "ORDER BY tro.id_external, tro.name"
            if line_order_by:
                if line_order_by == 'ORIGINATOR_ORDER_LINE_ID':
                    order_by_part += ", trol.id_orginator_line"
                elif line_order_by == 'BUYER_ORDER_LINE_ID':
                    order_by_part += ", trol.id_buyer_line"
                elif line_order_by == 'PRODUCT_ID':
                    order_by_part += ", pp.default_code"
                elif line_order_by == 'ORIGINATOR_PRODUCT_ID':
                    order_by_part += ", trol.seller_product_code"
                elif line_order_by == 'BUYER_PRODUCT_ID':
                    order_by_part += ", trol.buyer_product_code"    
                elif line_order_by == 'PRODUCT_BARCODE':
                    order_by_part += ", pb.barcode"
                else:
                    order_by_part += ", trol.id_container_line"
                    
            
            
            self._cr.execute("""
                SELECT
                    ail.id
                FROM
                    account_invoice_line AS ail
                JOIN
                    transportation_order_line AS trol ON (
                        ail.transportation_order_line_id = trol.id
                    )
                JOIN
                    transportation_order AS tro ON (
                        trol.transportation_order_id = tro.id
                    )
                JOIN
                    product_product AS pp ON (
                        trol.product_id = pp.id
                    )
                JOIN
                    product_barcode AS pb ON (
                        pb.product_id = pp.id
                    )
                WHERE
                    invoice_id = %s
            """+order_by_part, (invoice.id,))
            invoice_line_ids = [i[0] for i in self._cr.fetchall() if i]
            invoice_line_ids = list(set(invoice_line_ids))
            i = 0
            for invoice_line_id in invoice_line_ids:
                i += 1
            
                self._cr.execute("""
                    UPDATE
                        account_invoice_line
                    SET
                        line_number = %s
                    WHERE
                        id = %s
                """, (i, invoice_line_id,))
        return True
    
    @api.multi
    def recompute_document_totals(self):
        inv_line_env = self.env['account.invoice.line']
        
        for invoice in self:
            self._cr.execute('''
                SELECT
                    annul_document, type
                FROM
                    account_invoice
                WHERE
                    id = %s
                LIMIT 1
            ''', (invoice.id,))
            annul_document, inv_type = self._cr.fetchone()
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    account_invoice_line
                WHERE
                    invoice_id = %s
            ''', (invoice.id,))
            inv_line_ids = [i[0] for i in self._cr.fetchall()]
            inv_lines = inv_line_env.browse(inv_line_ids)
            lines_totals = inv_lines.recompute_prices()
            
            amount_untaxed = abs(lines_totals[0])
            
            self._cr.execute('''
                SELECT
                    SUM(amount)
                FROM
                    account_invoice_tax
                WHERE
                    invoice_id = %s
            ''', (invoice.id,))
            amount_tax, = self._cr.fetchone()
            
            amount_tax = abs(amount_tax or 0.0)
            
            amount_total = amount_untaxed + amount_tax
            
            sign = (inv_type in ['in_refund', 'out_refund'] or annul_document) and -1 or 1
                
            amount_total_company_signed = amount_total * sign
            amount_total_signed = amount_total * sign
            amount_untaxed_signed = amount_untaxed * sign
                
            self._cr.execute('''
                UPDATE
                    account_invoice
                SET
                    amount_untaxed = %s,
                    amount_tax = %s,
                    amount_total = %s,
                    amount_total_company_signed = %s,
                    amount_total_signed = %s,
                    amount_untaxed_signed = %s
                WHERE
                    id = %s
            ''', (
                    amount_untaxed, amount_tax, amount_total,
                    amount_total_company_signed, amount_total_signed,
                    amount_untaxed_signed, invoice.id,
                )
            )    
        
        return True
    
    
#     @api.multi
#     def get_product_move_order_vals(self):
#         self.ensure_one()
#         
#         return {}

    @api.model
    def create_pickings_if_missing(self):
        
        datetime_now = datetime.datetime.now()
        datetime_30min_ago = datetime_now - datetime.timedelta(minutes=30)
        
        datetime_30min_ago_str = datetime_30min_ago.strftime('%Y-%m-%d %H:%M:%S')
        
        self._cr.execute('''
            SELECT
                id
            FROM
                account_invoice
            WHERE
                generated_in_atlas = true
            AND
                out_picking_created = false
            AND
                create_date < %s
        ''', (datetime_30min_ago_str,))
        
        invoice_ids = [i[0] for i in self._cr.fetchall()]
        if invoice_ids:
            invoices = self.browse(invoice_ids)
            invoices.create_stock_pickings()
        
        return True
    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    _order = 'line_number'

    @api.model
    def _get_invoice_categories(self):
        inv_env = self.env['account.invoice']
        return inv_env._get_document_operation_types()

    transportation_order_line_id = fields.Many2one(
        'transportation.order.line', "Transportation Order Line",
        readonly=True, index=True
    )
    primary_invoice_line_id = fields.Many2one(
        'account.invoice.line', "Primary Invoice Line", 
        readonly=True, index=True
    )
    line_number = fields.Integer("Line No.", readonly=True)
    exp_date = fields.Date("Expiration Date")
    container_id = fields.Many2one('account.invoice.container', "Container", index=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot', index=True) #perkloju Vytauto modulio apibrezima, kad prideti indexa
    price_after_disc = fields.Float('Unit price after Discount')
    category = fields.Selection(_get_invoice_categories, "Category")

    @api.multi
    def get_transportation_order_data(self):
        # Metodas gauti susijusį transportavimo užsakymą(gautą iš BLS)

        order_sql = '''
            SELECT
                tro.id, tro.name, trol.id_line
            FROM
                transportation_order tro
                JOIN transportation_order_line trol on (trol.transportation_order_id = tro.id)
                JOIN account_invoice_line ail on (ail.transportation_order_line_id = trol.id)
            WHERE
                ail.id = %s
            LIMIT 1
        '''
        order_where = (self.id,)
        self.env.cr.execute(order_sql, order_where)
        return self.env.cr.dictfetchone()

    
    @api.multi
    def write(self, vals):
        inv_line_env = self.env['account.invoice.line']
        context = self._context or {}
        if context.get('primary_lines_vals', False):
            new_doc_lines = inv_line_env.search([('primary_invoice_line_id','in',self.ids)])
            res = super(AccountInvoiceLine, new_doc_lines.with_context(primary_lines_vals=False)).write(vals)

        else:
            res = super(AccountInvoiceLine, self.with_context(primary_lines_vals=False)).write(vals)
        return res

    # ------------------------------------------ Vytautas {--------------------------------------

    @api.multi
    def get_fake_invoice_line_vals_for_ubl(self, line_counter=1):
        fake_lines_vals = self.get_invoice_line_vals_for_ubl(line_counter)
        for line_key in [
            'price', 'invoiced_quantity', 'line_extension_amount',
            'invoiced_quantity_unit_code', 'tax_total'
        ]:
            if line_key in fake_lines_vals:
                del fake_lines_vals[line_key]
        return fake_lines_vals

    @api.multi
    def get_invoice_line_vals_for_ubl(self, line_counter=1):
        inv_line_id = self.id
        self._cr.execute('''
            SELECT
                quantity, uom_id, product_id,
                transportation_order_line_id,
                price_subtotal, price_total,
                container_id, exp_date, lot_id
            FROM
                account_invoice_line
            WHERE id = %s
            LIMIT 1
        ''', (inv_line_id,))
        qty, uom_id, prod_id, \
        transportation_order_line_id, \
        line_amount_untaxed, line_amount_total, \
        container_id, exp_date, lot_id = self._cr.fetchone()

        line_amount_tax = line_amount_total - line_amount_untaxed

        if uom_id:
            self._cr.execute('''
                SELECT
                    name
                FROM
                    product_uom
                WHERE id = %s
                LIMIT 1
            ''', (uom_id,))
            uom, = self._cr.fetchone()
        else:
            uom = ""

        self._cr.execute('''
            SELECT
                pt.name, pp.default_code
            FROM
                product_product AS pp
            JOIN product_template AS pt ON (
                pp.product_tmpl_id = pt.id
            )
            WHERE pp.id = %s
            LIMIT 1
        ''', (prod_id,))
        prod_name, default_code = self._cr.fetchone()

        self._cr.execute('''
            SELECT
                barcode
            FROM
                product_barcode
            WHERE product_id = %s
            ORDER BY create_date DESC
            LIMIT 1
        ''', (prod_id,))
        sql_res = self._cr.fetchone()
        if sql_res:
            barcode, = sql_res
        else:
            barcode = False


        line_vals = {
            "id": str(line_counter),
            "invoiced_quantity": qty,
            "line_extension_amount": "%.2f" % (line_amount_untaxed),
            #                 "_ext_attributes": {
            #                     "invoiced_quantity": {
            #                       "unit_code": uom,
            #                     },
            #                     "line_extension_amount": {
            #                       "currency_id": currency,
            #                     },
            #                 },

            "invoiced_quantity_unit_code": uom,

            "tax_total": {
                "tax_amount": "%.2f" % (line_amount_tax),
                #                     "_ext_attributes": {
                #                         "tax_amount": {
                #                           "currency_id": currency,
                #                         }
                #                     },
                "tax_subtotal": [{
                    "taxable_amount": "%.2f" % (line_amount_untaxed),
                    "tax_amount": "%.2f" % (line_amount_tax),
                    #                         "_ext_attributes": {
                    #                             "taxable_amount": {
                    #                               "currency_id": currency,
                    #                             },
                    #                             "tax_amount": {
                    #                               "currency_id": currency,
                    #                             },
                    #                         },
                    "tax_category": {
                        "percent": "%.0f" % (
                        line_amount_tax and round((line_amount_tax / line_amount_untaxed) * 100) or 0.0),
                        "tax_scheme": {
                            "name": "VAT",
                            "tax_type": "VAT"
                        }
                    }
                }],
            },
            "price": {
                "price_amount": "%.2f" % (line_amount_untaxed),
                #                     "_ext_attributes": {
                #                         "price_amount": {
                #                           "currency_id": currency,
                #                         },
                #                     },
            },
            "item": {
                "description": prod_name,
                "additional_item_identification": [
                    {
                        "id": default_code,
                        #                             "_ext_attributes": {
                        #                                 "id": {
                        #                                   "scheme_id": "PRODUCT_CODE",
                        #                                   "scheme_name": "Product code",
                        #                                   "scheme_agency_id": "BLS"
                        #                                 }
                        #                             },
                        "scheme_id": "PRODUCT_CODE",
                        "scheme_name": "Product code",
                        "scheme_agency_id": "BLS"
                    }
                ]
            },
        }
        # ------------------------------------------ Vytautas {--------------------------------------

        # susirandu sale.order eilutes
        self._cr.execute('''
            SELECT
                order_line_id
            FROM
                invoice_line_so_line_rel
            WHERE
                invoice_line_id = %s
        ''', (inv_line_id,))
        sol_ids = [line_id[0] for line_id in self.env.cr.fetchall()]  # Tiksriausiai gali būti kelios eilutės

        if sol_ids:
            # iš konteinerio eilučių išsitraukiu OUT DESPATCH ID, ir eilutės DESP ID, kolkas limituoju 1
            self._cr.execute('''
                SELECT
                    id, out_despatch_id, despatch_advice_id
                FROM
                    account_invoice_container_line
                WHERE
                    sale_order_line_id in %s
            ''', (tuple(sol_ids),))
            for cont_line_id, out_desp_id, desp_id in self.env.cr.fetchall():  # Tiksriausiai gali būti kelios eilutės
                id_despatch_line = str(cont_line_id)
                if out_desp_id: # BLS nori gauti ir to despatch'o nuorodą kurį mes sukūrėme (Bėda ta kad eilutė ta pati su tuo pačiu ID)
                    self._cr.execute('''
                        SELECT
                            name, id_external
                        FROM
                            despatch_advice
                        WHERE 
                            id = %s
                        LIMIT 1
                    ''', (out_desp_id,))
                    out_despatch_name, out_id_despatch = self._cr.fetchone()

                    if 'despatch_line_reference' not in line_vals:
                        line_vals['despatch_line_reference'] = []
                    line_vals["despatch_line_reference"].append({
                        'line_id': id_despatch_line,
                        'document_reference': {
                            'id': out_despatch_name,
                            'uuid': out_id_despatch,
                        }
                    })

                if desp_id: # BLS nori gauti ir to despatch'o nuorodą kurį jie patys atsiuntė (Bėda ta kad eilutė ta pati su tuo pačiu ID)
                    self._cr.execute('''
                        SELECT
                            name, id_external
                        FROM
                            despatch_advice
                        WHERE 
                            id = %s
                        LIMIT 1
                    ''', (desp_id,))
                    despatch_name, id_despatch = self._cr.fetchone()
                    if 'despatch_line_reference' not in line_vals:
                        line_vals['despatch_line_reference'] = []
                    line_vals["despatch_line_reference"].append({
                        'line_id': id_despatch_line,
                        'document_reference': {
                            'id': despatch_name,
                            'uuid': id_despatch,
                        }
                    })

        # ------------------------------------------} Vytautas --------------------------------------

        # }

        if barcode:
            line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode

        if transportation_order_line_id:
            self._cr.execute('''
                SELECT
                    ordl.id_line, ord.name
                FROM
                    transportation_order_line AS ordl
                JOIN transportation_order AS ord ON (
                    ordl.transportation_order_id = ord.id
                )
                WHERE ordl.id = %s
                LIMIT 1
            ''', (transportation_order_line_id,))
            sql_res = self._cr.fetchone()
            if not sql_res:
                self._cr.execute('''
                    SELECT
                        ordl.id_line, ord.name
                    FROM
                        transportation_order_line AS ordl
                    JOIN transportation_order_line AS parent_l ON (
                        ordl.parent_line_id = parent_l.id
                    )
                    JOIN transportation_order AS ord ON (
                        parent_l.transportation_order_id = ord.id
                    )
                    WHERE ordl.id = %s
                    LIMIT 1
                ''', (transportation_order_line_id,))
                sql_res = self._cr.fetchone()
            if sql_res:
                id_ord_line, id_ord = sql_res

                if id_ord_line:
                    line_vals['order_line_reference'] = {
                        'line_id': id_ord_line
                    }
                    if id_ord:
                        line_vals['order_line_reference']['order_reference'] = {"id": id_ord}

        # self._cr.execute('''
        #     SELECT
        #         container_line_id
        #     FROM
        #         invoice_line_container_line_rel
        #     WHERE
        #         invoice_line_id = %s
        #     ORDER BY
        #         container_line_id
        #     LIMIT 1
        # ''', (inv_line_id,))
        # sql_res = self._cr.fetchone()

        # if sql_res and sql_res[0]:
        #     container_line_id = sql_res[0]
        #
        #     self._cr.execute('''
        #         SELECT
        #             id_external, name
        #         FROM
        #             despatch_advice
        #         WHERE
        #             id = (
        #                 SELECT out_despatch_id
        #                 FROM account_invoice_container_line
        #                 WHERE id = %s
        #                 LIMIT 1
        #             )
        #         LIMIT 1
        #     ''', (container_line_id,))
        #     sql_res = self._cr.fetchone()
        #     if sql_res:
        #         despatch_uuid, despatch_name = sql_res
        #
        #         line_vals['despatch_line_reference'] = {
        #             'line_id': str(container_line_id),
        #             'document_reference': {
        #                 'id': despatch_name,
        #                 'uuid': despatch_uuid,
        #             }
        #         }

        lot_exp_date = False
        if lot_id:
            self._cr.execute('''
            SELECT
                name, expiry_date
            FROM
                stock_production_lot
            WHERE
                id = %s
            LIMIT 1
        ''', (lot_id,))
            lot_name, lot_exp_date = self._cr.fetchone()
            line_vals["item"]['item_instance'] = {
                'lot_identification': {
                    'lot_number': lot_name,
                }
            }
            if lot_exp_date:
                line_vals["item"]['item_instance']['lot_identification']['expiry_date'] = lot_exp_date

        if container_id or (exp_date and not lot_exp_date):
            if not line_vals["item"].get('item_instance', False):
                line_vals["item"]['item_instance'] = {}

            if container_id:
                self._cr.execute('''
                    SELECT
                        container_no
                    FROM
                        account_invoice_container
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (container_id,))
                container_no, = self._cr.fetchone()
                if container_no:
                    line_vals["item"]['item_instance']['additional_item_property'] = [
                        {
                            'name': "ContainerNo",
                            'value': container_no,
                        }
                    ]
            if exp_date and not lot_exp_date:
                if not line_vals["item"]['item_instance'].get('additional_item_property', False):
                    line_vals["item"]['item_instance']['additional_item_property'] = []
                line_vals["item"]['item_instance']['additional_item_property'].append({
                    'name': "ExpirationDate",
                    'value': exp_date,
                })

    # ------------------------------------------} Vytautas --------------------------------------
        return line_vals


    @api.multi
    def recompute_prices(self):
        partner_env = self.env['res.partner']
        tax_env = self.env['account.tax']
        product_env = self.env['product.product']
        total_subtotal = 0.0
        total_discount = 0.0
        total_price = 0.0
        
        currency = self.env.user.company_id.currency_id
        for inv_line in self:
            inv_line_id = inv_line.id
            self._cr.execute("""
                SELECT
                    invoice_id, price_unit, discount,
                    quantity, product_id
                FROM
                    account_invoice_line
                WHERE id = %s
                LIMIT 1
            """ , (inv_line_id,))
            invoice_id, price_unit, discount, quantity, product_id = self._cr.fetchone()
            
            self._cr.execute("""
                SELECT
                    doc_discount, partner_id, annul_document, type
                FROM
                    account_invoice
                WHERE id = %s
                LIMIT 1
            """ , (invoice_id,))
            doc_discount, partner_id, annul_document, inv_type = self._cr.fetchone()
            
            self._cr.execute("""
                SELECT
                    tax_id
                FROM
                    account_invoice_line_tax
                WHERE invoice_line_id = %s
            """ , (inv_line_id,))
            tax_ids = [i[0] for i in self._cr.fetchall() if i]
            
            tax_vals = False
            price = price_unit * (1 - ((discount + (doc_discount or 0.0)) or 0.0) / 100.0)
            if tax_ids:
                if partner_id:
                    partner = partner_env.browse(partner_id)
                else:
                    partner = None
                if product_id:
                    product = product_env.browse(product_id)
                else:
                    product = None
                taxes = tax_env.browse(tax_ids)
                tax_vals = taxes.compute_all(price, currency, quantity, product=product, partner=partner)
            price_subtotal = tax_vals['total_excluded'] if tax_vals else quantity * price
            price_total = tax_vals['total_included'] if tax_vals else price_subtotal
            
            sign = (inv_type in ['in_refund', 'out_refund'] or annul_document) and -1 or 1
            
#             price_subtotal = price_subtotal
            price_subtotal_signed = price_subtotal * sign
            discount_amount = round(price_subtotal * quantity, 2)\
                * ((discount + (doc_discount or 0.0)) / 100.0)

            
            self._cr.execute("""
                UPDATE
                    account_invoice_line
                SET
                    price_subtotal = %s,
                    price_subtotal_signed = %s,
                    discount_amount = %s,
                    price_total = %s
                WHERE id = %s
            """ , (price_subtotal, price_subtotal_signed, discount_amount, price_total, inv_line_id,)) 
            
            total_subtotal += price_subtotal
            total_discount += discount_amount
            total_price += price_total

        res = (total_subtotal, total_discount, total_price)

        return res

class AccountInvoiceEditConfig(models.Model):
    _name = 'account.invoice.edit.config'
    
    type = fields.Selection([
        ("month_day", "Day of the month"),
        ("days_period", "Days after document is invoiced.")
    ], "Type", help="Edit period type.", default="days_period", required=True)
    days = fields.Integer("Day(s)", default=60)
    generated_number_config = fields.Selection([
        ("next", "Generate next number"),
        ("same", "Leave the same number")
    ], "ATLAS Generated Number Config", default="next", required=True)
    
    @api.multi
    def name_get(self):
        res = []
        for doc_edit_conf in self:
            self._cr.execute("""
                SELECT
                    type, days, generated_number_config
                FROM
                    account_invoice_edit_config
                WHERE id = %s
                LIMIT 1
            """ , (doc_edit_conf.id,))
            type, days, generated_number_config = self._cr.fetchone()
            
            name = generated_number_config == 'next' and _("Generate next number")\
                or _("Leave the same number")
            
            if days > 0:
                if type == 'month_day':
                    day_str = days == 1 and _("1st day of the month")\
                        or days == 2 and _("2nd day of the month")\
                        or days == 3 and _("3rd day of the month")\
                        or _("%sth day of the month") % (days)
                
                    edit_period_msg = _("Can be edited until %s") % (day_str)
                else:
                    if str(days)[-1] == '1':
                        edit_period_msg = _("Can be edited in %s day") % (days)
                    else:
                        edit_period_msg = _("Can be edited in %s days") % (days)
            else:
                edit_period_msg = _("Can be edited anytime")
            
            name += " | %s" % (edit_period_msg)
            res.append((doc_edit_conf.id, name))
        return res
    
class AccountInvoiceContainer(models.Model):
    _inherit = 'account.invoice.container'
 
    id_external = fields.Char('External ID', size=32, readonly=True, index=True)