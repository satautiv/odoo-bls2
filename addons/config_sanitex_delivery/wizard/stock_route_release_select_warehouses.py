# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp import api, fields, models


class stock_route_release_select_warehouse_osv(models.TransientModel):
    _name = 'stock.route.release.select_warehouse.osv'
    _description = 'Release Route' 
    
    selected_warehouse_ids = fields.Many2many(
        'stock.warehouse', 'selected_warehouse_release_osv_rel', 'osv_id', 'wh_id', 'Warehouses'
    )
    
    available_warehouse_ids = fields.Many2many(
        'stock.warehouse', 'available_warehouse_release_osv_rel', 'osv_id', 'wh_id', 'Warehouses'
    )
    route_id = fields.Many2one('stock.route', 'Parent Route', readonly=True)
    
    @api.multi
    def release(self):
        osv = self[0]
        if 1 < len(osv.selected_warehouse_ids) < len(osv.available_warehouse_ids):
            osv2 = self.env['stock.route.release.select_warehouse.step2.osv'].create({
                'osv_id': osv.id,
                'available_warehouse_ids': [(6, 0, osv.selected_warehouse_ids.mapped('id'))]
            })
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.route.release.select_warehouse.step2.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'res_id': osv2.id,
                'nodestroy': True,
            }
        else:
            for sale in osv.route_id.sale_ids.filtered(lambda record: record.warehouse_id != record.shipping_warehouse_id): 
                if sale.shipping_warehouse_id in osv.selected_warehouse_ids:
                    sale.extend_chain()
                else:
#                     sale.extend_chain([osv.selected_warehouse_ids[0].id])
                    sale.extend_chain([osv.selected_warehouse_ids[0].id, sale.shipping_warehouse_id.id])
                    
        return osv.route_id.action_release()
    

class stock_route_release_select_warehouse_step2_osv(models.TransientModel):
    _name = 'stock.route.release.select_warehouse.step2.osv'
    _description = 'Release Route 2' 
    
    selected_warehouse_id = fields.Many2one('stock.warehouse', 'Selected Warehouse')
    available_warehouse_ids = fields.Many2many(
        'stock.warehouse', 'available_warehouse_release_osv2_rel', 'osv_id', 'wh_id', 'Warehouses'
    )
    osv_id = fields.Many2one('stock.route.release.select_warehouse.osv', 'OSV', readonly=True)
    
    @api.multi
    def release(self):
        osv2 = self[0]
        osv = osv2.osv_id
        if 1 < len(osv.selected_warehouse_ids) < len(osv.available_warehouse_ids):
            for sale in osv.route_id.sale_ids.filtered(lambda record: record.warehouse_id != record.shipping_warehouse_id): 
                if sale.shipping_warehouse_id in osv.selected_warehouse_ids:
                    sale.extend_chain()
                else:
#                     sale.extend_chain([osv2.selected_warehouse_id.id])
                    sale.extend_chain([osv2.selected_warehouse_id.id, sale.shipping_warehouse_id.id])
                    
        return osv.route_id.action_release()