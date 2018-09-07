# # -*- encoding: utf-8 -*-
# ###########################################################################
# #
# #    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
# #
# ###########################################################################
# 
# from openerp import api, fields, models
# from openerp.tools.translate import _
# 
# import time
# 
# class sale_order_create_route_osv(models.TransientModel):
#     _name = 'sale.order.create_route.osv'
#     _description = 'Create Route from several orders' 
# 
#     route_type = fields.Selection([
#         ('internal', 'Interbranch (IBL)'),
#         ('out', 'Distributive (DST)'),
#         ('mixed', 'Mixed')
#     ], 'Route Type', required=True, default='mixed')
#     
#     @api.multi
#     def create_route(self):
#         so_env = self.env['sale.order']
#         route_env = self.env['stock.route']
#         usr_env = self.env['res.users']
#         wh_env = self.env['stock.warehouse']
#         
#         user = usr_env.browse(self.env.uid)
#         osv = self[0]
#         context = self.env.context or {}
#         sale_ids = context.get('active_ids', [])
#         if sale_ids:
#             sales = so_env.browse(sale_ids)
#             route_vals = {}
#             route_vals['type'] = osv.route_type
#             route_vals['date'] = time.strftime('%Y-%m-%d')
#             route_numbers = sales.mapped('route_number')
#             if route_numbers:
#                 route_vals['receiver'] = route_numbers[0]
#             if user.default_warehouse_id:
#                 warehouse_id = user.default_warehouse_id.id
#             else:
#                 warehouse_id = sales.mapped('warehouse_id')[0].id
#             wh = wh_env.browse(warehouse_id)
#             route_vals['warehouse_id'] = wh.id
#             route_vals['source_location_id'] = wh.wh_output_stock_loc_id and wh.wh_output_stock_loc_id.id or False
#             if osv.route_type == 'internal':
#                 sh_warehouses = sales.mapped('shipping_warehouse_id')
#                 if sh_warehouses:
#                     route_vals['destination_warehouse_id'] = sh_warehouses[0].id
#                     route_vals['return_location_id'] = sh_warehouses[0].wh_return_stock_loc_id and sh_warehouses[0].wh_return_stock_loc_id.id or False
#             else:
#                 route_vals['return_location_id'] = wh.wh_return_stock_loc_id and wh.wh_return_stock_loc_id.id
#             if sales.mapped('driver_id'):
#                 route_vals['location_id'] = sales.mapped('driver_id')[0].id
# #             route_vals['sale_ids'] = [(6, 0, sale_ids)]
#             route = route_env.create(route_vals)
#             sales.write({'route_id': route.id})
#             
#             form_view = self.env.ref('config_sanitex_delivery.view_stock_routes_form', False)[0]
#             view = self.env.ref('config_sanitex_delivery.view_stock_routes_tree', False)[0]
#             domain = [('id','=',route.id)]
#             return {
#                 'name': _('Created Route'),
#                 'view_type': 'form',
#                 'view_mode': 'form,tree',
#                 'res_model': 'stock.route',
#                 'views': [(form_view.id,'form'),(view.id,'tree')],
#                 'type': 'ir.actions.act_window',
#                 'res_id': route.id,
#                 'domain': domain
#             }
#         
#         return {'type': 'ir.actions.act_window_close'}
#     
# sale_order_create_route_osv()