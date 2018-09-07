# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
from odoo.exceptions import UserError


class SaleOrderAssignRouteTemplate(models.TransientModel):
    _name = 'sale.order.assign.route.template.osv'
    _description = 'Assign Route Template to Transportation Task'

    route_template_id = fields.Many2one(
        'stock.route.template', 'Route Template', required=True
    )

    @api.multi
    def assign(self):
        context = self.env.context or {}
        task_env = self.env['sale.order']

        tasks = task_env.browse([])
        for task_id in context.get('active_ids',[]):
            task = task_env.browse(task_id)
            if task.route_id:
                raise UserError(_('Task already in route(%s, ID: %s)') % (task.route_id.name, str(task.route_id.id)))
            if task.route_number_id:
                #TODO: kažką gal daryti?
                pass
            task.write({'shipping_warehouse_id': task.warehouse_id.id})
            tasks += task
        self.route_template_id.assign_tasks(tasks)


        return {'type': 'ir.actions.act_window_close'}