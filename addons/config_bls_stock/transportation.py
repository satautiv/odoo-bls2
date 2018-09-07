# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tools.translate import _
from odoo import api, models, fields
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
import re

# import time

class DocumentForm(models.Model):
    _name = 'document.form'
    _description = 'Document form'
    
    name = fields.Char("Name", size=64)
    code = fields.Char("Code", size=32)

class TransportationOrderDocument(models.Model):
    _name = 'transportation.order.document'
    _description = 'Transportation Order Document'
    
    @api.model
    def get_sending_type_selection(self):
        inv_env = self.env['account.invoice']
        return inv_env.get_sending_type_selection()
        
    @api.model
    def get_document_type_selection(self):
        return [
            ('waybill', _("Way-Bill")),
            ('invoice', _("Invoice")),
        ]
        
    @api.model
    def get_tare_in_total_selection(self):
        return [
            ('include', _("Include")),
            ('no_include', _("Do not include"))
        ]
        
    @api.model
    def get_document_lines_order_selection(self):
        return [
            ('ORIGINATOR_ORDER_LINE_ID', _("Owner Order Line ID")),
            ('BUYER_ORDER_LINE_ID', _("Buyer Order Line ID")),
            ('CONTAINER', _("Container Line ID")),
            ('PRODUCT_ID', _("Product Code")),
            ('ORIGINATOR_PRODUCT_ID', _("Owner Product Code")), #Trubut Seller Product Code naudosis
            ('BUYER_PRODUCT_ID', _("Buyer Product Code")),
            ('PRODUCT_BARCODE', _("Product Barcode")),
        ]
    
    document_no = fields.Char("Document No.", readonly=True, index=True)
    sending_type = fields.Selection(get_sending_type_selection, "Sending Type")
    document_type = fields.Selection(get_document_type_selection, "Document Type")
    document_form_id = fields.Many2one('document.form', "Document Form")
#     note = fields.Text("Note")
    print_copies = fields.Integer("Print Copies", default=1)
    delivery_conditions = fields.Char("Delivery Conditions")
    document_counter = fields.Char("Documemt Counter", readonly=True)
#     logo_url = fields.Char("Logo URL", readonly=True)
#     document_date = fields.Date("Document Date")
#     document_create_datetime = fields.Datetime("Document Create Date/Time", readonly=True)
#     document_create_user_id = fields.Many2one('res.user', "Document Creator")
#     issued_by_user_id = fields.Many2one('res.user', "Issued By")
#     dublicate_ids = fields.Many2many(
#         'report.print.log', 'sod_print_log_rel', 'sod_id', 'print_log_id',
#         "Reprints"
#     )
    group_by_transport_unit = fields.Boolean("Group by Transport Unit", default=True)
    group_by_prod_params = fields.Boolean("Group by Product Parameters", default=True)

    transportation_order_id = fields.Many2one(
        'transportation.order', "Transportation Order", index=True,
        ondelete='cascade'
    )
    
    document_lines_order = fields.Selection(
        get_document_lines_order_selection, "Document Lines Selection", readonly=True
    )

    # Invoice fields
#     tare_in_total = fields.Selection(get_tare_in_total_selection, 'Tare in Total')
#     discount = fields.Float("Discount")
#     amount_wo_vat = fields.Float("Amount wo VAT")
#     total_amount = fields.Float("Total Amount", digits=dp.get_precision('Total Line Amount'))
#     deposit_amount = fields.Float("Deposit Amount", digits=dp.get_precision('Deposit Amount'))
#     tare_amount = fields.Float("Tare Amount", digits=dp.get_precision('Tare Amount'))
    #VAT???????

class TransportationOrder(models.Model):
    _inherit = 'transportation.order'
    
    @api.model
    def get_declare_to_vmi_selection(self):
        return [
            (0, _("Do not declare")),
            (1, _("BLS send declaracion")),
            (2, _("Electronic form declaration is required")),
            (3, _("VMI formated packing list is send to client."))
        ]
        
    @api.model
    def get_wms_process_type_selection(self):
        return [
            ('r', _("Retail")),
            ('w', _("Wholesale")),
            ('e', _("Export"))
        ]
        
    @api.model
    def get_delivery_terms_selection(self):
        return [
#             ('warehouse',_("Client receive from picking warehouse")),
#             ('cross_dock', _("Client receive from cross-dock")),
#             ('truck_delivery', _('Delivery for client')),
            ('parcel', _("Delivery by parcel company")),
            ('bls', _("Delivery by BLS")), #Kolkas neaisku kas cia, bet taip jie siuncia
            ('agent', _("Agent takes it")),
            ('client', _("Client takes it itself")),
        ]
        
    @api.model
    def get_order_type_selection(self):
        return [
            ('order', _("Order")),
            ('lead', _("Lead for driver")),
        ]
        
    @api.model
    def get_urgent_order_selection(self):
        return [
            ('regular', _("Regular")),
        ]
        
    @api.model
    def get_payment_channel_selection(self):
        return [
            ('bank_transfer', _("Bank transfer")),
            ('cash_invoice', _("Cash")),
        ]
        
    @api.model
    def get_order_type_code_selection(self):
        return [
            ('SHIPMENT', _("SHIPMENT")),
            ('PURCHASE', _("PURCHASE")),
        ]
    
    lang = fields.Char("Language Code")
#     inner_name = fields.Char("Inner Name", readonly=True)
#     seller_order_number = fields.Char('Seller Order No.', readonly=True)
#     customer_order_number = fields.Char('Customer Order No.', readonly=True)
#     receive_datetime = fields.Datetime("Receive Date/Time", readonly=True)
#     document_source = fields.Char("Document Source", readonly=True)
#     data_packet_number = fields.Char("Document Packet No.", readonly=True)
#     id_data_sender = fields.Char("Data Sender ID", readonly=True)
#     four_docs_system = fields.Boolean("4 Doc. System", readonly=True, default=False)
    declare_to_vmi = fields.Selection(get_declare_to_vmi_selection, "Declaration to VMI")
    document_ids = fields.One2many('transportation.order.document', 'transportation_order_id', "Documents")
    
#     infoline_text = fields.Text("Infoline Text")
#     infoline_phone = fields.Char("Infoline Phone")
#     infoline_email = fields.Char("Infoline Email")
#     comment = fields.Text("Comment")
#     agent = fields.Char("Agent")
    
#     cash_amount = fields.Float("Cash Amount")
#     order_cash = fields.Boolean(
#         "Order Cash", default=False,
#         help="If order cahs is true, then cash amount will be added to order sum"
#     )
    
    seperate_picking = fields.Boolean(
        "Seperate", default=False,
        help="Is it allowed to put different orders' product to the same container in warehouse"
    )
    urgent_order = fields.Selection(get_urgent_order_selection, "Urgent Order")
    clear_after_close = fields.Boolean(
        "Clear After Close", default=False,
        help="Clear unpicked lines after order confirm"
    )
    picking_from_stock_leftovers = fields.Boolean(
        "Allow Picking from Stock Leftovers", default=False,
    )
    picking_from_inbound = fields.Boolean(
        "Allow Picking from Inbound", default=False,
    )
    pincking_from_inbound_id_receive_document = fields.Char(
        "Allow Picking from Inbound receive Document ID"
    )
    wms_process_type = fields.Selection(get_wms_process_type_selection, "WMS Process Type")
    
#     delivery_date = fields.Date("Delivery Date")
#     esimated_delivery_date = fields.Date("Estimated Delivery Date")
#     delivery_start_time = fields.Float("Delivery Start Time")
#     delivery_end_time = fields.Float("Delivery End Time")
    delivery_terms = fields.Selection(get_delivery_terms_selection, "Delivery Terms")
    several_deliveries_split = fields.Boolean("Allow Order to Deliver in Several Parts")
    parcel_company = fields.Char("Parcel Company")
#     parcel_sender = fields.Char("Parcel Sender")
#     route_datetime = fields.Datetime("Route Date/Time")
    valid_client_start_time = fields.Char("Min. Delivery Hour According Client")
    valid_client_stop_time = fields.Char("Max. Delivery Hour According Client")
    route_id = fields.Many2one('stock.route', "Route")
#     route_number = fields.Char("Route Number", readonly=True)
#     route_name = fields.Char("Route Name", readonly=True)
#     route_priority = fields.Integer("Route Priority")
    carrier_id = fields.Many2one('res.partner', "Carrier")
    order_type = fields.Selection(get_order_type_selection, "order Type")
    seller_id = fields.Many2one('res.partner', "Seller")
#     depot_receiver_warehouse_id = fields.Many2one(
#         'stock.warehouse', "Depot Receiver", help="It is used for ASN destination warehouse"
#     )
#     receiver_id = fields.Many2one('res.partner', "Receiver (Client)")
#     payer_id = fields.Many2one('res.partner', "Payer")
    
#     container_ids = fields.Many2many(
#         'account.invoice.container', 'transportation_order_container_rel', 'transportation_order_id',
#         'container_id', "Containers"
#     )
#     certificate_ids = fields.One2many('product.certificate', 'transportation_order_id', "Certificates")
    
    issue_datetime = fields.Datetime("Issue Date/Time", readonly=True)
    id_external = fields.Char("External ID", readonly=True, index=True, size=64)
    currency_id = fields.Many2one('res.currency', 'Currency')
    delivery_address_id = fields.Many2one('res.partner', 'Delivery Address')
    despatch_address_id = fields.Many2one('res.partner', "Despatch Address")
    buyer_id = fields.Many2one('res.partner', "Buyer/Receiver")
#     handling_code = fields.Char("Handling Code")
    payment_channel = fields.Selection(get_payment_channel_selection, "Payment Channel")
    owner_partner_id = fields.Many2one('res.partner', "Owner Partner")
    
    imported = fields.Boolean("Imported", help="Order was imported from API (not generated)", default=False)

    car_number = fields.Char("Car Number")
    product_count = fields.Integer("Product Count")
    posid_code = fields.Char("POSID")
    one_time_buyer_id = fields.Many2one('transportation.order.partner', "Buyer")
    note = fields.Text("Note")
    pref_code = fields.Char("Pref Code")
    
#     id_external_int = fields.Integer("External ID", readonly=True, index=True)
    
    name = fields.Char(
        'Order Reference', size=64,  required=True, copy=False, index=True
    )
    
    order_type_code = fields.Selection(
        get_order_type_code_selection, 'Order Type Code'
    )
    
    @api.model
    def get_create_vals(self, json_data):
        partner_env = self.env['res.partner']
        order_line_env = self.env['transportation.order.line']
        doc_form_env = self.env['document.form']
#         seq_env = self.env['ir.sequence']
        transport_type_env = self.env['transport.type']
        order_partner_env = self.env['transportation.order.partner']
        location_env = self.env['stock.location']
        
        html_cleaner = re.compile('<.*?>')
        
        name = json_data.get('ID', '')
        self._cr.execute('''
            SELECT
                id
            FROM
                transportation_order
            WHERE name = %s
            LIMIT 1
        ''', (name,))
        sql_res = self._cr.fetchone()
        if sql_res:
            return False
        
        if json_data.get('IssueDate', False) and json_data.get('IssueTime', False):
            issue_datetime = '%s %s' % (json_data['IssueDate'], json_data['IssueTime'])
        else:
            issue_datetime = False
            
        tax_currency_code = json_data.get('DocumentCurrencyCode', json_data.get('TaxCurrencyCode', False))
        if tax_currency_code:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    res_currency
                WHERE name = %s
                LIMIT 1
            ''', (tax_currency_code,))
            sql_res = self._cr.fetchone()
            currency_id = sql_res and sql_res[0] or False
        else:
            currency_id = False
        
        lines_vals = []
        for line_data in json_data['OrderLine']:
            line_vals = order_line_env.form_vals_from_json(line_data['LineItem'])
            lines_vals.append((0,0,line_vals))

        one_time_customer = False
            
        doc_vals = []
        processing_vals= {} 
        for ubl_extension_data in json_data['UBLExtensions']['UBLExtension']:
            ubl_content_data = ubl_extension_data['ExtensionContent']
            settings_data = ubl_content_data['Settings']
            
            reason_code = ubl_extension_data['ExtensionReasonCode']
            if reason_code == "ORDER_PROCESSING":
                put_away_strategy_data = settings_data.get('PutAwayStrategy', False)
                transportation_strategy_data = settings_data.get('TransportationStrategy', False)
                
                transportation_group_code = transportation_strategy_data.get('HandlingCode', False)
                if transportation_group_code:
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            transport_type
                        WHERE code = %s
                        LIMIT 1
                    ''', (transportation_group_code,))
                    sql_res = self._cr.fetchone()
                    if sql_res:
                        transportation_group_id = sql_res[0]
                    else:
                        transportation_group_id = transport_type_env.create({
                            'name': transportation_group_code,
                            'code': transportation_group_code,
                        }).id
                else:
                    transportation_group_id = False
                
                one_time_customer = settings_data.get('OneTimeCustomer', False)
                
                processing_vals = {
                    'picking_from_inbound': put_away_strategy_data.get('PickFromInbound', False),
                    'parcel_company': put_away_strategy_data.get('ParcelCompanyID', False),
                    'seperate_picking': put_away_strategy_data.get('SeparatePicking', False),
                    'wms_process_type': put_away_strategy_data.get('WmsProcessType', 'r').lower(),
                    'picking_from_stock_leftovers': put_away_strategy_data.get('PickFromStock', False),
                    'clear_after_close': put_away_strategy_data.get('ClearAfterClose', False),
                    'urgent_order': put_away_strategy_data.get('UrgentOrder', 'regular').lower(),
                    'declare_to_vmi': settings_data.get('Waybill2VMI', False),
                    'delivery_terms': transportation_strategy_data.get('DeliveryType', 'BLS').lower(),
                    'several_deliveries_split': transportation_strategy_data.get('SplitOrderToFewDeliveries', False),
#                     'handling_code': transportation_strategy_data.get('HandlingCode', False),
                    'transport_type_id': transportation_group_id,
                    'lang': settings_data.get('LanguageCode', False),
                }
            elif reason_code in ('INVOICE', 'BILL'):
                document_type = reason_code == 'INVOICE' and 'invoice' or 'waybill'
                sending_type = settings_data.get('EDIExchangeType', False)
                if sending_type:
                    sending_type = sending_type.lower()
                    if sending_type == 'edi':
                        sending_type = 'electronical'
                delivery_conditions = settings_data.get('Incoterm', False)
                print_copies = settings_data.get('PrintCopies', 1)
                
                document_form = settings_data.get('DocumentFormID', 'INVOICE2')
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        document_form
                    WHERE code = %s
                    LIMIT 1
                ''', (document_form,))
                sql_res = self._cr.fetchone()
                if sql_res:
                    document_form_id = sql_res[0]
                else:
                    document_form_id = doc_form_env.create({
                        'name': document_form,
                        'code': document_form,
                    }).id
                
                doc_counter = settings_data.get('DocumentFormID', False)
                
                if settings_data.get('DocumentNumber', False):
                    number = settings_data.get('DocumentNumber', False)
                else:
                    number = False
#                     self._cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             ir_sequence
#                         WHERE prefix = %s
#                         LIMIT 1
#                     ''', (doc_counter,))
#                     sql_res = self._cr.fetchone()
#                     
#                     if sql_res:
#                         seq = seq_env.browse(sql_res[0])
#                     else:
#                         seq = seq_env.create({
#                             'name': "%s Document counter" % (doc_counter),
#                             'prefix': doc_counter,
#                             'padding': 0,
#                         })
#                     number = seq.next_by_id()
                    
                group_by_transport_unit = settings_data.get('DetailsGroupByTransportUnit', False)
                group_by_prod_params = settings_data.get('DetailsGroupByProductParameters', False)   
                
                doc_vals.append((0,0,{
                    'document_no': number,
                    'sending_type': sending_type,
                    'document_type': document_type,
                    'document_form_id': document_form_id,
                    'print_copies': print_copies,
                    'delivery_conditions': delivery_conditions,
                    'document_counter': doc_counter,
                    'group_by_transport_unit': group_by_transport_unit,
                    'group_by_prod_params': group_by_prod_params,
                    'document_lines_order': settings_data.get('ProductsSortingMethod', 'CONTAINER')
                }))
                
        payment_channel = json_data.get('PaymentMeans', False)\
            and json_data['PaymentMeans'].get('PaymentChannelCode', False)\
            or 'cash_invoice'
        payment_channel = payment_channel.lower()
    
        if json_data.get('SellerSupplierParty', False) and json_data['SellerSupplierParty'].get('Party', False):
            seller_id = partner_env.create_or_update_partner(json_data['SellerSupplierParty']['Party'])
        else:
            seller_id = False
#         if json_data.get('BuyerCustomerParty', False) and json_data['BuyerCustomerParty'].get('Party', False):
#             buyer_id = partner_env.create_or_update_partner(json_data['BuyerCustomerParty']['Party'])
#         else:
#             buyer_id = False

        orginator_customer_data = json_data.get('OriginatorCustomerParty', False)
        owner_partner_id = False
        owner_code = False
        owner_id = False
        
        if orginator_customer_data and orginator_customer_data.get('Party', False):
            orginator_customer_party_data = orginator_customer_data['Party']
            owner_partner_id = partner_env.create_or_update_partner(orginator_customer_party_data)
            if orginator_customer_party_data.get('PartyIdentification', False):
                for party_ident_data in orginator_customer_party_data['PartyIdentification']:
                    id_attr = party_ident_data['_ext_attributes']['ID']
                    if id_attr['schemeID'] == 'SHORT_NAME':
                        owner_code = party_ident_data['ID']
                        break
                                 
        if owner_code:
            self._cr.execute('''
	            SELECT
                    id
                FROM
                    product_owner
                WHERE
                    owner_code = %s
                ORDER BY
                    id
                LIMIT 1
            ''', (owner_code,))
            sql_res = self._cr.fetchone()
            if sql_res:
                owner_id = sql_res[0]
        
        #TODO: isimti sita nesamone, nes dabar ideta tik testavimuisi       
#         if not owner_id:
# #             NERAAAAAA_OWNERIOOOO
#             owner_id = 287

#             else:
#                 raise UserError(
#                     _('There is no owner %s in ATLAS system') % (owner_code)
#                 )

#         if json_data.get('OriginatorCustomerParty', False) and json_data['OriginatorCustomerParty'].get('Party', False):
#             owner_partner_id = partner_env.create_or_update_partner(json_data['OriginatorCustomerParty']['Party'])
#         else:
#             owner_partner_id = False
        
        buyer_id = False
        one_time_buyer_id = False    
        if json_data.get('BuyerCustomerParty', False) and json_data['BuyerCustomerParty'].get('Party', False):
            buyer_party_data = json_data['BuyerCustomerParty']['Party']
            if one_time_customer:
                one_time_buyer_id = order_partner_env.create_from_data(buyer_party_data)
                buyer_id = self.env.ref('config_bls_stock.res_partner_template_partner', False)[0].id
            else:
                buyer_id = partner_env.create_or_update_partner(buyer_party_data)
            
        delivery_data = json_data.get('Delivery', False)
        
        delivery_location_data = delivery_data.get('DeliveryLocation', False)
        despatch_location_data = delivery_data.get('Despatch', {}).get('DespatchLocation', False)    
        
        location_id = False
        pref_code = ''
        
        if despatch_location_data:
            location_code = despatch_location_data.get('SubsidiaryLocation', {}).get('Name', False)
            pref_code = despatch_location_data.get('Name', False)
            
            if location_code:
                location, warehouse = location_env.get_location_warehouse_id_from_code(
                    location_code, return_location_id=True, create_if_not_exists=True
                )
                location_id = location and location.id or False

        id_external = json_data.get('UUID', name)
#         try:
#             id_external_int = int(id_external)
#         except:
#             id_external_int = False
        
        res = {
            'id_external': id_external,
#             'id_external_int': id_external_int,
            'name': name,
            'issue_datetime': issue_datetime,
            'seller_id': seller_id,
            'currency_id': currency_id,
            'delivery_address_id': delivery_location_data and partner_env.create_or_update_address(delivery_location_data) or False,
            'despatch_address_id': despatch_location_data and partner_env.create_or_update_address(despatch_location_data) or False,
#             'buyer_id': partner_env.create_or_update_partner(json_data['BuyerCustomerParty']['Party']),
            'buyer_id': buyer_id,
            'line_ids': lines_vals,
            'document_ids': doc_vals,
            'owner_partner_id': owner_partner_id,
            'state': 'being_collected',
            'imported': True,
            'product_count': len(lines_vals),
            'one_time_buyer_id': one_time_buyer_id,
            'owner_id': owner_id,
            'note': re.sub(html_cleaner, '', json_data.get('Note', '')),
            'location_id': location_id,
            'pref_code': pref_code,
            'order_type_code': json_data.get('OrderTypeCode', ''),
        }
        
        res.update(processing_vals)
        
        return res
    
    @api.multi
    def create_despatch_links(self):
        container_line_env = self.env['account.invoice.container.line']
        despatch_env = self.env['despatch.advice']
        
        container_line_ids = []
        used_despatch_ids = []
        
        for order in self:
            self._cr.execute('''
                SELECT
                    id_external, name
                FROM
                    transportation_order
                WHERE id = %s
                LIMIT 1
            ''', (order.id,))
            id_external, order_name = self._cr.fetchone()
            if id_external or order_name:
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        account_invoice_container_line
                    WHERE
                        id_order = %s
                    OR
                        order_name = %s
                ''', (id_external, order_name))
            else:
                continue
            
#             self._cr.execute('''
#                 SELECT
#                     id_external, id_external_int
#                 FROM
#                     transportation_order
#                 WHERE id = %s
#                 LIMIT 1
#             ''', (order.id,))
#             id_external, id_external_int = self._cr.fetchone()
#             if id_external_int:
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         account_invoice_container_line
#                     WHERE id_order_int = %s
#                 ''', (id_external_int,))
#             elif id_external_int:
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         account_invoice_container_line
#                     WHERE id_order = %s
#                 ''', (id_external,))
#             else:
#                 continue
 
            sql_res = self._cr.fetchall()
            container_line_ids += sql_res and [i[0] for i in sql_res] or []
        if container_line_ids:
            container_lines = container_line_env.browse(container_line_ids)
            container_lines.link_to_order_and_order_line()
            for container_line in container_lines:
                self._cr.execute('''
                    SELECT
                        despatch_advice_id
                    FROM
                        account_invoice_container_line
                    WHERE id = %s
                    LIMIT 1
                ''', (container_line.id,))
                despatch_id, = self._cr.fetchone()
                despatch = despatch_env.browse(despatch_id)
#                 despatch = container_line.despatch_advice_id

                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        stock_picking
                    WHERE despatch_id = %s
                    LIMIT 1
                ''', (despatch_id,))
                sql_res = self._cr.fetchone()

                if despatch_id not in used_despatch_ids:
                    used_despatch_ids.append(despatch_id)
                    despatch.link_with_sale_order(skip_order_checking=True)
                    if not sql_res:
                        despatch.create_stock_pickings()
            
        return True
    
    @api.multi
    def update_vals_from_despatch(self):
        transportation_order_line_env = self.env['transportation.order.line']
        for order in self:
            total_picked_qty_percent = 0.0 # Devide from lines count, shows order state. (1 - fully picked; <1 - being picked)
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    transportation_order_line
                WHERE transportation_order_id = %s
            ''', (order.id,))
            sql_res = self._cr.fetchall()
            if not sql_res:
                return False
            
            order_line_ids = [i[0] for i in sql_res]
            
            for order_line_id in order_line_ids:
                order_line = transportation_order_line_env.browse(order_line_id)
                picked_qty_percent = order_line.update_picked_qty()
                total_picked_qty_percent += picked_qty_percent
            state_counter = order_line_ids and round(total_picked_qty_percent/len(order_line_ids)) or 1.0

#             order_vals = {}
            if state_counter == 1.0:
                self._cr.execute('''
                    UPDATE
                        transportation_order
                    SET state = 'need_invoice'
                    WHERE id = %s
                ''', (order.id, ))
#                 order_vals['state'] = 'need_invoice'
                
#             self._cr.execute('''
#                 SELECT
#                     da.truck_reg_plate, da.carrier_id
#                 FROM
#                     despatch_advice as da
#                 JOIN
#                     account_invoice_container_line as aicl on (aicl.despatch_advice_id = da.id)
#                 WHERE aicl.order_id = %s
#             ''', (order.id,))
#             sql_res = self._cr.fetchall()
#             if sql_res:
#                 car_numbers = [i[0] for i in sql_res if i[0]]
#                 carrier_ids = [i[1] for i in sql_res if i[1]]
#                 carrier_ids = list(set(carrier_ids))
#                 
#                 order_vals['car_number'] = ', '.join(car_numbers)
#                 
#                 if carrier_ids:
#                    order_vals['carrier_id']  = carrier_ids[0]

#             self._cr.execute('''
#                 SELECT
#                     da.truck_reg_plate, da.carrier_id
#                 FROM
#                     despatch_advice as da
#                 JOIN
#                     account_invoice_container_line as aicl on (aicl.despatch_advice_id = da.id)
#                 WHERE aicl.order_id = %s
#             ''', (order.id,))
            
#             if order_vals:
#                 order.write(order_vals)    #KOLKAS tik state irasineju, tai geriau SQL naudoti
            
        return True
    
#     @api.multi
#     def set_warehouse_and_location(self):
#         for order in self:
#             order_line_ids = order.line_ids.ids
#             self._cr.execute('''
#                 SELECT
#                     location_id, warehouse_id
#                 FROM
#                     transportation_order_line_warehouse
#                 WHERE order_line_id in %s
#             ''', (tuple(order_line_ids),))
#             sql_res = self._cr.fetchall()
#             if len(sql_res) == 1:
#                 location_id, warehouse_id = sql_res[0]
#                 order.write({
#                     'location_id': location_id,
#                     'warehouse_id': warehouse_id,
#                 })
#         return True
    
    @api.multi
    def recalc_depended_values(self):
        self.ensure_one()
        vals = {}
        if self.delivery_address_id:
            vals['posid_code'] = self.delivery_address_id.possid_code or ''
            
        order_line_ids = self.line_ids.ids
        if order_line_ids:
            self._cr.execute('''
                SELECT
                    location_id, warehouse_id
                FROM
                    transportation_order_line_warehouse
                WHERE order_line_id in %s
                GROUP BY location_id, warehouse_id
            ''', (tuple(order_line_ids),))
            sql_res = self._cr.fetchall()
            if len(sql_res) == 1:
                location_id, warehouse_id = sql_res[0]
                vals['location_id'] = location_id
                vals['warehouse_id'] = warehouse_id
            
        if vals:
            self.write(vals)
        
        return True
    
    @api.model
    def create(self, vals):
        res = super(TransportationOrder, self).create(vals)
#         if not vals.get('id_external_int', False):
#             res.calc_int_identificators()
#         res.set_warehouse_and_location()
        res.recalc_depended_values()
        return res
    
    
#     @api.multi
#     def calc_int_identificators(self):
#         self.ensure_one()
#         
#         self._cr.execute('''
#             SELECT
#                 id_external
#             FROM
#                 transportation_order
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         id_external, = self._cr.fetchone()
#         
#         if id_external and id_external[0] != '0':
#             try:
#                 id_external_int = int(id_external)
#                 self._cr.execute('''
#                     UPDATE
#                         transportation_order
#                     SET
#                         id_external_int = %s
#                     WHERE id = %s
#                 ''', (id_external_int, self.id,))
#             except:
#                 pass
#         
#         return True
    
class TransportationOrderLineProductType(models.Model):
    _name = 'transportation.order.line.product_type'
    _description = "Product type in logistics companies"
    
    name = fields.Char('Name')
    code = fields.Char('Code', required=True) 
    
class TransportationOrderLine(models.Model):
    _inherit = 'transportation.order.line'
    
    @api.model
    def get_payment_term_method_selection(self):
        return [
            ('FromInvoiceDate', _("From invoice date")),
            ('FromDeliveryDate', _("From delivery date"))
        ]
        
    @api.model
    def get_put_away_strategy_selection(self):
        return [
            ('soft', "Soft"),
            ('hard', "Hard")
        ]
    
    id_line = fields.Char("Line ID", readonly=True, index=True)
    unit_price = fields.Float("Unit Price", digits=dp.get_precision('Product Price'))
#     product_code = fields.Char("Product Code")
    seller_product_code = fields.Char("Seller Product Code")
    buyer_product_code = fields.Char("Buyer Product Code")
    manufacturer_product_code = fields.Char("Seller Product Code")
    order_line_warehouse_ids = fields.One2many(
        'transportation.order.line.warehouse', 'order_line_id',
        string="Warehouses"
    )
    prod_type = fields.Many2one('transportation.order.line.product_type', "Product Type")
    payment_term_method = fields.Selection(
        get_payment_term_method_selection, "Payment Term Method"
    )
    payment_term = fields.Char("Payment Term")
    invoice_group_index = fields.Char("Invoice Group Index", index=True)
    waybill_group_index = fields.Char("Waybill Group Index", index=True)
    min_exp_date = fields.Date('Min. Expiration Date')
    max_exp_date = fields.Date('Max. Expiration Date')
    min_exp_days = fields.Integer("Min. Expiration Days")
    max_exp_days = fields.Integer("Max. Expiration Days")
    put_away_strategy = fields.Selection(
        get_put_away_strategy_selection, "Put Away Strategy"
    )
    min_delivery_qty = fields.Float(
        "Min. Delivery Quantity", digits=dp.get_precision('Product Unit of Measure')
    )
    payment_term_date = fields.Date('Payment Term Date')
    calculate = fields.Boolean("Calculate", default=True)
    include_to_totals = fields.Boolean("Include to Totals", default=True)
    discount = fields.Float("Discount", digits=(5,2))
#     discount_amount = fields.Float("Discount Amount", digits=dp.get_precision('Product Price'))
    tax_id = fields.Many2one('account.tax', "Tax")
    parent_line_id = fields.Many2one(
        'transportation.order.line', "Main Item Line",
        help="This can be filled only for lines with subitems, which has one main item line",
        ondelete='cascade', index=True
    )
    subitem_line_ids = fields.One2many(
        'transportation.order.line', 'parent_line_id', string="Subitem Lines"
    )
    container_line_ids = fields.One2many('account.invoice.container.line', 'order_line_id', "Container Lines")
    picked_qty = fields.Float("Picked Quantity", digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    fully_picked = fields.Boolean("Fully Picked", default=False)
    location_id = fields.Many2one('stock.location')
    pref_code = fields.Char("Pref Code")
    
#     id_line_int = fields.Integer("Line ID", readonly=True, index=True)
    
    id_orginator_line = fields.Char("Orginator Line ID", readonly=True, index=True)
    id_buyer_line = fields.Char("Buyer Line ID", readonly=True, index=True)
    id_container_line = fields.Char("Container Line ID", readonly=True, index=True)
    

    @api.model
    def form_vals_from_json(self, line_data):
        product_env = self.env['product.product']
        uom_env = self.env['product.uom']
        location_env = self.env['stock.location']
        barcode_env = self.env['product.barcode']
        tax_env = self.env['account.tax']
        
#         line_data = json_data['LineItem']
        
        uom = line_data.get('_ext_attributes', False)\
            and line_data['_ext_attributes'].get('Quantity', False)\
            and line_data['_ext_attributes']['Quantity']['unitCode'] or ''
        
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
            

        item_data = line_data['Item']
        
        
#         valid_date = item_data.get('ItemInstance', False)\
#             and item_data['ItemInstance']['BestBeforeDate'] or False
        warehouses = []
        prod_type = False
        inv_group_index = False
        waybill_group_index = False
        min_exp_date = False
        max_exp_date = False
        min_exp_days = False
        max_exp_days = False
        put_awaya_strategy = False
        min_delivery_qty = False
        payment_term_method = False
        payment_term = False
        payment_date = False
        id_orginator_line = False
        id_buyer_line = False
        id_container_line = False

        if item_data.get('ItemInstance', False):
            item_instance_data = item_data['ItemInstance']
            for item_property_data in item_instance_data.get('AdditionalItemProperty', []):
                if item_property_data['Name'] == 'PickingWarehouse':
                    code = item_property_data['Value']
                    sequence = item_property_data.get('ImportanceCode', 10)
#                     self._cr.execute('''
#                             SELECT
#                                 id
#                             FROM
#                                 stock_location
#                             WHERE name = %s
#                             LIMIT 1
#                         ''', (code,))
#                     sql_res = self._cr.fetchone()
#                     location_id = sql_res and sql_res[0] or False
#                     if location_id:
#                         loc = location_env.browse(location_id)
#                         warehouse = loc.get_location_warehouse_id()
#                         warehouse_id = warehouse and warehouse.id or False
#                     else:
#                         warehouse_id = False

                    location, warehouse = location_env.get_location_warehouse_id_from_code(
                        code, return_location_id=True, create_if_not_exists=True
                    )
                
                    warehouses.append((0,0,{
                        'code': code,
                        'sequence': sequence,
                        'location_id': location and location.id,
                        'warehouse_id': warehouse and warehouse.id,
                    }))
                elif item_property_data['Name'] == 'MinExpirationDate':
                    min_exp_date = item_property_data['Value']
                elif item_property_data['Name'] == 'MaxExpirationDate':
                    max_exp_date = item_property_data['Value']
                elif item_property_data['Name'] == 'MinExpirationInDays':
                    min_exp_days = item_property_data['Value']
                elif item_property_data['Name'] == 'MaxExpirationInDays':
                    max_exp_days = item_property_data['Value']
                elif item_property_data['Name'] == 'PutAwayStrategy':
                    put_awaya_strategy = item_property_data['Value'].lower()
                elif item_property_data['Name'] == 'MinDeliveryQuantity':
                    min_delivery_qty = float(item_property_data['Value'])
                elif item_property_data['Name'] == 'PaymentTermType':
                    payment_term_method = item_property_data['Value']
                elif item_property_data['Name'] == 'PaymentTerm':
                    payment_term = item_property_data['Value']
                elif item_property_data['Name'] == 'PaymentDate':
                    payment_date = item_property_data['Value']
                elif item_property_data['Name'] == 'InvoiceGroupCode':
                    inv_group_index = item_property_data['Value']
                elif item_property_data['Name'] == 'WaybillGroupCode':
                    waybill_group_index = item_property_data['Value']
                elif item_property_data['Name'] == 'OriginatorLineID':
                    id_orginator_line = item_property_data['Value']
                elif item_property_data['Name'] == 'BuyerLineID':
                    id_buyer_line = item_property_data['Value']
                elif item_property_data['Name'] == 'ContainerLineID':
                    id_container_line = item_property_data['Value']
        
        id_manifacturer = item_data.get('ManufacturersItemIdentification', False)\
            and item_data['ManufacturersItemIdentification']['ID'] or ''
#         name = item_data.get('Name', '')
        name = item_data.get('Description', '')

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
#             prod_vals['barcode_ids'] = barcode_id and [(4, barcode_id)]\
#                 or [(0,0,{'barcode': barcode})]
        
        deposit_calc = False
        include_in_total_sum = False
        if line_data.get('PriceCalculation', False):
            price_calc_data = line_data['PriceCalculation']
            deposit_calc = price_calc_data.get('DepositCalculateIndicator', False)
            include_in_total_sum = price_calc_data.get('IncludeInTotalSumIndicator', False)
            
        discount = 0.0
        if line_data.get('Price', {}).get('AllowanceCharge', False):
            allowance_data = line_data['Price']['AllowanceCharge']
            if allowance_data.get('AllowanceChargeReason', False) == 'Discount':
                discount = allowance_data.get('MultiplierFactorNumeric', 0.0)
                
        tax_id = False
        tax_percent = False
        
        tax_total_data = line_data.get('TaxTotal', {})
        tax_subtotal_data_list = tax_total_data.get('TaxSubtotal', False)
        tax_subtotal_data = tax_subtotal_data_list and tax_subtotal_data_list[0] or False
        
        
        if tax_subtotal_data and tax_subtotal_data.get('TaxCategory', False)\
         and tax_subtotal_data['TaxCategory'].get('Percent', False):
            tax_percent = float(tax_subtotal_data['TaxCategory']['Percent'])
        elif tax_subtotal_data and tax_subtotal_data.get('Percent', False):
            tax_percent = float(tax_subtotal_data['Percent'])
            
#         if line_data.get('TaxTotal', False) and line_data['TaxTotal'].get('TaxSubtotal', False)\
#          and line_data['TaxTotal']['TaxSubtotal'].get('TaxCategory', False)\
#          and line_data['TaxTotal']['TaxSubtotal']['TaxCategory'].get('Percent', False):
#             tax_percent = float(line_data['TaxTotal']['TaxSubtotal']['TaxCategory']['Percent'])
#         elif line_data.get('TaxTotal', False) and line_data['TaxTotal'].get('TaxSubtotal', False)\
#          and line_data['TaxTotal']['TaxSubtotal'].get('Percent', False):
#             tax_percent = float(line_data['TaxTotal']['TaxSubtotal']['Percent'])
        
        if tax_percent:    
            self._cr.execute('''
                SELECT
                    id
                FROM
                    account_tax
                WHERE amount = %s
                    AND type_tax_use = 'sale'
                LIMIT 1
            ''', (tax_percent,))
            sql_res = self._cr.fetchone()
            tax_id = sql_res and sql_res[0] or False
            if not tax_id:
                tax_vals = tax_env.default_get(tax_env._fields)
                tax_vals['name'] = '%s %%' % (tax_percent)
                tax_vals['type_tax_use'] = 'sale'
                tax_vals['amount'] = tax_percent
                tax_id = tax_env.create(tax_vals).id
                
        sublines_vals = []
        for subline_data in line_data.get('SubLineItem', []):
            subline_vals = self.form_vals_from_json(subline_data)
            sublines_vals.append((0,0,subline_vals))
            
        delivery_data = line_data.get('Delivery', False)
        
        location_id = False
        pref_code = ''
        
        if delivery_data:
            despatch_location_data = delivery_data.get('Despatch', {}).get('DespatchLocation', False)

            location_code = despatch_location_data.get('SubsidiaryLocation', {}).get('Name', False)
            pref_code = despatch_location_data.get('Name', False)
            if location_code:
                location, warehouse = location_env.get_location_warehouse_id_from_code(
                    location_code, return_location_id=True, create_if_not_exists=True
                )
                location_id = location and location.id or False
        
        id_line = line_data['ID']
#         try:
#             id_line_int = int(id_line)
#         except:
#             id_line_int = False
        
        res = {
            'quantity': line_data.get('Quantity', 0.0),
            'unit_price': line_data.get('Price', {}).get('PriceAmount', 0.0),
            'id_line': id_line,
#             'id_line_int': id_line_int,
            'uom_id': uom_id,
#             'exp_date': valid_date,
            'product_code': default_code,
            'seller_product_code': id_seller,
            'buyer_product_code': id_buyer,
            'manufacturer_product_code': id_manifacturer,
            'product_id': product_id,
            'order_line_warehouse_ids': warehouses,
            'prod_type': prod_type,
            'invoice_group_index': inv_group_index,
            'waybill_group_index': waybill_group_index,
            'min_exp_date': min_exp_date,
            'max_exp_date': max_exp_date,
            'min_exp_days': min_exp_days,
            'max_exp_days': max_exp_days,
            'put_away_strategy': put_awaya_strategy,
            'min_delivery_qty': min_delivery_qty,
            'payment_term_method': payment_term_method,
            'payment_term': payment_term,
            'payment_term_date': payment_date,
            'calculate': deposit_calc,
            'include_to_totals': include_in_total_sum,
            'discount': discount,
            'tax_id': tax_id,
            'subitem_line_ids': sublines_vals,
            'location_id': location_id,
            'pref_code': pref_code,
            'id_orginator_line': id_orginator_line,
            'id_buyer_line': id_buyer_line,
            'id_container_line': id_container_line,
        }
        
        return res
            
    @api.multi
    def update_picked_qty(self):
        self.ensure_one()
        self._cr.execute('''
            SELECT
                quantity
            FROM
                transportation_order_line
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        qty, = self._cr.fetchone()
        
        
#         qty = self.quantity
#         picked_qty = 0.0
#         for container_line in self.container_line_ids:
#             picked_qty += container_line.qty or 0.0

        self._cr.execute('''
            SELECT
                sum(qty)
            FROM
                account_invoice_container_line
            WHERE order_line_id = %s
        ''', (self.id,))
        picked_qty, = self._cr.fetchone()
        
        if picked_qty and picked_qty >= qty:
            res = 1
            fully_picked = True
        elif picked_qty and qty:
            res = picked_qty / qty
            fully_picked = False
        else:
            res = 0.0
            fully_picked = False
            
        self.write({
            'picked_qty': picked_qty,
            'fully_picked': fully_picked,
        })
           
        return res
    
#     @api.model
#     def create(self, vals):
#         res = super(TransportationOrderLine, self).create(vals)
#         if not vals.get('id_line_int', False):
#             res.calc_int_identificators()
#         return res
    
#     @api.multi
#     def calc_int_identificators(self):
#         self.ensure_one()
#         
#         self._cr.execute('''
#             SELECT
#                 id_line
#             FROM
#                 transportation_order_line
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         id_external, = self._cr.fetchone()
#         
#         if id_external and id_external[0] != '0':
#             try:
#                 id_external_int = int(id_external)
#                 self._cr.execute('''
#                     UPDATE
#                         transportation_order_line
#                     SET
#                         id_line_int = %s
#                     WHERE id = %s
#                 ''', (id_external_int, self.id,))
#             except:
#                 pass
#         
#         return True
    

class TransportationOrderLineWarehouse(models.Model):
    _name = 'transportation.order.line.warehouse'
    _description = "Order line warehouses with sequence"
    _rec_name = 'code'
    _order = 'sequence'
    
    code = fields.Char('Code')
    location_id = fields.Many2one('stock.location', "Location")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    sequence = fields.Integer('Sequence', default=10)
    order_line_id = fields.Many2one(
        'transportation.order.line', 'Order Line',
        ondelete='cascade', index=True
    )
    
    
class TransportationOrderPartner(models.Model):
    _name = 'transportation.order.partner'
    _description = 'Transportation order partner'
    
    name = fields.Char("Name")
    vat = fields.Char("VAT")
    address = fields.Char("Address")
    ref = fields.Char('Ref')
    bls_code = fields.Char("BLS Code")
    inidividual_actv_nr = fields.Char("Invidual Activity No.")
    farmer_code = fields.Char("Farmer Code")
    bsn_lic_nr = fields.Char("Business License No.")
    route = fields.Char("Route")
    bank_name = fields.Char("Bank Name")
    bank_account = fields.Char("Bank Account")
    alcohol_license_type = fields.Char("Alcohol License Type")
    alcohol_license_sale_type = fields.Char("Alcohol License Sale Type")
    alcohol_license_no = fields.Char("Alcohol License No.")
    alcohol_license_date = fields.Date("Alcohol License Date")
    alcohol_license_consume = fields.Char("Alcohol License Consume")
    tobac_license_type = fields.Char("Tobac License Type")
    tobac_license_sale_type = fields.Char("Tobac License Sale Type")
    tobac_license_no = fields.Char("Tobac License No.")
    tobac_license_date = fields.Date("Tobac License Date")
    client_code = fields.Char("Client Code")
    posid_name = fields.Char('POSID Name', size=128)
    posid_code = fields.Char('POSID Code', size=128)
    
    @api.model
    def create_from_data(self, json_data):
        vat = ''   
        tax_dict = json_data.get('PartyTaxScheme', False)
        if tax_dict:
            tax_attr_dict = tax_dict.get('_ext_attributes', {})
            if tax_attr_dict.get('CompanyID', False)\
                and tax_attr_dict['CompanyID']['schemeID'] == 'VAT_CODE'\
            :
                vat = tax_dict.get('CompanyID', "")
                
        bls_code = json_data.get('PartyIdentification', False)\
            and json_data['PartyIdentification'][0]['ID'] or ''
            
        ref = json_data.get('PartyLegalEntity', False)\
            and json_data['PartyLegalEntity'][0].get('CompanyID', "") or ""
        
        self._cr.execute('''
            SELECT
                id
            FROM
                transportation_order_partner
            WHERE bls_code = %s
                AND ref = %s
            LIMIT 1
        ''', (bls_code, ref,))
        sql_res = self._cr.fetchone()
        if sql_res:
            to_partner_id = sql_res[0]
        else:
        
            address_dict = json_data.get('PhysicalLocation', False)\
                and json_data['PhysicalLocation']['Address'] or False
            
            vals = {
                'bls_code': bls_code,
                'name': json_data.get('PartyName', False) and json_data['PartyName']['Name'] or '',
                'address': address_dict and address_dict['AddressLine']\
                    and address_dict['AddressLine'][0]\
                    and address_dict['AddressLine'][0]['Line'] or "",
                'vat': vat,
                'ref': ref
            }
            
            to_partner_id = self.create(vals).id
        
        return to_partner_id