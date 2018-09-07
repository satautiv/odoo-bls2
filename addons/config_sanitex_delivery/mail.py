# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, api

class MailMessage(models.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    
    _inherit = 'mail.message'
    
    @api.model
    def _get_default_from(self):
        # TODO išsiaiškinti kokiu tikslu užklota
        return ''