# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api

class SendPrintDocumentWizard(models.TransientModel):
    _name = 'send.print.document.wizard'
    _description = 'Wizard to send or print document depending on document type'
    
    @api.model
    def _get_printer(self):
        usr_obj = self.env['res.users']
        return usr_obj.browse(self.env.uid).get_default_printer()
    
    printer_id = fields.Many2one('printer', 'Printer', default=_get_printer)
    print_even_electronical_documents = fields.Boolean(
        "Print Even Electonical Documents", default=False
    )
    
    @api.multi
    def send_documents(self):
        context = self._context or {}
        invoice_env = self.env['account.invoice']
        
        invoice_ids = context.get('active_ids', False)
        if invoice_ids:
            invoices = invoice_env.browse(invoice_ids)
            invoices.sorted(key=lambda r: r.id).send_document(
                printer=self.printer_id, force_print=self.print_even_electronical_documents
            )
        return True 