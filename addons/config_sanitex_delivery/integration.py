# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from datetime import datetime, timedelta

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError

import json
import time
import traceback

import logging
_logger = logging.getLogger(__name__)

class DeliveryIntegrationLog(models.Model):
    _name = 'delivery.integration.log'
    _description = 'Delivery Integration Log'


    create_date = fields.Datetime('Date', readonly=True)
    function = fields.Char('Function', size=256, readonly=True)
    received_information = fields.Text('Received Information', readonly=True)
    returned_information = fields.Text('Returned Information', readonly=True)
    traceback = fields.Text('Traceback', readonly=False)

    
    _rec_name = 'function'
    _order = 'create_date DESC'
    
    @api.model
    def cron_remove_old_objects(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        days_after = company.unlinkt_old_objects_after_days
        context = self.env.context or {}
        ctx = context.copy()
        ctx['allow_to_delete_integration_obj'] = True
        _logger.info('Removing old Integration Log objects (%s days old)' % str(days_after)) 
        today = datetime.now()
        delete_until = (today - timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')
        old_log_objects = self.search([
            ('create_date','<=',delete_until)
        ], limit=100)
        
        while old_log_objects:
            _logger.info('Deleting %s' % str(old_log_objects.mapped('id'))) 
            old_log_objects.with_context(ctx).unlink()
            self.env.cr.commit()
            old_log_objects = self.search([
                ('create_date','<=',delete_until)
            ], limit=100)

    @api.multi
    def write(self, vals):
        if 'returned_information' in vals.keys():
            vals['returned_information'] = vals['returned_information'].encode('utf-8').decode('unicode-escape')
            
        return super(DeliveryIntegrationLog, self).write(vals)

    @api.model
    def create(self, vals):
        if 'received_information' in vals.keys():
            vals['received_information'] = vals['received_information'].encode('utf-8').decode('unicode-escape')
        return super(DeliveryIntegrationLog, self).create(vals)

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_delete_integration_obj', False):
            raise UserError(_('You can\'t delete integration objects %s') % ', '.join([str(id) for id in self.mapped('id')]))
        return super(DeliveryIntegrationLog, self).unlink()
    
    
class PodIntegration(models.Model):
    _name = 'pod.integration'
    _description = 'POD Integration'
    
    _ENV_BY_OBJS = {
        'user': 'stock.location',
        'carrier': 'res.partner',
        'route': 'stock.route',
        'fleet': 'stock.fleet',
        'documentLine': 'account.invoice.line',
        'document': 'account.invoice',
        'container': 'account.invoice.container',
        'owner': 'product.owner',
        'supplier': 'res.partner',
    }
    
    _FUNCTION_BY_OBJ = {
        'user': 'PODDriver',
        'carrier': 'PODCarrier',
        'route': 'PODRoute',
        'fleet': 'PODFleet',
        'documentLine': 'PODDocumentLine',
        'document': 'PODDocument',
        'container': 'PODContainer',
        'owner': 'PODOwner',
        'supplier': 'PODSupplier',
    }
    
    @api.model
    def get_pod_integration_function_selection(self):
        return [
            ('PODDriver', 'PODDriver'),
            ('PODCarrier', 'PODCarrier'),
            ('PODRoute', 'PODRoute'),
            ('PODFleet', 'PODFleet'),
            ('PODDocumentLine', 'PODDocumentLine'),
            ('PODDocument', 'PODDocument'),
            ('PODContainer', 'PODContainer'),
            ('PODOwner', 'PODOwner'),
            ('PODSupplier', 'PODSupplier'),
        ]
        
    function = fields.Selection(get_pod_integration_function_selection, "Function", required=True)
    limit = fields.Integer("Limit", default=50)
    company_id = fields.Many2one('res.company', "Company", required=True)
        
#     @api.model
#     def get_env_by_obj(self, obj):
#         return self._ENV_BY_OBJS.get(obj, False)
    
    @api.model
    def get_function_by_obj(self, obj):
        return self._FUNCTION_BY_OBJ.get(obj, False)
    
    @api.model
    def get_objects_by_version(self, obj, id_version):
        obj_env = self.env[self._ENV_BY_OBJS.get(obj, False)]
        
        try:
            domain = obj_env.get_pod_domain(obj)
        except:
            domain = []

        company = self.env['res.users'].browse(self.env.uid).company_id
        function = self._FUNCTION_BY_OBJ.get(obj, False)
        limit_record = self.search([
            ('function','=',function),
            ('company_id','=',company.id)
        ], limit=1)
        limit = id_version and (limit_record and limit_record.limit or 50) or 1
        
        search_order = id_version and 'id_version' or 'id_version desc'
        
        if id_version:
            domain.append(('id_version','>',id_version))

        ctx = self._context.copy()
        ctx['active_test'] = False
        return obj_env.with_context(ctx).search(domain, order=search_order, limit=limit)

    
    @api.model
    def get_obj_information_by_version(self, obj, id_version):
        interm_env = self.env['stock.route.integration.intermediate']
        receive_vals = _('Received version parameter') + ': '
        result_vals = ''
        processed = True
        trb = ''
        
        start_datetime = datetime.now()
        
        if isinstance(id_version, str):
            receive_vals += id_version
        else:
            receive_vals += str(id_version)
        
        receive_vals += '\n'+_("Received object parameter") + ': ' + obj
        
        intermediate = interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': self.get_function_by_obj(obj),
            'received_values': receive_vals,
            'processed': False
        })
        self.env.cr.commit()
        results = {obj: []}
        try:
            objects = self.get_objects_by_version(obj, id_version)
            result_vals += _('Objects to return: ') + str(objects.mapped('id')) + '\n\n'

            for object in objects:
                results[obj].append(object.to_dict_for_pod_integration(obj))
            results[obj] = sorted(results[obj], key=lambda k: k['id_version'])
            result_vals += _('Result: ') + '\n\n' + str(json.dumps(results, indent=2))
        except Exception as e:
            err_note = _('Failed to return %s objects: %s') % (obj, tools.ustr(e),)
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
        return results
    
    @api.model
    def get_examples(self):
        res = []
        for obj in self._ENV_BY_OBJS.keys():
            object = self.with_context(for_raml=True).get_objects_by_version(obj, False)
            res.append({
                obj : [object.to_dict_for_pod_integration(obj)]
            })
        return res
        
        
class IcebergIntegration(models.Model):
    _name = 'iceberg.integration'
    _description = 'ICEBERG Integration'
    
    @api.model
    def get_iceberg_integration_function_selection(self):
        return [
            ('IcebergCreateDriver', 'IcebergCreateDriver'),
            ('IcebergCreateFleet', 'IcebergCreateFleet'),
            ('IcebergGetDriverTotalDebt', 'IcebergGetDriverTotalDebt'),
        ]
        
    _ENV_BY_OBJS = {
        'driver': 'stock.location',
        'fleet': 'stock.fleet',
        'trailer': 'stock.fleet',
        'truck': 'stock.fleet',
    }
        
    _FUNCTION_BY_OBJ = {
        'driver': 'IcebergCreateDriver',
        'fleet': 'IcebergCreateFleet',
        'trailer': 'IcebergCreateFleet',
        'truck': 'IcebergCreateFleet',
    }
    
    @api.model
    def set_data(self, data, intermediate=None):
        interm_env = self.env['stock.route.integration.intermediate']
        obj = data and data.get('obj', False)
        obj_lower = obj.lower()
        start_datetime = datetime.now()
        processed = True
        trb = ''
        result_vals = ""

        if intermediate is None:
            if self._FUNCTION_BY_OBJ.get(obj_lower, False):
                intermediate = interm_env.create({
                    'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'function': self._FUNCTION_BY_OBJ.get(obj_lower, False),
                    'received_values': str(json.dumps(data, indent=2)),
                    'processed': False
                })
            else:
                intermediate = interm_env.create({
                    'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'function': self._FUNCTION_BY_OBJ.get(obj_lower, False),
                    'received_values': str(json.dumps(data, indent=2)),
                    'processed': False,
                    'traceback_string': _("Got wrong data format from Iceberg"),
                    'return_results': _("Got wrong data format from Iceberg"),
                })
                return "Got wrong data format"
        
        self.env.cr.commit()
        
        try:
            result_vals = self.env[self._ENV_BY_OBJS[obj_lower]].set_iceberg_data(data)
        except Exception as e:
            result_vals = _('Failed to create or update %s object: %s') % (obj_lower, tools.ustr(e),)
            processed = False
            trb = traceback.format_exc()
            self.env.cr.rollback()
        
        end_datetime = datetime.now()
            
        intermediate.write({
            'processed': processed,
            'return_results': result_vals,
            'traceback_string': trb,
            'duration': (end_datetime-start_datetime).seconds
        })
        self.env.cr.commit()
        return result_vals