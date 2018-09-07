# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, api

class IrActReport_xml(models.Model):
    _inherit = 'ir.actions.report'
    
    @api.multi
    def use_report_server(self):
        res = super(IrActReport_xml, self).use_report_server()
        if not res:
            res = self.report_name == 'config_bls_stock.invoice_document_print_form'
        return res