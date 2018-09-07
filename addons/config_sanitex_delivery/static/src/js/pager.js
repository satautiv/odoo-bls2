odoo.define('config_sanitex_delivey.Pager', function (require) {
	"use strict";

	var Pager  = require('web.Pager');

	Pager.include({
		// Padaryta kad res.partner lentelėje nebūtų galima keisti limito
		init: function (parent, size, current_min, limit, options) {
            var can_edit_value = true;
            if (parent.hasOwnProperty('modelName')){
                if (parent.modelName == 'res.partner'){
                    can_edit_value = false;
                }
            };
            var new_options = _.defaults({}, options, {
                can_edit: can_edit_value
            });
            this._super(parent, size, current_min, limit, new_options);
        },

	});
});