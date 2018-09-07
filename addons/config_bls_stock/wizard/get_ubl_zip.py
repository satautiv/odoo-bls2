# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
# import time
import os
from zipfile import ZipFile
import base64

class GetUBLZip(models.TransientModel):
    _name = 'get.ubl.zip.wizard'
    _description = 'Adds formed UBLs to ZIP and returns to UI'
    
    file_name = fields.Char("File Name", size=128)
    ubl_zip = fields.Binary("File", attachment=True)
    
    @api.model
    def get_xml_paths(self, directory):
        file_paths = []
        for root, directories, files in os.walk(directory):
            for filename in files:
                if filename.lower().endswith('.xml'):
                    filepath = os.path.join(root, filename)
                    file_paths.append(filepath)
     
        return file_paths 
    
    @api.multi
    def get_ubls(self):
#         zip_file_name = time.strftime('%Y_%m_%d_%H_%M_%S') + ".zip"

        zip_file_name = self.env.user.get_today_datetime('%Y_%m_%d_%H_%M_%S') + ".zip"
        company = self.env.user.company_id
        
        self._cr.execute("""
            SELECT
                ubl_save_directory
            FROM
                res_company
            WHERE id = %s
            LIMIT 1
        """ , (company.id,))
        ubl_save_directory, = self._cr.fetchone()
        if not ubl_save_directory:
            raise UserError(
                _("UBL save directory is missing in the company configurations")
            )
            
        if ubl_save_directory.startswith('~'):
            home = os.path.expanduser("~")
            ubl_save_directory = home + ubl_save_directory[1:]
        
        if not os.path.exists(ubl_save_directory):
            os.makedirs(ubl_save_directory)

        xml_paths = self.get_xml_paths(ubl_save_directory)
        if not xml_paths:
            raise UserError(
                _("There are not any UBLs formed which can be downloaded")
            )

        zip_file_name_with_directory = os.path.join(ubl_save_directory, zip_file_name)
        
        with ZipFile(zip_file_name_with_directory,'w') as zip:
            for file in xml_paths:
                zip.write(file, os.path.basename(file))
                
        with open(zip_file_name_with_directory,'rb') as zip:
            self.write({
                'file_name': zip_file_name,
                'ubl_zip': base64.b64encode(zip.read()),
            })
        
        
        
        for file in xml_paths:        
            if os.path.isfile(file):
                os.unlink(file)
        
        context = self._context.copy()
        context['form_view_initial_mode'] = 'readonly'
        form_view = self.env.ref('config_bls_stock.view_get_ubl_zip_wizard2', False)[0]
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'get.ubl.zip.wizard',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id,'form')],
            'res_id': self.id,
            'nodestroy': False,
            'context': context,
        }