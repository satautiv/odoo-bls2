# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models

class AccountInvoiceContainerChangeState(models.TransientModel):
    _name = 'account.invoice.container.change_state.osv'
    _description = 'Change State for Container' 

    state_to = fields.Selection([
        ('not_received', 'Not Received From Client'),
        ('canceled', 'Canceled'),
        ('registered', 'Registered'),
        ('in_terminal', 'In Terminal'),
        ('transported', 'Being Transported'),
        ('delivered', 'Delivered'),
        ('returned_to_supplier', 'Returned to Supplier'),
        ('lost', 'Lost'),
    ], 'State', required=True, default=lambda self: self._context.get('default_state_to', False))
    
    @api.multi
    def change_state(self):
        context = self.env.context or None
        data = self[0]
        if context.get('active_ids', []):
            if data.state_to == 'refused_by_client':
                containers = self.env['account.invoice.container'].browse(context['active_ids'])
                containers.write({'state': 'in_terminal'})
                containers.mapped('package_id').write({'state': 'in_terminal'})
            else:
                containers = self.env['account.invoice.container'].browse(context['active_ids'])
                containers.write({'state': self[0].state_to})
        return {'type': 'ir.actions.act_window_close'}