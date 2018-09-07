# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError

class StockLocationChangeOwner(models.TransientModel):
    _name = 'stock.location.change_owner.osv'
    _description = 'Change Drivers Owner' 

    new_owner_id = fields.Many2one(
        'res.partner', 'New Owner', required=True, ondelete='cascade'
    )
    note = fields.Text('Note', readonly=True)
    wiz_stage = fields.Selection([('1','1'),('2','2')], 'Stage', default='1')
    location_id = fields.Many2one(
        'stock.location', 'Location'
    )

    @api.multi
    def next(self):
        context = self.env.context or {}
        loc_obj = self.env['stock.location']
        if context.get('active_ids', False):
            location = loc_obj.browse(context['active_ids'][0])
            if location.owner_id and \
                location.owner_id.id != self.new_owner_id.id \
            :
                if location.get_drivers_debt_all():
                    raise UserError(_('You can\'t change drivers company, because driver still has debt'))
                else:
                    return self.change()
        return {'type':'ir.actions.act_window_close'}

    @api.multi
    def change(self):
        context = self.env.context or {}
        loc_obj = self.env['stock.location']
        if self.location_id:
            loc_id = self.location_id.id
        else:
            loc_id = context.get('active_ids', [])[0]
        loc_obj.browse(loc_id).write({
            'owner_id': self.new_owner_id.id,
        })
        return {'type':'ir.actions.act_window_close'}