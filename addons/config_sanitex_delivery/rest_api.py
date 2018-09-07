# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo import http, registry, SUPERUSER_ID, api
from odoo.http import request, Response
from odoo import tools
from odoo.tools import config
from odoo.tools import ustr

from json import dumps
import traceback
import logging
import json

_logger = logging.getLogger(__name__)

MAIN_DATABASE = 'bls'


class RestAPIIntegration(http.Controller):

    @http.route('/driver_debt/<driver_name>', type='http', auth='none', methods=['GET'], csrf=False)
    def return_driver_debt(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        debt = {}
        try:
            db_registry = registry(db)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                debt = env['stock.location'].get_driver_debt_for_rest_api(post.get('driver_name', False))
        except Exception as e:
            err_note = 'Failed /driver_debt/<driver_name> with parameters %s. ERROR: %s' %(str(post), tools.ustr(e))
            trb = '\n\n' + traceback.format_exc() + '\n\n'
            _logger.info(err_note + trb)
        if debt.get('code', False):
            body=json.dumps({'error': {'message': debt['message']}}, default=ustr)
            status = debt['code'] == 'not_found' and 404 or 500
            return Response(
                body, status=status, headers=[('Content-Type', 'application/json'),('Content-Length', len(body))]
            )

        return request.make_response(dumps(debt))

    @http.route('/routes/<version_id>', type='http', auth='none', methods=['GET'], csrf=False)
    def return_routes(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        routes = []
        try:
            db_registry = registry(db)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                routes = env['stock.route'].get_route_information_by_version(post.get('version_id', False))
        except Exception as e:
            err_note = 'Failed /routes/<version_id> with parameters %s. ERROR: %s' %(str(post), tools.ustr(e))
            trb = '\n\n' + traceback.format_exc() + '\n\n'
            _logger.info(err_note + trb)

        return request.make_response(dumps(routes))
    
    @http.route('/pod_integration/<integration_obj>/<id_version>', type='http', auth='none', methods=['GET'], csrf=False)
    def return_pod_objs(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        objs = []
        try:
            db_registry = registry(db)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
#                 obj_env = env['pod.integration'].get_env_by_obj(post.get('integration_obj', False))
#                 objs = obj_env.get_obj_information_by_version(post.get('id_version', False))
                objs = env['pod.integration'].get_obj_information_by_version(post.get('integration_obj', False), post.get('id_version', False))
        except Exception as e:
            err_note = 'Failed /pod_integration/<integration_obj>/<version_id> with parameters %s. ERROR: %s' %(str(post), tools.ustr(e))
            trb = '\n\n' + traceback.format_exc() + '\n\n'
            _logger.info(err_note + trb)

        return request.make_response(dumps(objs))
    
    @http.route('/test_connection', type='http', auth='none', methods=['GET'], csrf=False)
    def test_connection(self, **post):
        return "Connection is <b>OK</b>"
    
    
    @http.route('/pod_raml', type='http', auth='none', methods=['GET'], csrf=False)
    def return_pod_raml(self, **post):
        db = config.get('db_name', MAIN_DATABASE)   
        db_registry = registry(db)
        example_text = ""
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            
            all_obj_examples = env['pod.integration'].get_examples()
            for example in all_obj_examples:
                obj = list(example.keys())[0]
                example_text_part = """
  /%s
    /{id_version}:
      get:
        response:
          200:
            body:
              aplication/json:
                example:<div style="display:block;margin-left:10em;">%s</div>""" % (obj, str(dumps(example, indent=2)).encode('utf-8').decode('unicode-escape'))
                example_text += example_text_part
                
        res = """<pre>#%%RAML 1.0
title: POD data from ATLAS
baseUri: 192.168.52.172:11069
version: v1

/pod_integration:%s</pre>""" % (example_text)
        
        return res

    @http.route('/status', type='http', auth='none', methods=['GET'], csrf=False)
    def return_status(self):
        result = {'status': 'ok', 'version': '1.0.0', 'data': {}}
        return request.make_response(dumps(result))
    
    @http.route('/iceberg_integration/post_data/<obj>', type='json', auth='none', methods=['POST'], csrf=False)
    def post_iceberg_integration_data(self, **post):
        db = config.get('db_name', MAIN_DATABASE)   
        db_registry = registry(db)
        json_req = request.jsonrequest
        json_req.update(post)
        
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['iceberg.integration'].set_data(json_req)
        return ""
    
    
    @http.route('/iceberg/post/raml', type='http', auth='none', methods=['GET'], csrf=False)
    def return_iceberg_post_raml(self, **post):
        return  """<pre>#%%RAML 1.0
title: Iceberg data to ATLAS
baseUri: 192.168.52.172:11069
version: v1

/iceberg_integration
  /post_data
    /truck:
      post:
        description:
          Fūros (jei nepatogu naudoti "fleet")     
        queryParameters:
          truckId:
            description: "Unikalus fūros ID, kuris bus naudojamas susiejimams su kitais objektais ir naujinimams"
            required: true
            type: string
            example: "truck123123"
          deleted:
            description: "Ar įrašas ištrintas. Atlas sistemoje toks įrašas bus nustatytas į neaktyvų, kad nesimatytų"
            required: false
            type: boolean
            example: false
            default: false
          active:
            description: "Įrašo aktyvumas. Neaktyvūs įrašai nematomi naudotojams"
            required: false
            type: boolean
            example: false
            default: false
          carrierId:
            description: "Unikalus vežėjo ID, per kurį susiejamas su kitais objektais"
            required: false
            type: string
            example: "47"
          capacity:
            description: "Talpa"
            required: false
            type: integer
            example: 50
          odometerReading:
            description: "Odometro rodmenys"
            required: false
            type: integer
            example: 200000
          runHours:
            description: "Veiksnumo laikas"
            required: false
            type: integer
            example: 2
          registrationPlate:
            description: "Valst. numeriai"
            required: false
            type: string
            example: "NUM123"
                
    /trailer:
      post:
        description:
          Priekabos (jei nepatogu naudoti "fleet")     
        queryParameters:
          trailerId:
            description: "Unikalus priekabos ID, kuris bus naudojamas susiejimams su kitais objektais ir naujinimams"
            required: true
            type: string
            example: "trail123123"
          deleted:
            description: "Ar įrašas ištrintas. Atlas sistemoje toks įrašas bus nustatytas į neaktyvų, kad nesimatytų"
            required: false
            type: boolean
            example: false
            default: false
          active:
            description: "Įrašo aktyvumas. Neaktyvūs įrašai nematomi naudotojams"
            required: false
            type: boolean
            example: false
            default: false
          carrierId:
            description: "Unikalus vežėjo ID, per kurį susiejamas su kitais objektais"
            required: false
            type: string
            example: "47"
          capacity:
            description: "Talpa"
            required: false
            type: integer
            example: 10
          registrationPlate:
            description: "Valst. numeriai"
            required: false
            type: string
            example: "PRK123"
                 
    /fleet:
      post:
        description:
          Fūros arba priekabos (galima siųsti tiek vieną, tiek kitą. Atskirsime pagal tipą)     
        queryParameters:
          truckId:
            description: "Unikalus transp. priemonės ID, kuris bus naudojamas susiejimams su kitais objektais ir naujinimams"
            required: true
            type: string
            example: "fleet123123"
          type:
            description: "Transp. priemonės tipas"
            required: false
            type: string
            enum: ['trail','truck']
            example: 'trail'
            default: 'truck'
          deleted:
            description: "Ar įrašas ištrintas. Atlas sistemoje toks įrašas bus nustatytas į neaktyvų, kad nesimatytų"
            required: false
            type: boolean
            example: false
            default: false
          active:
            description: "Įrašo aktyvumas. Neaktyvūs įrašai nematomi naudotojams"
            required: false
            type: boolean
            example: false
            default: false
          carrierId:
            description: "Unikalus vežėjo ID, per kurį susiejamas su kitais objektais"
            required: false
            type: string
            example: "47"
          capacity:
            description: "Talpa"
            required: false
            type: integer
            example: 50
          odometerReading:
            description: "Odometro rodmenys. Aktualu jei pateikinėjama fūra."
            required: false
            type: integer
            example: 200000
          runHours:
            description: "Veiksnumo laikas. Aktualu jei pateikinėjama fūra."
            required: false
            type: integer
            example: 2
          registrationPlate:
            description: "Valst. numeriai"
            required: false
            type: string
            example: "FLT123"
                
    /driver:
      post:
        description:
          Vairuotojai     
        queryParameters:
          driverId:
            description: "Unikalus vairuotojo ID, kuris bus naudojamas susiejimams su kitais objektais ir naujinimams"
            required: true
            type: string
            example: "132123"
          deleted:
            description: "Ar įrašas ištrintas. Atlas sistemoje toks įrašas bus nustatytas į neaktyvų, kad nesimatytų"
            required: false
            type: boolean
            example: false
            default: false
          name:
            description: "Vairuotojo vardas ir pavardė. Jei įrašas naujas, o ne atnaujinamas, tada reikia, kad būtų užpildyta"
            required: false
            type: string
            example: "Petras Petraitis"
          carrierId:
            description: "Unikalus vežėjo ID, per kurį susiejamas su kitais objektais"
            required: false
            type: string
            example: "47"
          phone:
            description: "Telefono nr."
            required: false
            type: string
            example: '+37063456789'
            maxLength: 16
          email:
            description: "El.pašto adresas"
            required: false
            type: string
            example: "petras.petraitis@pastas.lt"
          userName:
            description: "Vairuotojo prisijungimo vardas"
            required: false
            type: string
          password:
            description: "Vairuotojo prisijungimo slaptažodis"
            required: false
            type: string
          enabled:
            description: "Galimybė naudotis vairuotojo paslaugomis"
            required: false
            type: boolean
            default: true"""

    @http.route('/create_or_update_location/post_data', type='json', auth='none', methods=['POST'], csrf=False)
    def post_location_data(self, **post):
        db = config.get('db_name', MAIN_DATABASE)
        db_registry = registry(db)
        json_req = request.jsonrequest
        json_req.update(post)
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['stock.location'].create_or_update_location(json_req)

        return True


    @http.route('/create_or_update_location/documentation', type='http', auth='none', methods=['GET'], csrf=False)
    def post_location_data_documentation(self, **post):
        return """<pre>#%%RAML 1.0
        title: Iceberg data to ATLAS
        baseUri: 192.168.52.172:11069
        version: v1

        /create_or_update_location
          /post_data
            post:
              description:
                Sukuriama arba atnaujinama DOS vieta.     
              queryParameters:
                code:
                  description: "Unikalus vietos kodas."
                  required: true
                  type: string
                  example: "AA1"
                name:
                  description: "Vietos pavadinimas."
                  required: false
                  type: string
                  default: "Autocentro alkoholio didmena"
                name_lt:
                  description: "Vietos pavadinimas lietuvių kalba"
                  required: false
                  type: string
                  default: "Autocentro alkoholio didmena"
                name_en:
                  description: "Vietos pavadinimas anglų kalba"
                  required: false
                  type: string
                  default: "Autocentrum of alcohol in bulk"
                name_lv:
                  description: "Vietos pavadinimas latvių kalba"
                  required: false
                  type: string
                  default: "Beztaras spirta autocentrs"
                name_ru:
                  description: "Vietos pavadinimas rusų kalba"
                  required: false
                  type: string
                  default: "Автоцентр алкоголя навалом"
                name_ee:
                  description: "Vietos pavadinimas estų kalba"
                  required: false
                  type: string
                  default: "Avatud alkoholide autokeskus"
                pref:
                  description: "Vietos PREF kodas."
                  required: false
                  type: string
                  default: "ACE"
                active:
                  description: "Įrašo aktyvumas. Neaktyvūs įrašai nematomi naudotojams"
                  required: false
                  type: boolean
                  example: false
                  default: true
                address:
                  description: "Vietos adresas."
                  required: false
                  type: string
                  default: "Ateities pl.39, Kaunas alk.sand. Nr. 1-CI"
                country_code:
                  description: "Vietos šalies kodas."
                  required: false
                  type: string
                  default: "LTU"
                vat_code:
                  description: "Vietos PVM kodas."
                  required: false
                  type: string
                  default: "LT100003677319"
                reg_code:
                  description: "Vietos registracijos kodas."
                  required: false
                  type: string
                  default: "30135347" """
        