# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tools.translate import _
from odoo import api, models, fields, tools
import json
from odoo.exceptions import UserError
import traceback
import time
from datetime import datetime
import pytz

import os

import xml.dom.minidom
import requests

from .import_schemas.models.order.schemas import OrderSchema
from .import_schemas.models.bls_receipt_confirmation.schemas import BlsReceiptConfirmationSchema
from .import_schemas.models.bls_movement.schemas import BlsMovementSchema
from .import_schemas.models.bls_adjustment.schemas import BlsAdjustmentSchema
order_schema = OrderSchema()
bls_receipt_confirmation_schema = BlsReceiptConfirmationSchema()
bls_movement_schema = BlsMovementSchema()
bls_adjustment_schema = BlsAdjustmentSchema()


def utc_str_to_local_str(utc_str=None, date_format='%Y-%m-%d %H:%M:%S', timezone_name='Europe/Vilnius'):
    if not utc_str:
        utc_str = time.strftime(date_format)
    utc_datetime = datetime.strptime(utc_str, date_format).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(timezone_name))
    return utc_datetime.strftime(date_format)


def get_local_time_timestamp():
    return datetime.now().replace(tzinfo=pytz.utc).astimezone(pytz.timezone('Europe/Vilnius')).timestamp()


class StockRouteIntegrationIntermediate(models.Model):
    _inherit = 'stock.route.integration.intermediate'
    _description = 'Intermediate table for importing routes'
    
    @api.model
    def get_selection_values(self):
        return super(StockRouteIntegrationIntermediate, self).get_selection_values() + [
            ('CreateTransportationOrder', 'CreateTransportationOrder'),
            ('CreateDespatchAdvice', 'CreateDespatchAdvice'),
            ('SendElectronicDocumentInvoice', 'SendElectronicDocumentInvoice'),
            ('SendElectronicDocumentWaybill', 'SendElectronicDocumentWaybill'),
            ('SendCustomerDespatchAdvice', 'SendCustomerDespatchAdvice'),
            ('SendAtlasWhDespatchAdvice', 'SendAtlasWhDespatchAdvice'),
            ('SendAtlasWhTransportationOrder', 'SendAtlasWhTransportationOrder'),
            ('SendSaleBlsReceiptConfirmation', 'SendSaleBlsReceiptConfirmation'),
            ('SendOneDespatch', 'SendOneDespatch'),
            ('SendMovement', 'SendMovement'),
            ('SendAdjustment', 'SendAdjustment'),
            ('CreateBlsDespatchAdvice', 'CreateBlsDespatchAdvice'),
        ]

    function = fields.Selection(get_selection_values, 'Function', readonly=False)
    received_values = fields.Text('Received Values', readonly=False)
#     cursor = fields.Integer('Cursor', False)
    id_xml = fields.Char("XML ID", help="It's used to get specific XML from End Point integration")
    valid_xml = fields.Boolean(
        "Valid XML", help="It shows if intermediate result is valid XML or just some kind of error",
        default=False
    )

    @api.multi   
    def process_intermediate_object_transportation_order(self):
        from .import_schemas.models.order.schemas import OrderSchema
        
        to_env = self.env['transportation.order']
        result = {}
        try:
            order_schema = OrderSchema()
            
    #         if self.valid_xml:
    #             xml_str = self.received_values
    #         else:
    #             intermediate = self.get_transportation_order_from_api(id_order=self.id_xml)
    #             if intermediate.received_values:
    #                 xml_str = intermediate.received_values
    #             else:
    #                 return False
    
            self._cr.execute('''
                SELECT
                    valid_xml, id_xml, received_values
                FROM
                    stock_route_integration_intermediate
                WHERE id = %s
                LIMIT 1
            ''', (self.id,))
            sql_res = self._cr.fetchone()
            
            valid_xml, id_xml, received_values = sql_res
            
            if id_xml:
                if valid_xml:
                    xml_str = received_values
                else:
                    intermediate = self.get_transportation_order_from_api(id_order=id_xml)
                    
                    self._cr.execute('''
                        SELECT
                            received_values
                        FROM
                            stock_route_integration_intermediate
                        WHERE id = %s
                        LIMIT 1
                    ''', (intermediate.id,))
                    received_values = sql_res and sql_res[0]
                    if received_values:
                        xml_str = received_values
                    else:
                        return False
            else:
                xml_str = received_values
    
            data = order_schema.loads(xml_str)
            data_json = order_schema.dumps(data, content_type='application/json')
            try:
                data_dict = json.loads(data_json)
            except:
                json_acceptable_string = data_json.replace("'", "\"")
                data_dict = json.loads(json_acceptable_string)
            
            self._cr.commit()
            result = {
                'created_objects': [],
                'result': _('Transportaion order was created successfully'),
                'error':  False
            }

            to_vals = to_env.get_create_vals(data_dict)

            processed = True
            trb = ''
            
            if to_vals:
                to_rec = to_env.create(to_vals)

                to_rec.create_despatch_links()

                to_rec_read = to_rec.read(['id', 'name'])
                result['created_objects'] += [to_rec_read]
            else:
                result = {
                    'created_objects': [],
                    'result': _('This transportation order was already created by another intermediate object.'),
                    'error':  True
                }

        except UserError as e:
            result['result'] = _('Failed to create d: %s') % (tools.ustr(e),)
            processed = False
            trb = traceback.format_exc()
            result['error'] = True
            self._cr.rollback()
        except Exception as e:
            result['result'] = _('Failed to create transportation order: %s') % (tools.ustr(e),)
            processed = False
            trb = traceback.format_exc()
            result['error'] = True
            self._cr.rollback()
            
        vals = {
            'return_results': result,
            'processed': processed,
            'traceback_string': trb,
        }
        self.write(vals)
        self._cr.commit()

        return True
    
    @api.multi   
    def process_intermediate_object_despatch_advice(self):
        from .import_schemas.models.despatch_advice.schemas import DespatchAdviceSchema
        result = {}
        try:
            da_env = self.env['despatch.advice']
            container_line_env = self.env['account.invoice.container.line']
            da_schema = DespatchAdviceSchema()
            
            self._cr.execute('''
                SELECT
                    valid_xml, id_xml, received_values
                FROM
                    stock_route_integration_intermediate
                WHERE id = %s
                LIMIT 1
            ''', (self.id,))
            sql_res = self._cr.fetchone()
            
            valid_xml, id_xml, received_values = sql_res
            
            if id_xml:
                get_orders_from_api = True
                if valid_xml:
                    xml_str = received_values
                else:
                    intermediate = self.get_despatch_from_api(id_desp=id_xml)
        
                    self._cr.execute('''
                        SELECT
                            received_values
                        FROM
                            stock_route_integration_intermediate
                        WHERE id = %s
                        LIMIT 1
                    ''', (intermediate.id,))
                    received_values = sql_res and sql_res[0]
                    if received_values:
                        xml_str = received_values
                    else:
                        return False
            else:
                get_orders_from_api = False
                xml_str = received_values
            
            data = da_schema.loads(xml_str)
            data_json = da_schema.dumps(data, content_type='application/json')
            
#             test_json_data = da_schema.loads(data_json)
#             test_data_xml = da_schema.dumps(test_json_data, content_type='application/xml')
            
            try:
                data_dict = json.loads(data_json)
            except:
                json_acceptable_string = data_json.replace("'", "\"")
                data_dict = json.loads(json_acceptable_string)
                
            self._cr.commit()
            result = {
                'created_objects': [],
                'result': _('Despatch advice was created successfully'),
                'error':  False
            }
#         da_vals, order_intermediates = da_env.get_create_vals(data_dict)

            da_vals, order_intermediates = da_env.get_create_vals(data_dict, get_orders_from_api)
            
            processed = True
            trb = ''
            if da_vals:
                
                da_rec = da_env.create(da_vals)
                
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        account_invoice_container_line
                    WHERE despatch_advice_id = %s
                ''', (da_rec.id, ))
                sql_res = self._cr.fetchall()
                if sql_res:
                    container_line_ids = [i[0] for i in sql_res]
                    container_lines = container_line_env.browse(container_line_ids)
                    container_lines.link_to_order_and_order_line()

                da_rec_read = da_rec.read(['id', 'name'])
                
    #             processed = False
                result['created_objects'] += [da_rec_read]
                
                for order_intermediate in order_intermediates:
                    order_intermediate_read = order_intermediate.read(['id', 'function'])
                    result['created_objects'] += [order_intermediate_read]

                da_rec.link_with_sale_order()
                da_rec.create_stock_pickings(confirmation_type='sale')

            else:
                result = {
                    'created_objects': [],
                    'result': _('This despatch was already created by another intermediate object.'),
                    'error':  True
                }
            
#             stock_pickings.action_reserve()
        except UserError as e:
            result['result'] = _('Failed to create despatch advice: %s') % (tools.ustr(e),)
            processed = False
            trb = traceback.format_exc()
            result['error'] = True
            self._cr.rollback()
        except Exception as e:
            result['result'] = _('Failed to create despatch advice: %s') % (tools.ustr(e),)
            processed = False
            trb = traceback.format_exc()
            result['error'] = True
            self._cr.rollback()
            
        vals = { 
            'return_results': result,
            'processed': processed,
            'traceback_string': trb,
        }
        self.write(vals)
        self._cr.commit()
        
        return True
    
#     @api.multi   
#     def process_intermediate_object_send_electronic_invoice(self):
#         
#         return True
#     
#     @api.multi   
#     def process_intermediate_object_send_electronic_waybill(self):
#         
#         return True
# 
#     @api.multi   
#     def process_intermediate_object_send_customer_despatch(self):
#         
#         return True
    
    @api.multi
    def process_additional_intermediate_object(self):
        res = {}
        
        obj = self.read(['function'])[0]
        
        if obj['function'] == 'CreateTransportationOrder':
            res = self.process_intermediate_object_transportation_order()
        elif obj['function'] == 'CreateDespatchAdvice':
            res = self.process_intermediate_object_despatch_advice()
#         elif obj['function'] == 'SendElectronicDocumentInvoice':
#             res = self.process_intermediate_object_send_electronic_invoice()
#         elif obj['function'] == 'SendElectronicDocumentWaybill':
#             res = self.process_intermediate_object_send_electronic_waybill()
#         elif obj['function'] == 'SendCustomerDespatchAdvice':
#             res = self.process_intermediate_object_send_customer_despatch()
        
        return res
    
    @api.model
    def get_transportation_order_from_api(self, id_order, commit_at_the_end=False):
        interm_env = self.env['stock.route.integration.intermediate']
        uncompleted_intermediate_id = False
        if id_order:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_integration_intermediate
                WHERE id_xml = %s
                    AND function = 'CreateTransportationOrder'
                    AND valid_xml = true
                LIMIT 1
            ''', (id_order,))
            sql_res = self._cr.fetchone()
            if sql_res and sql_res[0]:
                return False
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_integration_intermediate
                WHERE id_xml = %s
                    AND function = 'CreateTransportationOrder'
                    AND valid_xml = false
                LIMIT 1
            ''', (id_order,))
            sql_res = self._cr.fetchone()
            uncompleted_intermediate_id = sql_res and sql_res[0] or False
            
        company = self.env.user.company_id
        
        if not company.despatch_api_link:
            raise UserError(
                _('Despatch API link is missing')
            )
        
        order_link = company.despatch_api_link + "order/%s.xml" % (id_order)
        
        order_response = requests.get(order_link, headers={'Content-type': 'application/json'})
        
        order_content = order_response.content
        order_status = order_response.status_code
        
        if order_status != 200:
#             raise UserError(
#                 _('Error while getting order %s') % (id_order)
#             )
            valid_xml = False
            received_values = order_status
        else:
            valid_xml = True
            received_values = order_content
            
        try:
            received_values = xml.dom.minidom.parseString(received_values.decode("utf-8")).toprettyxml(encoding='utf-8')
        except:
            pass
        
        if uncompleted_intermediate_id:
            intermediate = interm_env.browse(uncompleted_intermediate_id)
            intermediate.write({
                'received_values': received_values,
                'valid_xml': valid_xml
            })
        else:         
            intermediate = interm_env.create({
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                'function': 'CreateTransportationOrder',
                'received_values': received_values,
                'processed': False,
                'id_xml': id_order,
                'valid_xml': valid_xml
            })
            
        if commit_at_the_end:
            self._cr.commit()
        
        return intermediate
    
    @api.model
    def get_despatch_from_api(self, url=False, id_desp=False):
        if not (id_desp or url):
            raise UserError(
                _('Error while getting despatch. No url or despatch ID is given.')
            )
        uncompleted_intermediate_id = False
        if id_desp:
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_integration_intermediate
                WHERE id_xml = %s
                    AND function = 'CreateDespatchAdvice'
                    AND valid_xml = true
                LIMIT 1
            ''', (id_desp,))
            sql_res = self._cr.fetchone()
            if sql_res and sql_res[0]:
                return False
            
            self._cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_integration_intermediate
                WHERE id_xml = %s
                    AND function = 'CreateDespatchAdvice'
                    AND valid_xml = false
                LIMIT 1
            ''', (id_desp,))
            sql_res = self._cr.fetchone()
            uncompleted_intermediate_id = sql_res and sql_res[0] or False
            
        interm_env = self.env['stock.route.integration.intermediate']
        
        if url:
            despatch_link = url
        else:
            company = self.env.user.company_id
            if not company.despatch_api_link:
                raise UserError(
                    _('Despatch API link is missing')
                )
        
            despatch_link = company.despatch_api_link + "despatch_advice/%s.xml" % (id_desp)
        
        despatch_response = requests.get(despatch_link, headers={'Content-type': 'application/json'})
        
        despatch_content = despatch_response.content
        despatch_status = despatch_response.status_code
        
        if despatch_status != 200:
            valid_xml = False
            received_values = despatch_status
#             raise UserError(
#                 _('Error while getting despatch %s') % (id_desp or url)
#             )

        else:
            valid_xml = True
            received_values = despatch_content
        
        try:
            received_values = xml.dom.minidom.parseString(received_values.decode("utf-8")).toprettyxml(encoding='utf-8')
        except:
            pass

        if uncompleted_intermediate_id:
            intermediate = interm_env.browse(uncompleted_intermediate_id)
            intermediate.write({
                'received_values': received_values,
                'valid_xml': valid_xml
            })
        else:     
            intermediate = interm_env.create({
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                'function': 'CreateDespatchAdvice',
                'received_values': received_values,
                'processed': False,
                'id_xml': id_desp,
                'valid_xml': valid_xml
            })
        
        return intermediate
    
    @api.model
    def get_despatch_list_from_api(self):
        company = self.env.user.company_id
        
        if not company.despatch_api_link:
            raise UserError(
                _('Despatch API link is missing')
            )
        
        list_import_limit = company.despatch_import_limit or 200
        
        despatches_link = company.despatch_api_link + "despatch_advice?first=%s" % (
            list_import_limit
        )
        
        if company.desp_adv_cursor:
            despatches_link += "&after=%s" % (company.desp_adv_cursor)
            
        despatches = requests.get(despatches_link, headers={'Content-type': 'application/json'})
        
        despatches_content = despatches.content
        despatches_status = despatches.status_code
        
        if despatches_status != 200:
            raise UserError(
                _('Error while getting despatch list with URL %s') % (despatches_link)
            )
            
        despatches_content = despatches_content.decode('utf8').replace("'", '"')
        desp_list_dict = json.loads(despatches_content)
                      
        desp_cursor = 0

        desp_list = desp_list_dict.get('edges', [])
        
#         if len(desp_list) == list_import_limit:
#             repeat_list_import = True
#         else:
#             repeat_list_import = False
        
        for desp_list_item in desp_list:
            cursor = desp_list_item['cursor']
            id_desp = desp_list_item['node']['id']
            despt_api_link_end = desp_list_item['node']['url']
            if despt_api_link_end.startswith('/api/'):
                despt_api_link_end = despt_api_link_end[5:]
            despt_api_link = company.despatch_api_link + despt_api_link_end
            
            self.get_despatch_from_api(url=despt_api_link, id_desp=id_desp)
            if cursor > desp_cursor:
                desp_cursor = cursor
            self._cr.commit()
   
        if desp_cursor:
            company.write({'desp_adv_cursor': desp_cursor})
        self._cr.commit()
        
#         if repeat_list_import:
#             self.get_despatch_list_from_api()
                
        return True
    
    
    @api.model
    def create_despatch_intermediate(self, xml_str):
        interm_env = self.env['stock.route.integration.intermediate']
        
        try:
            received_values = xml.dom.minidom.parseString(xml_str.decode("utf-8")).toprettyxml(encoding='utf-8')
        except:
            pass
        
        interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'CreateDespatchAdvice',
            'received_values': received_values,
            'processed': False,
        })
        
        return True

    @api.model
    def create_bls_despatch_intermediate(self, xml_str):
        interm_env = self.env['stock.route.integration.intermediate']

        try:
            received_values = xml.dom.minidom.parseString(xml_str.decode("utf-8")).toprettyxml(encoding='utf-8')
        except:
            pass

        interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'CreateBlsDespatchAdvice',
            'received_values': received_values,
            'processed': False,
        })

        return True

    @api.model
    def create_transportation_order_intermediate(self, xml_str):
        interm_env = self.env['stock.route.integration.intermediate']
        
        try:
            received_values = xml.dom.minidom.parseString(xml_str.decode("utf-8")).toprettyxml(encoding='utf-8')
        except:
            pass
        
        interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'CreateTransportationOrder',
            'received_values': received_values,
            'processed': False,
        })
        
        return True

    @api.model
    def get_ubl_documents_json_vals(self, id_version, ubl_doc):
#         res = {}
        res = []
        start_datetime = datetime.now()
#         invoice_env = self.env['account.invoice']
        integration_intermediate_env = self.env['stock.route.integration.intermediate']

        domain = [
            ('id_version','>',id_version),
            ('id_external','!=',False)  #sitas pades isvengti, kad neluztu ant senos strukturos irasu
        ]
        
        
        if ubl_doc == 'invoice':
            domain += [('category','=',ubl_doc), ('generated_in_atlas','=',True)]
            # Dabar kazkodel ateina vien tik dokumentai, kurie praso PAPER formos, tad kad butu galima testuotis paduodam visus
#             domain += [('sending_type','in',('electronical', 'paper_edi'))]
            function = "SendElectronicDocumentInvoice"
            method = 'get_invoice_ubl'
            obj_env = self.env['account.invoice']
            table_name = 'account_invoice'
        elif ubl_doc == 'waybill':
            # Dabar kazkodel ateina vien tik dokumentai, kurie praso PAPER formos, tad kad butu galima testuotis paduodam visus
#             domain += [('sending_type','in',('electronical', 'paper_edi'))]
            domain += [('category','=',ubl_doc), ('generated_in_atlas','=',True)]
            function = "SendElectronicDocumentWaybill"
            method = 'get_waybill_ubl'
            obj_env = self.env['account.invoice']
            table_name = 'account_invoice'
        elif ubl_doc in ['despatch', 'sale_despatch']:
            function = "SendCustomerDespatchAdvice"
            method = 'get_customer_despatch_ubl'
            obj_env = self.env['despatch.advice']
            table_name = 'despatch_advice'
            domain += [('despatch_type','=','out_sale')]
        elif ubl_doc == 'atlas_wh_despatch':
            function = "SendAtlasWhDespatchAdvice"
#             method = 'get_atlas_wh_despatch_ubl'
            method = 'get_customer_despatch_ubl'
            obj_env = self.env['despatch.advice']
            table_name = 'despatch_advice'
            domain += [('despatch_type','=','out_atlas_wh')]
        elif ubl_doc == 'atlas_wh_order':
            function = "SendAtlasWhTransportationOrder"
            method = 'get_transportation_order_ubl'
            obj_env = self.env['stock.picking']
            table_name = 'stock_picking'
            domain += [('picking_from_warehouse_for_internal_order_id','!=',False), ('operation_type','=','atlas_movement')]
        elif ubl_doc in ('bls_receipt_confirmation', 'sale_bls_receipt_confirmation'):
            function = "SendSaleBlsReceiptConfirmation"
            method = 'get_bls_receipt_confirmation_ubl'
            obj_env = self.env['stock.picking']
            table_name = 'stock_picking'
            domain += [('received_by_user_id','!=',False), ('despatch_id','!=',False), ('confirmation_type','=','sale')]
        elif ubl_doc in ['movement']:
            function = "SendMovement"
            method = 'get_movement_ubl'
            obj_env = self.env['stock.picking']
            table_name = 'stock_picking'
            domain += [('operation_type','=','warehouse_movement')]
        elif ubl_doc in ['adjustment']:
            function = "SendAdjustment"
            method = 'get_adjustment_ubl'
            obj_env = self.env['stock.picking']
            table_name = 'stock_picking'
            domain += [('operation_type','=','adjustment')]
        else:
            function = ""
            
        receive_vals = "<ubl_doc> - %s\n<id_version> - %s" % (ubl_doc, id_version)
        result_vals = ''
        processed = True
        trb = ''
            
        intermediate = integration_intermediate_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': function,
            'received_values': receive_vals,
            'processed': False
        })
        self.env.cr.commit()
        
        try:
            if not function:
                raise UserError(
                    _('Unknown UBL document: %s') % (ubl_doc)
                )
            doc_limit = self.env.user.company_id.ubl_export_limit 
            documents = obj_env.search(domain, limit=doc_limit, order='id_version ASC')
            for document in documents:
#                 ubl_xml = getattr(document, method)().decode('utf-8').encode('unicode-escape')
                ubl_xml = getattr(document, method)()
                if not ubl_xml:
                    continue
                ubl_xml = ubl_xml.decode('utf-8')
                
                self._cr.execute('''
                    SELECT
                        id_version
                    FROM ''' + table_name + '''
                    WHERE id = %s
                    LIMIT 1
                ''', (document.id,))
                id_version, = self._cr.fetchone()
                
                
                
#                 xsd_validation_error = self.check_xsd_validity(ubl_xml, ubl_doc)
#                 if xsd_validation_error:
#                     print ("\n\n\n xsd_validation_error: ", xsd_validation_error, id_version)
                
                res.append(
                    {
                        'id_version': id_version,
                        'data': ubl_xml
                    }
                )
#                 res[id_version] = ubl_xml

#             result_vals += _('Result: ') + '\n\n' + str(json.dumps(res, indent=2))
            result_vals += _('Result: ') + '\n\n' + str(json.dumps(res, indent=2))
            if documents:
                if ubl_doc == 'despatch':
                     self._cr.execute('''
                        UPDATE despatch_advice
                        SET customer_despatch_intermediate_id = %s
                        WHERE id in %s
                    ''', (intermediate.id, tuple(documents.ids)))
                else:
                    self._cr.execute('''
                        UPDATE account_invoice
                        SET intermediate_id = %s
                        WHERE id in %s
                    ''', (intermediate.id, tuple(documents.ids))) 
        except Exception as e:
            err_note = _('Failed to return %s UBLs: %s') % (ubl_doc, tools.ustr(e),)
            result_vals += err_note
            processed = False
            trb += traceback.format_exc() + '\n\n'
            self.env.cr.rollback()
        
        end_datetime = datetime.now()
        
        intermediate.write({
            'processed': processed,
            'return_results': result_vals,
            'traceback_string': trb,
            'duration': (end_datetime-start_datetime).seconds
        })
        self.env.cr.commit()
        
        return processed and res or "Error"
    
    @api.model
    def xml_save_to_file(self, xml_data, name):
        company = self.env.user.company_id
        
        self._cr.execute("""
            SELECT
                ubl_save_directory
            FROM
                res_company
            WHERE id = %s
            LIMIT 1
        """ , (company.id,))
        ubl_save_directory, = self._cr.fetchone()
        if not ubl_save_directory:
            raise UserError(
                _("UBL save directory is missing in the company configurations")
            )
            
        if ubl_save_directory.startswith('~'):
            home = os.path.expanduser("~")
            ubl_save_directory = home + ubl_save_directory[1:]
        
        if not os.path.exists(ubl_save_directory):
            os.makedirs(ubl_save_directory)
            
        with open(os.path.join(ubl_save_directory, name+".xml"), 'wb') as f:
            f.write(xml_data)
#             f.closed
        return True
    
      
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    @api.model
    def get_state_selection(self):
        return [
            ('draft', _('Draft')),
#             ('waiting', 'Waiting Another Operation'),
#             ('confirmed', 'Waiting'),
#             ('assigned', 'Ready'),
            ('reserved', _('Reserved')),
            ('done', _('Done')),
            ('cancel', _('Cancelled')),
        ]
    
    @api.model
    def _get_confirmation_type_selection(self):
        return [
            ('supply', _("Supply")), 
            ('atlas_dos', _("Atlas DOS")),
            ('atlas_wh', _("Atlas Wh")),
            ('sale', _("Sale")), 
        ]
    
    state = fields.Selection(
        get_state_selection, string='Status', readonly=True,
        track_visibility='onchange', default='draft'
    )
    despatch_id = fields.Many2one('despatch.advice', "Despatch", index=True)
    id_version = fields.Char('Version', size=128, readonly=True)
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Intermediate', readonly=True
    )
    transportation_order_no = fields.Char("Transportation Order No.", size=32)
    id_external = fields.Char("External ID", size=64, readonly=True)
    confirmation_type = fields.Selection(_get_confirmation_type_selection, "Despatch Type")
    
    @api.multi
    def set_version(self):
        for picking in self:
            self._cr.execute('''
                UPDATE
                    stock_picking
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), picking.id))
        return True
    
    @api.multi
    def set_transportation_order_no(self):
        doc_type_env = self.env['document.type']
        warehouse_env = self.env['stock.warehouse']
        owner_env = self.env['product.owner']
        
        warehouse_id = self.env.user.get_main_warehouse_id()
        warehouse = warehouse_env.browse(warehouse_id)
        
        for picking in self:
            self._cr.execute('''
                SELECT
                    owner_id
                FROM
                    stock_picking
                WHERE
                    id = %s
            ''', (picking.id,))
            owner_id, = self._cr.fetchone()
            owner = owner_env.browse(owner_id)

            transportation_order_no = doc_type_env.get_next_number_by_code(
                'out.transportation.order', warehouse=warehouse, owner=owner
            )
            
            self._cr.execute('''
                UPDATE
                    stock_picking
                SET
                    transportation_order_no = %s
                WHERE id = %s
            ''', (transportation_order_no, picking.id))
        return True
    
    @api.model
    def get_issue_date_and_time(self, issue_date_time):
        if len(issue_date_time) > 19:
            issue_date_time = issue_date_time[:19]
            
        tz_date_time_str = self.env.user.convert_datetime_to_user_tz(issue_date_time)
        tz_date_time = datetime.strptime(
            tz_date_time_str, "%Y-%m-%d %H:%M:%S"
        )
        issue_date = tz_date_time.date()
        issue_time = tz_date_time.time()
        
        return (issue_date, issue_time)
    
    @api.multi
    def get_transportation_order_vals(self):
        self.ensure_one()
        partner_env = self.env['res.partner']
        
        user = self.env.user
        
        self._cr.execute("""
            SELECT
                date, create_date, transportation_order_no,
                picking_from_warehouse_for_internal_order_id,
                id_external
            FROM
                stock_picking
            WHERE
                id = %s
            LIMIT 1
        """ , (self.id,))
        picking_date, create_date, name,\
        internal_operation_id, id_external = self._cr.fetchone()
        
        dest_warehouse_id = False
        dest_location_id = False
        
        if internal_operation_id:
            self._cr.execute('''
                SELECT
                    iopm.warehouse_to_id, iop.location_to_id
                FROM
                    internal_operation AS iop
                JOIN
                    internal_operation_movement AS iopm ON (
                        iopm.operation_id = iop.id
                    )  
                WHERE 
                    iop.id = %s
                LIMIT 1
            ''', (internal_operation_id,))
            dest_warehouse_id, dest_location_id = self._cr.fetchone()
        
        delivery_tag_vals = False
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
            
            delivery_tag_vals = {
                'despatch': {
                    'despatch_location': {
                        'name': wh_code,
                    }
                }
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
            
                delivery_tag_vals['despatch']['despatch_location']['subsidiary_location'] = {
                    'name': loc_code,
                }
        
        issue_date_time = picking_date or create_date
        issue_date, issue_time = self.get_issue_date_and_time(issue_date_time)
#         if len(issue_date_time) > 19:
#             issue_date_time = issue_date_time[:19]
#             
#         tz_date_time_str = self.env.user.convert_datetime_to_user_tz(issue_date_time)
#         tz_date_time = datetime.strptime(
#             tz_date_time_str, "%Y-%m-%d %H:%M:%S"
#         )
#         issue_date =tz_date_time.date()
#         issue_time = tz_date_time.time()
        
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
        
        res = {
            "id": name,
            "uuid": id_external,
            "issue_date": issue_date,
            "issue_time": issue_time,
            "order_type_code": "SHIPMENT",  #Neiasku ar tikrai, bet SHIPMENT siuntimas klientui. Dar gali buti purchase, bet cia gal tiekime bus
        }
        
        if delivery_tag_vals:
            res['delivery'] = delivery_tag_vals
        
        if company_partner_id:
            company_partner_vals = {"party": partner_env.get_partner_vals(company_partner_id)}
            if company_partner_vals:
                res['buyer_customer_party'] = company_partner_vals
                res['seller_supplier_party'] = company_partner_vals
                
        self._cr.execute('''
            SELECT
                id
            FROM
                stock_move    
            WHERE 
                picking_id = %s
            ORDER BY
                id
        ''', (self.id,))
        move_ids = [i[0] for i in self._cr.fetchall()]
        
        line_vals_list = []
        for move_id in move_ids:
            self._cr.execute("""
                SELECT
                    product_id, product_uom_qty,
                    price_unit, product_uom
                FROM
                    stock_move
                WHERE
                    id = %s
                LIMIT 1
            """ , (move_id,))
            product_id, qty, price_unit, uom_id = self._cr.fetchone()
            
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
            ''', (product_id,))
            prod_name, default_code = self._cr.fetchone()
            
            line_vals = {
                "id": str(move_id),
                "quantity": "%.3f" % (qty),
                "quantity_unit_code": uom,
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
                }
            }
            
            if price_unit:
                line_vals['price'] = {
                    'price_amount': price_unit,
                }
            
            line_vals_list.append({'line_item': line_vals})
        
        if line_vals_list:
            res['order_line'] = line_vals_list
        
        return res

    @api.multi
    def get_adjustment_vals(self):
        self.ensure_one()
        move_env = self.env['stock.move']
        own_env = self.env['product.owner']

        self._cr.execute("""
            SELECT
                name, date, create_date, despatch_id, id_external, owner_id
            FROM
                stock_picking
            WHERE
                id = %s
            LIMIT 1
        """ , (self.id,))
        picking_name, picking_date, create_date, despatch_id, id_external, owner_id = self._cr.fetchone()
        issue_date_time = picking_date or create_date
        issue_date, issue_time = self.get_issue_date_and_time(issue_date_time)

        res = {
            'ubl_extensions': {
                'ubl_extension': [
                    {
                        'extension_reason_code': "BLS_ADJUSTMENT",
                    }
                ]
            },
            'ubl_version_id': '2.1',
            'id': picking_name,
            'uuid': id_external,
            'issue_date': issue_date,
            'issue_time': issue_time,
            # 'note': '',
            ###########
            # 'despatch_supplier_party': '', # Neaišku kas turi būti
            # 'delivery_customer_party': '', # Neaišku kas turi būti
            # 'originator_customer_party': '',
            'adjustment_line': '',
        }
        res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {
            'settings': {}
        }

        self._cr.execute("""
            SELECT
                company_code
            FROM
                res_company
            WHERE
                id=1
            LIMIT 1
        """)
        comp_code, = self._cr.fetchone()
        if comp_code:
            res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {'settings': {'document_source_id': comp_code}}

        self._cr.execute("""
            SELECT
                CASE 
                    WHEN picking_to_warehouse_for_internal_order_id is not NULL THEN 'ADJUSTMENT_PLUS'
                    WHEN picking_from_warehouse_for_internal_order_id is not NULL THEN 'ADJUSTMENT_MINUS'
                END
            FROM
                stock_picking
            WHERE
                id =%s
            LIMIT 1
        """, (self.id,))
        adjustment_type, = self._cr.fetchone() or (False,)
        if adjustment_type:
            if 'extension_content' not in res['ubl_extensions']['ubl_extension'][0]:
                res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {'settings': {}}
            res['ubl_extensions']['ubl_extension'][0]['extension_content']['settings']['adjustment_type'] = adjustment_type

        self._cr.execute("""
            SELECT
                ior.name, ior.code
            FROM
                stock_picking sp
                JOIN internal_operation io on (
                    io.id = sp.picking_to_warehouse_for_internal_order_id 
                    OR io.id = sp.picking_from_warehouse_for_internal_order_id
                ) JOIN internal_operation_adjustment ioa on (io.id = ioa.operation_id)
                JOIN internal_operation_reason ior on (ior.id = ioa.reason_id)
            WHERE
                sp.id = %s
            LIMIT 1
        """, (self.id,))
        reason_name, reason_code = self._cr.fetchone() or (False, False)
        if reason_name:
            if 'extension_content' not in res['ubl_extensions']['ubl_extension'][0]:
                res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {'settings': {}}
            res['ubl_extensions']['ubl_extension'][0]['extension_content']['settings']['movement_reason'] = reason_name
        if reason_code:
            if 'extension_content' not in res['ubl_extensions']['ubl_extension'][0]:
                res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {'settings': {}}
            res['ubl_extensions']['ubl_extension'][0]['extension_content']['settings']['movement_reason_code'] = reason_code

        if owner_id:
            originator_party_vals = own_env.browse(owner_id).get_originator_party_vals()
            if originator_party_vals:
                res['originator_customer_party'] = originator_party_vals

        shipment_vals = self.get_shipment_vals_from_picking()
        if shipment_vals:
            res['shipment'] = shipment_vals

        adjustment_lines = []

        self._cr.execute("""
            SELECT
                id
            FROM
                stock_move 
            WHERE
                picking_id=%s
        """, (self.id,))
        move_ids = [move[0] for move in self.env.cr.fetchall()]

        for move_id in move_ids:
            adjustment_line = move_env.browse(move_id).get_adjustment_line_from_move()
            if adjustment_line:
                adjustment_lines.append(adjustment_line)

        if adjustment_lines:
            res['adjustment_line'] = adjustment_lines

        return res

    @api.multi
    def get_movement_vals(self):
        self.ensure_one()
        move_env = self.env['stock.move']
        own_env = self.env['product.owner']

        self._cr.execute("""
            SELECT
                name, date, create_date, despatch_id, id_external, owner_id
            FROM
                stock_picking
            WHERE
                id = %s
            LIMIT 1
        """, (self.id,))
        picking_name, picking_date, create_date, despatch_id, id_external, owner_id = self._cr.fetchone()
        issue_date_time = picking_date or create_date
        issue_date, issue_time = self.get_issue_date_and_time(issue_date_time)

        res = {
            'ubl_extensions': {
                'ubl_extension': [
                    {
                        'extension_reason_code': "BLS_MOVEMENT",
                    }
                ]
            },
            'ubl_version_id': "2.1",
            'id': picking_name,
            "uuid": id_external,
            "issue_date": issue_date,
            "issue_time": issue_time,
        }
        self._cr.execute("""
            SELECT
                so.name
            FROM
                stock_picking sp
                JOIN account_invoice ai on (ai.id = sp.invoice_id)
                JOIN sale_order so on (so.id=ai.automatically_created_sale_id)
            WHERE
                sp.id=%s
            LIMIT 1
        """, (self.id,))
        task_name_res = self._cr.fetchone()

        if task_name_res:
            task_name, = task_name_res
            self._cr.execute("""
                SELECT
                    company_code
                FROM
                    res_company
                WHERE
                    id=1
                LIMIT 1
            """)
            comp_code, = self._cr.fetchone()

            res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {
                'settings': {
                    'document_source_id': comp_code,
                    'bls_shipment_id': task_name,
                    # 'movement_reason': '',
                    # 'movement_reason_code': ''
                }

            }
        self._cr.execute("""
            SELECT
                id
            FROM
                stock_move 
            WHERE
                picking_id=%s
        """, (self.id,))
        move_ids = [move[0] for move in self.env.cr.fetchall()]

        move_desp_lines = []
        for move_id in move_ids:
            move_desp_line = move_env.browse(move_id).get_despatch_line_vals_from_move()
            if move_desp_line:
                move_desp_lines.append(move_desp_line)

        if owner_id:
            originator_party_vals = own_env.browse(owner_id).get_originator_party_vals()
            if originator_party_vals:
                res['originator_customer_party'] = originator_party_vals

        res['despatch_line'] = move_desp_lines
        shipment_vals = self.get_shipment_vals_from_picking()
        if shipment_vals:
            res['shipment'] = shipment_vals


        return res
    # originator_customer_party = fields.Nested(
    #     OriginatorCustomerPartySchema, ns=ns['cac'])

    @api.multi
    def get_delivery_vals_from_picking(self):
        loc_env = self.env['stock.location']
        self._cr.execute("""
            SELECT
                location_dest_id, date, location_id, operation_type
            FROM
                stock_picking
            WHERE
                id = %s
            LIMIT 1
        """ , (self.id,))
        location_dest_id, date, location_id, operation_type = self._cr.fetchone()
        delivery_location = {}
        despatch_location = {}
        if operation_type == 'adjustment':

            self._cr.execute("""
                SELECT
                    CASE 
                        WHEN picking_to_warehouse_for_internal_order_id is not NULL THEN 'ADJUSTMENT_PLUS'
                        WHEN picking_from_warehouse_for_internal_order_id is not NULL THEN 'ADJUSTMENT_MINUS'
                    END
                FROM
                    stock_picking
                WHERE
                    id=%s
                LIMIT 1
            """ , (self.id,))
            adjustment_type, = self._cr.fetchone() or (False,)
            if adjustment_type == 'ADJUSTMENT_PLUS':
                delivery_location = loc_env.browse(location_dest_id).get_delivery_location_vals()
                despatch_location = delivery_location.copy()
            elif adjustment_type == 'ADJUSTMENT_MINUS':
                delivery_location = loc_env.browse(location_id).get_delivery_location_vals()
                despatch_location = delivery_location.copy()
        else:
            delivery_location = loc_env.browse(location_dest_id).get_delivery_location_vals()
            despatch_location = loc_env.browse(location_id).get_delivery_location_vals()
        actual_delivery_date, actual_delivery_time = self.get_issue_date_and_time(date)

        delivery = {
            'delivery_location': delivery_location,
            # 'alternative_delivery_location': '',
            # 'promised_delivery_period': '',
            # 'estimated_delivery_period': '',
            'actual_delivery_date': actual_delivery_date,
            'actual_delivery_time': actual_delivery_time,
            # 'carrier_party': '',
            'despatch': {'despatch_location': despatch_location},
        }

        carrier = self.get_carrier()
        if carrier:
            delivery['carrier_party'] = carrier.get_partner_vals()

        return delivery

    @api.multi
    def get_carrier(self):
        return False

    @api.multi
    def get_shipment_vals_from_picking(self):

        shipment = {
            'id': '1',
            'delivery': self.get_delivery_vals_from_picking(),
            # 'consignment': '', # Neaišku iš kur konteinerius gauti
            # 'goods_item': '',
            # 'transport_handling_unit': '', #Reikia transporto
        }
        return shipment



    @api.multi
    def get_receipt_confirmation_vals(self):
        self.ensure_one()
        partner_env = self.env['res.partner']
        despatch_env = self.env['despatch.advice']
        
#         user = self.env.user
        
        self._cr.execute("""
            SELECT
                name, date, create_date, despatch_id, id_external
            FROM
                stock_picking
            WHERE
                id = %s
            LIMIT 1
        """ , (self.id,))
        picking_name, picking_date, create_date, despatch_id, id_external = self._cr.fetchone()
        
        issue_date_time = picking_date or create_date
        issue_date, issue_time = self.get_issue_date_and_time(issue_date_time)
        

        res = {
            'ubl_extensions': {
                'ubl_extension': [
                    {
                        'extension_reason_code': "BLS_RECEIPT_CONFIRMATION",
                    }
                ]
            },
            'ubl_version_id': "1.2",
            'id': picking_name,
            "uuid": id_external,
            "issue_date": issue_date,
            "issue_time": issue_time,
        }
        
        if despatch_id:
            self._cr.execute('''
                SELECT
                    buyer_id, seller_id, id_source_doc, name
                FROM
                    despatch_advice
                WHERE id = %s
                LIMIT 1
            ''', (despatch_id,))
            buyer_id, seller_id, id_source_doc, despatch_name = self._cr.fetchone()
            
            res['ubl_extensions']['ubl_extension'][0]['extension_content'] = {
                'settings': {
                    'document_source_id': id_source_doc,
                    'sender_document_type': "DESPATCHADVICE",
                    'sender_document_id': despatch_name,
                }
            }
            
            if buyer_id:
                buyer_vals = {"party": partner_env.get_partner_vals(buyer_id)}
                res['buyer_customer_party'] = buyer_vals
                
            if seller_id:     
                seller_vals = {"party": partner_env.get_partner_vals(seller_id)}
                res['seller_supplier_party'] = seller_vals
                
            despatch = despatch_env.browse(despatch_id)
            delivery_vals = despatch.get_delivery_vals()
            if delivery_vals:
                res['delivery'] = delivery_vals
                
        res['legal_monetary_total'] = {'payable_amount': 0.0}
        
        self._cr.execute('''
            SELECT
                id
            FROM
                stock_move    
            WHERE 
                picking_id = %s
            ORDER BY
                id
        ''', (self.id,))
        move_ids = [i[0] for i in self._cr.fetchall()]
        
        line_vals_list = []
        for move_id in move_ids:
            self._cr.execute("""
                SELECT
                    product_id, product_uom_qty,
                    price_unit, product_uom, container_line_id
                FROM
                    stock_move
                WHERE
                    id = %s
                LIMIT 1
            """ , (move_id,))
            product_id, qty, price_unit, uom_id, container_line_id = self._cr.fetchone()
            
            if not container_line_id:
                return {}
                            
            self._cr.execute('''
                SELECT
                    id_despatch_line, despatch_advice_id, id_order, order_name, id_order_line
                FROM
                    account_invoice_container_line
                WHERE 
                    id = %s
                LIMIT 1
            ''', (container_line_id,))
            id_despatch_line, despatch_advice_id, id_order, order_name, id_order_line = self._cr.fetchone()
            
            self._cr.execute('''
                SELECT
                    name, id_external
                FROM
                    despatch_advice
                WHERE 
                    id = %s
                LIMIT 1
            ''', (despatch_advice_id,))
            despatch_name, id_despatch = self._cr.fetchone()
            
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
            ''', (product_id,))
            prod_name, default_code = self._cr.fetchone()
            
            line_vals = {
                "id": str(move_id),
                "received_quantity": "%.3f" % (qty),
                "received_quantity_unit_code": uom,
                "order_line_reference": {
                    'line_id': id_order_line,
                    'order_reference': {
                        'id': order_name,
#                         'uuid': id_order,
                    }
                },
                 "despatch_line_reference": {
                    'line_id': id_despatch_line,
                    'document_reference': {
                        'id': despatch_name,
#                         'uuid': id_despatch,
                    }
                },
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
                "shipment": {
                    'id': 1
                }
            }
            
            if price_unit:
                line_vals['price'] = {
                    'price_amount': price_unit,
                }
                
                
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
                        cert_issue_date = datetime.strptime(
                            cert_issue_date, "%Y-%m-%d"
                        ).date()
                        cert_vals["document_reference"]["issue_date"] = cert_issue_date
                    if cert_valid_from and cert_valid_to:
                        cert_vals["document_reference"]["validity_period"] = {
                            "start_date": datetime.strptime(
                                cert_valid_from, "%Y-%m-%d"
                            ).date(),
                            "end_date": datetime.strptime(
                                cert_valid_to, "%Y-%m-%d"
                            ).date(),
                        }                      
                certificates.append(cert_vals)
                 
            if certificates:
                line_vals["item"]["certificate"] = certificates
                
                
                
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
                
            if lot_id:
                self._cr.execute('''
                    SELECT
                        name, expiry_date
                    FROM
                        stock_production_lot
                    WHERE id = %s
                    LIMIT 1
                ''', (lot_id,))
                lot_cert_name, lot_expiry_date = self._cr.fetchone()
                 
                line_vals["item"]["item_instance"] = {
                    "lot_identification": {
                        'lot_number_id': lot_cert_name,
                    }
                }
                if lot_expiry_date:
                    line_vals["item"]["item_instance"]['lot_identification']['expiry_date'] = datetime.strptime(
                        lot_expiry_date, "%Y-%m-%d"
                    )    
                
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
                
                line_vals['shipment']['consignment'] = [{
                    'id': container_no,
                    'consignment_quantity': line_qty,
                }]
                
            
            line_vals_list.append(line_vals)
        
        if line_vals_list:
            res['receipt_confirmation_line'] = line_vals_list
            
        return res
    
    @api.multi
    def get_transportation_order_ubl(self, pretty=False):
        self.ensure_one()
        transportation_order_vals = self.get_transportation_order_vals()
        if not transportation_order_vals:
            return False

        data_xml = order_schema.dumps(
            transportation_order_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )
 
        return data_xml
    
    @api.multi
    def get_bls_receipt_confirmation_ubl(self, pretty=False):
        self.ensure_one()
        receipt_confirmation_vals = self.get_receipt_confirmation_vals()
        if not receipt_confirmation_vals:
            return False

        data_xml = bls_receipt_confirmation_schema.dumps(
            receipt_confirmation_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )
 
        return data_xml

    @api.multi
    def get_movement_ubl(self, pretty=False):
        self.ensure_one()
        movement_vals = self.get_movement_vals()
        if not movement_vals:
            return False

        data_xml = bls_movement_schema.dumps(
            movement_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )

        return data_xml

    @api.multi
    def get_adjustment_ubl(self, pretty=False):
        self.ensure_one()
        adjustment_vals = self.get_adjustment_vals()
        if not adjustment_vals:
            return False

        data_xml = bls_adjustment_schema.dumps(
            adjustment_vals, content_type='application/xml', encoding='utf8', method='xml',
            xml_declaration=True, pretty_print=pretty
        )

        return data_xml


#     @api.multi
#     def action_reserve(self):
#         for picking in self:
#             picking.move_lines.action_reserve()
#             picking.write({'state': 'reserved'})
#         return True
 
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def get_state_selection(self):
        return [
            ('draft', _('New')),
            ('cancel', _('Cancelled')),
#             ('waiting', 'Waiting Another Move'),
#             ('confirmed', 'Waiting Availability'),
#             ('partially_available', 'Partially Available'),
#             ('assigned', 'Available'),
            ('reserved', _('Reserved')),
            ('done', _('Done'))
        ]
    
    state = fields.Selection(
        get_state_selection, string='Status',
        default='draft', readonly=True
    )
    container_line_id = fields.Many2one('account.invoice.container.line', "Container Line")

    @api.multi
    def get_adjustment_line_from_move(self, counter=None):
        if counter is None:
            counter = self.id
        self._cr.execute('''
             SELECT
                 sm.product_uom_qty, sm.product_id, pu.name
             FROM
                 stock_move sm,
                 product_uom pu
             WHERE 
                sm.id = %s
                AND pu.id = sm.product_uom                
             LIMIT 1
         ''', (self.id,))
        product_uom_qty, product_id, uom_name = self._cr.fetchone()
        adjustment_line = {
            'id': str(counter),
            'adjustment': product_uom_qty,
            'adjustment_unit_code': uom_name,
            'shipment': '', # ar tikrai reikia jeigu prie pačio adjustmento jau shipmentas yra paduodamas
        }
        if product_id:
            item_vals = self.env['product.product'].browse(product_id).get_item_vals()
            if item_vals:
                adjustment_line['item'] = item_vals
        return adjustment_line

    @api.multi
    def get_despatch_line_vals_from_move(self):

        self._cr.execute('''
             SELECT
                 product_uom_qty, product_id, product_uom
             FROM
                 stock_move
             WHERE 
                id = %s
             LIMIT 1
         ''', (self.id,))
        product_uom_qty, product_id, uom_id = self._cr.fetchone()

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
            uom = ''

        # self._cr.execute('''
        #     SELECT
        #         pt.name, pp.default_code, pb.barcode
        #     FROM
        #         product_product AS pp
        #     JOIN product_template AS pt ON (
        #         pp.product_tmpl_id = pt.id
        #     )
        #     LEFT JOIN product_barcode pb on (pb.product_id=pp.id)
        #     WHERE pp.id = %s
        #     LIMIT 1
        # ''', (product_id,))
        # prod_name, default_code, barcode_str = self._cr.fetchone()

        line_vals = {
            "id": str(self.id),
            "delivered_quantity": product_uom_qty,
            # "item": {
            #     "description": prod_name,
            #     "additional_item_identification": [
            #         {
            #             "id": default_code,
            #             "scheme_id": "PRODUCT_CODE",
            #             "scheme_name": "Product code",
            #             "scheme_agency_id": "BLS"
            #         }
            #     ]
            # },
            "quantity_unit_code": uom,
        }
        if product_id:
            item_vals = self.env['product.product'].browse(product_id).get_item_vals()
            if item_vals:
                line_vals['item'] = item_vals

        # if barcode_str:
        #     line_vals["item"]["additional_item_identification"][0]["barcode_symbology_id"] = barcode_str

        return line_vals



#     @api.multi
#     def reserve_qty(self):
#         loc_stock_obj = self.env['sanitex.product.location.stock']
#         for move in self:
#             if move.location_id and move.product_id:
#                 quantity = move.product_uom_qty
#                 loc_id = move.location_id.id
#                 product_id = move.product_id.id
#                 uom_id = move.product_uom.id
#                 
#                 loc_stock_obj.reserve_qty(loc_id, product_id, quantity, uom_id)
#     
#     @api.multi
#     def action_reserve(self):
#         for move in self:
#             move.reserve_qty()
#             move.write({'state': 'reserved'})
#             
#         return True
           
class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    asn_location = fields.Boolean("ASN Location", default=False)
    
    
#     @api.multi
#     def get_partner_party_vals(self):
#         self.ensureone()
#         
#         res = {
#             
#         }
#         
#         return res

    @api.multi
    def get_delivery_location_vals(self):
        res = {}

        self._cr.execute('''
            SELECT
                load_address, name
            FROM
                stock_location
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        load_address, name = self._cr.fetchone()

        wh_id = False
        lot_stock_id = self.id
        wh_name = ''
        while not wh_id:
            self._cr.execute('''
                SELECT
                    id, name
                FROM
                    stock_warehouse
                WHERE 
                    lot_stock_id = %s
                LIMIT 1
            ''', (lot_stock_id,))
            wh_id, wh_name = self._cr.fetchone() or (False, False)
            if not wh_id:
                self._cr.execute('''
                    SELECT
                        location_id
                    FROM
                        stock_location
                    WHERE 
                        id = %s
                    LIMIT 1
                ''', (lot_stock_id,))
                lot_stock_id, = self._cr.fetchone()
                if not lot_stock_id:
                    break

        if wh_name:
            res['name'] = wh_name
        elif name:
            res['name'] = name

        res["address"] = {
            "address_line": [
                {
                    "line": load_address
                }
            ],
        }

        res['subsidiary_location'] = {
            'name': name
        }
        return res

    
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    asn_location_id = fields.Many2one(
        'stock.location', "ASN Location", domain="[('asn_location','=',True)]"
    )
    
class StockRouteTemplate(models.Model):
    _inherit = 'stock.route.template'
    
    fully_received_lines = fields.Char(
        "Fully Received Lines", readonly=True, default = "0 / 0",
        compute='calc_fully_received_lines'
    )
    documents_counter_status = fields.Char(
        "Documents", readonly=True, default = "0 / 0",
        compute='calc_documents_counter_status'
    )
    
    @api.multi
    def do_invoice(self, allow_splitting=False):
        sale_order_env = self.env['sale.order']
        
#         warehouse_id = self.env.user.get_default_warehouse()
#         if not warehouse_id:
#             raise UserError(
#                 _('Please select warehouse you are working in')
#             )

        warehouses = self.env.user.get_current_warehouses()
        warehouse_ids = warehouses.ids
        
        if not warehouse_ids:
            raise UserError(
                _('Please select warehouse you are working in.')
            )
        
        sale_orders = sale_order_env.search([
            ('route_template_id','in',self.ids),
            ('state','in',['need_invoice', 'being_collected']),
            ('warehouse_id','in',warehouse_ids),
            ('previous_task_received','=',True)
        ])
        
        if not sale_orders:
            do_invoice_result_wiz_env = self.env['do.invoice.result.wizard']
            do_invoice_result_wiz = do_invoice_result_wiz_env.create({
                'msg': _("There are not any transportation tasks, which can be invoiced, in the selected routes.")
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
            }

        
        return sale_orders.do_invoice(allow_splitting=allow_splitting)
    
#     @api.depends('task_ids')
    @api.multi
    def calc_fully_received_lines(self):
#         warehouse_id = self.env.user.get_default_warehouse()
        warehouses = self.env.user.get_current_warehouses()
        warehouse_ids = warehouses.ids
        if warehouse_ids:
            for route_template in self:
    #             route_template.fully_received_lines = "-"
    #             total_tasks = 0
                fully_picked_tasks = 0
#                 if not warehouse_id:
#                     raise UserError(
#                         _('Please select warehouse you are working in')
#                     )
                  
                self._cr.execute('''
                    SELECT
                        state, order_package_type, has_related_document
                    FROM
                        sale_order
                    WHERE route_template_id = %s
                        AND warehouse_id in %s
                        AND previous_task_received = true
                ''', (route_template.id, tuple(warehouse_ids)))
                sql_res = self._cr.fetchall()
                if sql_res:
                    total_tasks = len(sql_res)
                    for state, order_package_type, has_related_document in sql_res:
                        if state == 'need_invoice' or order_package_type == 'package' or has_related_document == True:
                            fully_picked_tasks += 1
                      
                    route_template.fully_received_lines = "%s / %s" % (fully_picked_tasks, total_tasks)
                else:
                    route_template.fully_received_lines = "-"
        else:
            for route_template in self:
                route_template.fully_received_lines = "?"
     
     
    @api.multi
    def calc_documents_counter_status(self):
        warehouses = self.env.user.get_current_warehouses()
        warehouse_ids = warehouses.ids
        if warehouse_ids:
            for route_template in self:

                route_template.documents_counter_status = "-"
                  
                self._cr.execute('''
                    SELECT
                        id
                    FROM
                        sale_order
                    WHERE route_template_id = %s
                        AND warehouse_id in %s
                        AND previous_task_received = true
                        AND linked_with_despatch = true
                ''', (route_template.id, tuple(warehouse_ids)))
                sale_ids = set([i[0] for i in self._cr.fetchall()])
                
#                 print ("\n\n Sale IDS susiradau per: %.5f" % (time.time() - t2))
                if sale_ids:
                    self._cr.execute('''
                        SELECT
                            distinct(islr.invoice_id)
                        FROM
                            invoice_so_line_rel AS islr
                        JOIN
                            sale_order_line AS sol ON (
                                sol.id = islr.order_line_id
                            )
                        WHERE sol.order_id in %s
                    ''', (tuple(sale_ids), ))
                    sql_res = self._cr.fetchall()
                    invoiced_docs = len(sql_res) or 0
                    
                    total_docs = invoiced_docs

#                     self._cr.execute('''
#                         SELECT
#                             tol.invoice_group_index, tol.waybill_group_index
#                         FROM
#                             transportation_order_line AS tol
#                         JOIN 
#                             account_invoice_container_line AS aicl ON (
#                                 aicl.order_line_id = tol.id
#                             )
#                         JOIN
#                             sale_order_line AS sol ON (
#                                 aicl.sale_order_line_id = sol.id
#                             )
#                         LEFT JOIN
#                             invoice_so_line_rel AS islr ON (
#                                 sol.id = islr.order_line_id
#                             )
#                         WHERE
#                             sol.order_id in %s
#                         AND
#                             islr.order_line_id IS NULL
#                         GROUP  BY
#                             tol.invoice_group_index, tol.waybill_group_index
#                     ''', (tuple(sale_ids),))

                    self._cr.execute('''
                        SELECT
                            invoice_group_index, waybill_group_index
                        FROM
                            sale_order_line
                        WHERE
                            order_id in %s
                        GROUP  BY
                            invoice_group_index, waybill_group_index
                    ''', (tuple(sale_ids),))

                    sql_res = self._cr.fetchall()

                    add_one = False
                    used_inv_indexes = []
                    used_wb_indexes = []
                    
                    for invoice_group_index, waybill_group_index in sql_res:
                        if invoice_group_index or waybill_group_index:
#                             total_docs += (invoice_group_index and (invoice_group_index != '-') and 1 or 0)\
#                                 + (waybill_group_index and (waybill_group_index != '-') and 1 or 0)
                            if invoice_group_index and invoice_group_index not in used_inv_indexes:
                                used_inv_indexes.append(invoice_group_index)
                                total_docs += 1
                            if waybill_group_index and waybill_group_index not in used_wb_indexes:
                                used_wb_indexes.append(waybill_group_index)
                                total_docs += 1
                        elif not add_one:
                            add_one = True
                    if add_one:
                        total_docs += 1
                        
                    route_template.documents_counter_status = "%s / %s" % (invoiced_docs, total_docs)   

        else:
            for route_template in self:
                route_template.documents_counter_status = "?"
            
#     @api.multi
#     def calc_documents_counter_status(self):
# #         warehouse_id = self.env.user.get_default_warehouse()
#         warehouses = self.env.user.get_current_warehouses()
#         warehouse_ids = warehouses.ids
#         if warehouse_ids:
#             
#             for route_template in self:
#                 route_template.documents_counter_status = "-"
#                 total_docs = 0
#                 invoiced_docs = 0
#                  
#                 self._cr.execute('''
#                     SELECT
#                         id
#                     FROM
#                         sale_order
#                     WHERE route_template_id = %s
#                         AND warehouse_id in %s
#                         AND previous_task_received = true
#                         AND linked_with_despatch = true
#                 ''', (route_template.id, tuple(warehouse_ids)))
#                 sale_ids = set([i[0] for i in self._cr.fetchall()])
#      
#                 doc_nos = set()
#                 used_sale_ids = set()
#                 
#                 used_invoice_indexes = []
#                 used_waybill_indexes = []
#                 
#                 if sale_ids:
#                     self._cr.execute('''
#                         SELECT
#                             tod.document_no, sol.order_id
#                         FROM
#                             transportation_order_document AS tod
#                         JOIN transportation_order AS transo ON (
#                             tod.transportation_order_id = transo.id
#                         )
#                         JOIN account_invoice_container_line AS aicl ON (
#                             aicl.order_id = transo.id
#                         )
#                         JOIN sale_order_line AS sol ON (
#                             aicl.sale_order_line_id = sol.id
#                         )
#                         WHERE sol.order_id in %s
#                             AND tod.document_no is not null
#                             AND tod.document_no <> ''
#                     ''', (tuple(sale_ids),))
#                     sql_res = self._cr.fetchall()
#                      
#                     for doc_no, sale_id in sql_res:
#                         doc_nos.add(doc_no)
#                         used_sale_ids.add(sale_id)
#                     
#                     total_docs += len(doc_nos)
#                     
#                     if doc_nos:
#                         self._cr.execute('''
#                             SELECT
#                                 distinct(id)
#                             FROM
#                                 account_invoice
#                             WHERE name in %s
#                                 AND generated_in_atlas = true
#                         ''', (tuple(doc_nos),))
#                         invoiced_docs += len(self._cr.fetchall())
#                      
#                     sale_ids -= used_sale_ids
#                      
#                     if sale_ids:
#                         self._cr.execute('''
#                             SELECT
#                                 tol.invoice_group_index, tol.waybill_group_index
#                             FROM
#                                 transportation_order_line AS tol
#                             JOIN account_invoice_container_line AS aicl ON (
#                                 aicl.order_line_id = tol.id
#                             )
#                             JOIN sale_order_line AS sol ON (
#                                 aicl.sale_order_line_id = sol.id
#                             )
#                             WHERE sol.order_id in %s
#                         ''', (tuple(sale_ids),))
#                         sql_res = self._cr.fetchall()
#                         
#                         for invoice_group_index, waybill_group_index in sql_res:
#                             if invoice_group_index and invoice_group_index != '-'\
#                                 and invoice_group_index not in used_invoice_indexes\
#                             :
#                                 used_invoice_indexes.append(invoice_group_index)
#                                 self._cr.execute('''
#                                     SELECT
#                                         distinct(id)
#                                     FROM
#                                         account_invoice
#                                     WHERE merge_code = %s
#                                 ''', (invoice_group_index,))
#                                 no_of_docs = len(self._cr.fetchall())
#     #                             if not no_of_docs > 1:
#     #                                 total_docs += 1
#     #                                 if no_of_docs:
#     #                                     invoiced_docs += 1
#     #                             else:
#     #                                 total_docs += no_of_docs
#     #                                 invoiced_docs += no_of_docs
#                                 
#                                 total_docs += no_of_docs
#                                 invoiced_docs += no_of_docs
#                                      
#                                 self._cr.execute('''
#                                     SELECT
#                                         sol.id
#                                     FROM
#                                         sale_order_line as sol
#                                     JOIN sale_order as saleo ON (
#                                         sol.order_id = saleo.id
#                                     )    
#                                     JOIN account_invoice_container_line as cl ON (
#                                         cl.sale_order_line_id = sol.id
#                                     )
#                                       
#                                     JOIN transportation_order_line as tol ON (
#                                         cl.order_line_id = tol.id
#                                     )    
#                                     WHERE sol.product_uom_qty > sol.qty_invoiced
#                                     AND tol.invoice_group_index = %s 
#                                     LIMIT 1
#                                 ''', (invoice_group_index,))
#                                 if self._cr.fetchone():
#                                     total_docs += 1
#          
#                             if waybill_group_index and waybill_group_index != '-'\
#                                 and waybill_group_index not in used_waybill_indexes\
#                             :
#                                 used_waybill_indexes.append(waybill_group_index)
#                                 self._cr.execute('''
#                                     SELECT
#                                         distinct(id)
#                                     FROM
#                                         account_invoice
#                                     WHERE merge_code = %s
#                                 ''', (waybill_group_index,))
#                                 no_of_docs = len(self._cr.fetchall())
#     #                             if not no_of_docs > 1:
#     #                                 total_docs += 1
#     #                                 if no_of_docs:
#     #                                     invoiced_docs += 1
#     #                             else:
#     #                                 total_docs += no_of_docs
#     #                                 invoiced_docs += no_of_docs
#                                 total_docs += no_of_docs
#                                 invoiced_docs += no_of_docs
#                                      
#                                 self._cr.execute('''
#                                     SELECT
#                                         sol.id
#                                     FROM
#                                         sale_order_line as sol
#                                     JOIN sale_order as saleo ON (
#                                         sol.order_id = saleo.id
#                                     )    
#                                     JOIN account_invoice_container_line as cl ON (
#                                         cl.sale_order_line_id = sol.id
#                                     )
#                                       
#                                     JOIN transportation_order_line as tol ON (
#                                         cl.order_line_id = tol.id
#                                     )    
#                                     WHERE sol.product_uom_qty > sol.qty_invoiced
#                                     AND tol.waybill_group_index = %s 
#                                     LIMIT 1
#                                 ''', (waybill_group_index,))
#                                 if self._cr.fetchone():
#                                     total_docs += 1
#     
#                     route_template.documents_counter_status = "%s / %s" % (invoiced_docs, total_docs)
#                 else:
#                     route_template.documents_counter_status = "-"
#         else:
#             for route_template in self:
#                 route_template.documents_counter_status = "?"
                
                
class StockRoute(models.Model):
    _inherit = 'stock.route'

    @api.multi
    def action_call_cmr_wizard(self):
        document_ids = []
        for route in self:
            document_ids += route.get_document_ids()
        if document_ids:
            document_ids = list(set(document_ids))
            foreign_document_ids = self.env['account.invoice'].browse(document_ids).get_documents_to_other_coutries()
            if foreign_document_ids:
                wizard = self.env['stock.route.create.cmr.osv'].create({
                    'document_ids': [(6, 0, foreign_document_ids.ids)]
                })
                return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.route.create.cmr.osv',
                    'target': 'new',
                    'res_id': wizard.id,
                    'type': 'ir.actions.act_window',
                    'context': self.env.context or {},
                    'nodestroy': True,
                }
            else:
                raise UserError(_('Selected routes(%s) doesn\'t have any documents for foreign customers.') % str(self.mapped('name')))
        else:
            raise UserError(_('Selected routes(%s) doesn\'t have any documents.') % str(self.mapped('name')))

    @api.multi
    def action_release(self):
        sale_env = self.env['sale.order']
        res = super(StockRoute, self.with_context(no_commit=True)).action_release()
        for route in self:
#             self._cr.execute('''
#                 SELECT
#                     id
#                 FROM
#                     sale_order
#                 WHERE
#                     route_id = %s
#             ''', (route.id,))
#             sale_ids = [i[0] for i in self._cr.fetchall()]
#             sales = sale_env.browse(sale_ids)
#             sales.do_out_despatch()

            self._cr.execute('''
                SELECT
                    id
                FROM
                    sale_order
                WHERE
                    route_id = %s
                AND
                    internal_movement_id IS NOT NULL
            ''', (route.id,))
            sale_ids = [i[0] for i in self._cr.fetchall()]
            if sale_ids:
                sales = sale_env.browse(sale_ids)
                sales.do_out_movement_despatch()
        return res