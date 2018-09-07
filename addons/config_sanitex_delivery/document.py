# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields


class DocumentAttachment(models.Model):
    _name = 'document.attachment'

    name = fields.Char('Name', size=256, required=True)
    file_name = fields.Char('File Name', size=256)
    file = fields.Binary('File', attachment=True)