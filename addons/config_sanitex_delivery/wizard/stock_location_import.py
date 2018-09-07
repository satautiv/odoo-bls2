# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, api
import csv
import base64

from odoo.exceptions import UserError

class stock_location_import_osv(models.TransientModel):
    _name = 'stock.location.import.osv'
    _description = 'Import Locations' 
    
    csv_file = fields.Binary('File', required=True)

    @api.multi
    def import_file(self):
        loc_obj = self.env['stock.location']
        file_splited = base64.decodestring(self.csv_file).decode('utf-8').split('\n')
        csvreader = csv.reader(file_splited, delimiter = ',')
        
        csvreader.__next__()
        for row in csvreader:
            if not row:
                continue
            parent_code = row[0]
            code = row[1]
            name = row[2]
            
            if not loc_obj.search([
                ('code','=',code)
            ]):
                parent = loc_obj.search([
                    ('name','=',parent_code)
                ], limit=1)
                if not parent:
                    raise UserError(_('There are no parent location with name %s') % parent_code)
                loc_vals = self.default_get(loc_obj._fields.keys())
                loc_vals['name'] = code + ' ' + name
                loc_vals['code'] = code
                loc_vals['location_id'] = parent.id
                loc_obj.create(loc_vals)
        return {'type':'ir.actions.act_window_close'}
    
stock_location_import_osv()