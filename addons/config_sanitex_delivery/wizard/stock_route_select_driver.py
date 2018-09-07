# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockRouteSelectDriver(models.TransientModel):
    _name = 'stock.route.select_driver.osv'
    _description = 'Select Driver' 
    
    driver_id = fields.Many2one('stock.location', 'Driver', required=True, ondelete='cascade')
    license_plate = fields.Char('License Plate')
    trailer = fields.Char('Trailer')
    driver_company_id = fields.Many2one('res.partner', 'Drivers Company', readonly=True)
    show_all_drivers = fields.Boolean('Allow to Select From All Drivers',
        help='Drivers are filtered by users region. When this checkbox is marked region filter will not be applied'
    )
    
    
    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        if self.driver_id:
            self.license_plate = self.driver_id.license_plate
            self.trailer = self.driver_id.trailer
            self.driver_company_id = self.driver_id.owner_id and self.driver_id.owner_id.id or False
        else:
            self.license_plate = ''
            self.trailer = ''
            self.driver_company_id = False
            
    
    @api.multi
    def select_from_dif_obj(self):
        #Metodas, kad galmetu uzkolti kitam moduly
        return True

    @api.multi
    def select(self):
        context = self.env.context or {}

        if context.get('active_model', 'stock.route') == 'stock.route':
            if context.get('active_ids', False):
                route_obj = self.env['stock.route']
                route = route_obj.browse(context['active_ids'][0])
                if route.state != 'draft':
                    raise UserError(_('You can\'t change driver to route witch is not in \'draft\' state'))
                route.write({
                    'location_id': self.driver_id.id,
                    'license_plate': self.license_plate or route.license_plate or '',
                    'trailer':  self.trailer or route.trailer or '',
                    'driver_picked': True,
                })
                
                update_driver_vals = {}

                # Prie vairuotojo pakeičia umerius ir priekabos numerius jeigu jie nesutampa su naujai
                # wizarde įvestais duomenimis

                if self.license_plate and self.license_plate != self.driver_id.license_plate:
                    update_driver_vals['license_plate'] = self.license_plate
                if self.trailer and self.trailer != self.driver_id.trailer:
                    update_driver_vals['trailer'] = self.trailer
                if update_driver_vals:
                    self.driver_id.write(update_driver_vals)
    
                if route.picking_ids:
                    # Pakeičia vairuotoją prie sukurtų važtaraščių ir perkėlimų
                    # (kuriais perduodama tara vairuotojui)

                    route.move_ids.sudo().write({
                        'location_dest_id': self.driver_id.id
                    })
                    route.picking_ids.sudo().write({
                        'location_dest_id': self.driver_id.id
                    })
        else:
            self.select_from_dif_obj()
        return {'type':'ir.actions.act_window_close'}