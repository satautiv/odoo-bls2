# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api
 
class StockRouteTransferProduct(models.TransientModel):
    _name = 'stock.route.transfer_product.osv'
    _description = 'Transfer Orders to another Route' 

    line_ids = fields.One2many('stock.route.transfer_product.line.osv', 'osv_id', 'Lines')
    parent_route_id = fields.Many2one('stock.route', 'Route to Transfer from')

    @api.multi
    def transfer(self):
        return {'type':'ir.actions.act_window_close'}


class StockRouteTransferProductLine(models.TransientModel):
    _name = 'stock.route.transfer_product.line.osv'
    _description = 'Transfer Orders to another Route Line' 

    product_id = fields.Many2one('product.product', 'Product to Transfer', requred=True)
    rem_qty_bydriver = fields.Float('Remaining Drivers Quantity', digits=(16,2))
    route_id = fields.Many2one(
        'stock.route', 'Route to Transfer for', required=False, ondelete='cascade'
    )
    qty = fields.Float('Quantity', digits=(16,2))
    osv_id= fields.Many2one('stock.route.transfer_product.osv', 'Osv')