# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo import http, registry, SUPERUSER_ID, api, tools
from odoo.http import request, Response
from odoo.tools import config
# from odoo.tools import ustr
import traceback
# from json import dumps
# import traceback
import logging
import json

_logger = logging.getLogger(__name__)

MAIN_DATABASE = 'bls'


class RestAPIIntegration(http.Controller):

    @http.route('/api/bls_despatch_advice', type='http', auth='none', methods=['POST'], csrf=False)
    def post_bls_despatch_advice_data(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        db_registry = registry(db)

        xml_req = request.httprequest.stream.read()

        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['stock.route.integration.intermediate'].create_bls_despatch_intermediate(xml_req)

        return ""
    
    @http.route('/api/despatch_advice', type='http', auth='none', methods=['POST'], csrf=False)
    def post_despatch_advice_data(self, **post):
        db = config.get('db_name', MAIN_DATABASE)   
        db_registry = registry(db)

        xml_req = request.httprequest.stream.read()
        
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['stock.route.integration.intermediate'].create_despatch_intermediate(xml_req)
        
        return ""
    
    @http.route('/api/transportation_order', type='http', auth='none', methods=['POST'], csrf=False)
    def post_transportation_order_data(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        db_registry = registry(db)

        xml_req = request.httprequest.stream.read()
        
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['stock.route.integration.intermediate'].create_transportation_order_intermediate(xml_req)
        
        return ""
    
    @http.route('/api/atlas/<ubl_doc>/<id_version>', type='http', auth='none', methods=['GET'], csrf=False)
    def return_ubl_documents(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        ubls = {}
        error = False
        try:
            db_registry = registry(db)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                ubl_doc = post.get('ubl_doc', False)
                id_version =  post.get('id_version', False)
                
                ubls = env['stock.route.integration.intermediate'].get_ubl_documents_json_vals(id_version, ubl_doc)
                
                if ubls == "Error":
                    error = True
                
        except Exception as e:
            err_note = '/api/atlas/<ubl_doc>/<id_version> with parameters %s. ERROR: %s' %(str(post), tools.ustr(e))
            trb = '\n\n' + traceback.format_exc() + '\n\n'
            _logger.info(err_note + trb)
            error = True
        
#         print ("\n\n__DICT__: ", request.__dict__)
        
        json_header = {'Content-Type': 'application/json', 'Accept': 'text/plain'}
        
        if error:
            return Response(status=400, headers=json_header)

        return request.make_response(json.dumps(ubls), headers=json_header)

    @http.route('/api/atlas/<despatch_type>/<identificator>=<id>', type='http', auth='none', methods=['GET'], csrf=False)
    def return_one_despatch(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        error = False
        
        status_code = 400
        res_xml = False
        try:
            db_registry = registry(db)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                despatch_type = post.get('despatch_type', False)
                identificator = post.get('identificator', False)
                id_value = post.get('id', False)
                
                res_xml = env['despatch.advice'].get_one_despatch(despatch_type, identificator, id_value)
                
                if res_xml == "Error":
                    error = True
                elif res_xml == "404":
                    error = True
                    status_code = 404
                
        except Exception as e:
            err_note = '/api/atlas/<despatch_type>/<identificator>=<id> with parameters %s. ERROR: %s' %(str(post), tools.ustr(e))
            trb = '\n\n' + traceback.format_exc() + '\n\n'
            _logger.info(err_note + trb)
            error = True
        
#         print ("\n\n__DICT__: ", request.__dict__)
        
        xml_header = {'Content-Type': 'application/xml', 'Accept': 'text/plain'}
        
        if error:
            return Response(status=status_code, headers=xml_header)

        return request.make_response(res_xml, headers=xml_header)
