# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class ProductCertificate(models.Model):
    _inherit = 'product.certificate'
    
    product_id = fields.Many2one('product.product', 'Product', index=True)
    transportation_order_id = fields.Many2one('transportation.order', 'Transportation Order')
    product_code = fields.Char("Product Code", readonly=True)
#     lot_id = fields.Many2one('stock.production.lot', "Lot")
#     number = fields.Char("Number") #Turbut tas pat kas NAME
    issue_date = fields.Date('Issue Date')
    issued_by = fields.Char('Issued By')
    issued_place = fields.Char('Issued Place')
    keep_organisation_id = fields.Many2one('res.partner', "Organisation Where Certificate is Kept")
    reg_number = fields.Char("Reg. Number")
    type = fields.Char("Type")
    lot_ids = fields.Many2many(
        'stock.production.lot', 'certificate_lot_rel', 'certificate_id',
        'lot_id', string="Lots"
    )
    
    
class SanitexProductLocationStock(models.Model):
    _inherit = 'sanitex.product.location.stock'
    
    reserved_qty = fields.Float(
        'Reserved Quantity', digits=(16,4), default=0.0
    )
    uom_id = fields.Many2one('product.uom', "UoM")
    
#     @api.model
#     def reserve_qty(self, loc_id, product_id, qty, uom_id):
#         self._cr.execute('''
#             SELECT
#                 id
#             FROM
#                 sanitex_product_location_stock
#             WHERE product_id = %s
#                 AND location_id = %s
#             LIMIT 1
#         ''', (product_id,loc_id))
#         sql_res = self._cr.fetchone()
#         prod_loc_stock_id = sql_res and sql_res[0] or False
#         
#         if prod_loc_stock_id:
#             prod_loc_stock = self.browse(prod_loc_stock_id)
#             prod_loc_stock.write({
#                 'reserved_qty': prod_loc_stock.reserved_qty + qty
#             })
#         else:
#             self.create({
#                 'product_id': product_id,
#                 'location_id': loc_id,
#                 'reserved_qty': qty,
#                 'uom_id': uom_id
#             })
#         
#         return True


class ProductOwner(models.Model):
    _inherit = 'product.owner'
    
    document_edit_config_id = fields.Many2one('account.invoice.edit.config', "Document Edit Config")

    @api.multi
    def get_originator_party_vals(self):
        vals = {}
        partner = self.get_related_partner()

        self._cr.execute('''
            SELECT
                owner_code
            FROM
                product_owner
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        owner_code, = self._cr.fetchone() or ('',)
        if partner:
            partner_vals = self.env['res.partner'].get_partner_vals(partner.id, owner_code=owner_code)
            vals = {"party": partner_vals}
        return vals

# class ProductBarcode(models.Model):
#     _inherit = 'product.barcode'
#     
#     barcode = fields.Char('Barcode', size=32, index=True)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def get_item_vals(self):
        self._cr.execute('''
            SELECT
                pt.name, pp.default_code, pb.barcode
            FROM
                product_product AS pp
            JOIN product_template AS pt ON (
                pp.product_tmpl_id = pt.id
            )
            LEFT JOIN product_barcode pb on (pb.product_id=pp.id)
            WHERE pp.id = %s
            LIMIT 1
        ''', (self.id,))
        prod_name, default_code, barcode_str = self._cr.fetchone()

        item_vals = {
            'description': prod_name,
            # 'language_id': '',
            # 'buyers_item_identification': '',
            # 'sellers_item_identification': '',
            # 'manufacturers_item_identification': '',
            # 'standard_item_identification': '',
            'additional_item_identification': [
                {
                    "id": default_code,
                    "scheme_id": "PRODUCT_CODE",
                    "scheme_name": "Product code",
                    "scheme_agency_id": "BLS"
                }
            ],
            # 'commodity_classification': '',
            # 'item_instance': '',
            # 'certificate': '',
        }
        if barcode_str:
            item_vals["additional_item_identification"][0]["barcode_symbology_id"] = barcode_str

        return item_vals
