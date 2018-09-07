# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    desp_adv_cursor = fields.Integer("Last Despatch Advice ID", readonly=True)
    despatch_api_link = fields.Char("Despatch API Link", default="http://192.168.52.185/api/")
    despatch_import_limit = fields.Integer("Despatch Import Limit", default=200)
    document_edit_config_id = fields.Many2one('account.invoice.edit.config', "Document Edit Config")
    ubl_save_directory = fields.Char("UBL Save Dirctory", default='~/ATLAS_formed_UBLs')
    ubl_export_limit = fields.Integer("UBL Export Limit", default=50)
    save_test_ubs_to_disk = fields.Boolean("Save Test UBLs to Disk", default=False)
    cmr_document_sequence_id = fields.Many2one('ir.sequence', 'CMR Numbering Sequence')
    price_change_url = fields.Char('Price Change URL', size=256,
       default='http://testing.snx.lt/exchange/api/pricerecalc'
    )
    country_codes = fields.Char('Codes(s) for Country', size=32)

    @api.multi
    def get_country_codes(self):
        # Kai kada reikia ieškoti partnerių priklausančių tai pačiai šaliai kaip ir įmonė.
        # Ši funkcija grąžina šalies kodus (LTU, LT ...)
        codes = []
        if self.country_codes:
            for code in self.country_codes.split(','):
                codes.append(code.strip())
        return codes
