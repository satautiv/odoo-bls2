# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models


class StockRouteReceive(models.TransientModel):
    _name = 'stock.route.receive.osv'
    _description = 'Receive Route Sales' 
    
    line_ids = fields.One2many('stock.route.receive.lines.osv', 'osv_id', 'Lines')
    route_id = fields.Many2one('stock.route', 'Route')
    
    @api.multi
    def receive(self):
        return self.line_ids.receive()
    
class StockRouteReceiveLines(models.TransientModel):
    _name = 'stock.route.receive.lines.osv'
    
    check_all = fields.Boolean('All Containers', default=False)
    osv_id = fields.Many2one('stock.route.receive.osv', 'OSV')
    picking_warehouse_id = fields.Many2one('stock.warehouse', 'Picking Warehouse', readonly=True)
    picking_warehouses = fields.Char('Picking Warehouses', readonly=True)
    shipping_warehouse_id = fields.Many2one('stock.warehouse', 'Shipping Warehouse', readonly=True, required=False)
#     sale_ids = fields.Many2many(
#         'sale.order', 'sale_order_route_receive_line_rel', 'osv_id', 
#         'sale_id', 'Received Orders'
#     )
    container_ids = fields.Many2many(
        'account.invoice.container', 'invoice_container_route_receive_line_rel', 'osv_id', 
        'container_id', 'Received Containers'
    )
    sales = fields.Char('Containers', size=16, readonly=True)
    
    
    @api.multi
    def receive(self):
        for line in self:
            if line.check_all:
                line.container_ids.receive(route_id=line.osv_id.route_id.id)
            else:
                line.container_ids.filtered('route_received').receive(
                    route_id=line.osv_id.route_id.id
                )
                line.container_ids.filtered('route_not_received').not_receive(
                    route_id=line.osv_id.route_id.id
                )
        return True
                
        
    @api.onchange('check_all')
    def _onchange_check_all(self):
        if self.check_all:
            self.sales = str(len(self.container_ids)) + '/' + str(len(self.container_ids))
        else:
            self.sales = str(len(self.container_ids.filtered('route_received'))) + '/' + str(len(self.container_ids))
            
    @api.multi
    def action_open(self):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'res_id': self.id,
            'nodestroy': True,
            'auto_refresh': 5,
        }
    
    @api.multi
    def action_save(self):
        for line in self:
            check_all = True
            if len(line.container_ids.filtered('route_received')) != len(line.container_ids):
                check_all = False
            self.write({
                'check_all': check_all,
                'sales': str(len(line.container_ids.filtered('route_received'))) + '/' + str(len(line.container_ids))
            })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.receive.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'res_id': self.osv_id.id,
            'nodestroy': True,
        }

    @api.multi
    def action_check_all(self):
        check_all = not self[0].check_all
        self.write({'check_all': check_all})
        for line in self:
            line._onchange_check_all()
        return {
            "type": "reload",
        }