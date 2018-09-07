# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api



class StockRouteDocumentScanning(models.Model):
    _name = 'stock.route.document.scanning'
    _description = 'Scanning Lines for Route'

    route_id = fields.Many2one('stock.route', 'Route', readonly=True, ondelete='cascade', index=True)
    invoice_id = fields.Many2one('account.invoice', 'Document', readonly=True, ondelete='cascade')
    name = fields.Char('Document Number', size=128, readonly=True)
    scanned = fields.Boolean('Scanned', readonly=True, default=False, index=True)
    invoice_type = fields.Selection([
        ('need_scanning','Need Scanning'),
        ('collection_package','Collection Package'),
        ('digital_doc','Digital Document'),
    ])

    @api.model
    def create_if_not_exists(self, route_id, invoice_id, invoice_name, vals):
        search_sql = '''
            SELECT
                id
            FROM
                stock_route_document_scanning
            WHERE
                route_id = %s
                AND invoice_id = %s
                AND name = %s
        '''
        search_where = (route_id, invoice_id, invoice_name)
        self.env.cr.execute(search_sql, search_where)
        if not self.env.cr.fetchall():
            line_vals = vals.copy()
            line_vals.update({
                'route_id': route_id,
                'invoice_id': invoice_id,
                'name': invoice_name
            })
            return self.create(line_vals)
        return self