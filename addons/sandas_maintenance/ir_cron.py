# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models
from odoo.tools import config

import logging

_logger = logging.getLogger(__name__)


class IrCronLog(models.Model):
    _name = 'ir.cron.log'
    _description = 'Cron Log'

    cron_id = fields.Many2one(
        'ir.cron', 'Cron', ondelete='set null', readonly=True
    )
    start_date = fields.Datetime('Start Date', readonly=True)
    done_date = fields.Datetime('Done Date', readonly=True)
    success = fields.Boolean('Success', readonly=True)
    error = fields.Char('Error', size=128, readonly=True)
    traceback = fields.Text('Traceback', readonly=True)


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def _process_end(self, modules):
        res = super(IrModelData, self)._process_end(modules)
        if config.get('readonly', False):
            return res
        try:
            cron_log_obj = self.env['ir.cron.log']
            logs = cron_log_obj.search([('done_date','=',False)])
            for log in logs:
                log.write({
                    'done_date': log.start_date,
                    'success': False,
                    'error': 'Server has been restarted.',
                })
        except Exception as e:
            _logger.info(e)
            _logger.info('Could not update canceled cron jobs.')
        return res
