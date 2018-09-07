# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp import api, fields, models

class stock_package_assign_to_route_osv(models.TransientModel):
    _name = 'stock.package.assign_to_route.osv'
    _description = 'Assign Package to Route' 
    
#     _columns = {
#         'route_id': fields.many2one(
#             'stock.route', 'Route', required=True
#         ),
#     }
    
    route_id = fields.Many2one('stock.route', 'Route', required=True, ondelete='cascade')
#     type = fields.Selection([('collection','Collection'),('delivery','Delivery')], 'Type')
    
    @api.multi
    def assign(self):
        context = self._context or {}
        type = context.get('type', 'delivery')
        
        package_obj = self.env['stock.package']
        data = self[0]
        if context.get('active_ids', []):
            if type == 'collection':
                packages = package_obj.search([('collection_route_id','!=',False),('id','in',context['active_ids'])])
                if packages:
                    package = packages[0]
                    route = package.collection_route_id
                    raise UserError(_('Package(%s, ID: %s) already assigned to route(%s, ID: %s)') % (
                        package.internal_order_number, str(package.id), route.name_get() and route.name_get()[0] and route.name_get()[0][1] or route.receiver, str(route.id)
                    ))
                packages = package_obj.browse(context['active_ids'])
                packages.write({'collection_route_id': data.route_id.id})
            elif type == 'delivery':
                #check
                packages = package_obj.browse(context['active_ids'])
                packages.write({'delivery_route_ids': [(4, data.route_id.id)]})
                data.route_id.fill_in_containers()
                
#             for id in context['active_ids']:
#                 if package_obj.check_if_in_route(cr, uid, id, context=context):
#                     package = package_obj.browse(cr, uid, id, context=context)
#                     route_ids = package_obj.check_if_in_route(cr, uid, id, context=context)
#                     route = route_obj.browse(cr, uid, route_ids[0], context=context)
#                     raise UserError(_('Package(%s, ID: %s) already assigned to route(%s, ID: %s)') % (
#                         package.internal_order_number, str(package.id), route.name_get() and route.name_get()[0] and route.name_get()[0][1] or route.receiver, str(route.id)
#                     ))
#             data = self.browse(cr, uid, ids[0], context=context)
#             route_obj.write(cr, uid, [data.route_id.id], {
#                 'package_ids': [(4, id) for id in context['active_ids']]
#             }, context=context)
#             package_obj.write(
#                 cr, uid, context['active_ids'], {
#                     'state': 'assigned_to_route'
#                 }, context=context
#             )
        return {'type':'ir.actions.act_window_close'}
    
stock_package_assign_to_route_osv()