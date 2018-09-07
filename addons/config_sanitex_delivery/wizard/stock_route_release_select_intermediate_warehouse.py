# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models


class StockRouteReleaseSelectIntermediateWarehouse(models.TransientModel):
    _name = 'stock.route.release.select_intermediate_warehouse.osv'
    _description = 'Release Route' 
    
    intermediate_warehouse_id = fields.Many2one('stock.warehouse', 'Intermediate Warehouse')
    route_id = fields.Many2one('stock.route', 'Parent Route', readonly=True)
    available_sale_ids = fields.Many2many(
        'sale.order', 'available_sales_release_osv1_rel', 'osv_id', 
        'sale_id', 'Available Sales', readonly=True
    )
    
    @api.multi
    def release(self):
        osv = self[0]
        if osv.intermediate_warehouse_id:
            osv2 = self.env['stock.route.release.select_intermediate.step2.osv'].create({
                'osv_id': osv.id,
                'available_sale_ids': [(6, 0, osv.available_sale_ids.mapped('id'))],
                'selected_sale_ids': [(6, 0, osv.available_sale_ids.mapped('id'))]
            })
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.route.release.select_intermediate.step2.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'res_id': osv2.id,
                'nodestroy': True,
            }
        else:
            return {'type':'ir.actions.act_window_close'}
    

class StockRouteReleaseSelectIntermediateWarehouseStep2(models.TransientModel):
    _name = 'stock.route.release.select_intermediate.step2.osv'
    _description = 'Release Route 2' 
    
    osv_id = fields.Many2one('stock.route.release.select_intermediate_warehouse.osv', 'OSV', readonly=True)
    selected_sale_ids = fields.Many2many(
        'sale.order', 'selected_sales_release_osv2_rel', 'osv_id', 'sale_id', 'Selected Sales'
    )
    available_sale_ids = fields.Many2many(
        'sale.order', 'available_sales_release_osv3_rel', 'osv_id', 
        'sale_id', 'Available Sales', readonly=True
    )
    
    @api.multi
    def release_and_go_back(self):
        return self.release(go_back=True)
    
    @api.multi
    def release_and_quit(self):
        return self.release(go_back=False)
    
    @api.multi
    def release(self, go_back=False):
        osv2 = self[0]
        osv = osv2.osv_id
        for sale in osv2.selected_sale_ids.filtered('boolean_for_intermediate_wizard'):
            if sale.shipping_warehouse_id.id != osv.intermediate_warehouse_id.id:
                if sale.warehouse_next_to_id.id:
                    # sale.write({
                    #     'shipping_warehouse_id': osv.intermediate_warehouse_id.id
                    # })
                    self.env.cr.execute('''
                        UPDATE 
                            sale_order 
                        SET 
                            shipping_warehouse_id = %s
                        WHERE 
                            id = %s''',
                        (osv.intermediate_warehouse_id.id, sale.id)
                    )
                else:
                    # sale.write({
                    #     'warehouse_next_to_id': sale.shipping_warehouse_id.id,
                    #     'shipping_warehouse_id': osv.intermediate_warehouse_id.id
                    # })
                    self.env.cr.execute('''
                        UPDATE 
                            sale_order 
                        SET 
                            warehouse_next_to_id = %s,
                            shipping_warehouse_id = %s
                        WHERE 
                            id = %s''',
                        (sale.shipping_warehouse_id.id, osv.intermediate_warehouse_id.id, sale.id)
                    )
        self.env.clear()
        osv2.selected_sale_ids.update_shipping_warehouse_route_released()
        routes = osv2.selected_sale_ids.mapped('route_id')
        routes.update_route_type()
        routes.update_shipping_warehouse_id_filter()
        routes.update_picking_warehouse_id_filter()
        routes.mapped('sale_ids').mapped('route_number_id').create_route_template()

        osv.write({
            'available_sale_ids': [(6, 0, (osv2.available_sale_ids - osv2.selected_sale_ids.filtered('boolean_for_intermediate_wizard')).mapped('id'))],
            'intermediate_warehouse_id': False
        })
        if go_back:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.route.release.select_intermediate_warehouse.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'res_id': osv.id,
                'nodestroy': True,
            }
        else:
            return osv.release()