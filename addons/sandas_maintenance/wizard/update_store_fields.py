# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

class MaintenanceUpdateStoreFieldsOsv(models.TransientModel):
    _name = "maintenance.update.store.fields.osv"
    _description = "Maintance Update Store Fields Wizard"

    field_ids = fields.Many2many('ir.model.fields',
        'maintenance_update_store_fields_osv_rel', 'maintenance_id',
        'field_id', 'Fields'
    )
    domain = fields.Char('Domain', size=512)
    parent_store_model_ids = fields.Many2many('ir.model',
        'maintenance_update_sf_ir_model_rel', 'maintenance_id',
        'model_id', 'Parent Store'
    )

    @api.multi
    def do_update(self):
        form = self[0]
        for fld in form.field_ids:
            obj = self.env[fld.model]
            if form.domain:
                model_records = obj.sudo().search(safe_eval(form.domain))
            else:
                model_records = obj.sudo().search([])
            self.env.add_todo(obj._fields[fld.name], model_records)
            obj.recompute()
        for model in form.parent_store_model_ids:
            obj = self.env[model.model]
            obj._parent_store_compute()
        return {'type': 'ir.actions.act_window_close'}
