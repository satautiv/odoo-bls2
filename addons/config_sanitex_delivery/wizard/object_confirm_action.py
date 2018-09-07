# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp import api, fields, models


class object_confirm_action(models.TransientModel):
    _name = 'object.confirm.action.osv'
    _description = 'Confirmation for Action on any Object'

    message = fields.Text(string='Warning', readonly=True,
        default=lambda self: self._context.get('warning', '')
    )
    just_close = fields.Boolean('Just Close', default=lambda self: self._context.get('just_close', False))

    @api.multi
    def do_action(self):
        context = self._context or {}
        if context.get('active_ids', []) and context.get('action_model', '') and context.get('action_function', ''):
            obj_env = self.env[context['action_model']]
            objects = obj_env.browse(context['active_ids'])
            method_to_call = getattr(objects, context['action_function'])
            return method_to_call()

        return {'type': 'ir.actions.act_window_close'}


object_confirm_action()