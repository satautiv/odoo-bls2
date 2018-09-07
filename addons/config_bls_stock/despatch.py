# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields, _, SUPERUSER_ID, tools
from odoo.exceptions import UserError
import re
from .stock import get_local_time_timestamp
# import json
import time
import datetime
import uuid

import traceback

from .import_schemas.models.despatch_advice.schemas import DespatchAdviceSchema
da_schema = DespatchAdviceSchema()

class DateTimePeriod(models.Model):
    _name = 'date.time.period'
    _description = 'Period with start and end dates and times'
    
    start_date = fields.Date('Start Date')
    start_time = fields.Char("Start Time")
    end_date = fields.Date("End Date")
    end_time = fields.Char("End Time")
    despatch_advice_id = fields.Many2one('despatch.advice', "Despatch Advice")

class DespatchAdvice(models.Model):
    _name = 'despatch.advice'
    _description = 'Despatch advice'
    
    @api.model
    def get_shipment_type_selection(self):
        return [
            ('TransDepot', 'TransDepot'),
            ('InterBranch', 'InterBranch'), # Tiesiog pervadintas iš TransDepot
        ]
        
    @api.model
    def _get_despatch_type_selection(self):
        return [
#             ('in', _("In")),
#             ('out', _("Out")),
#             ('in_bls', _("In BLS")),
#             ('out_bls', _("Out BLS")),
            ('in_sale', _("In Sale")),
            ('out_sale', _("Out Sale")),
            ('out_atlas_wh', _("Out Atlas Wh")),
            ('out_atlas_dos', _("Out Atlas DOS")),
            ('bls_in_supply', _("In Supply")), 
            ('bls_in_atlas_dos', _("In Atlas DOS")), 
        ]
    
    name = fields.Char("Name", readonly=True, index=True)
    issue_datetime = fields.Datetime("Issue Date/Time", readonly=True)
    id_external = fields.Char("External ID", readonly=True, size=64)
    buyer_id = fields.Many2one('res.partner', "Buyer")
    seller_id = fields.Many2one('res.partner', "Seller")
    owner_partner_id = fields.Many2one('res.partner', "Owner Partner")
    receiver_id = fields.Many2one('res.partner', "Receiver")
    despatch_place_ids = fields.One2many(
        'despatch.advice.despatch_place', 'despatch_advice_id',
        string="Places"
    )
    container_line_ids = fields.One2many(
        'account.invoice.container.line', 'despatch_advice_id',
        string="Container Lines"
    )
#     promised_delivery_period_start_date = fields.Date("Promised Delivery Period Start Date")
#     promised_delivery_period_start_time = fields.Char("Promised Delivery Period Start Time")
#     promised_delivery_period_end_date = fields.Date("Promised Delivery Period End Date")
#     promised_delivery_period_end_time = fields.Char("Promised Delivery Period End Time")
    truck_reg_plate = fields.Char("Truck Registration Plate")
    trailer_reg_plate = fields.Char("Trailer Registration Plate")
    
    actual_delivery_date = fields.Date("Actual Delivery Date")
    delivery_address_id = fields.Many2one('res.partner', "Delivery Address")
    despatch_address_id = fields.Many2one('res.partner', "Despatch Address")

    carrier_id = fields.Many2one('res.partner', "Carrier")
    
    delivery_terms = fields.Char("Delivery Terms")
    
    promised_delivery_period_id = fields.Many2one('date.time.period', "Promised Delivery Period")
    estimated_delivery_period_id = fields.Many2one('date.time.period', "Estimated Delivery Period")
    
    validity_period_ids = fields.One2many('date.time.period', 'despatch_advice_id',
        string="Validity Periods"
    )
    
#     orders_are_missing = fields.Boolean("Orders Are Missing")
    
    picking_ids = fields.One2many('stock.picking', 'despatch_id', "Pickings")
    
    note = fields.Text("Note")
    
    delivery_coordinate_id = fields.Many2one('res.partner.coordinate', "Delivery Coordinate")
    
    id_source_doc = fields.Char("Source Document ID")
    shipment_type = fields.Selection(get_shipment_type_selection, "Shipment Type")
    id_bls_shipment = fields.Char("BLS Shipment ID", index=True)
    
    sale_order_id = fields.Many2one('sale.order', "Transportation Task", index=True)
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse")
    location_id = fields.Many2one('stock.location', "Location")
    one_time_buyer_id = fields.Many2one('transportation.order.partner', "Buyer")
    transport_type_id = fields.Many2one('transport.type', 'Transport Group')
    posid_code = fields.Char("POSID")
    owner_id = fields.Many2one('product.owner', "Owner")
    pref_code = fields.Char("Pref Code")
    
    despatch_type = fields.Selection(_get_despatch_type_selection, "Despatch Type")
    out_container_line_ids = fields.One2many(
        'account.invoice.container.line', 'out_despatch_id',
        string="Out Container Lines"
    )
    id_version = fields.Char('POD Version', size=128, readonly=True)
    route_id = fields.Many2one('stock.route', "Route", readonly=True)
    route_template_id = fields.Many2one('stock.route.template', "Route Template", readonly=True, index=True)
    customer_despatch_intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate' ,"Customer Despatch Intermediate", readonly=True
    )
    
    despatch_supplier_id = fields.Many2one('res.partner', "Despatch Supplier")
    
    dest_warehouse_id = fields.Many2one('stock.warehouse', "Destination Warehouse")
    dest_location_id = fields.Many2one('stock.location', "Destination Location")
    
    @api.model
    def get_create_vals(self, json_data, get_orders_from_api):
        partner_env = self.env['res.partner']
        location_env = self.env['stock.location']
        container_line_env = self.env['account.invoice.container.line']
        date_time_period_env = self.env['date.time.period']
        interm_env = self.env['stock.route.integration.intermediate']
        coordinate_env = self.env['res.partner.coordinate']
        order_partner_env = self.env['transportation.order.partner']
        container_env = self.env['account.invoice.container']
        
        html_cleaner = re.compile('<.*?>')
        
        intermediates = self.env['stock.route.integration.intermediate']
        orders = set([])
        container_lines_vals = []
        
        name = json_data.get('ID', '')
        self._cr.execute('''
            SELECT
                id
            FROM
                despatch_advice
            WHERE name = %s
            LIMIT 1
        ''', (name,))
        sql_res = self._cr.fetchone()
        
        if sql_res:
            return (False, intermediates)
        
        for line_data in json_data['DespatchLine']:
#             line_vals = container_line_env.form_vals_from_json(line_data)
            line_vals_list = container_line_env.form_vals_from_json(line_data)
            for line_vals in line_vals_list:
                container_lines_vals.append((0,0,line_vals))
                orders.add(line_vals['id_order'])
            
        if get_orders_from_api:
            for order in orders:
                order_intermediate = interm_env.get_transportation_order_from_api(order, commit_at_the_end=True)
                if order_intermediate:
                    intermediates += order_intermediate
                    
        if json_data.get('IssueDate', False) and json_data.get('IssueTime', False):
            issue_datetime = '%s %s' % (json_data['IssueDate'], json_data['IssueTime'])
        else:
            issue_datetime = False
        
        
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
                

#             else:
#                 raise UserError(
#                     _('There is no owner %s in ATLAS system') % (owner_code)
#                 )

#         if json_data.get('OriginatorCustomerParty', False) and json_data['OriginatorCustomerParty'].get('Party', False):
#             owner_partner_id = partner_env.create_or_update_partner(json_data['OriginatorCustomerParty']['Party'])
#         else:
#             owner_partner_id = False
            
        if json_data.get('DeliveryCustomerParty', False) and json_data['DeliveryCustomerParty'].get('Party', False):
            receiver_id = partner_env.create_or_update_partner(json_data['DeliveryCustomerParty']['Party'])
        else:
            receiver_id = False
            
        places_vals = []
        warehouse_id = False
        location_id = False
#         if json_data.get('DespatchSupplierParty', False) and json_data['DespatchSupplierParty'].get('Party', False)\
#          and json_data['DespatchSupplierParty']['Party'].get('PartyIdentification', False):
#             for desp_sup_party_id_data in json_data['DespatchSupplierParty']['Party']['PartyIdentification']:
#                 id_external = desp_sup_party_id_data['ID']
#                 id_attr_data = desp_sup_party_id_data['_ext_attributes']['ID']
#                 
#                 place_vals = {
#                     'name': id_external
#                 }
#                 
#                 if id_attr_data['schemeID'] == 'COMPANY_ID':
#                     self._cr.execute('''
#                         SELECT
#                             id
#                         FROM
#                             res_partner
#                         WHERE external_customer_id = %s
#                         LIMIT 1
#                     ''', (id_external,))
#                     sql_res = self._cr.fetchone()
#                     if sql_res and sql_res[0]:
#                         place_vals['partner_id'] = sql_res[0]
# #                 elif id_attr_data['schemeID'] == 'WAREHOUSE_ID':
# # #                     self._cr.execute('''
# # #                         SELECT
# # #                             id
# # #                         FROM
# # #                             stock_location
# # #                         WHERE name = %s
# # #                         LIMIT 1
# # #                     ''', (id_external,))
# # #                     sql_res = self._cr.fetchone()
# # #                     location_id = sql_res and sql_res[0] or False
# # #                     if location_id:
# # #                         loc = location_env.browse(location_id)
# # #                         warehouse = loc.get_location_warehouse_id()
# # #                         warehouse_id = warehouse and warehouse.id or False
# # #                     else:
# # #                         warehouse_id = False
# # #                     place_vals['location_id'] = location_id
# # #                     place_vals['warehouse_id'] = warehouse_id
# #                     location, warehouse = location_env.get_location_warehouse_id_from_code(
# #                         id_external, return_location_id=True, create_if_not_exists=True
# #                     )
# #                     warehouse_id = warehouse and warehouse.id or False
# #                     location_id = location and location.id or False
# #                     
# #                     place_vals['location_id'] = location_id
# #                     place_vals['warehouse_id'] = warehouse_id
#                     
#                 places_vals.append(
#                     (0,0,place_vals)
#                 )
                
        shipment_data = json_data['Shipment']
        
        truck_plate_number = False
        trailer_plate_number = False
        
        for transport_data in shipment_data.get('TransportHandlingUnit', False)\
         and shipment_data['TransportHandlingUnit'].get('TransportMeans', False) or []:
            if transport_data.get('RoadTransport', False):
                road_transport_attr_data = transport_data['RoadTransport']['_ext_attributes']
                if road_transport_attr_data.get('LicensePlateID', False):
                    if road_transport_attr_data['LicensePlateID']['schemeID'] == 'TRUCK_NUMBER':
                        truck_plate_number = transport_data['RoadTransport']['LicensePlateID']
                    elif road_transport_attr_data['LicensePlateID']['schemeID'] == 'TRAILER_NUMBER':
                        trailer_plate_number = transport_data['RoadTransport']['LicensePlateID']
                                  
        for consignment_data in shipment_data.get('Consignment', []):
            id_container = consignment_data.get('ID', False)
            code = consignment_data.get('HandlingCode', False)
            if id_container:
                self._cr.execute('''
                    SELECT
                        id, code
                    FROM
                        account_invoice_container
                    WHERE id_external = %s
                        OR container_no = %s
                    LIMIT 1
                ''', (id_container,id_container))
                sql_res = self._cr.fetchone()
                if sql_res:
                    if not sql_res[1]:
                        self._cr.execute('''
                            UPDATE account_invoice_container
                            SET code = %s
                            WHERE id = %s
                        ''', (code,sql_res[0]))
                else:
                    container_env.create({
                        'id_external': id_container,
                        'container_no': id_container,
                        'code': code
                    }).id
          
        delivery_data = shipment_data['Delivery']
        
        delivery_despatch_data = delivery_data.get('Despatch', False)
        if delivery_despatch_data and delivery_despatch_data.get('DespatchLocation', False):
            despatch_location_data = delivery_despatch_data['DespatchLocation']
            
            location_code = despatch_location_data.get('SubsidiaryLocation', {}).get('Name', False)
            pref_code = despatch_location_data.get('Name', False)
            if location_code:
                location, warehouse = location_env.get_location_warehouse_id_from_code(
                    location_code, return_location_id=True, create_if_not_exists=True
                )
                warehouse_id = warehouse and warehouse.id or False
                location_id = location and location.id or False
        
        promised_delivery_period_vals = {}
        if delivery_data.get('PromisedDeliveryPeriod', False):
            promised_delivery_period_data = delivery_data['PromisedDeliveryPeriod']
            
            promised_delivery_period_vals['start_date'] =\
                promised_delivery_period_data.get('StartDate', False)
            promised_delivery_period_vals['start_time'] =\
                promised_delivery_period_data.get('StartTime', False)
            promised_delivery_period_vals['end_date'] =\
                promised_delivery_period_data.get('EndDate', False) 
            promised_delivery_period_vals['end_time'] =\
                promised_delivery_period_data.get('EndTime', False)
                           
        if delivery_data.get('CarrierParty', False):
            carrier_id = partner_env.create_or_update_partner(delivery_data['CarrierParty'])
        else:
            carrier_id = False
             
        estimated_delivery_period_vals = {}
        if delivery_data.get('EstimatedDeliveryPeriod', False):
            estimated_delivery_period_data = delivery_data['EstimatedDeliveryPeriod']
            
            estimated_delivery_period_vals['start_date'] =\
                estimated_delivery_period_data.get('StartDate', False)
            estimated_delivery_period_vals['start_time'] =\
                estimated_delivery_period_data.get('StartTime', False)
            estimated_delivery_period_vals['end_date'] =\
                estimated_delivery_period_data.get('EndDate', False) 
            estimated_delivery_period_vals['end_time'] =\
                estimated_delivery_period_data.get('EndTime', False)
        
        delivery_location_data = delivery_data.get('DeliveryLocation', False)
        validity_periods_vals = []
        delivery_coordinate_id = False
        posid_code = False
        delivery_address_id = False
        
        despatch_location_data = delivery_despatch_data and delivery_despatch_data.get('DespatchLocation', False) or False
        despatch_address_id = despatch_location_data and partner_env.create_or_update_address(despatch_location_data) or False
        
        if delivery_location_data:
            delivery_address_id = partner_env.create_or_update_address(delivery_location_data)
            
            
            for validity_period_data in delivery_location_data.get('ValidityPeriod', False) or []:
                validity_periods_vals.append((0,0, {
                    'start_date': validity_period_data.get('StartDate'),
                    'start_time': validity_period_data.get('StartTime'),
                    'end_date': validity_period_data.get('EndDate'),
                    'end_time': validity_period_data.get('EndTime'),
                }))
                
                 
            delivery_coordinate_data = delivery_location_data.get('LocationCoordinate', False)
            if delivery_coordinate_data:
                delivery_coordinate_id = coordinate_env.create({
                    'code': delivery_coordinate_data.get('CoordinateSystemCode', ''),
                    'unit_code': "LKS", #Kolkas tik su tokiom veiks
                    'latitude_dagrees': delivery_coordinate_data.get('LatitudeDegreesMeasure', ''),
                    'latitude_minutes': delivery_coordinate_data.get('LatitudeMinutesMeasure', ''),
                    'longitude': delivery_coordinate_data.get('LongitudeDegreesMeasure', ''),
                    'longitude_minutes': delivery_coordinate_data.get('LongitudeMinutesMeasure', ''),
                }).id
 
            attr_data = delivery_location_data['_ext_attributes']
            attr_id_data = attr_data['ID']
            id_id_schema = attr_id_data['schemeID']
            if id_id_schema == 'POS_ID':
                posid_code = delivery_location_data.get('ID', False)
        
        ubl_extensions_data = json_data.get('UBLExtensions', False)\
            and json_data['UBLExtensions'].get('UBLExtension', False) or []
         
        settings_vals = {}
        one_time_customer = False

        for ubl_extension_data in ubl_extensions_data:
            if ubl_extension_data.get('ExtensionReasonCode', False) == "DESPATCH_ADVICE":
                ubl_extension_content = ubl_extension_data.get('ExtensionContent',{})
                settings_data = ubl_extension_content.get('Settings', False)
                if settings_data:
                    one_time_customer = settings_data.get('OneTimeCustomer', False)
                    settings_vals = {
                        'id_source_doc': settings_data.get('DocumentSourceID', False),
                        'shipment_type': settings_data.get('ShipmentType', False),
                        'id_bls_shipment': settings_data.get('BLSShipmentID', False),
                    }
        if not settings_vals.get('id_bls_shipment', False):
            raise UserError(
                _('Can not find BLSShipmentID.')
            )
                   
        buyer_id = False
        one_time_buyer_id = False    
        if json_data.get('BuyerCustomerParty', False) and json_data['BuyerCustomerParty'].get('Party', False):
            buyer_party_data = json_data['BuyerCustomerParty']['Party']
            if one_time_customer:
                one_time_buyer_id = order_partner_env.create_from_data(buyer_party_data)
                buyer_id = self.env.ref('config_bls_stock.res_partner_template_partner', False)[0].id
            else:
                buyer_id = partner_env.create_or_update_partner(buyer_party_data)

        res = {
            'id_external': json_data.get('UUID', name),
            'name': name,
            'issue_datetime': issue_datetime,
            'buyer_id': buyer_id,
            'seller_id': seller_id,
            'owner_partner_id': owner_partner_id,
            'receiver_id': receiver_id,
            'despatch_place_ids': places_vals,
            'truck_reg_plate': truck_plate_number,
            'trailer_reg_plate': trailer_plate_number,
            'actual_delivery_date': delivery_data.get('ActualDeliveryDate', False),
            'delivery_address_id': delivery_address_id,
            'despatch_address_id': despatch_address_id,
            'carrier_id': carrier_id,
            'container_line_ids': container_lines_vals,
            'promised_delivery_period_id': date_time_period_env.create(promised_delivery_period_vals).id,
            'estimated_delivery_period_id': estimated_delivery_period_vals\
                and date_time_period_env.create(estimated_delivery_period_vals).id or False,
            'delivery_terms': delivery_data.get('DeliveryTerms', False)\
                and delivery_data['DeliveryTerms'].get('ID', False) or "CIP",
            'validity_period_ids': validity_periods_vals,
            'note': re.sub(html_cleaner, '', json_data.get('Note', '')),
            'delivery_coordinate_id': delivery_coordinate_id,
            'one_time_buyer_id': one_time_buyer_id,
            'warehouse_id': warehouse_id,
            'location_id': location_id,
            'owner_id': owner_id,
            'posid_code': posid_code,
            'pref_code': pref_code,
            'despatch_type': "in_sale",
        }
        res.update(settings_vals)

        return (res, intermediates)
    
    @api.multi
    def create_stock_pickings(self, confirmation_type=False):
        stock_picking_env = self.env['stock.picking']
        stock_move_env = self.env['stock.move']
        loc_env = self.env['stock.location']
#         stock_picking_type_env = self.env['stock.picking.type']
#         warehouse_env = self.env['stock.warehouse']
        
#         customer_location = loc_env.search([
#             ('usage','=','customer')
#         ], limit=1)
        
        created_pickings = self.env['stock.picking']
        
        pick_vals = stock_picking_env.default_get(stock_picking_env._fields)
        pick_vals['received_by_user_id'] = SUPERUSER_ID
        if confirmation_type:
            pick_vals['confirmation_type'] = confirmation_type

        for despatch in self:
#             location = despatch.location_id or False
#             location_id = location and location.id or False
#             parent_location_id =  location and location.location_id and location.location_id.id or False 
#             warehouse = despatch.warehouse_id or False
#             warehouse_id = warehouse and warehouse.id or False
            
            self._cr.execute('''
                SELECT
                    owner_id
                FROM
                    despatch_advice
                WHERE id = %s
                LIMIT 1
            ''', (despatch.id,))
            owner_id, = self._cr.fetchone()
            
            self._cr.execute('''
                SELECT
                    location_id, warehouse_id
                FROM
                    despatch_advice
                WHERE id = %s
                    AND location_id is not NULL
                    AND warehouse_id is not NULL
                LIMIT 1
            ''', (despatch.id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                location_id, warehouse_id = sql_res
            else:
#             if not (location_id and warehouse_id):
                self._cr.execute('''
                    SELECT
                        location_id, warehouse_id
                    FROM
                        despatch_advice_despatch_place
                    WHERE despatch_advice_id = %s
                        AND location_id is not NULL
                    LIMIT 1
                ''', (despatch.id,))
                sql_res = self._cr.fetchone()
                if sql_res:
                    location_id, warehouse_id = sql_res 
#                 location_id = location_id or sql_res and sql_res[0]
#                 if not warehouse_id:
#                     warehouse_id = sql_res and sql_res[1]
#                     warehouse = warehouse_env.browse(warehouse_id)
  
            if not warehouse_id:
                raise UserError(
                    _('Can not find warehouse')
                )
                
#             dest_location_id = False
            self._cr.execute('''
                SELECT
                    asn_location_id, code
                FROM
                    stock_warehouse
                WHERE id = %s
                LIMIT 1
            ''', (warehouse_id,))
            asn_location_id, wh_code = self._cr.fetchone()
            
            if location_id:
                self._cr.execute('''
                    SELECT
                        location_id
                    FROM
                        stock_location
                    WHERE id = %s
                    LIMIT 1
                ''', (location_id,))
                sql_res = self._cr.fetchone()
                parent_location_id = sql_res and sql_res[0]
            else:
                parent_location_id = False

            if asn_location_id:
                dest_location_id = asn_location_id
            else:
                da_loc_vals = loc_env.default_get(loc_env._fields)
                da_loc_vals['asn_location'] = True
                da_loc_vals['name'] = wh_code
                da_loc_vals['usage'] = 'internal'
                da_loc_vals['location_id'] = parent_location_id
                
                dest_location_id = loc_env.create(da_loc_vals).id
#                 warehouse.write({'asn_location_id': dest_location_id})

                self._cr.execute('''
                    UPDATE
                        stock_warehouse
                    SET
                        asn_location_id = %s
                    WHERE id = %s
                ''', (dest_location_id, warehouse_id))





            self._cr.execute('''
                SELECT
                    id, product_id, qty
                FROM
                    account_invoice_container_line
                WHERE despatch_advice_id = %s
            ''', (despatch.id,))
            container_line_tuples = self._cr.fetchall()

            for container_line_tuple in container_line_tuples:
#                 container_line_read = container_line.read(['product_id', 'qty'])
#                 product_id = container_line_read[0]['product_id']
#                 total_qty = container_line_read[0]['qty'] or 0.0

                container_line_id, product_id, total_qty = container_line_tuple
                
#                 location_id = False
#                 warehouse_id = False
#                 
#                 if desp_location_id:
#                     location_id = desp_location_id
#                     warehouse_id = desp_warehouse_id
#                 else:
#                     order_line = container_line.order_line_id
#                     if len(order_line.order_line_warehouse_ids) == 1:
#                         order_line_wh = order_line.order_line_warehouse_ids[0]
#                         
#                         location_id = order_line_wh.location_id and order_line_wh.location_id.id or False
#                         warehouse_id = order_line_wh.warehouse_id and order_line_wh.warehouse_id.id or False  
  
#                 picking = created_pickings.filtered(lambda r: r.location_id.id == location_id)

                if created_pickings:
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            stock_picking
                        WHERE location_id = %s
                            AND id in %s
                        LIMIT 1
                    ''', (location_id, tuple(created_pickings.ids)))
                    sql_res = self._cr.fetchone()
                    
                    picking_id = sql_res and sql_res[0] or False
                else:
                    picking_id = False

                if not picking_id:
                    this_picking_vals = pick_vals.copy()
                    this_picking_vals['location_id'] = location_id
                    this_picking_vals['location_dest_id'] = dest_location_id
                    this_picking_vals['despatch_id'] = despatch.id
                    this_picking_vals['id_external'] = uuid.uuid1()

                    type_record_id = False
                    if warehouse_id:
#                         type_record = stock_picking_type_env.search([
#                             ('code','=','outgoing'),
#                             ('warehouse_id','=',warehouse_id)
#                         ], limit=1)
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
                        type_record_id = sql_res and sql_res[0] or False
                    if not type_record_id:
#                         type_record = stock_picking_type_env.search([
#                             ('code','=','outgoing')
#                         ], limit=1)
                        self._cr.execute('''
                            SELECT
                                id
                            FROM
                                stock_picking_type
                            WHERE code = 'outgoing'
                            LIMIT 1
                        ''')
                        sql_res = self._cr.fetchone()
                        type_record_id = sql_res and sql_res[0] or False

                    this_picking_vals['picking_type_id'] = type_record_id
                    picking = stock_picking_env.with_context(tracking_disable=True, recompute=False).create(this_picking_vals)
                    
                    created_pickings += picking
                    picking_id = picking.id
                    
                move_vals = {
                    'product_uom_qty': total_qty,
                    'product_uos_qty': total_qty,
                    'picking_id': picking_id,
                    'location_id': location_id,
                    'location_dest_id': dest_location_id,
                    'product_id': product_id,
                    'container_line_id': container_line_id,
                }
                temp_move = stock_move_env.new(move_vals)
                temp_move.onchange_product_id()
                move_vals.update(temp_move._convert_to_write(temp_move._cache))

                stock_move_env.with_context(tracking_disable=True, recompute=False).create(move_vals)
                
#                 for order_line_wh in order_line.order_line_warehouse_ids.sorted(key=lambda r: r.sequence):
#                     location = order_line_wh.location_id
#                     warehouse = order_line_wh.warehouse_id
#                     
#                     if order_line_wh.quantity:
#                         qty = order_line_wh.quantity
#                         total_qty -= order_line_wh.quantity
#                     else:
#                         qty = total_qty
#                         total_qty = 0.0
#                         
#                     picking = created_pickings.filtered(lambda r: r.location_id == location)
#                     if not picking:
#                         this_picking_vals = pick_vals.copy()
#                         this_picking_vals['location_id'] = location.id
#                         this_picking_vals['location_dest_id'] = customer_location.id
#                         
#                         picking = stock_picking_env.create(this_picking_vals)
                            
#         created_pickings.action_reserve()


        created_pickings.with_context(qty_sql_write=True).action_confirm_bls()
        created_pickings.set_version()
   
        return created_pickings
    
    
    @api.multi
    def recalc_depended_values(self):
        self.ensure_one()
        vals = {}
        if self.delivery_address_id:
            vals['posid_code'] = self.delivery_address_id.possid_code or ''
        if vals:
            self.write(vals)
        
        return True
    
    @api.model
    def create(self, vals):
        res = super(DespatchAdvice, self).create(vals)
#         res.recalc_depended_values()
#         res.link_with_sale_order()
        return res     
    
    
    @api.multi
    def link_with_sale_order(self, sale_order_id=False, skip_order_checking=False):
        sale_order_env = self.env['sale.order']
        for despatch in self:
            if not skip_order_checking: #True ateis kai issikvies is paties orderio sukurimo
                self._cr.execute('''
                    SELECT
                        aicl.order_id, aicl.order_line_id
                    FROM
                        account_invoice_container_line AS aicl
                    JOIN
                        despatch_advice AS da ON (
                            aicl.despatch_advice_id = da.id
                        )
                    WHERE da.id = %s
                    LIMIT 1
                ''', (despatch.id,))
                sql_res = self._cr.fetchone()
                if sql_res:
                    order_id, order_line_id = sql_res
                    if not (order_id and order_line_id):
                        continue

            so_id = False
            if sale_order_id:
                so_id = sale_order_id
            else:
                self._cr.execute('''
                    SELECT
                        id_bls_shipment
                    FROM
                        despatch_advice
                    WHERE id = %s
                ''', (despatch.id,))
                id_bls_shipment, = self._cr.fetchone()
                if id_bls_shipment:
                    self._cr.execute('''
                        SELECT
                            id
                        FROM
                            sale_order
                        WHERE name = %s
                        LIMIT 1
                    ''', (id_bls_shipment, ))
                    sql_res = self._cr.fetchone()
                    if not sql_res:
                        continue
                    so_id, = sql_res
            if not so_id:
                continue
            
            self._cr.execute('''
                UPDATE
                    despatch_advice
                SET sale_order_id = %s
                WHERE id = %s
            ''', (so_id, despatch.id))
            
            self._cr.execute('''
                UPDATE
                    sale_order
                SET linked_with_despatch = True
                WHERE id = %s
            ''', (so_id, ))
            
            sale_order = sale_order_env.browse(so_id)
            sale_order.calc_picked_qty_from_despatch()
            
        return True
#         



#         if sale_order_id:
#             self.write({'sale_order_id': sale_order_id})
#             sale_order = sale_order_env.browse(sale_order_id)
#             sale_order.calc_picked_qty_from_despatch()
#         else:
#             for despatch in self:
#                 despatch_read = despatch.read(['id_bls_shipment'])
#                 name = despatch_read[0]['id_bls_shipment']
#                 if name:
#                     sale_order = sale_order_env.search([
#                         ('name','=',name)
#                     ], limit=1)
#                     if sale_order:
# #                         despatch.write({'sale_order_id': sale_order.id})
# #                         sale_order.write({'linked_with_despatch': True})
#                         self._cr.execute('''
#                             UPDATE
#                                 despatch_advice
#                             SET sale_order_id = %s
#                             WHERE id = %s
#                         ''', (sale_order.id, despatch.id))
#                         
#                         self._cr.execute('''
#                             UPDATE
#                                 sale_order
#                             SET linked_with_despatch = True
#                             WHERE id = %s
#                         ''', (sale_order.id, ))
# 
#                         sale_order.calc_picked_qty_from_despatch()
#         return True
    
    
    
#     @api.multi                
#     def create_sale_order(self):
#         sale_order_env = self.env['sale.order']
#         for da in self:
#             if da.sale_order_id:
#                 continue
#             
#             self._cr.execute('''
#                 SELECT
#                     DISTINCT(transo.transport_type_id)
#                 FROM
#                     transportation_order AS transo
#                 LEFT JOIN
#                     account_invoice_container_line AS aicl ON (
#                         aicl.order_id = transo.id
#                     )
#                 WHERE aicl.despatch_advice_id = %s
#                  AND transo.transport_type_id is not NULL
#             ''', (da.id,))
#             sql_res = self._cr.fetchall()
#             if len(sql_res) == 1:
#                 transport_type_id = sql_res[0]
#             else:
#                 transport_type_id = False
#             
#             
#             
#             self._cr.execute('''
#                 SELECT
#                     tol.id
#                 FROM
#                     transportation_order_line tol
#                 LEFT JOIN
#                     account_invoice_container_line aicl ON (
#                         aicl.order_line_id = tol.id
#                     )
#                 WHERE tol.fully_picked = false
#                     AND aicl.despatch_advice_id = %s
#                 LIMIT 1
#             ''', (da.id,))
#             sql_res = self._cr.fetchone()
#             
#             fully_picked = not sql_res and True or False
#             
#             sale_vals = sale_order_env.default_get(sale_order_env._fields)
#             sale_vals['despatch_advice_id'] = da.id
#             sale_vals['name'] = da.name
#             sale_vals['external_sale_order_id'] = da.name
#             sale_vals['partner_id'] = da.buyer_id and da.buyer_id.id or False
#             sale_vals['partner_invoice_id'] = da.buyer_id and da.buyer_id.id or False
#             sale_vals['one_time_partner_id'] = da.one_time_buyer_id and da.one_time_buyer_id.id or False
#             sale_vals['partner_shipping_id'] = da.delivery_address_id and da.delivery_address_id.id or False
#             sale_vals['date_order'] = da.issue_datetime
#             sale_vals['warehouse_id'] = da.warehouse_id and da.warehouse_id.id or False
#             sale_vals['picking_location_id'] = da.location_id and da.location_id.id or False
#             sale_vals['state'] = fully_picked and 'need_invoice' or 'being_collected'
#             sale_vals['transport_type_id'] = transport_type_id
#             sale_vals['owner_partner_id'] = da.owner_partner_id and da.owner_partner_id.id or False
#             sale_vals['lines_count'] = len(da.container_line_ids)
#             sale_vals['shipping_date'] = da.promised_delivery_period_id and\
#                 da.promised_delivery_period_id.end_date or False
#             sale_vals['posid'] = da.posid_code or ''
#             sale_vals['order_package_type'] = 'order'
#             sale_vals['order_type'] = 'order'
#             sale_vals['delivery_type'] = 'delivery'
#             
#             
#             sale_order = sale_order_env.create(sale_vals)
#             sale_order.update_weight()
#             
#             da.container_line_ids.write({
#                 'sale_order_id': sale_order.id
#             })
#             
#             da.write({
#                 'sale_order_id': sale_order.id,
#                 'transport_type_id': transport_type_id,
#             })
#         
#         return True    


                
#     @api.multi
#     def get_receipt_confirmation_vals(self):
#         res = {}
#         
#         return res
    
    @api.multi
    def set_version(self):
        for da in self:
            self._cr.execute('''
                UPDATE
                    despatch_advice
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), da.id))
        return True
    
    @api.multi
    def form_and_save_to_disk(self):
        intermediate_env = self.env['stock.route.integration.intermediate']
        for despatch in self:
            despatch_read = despatch.read([
                'name'
            ])[0]
            despatch_name = despatch_read['name']
  
            customer_despatch_ubl_xml = despatch.get_customer_despatch_ubl()
            if customer_despatch_ubl_xml:
                intermediate_env.xml_save_to_file(customer_despatch_ubl_xml, 'customer_despatch_%s' % (despatch_name,))

        return True
    
    @api.multi
    def get_issue_date_and_time(self):
        self.ensure_one()
        self._cr.execute('''
            SELECT
                issue_datetime, create_date
            FROM
                despatch_advice
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
        
    @api.multi
    def get_delivery_vals(self):
        self.ensure_one()
        partner_env = self.env['res.partner']
    
        res = {}
    
        self._cr.execute('''
            SELECT
                delivery_address_id, despatch_address_id,
                carrier_id, dest_warehouse_id, dest_location_id
            FROM
                despatch_advice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        
        delivery_address_id, despatch_address_id,\
        carrier_id, dest_warehouse_id, dest_location_id = self._cr.fetchone()
        
        despatch_location_tag_vals = False
        if dest_warehouse_id:
            
            self._cr.execute('''
                SELECT
                    code
                FROM
                    stock_warehouse
                WHERE
                    id = %s
                LIMIT 1
            ''', (dest_warehouse_id,))
            wh_code, = self._cr.fetchone()
            
            despatch_location_tag_vals = {
                'name': wh_code,
            }
            
            if dest_location_id:
            
                self._cr.execute('''
                    SELECT
                        code
                    FROM
                        stock_location
                    WHERE
                        id = %s
                    LIMIT 1
                ''', (dest_location_id,))
                loc_code, = self._cr.fetchone()
            
                despatch_location_tag_vals['subsidiary_location'] = {
                    'name': loc_code,
                }
    
        if carrier_id:
            res["carrier_party"] = partner_env.get_partner_vals(carrier_id)
        if delivery_address_id:
            res["delivery_location"] = partner_env.get_partner_location_vals(delivery_address_id)
        if despatch_address_id:
            res["despatch"] = {
                "despatch_location": partner_env.get_partner_location_vals(despatch_address_id)
            }
            
        if despatch_location_tag_vals:
            if not res.get('despatch', False):
                res['despatch'] = {
                    'despatch_location': {}
                }
            res['despatch']['despatch_location'].update(despatch_location_tag_vals)
            
        return res
    
    @api.multi
    def get_customer_despatch_vals(self):
        self.ensure_one()
        partner_env = self.env['res.partner']
        
        issue_date, issue_time = self.get_issue_date_and_time() or ("", "")
        
#         self._cr.execute('''
#             SELECT
#                 buyer_id, name, owner_id, seller_id, despatch_supplier_id,
#                 receiver_id, delivery_address_id, despatch_address_id,
#                 carrier_id, truck_reg_plate, trailer_reg_plate, route_id,
#                 location_id, warehouse_id, dest_warehouse_id, dest_location_id
#             FROM
#                 despatch_advice
#             WHERE id = %s
#             LIMIT 1
#         ''', (self.id,))
#         buyer_id, name, owner_id, seller_id, despatch_supplier_id,\
#         receiver_id, delivery_address_id, despatch_address_id,\
#         carrier_id, truck_reg_plate, trailer_reg_plate,route_id,\
#         location_id, warehouse_id, dest_warehouse_id, dest_location_id = self._cr.fetchone()

        self._cr.execute('''
            SELECT
                buyer_id, name, owner_id, seller_id, despatch_supplier_id,
                receiver_id, truck_reg_plate, trailer_reg_plate, id_external
            FROM
                despatch_advice
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        buyer_id, name, owner_id, seller_id, despatch_supplier_id,\
        receiver_id, truck_reg_plate, trailer_reg_plate, id_external = self._cr.fetchone()
        
#         despatch_location_tag_vals = False
#         if dest_warehouse_id:
#             
#             self._cr.execute('''
#                 SELECT
#                     code
#                 FROM
#                     stock_warehouse
#                 WHERE
#                     id = %s
#                 LIMIT 1
#             ''', (dest_warehouse_id,))
#             wh_code, = self._cr.fetchone()
#             
#             despatch_location_tag_vals = {
#                 'name': wh_code,
#             }
#             
#             if dest_location_id:
#             
#                 self._cr.execute('''
#                     SELECT
#                         code
#                     FROM
#                         stock_location
#                     WHERE
#                         id = %s
#                     LIMIT 1
#                 ''', (dest_location_id,))
#                 loc_code, = self._cr.fetchone()
#             
#                 despatch_location_tag_vals['subsidiary_location'] = {
#                     'name': loc_code,
#                 }
                
                
         
        shipment_type = "InterBranch"
        
        
        shipment_vals = {
            "id": "1",
#             "delivery": {
#                 
#             }
            "delivery": self.get_delivery_vals()

        }
        
#         if carrier_id:
#             shipment_vals["delivery"]["carrier_party"] = partner_env.get_partner_vals(carrier_id)
#         if delivery_address_id:
#             shipment_vals["delivery"]["delivery_location"] = partner_env.get_partner_location_vals(delivery_address_id)
#         if despatch_address_id:
#             shipment_vals["delivery"]["despatch"] = {
#                 "despatch_location": partner_env.get_partner_location_vals(despatch_address_id)
#             }
#             
#         if despatch_location_tag_vals:
#             if not shipment_vals["delivery"].get('despatch', False):
#                 shipment_vals["delivery"]['despatch'] = {
#                     'despatch_location': {}
#                 }
#             shipment_vals["delivery"]['despatch']['despatch_location'].update(despatch_location_tag_vals)

            
        if (truck_reg_plate and truck_reg_plate not in ('.','-'))\
            or (trailer_reg_plate and trailer_reg_plate not in ('.','-'))\
        :
            shipment_vals['transport_handling_unit'] = {
                'transport_means' : []
            }
            if truck_reg_plate and truck_reg_plate not in ('.','-'):
                shipment_vals['transport_handling_unit']['transport_means'].append(
                    {
                        'road_transport': {
                            "scheme_id": "TRUCK_NUMBER",
                            "license_plate_id": truck_reg_plate,
                        }
                    }
                )
            if trailer_reg_plate and trailer_reg_plate not in ('.','-'):
                shipment_vals['transport_handling_unit']['transport_means'].append(
                    {
                        'road_transport': {
                            "scheme_id": "TRAILER_NUMBER",
                            "license_plate_id": trailer_reg_plate,
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
            WHERE aicl.despatch_advice_id = %s
        ''', (self.id,))
        container_tuples = self._cr.fetchall()
        for container_tuple in container_tuples:
            containers.append({
                "id": container_tuple[0],
                "handling_code": container_tuple[1]
            })
        if containers:
            shipment_vals['consignment'] = containers
                    
        
        res = {
            "ubl_extensions": {
                "ubl_extension": [
                    {
                        "extension_reason_code": "DESPATCH_ADVICE",
                        "extension_content": {
                            "settings": {
                                "shipment_type": shipment_type,
                            }
                        }
                     
                    }
                ]
            },
            "ubl_version_id": "2.1",
            "customization_id": "BLS",
            "id": name,
            "uuid": id_external,
            "issue_date": issue_date,
            "issue_time": issue_time,
            "shipment": shipment_vals,
        }
        
        buyer_vals = False
        if buyer_id:
            buyer_vals = {"party": partner_env.get_partner_vals(buyer_id)}
            res['buyer_customer_party'] = buyer_vals
            
        if receiver_id:
            res['delivery_customer_party'] = {"party": partner_env.get_partner_vals(receiver_id)}
        elif buyer_vals:
            res['delivery_customer_party'] = buyer_vals
             
#         if not seller_id:
#             raise UserError(
#                 _('Seller partner is missing.')
#             )

        despatch_supplier_vals = False
        if seller_id:     
            seller_vals = {"party": partner_env.get_partner_vals(seller_id)}
            res['seller_supplier_party'] = seller_vals
            despatch_supplier_vals = seller_vals
        if despatch_supplier_id:
            despatch_supplier_vals = {"party": partner_env.get_partner_vals(despatch_supplier_id)}
        
        if despatch_supplier_vals:
            res['despatch_supplier_party'] = despatch_supplier_vals
        
        lines_vals_list = []
        self._cr.execute('''
            SELECT
                id
            FROM
                account_invoice_container_line
            WHERE
                out_despatch_id = %s or despatch_advice_id = %s
            ORDER BY
                id
        ''', (self.id, self.id))
#         line_counter = 0
        container_line_ids_tuple_list = self._cr.fetchall()
        
        pushed_lots = set([])
        
        for container_line_id, in container_line_ids_tuple_list:
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
            
            line_consignment_data = False
            self._cr.execute('''
                SELECT
                    aicl.qty, aic.container_no
                FROM
                    account_invoice_container_line AS aicl
                JOIN
                    account_invoice_container AS aic ON (
                        aic.id = aicl.container_id
                    )
                WHERE 
                    aicl.id = %s
                LIMIT 1
            ''', (container_line_id,))
            sql_res = self._cr.fetchone()
            if sql_res:
                line_qty, container_no = sql_res
                
                line_consignment_data = {
                    'id': container_no,
                    'consignment_quantity': line_qty,
                }
            
            if lot_id and line_consignment_data and lot_id in pushed_lots:
                self._cr.execute('''
                    SELECT
                        name
                    FROM
                        stock_production_lot
                    WHERE id = %s
                    LIMIT 1
                ''', (lot_id,))
                lot_name, = self._cr.fetchone()
                for desp_line_vals in lines_vals_list:
                    if desp_line_vals.get('item_instance', {}).get('lot_identification', {})\
                        .get('lot_number_id', False) == lot_name\
                    :
                        if not desp_line_vals.get('shipment', False):
                            desp_line_vals['shipment'] = {
                                'id': 1
                            }
                        
                        if not desp_line_vals['shipment'].get('consignment', False):
                            desp_line_vals['shipment']['consignment'] = []
                            
                        desp_line_vals['shipment']['consignment'].append(line_consignment_data)
                        
                        desp_line_vals['delivered_quantity'] += line_qty
            
            else:
#                 line_counter += 1 
                self._cr.execute('''
                    SELECT
                        uom_id, product_id, qty, barcode_str,
                        order_line_id, id_order, id_order_line, id_despatch_line
                    FROM
                        account_invoice_container_line
                    WHERE id = %s
                    LIMIT 1
                ''', (container_line_id,))
                uom_id, prod_id, qty, barcode_str,\
                transportation_order_line_id, id_order, id_order_line, id_despatch_line = self._cr.fetchone()
                
                uom = False    
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
                
                line_vals = {
                    # "id": id_despatch_line or str(container_line_id), blogai paduodant desp eilutės ID nes gali dubliuotis
                    "id": str(container_line_id),
                    "delivered_quantity": qty,
                    "item": {
                        "description": prod_name,
                        "additional_item_identification": [
                            {
                                "id": default_code,
                                "scheme_id": "PRODUCT_CODE",
                                "scheme_name": "Product code",
                                "scheme_agency_id": "BLS"
                            }
                        ]
                    },
                    "quantity_unit_code": uom,
                }
                 
                if barcode_str:
                    line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode_str
    
                certificates = []
                self._cr.execute('''
                    SELECT
                        certificate_id
                    FROM
                        container_line_certificate_rel
                    WHERE container_line_id = %s
                ''', (container_line_id,))
                certificate_ids_tuple_list = self._cr.fetchall()
                for certificate_id, in certificate_ids_tuple_list:
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
                                "start_date": datetime.datetime.strptime(
                                    cert_valid_from, "%Y-%m-%d"
                                ).date(),
                                "end_date": datetime.datetime.strptime(
                                    cert_valid_to, "%Y-%m-%d"
                                ).date(),
                            }                      
                    certificates.append(cert_vals)
                     
                if certificates:
                    line_vals["item"]["certificate"] = certificates
                    
    #             self._cr.execute('''
    #                  SELECT
    #                      lot_id
    #                  FROM
    #                      container_line_lot_rel
    #                  WHERE container_line_id = %s
    #                  LIMIT 1
    #              ''', (container_line_id,))
    #             sql_res = self._cr.fetchone()
                  
                if lot_id:
#                     lot_id, = sql_res
                    self._cr.execute('''
                        SELECT
                            name, expiry_date
                        FROM
                            stock_production_lot
                        WHERE id = %s
                        LIMIT 1
                    ''', (lot_id,))
                    lot_cert_name, lot_expiry_date = self._cr.fetchone()
                     
                    line_vals["item_instance"] = {
                        "lot_identification": {
                            'lot_number_id': lot_cert_name,
    #                         'expiry_date': datetime.datetime.strptime(
    #                             lot_expiry_date, "%Y-%m-%d"
    #                         )
                        }
                    }
                    if lot_expiry_date:
                        line_vals["item_instance"]['lot_identification']['expiry_date'] = datetime.datetime.strptime(
                            lot_expiry_date, "%Y-%m-%d"
                        )
                      
                if id_order_line:
                    line_vals['order_line_reference'] = {
                        'line_id': id_order_line
                    }
                    if id_order:
                        line_vals['order_line_reference']['order_reference'] = {"id": id_order}
                        
                if line_consignment_data:
                    if not line_vals.get('shipment', False):
                        line_vals['shipment'] = {
                            'id': 1
                        }
 
                    line_vals['shipment']['consignment']=  [line_consignment_data]
                        
                lines_vals_list.append(line_vals)
            if lot_id:
                pushed_lots.add(lot_id)
            
        if not lines_vals_list:
            return False
        res['despatch_line'] = lines_vals_list
        
        return res
    
    @api.multi
    def get_customer_despatch_ubl(self, pretty=False):
        self.ensure_one()
        customer_despatch_vals = self.get_customer_despatch_vals()
        if not customer_despatch_vals:
            return False

        data_xml = da_schema.dumps(
            customer_despatch_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )
 
        return data_xml
    
    @api.model
    def get_one_despatch(self, despatch_type, identificator, id_value):
        ubl_xml = False
        start_datetime = datetime.datetime.now()
        
        integration_intermediate_env = self.env['stock.route.integration.intermediate']
        
        receive_vals = "<despatch_type> - %s\n<identificator> - %s\n<id> - %s" % (despatch_type, identificator, id_value)
        result_vals = ''
        processed = True
        trb = ''
        
        intermediate = integration_intermediate_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'SendOneDespatch',
            'received_values': receive_vals,
            'processed': False
        })
        self.env.cr.commit()

        if despatch_type == 'sale_despatch':
            # dabar prie invoiceline visada paduodam du despatchus: jų atsiųstą ir mūsų sugeneruotą.
            # Tada dycodeas bando juos abu ir pasiimt iš Atlaso. O tas BLS atsiųstas turi kitą tipą - in_sale
            desp_type = ('out_sale', 'in_sale')
        else:
            desp_type = 'out_sale' #Ateity atsiras visokiu ELIF'u, kurie nores kitokiu tipu
            
        id_field = identificator == 'id' and "name" or identificator == 'uuid' and "id_external" or identificator

        sql_statement = "SELECT id FROM despatch_advice WHERE despatch_type in '%s' and %s = '%s' LIMIT 1" % (str(desp_type), id_field, id_value)
        self._cr.execute("SELECT id FROM despatch_advice WHERE despatch_type in %s and " + id_field + " = %s LIMIT 1", (desp_type, id_value))
        sql_res = self._cr.fetchone()
        if sql_res:
            desp_id, = sql_res
            
            try:
                despatch = self.browse(desp_id)
                ubl_xml = despatch.get_customer_despatch_ubl()
                ubl_xml = ubl_xml.decode('utf-8')
                result_vals += _('Result: ') + '\n\n' + ubl_xml
            except Exception as e:
                err_note = _('Failed to return despatch: %s') % (tools.ustr(e),)
                result_vals += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                self.env.cr.rollback()
        else:
            ubl_xml = "404"
            result_vals = "Despatch not found. %s" % (sql_statement)
            processed = False
        
        end_datetime = datetime.datetime.now()
        
        intermediate.write({
            'processed': processed,
            'return_results': result_vals,
            'traceback_string': trb,
            'duration': (end_datetime-start_datetime).seconds
        })
        self.env.cr.commit()
        
        return ubl_xml or "Error" 


class DespatchAdviceDespatchPlace(models.Model):
    _name = 'despatch.advice.despatch_place'
    _description = 'Despatch advice despatch places (warehouse, location, address, company)'
    
    name = fields.Char('Name', help="External ID")
    despatch_advice_id = fields.Many2one('despatch.advice', "Despatch Advice")
    partner_id = fields.Many2one('res.partner', "Partner")
    location_id = fields.Many2one('stock.location', "Location")
    warehouse_id = fields.Many2one('stock.warehouse', "Warehouse")
    