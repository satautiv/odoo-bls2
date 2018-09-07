# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api

class DoInvoiceResultWizard(models.TransientModel):
    _name = 'do.invoice.result.wizard'
    _description = 'Result wizard for "Do invoice" method'
    
    @api.model
    def _get_printer(self):
        usr_obj = self.env['res.users']
        return usr_obj.browse(self.env.uid).get_default_printer()
    
    @api.model
    def get_doc_package_no(self):
        return self._context.get('doc_package_no', "")
    
    msg = fields.Text("Message", readonly=True)
    created_invoice_ids = fields.Many2many('account.invoice', string="Created Invoices", readonly=True)
    printer_id = fields.Many2one('printer', 'Printer', default=_get_printer)
#     last_printed_doc_no = fields.Char("Number of Last printed Document", help="In case printer error.")
    document_package_no = fields.Char("Document Package No.", readonly=True, default=get_doc_package_no)
    
    @api.multi
    def send_documents(self):
        self.created_invoice_ids.sorted(key=lambda r: r.id).send_document(printer=self.printer_id)
        return True
#         if not self.created_invoice_ids.filtered(lambda inv:\
#                     inv.sending_type == 'paper'
#         ):
#             return True
#         
#         self.write({'msg': ""})
#         form_view = self.env.ref('config_bls_stock.view_do_invoice_result_wizard2', False)[0]
#         
#         return {
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'do.invoice.result.wizard',
#             'target': 'new',
#             'type': 'ir.actions.act_window',
#             'views': [(form_view.id,'form')],
#             'res_id': self.id,
#             'nodestroy': False,
#         }
        
#     @api.multi
#     def continue_printing(self):
#         last_doc_number = self.last_printed_doc_no
#         skip_actions = False
#         if last_doc_number:
#             last_invoce_sent = self.created_invoice_ids.filtered(lambda inv:\
#                 inv.name.lower() == last_doc_number.lower()
#             )
#             if not last_invoce_sent:
#                 self.write({
#                     'msg': _("You have inserted worng document number. There is not document with such number: %s.") % (
#                         last_doc_number
#                     )
#                 })
#                 skip_actions = True
#         else:
#             last_invoce_sent = False
# 
#         if not skip_actions:
#             document_which_need_reprint = self.created_invoice_ids.filtered(lambda inv:\
#                 inv.sending_type == 'paper'\
#                 and (
#                     last_invoce_sent and inv.id > last_invoce_sent.id\
#                     or not last_invoce_sent
#                 )
#             )
#             
#             if not document_which_need_reprint:
#                 return True
#             
#             document_which_need_reprint.send_document(printer=self.printer_id)
#             self.write({'msg': ""})
#             
#         form_view = self.env.ref('config_bls_stock.view_do_invoice_result_wizard2', False)[0]
#         return {
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'do.invoice.result.wizard',
#             'target': 'new',
#             'type': 'ir.actions.act_window',
#             'views': [(form_view.id,'form')],
#             'res_id': self.id,
#             'nodestroy': False,
#         }
        