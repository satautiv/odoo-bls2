odoo.define('config_sanitex_delivey.DataExport', function (require) {
	"use strict";

	var DataExport = require('web.DataExport');
    var core = require('web.core');
    var Dialog = require('web.Dialog');

    var QWeb = core.qweb;
    var _t = core._t;


    DataExport.include({

//        Užklota kad į eksportų paiešką būtų galima perduoti kontextą
        show_exports_list: function() {
            if (this.$('.o_exported_lists_select').is(':hidden')) {
                this.$('.o_exported_lists').show();
                return $.when();
            }

            var self = this;
            return this._rpc({
                model: 'ir.exports',
                method: 'search_read',
                fields: ['name'],
                context: this.record.context,
                domain: [['resource', '=', this.record.model]]
            }).then(function (export_list) {
                if (!export_list.length) {
                    return;
                }
                self.$('.o_exported_lists').append(QWeb.render('Export.SavedList', {'existing_exports': export_list}));
                self.$('.o_exported_lists_select').on('change', function() {
                    self.$fields_list.empty();
                    var export_id = self.$('.o_exported_lists_select option:selected').val();
                    if(export_id) {
                        self._rpc({
                                route: '/web/export/namelist',
                                params: {
                                    model: self.record.model,
                                    export_id: parseInt(export_id, 10),
                                },
                            })
                            .then(do_load_export_field);
                    }
                });
                self.$('.o_delete_exported_list').click(function() {
                    self._rpc({
                            model: 'res.users',
                            method: 'can_user_edit_export',
                            args: [self.getSession().uid, ['o_delete_exported_list']],
                        }, {
                            timeout: 3000,
                            shadow: true,
                        }).then(function(result){
                            if(!result) {
                                Dialog.alert(self, _t("No Rights"));
                                return;
                            } else {

                                var select_exp = self.$('.o_exported_lists_select option:selected');
                                var options = {
                                    confirm_callback: function () {
                                        if (select_exp.val()) {
                                            self.exports.unlink([parseInt(select_exp.val(), 10)]);
                                            select_exp.remove();
                                            self.$fields_list.empty();
                                            if (self.$('.o_exported_lists_select option').length <= 1) {
                                                self.$('.o_exported_lists').hide();
                                            }
                                        }
                                    }
                                }
                                Dialog.confirm(this, _t("Do you really want to delete this export template?"), options);
                        }
                    });
                });
           });

            function do_load_export_field(field_list) {
                _.each(field_list, function (field) {
                    self.$fields_list.append(new Option(field.label, field.name));
                });
            }
        },
    });

});