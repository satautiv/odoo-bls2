# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class ResUsersSelectDefaultwarehouse(models.TransientModel):
    _name = 'res.users.select_default_warehouse.osv'
    _description = 'Change Drivers Owner' 
    
    new_warehouse_id = fields.Many2one(
        'stock.warehouse', 'New Default Warehouse', required=True, ondelete='cascade'
    )

    @api.multi
    def select(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        user.select_warehouse(self.new_warehouse_id.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }