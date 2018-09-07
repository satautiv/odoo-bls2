# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api
from odoo.api import Environment


import threading
import logging

_logger = logging.getLogger(__name__)

class ResLang(models.Model):
    _inherit = 'res.lang'

    last_synchronisation_datetime = fields.Datetime('Date of Last Synchronisation', readonly=True)

    @api.multi
    def synchronise_translations(self):
        tranlation_env = self.env['ir.translation']
        for language in self:
            language_code = language.code
            sql = '''
                SELECT
                    id
                FROM
                    ir_translation
                WHERE
                    lang = %s
                    AND (last_synchronisation_datetime is null
                        OR (last_update_date is not null AND last_update_date > last_synchronisation_datetime))
            '''
            where = (language_code,)
            self.env.cr.execute(sql, where)
            tranlation_results = self.env.cr.fetchall()
            _logger.info('Found %s tranlsations to synchronize with querry: %s' % (
                str(len(tranlation_results)), sql%where
            ))
            if tranlation_results:
                translation_ids = [tranlation_result[0] for tranlation_result in tranlation_results]
                tranlation_env.browse(translation_ids).synchronise_translations()

    @api.model
    def cron_sync_translation(self):
        self.search([('active','=',True)]).synchronise_translations()

    @api.multi
    def _run_translation_sync(self):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            try:
                databases = new_self.env.user.company_id.atlas_server_ids.mapped('database_ids')
                for language in new_self:
                    language.synchronise_translations()
                    for database in databases:
                        database.call_method('ir.translation', 'clear_cache_after_syncronisations')
                        database.call_method('res.lang', 'start_sync', [[language.code]])
                new_cr.commit()
            finally:
                new_cr.close()

    @api.multi
    def run_translation_sync_in_thread(self):
        threaded_calculation = threading.Thread(
            target=self._run_translation_sync
        )
        threaded_calculation.start()

    @api.multi
    def action_sync_translations(self):
        self.run_translation_sync_in_thread()

    @api.model
    def start_sync(self, lang_codes):
        self.search([('code','in',lang_codes)]).synchronise_translations()
        return True