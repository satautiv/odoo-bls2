# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp import api, fields, models
from openerp.tools.translate import _


class integration_open_objects_osv(models.TransientModel):
    _name = 'integration.open_objects.osv'
    _description = 'Open created or updated objects from intermediate' 
    
    @api.model
    def _get_objects(self):
        object_names = {
            'product.product': _('Products'),
            'res.partner': _('Clients/POSID'),
            'sale.order': _('Orders'),
            'account.invoice': _('Invoices'),
            'stock.route': _('Routes'),
            'stock.package': _('Packages'),
            'sanitex.product.partner.stock': _('Client Stocks'),
        }
        context = self.env.context or {}
        if context.get('objects', []):
            return [(obj, object_names[obj]) for obj in context['objects']]
        if context.get('active_ids', []):
            intermediates = self.env['stock.route.integration.intermediate'].browse(context['active_ids'])
            objects = intermediates.get_objects()
            return [(obj, object_names[obj]) for obj in objects.keys()]
        return [('no',_('No Objects'))]
    
    object = fields.Selection(_get_objects, 'Objects to Open', required=True)
    
    @api.multi
    def open_objects(self):
        context = self.env.context or {}
        data = self[0]
        if data.object == 'no':
            return {'type':'ir.actions.act_window_close'}
        interm_env = self.env['stock.route.integration.intermediate']
        if context.get('active_ids', []):
            intermediates = interm_env.browse(context['active_ids'])
            objects = intermediates.get_objects(model=data.object)
            return interm_env.show_open(data.object, objects[data.object])
        return {'type':'ir.actions.act_window_close'}