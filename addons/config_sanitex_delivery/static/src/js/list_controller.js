odoo.define('config_sanitex_delivey.ListController', function (require) {
	"use strict";

	var ListController = require('web.ListController');
    var core = require('web.core');
    var Sidebar = require('web.Sidebar');

    var _t = core._t;

	ListController.include({
	// Veiksmo mygtukams pridedami sequence numeriai, kad vėliau būtų galima surykiuoti mygtukus
		renderSidebar: function ($node) {
            if (this.hasSidebar && !this.sidebar) {
                var other = [];
                if (this.is_action_enabled('export')){
                    other.push({
                        label: _t("Export"),
                        callback: this._onExportData.bind(this),
                        sequence_no: 50
                    });
                }
                if (this.archiveEnabled) {
                    other.push({
                        label: _t("Archive"),
                        callback: this._onToggleArchiveState.bind(this, true),
                        sequence_no: 60
                    });
                    other.push({
                        label: _t("Unarchive"),
                        callback: this._onToggleArchiveState.bind(this, false),
                        sequence_no: 70
                    });
                }
                if (this.is_action_enabled('delete')) {
                    other.push({
                        label: _t('Delete'),
                        callback: this._onDeleteSelectedRecords.bind(this),
                        sequence_no: 80
                    });
                }
                this.sidebar = new Sidebar(this, {
                    editable: this.is_action_enabled('edit'),
                    env: {
                        context: this.model.get(this.handle, {raw: true}).getContext(),
                        activeIds: this.getSelectedIds(),
                        model: this.modelName,
                    },
                    actions: _.extend(this.toolbarActions, {other: other}),
                });
                this.sidebar.appendTo($node);

                this._toggleSidebar();
            }
        },


	});

});