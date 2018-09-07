# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.api import Environment
from odoo import tools

import threading
import logging
import traceback
import time

_logger = logging.getLogger(__name__)


class run_function(models.TransientModel):
    _name = 'settings.run_function'
    _description = 'Run Any Function for any Object'

    object_name = fields.Char('Model', required=True)
    function_name = fields.Char('Method to Run', required=True)
    domain = fields.Char('Domain')

    @api.multi
    def _run_method(self, model, ffunction, records):

        with Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            records = records.with_env(self.env())
            i = pi = 0
            total_time = 0
            try:
                all = len(records)
                _logger.info('Runnin Function %s for model %s. %s records found' %(ffunction, str(model), all))
                for record in records:
                    i += 1
                    # res = i*1000/all
                    # if res/10 > ((i-1)*1000/all)/10:

                    if round((i / all) * 1000) != pi:
                        pi = round((i / all) * 1000)
                        _logger.info('Running Function %s, model %s progress: %s / %s . Average duration - %.5f' % (
                            ffunction, str(model), str(i), all, total_time/i)
                        )
                    try:
                        method_to_call = getattr(record, ffunction)
                        t = time.time()
                        method_to_call()
                        duration = time.time() - t
                        total_time += duration
                        new_cr.commit()
                    except Exception as e:
                        _logger.info('Runnin Function %s, model %s, record %s: Error - %s \n %s' % (
                            str(model), ffunction, str(record), tools.ustr(e), traceback.format_exc())
                        )
                        new_cr.rollback()
                        pass

                new_cr.commit()
            finally:
                new_cr.close()

    @api.multi
    def run_method_in_thread(self, model, ffunction, records):
        threaded_calculation = threading.Thread(
            target=self._run_method, args=(model, ffunction, records)
        )
        threaded_calculation.start()

    @api.multi
    def run(self):
        model_env = self.env[self.object_name]
        if self.domain:
            model_records = model_env.sudo().search(safe_eval(self.domain))
        else:
            model_records = model_env.sudo().search([])
        self.run_method_in_thread(model_env, self.function_name, model_records)
        return {'type': 'ir.actions.act_window_close'}