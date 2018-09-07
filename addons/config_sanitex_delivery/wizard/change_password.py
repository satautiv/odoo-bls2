# -*- coding: utf-8 -*-
from odoo import api, models

class ChangePasswordUser(models.TransientModel):
    _inherit = 'change.password.user'
    _description = 'Change Password Wizard User'

    @api.multi
    def change_password_button(self):
        context = self._context and self._context.copy() or {}
        context['pw_change_wizard'] = True
        return super(ChangePasswordUser, self.with_context(context)).change_password_button()