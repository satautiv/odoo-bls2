# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, tools

import traceback
import psycopg2
import logging

_logger = logging.getLogger(__name__)


class ActionQueue(models.Model):
    _name = 'action.queue'
    _description = 'Cron will do these actions'

    function_to_perform = fields.Char('Function to Perform', size=128, readonly=True)
    object_for_action = fields.Char('Object of the Action', size=128, readonly=True)
    id_of_object = fields.Integer('Object ID', readonly=True)
    comments = fields.Text('Comments', readonly=True)
    error_traceback = fields.Text('Traceback', readonly=True)

    @api.multi
    def process(self):
        if self.exists():
            lock_cursor = self.env.registry.cursor()
            job_cursor = self.env.registry.cursor()
            try:
                lock_cursor.execute("""SELECT *
                                   FROM action_queue
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (str(self.id),), log_exceptions=False)
                locked_action = lock_cursor.fetchone()
                if not locked_action:
                    _logger.info("Action `%s` already executed by another process/thread (%s, %s, %s). Skipping it" % (
                        str(self.id), self.object_for_action, self.function_to_perform, str(self.id_of_object)
                    ))
                    return
                try:
                    new_env = self.env(cr=job_cursor)
                    record = new_env[self.object_for_action].with_context(action_from_queue=True).browse(self.id_of_object)
                    if record.exists():
                        method_to_call = getattr(record, self.function_to_perform)
                        method_to_call()
                    lock_cursor.execute('''DELETE FROM action_queue where id = %s''', (self.id,))
                except Exception as e:
                    err_note = tools.ustr(e)
                    trb = traceback.format_exc()
                    lock_cursor.execute(
                        """UPDATE action_queue SET comments = %s, error_traceback=%s WHERE id = %s""",
                        (err_note, trb, self.id)
                    )

            except psycopg2.OperationalError as e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.info("Action `%s` already executed by another process/thread (%s, %s, %s). Skipping it" % (
                        str(self.id), self.object_for_action, self.function_to_perform, str(self.id_of_object)
                    ))
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                lock_cursor.commit()
                lock_cursor.close()
                job_cursor.commit()
                job_cursor.close()


        # self.env.registry.db_name

    @api.multi
    def process_actions(self, functions=None):
        if functions is None:
            functions = []
        i = 0
        count = len(self)
        for action in self:
            i += 1
            _logger.info('Process action object %s (ID: %s) -- %s / %s' % (
                str(functions), str(action.id), str(i), str(count))
            )
            try:
                action.process()
                self.env.cr.commit()
            except:
                trb = traceback.format_exc()
                _logger.info(trb.encode('utf-8').decode('unicode-escape'))
                self.env.cr.rollback()

    @api.model
    def cron_process_the_queue(self, functions=None):
        if functions is None:
            functions = []
        domain = []
        if functions:
            domain.append(('function_to_perform','in',functions))
        actions = self.search(domain, order='id')
        return actions.process_actions(functions=functions)