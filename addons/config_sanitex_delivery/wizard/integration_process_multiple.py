# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, api, fields

class IntegrationProcessMultiple(models.TransientModel):
    _name = 'integration.process.multiple.osv'
    _description = 'Integration Process' 
    
    process_for = fields.Selection([
        ('selected','Selected'),
        ('CreateOrder','CreateOrder'),
        ('CreateRoute','CreateRoute'),
        ('CreateInvoice','CreateInvoice'),
        ('CreatePackage','CreatePackage'),
        ('create_packing','create_packing'),
        ('quantity_by_customer','quantity_by_customer'),
        ('CreateClient','CreateClient'),
        ('CreatePOSID','CreatePOSID'),
    ], 'Process For', required=True, default='selected')

    @api.multi
    def process(self):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self._context or {}
        ctx = context.copy()
        ctx['force_process_intermediate'] = True
        if self.process_for == 'selected':
            intermediate_ids = context.get('active_ids', [])
            intermediates = interm_obj.search([
                ('id','in',intermediate_ids)
            ], order='datetime, id')
        else:
            intermediates = interm_obj.search([
                ('processed','=',False),
                ('function','=',self.process_for)
            ], order='datetime, id')

        intermediates.with_context(ctx).process_intermediate_objects_threaded()
        return {'type':'ir.actions.act_window_close'}
    
    @api.multi
    def remove_skip(self):
        interm_obj = self.env['stock.route.integration.intermediate']
        context = self._context or {}
        data = self[0]
        if data.process_for == 'selected':
            intermediate_ids = context.get('active_ids', [])
            intermediates = interm_obj.browse(intermediate_ids)
        else:
            intermediates = interm_obj.search([('function','=',data.process_for),('skip','=',True)])
        if intermediates:
            intermediates.write({'skip': False, 'count': 0})
        return {'type':'ir.actions.act_window_close'}