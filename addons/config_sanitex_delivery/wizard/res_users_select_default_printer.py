# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class ResUsersSelectDefaultPrinter(models.TransientModel):
    _name = 'res.users.select_default_printer.osv'
    _description = 'Change Drivers Owner' 
    
    new_printer_id = fields.Many2one(
        'printer', 'New Default Printer', required=True, ondelete='cascade'
    )

    @api.multi
    def select(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        user.select_printer(self.new_printer_id.id)
        return {'type':'ir.actions.act_window_close'}