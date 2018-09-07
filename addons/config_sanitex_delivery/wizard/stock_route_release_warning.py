# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp import api, fields, models


class stock_route_release_warning_osv(models.TransientModel):
    _name = 'stock.route.release_warning.osv'
    _description = 'Route Release Warning' 

    message = fields.Text(string='Warning', readonly=True, 
        default=lambda self: self._context.get('warning', '')
    )
    
    @api.multi
    def release(self):
        context = self._context or {}
        if context.get('active_ids', []):
            self.env['stock.route'].browse(context['active_ids']).action_release()
                
        return {'type': 'ir.actions.act_window_close'}
    
stock_route_release_warning_osv()