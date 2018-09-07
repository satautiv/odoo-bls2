# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api


class StockRouteCreateCMR(models.TransientModel):
    _name = 'stock.route.create.cmr.osv'
    _description = 'Wizard to create and print CMR report from route'

    document_ids = fields.Many2many('account.invoice', 'cmr_osv_document_rel', 'osv_id', 'invoice_id', 'Documents')

    @api.multi
    def create_cmr(self):
        for osv in self:
            osv.document_ids.create_cmr_documents()