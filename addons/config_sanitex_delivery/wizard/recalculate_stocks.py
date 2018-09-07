# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class StockRecalculate(models.TransientModel):
    _name = 'stock.recalculate.osv'
    _description = 'Recalculate Stocks' 

    location_ids = fields.Many2many(
        'stock.location', 'stock_recalculate_wiz_location_rel',
        'location_id', 'osv_id', 'Locations'
    )
    product_ids = fields.Many2many(
        'product.product', 'stock_recalculate_wiz_product_rel',
        'product_id', 'osv_id', 'Products'
    )
    partner_ids = fields.Many2many(
        'res.partner', 'stock_recalculate_wiz_partner_rel',
        'partner_id', 'osv_id', 'Partners'
    )
    recalculate_reconciliation_info = fields.Boolean('Recalculate Reconciliation Info')

    @api.multi
    def recalculate(self):
        prod_obj = self.env['product.product']
        move_obj = self.env['stock.move']
        
        product_ids = self.product_ids and self.product_ids.mapped('id') or []
        location_ids = self.location_ids and self.location_ids.mapped('id') or []
        partner_ids = self.partner_ids and self.partner_ids.mapped('id') or []

        if not self.recalculate_reconciliation_info:
            prod_obj.recalculate_threaded(
                product_ids, location_ids, partner_ids
            )
        
        if self.recalculate_reconciliation_info:
            move_obj.recalculate_reconciliation_info_threaded(
                product_ids, location_ids, partner_ids
            )
        
        return {'type':'ir.actions.act_window_close'}