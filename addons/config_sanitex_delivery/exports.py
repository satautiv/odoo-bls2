# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api

class IrExports(models.Model):
    _inherit = 'ir.exports'

    filter_value = fields.Char('Filter Value', size=128)
    
    @api.model
    def create(self, vals):
        context = self.env.context or {}
        if context.get('export_filter_value', False):
            vals['filter_value'] = context['export_filter_value']
        return super(IrExports, self).create(vals)

    @api.model
    def get_search_domain(self, domain):
        context = self.env.context or {}
        if context.get('export_filter_value', False):
            domain.append(('filter_value','=',context['export_filter_value']))

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(IrExports, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )